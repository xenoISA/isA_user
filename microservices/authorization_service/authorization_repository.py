"""
Authorization Repository

Data access layer for the authorization microservice.
Migrated to use PostgresClient with gRPC.
Uses service clients instead of direct cross-schema database queries.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import json

# Database client setup
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from google.protobuf.json_format import MessageToDict
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
    """Repository for authorization data operations"""

    def __init__(self):
        self.db = PostgresClient(
            host='isa-postgres-grpc',
            port=50061,
            user_id='authorization_service'
        )
        self.schema = "authz"
        self.table_name = "permissions"  # Use unified permissions table

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
            with self.db:
                result = self.db.health_check()
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
            data = {
                "permission_type": "resource_config",
                "target_type": "global",
                "target_id": None,
                "resource_type": permission.resource_type.value,
                "resource_name": permission.resource_name,
                "resource_category": permission.resource_category,
                "access_level": permission.access_level.value,
                "permission_source": "system_default",
                "subscription_tier_required": permission.subscription_tier_required.value,
                "description": permission.description,
                "is_active": permission.is_enabled,
                "metadata": {}
            }

            with self.db:
                count = self.db.insert_into(self.table_name, [data], schema=self.schema)

            if count is not None and count > 0:
                # Query back the created permission
                return await self.get_resource_permission(permission.resource_type, permission.resource_name)

            return None

        except Exception as e:
            logger.error(f"Failed to create resource permission: {e}")
            return None
    
    async def get_resource_permission(self, resource_type: ResourceType, resource_name: str) -> Optional[ResourcePermission]:
        """Get resource permission configuration"""
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("permission_type", "resource_config")\
                .eq("resource_type", resource_type.value)\
                .eq("resource_name", resource_name)\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            if result.data:
                # Map unified table fields back to ResourcePermission model
                data = {
                    "id": str(result.data.get("id")) if result.data.get("id") else None,
                    "resource_type": result.data.get("resource_type"),
                    "resource_name": result.data.get("resource_name"),
                    "resource_category": result.data.get("resource_category"),
                    "subscription_tier_required": result.data.get("subscription_tier_required"),
                    "access_level": result.data.get("access_level"),
                    "is_enabled": result.data.get("is_active"),
                    "description": result.data.get("description"),
                    "created_at": result.data.get("created_at"),
                    "updated_at": result.data.get("updated_at")
                }
                return ResourcePermission(**data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting resource permission {resource_type}:{resource_name}: {e}")
            return None
    
    async def list_resource_permissions(self, resource_type: Optional[ResourceType] = None) -> List[ResourcePermission]:
        """List resource permission configurations"""
        try:
            query = self.supabase.table(self.table_name).select("*").eq("permission_type", "resource_config").eq("is_active", True)
            
            if resource_type:
                query = query.eq("resource_type", resource_type.value)
            
            result = query.execute()
            
            if result.data:
                permissions = []
                for item in result.data:
                    # Map unified table fields back to ResourcePermission model
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
            data = {
                "resource_category": permission.resource_category,
                "description": permission.description,
                "subscription_tier_required": permission.subscription_tier_required.value,
                "access_level": permission.access_level.value,
                "is_active": permission.is_enabled,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.table_name)\
                .update(data)\
                .eq("permission_type", "resource_config")\
                .eq("resource_type", permission.resource_type.value)\
                .eq("resource_name", permission.resource_name)\
                .execute()
            
            if result.data:
                # Map back to ResourcePermission model
                response_data = result.data[0]
                response_data["id"] = str(response_data["id"]) if response_data.get("id") else None
                data = {
                    "id": response_data.get("id"),
                    "resource_type": response_data.get("resource_type"),
                    "resource_name": response_data.get("resource_name"),
                    "resource_category": response_data.get("resource_category"),
                    "subscription_tier_required": response_data.get("subscription_tier_required"),
                    "access_level": response_data.get("access_level"),
                    "is_enabled": response_data.get("is_active"),
                    "description": response_data.get("description"),
                    "created_at": response_data.get("created_at"),
                    "updated_at": response_data.get("updated_at")
                }
                return ResourcePermission(**data)
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
            data = {
                "permission_type": "user_permission",
                "target_type": "user",
                "target_id": permission.user_id,
                "resource_type": permission.resource_type.value,
                "resource_name": permission.resource_name,
                "access_level": permission.access_level.value,
                "permission_source": permission.permission_source.value,
                "is_active": permission.is_active,
                "metadata": {"granted_by": permission.granted_by_user_id}
            }

            with self.db:
                count = self.db.insert_into(self.table_name, [data], schema=self.schema)

            if count is not None and count > 0:
                # Query back the created permission
                return await self.get_user_permission(permission.user_id, permission.resource_type, permission.resource_name)

            return None

        except Exception as e:
            logger.error(f"Failed to grant user permission: {e}")
            return None
    
    async def get_user_permission(self, user_id: str, resource_type: ResourceType, resource_name: str) -> Optional[UserPermissionRecord]:
        """Get user permission for specific resource"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"""SELECT * FROM {self.schema}.{self.table_name}
                        WHERE permission_type = $1
                        AND target_id = $2
                        AND resource_type = $3
                        AND resource_name = $4
                        AND is_active = TRUE
                    """,
                    ["user_permission", user_id, resource_type.value, resource_name],
                    schema=self.schema
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
            query = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("permission_type", "user_permission")\
                .eq("target_id", user_id)\
                .eq("is_active", True)\
                .or_("expires_at.is.null,expires_at.gt.now()")
            
            if resource_type:
                query = query.eq("resource_type", resource_type.value)
            
            result = query.execute()
            
            if result.data:
                permissions = []
                for item in result.data:
                    # Map back to UserPermissionRecord model
                    record_data = {
                        "id": str(item.get("id")) if item.get("id") else None,
                        "user_id": item.get("target_id"),
                        "resource_type": item.get("resource_type"),
                        "resource_name": item.get("resource_name"),
                        "access_level": item.get("access_level"),
                        "permission_source": item.get("permission_source"),
                        "granted_by_user_id": item.get("granted_by_user_id"),
                        "organization_id": None,  # Not stored in unified table currently
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
            now = datetime.now(tz=timezone.utc)

            with self.db:
                self.db.execute(
                    f"""UPDATE {self.schema}.{self.table_name}
                        SET is_active = FALSE, updated_at = $1
                        WHERE permission_type = $2
                        AND target_id = $3
                        AND resource_type = $4
                        AND resource_name = $5
                    """,
                    [now, "user_permission", user_id, resource_type.value, resource_name],
                    schema=self.schema
                )

            return True

        except Exception as e:
            logger.error(f"Failed to revoke user permission: {e}")
            return False
    
    # ====================
    # Organization Permission Management
    # ====================
    
    async def create_organization_permission(self, permission: OrganizationPermission) -> Optional[OrganizationPermission]:
        """Create organization permission configuration"""
        try:
            data = {
                "organization_id": permission.organization_id,
                "resource_type": permission.resource_type.value,
                "resource_name": permission.resource_name,
                "access_level": permission.access_level.value,
                "org_plan_required": permission.org_plan_required,
                "is_enabled": permission.is_enabled,
                "created_by_user_id": permission.created_by_user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Use unified table with org permission type
            unified_data = {
                "permission_type": "org_permission",
                "target_type": "organization",
                "target_id": permission.organization_id,
                "resource_type": permission.resource_type.value,
                "resource_name": permission.resource_name,
                "access_level": permission.access_level.value,
                "permission_source": "organization_admin",
                "subscription_tier_required": permission.org_plan_required,
                "is_active": permission.is_enabled,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.table_name).insert(unified_data).execute()

            if result.data:
                return OrganizationPermission(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to create organization permission: {e}")
            return None
    
    async def get_organization_permission(self, organization_id: str, resource_type: ResourceType, resource_name: str) -> Optional[OrganizationPermission]:
        """Get organization permission configuration"""
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("permission_type", "org_permission")\
                .eq("target_id", organization_id)\
                .eq("resource_type", resource_type.value)\
                .eq("resource_name", resource_name)\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            if result.data:
                return OrganizationPermission(**result.data)
            return None
            
        except Exception as e:
            logger.debug(f"Organization permission not found: {organization_id} - {resource_type}:{resource_name}")
            return None
    
    async def list_organization_permissions(self, organization_id: str) -> List[OrganizationPermission]:
        """List all permissions for an organization"""
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("permission_type", "org_permission")\
                .eq("target_id", organization_id)\
                .eq("is_active", True)\
                .execute()
            
            if result.data:
                return [OrganizationPermission(**item) for item in result.data]
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
            # Use AccountServiceClient instead of direct database query
            account_profile = await self.account_client.get_account_profile(user_id)

            if not account_profile:
                logger.debug(f"User not found via account service: {user_id}")
                return None

            # Get user's organizations via OrganizationServiceClient
            user_orgs = await self.org_client.get_user_organizations(user_id)
            organization_id = None
            if user_orgs and len(user_orgs) > 0:
                # Take the first active organization
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
            # Use OrganizationServiceClient instead of direct database query
            # Note: We need a user_id for authorization, using system user
            org_data = await self.org_client.get_organization(
                organization_id=organization_id,
                user_id="system"  # Internal service call
            )

            if not org_data:
                logger.debug(f"Organization not found via service: {organization_id}")
                return None

            # Get member count from members list
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
            # Get organization members via OrganizationServiceClient
            members = await self.org_client.get_members(
                organization_id=organization_id,
                user_id="system"  # Internal service call
            )

            if not members:
                return False

            # Check if user_id is in the members list
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
            # Get user info
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return None
            
            # Get organization info if applicable
            org_info = None
            if user_info.organization_id:
                org_info = await self.get_organization_info(user_info.organization_id)
            
            # Get user permissions
            permissions = await self.list_user_permissions(user_id)
            
            # Calculate statistics
            permissions_by_type = {}
            permissions_by_source = {}
            permissions_by_level = {}
            expires_soon_count = 0
            
            soon_threshold = datetime.utcnow() + timedelta(days=7)
            
            for perm in permissions:
                # By type
                permissions_by_type[perm.resource_type] = permissions_by_type.get(perm.resource_type, 0) + 1
                
                # By source
                permissions_by_source[perm.permission_source] = permissions_by_source.get(perm.permission_source, 0) + 1
                
                # By level
                permissions_by_level[perm.access_level] = permissions_by_level.get(perm.access_level, 0) + 1
                
                # Expires soon
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
            # Count total permissions
            perm_result = self.supabase.table(self.table_name)\
                .select("count")\
                .eq("permission_type", "user_permission")\
                .eq("is_active", True)\
                .execute()
            total_permissions = len(perm_result.data) if perm_result.data else 0
            
            # Count unique users with permissions
            user_result = self.supabase.table(self.table_name)\
                .select("target_id")\
                .eq("permission_type", "user_permission")\
                .eq("is_active", True)\
                .execute()
            unique_users = len(set(item["target_id"] for item in user_result.data)) if user_result.data else 0
            
            # Count resource types
            resource_result = self.supabase.table(self.table_name)\
                .select("resource_type")\
                .eq("permission_type", "resource_config")\
                .eq("is_active", True)\
                .execute()
            unique_resources = len(set(item["resource_type"] for item in resource_result.data)) if resource_result.data else 0
            
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
            result = self.supabase.table(self.table_name)\
                .delete()\
                .eq("permission_type", "user_permission")\
                .lt("expires_at", datetime.utcnow().isoformat())\
                .execute()
            
            cleaned_count = len(result.data) if result.data else 0
            logger.info(f"Cleaned up {cleaned_count} expired permissions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired permissions: {e}")
            return 0
    
    # ====================
    # Cleanup
    # ====================

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
            data = {
                "user_id": audit_log.user_id,
                "resource_type": audit_log.resource_type.value,
                "resource_name": audit_log.resource_name,
                "action": audit_log.action,
                "old_access_level": audit_log.old_access_level.value if audit_log.old_access_level else None,
                "new_access_level": audit_log.new_access_level.value if audit_log.new_access_level else None,
                "performed_by_user_id": audit_log.performed_by_user_id,
                "reason": audit_log.reason,
                "success": audit_log.success,
                "error_message": audit_log.error_message,
                "timestamp": audit_log.timestamp
            }
            
            # Use a separate audit_logs table or add to unified table with audit type
            audit_data = {
                "permission_type": "audit_log",
                "target_type": "system",
                "target_id": audit_log.user_id,
                "resource_type": audit_log.resource_type.value,
                "resource_name": audit_log.resource_name,
                "access_level": audit_log.new_access_level.value if audit_log.new_access_level else None,
                "permission_source": "audit_system",
                "is_active": audit_log.success,
                "created_at": audit_log.timestamp.isoformat(),
                "updated_at": audit_log.timestamp.isoformat()
            }
            
            result = self.supabase.table(self.table_name).insert(audit_data).execute()

            return result.data is not None
            
        except Exception as e:
            logger.error(f"Failed to log permission action: {e}")
            return False