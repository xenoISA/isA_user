"""
Invitation Service Protocols - DI Interfaces

All dependencies defined as Protocol classes for testability.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List, Tuple
from datetime import datetime


@runtime_checkable
class InvitationRepositoryProtocol(Protocol):
    """Repository interface for invitation data access"""

    async def create_invitation(
        self,
        organization_id: str,
        email: str,
        role: Any,
        invited_by: str
    ) -> Optional[Any]:
        """Create new invitation and return InvitationResponse"""
        ...

    async def get_invitation_by_id(
        self, invitation_id: str
    ) -> Optional[Any]:
        """Get invitation by ID"""
        ...

    async def get_invitation_by_token(
        self, invitation_token: str
    ) -> Optional[Any]:
        """Get invitation by token"""
        ...

    async def get_invitation_with_organization_info(
        self, invitation_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get invitation with organization info"""
        ...

    async def get_pending_invitation_by_email_and_organization(
        self, email: str, organization_id: str
    ) -> Optional[Any]:
        """Get pending invitation by email and org"""
        ...

    async def get_organization_invitations(
        self, organization_id: str, limit: int, offset: int
    ) -> List[Any]:
        """List organization invitations"""
        ...

    async def update_invitation(
        self, invitation_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """Update invitation fields"""
        ...

    async def accept_invitation(self, invitation_token: str) -> bool:
        """Accept invitation by token"""
        ...

    async def cancel_invitation(self, invitation_id: str) -> bool:
        """Cancel invitation"""
        ...

    async def expire_old_invitations(self) -> int:
        """Expire old pending invitations"""
        ...

    async def delete_invitation(self, invitation_id: str) -> bool:
        """Delete invitation"""
        ...

    async def get_invitation_stats(
        self, organization_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get invitation statistics"""
        ...

    async def cancel_organization_invitations(
        self, organization_id: str
    ) -> int:
        """Cancel all pending invitations for an organization"""
        ...

    async def cancel_invitations_by_inviter(self, user_id: str) -> int:
        """Cancel all pending invitations sent by a user"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for NATS publishing"""

    async def publish_event(self, event: Any) -> None:
        """Publish event to NATS"""
        ...

    async def subscribe(
        self, subject: str, callback: Any
    ) -> None:
        """Subscribe to NATS subject"""
        ...

    async def close(self) -> None:
        """Close connection"""
        ...


@runtime_checkable
class OrganizationClientProtocol(Protocol):
    """Client interface for organization service calls"""

    async def get_organization_info(
        self, organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get organization info"""
        ...

    async def get_organization_name(
        self, organization_id: str
    ) -> Optional[str]:
        """Get organization name"""
        ...

    async def can_user_invite(
        self, user_id: str, organization_id: str
    ) -> bool:
        """Check if user can invite to organization"""
        ...

    async def is_user_member(
        self, user_id: str, organization_id: str
    ) -> bool:
        """Check if user is already a member"""
        ...

    async def add_member_to_organization(
        self,
        organization_id: str,
        user_id: str,
        role: str,
        invited_by: Optional[str]
    ) -> bool:
        """Add user as organization member"""
        ...

    async def get_organization_member_count(
        self, organization_id: str
    ) -> int:
        """Get current member count"""
        ...

    async def close(self) -> None:
        """Close client connection"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Client interface for account service calls"""

    async def get_user_by_email(
        self, email: str
    ) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        ...

    async def get_user_by_id(
        self, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        ...

    async def verify_user_email(
        self, user_id: str, email: str
    ) -> bool:
        """Verify user's email matches"""
        ...

    async def close(self) -> None:
        """Close client connection"""
        ...


__all__ = [
    "InvitationRepositoryProtocol",
    "EventBusProtocol",
    "OrganizationClientProtocol",
    "AccountClientProtocol",
]
