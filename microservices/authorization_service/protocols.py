"""
Authorization Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import (
    ResourcePermission,
    UserPermissionRecord,
    OrganizationPermission,
    ResourceType,
    AccessLevel,
    UserPermissionSummary,
    PermissionAuditLog,
    ExternalServiceUser,
    ExternalServiceOrganization,
)


# Custom exceptions - defined here to avoid importing repository

class AuthorizationException(Exception):
    """Base authorization exception"""
    pass


class PermissionNotFoundException(AuthorizationException):
    """Permission not found"""
    pass


class UserNotFoundException(AuthorizationException):
    """User not found"""
    pass


class OrganizationNotFoundException(AuthorizationException):
    """Organization not found"""
    pass


class InvalidPermissionError(AuthorizationException):
    """Invalid permission configuration"""
    pass


@runtime_checkable
class AuthorizationRepositoryProtocol(Protocol):
    """
    Interface for Authorization Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    # Resource Permission Management
    async def create_resource_permission(
        self, permission: ResourcePermission
    ) -> bool:
        """Create a new resource permission"""
        ...

    async def get_resource_permission(
        self, resource_type: ResourceType, resource_name: str
    ) -> Optional[ResourcePermission]:
        """Get resource permission configuration"""
        ...

    async def list_resource_permissions(
        self, resource_type: Optional[ResourceType] = None
    ) -> List[ResourcePermission]:
        """List all resource permissions"""
        ...

    # User Permission Management
    async def grant_user_permission(
        self, permission: UserPermissionRecord
    ) -> bool:
        """Grant permission to a user"""
        ...

    async def revoke_user_permission(
        self, user_id: str, resource_type: ResourceType, resource_name: str
    ) -> bool:
        """Revoke permission from a user"""
        ...

    async def get_user_permission(
        self, user_id: str, resource_type: ResourceType, resource_name: str
    ) -> Optional[UserPermissionRecord]:
        """Get user's permission for a specific resource"""
        ...

    async def list_user_permissions(
        self, user_id: str, resource_type: Optional[ResourceType] = None
    ) -> List[UserPermissionRecord]:
        """List all permissions for a user"""
        ...

    # Organization Permission Management
    async def get_organization_permission(
        self, organization_id: str, resource_type: ResourceType, resource_name: str
    ) -> Optional[OrganizationPermission]:
        """Get organization permission"""
        ...

    # User and Organization Information
    async def get_user_info(self, user_id: str) -> Optional[ExternalServiceUser]:
        """Get user information from account service"""
        ...

    async def get_organization_info(
        self, organization_id: str
    ) -> Optional[ExternalServiceOrganization]:
        """Get organization information"""
        ...

    async def is_user_organization_member(
        self, user_id: str, organization_id: str
    ) -> bool:
        """Check if user is member of organization"""
        ...

    # Permission Summary and Analytics
    async def get_user_permission_summary(
        self, user_id: str
    ) -> Optional[UserPermissionSummary]:
        """Get comprehensive permission summary for a user"""
        ...

    # Audit Logging
    async def log_permission_action(self, audit_log: PermissionAuditLog) -> bool:
        """Log permission action for audit trail"""
        ...

    # Service Management
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        ...

    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions"""
        ...

    async def cleanup(self) -> None:
        """Cleanup repository resources"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...
