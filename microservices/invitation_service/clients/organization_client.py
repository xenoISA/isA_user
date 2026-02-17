"""
Organization Service Client

Client for invitation_service to interact with organization_service.
Used for validating organization membership and roles for invitations.
"""

import os
import sys
from typing import Optional, Dict, Any, List

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.organization_service.client import OrganizationServiceClient


class OrganizationClient:
    """
    Wrapper client for Organization Service calls from Invitation Service.

    This wrapper provides invitation-specific convenience methods
    while delegating to the actual OrganizationServiceClient.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize Organization Service client

        Args:
            base_url: Organization service base URL (optional, uses service discovery)
        """
        self._client = OrganizationServiceClient(base_url=base_url)

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Invitation-specific convenience methods
    # =============================================================================

    async def get_organization_info(
        self, organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get organization information for invitation context.

        Args:
            organization_id: Organization ID

        Returns:
            Organization details or None
        """
        try:
            return await self._client.get_organization(organization_id)
        except Exception:
            return None

    async def get_organization_name(self, organization_id: str) -> Optional[str]:
        """
        Get organization name for invitation display.

        Args:
            organization_id: Organization ID

        Returns:
            Organization name or None
        """
        try:
            org = await self._client.get_organization(organization_id)
            if org:
                return org.get("name")
            return None
        except Exception:
            return None

    async def can_user_invite(
        self, user_id: str, organization_id: str
    ) -> bool:
        """
        Check if user can send invitations for this organization.

        Only admins and owners can invite new members.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            True if user can invite, False otherwise
        """
        try:
            member = await self._client.get_organization_member(
                organization_id, user_id
            )
            if member:
                role = member.get("role", "").lower()
                return role in ["admin", "owner"]
            return False
        except Exception:
            return False

    async def is_user_member(
        self, user_id: str, organization_id: str
    ) -> bool:
        """
        Check if user is already a member of the organization.

        Prevents duplicate invitations to existing members.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            True if user is a member, False otherwise
        """
        try:
            member = await self._client.get_organization_member(
                organization_id, user_id
            )
            return member is not None
        except Exception:
            return False

    async def add_member_to_organization(
        self,
        organization_id: str,
        user_id: str,
        role: str = "member",
        invited_by: Optional[str] = None
    ) -> bool:
        """
        Add user to organization after invitation acceptance.

        Args:
            organization_id: Organization ID
            user_id: User ID to add
            role: Role to assign (member, admin)
            invited_by: User ID who sent the invitation

        Returns:
            True if added successfully
        """
        try:
            result = await self._client.add_organization_member(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                metadata={"invited_by": invited_by} if invited_by else None
            )
            return result is not None
        except Exception:
            return False

    async def get_organization_member_count(
        self, organization_id: str
    ) -> int:
        """
        Get current member count for capacity checks.

        Args:
            organization_id: Organization ID

        Returns:
            Number of members
        """
        try:
            members = await self._client.get_organization_members(organization_id)
            if members:
                return len(members.get("members", []))
            return 0
        except Exception:
            return 0

    # =============================================================================
    # Direct delegation to OrganizationServiceClient
    # =============================================================================

    async def get_organization(self, organization_id: str):
        """Get organization details"""
        return await self._client.get_organization(organization_id)

    async def get_organization_members(self, organization_id: str):
        """Get organization members"""
        return await self._client.get_organization_members(organization_id)

    async def health_check(self) -> bool:
        """Check Organization Service health"""
        return await self._client.health_check()


__all__ = ["OrganizationClient"]
