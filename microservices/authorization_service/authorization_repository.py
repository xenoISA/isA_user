"""
Authorization Repository - Async Version

Data access layer for the authorization microservice using AsyncPostgresClient.
Uses service clients for cross-service communication.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from google.protobuf.json_format import MessageToDict
from core.config_manager import ConfigManager
from .models import (
    ResourcePermission, UserPermissionRecord, OrganizationPermission,
    ResourceType, AccessLevel, PermissionSource, SubscriptionTier,
    UserPermissionSummary, ResourceAccessSummary, OrganizationPermissionSummary,
    PermissionAuditLog, ExternalServiceUser, ExternalServiceOrganization
)

# Import service clients for cross-service communication
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from microservices.account_service.client import AccountServiceClient
from microservices.organization_service.client import OrganizationServiceClient

logger = logging.getLogger(__name__)


class AuthorizationRepository:
    """Repository for authorization data operations - async version"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("authorization_service")

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
            user_id='authorization_service'
        )
        self.schema = "authz"
        self.table_name = "permissions"

        # Initialize service clients for cross-service communication
        self.account_client = AccountServiceClient()
        self.org_client = OrganizationServiceClient()

    def _convert_proto_jsonb(self, jsonb_raw):
        """Convert proto JSONB to Python dict"""
        if hasattr(jsonb_raw, 'fields'):
            return MessageToDict(jsonb_raw)
        return jsonb_raw if jsonb_raw else {}

    # ====================
    # Connection Management
    # ====================

    async def check_connection(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1 as connected", params=[])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    # ====================
    # Resource Permission Management
    # ====================

    async def create_resource_permission(self, permission: ResourcePermission) -> Optional[ResourcePermission]:
        """Create a new resource permission configuration"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                INSERT INTO {self.schema}.{self.table_name}
                (permission_type, target_type, target_id, resource_type, resource_name,
                 resource_category, access_level, permission_source, subscription_tier_required,
                 description, is_active, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """
            params = [
                "resource_config",
                "global",
                None,
                permission.resource_type.value,
                permission.resource_name,
                permission.resource_category,
                permission.access_level.value,
                "system_default",
                permission.subscription_tier_required.value,
                permission.description,
                permission.is_enabled,
                {},
                now,
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count is not None and count > 0:
                return await self.get_resource_permission(permission.resource_type, permission.resource_name)

            return None

        except Exception as e:
            logger.error(f"Failed to create resource permission: {e}")
            return None

    async def get_resource_permission(self, resource_type: ResourceType, resource_name: str) -> Optional[ResourcePermission]:
        """Get resource permission configuration"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE permission_type = $1
                AND resource_type = $2
                AND resource_name = $3
                AND is_active = TRUE
            """
            async with self.db:
                result = await self.db.query_row(query, params=["resource_config", resource_type.value, resource_name])

            if result:
                data = {
                    "id": str(result.get("id")) if result.get("id") else None,
                    "resource_type": result.get("resource_type"),
                    "resource_name": result.get("resource_name"),
                    "resource_category": result.get("resource_category"),
                    "subscription_tier_required": result.get("subscription_tier_required"),
                    "access_level": result.get("access_level"),
                    "is_enabled": result.get("is_active"),
                    "description": result.get("description"),
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                }
                return ResourcePermission(**data)
            return None

        except Exception as e:
            logger.error(f"Error getting resource permission {resource_type}:{resource_name}: {e}")
            return None

    async def list_resource_permissions(self, resource_type: Optional[ResourceType] = None) -> List[ResourcePermission]:
        """List resource permission configurations"""
        try:
            conditions = ["permission_type = $1", "is_active = TRUE"]
            params = ["resource_config"]

            if resource_type:
                conditions.append("resource_type = $2")
                params.append(resource_type.value)

            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {self.schema}.{self.table_name} WHERE {where_clause}"

            async with self.db:
                results = await self.db.query(query, params=params)

            if results:
                permissions = []
                for item in results:
                    mapped_data = {
                        "id": str(item.get("id")) if item.get("id") else None,
                        "resource_type": item.get("resource_type"),
                        "resource_name": item.get("resource_name"),
                        "resource_category": item.get("resource_category"),
                        "subscription_tier_required": item.get("subscription_tier_required"),
                        "access_level": item.get("access_level"),
                        "is_enabled": item.get("is_active"),
                        "description": item.get("description"),
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at")
                    }
                    permissions.append(ResourcePermission(**mapped_data))
                return permissions
            return []

        except Exception as e:
            logger.error(f"Failed to list resource permissions: {e}")
            return []

    async def update_resource_permission(self, permission: ResourcePermission) -> Optional[ResourcePermission]:
        """Update resource permission configuration"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.schema}.{self.table_name}
                SET resource_category = $1, description = $2, subscription_tier_required = $3,
                    access_level = $4, is_active = $5, updated_at = $6
                WHERE permission_type = $7 AND resource_type = $8 AND resource_name = $9
            """
            params = [
                permission.resource_category,
                permission.description,
                permission.subscription_tier_required.value,
                permission.access_level.value,
                permission.is_enabled,
                now,
                "resource_config",
                permission.resource_type.value,
                permission.resource_name
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count and count > 0:
                return await self.get_resource_permission(permission.resource_type, permission.resource_name)
            return None

        except Exception as e:
            logger.error(f"Failed to update resource permission: {e}")
            return None

    # ====================
    # User Permission Management
    # ====================

    async def grant_user_permission(self, permission: UserPermissionRecord) -> Optional[UserPermissionRecord]:
        """Grant permission to a user"""
        try:
            now = datetime.now(timezone.utc)
            metadata = {"granted_by": permission.granted_by_user_id}

            query = f"""
                INSERT INTO {self.schema}.{self.table_name}
                (permission_type, target_type, target_id, resource_type, resource_name,
                 access_level, permission_source, is_active, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """
            params = [
                "user_permission",
                "user",
                permission.user_id,
                permission.resource_type.value,
                permission.resource_name,
                permission.access_level.value,
                permission.permission_source.value,
                permission.is_active,
                metadata,
                now,
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count is not None and count > 0:
                return await self.get_user_permission(permission.user_id, permission.resource_type, permission.resource_name)

            return None

        except Exception as e:
            logger.error(f"Failed to grant user permission: {e}")
            return None

    async def get_user_permission(self, user_id: str, resource_type: ResourceType, resource_name: str) -> Optional[UserPermissionRecord]:
        """Get user permission for specific resource"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE permission_type = $1 AND target_id = $2
                AND resource_type = $3 AND resource_name = $4 AND is_active = TRUE
            """
            async with self.db:
                result = await self.db.query_row(
                    query,
                    params=["user_permission", user_id, resource_type.value, resource_name]
                )

            if result:
                metadata = self._convert_proto_jsonb(result.get('metadata', {}))
                record_data = {
                    "id": str(result.get("id")),
                    "user_id": result.get("target_id"),
                    "resource_type": result.get("resource_type"),
                    "resource_name": result.get("resource_name"),
                    "access_level": result.get("access_level"),
                    "permission_source": result.get("permission_source"),
                    "granted_by_user_id": metadata.get("granted_by"),
                    "organization_id": None,
                    "expires_at": None,
                    "is_active": result.get("is_active"),
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                }
                return UserPermissionRecord(**record_data)
            return None

        except Exception as e:
            logger.debug(f"User permission not found: {user_id} - {resource_type}:{resource_name}")
            return None

    async def list_user_permissions(self, user_id: str, resource_type: Optional[ResourceType] = None) -> List[UserPermissionRecord]:
        """List all permissions for a user"""
        try:
            conditions = ["permission_type = $1", "target_id = $2", "is_active = TRUE"]
            params = ["user_permission", user_id]
            param_count = 2

            if resource_type:
                param_count += 1
                conditions.append(f"resource_type = ${param_count}")
                params.append(resource_type.value)

            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {self.schema}.{self.table_name} WHERE {where_clause}"

            async with self.db:
                results = await self.db.query(query, params=params)

            if results:
                permissions = []
                for item in results:
                    metadata = self._convert_proto_jsonb(item.get('metadata', {}))
                    record_data = {
                        "id": str(item.get("id")) if item.get("id") else None,
                        "user_id": item.get("target_id"),
                        "resource_type": item.get("resource_type"),
                        "resource_name": item.get("resource_name"),
                        "access_level": item.get("access_level"),
                        "permission_source": item.get("permission_source"),
                        "granted_by_user_id": metadata.get("granted_by"),
                        "organization_id": None,
                        "expires_at": item.get("expires_at"),
                        "is_active": item.get("is_active"),
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at")
                    }
                    permissions.append(UserPermissionRecord(**record_data))
                return permissions
            return []

        except Exception as e:
            logger.error(f"Failed to list user permissions: {e}")
            return []

    async def revoke_user_permission(self, user_id: str, resource_type: ResourceType, resource_name: str) -> bool:
        """Revoke user permission"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.schema}.{self.table_name}
                SET is_active = FALSE, updated_at = $1
                WHERE permission_type = $2 AND target_id = $3
                AND resource_type = $4 AND resource_name = $5
            """
            params = [now, "user_permission", user_id, resource_type.value, resource_name]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to revoke user permission: {e}")
            return False

    # ====================
    # Organization Permission Management
    # ====================

    async def create_organization_permission(self, permission: OrganizationPermission) -> Optional[OrganizationPermission]:
        """Create organization permission configuration"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                INSERT INTO {self.schema}.{self.table_name}
                (permission_type, target_type, target_id, resource_type, resource_name,
                 access_level, permission_source, subscription_tier_required, is_active,
                 created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """
            params = [
                "org_permission",
                "organization",
                permission.organization_id,
                permission.resource_type.value,
                permission.resource_name,
                permission.access_level.value,
                "organization_admin",
                permission.org_plan_required,
                permission.is_enabled,
                now,
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count and count > 0:
                return await self.get_organization_permission(
                    permission.organization_id, permission.resource_type, permission.resource_name
                )
            return None

        except Exception as e:
            logger.error(f"Failed to create organization permission: {e}")
            return None

    async def get_organization_permission(self, organization_id: str, resource_type: ResourceType, resource_name: str) -> Optional[OrganizationPermission]:
        """Get organization permission configuration"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE permission_type = $1 AND target_id = $2
                AND resource_type = $3 AND resource_name = $4 AND is_active = TRUE
            """
            async with self.db:
                result = await self.db.query_row(
                    query,
                    params=["org_permission", organization_id, resource_type.value, resource_name]
                )

            if result:
                return OrganizationPermission(
                    organization_id=result.get("target_id"),
                    resource_type=ResourceType(result.get("resource_type")),
                    resource_name=result.get("resource_name"),
                    access_level=AccessLevel(result.get("access_level")),
                    org_plan_required=result.get("subscription_tier_required"),
                    is_enabled=result.get("is_active"),
                    created_at=result.get("created_at"),
                    updated_at=result.get("updated_at")
                )
            return None

        except Exception as e:
            logger.debug(f"Organization permission not found: {organization_id} - {resource_type}:{resource_name}")
            return None

    async def list_organization_permissions(self, organization_id: str) -> List[OrganizationPermission]:
        """List all permissions for an organization"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE permission_type = $1 AND target_id = $2 AND is_active = TRUE
            """
            async with self.db:
                results = await self.db.query(query, params=["org_permission", organization_id])

            if results:
                return [
                    OrganizationPermission(
                        organization_id=item.get("target_id"),
                        resource_type=ResourceType(item.get("resource_type")),
                        resource_name=item.get("resource_name"),
                        access_level=AccessLevel(item.get("access_level")),
                        org_plan_required=item.get("subscription_tier_required"),
                        is_enabled=item.get("is_active"),
                        created_at=item.get("created_at"),
                        updated_at=item.get("updated_at")
                    )
                    for item in results
                ]
            return []

        except Exception as e:
            logger.error(f"Failed to list organization permissions: {e}")
            return []

    # ====================
    # External Service Integration
    # ====================

    async def get_user_info(self, user_id: str) -> Optional[ExternalServiceUser]:
        """Get user information from account service via HTTP client"""
        try:
            account_profile = await self.account_client.get_account_profile(user_id)

            if not account_profile:
                logger.debug(f"User not found via account service: {user_id}")
                return None

            user_orgs = await self.org_client.get_user_organizations(user_id)
            organization_id = None
            if user_orgs and len(user_orgs) > 0:
                organization_id = user_orgs[0].get("organization_id")

            return ExternalServiceUser(
                user_id=account_profile.get("user_id"),
                email=account_profile.get("email"),
                subscription_status=account_profile.get("subscription_plan", "free"),
                is_active=account_profile.get("is_active", True),
                organization_id=organization_id
            )

        except Exception as e:
            logger.error(f"Failed to get user info via service client: {e}")
            return None

    async def get_organization_info(self, organization_id: str) -> Optional[ExternalServiceOrganization]:
        """Get organization information from organization service via HTTP client"""
        try:
            org_data = await self.org_client.get_organization(
                organization_id=organization_id,
                user_id="system"
            )

            if not org_data:
                logger.debug(f"Organization not found via service: {organization_id}")
                return None

            members = await self.org_client.get_members(
                organization_id=organization_id,
                user_id="system"
            )
            member_count = len(members) if members else 0

            return ExternalServiceOrganization(
                organization_id=org_data.get("organization_id"),
                plan=org_data.get("plan", "free"),
                is_active=org_data.get("is_active", True),
                member_count=member_count
            )

        except Exception as e:
            logger.error(f"Failed to get organization info via service client: {e}")
            return None

    async def is_user_organization_member(self, user_id: str, organization_id: str) -> bool:
        """Check if user is a member of organization via service client"""
        try:
            members = await self.org_client.get_members(
                organization_id=organization_id,
                user_id="system"
            )

            if not members:
                return False

            for member in members:
                if member.get("user_id") == user_id and member.get("status") == "active":
                    return True

            return False

        except Exception as e:
            logger.debug(f"User is not organization member: {user_id} - {organization_id}, error: {e}")
            return False

    # ====================
    # Analytics and Summary
    # ====================

    async def get_user_permission_summary(self, user_id: str) -> Optional[UserPermissionSummary]:
        """Get comprehensive permission summary for user"""
        try:
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return None

            org_info = None
            if user_info.organization_id:
                org_info = await self.get_organization_info(user_info.organization_id)

            permissions = await self.list_user_permissions(user_id)

            permissions_by_type = {}
            permissions_by_source = {}
            permissions_by_level = {}
            expires_soon_count = 0

            soon_threshold = datetime.now(timezone.utc) + timedelta(days=7)

            for perm in permissions:
                permissions_by_type[perm.resource_type] = permissions_by_type.get(perm.resource_type, 0) + 1
                permissions_by_source[perm.permission_source] = permissions_by_source.get(perm.permission_source, 0) + 1
                permissions_by_level[perm.access_level] = permissions_by_level.get(perm.access_level, 0) + 1

                if perm.expires_at and perm.expires_at <= soon_threshold:
                    expires_soon_count += 1

            return UserPermissionSummary(
                user_id=user_id,
                subscription_tier=user_info.subscription_status,
                organization_id=user_info.organization_id,
                organization_plan=org_info.plan if org_info else None,
                total_permissions=len(permissions),
                permissions_by_type=permissions_by_type,
                permissions_by_source=permissions_by_source,
                permissions_by_level=permissions_by_level,
                expires_soon_count=expires_soon_count
            )

        except Exception as e:
            logger.error(f"Failed to get user permission summary: {e}")
            return None

    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service-wide statistics"""
        try:
            async with self.db:
                # Count total user permissions
                perm_result = await self.db.query_row(
                    f"SELECT COUNT(*) as count FROM {self.schema}.{self.table_name} WHERE permission_type = $1 AND is_active = TRUE",
                    params=["user_permission"]
                )
                total_permissions = perm_result.get("count", 0) if perm_result else 0

                # Count unique users
                user_result = await self.db.query(
                    f"SELECT DISTINCT target_id FROM {self.schema}.{self.table_name} WHERE permission_type = $1 AND is_active = TRUE",
                    params=["user_permission"]
                )
                unique_users = len(user_result) if user_result else 0

                # Count resource types
                resource_result = await self.db.query(
                    f"SELECT DISTINCT resource_type FROM {self.schema}.{self.table_name} WHERE permission_type = $1 AND is_active = TRUE",
                    params=["resource_config"]
                )
                unique_resources = len(resource_result) if resource_result else 0

            return {
                "total_permissions": total_permissions,
                "active_users": unique_users,
                "resource_types": unique_resources
            }

        except Exception as e:
            logger.error(f"Failed to get service statistics: {e}")
            return {
                "total_permissions": 0,
                "active_users": 0,
                "resource_types": 0
            }

    # ====================
    # Cleanup Operations
    # ====================

    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                DELETE FROM {self.schema}.{self.table_name}
                WHERE permission_type = $1 AND expires_at < $2
            """
            async with self.db:
                count = await self.db.execute(query, params=["user_permission", now])

            cleaned_count = count if count else 0
            logger.info(f"Cleaned up {cleaned_count} expired permissions")
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired permissions: {e}")
            return 0

    async def cleanup(self):
        """Cleanup resources (close service clients)"""
        try:
            await self.account_client.close()
            await self.org_client.close()
            logger.info("Service clients closed successfully")
        except Exception as e:
            logger.error(f"Error closing service clients: {e}")

    # ====================
    # Audit Logging
    # ====================

    async def log_permission_action(self, audit_log: PermissionAuditLog) -> bool:
        """Log permission action for audit trail"""
        try:
            query = f"""
                INSERT INTO {self.schema}.{self.table_name}
                (permission_type, target_type, target_id, resource_type, resource_name,
                 access_level, permission_source, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            params = [
                "audit_log",
                "system",
                audit_log.user_id,
                audit_log.resource_type.value,
                audit_log.resource_name,
                audit_log.new_access_level.value if audit_log.new_access_level else None,
                "audit_system",
                audit_log.success,
                audit_log.timestamp,
                audit_log.timestamp
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to log permission action: {e}")
            return False
