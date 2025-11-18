"""
Billing Service Client

HTTP client for synchronous communication with billing_service
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class BillingServiceClient:
    """Client for billing_service HTTP API"""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize billing service client

        Args:
            base_url: Base URL of billing service (e.g., "http://localhost:8009")
                     If None, will use service discovery via Consul
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or "http://billing_service:8009"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def get_subscription_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's subscription status

        Args:
            user_id: User ID

        Returns:
            Subscription data if found, None otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/billing/subscription/{user_id}"
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
            logger.error(f"Error calling billing_service.get_subscription_status: {e}")
            return None

    async def check_payment_status(self, user_id: str) -> Optional[str]:
        """
        Check user's payment status

        Args:
            user_id: User ID

        Returns:
            Payment status (e.g., "current", "overdue", "none") or None on error
        """
        try:
            subscription = await self.get_subscription_status(user_id)
            if subscription:
                return subscription.get("payment_status", "unknown")
            return "none"

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return None

    async def get_billing_history(
        self, user_id: str, limit: int = 10
    ) -> Optional[list]:
        """
        Get user's billing history

        Args:
            user_id: User ID
            limit: Maximum number of records to return

        Returns:
            List of billing records or None on error
        """
        try:
            url = f"{self.base_url}/api/v1/billing/history/{user_id}"
            params = {"limit": limit}
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json().get("history", [])
            else:
                logger.error(f"Failed to get billing history: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error calling billing_service.get_billing_history: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
