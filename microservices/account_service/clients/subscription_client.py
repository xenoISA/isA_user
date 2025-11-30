"""
Subscription Service Client

HTTP client for synchronous communication with subscription_service
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class SubscriptionServiceClient:
    """Client for subscription_service HTTP API"""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize subscription service client

        Args:
            base_url: Base URL of subscription service (e.g., "http://localhost:8228")
                     If None, will use default K8s service name
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or "http://subscription:8228"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's subscription

        Args:
            user_id: User ID

        Returns:
            Subscription data if found, None otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/users/{user_id}/subscription"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"No subscription found for user: {user_id}")
                return None
            else:
                logger.error(
                    f"Failed to get subscription for {user_id}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error calling subscription_service.get_user_subscription: {e}")
            return None

    async def create_subscription(
        self,
        user_id: str,
        tier_code: str = "free",
        billing_cycle: str = "monthly"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a subscription for a user

        Args:
            user_id: User ID
            tier_code: Subscription tier (free, pro, max, team, enterprise)
            billing_cycle: Billing cycle (monthly, yearly, quarterly)

        Returns:
            Created subscription data if successful, None otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/subscriptions"
            payload = {
                "user_id": user_id,
                "tier_code": tier_code,
                "billing_cycle": billing_cycle
            }
            response = await self.client.post(url, json=payload)

            if response.status_code in (200, 201):
                return response.json()
            else:
                logger.error(
                    f"Failed to create subscription for {user_id}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error calling subscription_service.create_subscription: {e}")
            return None

    async def get_or_create_subscription(
        self,
        user_id: str,
        tier_code: str = "free"
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing subscription or create a new one if not exists

        Args:
            user_id: User ID
            tier_code: Default tier code for new subscription

        Returns:
            Subscription data (existing or newly created)
        """
        # First try to get existing subscription
        result = await self.get_user_subscription(user_id)
        if result and result.get("subscription"):
            return result

        # No subscription found, create one
        logger.info(f"Creating default subscription for user: {user_id}")
        return await self.create_subscription(user_id, tier_code)

    async def get_subscription_tier(self, user_id: str) -> Optional[str]:
        """
        Get user's subscription tier code

        Args:
            user_id: User ID

        Returns:
            Tier code (e.g., "free", "pro", "max") or None on error
        """
        try:
            result = await self.get_user_subscription(user_id)
            if result and result.get("subscription"):
                return result["subscription"].get("tier_code", "free")
            return "free"  # Default to free if no subscription

        except Exception as e:
            logger.error(f"Error getting subscription tier: {e}")
            return "free"

    async def get_credit_balance(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's credit balance

        Args:
            user_id: User ID

        Returns:
            Credit balance data if found, None otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/credits/balance"
            params = {"user_id": user_id}
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get credit balance: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error calling subscription_service.get_credit_balance: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
