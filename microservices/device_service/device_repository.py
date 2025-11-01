"""
Device Repository - Data access layer for device service
Handles database operations for devices, groups, commands, and frame configs

Uses PostgresClient with gRPC for PostgreSQL access
"""

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .models import (
    DeviceResponse, DeviceStatus, DeviceType, ConnectivityType, SecurityLevel,
    DeviceGroupResponse, FrameConfig, DeviceAuthResponse
)

logger = logging.getLogger(__name__)


class DeviceRepository:
    """Device repository - data access layer for device operations"""

    def __init__(self):
        """Initialize device repository with PostgresClient"""
        # TODO: Use Consul service discovery instead of hardcoded host/port
        self.db = PostgresClient(
            host='isa-postgres-grpc',
            port=50061,
            user_id='device_service'
        )
        # Table names (device schema)
        self.schema = "device"
        self.devices_table = "devices"
        self.groups_table = "device_groups"
        self.commands_table = "device_commands"
        self.frame_configs_table = "frame_configs"

        # Ensure schema exists
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure device schema and tables exist"""
        try:
            # Create schema
            with self.db:
                self.db.execute("CREATE SCHEMA IF NOT EXISTS device", schema='public')
                logger.info("Device schema ensured")

            # Create devices table
            create_devices_table = '''
                CREATE TABLE IF NOT EXISTS device.devices (
                    device_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    organization_id VARCHAR(255),
                    device_name VARCHAR(200) NOT NULL,
                    device_type VARCHAR(50) NOT NULL,
                    manufacturer VARCHAR(100) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    serial_number VARCHAR(100) NOT NULL UNIQUE,
                    firmware_version VARCHAR(50) NOT NULL,
                    hardware_version VARCHAR(50),
                    mac_address VARCHAR(17),
                    connectivity_type VARCHAR(50) NOT NULL,
                    security_level VARCHAR(20) DEFAULT 'standard',
                    status VARCHAR(20) DEFAULT 'pending',
                    last_seen TIMESTAMPTZ,
                    location JSONB,
                    group_id VARCHAR(255),
                    tags TEXT[] DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    total_commands INTEGER DEFAULT 0,
                    total_telemetry_points INTEGER DEFAULT 0,
                    uptime_percentage DECIMAL(5,2) DEFAULT 0.00,
                    registered_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    last_authenticated_at TIMESTAMPTZ,
                    decommissioned_at TIMESTAMPTZ,
                    CONSTRAINT valid_status CHECK (status IN ('pending', 'active', 'inactive', 'maintenance', 'error', 'decommissioned')),
                    CONSTRAINT valid_security_level CHECK (security_level IN ('none', 'basic', 'standard', 'high', 'critical'))
                )
            '''
            with self.db:
                self.db.execute(create_devices_table, schema=self.schema)
                logger.info("Devices table ensured")

        except Exception as e:
            logger.warning(f"Could not ensure schema/tables (may already exist): {e}")

    # ==================== Device Operations ====================

    async def create_device(self, device_data: Dict[str, Any]) -> Optional[DeviceResponse]:
        """Create a new device"""
        try:
            # Prepare location, tags, and metadata as JSON strings for PostgreSQL JSONB/ARRAY types
            location = device_data.get("location", {})
            tags = device_data.get("tags", [])
            metadata = device_data.get("metadata", {})

            # Convert datetime objects to ISO format strings for gRPC
            now = datetime.now(timezone.utc)
            last_seen = device_data.get("last_seen")
            if isinstance(last_seen, datetime):
                last_seen = last_seen.isoformat()

            data = {
                "device_id": device_data["device_id"],
                "user_id": device_data["user_id"],
                "organization_id": device_data.get("organization_id"),
                "device_name": device_data["device_name"],
                "device_type": device_data["device_type"],
                "manufacturer": device_data["manufacturer"],
                "model": device_data["model"],
                "serial_number": device_data["serial_number"],
                "firmware_version": device_data["firmware_version"],
                "hardware_version": device_data.get("hardware_version"),
                "mac_address": device_data.get("mac_address"),
                "connectivity_type": device_data["connectivity_type"],
                "security_level": device_data.get("security_level", "standard"),
                "status": device_data.get("status", "pending"),
                "last_seen": last_seen,
                "location": json.dumps(location) if isinstance(location, dict) else location,
                "group_id": device_data.get("group_id"),
                "tags": tags if isinstance(tags, list) else [],
                "metadata": json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                "total_commands": 0,
                "total_telemetry_points": 0,
                "uptime_percentage": 0.0,
                "registered_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.devices_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_device_by_id(device_data["device_id"])

            # Even if count is None, try to get the device (might have been inserted)
            return await self.get_device_by_id(device_data["device_id"])

        except Exception as e:
            logger.error(f"Error creating device: {e}")
            raise

    async def get_device_by_id(self, device_id: str) -> Optional[DeviceResponse]:
        """Get device by device_id"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.devices_table}
                WHERE device_id = $1
            """
            params = [device_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                # Deserialize JSONB fields from JSON strings to dicts
                if 'location' in result and isinstance(result['location'], str):
                    result['location'] = json.loads(result['location'])
                if 'metadata' in result and isinstance(result['metadata'], str):
                    result['metadata'] = json.loads(result['metadata'])

                # Convert numeric types to float
                if 'uptime_percentage' in result and result['uptime_percentage'] is not None:
                    result['uptime_percentage'] = float(result['uptime_percentage'])

                return DeviceResponse(**result)
            return None

        except Exception as e:
            logger.error(f"Error getting device by ID {device_id}: {e}")
            return None

    async def list_user_devices(
        self,
        user_id: str,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        group_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DeviceResponse]:
        """List devices for a user with optional filters"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if device_type:
                param_count += 1
                conditions.append(f"device_type = ${param_count}")
                params.append(device_type)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            if group_id:
                param_count += 1
                conditions.append(f"group_id = ${param_count}")
                params.append(group_id)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.devices_table}
                WHERE {where_clause}
                ORDER BY last_seen DESC NULLS LAST, registered_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            # Deserialize JSONB fields for each row
            devices = []
            for row in results:
                if 'location' in row and isinstance(row['location'], str):
                    row['location'] = json.loads(row['location'])
                if 'metadata' in row and isinstance(row['metadata'], str):
                    row['metadata'] = json.loads(row['metadata'])
                # Convert numeric types to float
                if 'uptime_percentage' in row and row['uptime_percentage'] is not None:
                    row['uptime_percentage'] = float(row['uptime_percentage'])
                devices.append(DeviceResponse(**row))

            return devices

        except Exception as e:
            logger.error(f"Error listing user devices: {e}")
            return []

    async def update_device(
        self,
        device_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update device"""
        try:
            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            # Auto-add updated_at
            update_data["updated_at"] = datetime.now(timezone.utc)

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add WHERE condition
            param_count += 1
            params.append(device_id)
            device_id_param = param_count

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.devices_table}
                SET {set_clause}
                WHERE device_id = ${device_id_param}
            """

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating device: {e}")
            raise

    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus,
        last_seen: Optional[datetime] = None
    ) -> bool:
        """Update device status and last_seen"""
        try:
            update_data = {
                "status": status.value if isinstance(status, DeviceStatus) else status,
                "updated_at": datetime.now(timezone.utc)
            }

            if last_seen:
                update_data["last_seen"] = last_seen

            return await self.update_device(device_id, update_data)

        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return False

    async def delete_device(self, device_id: str) -> bool:
        """Delete a device (soft delete - set to decommissioned)"""
        try:
            update_data = {
                "status": DeviceStatus.DECOMMISSIONED.value,
                "decommissioned_at": datetime.now(timezone.utc)
            }
            return await self.update_device(device_id, update_data)

        except Exception as e:
            logger.error(f"Error deleting device: {e}")
            raise

    # ==================== Device Group Operations ====================

    async def create_device_group(self, group_data: Dict[str, Any]) -> Optional[DeviceGroupResponse]:
        """Create a device group"""
        try:
            tags = group_data.get("tags", [])
            metadata = group_data.get("metadata", {})
            now = datetime.now(timezone.utc)

            data = {
                "group_id": group_data["group_id"],
                "user_id": group_data["user_id"],
                "organization_id": group_data.get("organization_id"),
                "group_name": group_data["group_name"],
                "description": group_data.get("description"),
                "parent_group_id": group_data.get("parent_group_id"),
                "tags": tags if isinstance(tags, list) else [],
                "metadata": json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                "device_count": 0,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.groups_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_device_group_by_id(group_data["group_id"])

            return await self.get_device_group_by_id(group_data["group_id"])

        except Exception as e:
            logger.error(f"Error creating device group: {e}")
            raise

    async def get_device_group_by_id(self, group_id: str) -> Optional[DeviceGroupResponse]:
        """Get device group by ID"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.groups_table}
                WHERE group_id = $1
            """
            params = [group_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return DeviceGroupResponse(**result)
            return None

        except Exception as e:
            logger.error(f"Error getting device group: {e}")
            return None

    # ==================== Frame Config Operations ====================

    async def create_frame_config(self, device_id: str, config_data: Dict[str, Any]) -> bool:
        """Create or update frame configuration"""
        try:
            data = {
                "device_id": device_id,
                "brightness": config_data.get("brightness", 80),
                "contrast": config_data.get("contrast", 100),
                "auto_brightness": config_data.get("auto_brightness", True),
                "orientation": config_data.get("orientation", "auto"),
                "slideshow_interval": config_data.get("slideshow_interval", 30),
                "slideshow_transition": config_data.get("slideshow_transition", "fade"),
                "shuffle_photos": config_data.get("shuffle_photos", True),
                "show_metadata": config_data.get("show_metadata", False),
                "sleep_schedule": config_data.get("sleep_schedule", {"start": "23:00", "end": "07:00"}),
                "auto_sleep": config_data.get("auto_sleep", True),
                "motion_detection": config_data.get("motion_detection", True),
                "auto_sync_albums": config_data.get("auto_sync_albums", []),
                "sync_frequency": config_data.get("sync_frequency", "hourly"),
                "wifi_only_sync": config_data.get("wifi_only_sync", True),
                "display_mode": config_data.get("display_mode", "photo_slideshow"),
                "location": config_data.get("location"),
                "timezone": config_data.get("timezone", "UTC"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            with self.db:
                count = self.db.insert_into(
                    self.frame_configs_table,
                    [data],
                    schema=self.schema,
                    on_conflict="ON CONFLICT (device_id) DO UPDATE SET " +
                               ", ".join([f"{k} = EXCLUDED.{k}" for k in data.keys() if k != "device_id"])
                )

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error creating frame config: {e}")
            return False

    async def get_frame_config(self, device_id: str) -> Optional[FrameConfig]:
        """Get frame configuration"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.frame_configs_table}
                WHERE device_id = $1
            """
            params = [device_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return FrameConfig(**result)
            return None

        except Exception as e:
            logger.error(f"Error getting frame config: {e}")
            return None

    # ==================== Command Operations ====================

    async def create_device_command(self, command_data: Dict[str, Any]) -> bool:
        """Create a device command"""
        try:
            data = {
                "command_id": command_data["command_id"],
                "device_id": command_data["device_id"],
                "user_id": command_data["user_id"],
                "command": command_data["command"],
                "parameters": command_data.get("parameters", {}),
                "timeout": command_data.get("timeout", 30),
                "priority": command_data.get("priority", 1),
                "require_ack": command_data.get("require_ack", True),
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            }

            with self.db:
                count = self.db.insert_into(self.commands_table, [data], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error creating device command: {e}")
            return False

    async def update_command_status(
        self,
        command_id: str,
        status: str,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update command execution status"""
        try:
            update_data = {
                "status": status
            }

            if status == "sent":
                update_data["sent_at"] = datetime.now(timezone.utc)
            elif status == "acknowledged":
                update_data["acknowledged_at"] = datetime.now(timezone.utc)
            elif status in ["executed", "failed", "timeout"]:
                update_data["completed_at"] = datetime.now(timezone.utc)

            if result:
                update_data["result"] = result

            if error_message:
                update_data["error_message"] = error_message

            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(command_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.commands_table}
                SET {set_clause}
                WHERE command_id = ${param_count}
            """

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating command status: {e}")
            return False

    # ==================== Utility Methods ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            with self.db:
                result = self.db.query_row("SELECT 1 as connected", [])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
