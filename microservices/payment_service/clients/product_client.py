"""
Product Service Client for Payment Service

HTTP client for synchronous communication with product_service
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ProductClient:
    """Client for product_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Product Service client

        Args:
            base_url: Product service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("product_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8215"

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"ProductClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription plan

        Args:
            plan_id: Plan ID

        Returns:
            Plan details if found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/product/plans/{plan_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Plan {plan_id} not found")
                return None
            logger.error(f"Failed to get plan: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return None

    async def validate_subscription(
        self,
        subscription_id: str,
        user_id: str
    ) -> bool:
        """
        Validate subscription

        Args:
            subscription_id: Subscription ID
            user_id: User ID

        Returns:
            True if subscription is valid
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/product/subscriptions/{subscription_id}"
            )
            response.raise_for_status()
            subscription = response.json()

            return (
                subscription.get("user_id") == user_id and
                subscription.get("status") == "active"
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            logger.error(f"Failed to validate subscription: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error validating subscription: {e}")
            return False

    async def get_user_subscriptions(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get user's subscriptions

        Args:
            user_id: User ID

        Returns:
            List of subscriptions
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/product/subscriptions/user/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            logger.error(f"Failed to get user subscriptions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if product service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
