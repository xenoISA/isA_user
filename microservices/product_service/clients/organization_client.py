"""
Organization Service Client

HTTP client for synchronous communication with organization_service
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class OrganizationClient:
    """Client for organization_service"""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Organization Service client

        Args:
            base_url: Organization service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("organization_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8205"

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"OrganizationClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_organization(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization by ID

        Args:
            organization_id: Organization ID

        Returns:
            Organization data if found, None otherwise
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/organization/organizations/{organization_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Organization {organization_id} not found")
                return None
            logger.error(f"Failed to get organization {organization_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting organization {organization_id}: {e}")
            return None

    async def validate_organization(self, organization_id: str) -> bool:
        """
        Validate if organization exists

        Args:
            organization_id: Organization ID

        Returns:
            True if organization exists, False otherwise
        """
        org = await self.get_organization(organization_id)
        return org is not None

    async def get_organization_members(self, organization_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get organization members

        Args:
            organization_id: Organization ID

        Returns:
            List of members if found, None otherwise
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/organization/organizations/{organization_id}/members"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Organization {organization_id} not found")
                return None
            logger.error(f"Failed to get organization members: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting organization members: {e}")
            return None

    async def check_user_in_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """
        Check if user is member of organization

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            True if user is member, False otherwise
        """
        try:
            members = await self.get_organization_members(organization_id)
            if not members:
                return False

            return any(member.get("user_id") == user_id for member in members)

        except Exception as e:
            logger.error(f"Error checking user in organization: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if organization service is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
