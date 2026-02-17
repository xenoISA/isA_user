"""
Organization Service Client for Auth Service

Handles organization-related operations for authentication
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)


class OrganizationServiceClient:
    """Client for communicating with Organization Service"""

    def __init__(self):
        """Initialize Organization Service client"""
        try:
            # Add parent directory to path to import organization_service client
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

            from microservices.organization_service.client import OrganizationServiceClient as OrgClient

            self.client = OrgClient()
            logger.info("✅ OrganizationServiceClient initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize OrganizationServiceClient: {e}")
            self.client = None

    async def get_organization(self, organization_id: str, user_id: str = None):
        """
        Get organization details

        Args:
            organization_id: Organization ID
            user_id: User ID for access control (required by underlying client)

        Returns:
            Organization details or None if not found
        """
        try:
            if not self.client:
                logger.warning("OrganizationServiceClient not available")
                return None

            result = await self.client.get_organization(
                organization_id=organization_id,
                user_id=user_id or "internal-service"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get organization {organization_id}: {e}")
            return None

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.close()


__all__ = ["OrganizationServiceClient"]
