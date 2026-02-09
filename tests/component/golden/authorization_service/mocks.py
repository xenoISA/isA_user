"""
Mock implementations for Authorization Service testing

These mocks implement the protocols defined in authorization_service.protocols
for use in component testing without real I/O dependencies.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from microservices.authorization_service.models import (
    ResourcePermission,
    UserPermissionRecord,
    OrganizationPermission,
    ResourceType,
    AccessLevel,
    PermissionSource,
    SubscriptionTier,
    UserPermissionSummary,
    PermissionAuditLog,
    ExternalServiceUser,
    ExternalServiceOrganization,
)


class MockAuthorizationRepository:
    """
    Mock Authorization Repository implementing AuthorizationRepositoryProtocol.

    Used for component tests - no real database or HTTP calls needed.
    """

    def __init__(self):
        self._resource_permissions: Dict[str, ResourcePermission] = {}
        self._user_permissions: Dict[str, UserPermissionRecord] = {}
        self._org_permissions: Dict[str, OrganizationPermission] = {}
        self._users: Dict[str, ExternalServiceUser] = {}
        self._organizations: Dict[str, ExternalServiceOrganization] = {}
        self._org_members: Dict[str, List[str]] = {}  # org_id -> [user_ids]
        self._audit_logs: List[PermissionAuditLog] = []
        self._should_fail = False
        self._fail_message = ""

    def set_failure(self, message: str = "Mock repository failure"):
        """Configure mock to fail on next operation"""
        self._should_fail = True
        self._fail_message = message

    def add_user(
        self,
        user_id: str,
        email: str,
        subscription_status: str = "free",
        is_active: bool = True,
        organization_id: Optional[str] = None,
    ):
        """Add a user to the mock store"""
        self._users[user_id] = ExternalServiceUser(
            user_id=user_id,
            email=email,
            subscription_status=subscription_status,
            is_active=is_active,
            organization_id=organization_id,
        )

    def add_organization(
        self,
        organization_id: str,
        plan: str = "startup",
        is_active: bool = True,
        member_count: int = 0,
    ):
        """Add an organization to the mock store"""
        self._organizations[organization_id] = ExternalServiceOrganization(
            organization_id=organization_id,
            plan=plan,
            is_active=is_active,
            member_count=member_count,
        )

    def add_org_member(self, user_id: str, organization_id: str):
        """Add user as organization member"""
        if organization_id not in self._org_members:
            self._org_members[organization_id] = []
        if user_id not in self._org_members[organization_id]:
            self._org_members[organization_id].append(user_id)

    # Resource Permission Management
    async def create_resource_permission(
        self, permission: ResourcePermission
    ) -> bool:
        """Create a new resource permission"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        key = f"{permission.resource_type.value}:{permission.resource_name}"
        self._resource_permissions[key] = permission
        return True

    async def get_resource_permission(
        self, resource_type: ResourceType, resource_name: str
    ) -> Optional[ResourcePermission]:
        """Get resource permission configuration"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        key = f"{resource_type.value}:{resource_name}"
        return self._resource_permissions.get(key)

    async def list_resource_permissions(
        self, resource_type: Optional[ResourceType] = None
    ) -> List[ResourcePermission]:
        """List all resource permissions"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        if resource_type:
            return [
                perm
                for perm in self._resource_permissions.values()
                if perm.resource_type == resource_type
            ]
        return list(self._resource_permissions.values())

    # User Permission Management
    async def grant_user_permission(self, permission: UserPermissionRecord) -> bool:
        """Grant permission to a user"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        key = f"{permission.user_id}:{permission.resource_type.value}:{permission.resource_name}"
        self._user_permissions[key] = permission
        return True

    async def revoke_user_permission(
        self, user_id: str, resource_type: ResourceType, resource_name: str
    ) -> bool:
        """Revoke permission from a user"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        key = f"{user_id}:{resource_type.value}:{resource_name}"
        if key in self._user_permissions:
            del self._user_permissions[key]
            return True
        return False

    async def get_user_permission(
        self, user_id: str, resource_type: ResourceType, resource_name: str
    ) -> Optional[UserPermissionRecord]:
        """Get user's permission for a specific resource"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        key = f"{user_id}:{resource_type.value}:{resource_name}"
        return self._user_permissions.get(key)

    async def list_user_permissions(
        self, user_id: str, resource_type: Optional[ResourceType] = None
    ) -> List[UserPermissionRecord]:
        """List all permissions for a user"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        permissions = [
            perm
            for perm in self._user_permissions.values()
            if perm.user_id == user_id
        ]

        if resource_type:
            permissions = [p for p in permissions if p.resource_type == resource_type]

        return permissions

    # Organization Permission Management
    async def get_organization_permission(
        self, organization_id: str, resource_type: ResourceType, resource_name: str
    ) -> Optional[OrganizationPermission]:
        """Get organization permission"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        key = f"{organization_id}:{resource_type.value}:{resource_name}"
        return self._org_permissions.get(key)

    # User and Organization Information
    async def get_user_info(self, user_id: str) -> Optional[ExternalServiceUser]:
        """Get user information from account service"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        return self._users.get(user_id)

    async def get_organization_info(
        self, organization_id: str
    ) -> Optional[ExternalServiceOrganization]:
        """Get organization information"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        return self._organizations.get(organization_id)

    async def is_user_organization_member(
        self, user_id: str, organization_id: str
    ) -> bool:
        """Check if user is member of organization"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        return user_id in self._org_members.get(organization_id, [])

    # Permission Summary and Analytics
    async def get_user_permission_summary(
        self, user_id: str
    ) -> Optional[UserPermissionSummary]:
        """Get comprehensive permission summary for a user"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        user = await self.get_user_info(user_id)
        if not user:
            return None

        permissions = await self.list_user_permissions(user_id)

        return UserPermissionSummary(
            user_id=user_id,
            subscription_tier=user.subscription_status,
            organization_id=user.organization_id,
            organization_plan=None,
            total_permissions=len(permissions),
            permissions_by_type={},
            permissions_by_source={},
            permissions_by_level={},
            expires_soon_count=0,
            last_access_check=None,
        )

    # Audit Logging
    async def log_permission_action(self, audit_log: PermissionAuditLog) -> bool:
        """Log permission action for audit trail"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        self._audit_logs.append(audit_log)
        return True

    # Service Management
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        return {
            "total_permissions": len(self._user_permissions),
            "active_users": len(self._users),
            "resource_types": len(set(p.resource_type for p in self._resource_permissions.values())),
        }

    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        # Count expired (mock implementation)
        return 0

    async def cleanup(self) -> None:
        """Cleanup repository resources"""
        pass

    async def check_connection(self) -> bool:
        """Check database connection"""
        return not self._should_fail
