"""
Organization Service Client

Client for authorization_service to interact with organization_service.
Used for retrieving organization membership for permission checks.
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.organization_service.client import OrganizationServiceClient


class OrganizationClient:
    """
    Wrapper client for Organization Service calls from Authorization Service.

    This wrapper provides authorization-specific convenience methods
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
    # Authorization-specific convenience methods
    # =============================================================================

    async def get_user_organization_role(
        self, user_id: str, organization_id: str
    ) -> Optional[str]:
        """
        Get user's role in an organization.

        Used for organization-scoped permission checks.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            Role string (owner, admin, member) or None if not a member
        """
        try:
            member = await self._client.get_organization_member(
                organization_id, user_id
            )
            if member:
                return member.get("role")
            return None
        except Exception:
            return None

    async def is_organization_member(
        self, user_id: str, organization_id: str
    ) -> bool:
        """
        Check if user is a member of the organization.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            True if user is a member, False otherwise
        """
        role = await self.get_user_organization_role(user_id, organization_id)
        return role is not None

    async def is_organization_admin(
        self, user_id: str, organization_id: str
    ) -> bool:
        """
        Check if user is an admin or owner of the organization.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            True if user is admin or owner, False otherwise
        """
        role = await self.get_user_organization_role(user_id, organization_id)
        return role in ["admin", "owner"]

    async def is_organization_owner(
        self, user_id: str, organization_id: str
    ) -> bool:
        """
        Check if user is the owner of the organization.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            True if user is owner, False otherwise
        """
        role = await self.get_user_organization_role(user_id, organization_id)
        return role == "owner"

    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all organizations a user belongs to.

        Used for determining resource access scope.

        Args:
            user_id: User ID

        Returns:
            List of organization memberships
        """
        try:
            result = await self._client.get_user_organizations(user_id)
            if result:
                return result.get("organizations", [])
            return []
        except Exception:
            return []

    # =============================================================================
    # Direct delegation to OrganizationServiceClient
    # =============================================================================

    async def get_organization(self, organization_id: str):
        """Get organization details"""
        return await self._client.get_organization(organization_id)

    async def health_check(self) -> bool:
        """Check Organization Service health"""
        return await self._client.health_check()


__all__ = ["OrganizationClient"]
