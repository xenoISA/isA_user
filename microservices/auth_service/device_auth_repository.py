"""
Device Authentication Repository

设备认证数据访问层
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging
import json
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class DeviceAuthRepository:
    """设备认证数据访问层"""

    def __init__(self, organization_service_client=None, config: Optional[ConfigManager] = None):
        # Use organization service client for microservice communication
        self.organization_service_client = organization_service_client

        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("auth_service")

        # Discover PostgreSQL service (priority: env var → Consul → localhost)
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(host=host, port=port, user_id='auth-service')
        self.schema = "auth"
        self.devices_table = "devices"
        self.device_logs_table = "device_logs"
    
    async def create_device_credential(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建设备凭证"""
        try:
            # Verify organization exists via organization_service
            if self.organization_service_client:
                org = await self.organization_service_client.get_organization(
                    organization_id=device_data['organization_id'],
                    user_id="system"  # System call for device registration
                )
                if not org:
                    raise Exception(f"Organization '{device_data.get('organization_id')}' not found. Please ensure the organization exists before registering devices.")

            credential = {
                'device_id': device_data['device_id'],
                'device_secret': device_data['device_secret'],
                'organization_id': device_data['organization_id'],
                'device_name': device_data.get('device_name'),
                'device_type': device_data.get('device_type'),
                'status': device_data.get('status', 'active'),
                'metadata': device_data.get('metadata', {}),  # Keep as dict for JSONB
                'expires_at': device_data.get('expires_at')   # ISO string from main.py, or None
                # Note: created_at and updated_at use database DEFAULT NOW()
            }

            logger.info(f"Inserting device credential: {credential}")
            with self.db:
                count = self.db.insert_into(self.devices_table, [credential], schema=self.schema)

            logger.info(f"Insert result count: {count}")
            if count is not None and count > 0:
                # Fetch the device back to get all fields including created_at/updated_at
                return await self.get_device_credential(credential['device_id'])
            return None

        except Exception as e:
            import traceback
            logger.error(f"Error creating device credential: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            error_msg = str(e)
            if "does not exist" in error_msg:
                raise Exception(f"Database table '{self.schema}.{self.devices_table}' does not exist. Please run database migrations first.")
            elif "foreign key" in error_msg.lower() or "organization" in error_msg.lower():
                raise Exception(f"Organization '{device_data.get('organization_id')}' not found. Please ensure the organization exists before registering devices.")
            else:
                raise Exception(f"Failed to create device credential: {error_msg}")
    
    async def get_device_credential(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备凭证"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.devices_table} WHERE device_id = $1 AND status = 'active'",
                    [device_id],
                    schema=self.schema
                )

            return result
        except Exception as e:
            logger.error(f"Error getting device credential: {e}")
            return None
    
    async def verify_device_credential(self, device_id: str, device_secret: str) -> Optional[Dict[str, Any]]:
        """验证设备凭证"""
        try:
            # 获取设备凭证
            with self.db:
                device = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.devices_table} WHERE device_id = $1 AND device_secret = $2 AND status = 'active'",
                    [device_id, device_secret],
                    schema=self.schema
                )

            if device:
                # 检查是否过期
                expires_at = device.get('expires_at')
                if expires_at is not None:
                    if isinstance(expires_at, str):
                        # Parse ISO string and ensure it's timezone-aware
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    # Ensure expires_at is timezone-aware
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)

                    current_time = datetime.now(timezone.utc)
                    if expires_at < current_time:
                        await self._log_auth_attempt(device_id, 'failed',
                                              error='Device credential expired')
                        return None

                # 更新认证信息
                auth_count = device.get('authentication_count', 0) + 1
                now = datetime.now(timezone.utc)

                with self.db:
                    self.db.execute(
                        f"""UPDATE {self.schema}.{self.devices_table}
                           SET last_authenticated_at = $1, authentication_count = $2, updated_at = $3
                           WHERE device_id = $4""",
                        [now, auth_count, now, device_id],
                        schema=self.schema
                    )

                # 记录成功的认证
                await self._log_auth_attempt(device_id, 'success')

                return device
            else:
                # 记录失败的认证
                await self._log_auth_attempt(device_id, 'failed',
                                     error='Invalid credentials')
                return None

        except Exception as e:
            logger.error(f"Error verifying device credential: {e}")
            return None
    
    async def _log_auth_attempt(self, device_id: str, status: str,
                         ip_address: str = None, user_agent: str = None,
                         error: str = None):
        """记录认证尝试"""
        try:
            log_entry = {
                'device_id': device_id,
                'auth_status': status,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'error_message': error,
                'created_at': datetime.now(timezone.utc)
            }

            with self.db:
                self.db.insert_into(self.device_logs_table, [log_entry], schema=self.schema)
        except Exception as e:
            logger.error(f"Error logging auth attempt: {e}")
    
    async def update_device_credential(self, device_id: str,
                                      updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新设备凭证"""
        try:
            # 过滤掉不应更新的字段
            filtered_updates = {k: v for k, v in updates.items()
                              if k not in ['device_id', 'created_at']}

            if not filtered_updates:
                return None

            filtered_updates['updated_at'] = datetime.now(timezone.utc)

            # Build SET clause dynamically
            set_parts = []
            values = []
            param_index = 1

            for key, value in filtered_updates.items():
                set_parts.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1

            set_clause = ', '.join(set_parts)
            values.append(device_id)  # For WHERE clause

            with self.db:
                result = self.db.execute(
                    f"UPDATE {self.schema}.{self.devices_table} SET {set_clause} WHERE device_id = ${param_index}",
                    values,
                    schema=self.schema
                )

            if result > 0:
                return await self.get_device_credential(device_id)
            return None
        except Exception as e:
            logger.error(f"Error updating device credential: {e}")
            return None
    
    async def revoke_device_credential(self, device_id: str) -> bool:
        """撤销设备凭证"""
        try:
            now = datetime.now(timezone.utc)

            with self.db:
                result = self.db.execute(
                    f"UPDATE {self.schema}.{self.devices_table} SET status = 'revoked', updated_at = $1 WHERE device_id = $2",
                    [now, device_id],
                    schema=self.schema
                )

            return result > 0
        except Exception as e:
            logger.error(f"Error revoking device credential: {e}")
            return False
    
    async def list_organization_devices(self, organization_id: str) -> List[Dict[str, Any]]:
        """列出组织的所有设备"""
        try:
            with self.db:
                results = self.db.query(
                    f"""SELECT device_id, device_name, device_type, status,
                              last_authenticated_at, authentication_count, created_at, expires_at
                       FROM {self.schema}.{self.devices_table}
                       WHERE organization_id = $1
                       ORDER BY created_at DESC""",
                    [organization_id],
                    schema=self.schema
                )

            return results if results else []
        except Exception as e:
            logger.error(f"Error listing organization devices: {e}")
            return []
    
    async def get_device_auth_logs(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取设备认证日志"""
        try:
            with self.db:
                results = self.db.query(
                    f"SELECT * FROM {self.schema}.{self.device_logs_table} WHERE device_id = $1 ORDER BY created_at DESC LIMIT $2",
                    [device_id, limit],
                    schema=self.schema
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
        expires_at: 'datetime'
    ) -> Dict[str, Any]:
        """
        Create a new pairing token for a device
        
        Args:
            device_id: Device ID
            pairing_token: Generated pairing token
            expires_at: Token expiration time
            
        Returns:
            Dict with pairing token data
        """
        query = """
            INSERT INTO device_pairing_tokens 
            (device_id, pairing_token, expires_at)
            VALUES ($1, $2, $3)
            RETURNING id, device_id, pairing_token, expires_at, created_at
        """
        
        try:
            row = await self.db.fetchrow(query, device_id, pairing_token, expires_at)
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error creating pairing token: {e}")
            raise

    async def get_pairing_token(self, pairing_token: str) -> Optional[Dict[str, Any]]:
        """
        Get pairing token by token string
        
        Args:
            pairing_token: Pairing token
            
        Returns:
            Dict with pairing token data or None
        """
        query = """
            SELECT id, device_id, pairing_token, expires_at, created_at, used, used_at, user_id
            FROM device_pairing_tokens
            WHERE pairing_token = $1
        """
        
        try:
            row = await self.db.fetchrow(query, pairing_token)
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting pairing token: {e}")
            return None

    async def mark_pairing_token_used(
        self,
        pairing_token: str,
        user_id: str
    ) -> bool:
        """
        Mark pairing token as used
        
        Args:
            pairing_token: Pairing token
            user_id: User ID who used the token
            
        Returns:
            True if successful, False otherwise
        """
        from datetime import datetime, timezone
        
        query = """
            UPDATE device_pairing_tokens
            SET used = TRUE, used_at = $1, user_id = $2
            WHERE pairing_token = $3
        """
        
        try:
            await self.db.execute(query, datetime.now(timezone.utc), user_id, pairing_token)
            return True
        except Exception as e:
            logger.error(f"Error marking pairing token as used: {e}")
            return False

    async def delete_expired_pairing_tokens(self) -> int:
        """
        Delete expired pairing tokens (cleanup job)
        
        Returns:
            Number of deleted tokens
        """
        from datetime import datetime, timezone
        
        query = """
            DELETE FROM device_pairing_tokens
            WHERE expires_at < $1
        """
        
        try:
            result = await self.db.execute(query, datetime.now(timezone.utc))
            # Extract number from result string like "DELETE 5"
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Deleted {count} expired pairing tokens")
            return count
        except Exception as e:
            logger.error(f"Error deleting expired pairing tokens: {e}")
            return 0
