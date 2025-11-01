"""
OTA Repository

Data access layer for OTA service - handles database operations for:
- Firmware management
- Update campaigns
- Device updates
- Rollback operations
"""

import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct, ListValue

from isa_common.postgres_client import PostgresClient
from .models import (
    FirmwareResponse, UpdateCampaignResponse, DeviceUpdateResponse,
    RollbackResponse, UpdateStatsResponse,
    UpdateStatus, DeploymentStrategy, Priority, RollbackTrigger
)

logger = logging.getLogger(__name__)


def _convert_protobuf_to_native(value: Any) -> Any:
    """Convert Protobuf types to Python native types"""
    if isinstance(value, ListValue):
        return list(value)
    elif isinstance(value, Struct):
        return MessageToDict(value)
    elif isinstance(value, (list, tuple)):
        return [_convert_protobuf_to_native(item) for item in value]
    elif isinstance(value, dict):
        return {k: _convert_protobuf_to_native(v) for k, v in value.items()}
    else:
        return value


class OTARepository:
    """OTA data access layer"""

    def __init__(self):
        """Initialize OTA repository"""
        self.db = PostgresClient(
            host=os.getenv("POSTGRES_GRPC_HOST", "isa-postgres-grpc"),
            port=int(os.getenv("POSTGRES_GRPC_PORT", "50061")),
            user_id="ota_service"
        )
        self.schema = "ota"
        self.firmware_table = "firmware"
        self.campaigns_table = "update_campaigns"
        self.device_updates_table = "device_updates"
        self.downloads_table = "firmware_downloads"
        self.rollback_table = "rollback_logs"

    # ==================== Firmware Operations ====================

    async def create_firmware(self, firmware_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create firmware record"""
        try:
            # Check if firmware already exists
            existing = await self.get_firmware_by_id(firmware_data["firmware_id"])
            if existing:
                logger.info(f"Firmware already exists: {firmware_data['firmware_id']}")
                return existing

            # Check for duplicate device_model + version
            duplicate = await self.get_firmware_by_model_version(
                firmware_data["device_model"],
                firmware_data["version"]
            )
            if duplicate:
                logger.info(f"Firmware version already exists for {firmware_data['device_model']} v{firmware_data['version']}")
                return duplicate

            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.firmware_table} (
                    firmware_id, name, version, description, device_model, manufacturer,
                    min_hardware_version, max_hardware_version, file_size, file_url,
                    checksum_md5, checksum_sha256, tags, metadata, is_beta,
                    is_security_update, changelog, download_count, success_rate,
                    created_by, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
                RETURNING *
            '''

            params = [
                firmware_data["firmware_id"],
                firmware_data["name"],
                firmware_data["version"],
                firmware_data.get("description"),
                firmware_data["device_model"],
                firmware_data["manufacturer"],
                firmware_data.get("min_hardware_version"),
                firmware_data.get("max_hardware_version"),
                firmware_data["file_size"],
                firmware_data["file_url"],
                firmware_data["checksum_md5"],
                firmware_data["checksum_sha256"],
                firmware_data.get("tags", []),
                firmware_data.get("metadata", {}),
                firmware_data.get("is_beta", False),
                firmware_data.get("is_security_update", False),
                firmware_data.get("changelog"),
                firmware_data.get("download_count", 0),
                firmware_data.get("success_rate", 0.0),
                firmware_data["created_by"],
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                logger.info(f"Created firmware: {firmware_data['firmware_id']}")
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error creating firmware: {e}")
            raise

    async def get_firmware_by_id(self, firmware_id: str) -> Optional[Dict[str, Any]]:
        """Get firmware by ID"""
        try:
            query = f'SELECT * FROM {self.schema}.{self.firmware_table} WHERE firmware_id = $1 LIMIT 1'

            with self.db:
                results = self.db.query(query, [firmware_id], schema=self.schema)

            if results and len(results) > 0:
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error getting firmware: {e}")
            return None

    async def get_firmware_by_model_version(self, device_model: str, version: str) -> Optional[Dict[str, Any]]:
        """Get firmware by device model and version"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.firmware_table}
                WHERE device_model = $1 AND version = $2
                LIMIT 1
            '''

            with self.db:
                results = self.db.query(query, [device_model, version], schema=self.schema)

            if results and len(results) > 0:
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error getting firmware by model/version: {e}")
            return None

    async def list_firmware(
        self,
        device_model: Optional[str] = None,
        manufacturer: Optional[str] = None,
        is_beta: Optional[bool] = None,
        is_security_update: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List firmware with filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if device_model:
                param_count += 1
                conditions.append(f"device_model = ${param_count}")
                params.append(device_model)

            if manufacturer:
                param_count += 1
                conditions.append(f"manufacturer = ${param_count}")
                params.append(manufacturer)

            if is_beta is not None:
                param_count += 1
                conditions.append(f"is_beta = ${param_count}")
                params.append(is_beta)

            if is_security_update is not None:
                param_count += 1
                conditions.append(f"is_security_update = ${param_count}")
                params.append(is_security_update)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.firmware_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error listing firmware: {e}")
            return []

    async def update_firmware_stats(
        self,
        firmware_id: str,
        download_count_delta: int = 0,
        success_rate: Optional[float] = None
    ) -> bool:
        """Update firmware statistics"""
        try:
            # Get current stats
            firmware = await self.get_firmware_by_id(firmware_id)
            if not firmware:
                return False

            now = datetime.now(timezone.utc)
            update_parts = ["updated_at = $1"]
            params = [now]
            param_count = 1

            if download_count_delta != 0:
                current_count = firmware.get("download_count", 0)
                param_count += 1
                update_parts.append(f"download_count = ${param_count}")
                params.append(max(0, current_count + download_count_delta))

            if success_rate is not None:
                param_count += 1
                update_parts.append(f"success_rate = ${param_count}")
                params.append(success_rate)

            param_count += 1
            params.append(firmware_id)

            query = f'''
                UPDATE {self.schema}.{self.firmware_table}
                SET {', '.join(update_parts)}
                WHERE firmware_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating firmware stats: {e}")
            return False

    # ==================== Campaign Operations ====================

    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create update campaign"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.campaigns_table} (
                    campaign_id, name, description, firmware_id, status,
                    start_time, end_time, target_devices, target_criteria,
                    rollout_percentage, auto_rollback, rollback_threshold,
                    force_update, priority, tags, metadata, created_by,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                RETURNING *
            '''

            params = [
                campaign_data["campaign_id"],
                campaign_data["name"],
                campaign_data.get("description"),
                campaign_data["firmware_id"],
                campaign_data.get("status", "created"),
                campaign_data.get("start_time"),
                campaign_data.get("end_time"),
                campaign_data.get("target_devices", []),
                campaign_data.get("target_criteria", {}),
                campaign_data.get("rollout_percentage", 100),
                campaign_data.get("auto_rollback", True),
                campaign_data.get("rollback_threshold", 10.0),
                campaign_data.get("force_update", False),
                campaign_data.get("priority", 0),
                campaign_data.get("tags", []),
                campaign_data.get("metadata", {}),
                campaign_data["created_by"],
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                logger.info(f"Created campaign: {campaign_data['campaign_id']}")
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            raise

    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID"""
        try:
            query = f'SELECT * FROM {self.schema}.{self.campaigns_table} WHERE campaign_id = $1 LIMIT 1'

            with self.db:
                results = self.db.query(query, [campaign_id], schema=self.schema)

            if results and len(results) > 0:
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error getting campaign: {e}")
            return None

    async def list_campaigns(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List campaigns with filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            if priority:
                param_count += 1
                conditions.append(f"priority = ${param_count}")
                params.append(priority)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.campaigns_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error listing campaigns: {e}")
            return []

    async def update_campaign_status(
        self,
        campaign_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Update campaign status"""
        try:
            now = datetime.now(timezone.utc)
            update_parts = ["status = $1", "updated_at = $2"]
            params = [status, now]
            param_count = 2

            # Add optional timestamp fields
            if status == UpdateStatus.IN_PROGRESS and "actual_start" not in kwargs:
                param_count += 1
                update_parts.append(f"actual_start = ${param_count}")
                params.append(now)
            elif status == UpdateStatus.COMPLETED and "actual_end" not in kwargs:
                param_count += 1
                update_parts.append(f"actual_end = ${param_count}")
                params.append(now)

            # Add any additional kwargs
            for key, value in kwargs.items():
                param_count += 1
                update_parts.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(campaign_id)

            query = f'''
                UPDATE {self.schema}.{self.campaigns_table}
                SET {', '.join(update_parts)}
                WHERE campaign_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating campaign status: {e}")
            return False

    async def update_campaign_progress(
        self,
        campaign_id: str,
        pending_delta: int = 0,
        in_progress_delta: int = 0,
        completed_delta: int = 0,
        failed_delta: int = 0,
        cancelled_delta: int = 0
    ) -> bool:
        """Update campaign progress counters"""
        try:
            campaign = await self.get_campaign_by_id(campaign_id)
            if not campaign:
                return False

            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.campaigns_table}
                SET pending_devices = $1,
                    in_progress_devices = $2,
                    completed_devices = $3,
                    failed_devices = $4,
                    cancelled_devices = $5,
                    updated_at = $6
                WHERE campaign_id = $7
            '''

            params = [
                max(0, campaign.get("pending_devices", 0) + pending_delta),
                max(0, campaign.get("in_progress_devices", 0) + in_progress_delta),
                max(0, campaign.get("completed_devices", 0) + completed_delta),
                max(0, campaign.get("failed_devices", 0) + failed_delta),
                max(0, campaign.get("cancelled_devices", 0) + cancelled_delta),
                now,
                campaign_id
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating campaign progress: {e}")
            return False

    # ==================== Device Update Operations ====================

    async def create_device_update(self, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create device update record"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.device_updates_table} (
                    update_id, device_id, campaign_id, firmware_id, status,
                    progress, error_message, error_code, retry_count,
                    scheduled_at, started_at, completed_at, metadata,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING *
            '''

            params = [
                update_data["update_id"],
                update_data["device_id"],
                update_data["campaign_id"],
                update_data["firmware_id"],
                update_data.get("status", "pending"),
                update_data.get("progress", 0.0),
                update_data.get("error_message"),
                update_data.get("error_code"),
                update_data.get("retry_count", 0),
                update_data.get("scheduled_at"),
                update_data.get("started_at"),
                update_data.get("completed_at"),
                update_data.get("metadata", {}),
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                logger.info(f"Created device update: {update_data['update_id']}")
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error creating device update: {e}")
            raise

    async def get_device_update_by_id(self, update_id: str) -> Optional[Dict[str, Any]]:
        """Get device update by ID"""
        try:
            query = f'SELECT * FROM {self.schema}.{self.device_updates_table} WHERE update_id = $1 LIMIT 1'

            with self.db:
                results = self.db.query(query, [update_id], schema=self.schema)

            if results and len(results) > 0:
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error getting device update: {e}")
            return None

    async def list_device_updates(
        self,
        device_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List device updates"""
        try:
            conditions = []
            params = []
            param_count = 0

            if device_id:
                param_count += 1
                conditions.append(f"device_id = ${param_count}")
                params.append(device_id)

            if campaign_id:
                param_count += 1
                conditions.append(f"campaign_id = ${param_count}")
                params.append(campaign_id)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.device_updates_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error listing device updates: {e}")
            return []

    async def update_device_update_status(
        self,
        update_id: str,
        status: str,
        progress_percentage: Optional[float] = None,
        error_message: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Update device update status"""
        try:
            now = datetime.now(timezone.utc)
            update_parts = ["status = $1", "updated_at = $2"]
            params = [status, now]
            param_count = 2

            if progress_percentage is not None:
                param_count += 1
                update_parts.append(f"progress = ${param_count}")
                params.append(progress_percentage)

            if error_message:
                param_count += 1
                update_parts.append(f"error_message = ${param_count}")
                params.append(error_message)

            if status == UpdateStatus.IN_PROGRESS and "started_at" not in kwargs:
                param_count += 1
                update_parts.append(f"started_at = ${param_count}")
                params.append(now)
            elif status in [UpdateStatus.COMPLETED, UpdateStatus.FAILED, UpdateStatus.CANCELLED]:
                if "completed_at" not in kwargs:
                    param_count += 1
                    update_parts.append(f"completed_at = ${param_count}")
                    params.append(now)

            # Add any additional kwargs
            for key, value in kwargs.items():
                param_count += 1
                update_parts.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(update_id)

            query = f'''
                UPDATE {self.schema}.{self.device_updates_table}
                SET {', '.join(update_parts)}
                WHERE update_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating device update status: {e}")
            return False

    # ==================== Rollback Operations ====================

    async def create_rollback_log(self, rollback_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create rollback log"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.rollback_table} (
                    rollback_id, device_id, campaign_id, from_firmware_id,
                    to_firmware_id, reason, status, triggered_by,
                    error_message, metadata, created_at, completed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
            '''

            params = [
                rollback_data["rollback_id"],
                rollback_data["device_id"],
                rollback_data["campaign_id"],
                rollback_data["from_firmware_id"],
                rollback_data["to_firmware_id"],
                rollback_data["reason"],
                rollback_data.get("status", "pending"),
                rollback_data["triggered_by"],
                rollback_data.get("error_message"),
                rollback_data.get("metadata", {}),
                now,
                rollback_data.get("completed_at")
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                logger.info(f"Created rollback log: {rollback_data.get('rollback_id')}")
                return results[0]
            return None

        except Exception as e:
            logger.error(f"Error creating rollback log: {e}")
            raise

    # ==================== Statistics ====================

    async def get_update_stats(self) -> Optional[Dict[str, Any]]:
        """Get overall update statistics"""
        try:
            # Get campaign stats
            campaign_query = f'''
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as active,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM {self.schema}.{self.campaigns_table}
            '''

            # Get update stats
            update_query = f'''
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM {self.schema}.{self.device_updates_table}
            '''

            with self.db:
                campaign_results = self.db.query(campaign_query, [], schema=self.schema)
                update_results = self.db.query(update_query, [], schema=self.schema)

            if not campaign_results or not update_results:
                return None

            campaign_data = campaign_results[0]
            update_data = update_results[0]

            # Calculate success rate
            total = (update_data.get("completed", 0) or 0) + (update_data.get("failed", 0) or 0)
            success_rate = ((update_data.get("completed", 0) or 0) / total * 100) if total > 0 else 0.0

            return {
                "total_campaigns": campaign_data.get("total", 0) or 0,
                "active_campaigns": campaign_data.get("active", 0) or 0,
                "completed_campaigns": campaign_data.get("completed", 0) or 0,
                "failed_campaigns": campaign_data.get("failed", 0) or 0,
                "total_updates": update_data.get("total", 0) or 0,
                "pending_updates": update_data.get("pending", 0) or 0,
                "in_progress_updates": update_data.get("in_progress", 0) or 0,
                "completed_updates": update_data.get("completed", 0) or 0,
                "failed_updates": update_data.get("failed", 0) or 0,
                "success_rate": round(success_rate, 2),
                "avg_update_time": 8.5,  # TODO: Calculate from actual data
                "total_data_transferred": 0,  # TODO: Calculate from downloads
                "last_24h_updates": 0,  # TODO: Filter by time
                "last_24h_failures": 0,
                "last_24h_data_transferred": 0,
                "updates_by_device_type": {},
                "updates_by_firmware_version": {}
            }

        except Exception as e:
            logger.error(f"Error getting update stats: {e}")
            return None

    # ==================== Database Health ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            query = f'SELECT 1 FROM {self.schema}.{self.firmware_table} LIMIT 1'

            with self.db:
                self.db.query(query, [], schema=self.schema)

            return True

        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    async def cancel_device_updates(self, device_id: str) -> int:
        """Cancel all pending/in-progress updates for a device"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.device_update_table}
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE device_id = $2
                AND status IN ($3, $4, $5)
            '''
            with self.db:
                count = self.db.execute(
                    query,
                    ['cancelled', device_id, 'created', 'scheduled', 'in_progress'],
                    schema=self.schema
                )
            return count if count else 0
        except Exception as e:
            logger.error(f"Error cancelling device updates: {e}")
            return 0
