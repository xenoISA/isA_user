"""
Product Service Client

Client for fetching subscription tier information from product service.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ProductClient:
    """Client for product service"""

    def __init__(self, base_url: str = "http://product:8207"):
        self.base_url = base_url
        self.timeout = 10.0

    async def get_subscription_tiers(self) -> List[Dict[str, Any]]:
        """Get all subscription tiers from product service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/subscription-tiers")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("tiers", [])
                else:
                    logger.warning(f"Failed to get subscription tiers: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching subscription tiers: {e}")
            return []

    async def get_subscription_tier(self, tier_code: str) -> Optional[Dict[str, Any]]:
        """Get a specific subscription tier"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/subscription-tiers/{tier_code}")
                if response.status_code == 200:
                    return response.json().get("tier")
                else:
                    logger.warning(f"Tier {tier_code} not found: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching tier {tier_code}: {e}")
            return None

    async def get_cost_definition(
        self,
        service_type: str,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        operation_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cost definition for a specific service usage"""
        try:
            params = {"service_type": service_type}
            if provider:
                params["provider"] = provider
            if model_name:
                params["model_name"] = model_name
            if operation_type:
                params["operation_type"] = operation_type

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/cost-definitions/lookup",
                    params=params
                )
                if response.status_code == 200:
                    return response.json().get("cost_definition")
                else:
                    logger.warning(f"Cost definition not found: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching cost definition: {e}")
            return None


__all__ = ["ProductClient"]
