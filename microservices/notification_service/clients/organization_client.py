"""
Organization Service Client

HTTP client for synchronous communication with organization_service
Provides methods to fetch organization and member information for notifications
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class OrganizationServiceClient:
    """Client for organization_service HTTP API"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize organization service client

        Args:
            config_manager: ConfigManager instance for service discovery
        """
        self.config_manager = config_manager or ConfigManager("notification_service")

        # Get organization_service endpoint from Consul or use fallback
        self.base_url = self._get_service_url("organization_service", "http://localhost:8212")

        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "X-Service-Name": "notification_service"  # Internal service identifier
            }
        )

        logger.info(f"OrganizationServiceClient initialized with base_url: {self.base_url}")

    def _get_service_url(self, service_name: str, fallback_url: str) -> str:
        """Get service URL from Consul or use fallback"""
        try:
            if self.config_manager:
                url = self.config_manager.get_service_endpoint(service_name)
                if url:
                    return url
        except Exception as e:
            logger.warning(f"Failed to get {service_name} from Consul: {e}")

        logger.info(f"Using fallback URL for {service_name}: {fallback_url}")
        return fallback_url

    async def get_organization(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization details

        Args:
            organization_id: Organization ID

        Returns:
            Organization dict or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/organizations/{organization_id}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Organization not found: {organization_id}")
                return None
            else:
                logger.error(f"Failed to get organization {organization_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching organization {organization_id}: {e}")
            return None

    async def get_organization_members(
        self,
        organization_id: str,
        role: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get organization members list

        Args:
            organization_id: Organization ID
            role: Filter by role (owner, admin, member)
            limit: Maximum number of members to return

        Returns:
            List of member dicts
        """
        try:
            params = {"limit": limit}
            if role:
                params["role"] = role

            response = await self.client.get(
                f"/api/v1/organizations/{organization_id}/members",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("members", [])
            else:
                logger.error(f"Failed to get organization members {organization_id}: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching organization members {organization_id}: {e}")
            return []

    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all organizations a user belongs to

        Args:
            user_id: User ID

        Returns:
            List of organization dicts
        """
        try:
            response = await self.client.get(
                f"/api/v1/users/organizations",
                headers={"X-User-ID": user_id}  # Pass user context
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("organizations", [])
            else:
                logger.error(f"Failed to get user organizations for {user_id}: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching user organizations {user_id}: {e}")
            return []

    async def get_organization_admins(self, organization_id: str) -> List[Dict[str, Any]]:
        """
        Get organization admins (owner + admin roles)

        Args:
            organization_id: Organization ID

        Returns:
            List of admin member dicts
        """
        try:
            # Get all members
            members = await self.get_organization_members(organization_id)

            # Filter for owner and admin roles
            admins = [
                member for member in members
                if member.get("role") in ["owner", "admin"]
            ]

            return admins

        except Exception as e:
            logger.error(f"Error fetching organization admins {organization_id}: {e}")
            return []

    async def get_member_emails(self, organization_id: str) -> List[str]:
        """
        Get all member email addresses for an organization

        Args:
            organization_id: Organization ID

        Returns:
            List of email addresses
        """
        try:
            members = await self.get_organization_members(organization_id)

            # Extract emails (assuming members have email field)
            emails = [
                member.get("email")
                for member in members
                if member.get("email")
            ]

            return emails

        except Exception as e:
            logger.error(f"Error fetching member emails {organization_id}: {e}")
            return []

    async def get_organization_stats(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization statistics

        Args:
            organization_id: Organization ID

        Returns:
            Stats dict or None if failed
        """
        try:
            response = await self.client.get(f"/api/v1/organizations/{organization_id}/stats")

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get organization stats {organization_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching organization stats {organization_id}: {e}")
            return None

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
        logger.info("OrganizationServiceClient closed")
