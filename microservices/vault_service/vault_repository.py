"""
Vault Repository

Data access layer for vault service with encrypted storage.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import base64

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    VaultItem, VaultAccessLog, VaultShare,
    SecretType, VaultAction, PermissionLevel,
    VaultItemResponse, VaultShareResponse, VaultAccessLogResponse
)

logger = logging.getLogger(__name__)


class VaultRepository:
    """Repository for vault operations"""

    def __init__(self):
        self.client = get_supabase_client()
        self.vault_table = "vault_items"
        self.access_log_table = "vault_access_logs"
        self.share_table = "vault_shares"

    # ============ Vault Item Operations ============

    async def create_vault_item(self, vault_item: VaultItem) -> Optional[VaultItemResponse]:
        """Create a new vault item"""
        try:
            vault_id = str(uuid.uuid4())

            # Prepare vault data
            # Note: encrypted_value is stored as base64 string in the database
            encrypted_value_b64 = base64.b64encode(vault_item.encrypted_value).decode() if vault_item.encrypted_value else None

            vault_dict = {
                'vault_id': vault_id,
                'user_id': vault_item.user_id,
                'organization_id': vault_item.organization_id,
                'secret_type': vault_item.secret_type.value,
                'provider': vault_item.provider.value if vault_item.provider else None,
                'name': vault_item.name,
                'description': vault_item.description,
                'encrypted_value': encrypted_value_b64,
                'encryption_method': vault_item.encryption_method.value,
                'encryption_key_id': vault_item.encryption_key_id,
                'metadata': vault_item.metadata,
                'tags': vault_item.tags,
                'version': vault_item.version,
                'expires_at': vault_item.expires_at.isoformat() if vault_item.expires_at else None,
                'access_count': vault_item.access_count,
                'is_active': vault_item.is_active,
                'rotation_enabled': vault_item.rotation_enabled,
                'rotation_days': vault_item.rotation_days,
                'blockchain_reference': vault_item.blockchain_reference
            }

            result = self.client.table(self.vault_table).insert(vault_dict).execute()

            if not result.data:
                logger.error("Failed to create vault item")
                return None

            return VaultItemResponse(**result.data[0])

        except Exception as e:
            logger.error(f"Error creating vault item: {e}")
            return None

    async def get_vault_item(self, vault_id: str) -> Optional[Dict[str, Any]]:
        """Get vault item by ID (includes encrypted data)"""
        try:
            result = self.client.table(self.vault_table).select('*').eq('vault_id', vault_id).execute()

            if not result.data or len(result.data) == 0:
                return None

            return result.data[0]

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
            query = self.client.table(self.vault_table).select('*').eq('user_id', user_id)

            if active_only:
                query = query.eq('is_active', True)

            if secret_type:
                query = query.eq('secret_type', secret_type.value)

            if tags:
                # Filter by tags (array contains)
                for tag in tags:
                    query = query.contains('tags', [tag])

            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)

            result = query.execute()

            if not result.data:
                return []

            return [VaultItemResponse(**item) for item in result.data]

        except Exception as e:
            logger.error(f"Error listing vault items: {e}")
            return []

    async def update_vault_item(self, vault_id: str, update_data: Dict[str, Any]) -> bool:
        """Update vault item"""
        try:
            update_data['updated_at'] = datetime.utcnow().isoformat()

            result = self.client.table(self.vault_table).update(update_data).eq('vault_id', vault_id).execute()

            return result.data is not None and len(result.data) > 0

        except Exception as e:
            logger.error(f"Error updating vault item: {e}")
            return False

    async def delete_vault_item(self, vault_id: str) -> bool:
        """Delete vault item (soft delete)"""
        try:
            result = self.client.table(self.vault_table).update({
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('vault_id', vault_id).execute()

            return result.data is not None and len(result.data) > 0

        except Exception as e:
            logger.error(f"Error deleting vault item: {e}")
            return False

    async def increment_access_count(self, vault_id: str) -> bool:
        """Increment access count and update last accessed time"""
        try:
            # Get current access count
            item = await self.get_vault_item(vault_id)
            if not item:
                return False

            new_count = item.get('access_count', 0) + 1

            return await self.update_vault_item(vault_id, {
                'access_count': new_count,
                'last_accessed_at': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error incrementing access count: {e}")
            return False

    # ============ Access Log Operations ============

    async def create_access_log(self, log: VaultAccessLog) -> Optional[VaultAccessLogResponse]:
        """Create access log entry"""
        try:
            log_id = str(uuid.uuid4())

            log_dict = {
                'log_id': log_id,
                'vault_id': log.vault_id,
                'user_id': log.user_id,
                'action': log.action.value,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'success': log.success,
                'error_message': log.error_message,
                'metadata': log.metadata
            }

            result = self.client.table(self.access_log_table).insert(log_dict).execute()

            if not result.data:
                return None

            return VaultAccessLogResponse(**result.data[0])

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
            query = self.client.table(self.access_log_table).select('*')

            if vault_id:
                query = query.eq('vault_id', vault_id)

            if user_id:
                query = query.eq('user_id', user_id)

            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)

            result = query.execute()

            if not result.data:
                return []

            return [VaultAccessLogResponse(**log) for log in result.data]

        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return []

    # ============ Share Operations ============

    async def create_share(self, share: VaultShare) -> Optional[VaultShareResponse]:
        """Create a share"""
        try:
            share_id = str(uuid.uuid4())

            share_dict = {
                'share_id': share_id,
                'vault_id': share.vault_id,
                'owner_user_id': share.owner_user_id,
                'shared_with_user_id': share.shared_with_user_id,
                'shared_with_org_id': share.shared_with_org_id,
                'permission_level': share.permission_level.value,
                'expires_at': share.expires_at.isoformat() if share.expires_at else None,
                'is_active': share.is_active
            }

            result = self.client.table(self.share_table).insert(share_dict).execute()

            if not result.data:
                return None

            return VaultShareResponse(**result.data[0])

        except Exception as e:
            logger.error(f"Error creating share: {e}")
            return None

    async def get_shares_for_vault(self, vault_id: str) -> List[VaultShareResponse]:
        """Get all shares for a vault item"""
        try:
            result = self.client.table(self.share_table).select('*').eq('vault_id', vault_id).eq('is_active', True).execute()

            if not result.data:
                return []

            return [VaultShareResponse(**share) for share in result.data]

        except Exception as e:
            logger.error(f"Error getting shares: {e}")
            return []

    async def get_shares_for_user(self, user_id: str) -> List[VaultShareResponse]:
        """Get all secrets shared with a user"""
        try:
            result = self.client.table(self.share_table).select('*').eq('shared_with_user_id', user_id).eq('is_active', True).execute()

            if not result.data:
                return []

            return [VaultShareResponse(**share) for share in result.data]

        except Exception as e:
            logger.error(f"Error getting user shares: {e}")
            return []

    async def revoke_share(self, share_id: str) -> bool:
        """Revoke a share"""
        try:
            result = self.client.table(self.share_table).update({
                'is_active': False
            }).eq('share_id', share_id).execute()

            return result.data is not None and len(result.data) > 0

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
            for share in shares:
                if share.shared_with_user_id == user_id:
                    # Check if share is expired
                    if share.expires_at and share.expires_at < datetime.utcnow():
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
            query = self.client.table(self.vault_table).select('*')

            if user_id:
                query = query.eq('user_id', user_id)

            result = query.execute()

            if not result.data:
                return {
                    "total_secrets": 0,
                    "active_secrets": 0,
                    "expired_secrets": 0,
                    "secrets_by_type": {},
                    "secrets_by_provider": {},
                    "total_access_count": 0,
                    "blockchain_verified_secrets": 0
                }

            items = result.data
            now = datetime.utcnow()

            stats = {
                "total_secrets": len(items),
                "active_secrets": sum(1 for item in items if item.get('is_active')),
                "expired_secrets": sum(1 for item in items if item.get('expires_at') and datetime.fromisoformat(item['expires_at']) < now),
                "secrets_by_type": {},
                "secrets_by_provider": {},
                "total_access_count": sum(item.get('access_count', 0) for item in items),
                "blockchain_verified_secrets": sum(1 for item in items if item.get('blockchain_reference'))
            }

            # Count by type
            for item in items:
                secret_type = item.get('secret_type', 'unknown')
                stats['secrets_by_type'][secret_type] = stats['secrets_by_type'].get(secret_type, 0) + 1

            # Count by provider
            for item in items:
                provider = item.get('provider', 'unknown')
                if provider:
                    stats['secrets_by_provider'][provider] = stats['secrets_by_provider'].get(provider, 0) + 1

            # Get shared secrets count
            if user_id:
                shares_query = self.client.table(self.share_table).select('vault_id', count='exact').eq('owner_user_id', user_id).eq('is_active', True)
                shares_result = shares_query.execute()
                stats['shared_secrets'] = len(shares_result.data) if shares_result.data else 0

            return stats

        except Exception as e:
            logger.error(f"Error getting vault stats: {e}")
            return {}

    async def get_expiring_secrets(self, user_id: str, days: int = 7) -> List[VaultItemResponse]:
        """Get secrets expiring in the next N days"""
        try:
            future_date = datetime.utcnow() + timedelta(days=days)

            result = self.client.table(self.vault_table).select('*').eq('user_id', user_id).eq('is_active', True).lt('expires_at', future_date.isoformat()).gte('expires_at', datetime.utcnow().isoformat()).execute()

            if not result.data:
                return []

            return [VaultItemResponse(**item) for item in result.data]

        except Exception as e:
            logger.error(f"Error getting expiring secrets: {e}")
            return []
