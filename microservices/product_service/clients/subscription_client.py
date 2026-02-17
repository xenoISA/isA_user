"""
Subscription Service Client

Client for product_service to interact with subscription_service.
Used for checking subscription status for product access.
"""

import os
import sys
from typing import Optional, Dict, Any, List

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.subscription_service.client import SubscriptionServiceClient


class SubscriptionClient:
    """
    Wrapper client for Subscription Service calls from Product Service.

    This wrapper provides product-specific convenience methods
    while delegating to the actual SubscriptionServiceClient.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize Subscription Service client

        Args:
            base_url: Subscription service base URL (optional, uses service discovery)
        """
        self._client = SubscriptionServiceClient(base_url=base_url)

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Product-specific convenience methods
    # =============================================================================

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's active subscription.

        Args:
            user_id: User ID

        Returns:
            Subscription details or None
        """
        try:
            return await self._client.get_subscription(user_id)
        except Exception:
            return None

    async def check_user_has_subscription(self, user_id: str) -> bool:
        """
        Check if user has an active subscription.

        Args:
            user_id: User ID

        Returns:
            True if user has active subscription
        """
        try:
            subscription = await self._client.get_subscription(user_id)
            if subscription:
                status = subscription.get("status", "").lower()
                return status == "active"
            return False
        except Exception:
            return False

    async def check_product_access(
        self,
        user_id: str,
        product_id: str
    ) -> bool:
        """
        Check if user's subscription includes access to a product.

        Args:
            user_id: User ID
            product_id: Product ID

        Returns:
            True if user has access to the product
        """
        try:
            subscription = await self._client.get_subscription(user_id)
            if not subscription:
                return False

            if subscription.get("status") != "active":
                return False

            # Check if product is included in subscription
            included_products = subscription.get("included_products", [])
            return product_id in included_products
        except Exception:
            return False

    async def get_subscription_tier(self, user_id: str) -> str:
        """
        Get user's subscription tier/plan.

        Args:
            user_id: User ID

        Returns:
            Subscription tier (free, basic, premium, enterprise)
        """
        try:
            subscription = await self._client.get_subscription(user_id)
            if subscription:
                return subscription.get("plan", "free")
            return "free"
        except Exception:
            return "free"

    async def check_feature_access(
        self,
        user_id: str,
        feature_name: str
    ) -> bool:
        """
        Check if user's subscription includes a specific feature.

        Args:
            user_id: User ID
            feature_name: Feature name to check

        Returns:
            True if user has access to the feature
        """
        try:
            subscription = await self._client.get_subscription(user_id)
            if not subscription:
                return False

            if subscription.get("status") != "active":
                return False

            features = subscription.get("features", [])
            return feature_name in features
        except Exception:
            return False

    async def get_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage limits based on user's subscription.

        Args:
            user_id: User ID

        Returns:
            Dict with usage limits
        """
        try:
            subscription = await self._client.get_subscription(user_id)
            if subscription:
                return subscription.get("usage_limits", {})
            return {}
        except Exception:
            return {}

    # =============================================================================
    # Direct delegation to SubscriptionServiceClient
    # =============================================================================

    async def get_subscription(self, user_id: str):
        """Get subscription details"""
        return await self._client.get_subscription(user_id)

    async def health_check(self) -> bool:
        """Check Subscription Service health"""
        return await self._client.health_check()


__all__ = ["SubscriptionClient"]
