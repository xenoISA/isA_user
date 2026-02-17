"""
Subscription Service Client for Billing Service

Handles subscription-related operations: credit balance, credit consumption, tier info
"""

import logging
import httpx
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SubscriptionClient:
    """Client for communicating with Subscription Service"""

    def __init__(self, base_url: str = "http://subscription:8228"):
        """
        Initialize Subscription Service client

        Args:
            base_url: Subscription service base URL
        """
        self.base_url = base_url
        self.timeout = 10.0
        logger.info(f"✅ SubscriptionClient initialized with base URL: {base_url}")

    async def get_credit_balance(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's credit balance from subscription

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            Credit balance info dict or None if failed
        """
        try:
            params = {"user_id": user_id}
            if organization_id:
                params["organization_id"] = organization_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/credits/balance",
                    params=params
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.info(f"No subscription found for user {user_id}")
                    return None
                else:
                    logger.warning(
                        f"Failed to get credit balance: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Failed to get credit balance for user {user_id}: {e}")
            return None

    async def get_subscription_credits(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> int:
        """
        Get available subscription credits

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            Available credits (int), 0 if none
        """
        try:
            balance = await self.get_credit_balance(user_id, organization_id)
            if balance and balance.get("success"):
                return balance.get("subscription_credits_remaining", 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting subscription credits: {e}")
            return 0

    async def consume_credits(
        self,
        user_id: str,
        credits_amount: int,
        service_type: str,
        description: Optional[str] = None,
        usage_record_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Consume credits from user's subscription

        Args:
            user_id: User ID
            credits_amount: Amount of credits to consume
            service_type: Type of service (e.g., model_inference, storage_minio)
            description: Transaction description
            usage_record_id: Optional usage record reference
            organization_id: Optional organization ID
            metadata: Additional metadata

        Returns:
            Consumption result dict or None if failed
        """
        try:
            payload = {
                "user_id": user_id,
                "credits_to_consume": credits_amount,
                "service_type": service_type,
            }

            if description:
                payload["description"] = description
            if usage_record_id:
                payload["usage_record_id"] = usage_record_id
            if organization_id:
                payload["organization_id"] = organization_id
            if metadata:
                payload["metadata"] = metadata

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/credits/consume",
                    json=payload
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 402:
                    # Insufficient credits
                    result = response.json()
                    logger.warning(
                        f"Insufficient subscription credits for user {user_id}"
                    )
                    return {"success": False, "message": result.get("detail", "Insufficient credits")}
                elif response.status_code == 404:
                    logger.warning(f"No active subscription for user {user_id}")
                    return {"success": False, "message": "No active subscription"}
                else:
                    logger.warning(
                        f"Failed to consume credits: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Failed to consume credits for user {user_id}: {e}")
            return None

    async def get_user_subscription(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's active subscription

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            Subscription info dict or None if not found
        """
        try:
            params = {}
            if organization_id:
                params["organization_id"] = organization_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/users/{user_id}/subscription",
                    params=params if params else None
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    logger.warning(
                        f"Failed to get subscription: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Failed to get subscription for user {user_id}: {e}")
            return None

    async def get_subscription_tier_info(
        self,
        tier_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get subscription tier information

        Args:
            tier_code: Tier code (e.g., 'free', 'pro', 'max')

        Returns:
            Tier info dict or None if not found
        """
        try:
            # This would call the product service for tier definitions
            # For now, return basic tier info from subscription service
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/tiers/{tier_code}"
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return None

        except Exception as e:
            logger.error(f"Failed to get tier info for {tier_code}: {e}")
            return None


__all__ = ["SubscriptionClient"]
