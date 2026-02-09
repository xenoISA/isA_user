"""
Organization Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import (
    OrganizationResponse, OrganizationMemberResponse,
    OrganizationRole, MemberStatus
)


# ============================================================================
# Custom Exceptions - Defined here to avoid importing repository
# ============================================================================

class OrganizationNotFoundError(Exception):
    """Organization not found error"""
    pass


class OrganizationAccessDeniedError(Exception):
    """Organization access denied error"""
    pass


class OrganizationValidationError(Exception):
    """Organization validation error"""
    pass


class DuplicateEntryError(Exception):
    """Duplicate entry error"""
    pass


class MemberNotFoundError(Exception):
    """Member not found error"""
    pass


# ============================================================================
# Repository Protocols
# ============================================================================

@runtime_checkable
class OrganizationRepositoryProtocol(Protocol):
    """
    Interface for Organization Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_organization(
        self, organization_data: Dict[str, Any], owner_user_id: str
    ) -> Optional[OrganizationResponse]:
        """Create organization and add owner"""
        ...

    async def get_organization(self, organization_id: str) -> Optional[OrganizationResponse]:
        """Get organization by ID"""
        ...

    async def update_organization(
        self, organization_id: str, update_data: Dict[str, Any]
    ) -> Optional[OrganizationResponse]:
        """Update organization"""
        ...

    async def delete_organization(self, organization_id: str) -> bool:
        """Delete organization (soft delete)"""
        ...

    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all organizations for a user"""
        ...

    async def add_organization_member(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole,
        permissions: Optional[List[str]] = None
    ) -> Optional[OrganizationMemberResponse]:
        """Add member to organization"""
        ...

    async def update_organization_member(
        self,
        organization_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[OrganizationMemberResponse]:
        """Update organization member"""
        ...

    async def remove_organization_member(
        self, organization_id: str, user_id: str
    ) -> bool:
        """Remove member from organization"""
        ...

    async def get_organization_member(
        self, organization_id: str, user_id: str
    ) -> Optional[OrganizationMemberResponse]:
        """Get organization member"""
        ...

    async def get_organization_members(
        self,
        organization_id: str,
        limit: int = 100,
        offset: int = 0,
        role_filter: Optional[OrganizationRole] = None,
        status_filter: Optional[MemberStatus] = None
    ) -> List[OrganizationMemberResponse]:
        """Get organization members list"""
        ...

    async def get_user_organization_role(
        self, organization_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user role in organization"""
        ...

    async def get_organization_member_count(self, organization_id: str) -> int:
        """Get organization member count"""
        ...

    async def get_organization_stats(self, organization_id: str) -> Dict[str, Any]:
        """Get organization statistics"""
        ...

    async def list_all_organizations(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        plan_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[OrganizationResponse]:
        """List all organizations (admin)"""
        ...


@runtime_checkable
class FamilySharingRepositoryProtocol(Protocol):
    """
    Interface for Family Sharing Repository.

    Used for dependency injection to enable testing.
    """

    async def create_sharing(self, sharing_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create sharing resource"""
        ...

    async def get_sharing(self, sharing_id: str) -> Optional[Dict[str, Any]]:
        """Get sharing by ID"""
        ...

    async def update_sharing(
        self, sharing_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update sharing"""
        ...

    async def delete_sharing(self, sharing_id: str) -> bool:
        """Delete sharing"""
        ...

    async def get_sharing_member_permissions(
        self, sharing_id: str
    ) -> List[Dict[str, Any]]:
        """Get member permissions for sharing"""
        ...

    async def create_member_permission(
        self, permission_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create member permission"""
        ...

    async def get_member_permission(
        self, sharing_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get member permission"""
        ...

    async def update_member_permission(
        self, sharing_id: str, user_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update member permission"""
        ...

    async def delete_member_permission(self, sharing_id: str, user_id: str) -> bool:
        """Delete member permission"""
        ...

    async def delete_sharing_member_permissions(self, sharing_id: str) -> bool:
        """Delete all member permissions for sharing"""
        ...

    async def check_organization_admin(
        self, organization_id: str, user_id: str
    ) -> bool:
        """Check if user is organization admin"""
        ...

    async def check_organization_member(
        self, organization_id: str, user_id: str
    ) -> bool:
        """Check if user is organization member"""
        ...

    async def get_organization_members(
        self, organization_id: str
    ) -> List[Dict[str, Any]]:
        """Get organization members"""
        ...

    async def list_organization_sharings(
        self,
        organization_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List organization sharings"""
        ...

    async def get_member_permissions(
        self,
        organization_id: str,
        user_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get member permissions"""
        ...

    async def count_member_permissions(
        self,
        organization_id: str,
        user_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Count member permissions"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client"""

    async def get_account(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account by user ID"""
        ...

    async def validate_user_exists(self, user_id: str) -> bool:
        """Validate user exists"""
        ...


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Exceptions
    "OrganizationNotFoundError",
    "OrganizationAccessDeniedError",
    "OrganizationValidationError",
    "DuplicateEntryError",
    "MemberNotFoundError",
    # Protocols
    "OrganizationRepositoryProtocol",
    "FamilySharingRepositoryProtocol",
    "EventBusProtocol",
    "AccountClientProtocol",
]
