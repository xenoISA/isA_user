"""
Device Authentication Repository - Async Version

Device authentication data access layer using AsyncPostgresClient.
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class DeviceAuthRepository:
    """Device authentication data access layer - async version"""

    def __init__(self, organization_service_client=None, config: Optional[ConfigManager] = None):
        self.organization_service_client = organization_service_client

        if config is None:
            config = ConfigManager("auth_service")

        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id='auth-service')
        self.schema = "auth"
        self.devices_table = "devices"
        self.device_logs_table = "device_logs"
        self.pairing_tokens_table = "device_pairing_tokens"

    async def create_device_credential(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create device credential"""
        try:
            # Verify organization exists via organization_service
            if self.organization_service_client:
                org = await self.organization_service_client.get_organization(
                    organization_id=device_data['organization_id'],
                    user_id="system"
                )
                if not org:
                    raise Exception(f"Organization '{device_data.get('organization_id')}' not found.")

            now = datetime.now(timezone.utc)
            metadata = device_data.get('metadata', {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            query = f"""
                INSERT INTO {self.schema}.{self.devices_table}
                (device_id, device_secret, organization_id, device_name, device_type,
                 status, metadata, expires_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            params = [
                device_data['device_id'],
                device_data['device_secret'],
                device_data['organization_id'],
                device_data.get('device_name'),
                device_data.get('device_type'),
                device_data.get('status', 'active'),
                metadata,
                device_data.get('expires_at'),
                now,
                now
            ]

            logger.info(f"Inserting device credential: {device_data['device_id']}")
            async with self.db:
                count = await self.db.execute(query, params=params)

            logger.info(f"Insert result count: {count}")
            if count is not None and count > 0:
                return await self.get_device_credential(device_data['device_id'])
            return None

        except Exception as e:
            import traceback
            logger.error(f"Error creating device credential: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            error_msg = str(e)
            if "does not exist" in error_msg:
                raise Exception(f"Database table '{self.schema}.{self.devices_table}' does not exist.")
            elif "foreign key" in error_msg.lower() or "organization" in error_msg.lower():
                raise Exception(f"Organization '{device_data.get('organization_id')}' not found.")
            else:
                raise Exception(f"Failed to create device credential: {error_msg}")

    async def get_device_credential(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device credential"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.devices_table} WHERE device_id = $1 AND status = 'active'",
                    params=[device_id]
                )
            return result
        except Exception as e:
            logger.error(f"Error getting device credential: {e}")
            return None

    async def verify_device_credential(self, device_id: str, device_secret: str) -> Optional[Dict[str, Any]]:
        """Verify device credential"""
        try:
            async with self.db:
                device = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.devices_table} WHERE device_id = $1 AND device_secret = $2 AND status = 'active'",
                    params=[device_id, device_secret]
                )

            if device:
                # Check if expired
                expires_at = device.get('expires_at')
                if expires_at is not None:
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)

                    current_time = datetime.now(timezone.utc)
                    if expires_at < current_time:
                        await self._log_auth_attempt(device_id, 'failed', error='Device credential expired')
                        return None

                # Update authentication info
                auth_count = device.get('authentication_count', 0) + 1
                now = datetime.now(timezone.utc)

                async with self.db:
                    await self.db.execute(
                        f"""UPDATE {self.schema}.{self.devices_table}
                           SET last_authenticated_at = $1, authentication_count = $2, updated_at = $3
                           WHERE device_id = $4""",
                        params=[now, auth_count, now, device_id]
                    )

                await self._log_auth_attempt(device_id, 'success')
                return device
            else:
                await self._log_auth_attempt(device_id, 'failed', error='Invalid credentials')
                return None

        except Exception as e:
            logger.error(f"Error verifying device credential: {e}")
            return None

    async def _log_auth_attempt(self, device_id: str, status: str,
                                ip_address: str = None, user_agent: str = None,
                                error: str = None):
        """Log authentication attempt"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                INSERT INTO {self.schema}.{self.device_logs_table}
                (device_id, auth_status, ip_address, user_agent, error_message, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """
            params = [device_id, status, ip_address, user_agent, error, now]

            async with self.db:
                await self.db.execute(query, params=params)
        except Exception as e:
            logger.error(f"Error logging auth attempt: {e}")

    async def update_device_credential(self, device_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update device credential"""
        try:
            filtered_updates = {k: v for k, v in updates.items()
                                if k not in ['device_id', 'created_at']}

            if not filtered_updates:
                return None

            filtered_updates['updated_at'] = datetime.now(timezone.utc)

            set_parts = []
            values = []
            param_index = 1

            for key, value in filtered_updates.items():
                set_parts.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1

            set_clause = ', '.join(set_parts)
            values.append(device_id)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.devices_table} SET {set_clause} WHERE device_id = ${param_index}",
                    params=values
                )

            if result and result > 0:
                return await self.get_device_credential(device_id)
            return None
        except Exception as e:
            logger.error(f"Error updating device credential: {e}")
            return None

    async def revoke_device_credential(self, device_id: str) -> bool:
        """Revoke device credential"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.devices_table} SET status = 'revoked', updated_at = $1 WHERE device_id = $2",
                    params=[now, device_id]
                )

            return result is not None and result > 0
        except Exception as e:
            logger.error(f"Error revoking device credential: {e}")
            return False

    async def list_organization_devices(self, organization_id: str) -> List[Dict[str, Any]]:
        """List all devices for an organization"""
        try:
            async with self.db:
                results = await self.db.query(
                    f"""SELECT device_id, device_name, device_type, status,
                              last_authenticated_at, authentication_count, created_at, expires_at
                       FROM {self.schema}.{self.devices_table}
                       WHERE organization_id = $1
                       ORDER BY created_at DESC""",
                    params=[organization_id]
                )

            return results if results else []
        except Exception as e:
            logger.error(f"Error listing organization devices: {e}")
            return []

    async def get_device_auth_logs(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get device authentication logs"""
        try:
            async with self.db:
                results = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.device_logs_table} WHERE device_id = $1 ORDER BY created_at DESC LIMIT $2",
                    params=[device_id, limit]
                )

            return results if results else []
        except Exception as e:
            logger.error(f"Error getting device auth logs: {e}")
            return []

    # ============================================================================
    # Device Pairing Token Methods
    # ============================================================================

    async def create_pairing_token(
        self,
        device_id: str,
        pairing_token: str,
        expires_at: datetime
    ) -> Dict[str, Any]:
        """Create a new pairing token for a device"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                INSERT INTO {self.schema}.{self.pairing_tokens_table}
                (device_id, pairing_token, expires_at, created_at)
                VALUES ($1, $2, $3, $4)
                RETURNING id, device_id, pairing_token, expires_at, created_at
            """

            async with self.db:
                results = await self.db.query(query, params=[device_id, pairing_token, expires_at, now])

            if results and len(results) > 0:
                return dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Error creating pairing token: {e}")
            raise

    async def get_pairing_token(self, pairing_token: str) -> Optional[Dict[str, Any]]:
        """Get pairing token by token string"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"""SELECT id, device_id, pairing_token, expires_at, created_at, used, used_at, user_id
                        FROM {self.schema}.{self.pairing_tokens_table}
                        WHERE pairing_token = $1""",
                    params=[pairing_token]
                )

            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting pairing token: {e}")
            return None

    async def mark_pairing_token_used(self, pairing_token: str, user_id: str) -> bool:
        """Mark pairing token as used"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"""UPDATE {self.schema}.{self.pairing_tokens_table}
                        SET used = TRUE, used_at = $1, user_id = $2
                        WHERE pairing_token = $3""",
                    params=[now, user_id, pairing_token]
                )

            return result is not None and result > 0
        except Exception as e:
            logger.error(f"Error marking pairing token as used: {e}")
            return False

    async def delete_expired_pairing_tokens(self) -> int:
        """Delete expired pairing tokens (cleanup job)"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"DELETE FROM {self.schema}.{self.pairing_tokens_table} WHERE expires_at < $1",
                    params=[now]
                )

            count = result if result else 0
            logger.info(f"Deleted {count} expired pairing tokens")
            return count
        except Exception as e:
            logger.error(f"Error deleting expired pairing tokens: {e}")
            return 0
