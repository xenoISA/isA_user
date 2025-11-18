"""
Organization Service Client

HTTP client for synchronous communication with organization_service
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class OrganizationServiceClient:
    """Client for organization_service HTTP API"""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize organization service client

        Args:
            base_url: Base URL of organization service (e.g., "http://localhost:8007")
                     If None, will use service discovery via Consul
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or "http://organization_service:8007"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def get_organization(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization details

        Args:
            organization_id: Organization ID

        Returns:
            Organization data if found, None otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/organizations/{organization_id}"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Organization not found: {organization_id}")
                return None
            else:
                logger.error(
                    f"Failed to get organization {organization_id}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error calling organization_service.get_organization: {e}")
            return None

    async def validate_organization_exists(self, organization_id: str) -> bool:
        """
        Validate that an organization exists

        Args:
            organization_id: Organization ID

        Returns:
            True if organization exists, False otherwise
        """
        org = await self.get_organization(organization_id)
        return org is not None

    async def get_organization_members(self, organization_id: str) -> Optional[list]:
        """
        Get list of organization members

        Args:
            organization_id: Organization ID

        Returns:
            List of member data if found, None on error
        """
        try:
            url = f"{self.base_url}/api/v1/organizations/{organization_id}/members"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json().get("members", [])
            else:
                logger.error(
                    f"Failed to get organization members: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(
                f"Error calling organization_service.get_organization_members: {e}"
            )
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
