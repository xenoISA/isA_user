"""
Device Repository - Data access layer for device service
Handles database operations for devices, groups, commands, and frame configs

Uses AsyncPostgresClient with gRPC for PostgreSQL access (Async)
"""

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    DeviceResponse, DeviceStatus, DeviceType, ConnectivityType, SecurityLevel,
    DeviceGroupResponse, FrameConfig, DeviceAuthResponse
)

logger = logging.getLogger(__name__)


class DeviceRepository:
    """Device repository - data access layer for device operations (Async)"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize device repository with AsyncPostgresClient"""
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("device_service")

        # Discover PostgreSQL service
        # Priority: environment variable → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id='device_service'
        )
        # Table names (device schema)
        self.schema = "device"
        self.devices_table = "devices"
        self.groups_table = "device_groups"
        self.commands_table = "device_commands"
        self.frame_configs_table = "frame_configs"

    async def _ensure_schema(self):
        """Ensure device schema and tables exist"""
        try:
            # Create schema
            async with self.db:
                await self.db.execute("CREATE SCHEMA IF NOT EXISTS device")
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
                    uptime_percentage REAL DEFAULT 0.0,
                    registered_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    last_authenticated_at TIMESTAMPTZ,
                    decommissioned_at TIMESTAMPTZ,
                    CONSTRAINT valid_status CHECK (status IN ('pending', 'active', 'inactive', 'maintenance', 'error', 'decommissioned')),
                    CONSTRAINT valid_security_level CHECK (security_level IN ('none', 'basic', 'standard', 'high', 'critical'))
                )
            '''
            async with self.db:
                await self.db.execute(create_devices_table)
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

            query = f"""
                INSERT INTO {self.schema}.{self.devices_table} (
                    device_id, user_id, organization_id, device_name, device_type,
                    manufacturer, model, serial_number, firmware_version, hardware_version,
                    mac_address, connectivity_type, security_level, status, last_seen,
                    location, group_id, tags, metadata, total_commands,
                    total_telemetry_points, uptime_percentage, registered_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                    $21, $22, $23, $24
                )
                RETURNING *
            """

            params = [
                device_data["device_id"],
                device_data["user_id"],
                device_data.get("organization_id"),
                device_data["device_name"],
                device_data["device_type"],
                device_data["manufacturer"],
                device_data["model"],
                device_data["serial_number"],
                device_data["firmware_version"],
                device_data.get("hardware_version"),
                device_data.get("mac_address"),
                device_data["connectivity_type"],
                device_data.get("security_level", "standard"),
                device_data.get("status", "pending"),
                last_seen,
                json.dumps(location) if isinstance(location, dict) else location,
                device_data.get("group_id"),
                tags if isinstance(tags, list) else [],
                json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                0,  # total_commands
                0,  # total_telemetry_points
                0.0,  # uptime_percentage
                now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                row = results[0]
                # Deserialize JSONB fields
                if 'location' in row and isinstance(row['location'], str):
                    row['location'] = json.loads(row['location'])
                if 'metadata' in row and isinstance(row['metadata'], str):
                    row['metadata'] = json.loads(row['metadata'])
                if 'uptime_percentage' in row and row['uptime_percentage'] is not None:
                    row['uptime_percentage'] = float(row['uptime_percentage'])
                return DeviceResponse(**row)

            return None

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

            async with self.db:
                result = await self.db.query_row(query, params=params)

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

            async with self.db:
                results = await self.db.query(query, params=params)

            # Deserialize JSONB fields for each row
            devices = []
            if results:
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

            async with self.db:
                count = await self.db.execute(query, params=params)

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

            query = f"""
                INSERT INTO {self.schema}.{self.groups_table} (
                    group_id, user_id, organization_id, group_name, description,
                    parent_group_id, tags, metadata, device_count, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
            """

            params = [
                group_data["group_id"],
                group_data["user_id"],
                group_data.get("organization_id"),
                group_data["group_name"],
                group_data.get("description"),
                group_data.get("parent_group_id"),
                tags if isinstance(tags, list) else [],
                json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                0,  # device_count
                now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return DeviceGroupResponse(**results[0])

            return None

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

            async with self.db:
                result = await self.db.query_row(query, params=params)

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
            now = datetime.now(timezone.utc)
            sleep_schedule = config_data.get("sleep_schedule", {"start": "23:00", "end": "07:00"})
            auto_sync_albums = config_data.get("auto_sync_albums", [])

            query = f"""
                INSERT INTO {self.schema}.{self.frame_configs_table} (
                    device_id, brightness, contrast, auto_brightness, orientation,
                    slideshow_interval, slideshow_transition, shuffle_photos, show_metadata,
                    sleep_schedule, auto_sleep, motion_detection, auto_sync_albums,
                    sync_frequency, wifi_only_sync, display_mode, location, timezone,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (device_id) DO UPDATE SET
                    brightness = EXCLUDED.brightness,
                    contrast = EXCLUDED.contrast,
                    auto_brightness = EXCLUDED.auto_brightness,
                    orientation = EXCLUDED.orientation,
                    slideshow_interval = EXCLUDED.slideshow_interval,
                    slideshow_transition = EXCLUDED.slideshow_transition,
                    shuffle_photos = EXCLUDED.shuffle_photos,
                    show_metadata = EXCLUDED.show_metadata,
                    sleep_schedule = EXCLUDED.sleep_schedule,
                    auto_sleep = EXCLUDED.auto_sleep,
                    motion_detection = EXCLUDED.motion_detection,
                    auto_sync_albums = EXCLUDED.auto_sync_albums,
                    sync_frequency = EXCLUDED.sync_frequency,
                    wifi_only_sync = EXCLUDED.wifi_only_sync,
                    display_mode = EXCLUDED.display_mode,
                    location = EXCLUDED.location,
                    timezone = EXCLUDED.timezone,
                    updated_at = EXCLUDED.updated_at
            """

            params = [
                device_id,
                config_data.get("brightness", 80),
                config_data.get("contrast", 100),
                config_data.get("auto_brightness", True),
                config_data.get("orientation", "auto"),
                config_data.get("slideshow_interval", 30),
                config_data.get("slideshow_transition", "fade"),
                config_data.get("shuffle_photos", True),
                config_data.get("show_metadata", False),
                json.dumps(sleep_schedule) if isinstance(sleep_schedule, dict) else sleep_schedule,
                config_data.get("auto_sleep", True),
                config_data.get("motion_detection", True),
                auto_sync_albums if isinstance(auto_sync_albums, list) else [],
                config_data.get("sync_frequency", "hourly"),
                config_data.get("wifi_only_sync", True),
                config_data.get("display_mode", "photo_slideshow"),
                config_data.get("location"),
                config_data.get("timezone", "UTC"),
                now,
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count >= 0

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

            async with self.db:
                result = await self.db.query_row(query, params=params)

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
            now = datetime.now(timezone.utc)
            parameters = command_data.get("parameters", {})

            query = f"""
                INSERT INTO {self.schema}.{self.commands_table} (
                    command_id, device_id, user_id, command, parameters,
                    timeout, priority, require_ack, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """

            params = [
                command_data["command_id"],
                command_data["device_id"],
                command_data["user_id"],
                command_data["command"],
                json.dumps(parameters) if isinstance(parameters, dict) else parameters,
                command_data.get("timeout", 30),
                command_data.get("priority", 1),
                command_data.get("require_ack", True),
                "pending",
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

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
                update_data["result"] = json.dumps(result) if isinstance(result, dict) else result

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

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating command status: {e}")
            return False

    # ==================== Utility Methods ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1 as connected", params=[])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
