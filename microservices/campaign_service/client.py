"""
Campaign Service Client

Client for other services to call campaign_service.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class CampaignClient:
    """Client for campaign_service"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("default")

        host, port = config.discover_service(
            service_name='campaign_service',
            default_host='localhost',
            default_port=8240,
            env_host_key='CAMPAIGN_SERVICE_HOST',
            env_port_key='CAMPAIGN_SERVICE_PORT'
        )
        self.base_url = f"http://{host}:{port}"
        self.timeout = 30.0

    async def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign ID

        Returns:
            Campaign data or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/campaigns/{campaign_id}"
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json()
                return data.get("campaign")

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting campaign: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            return None

    async def list_campaigns(
        self,
        organization_id: Optional[str] = None,
        status: Optional[List[str]] = None,
        campaign_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List campaigns with filters.

        Args:
            organization_id: Filter by organization
            status: Filter by status list
            campaign_type: Filter by type
            limit: Page size
            offset: Page offset

        Returns:
            Campaign list response
        """
        try:
            params = {
                "limit": limit,
                "offset": offset,
            }
            if status:
                params["status"] = ",".join(status)
            if campaign_type:
                params["type"] = campaign_type

            headers = {}
            if organization_id:
                headers["X-Organization-ID"] = organization_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/campaigns",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error listing campaigns: {e}")
            return {"campaigns": [], "total": 0}

    async def create_campaign(
        self,
        name: str,
        campaign_type: str,
        organization_id: str,
        user_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a new campaign.

        Args:
            name: Campaign name
            campaign_type: Campaign type (scheduled/triggered)
            organization_id: Organization ID
            user_id: Creating user ID
            **kwargs: Additional campaign parameters

        Returns:
            Created campaign data
        """
        try:
            request_data = {
                "name": name,
                "campaign_type": campaign_type,
                **kwargs,
            }

            headers = {
                "X-Organization-ID": organization_id,
                "X-User-ID": user_id,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/campaigns",
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating campaign: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            raise

    async def schedule_campaign(
        self,
        campaign_id: str,
        scheduled_at: str,
        timezone: str = "UTC",
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Schedule a campaign.

        Args:
            campaign_id: Campaign ID
            scheduled_at: Scheduled time (ISO format)
            timezone: Timezone
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Updated campaign data
        """
        try:
            request_data = {
                "scheduled_at": scheduled_at,
                "timezone": timezone,
            }

            headers = {}
            if organization_id:
                headers["X-Organization-ID"] = organization_id
            if user_id:
                headers["X-User-ID"] = user_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/campaigns/{campaign_id}/schedule",
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error scheduling campaign: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Error scheduling campaign: {e}")
            raise

    async def activate_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Activate a triggered campaign.

        Args:
            campaign_id: Campaign ID
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Updated campaign data
        """
        try:
            headers = {}
            if organization_id:
                headers["X-Organization-ID"] = organization_id
            if user_id:
                headers["X-User-ID"] = user_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/campaigns/{campaign_id}/activate",
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error activating campaign: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Error activating campaign: {e}")
            raise

    async def pause_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pause a running campaign"""
        try:
            headers = {}
            if organization_id:
                headers["X-Organization-ID"] = organization_id
            if user_id:
                headers["X-User-ID"] = user_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/campaigns/{campaign_id}/pause",
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error pausing campaign: {e}")
            raise

    async def resume_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resume a paused campaign"""
        try:
            headers = {}
            if organization_id:
                headers["X-Organization-ID"] = organization_id
            if user_id:
                headers["X-User-ID"] = user_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/campaigns/{campaign_id}/resume",
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error resuming campaign: {e}")
            raise

    async def cancel_campaign(
        self,
        campaign_id: str,
        reason: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel a campaign"""
        try:
            request_data = {}
            if reason:
                request_data["reason"] = reason

            headers = {}
            if organization_id:
                headers["X-Organization-ID"] = organization_id
            if user_id:
                headers["X-User-ID"] = user_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/campaigns/{campaign_id}/cancel",
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error cancelling campaign: {e}")
            raise

    async def get_campaign_metrics(
        self,
        campaign_id: str,
        breakdown_by: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get campaign metrics"""
        try:
            params = {}
            if breakdown_by:
                params["breakdown_by"] = ",".join(breakdown_by)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/campaigns/{campaign_id}/metrics",
                    params=params,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error getting campaign metrics: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if campaign_service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


__all__ = ["CampaignClient"]
