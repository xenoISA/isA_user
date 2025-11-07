"""
Vault Repository

Data access layer for vault service with encrypted storage.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import uuid
import base64
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import ListValue, Struct

from .models import (
    VaultItem, VaultAccessLog, VaultShare,
    SecretType, VaultAction, PermissionLevel,
    VaultItemResponse, VaultShareResponse, VaultAccessLogResponse
)

logger = logging.getLogger(__name__)


class VaultRepository:
    """Repository for vault operations using PostgresClient"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("vault_service")

        # Discover PostgreSQL service
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(host=host, port=port, user_id="vault_service")
        self.schema = "vault"
        self.vault_table = "vault_items"
        self.access_log_table = "vault_access_logs"
        self.share_table = "vault_shares"

    def _convert_protobuf_to_native(self, value: Any) -> Any:
        """Convert Protobuf types to native Python types"""
        if isinstance(value, (ListValue, Struct)):
            return MessageToDict(value)
        return value

    def _parse_vault_item(self, data: Dict[str, Any], include_encrypted: bool = False) -> Dict[str, Any]:
        """Parse vault item data from database"""
        result = {
            "vault_id": data["vault_id"],
            "user_id": data["user_id"],
            "organization_id": data.get("organization_id"),
            "secret_type": data["secret_type"],
            "provider": data.get("provider"),
            "name": data["name"],
            "description": data.get("description"),
            "encryption_method": data["encryption_method"],
            "encryption_key_id": data.get("encryption_key_id"),
            "metadata": self._convert_protobuf_to_native(data.get("metadata", {})),
            "tags": self._convert_protobuf_to_native(data.get("tags", [])),
            "version": data.get("version", 1),
            "expires_at": data.get("expires_at"),
            "last_accessed_at": data.get("last_accessed_at"),
            "access_count": data.get("access_count", 0),
            "is_active": data.get("is_active", True),
            "rotation_enabled": data.get("rotation_enabled", False),
            "rotation_days": data.get("rotation_days"),
            "blockchain_reference": data.get("blockchain_reference"),
            "created_at": data["created_at"],
            "updated_at": data["updated_at"]
        }

        if include_encrypted:
            result["encrypted_value"] = data.get("encrypted_value")

        return result

    # ============ Vault Item Operations ============

    async def create_vault_item(self, vault_item: VaultItem) -> Optional[VaultItemResponse]:
        """Create a new vault item"""
        try:
            vault_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            # Prepare vault data
            encrypted_value_b64 = base64.b64encode(vault_item.encrypted_value).decode() if vault_item.encrypted_value else None

            query = f'''
                INSERT INTO {self.schema}.{self.vault_table} (
                    vault_id, user_id, organization_id, secret_type, provider,
                    name, description, encrypted_value, encryption_method, encryption_key_id,
                    metadata, tags, version, expires_at, access_count, is_active,
                    rotation_enabled, rotation_days, blockchain_reference, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                RETURNING *
            '''

            params = [
                vault_id,
                vault_item.user_id,
                vault_item.organization_id,
                vault_item.secret_type.value,
                vault_item.provider.value if vault_item.provider else None,
                vault_item.name,
                vault_item.description,
                encrypted_value_b64,
                vault_item.encryption_method.value,
                vault_item.encryption_key_id,
                vault_item.metadata,
                vault_item.tags,
                vault_item.version,
                vault_item.expires_at,
                vault_item.access_count,
                vault_item.is_active,
                vault_item.rotation_enabled,
                vault_item.rotation_days,
                vault_item.blockchain_reference,
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                item_data = self._parse_vault_item(results[0], include_encrypted=False)
                return VaultItemResponse(**item_data)

            return None

        except Exception as e:
            logger.error(f"Error creating vault item: {e}", exc_info=True)
            return None

    async def get_vault_item(self, vault_id: str) -> Optional[Dict[str, Any]]:
        """Get vault item by ID (includes encrypted data)"""
        try:
            query = f'SELECT * FROM {self.schema}.{self.vault_table} WHERE vault_id = $1'

            with self.db:
                results = self.db.query(query, [vault_id], schema=self.schema)

            if results and len(results) > 0:
                return self._parse_vault_item(results[0], include_encrypted=True)

            return None

        except Exception as e:
            logger.error(f"Error getting vault item: {e}")
            return None

    async def list_user_vault_items(
        self,
        user_id: str,
        secret_type: Optional[SecretType] = None,
        tags: Optional[List[str]] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[VaultItemResponse]:
        """List vault items for a user"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if active_only:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(True)

            if secret_type:
                param_count += 1
                conditions.append(f"secret_type = ${param_count}")
                params.append(secret_type.value)

            if tags:
                # PostgreSQL array contains check
                for tag in tags:
                    param_count += 1
                    conditions.append(f"${param_count} = ANY(tags)")
                    params.append(tag)

            where_clause = " AND ".join(conditions)

            param_count += 1
            limit_param = f"${param_count}"
            params.append(limit)

            param_count += 1
            offset_param = f"${param_count}"
            params.append(offset)

            query = f'''
                SELECT * FROM {self.schema}.{self.vault_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit_param} OFFSET {offset_param}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                items = []
                for result in results:
                    item_data = self._parse_vault_item(result, include_encrypted=False)
                    items.append(VaultItemResponse(**item_data))
                return items

            return []

        except Exception as e:
            logger.error(f"Error listing vault items: {e}", exc_info=True)
            return []

    async def update_vault_item(self, vault_id: str, update_data: Dict[str, Any]) -> bool:
        """Update vault item"""
        try:
            now = datetime.now(timezone.utc)

            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(now)

            # Add vault_id for WHERE clause
            param_count += 1
            params.append(vault_id)

            set_clause = ", ".join(set_clauses)

            query = f'''
                UPDATE {self.schema}.{self.vault_table}
                SET {set_clause}
                WHERE vault_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating vault item: {e}")
            return False

    async def delete_vault_item(self, vault_id: str) -> bool:
        """Delete vault item (soft delete)"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.vault_table}
                SET is_active = $1, updated_at = $2
                WHERE vault_id = $3
            '''

            with self.db:
                count = self.db.execute(query, [False, now, vault_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting vault item: {e}")
            return False

    async def increment_access_count(self, vault_id: str) -> bool:
        """Increment access count and update last accessed time"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.vault_table}
                SET access_count = access_count + 1,
                    last_accessed_at = $1,
                    updated_at = $2
                WHERE vault_id = $3
            '''

            with self.db:
                count = self.db.execute(query, [now, now, vault_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error incrementing access count: {e}")
            return False

    # ============ Access Log Operations ============

    async def create_access_log(self, log: VaultAccessLog) -> Optional[VaultAccessLogResponse]:
        """Create access log entry"""
        try:
            log_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.access_log_table} (
                    log_id, vault_id, user_id, action, ip_address, user_agent,
                    success, error_message, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
            '''

            params = [
                log_id,
                log.vault_id,
                log.user_id,
                log.action.value,
                log.ip_address,
                log.user_agent,
                log.success,
                log.error_message,
                log.metadata,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                data = results[0]
                return VaultAccessLogResponse(
                    log_id=data["log_id"],
                    vault_id=data["vault_id"],
                    user_id=data["user_id"],
                    action=VaultAction(data["action"]),
                    ip_address=data.get("ip_address"),
                    user_agent=data.get("user_agent"),
                    success=data["success"],
                    error_message=data.get("error_message"),
                    metadata=self._convert_protobuf_to_native(data.get("metadata", {})),
                    created_at=data["created_at"]
                )

            return None

        except Exception as e:
            logger.error(f"Error creating access log: {e}")
            return None

    async def get_access_logs(
        self,
        vault_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[VaultAccessLogResponse]:
        """Get access logs"""
        try:
            conditions = []
            params = []
            param_count = 0

            if vault_id:
                param_count += 1
                conditions.append(f"vault_id = ${param_count}")
                params.append(vault_id)

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            param_count += 1
            limit_param = f"${param_count}"
            params.append(limit)

            param_count += 1
            offset_param = f"${param_count}"
            params.append(offset)

            query = f'''
                SELECT * FROM {self.schema}.{self.access_log_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit_param} OFFSET {offset_param}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                logs = []
                for data in results:
                    logs.append(VaultAccessLogResponse(
                        log_id=data["log_id"],
                        vault_id=data["vault_id"],
                        user_id=data["user_id"],
                        action=VaultAction(data["action"]),
                        ip_address=data.get("ip_address"),
                        user_agent=data.get("user_agent"),
                        success=data["success"],
                        error_message=data.get("error_message"),
                        metadata=self._convert_protobuf_to_native(data.get("metadata", {})),
                        created_at=data["created_at"]
                    ))
                return logs

            return []

        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return []

    # ============ Share Operations ============

    async def create_share(self, share: VaultShare) -> Optional[VaultShareResponse]:
        """Create a share"""
        try:
            share_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.share_table} (
                    share_id, vault_id, owner_user_id, shared_with_user_id,
                    shared_with_org_id, permission_level, expires_at, is_active, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
            '''

            params = [
                share_id,
                share.vault_id,
                share.owner_user_id,
                share.shared_with_user_id,
                share.shared_with_org_id,
                share.permission_level.value,
                share.expires_at,
                share.is_active,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                data = results[0]
                return VaultShareResponse(
                    share_id=data["share_id"],
                    vault_id=data["vault_id"],
                    owner_user_id=data["owner_user_id"],
                    shared_with_user_id=data.get("shared_with_user_id"),
                    shared_with_org_id=data.get("shared_with_org_id"),
                    permission_level=PermissionLevel(data["permission_level"]),
                    expires_at=data.get("expires_at"),
                    is_active=data["is_active"],
                    created_at=data["created_at"]
                )

            return None

        except Exception as e:
            logger.error(f"Error creating share: {e}")
            return None

    async def get_shares_for_vault(self, vault_id: str) -> List[VaultShareResponse]:
        """Get all shares for a vault item"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.share_table}
                WHERE vault_id = $1 AND is_active = $2
            '''

            with self.db:
                results = self.db.query(query, [vault_id, True], schema=self.schema)

            if results and len(results) > 0:
                shares = []
                for data in results:
                    shares.append(VaultShareResponse(
                        share_id=data["share_id"],
                        vault_id=data["vault_id"],
                        owner_user_id=data["owner_user_id"],
                        shared_with_user_id=data.get("shared_with_user_id"),
                        shared_with_org_id=data.get("shared_with_org_id"),
                        permission_level=PermissionLevel(data["permission_level"]),
                        expires_at=data.get("expires_at"),
                        is_active=data["is_active"],
                        created_at=data["created_at"]
                    ))
                return shares

            return []

        except Exception as e:
            logger.error(f"Error getting shares: {e}")
            return []

    async def get_shares_for_user(self, user_id: str) -> List[VaultShareResponse]:
        """Get all secrets shared with a user"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.share_table}
                WHERE shared_with_user_id = $1 AND is_active = $2
            '''

            with self.db:
                results = self.db.query(query, [user_id, True], schema=self.schema)

            if results and len(results) > 0:
                shares = []
                for data in results:
                    shares.append(VaultShareResponse(
                        share_id=data["share_id"],
                        vault_id=data["vault_id"],
                        owner_user_id=data["owner_user_id"],
                        shared_with_user_id=data.get("shared_with_user_id"),
                        shared_with_org_id=data.get("shared_with_org_id"),
                        permission_level=PermissionLevel(data["permission_level"]),
                        expires_at=data.get("expires_at"),
                        is_active=data["is_active"],
                        created_at=data["created_at"]
                    ))
                return shares

            return []

        except Exception as e:
            logger.error(f"Error getting user shares: {e}")
            return []

    async def revoke_share(self, share_id: str) -> bool:
        """Revoke a share"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.share_table}
                SET is_active = $1
                WHERE share_id = $2
            '''

            with self.db:
                count = self.db.execute(query, [False, share_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error revoking share: {e}")
            return False

    async def check_user_access(self, vault_id: str, user_id: str) -> Optional[str]:
        """
        Check if user has access to a vault item

        Returns:
            Permission level if user has access, None otherwise
        """
        try:
            # Check if user owns the item
            item = await self.get_vault_item(vault_id)
            if item and item.get('user_id') == user_id:
                return 'owner'

            # Check if item is shared with user
            shares = await self.get_shares_for_vault(vault_id)
            now = datetime.now(timezone.utc)
            for share in shares:
                if share.shared_with_user_id == user_id:
                    # Check if share is expired
                    if share.expires_at and share.expires_at < now:
                        continue
                    return share.permission_level.value

            return None

        except Exception as e:
            logger.error(f"Error checking user access: {e}")
            return None

    # ============ Statistics ============

    async def get_vault_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get vault statistics"""
        try:
            where_clause = f"WHERE user_id = $1" if user_id else ""
            params = [user_id] if user_id else []

            query = f'''
                SELECT * FROM {self.schema}.{self.vault_table}
                {where_clause}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if not results or len(results) == 0:
                return {
                    "total_secrets": 0,
                    "active_secrets": 0,
                    "expired_secrets": 0,
                    "secrets_by_type": {},
                    "secrets_by_provider": {},
                    "total_access_count": 0,
                    "blockchain_verified_secrets": 0
                }

            now = datetime.now(timezone.utc)

            stats = {
                "total_secrets": len(results),
                "active_secrets": 0,
                "expired_secrets": 0,
                "secrets_by_type": {},
                "secrets_by_provider": {},
                "total_access_count": 0,
                "blockchain_verified_secrets": 0
            }

            for item in results:
                if item.get('is_active'):
                    stats['active_secrets'] += 1

                if item.get('expires_at') and item['expires_at'] < now:
                    stats['expired_secrets'] += 1

                secret_type = item.get('secret_type', 'unknown')
                stats['secrets_by_type'][secret_type] = stats['secrets_by_type'].get(secret_type, 0) + 1

                provider = item.get('provider')
                if provider:
                    stats['secrets_by_provider'][provider] = stats['secrets_by_provider'].get(provider, 0) + 1

                stats['total_access_count'] += item.get('access_count', 0)

                if item.get('blockchain_reference'):
                    stats['blockchain_verified_secrets'] += 1

            # Get shared secrets count
            if user_id:
                share_query = f'''
                    SELECT COUNT(*) as count FROM {self.schema}.{self.share_table}
                    WHERE owner_user_id = $1 AND is_active = $2
                '''

                with self.db:
                    share_results = self.db.query(share_query, [user_id, True], schema=self.schema)

                if share_results and len(share_results) > 0:
                    stats['shared_secrets'] = share_results[0].get('count', 0)

            return stats

        except Exception as e:
            logger.error(f"Error getting vault stats: {e}")
            return {}

    async def get_expiring_secrets(self, user_id: str, days: int = 7) -> List[VaultItemResponse]:
        """Get secrets expiring in the next N days"""
        try:
            now = datetime.now(timezone.utc)
            future_date = now + timedelta(days=days)

            query = f'''
                SELECT * FROM {self.schema}.{self.vault_table}
                WHERE user_id = $1
                  AND is_active = $2
                  AND expires_at IS NOT NULL
                  AND expires_at >= $3
                  AND expires_at < $4
                ORDER BY expires_at ASC
            '''

            with self.db:
                results = self.db.query(query, [user_id, True, now, future_date], schema=self.schema)

            if results and len(results) > 0:
                items = []
                for result in results:
                    item_data = self._parse_vault_item(result, include_encrypted=False)
                    items.append(VaultItemResponse(**item_data))
                return items

            return []

        except Exception as e:
            logger.error(f"Error getting expiring secrets: {e}", exc_info=True)
            return []

    # ====================
    # GDPR 数据管理
    # ====================

    async def delete_user_data(self, user_id: str) -> int:
        """删除用户所有 vault 数据（GDPR Article 17: Right to Erasure）"""
        try:
            # Delete vault items
            items_query = f'DELETE FROM {self.schema}.{self.vault_table} WHERE user_id = $1'

            with self.db:
                items_count = self.db.execute(items_query, [user_id], schema=self.schema)

            # Delete shares where user is the owner
            shares_query = f'DELETE FROM {self.schema}.{self.share_table} WHERE shared_by = $1'

            with self.db:
                shares_count = self.db.execute(shares_query, [user_id], schema=self.schema)

            # Delete shares where user is the recipient
            shares_to_query = f'DELETE FROM {self.schema}.{self.share_table} WHERE shared_with = $1'

            with self.db:
                shares_to_count = self.db.execute(shares_to_query, [user_id], schema=self.schema)

            # Delete access logs
            logs_query = f'DELETE FROM {self.schema}.{self.access_log_table} WHERE user_id = $1'

            with self.db:
                logs_count = self.db.execute(logs_query, [user_id], schema=self.schema)

            total_deleted = (
                (items_count if items_count is not None else 0) +
                (shares_count if shares_count is not None else 0) +
                (shares_to_count if shares_to_count is not None else 0) +
                (logs_count if logs_count is not None else 0)
            )

            logger.info(
                f"Deleted user {user_id} vault data: "
                f"{items_count} items, {shares_count + shares_to_count} shares, {logs_count} logs"
            )
            return total_deleted

        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}")
            raise
