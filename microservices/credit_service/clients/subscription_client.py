"""
Subscription Service HTTP Client

Provides async HTTP client for communicating with subscription_service.
Implements SubscriptionClientProtocol for dependency injection.
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SubscriptionClient:
    """Async HTTP client for subscription_service"""

    def __init__(self, base_url: str = "http://localhost:8228", config=None):
        """
        Initialize SubscriptionClient

        Args:
            base_url: Base URL for subscription_service
            config: ConfigManager instance for dynamic configuration
        """
        if config:
            base_url = config.get("SUBSCRIPTION_SERVICE_URL", base_url)
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"SubscriptionClient initialized with base_url: {self.base_url}")

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active subscription for user

        Args:
            user_id: User identifier

        Returns:
            Subscription data dictionary or None if not found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/user/{user_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                logger.info(f"Subscription not found for user: {user_id}")
                return None
            response.raise_for_status()
            logger.debug(f"Successfully retrieved subscription for user: {user_id}")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting subscription for user {user_id}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error getting subscription for user {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting subscription for user {user_id}: {e}", exc_info=True)
            return None

    async def get_subscription_credits(self, subscription_id: str) -> Optional[int]:
        """
        Get credits included in subscription plan

        Args:
            subscription_id: Subscription identifier

        Returns:
            Number of credits included or None if subscription not found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                logger.info(f"Subscription not found: {subscription_id}")
                return None
            response.raise_for_status()
            data = response.json()
            credits = data.get("credits_included", 0)
            logger.debug(f"Subscription {subscription_id} includes {credits} credits")
            return credits
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting subscription credits {subscription_id}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error getting subscription credits {subscription_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting subscription credits {subscription_id}: {e}", exc_info=True)
            return None

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()
        logger.info("SubscriptionClient connection closed")
