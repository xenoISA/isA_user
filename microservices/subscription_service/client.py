"""
Subscription Service Client

Client library for other microservices to interact with subscription service.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)


class SubscriptionServiceClient:
    """Subscription Service HTTP client"""

    def __init__(self, base_url: str = None, config=None):
        """
        Initialize Subscription Service client

        Args:
            base_url: Subscription service base URL, defaults to service discovery via ConfigManager
            config: Optional ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
            self.config = None
        else:
            if config is None:
                from core.config_manager import ConfigManager
                config = ConfigManager("subscription_service_client")

            self.config = config
            self.base_url = None

        self.client = httpx.AsyncClient(timeout=30.0)

    def _get_base_url(self) -> str:
        """Get base URL with lazy service discovery"""
        if self.base_url:
            return self.base_url

        if self.config:
            try:
                host, port = self.config.discover_service(
                    service_name='subscription_service',
                    default_host='localhost',
                    default_port=8228,
                    env_host_key='SUBSCRIPTION_SERVICE_HOST',
                    env_port_key='SUBSCRIPTION_SERVICE_PORT'
                )
                return f"http://{host}:{port}"
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                return "http://localhost:8228"

        return "http://localhost:8228"

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Subscription Management
    # =============================================================================

    async def create_subscription(
        self,
        user_id: str,
        tier_code: str = "free",
        organization_id: Optional[str] = None,
        billing_cycle: str = "monthly",
        payment_method_id: Optional[str] = None,
        seats: int = 1,
        use_trial: bool = False,
        promo_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new subscription for a user

        Args:
            user_id: User ID
            tier_code: Subscription tier (free, pro, max, team, enterprise)
            organization_id: Optional organization ID
            billing_cycle: Billing cycle (monthly, yearly, quarterly)
            payment_method_id: Payment method ID
            seats: Number of seats (for team/enterprise)
            use_trial: Whether to start with a trial
            promo_code: Promotional code
            metadata: Additional metadata

        Returns:
            CreateSubscriptionResponse data

        Example:
            >>> client = SubscriptionServiceClient()
            >>> result = await client.create_subscription(
            ...     user_id="user123",
            ...     tier_code="free"
            ... )
            >>> print(f"Subscription ID: {result['subscription']['subscription_id']}")
        """
        try:
            payload = {
                "user_id": user_id,
                "tier_code": tier_code,
                "billing_cycle": billing_cycle,
                "seats": seats,
                "use_trial": use_trial
            }
            if organization_id:
                payload["organization_id"] = organization_id
            if payment_method_id:
                payload["payment_method_id"] = payment_method_id
            if promo_code:
                payload["promo_code"] = promo_code
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self._get_base_url()}/api/v1/subscriptions",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription by ID

        Args:
            subscription_id: Subscription ID

        Returns:
            SubscriptionResponse data
        """
        try:
            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/subscriptions/{subscription_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription for a user

        Args:
            user_id: User ID

        Returns:
            SubscriptionResponse data with subscription details

        Example:
            >>> result = await client.get_user_subscription("user123")
            >>> if result and result.get('subscription'):
            ...     print(f"Tier: {result['subscription']['tier_code']}")
            ...     print(f"Credits: {result['subscription']['credits_remaining']}")
        """
        try:
            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/users/{user_id}/subscription"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get user subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            return None

    async def update_subscription(
        self,
        subscription_id: str,
        tier_code: Optional[str] = None,
        billing_cycle: Optional[str] = None,
        seats: Optional[int] = None,
        auto_renew: Optional[bool] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a subscription

        Args:
            subscription_id: Subscription ID
            tier_code: New tier code
            billing_cycle: New billing cycle
            seats: New seat count
            auto_renew: Auto-renew setting
            payment_method_id: Payment method ID
            metadata: Additional metadata

        Returns:
            Updated SubscriptionResponse data
        """
        try:
            update_data = {}
            if tier_code is not None:
                update_data["tier_code"] = tier_code
            if billing_cycle is not None:
                update_data["billing_cycle"] = billing_cycle
            if seats is not None:
                update_data["seats"] = seats
            if auto_renew is not None:
                update_data["auto_renew"] = auto_renew
            if payment_method_id is not None:
                update_data["payment_method_id"] = payment_method_id
            if metadata is not None:
                update_data["metadata"] = metadata

            if not update_data:
                logger.warning("No update data provided")
                return None

            response = await self.client.put(
                f"{self._get_base_url()}/api/v1/subscriptions/{subscription_id}",
                json=update_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return None

    async def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False,
        reason: Optional[str] = None,
        feedback: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cancel a subscription

        Args:
            subscription_id: Subscription ID
            immediate: If True, cancel immediately; if False, cancel at period end
            reason: Cancellation reason
            feedback: User feedback

        Returns:
            CancelSubscriptionResponse data
        """
        try:
            payload = {"immediate": immediate}
            if reason:
                payload["reason"] = reason
            if feedback:
                payload["feedback"] = feedback

            response = await self.client.post(
                f"{self._get_base_url()}/api/v1/subscriptions/{subscription_id}/cancel",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            return None

    # =============================================================================
    # Credit Management
    # =============================================================================

    async def get_credit_balance(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get credit balance for a user

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            CreditBalanceResponse data

        Example:
            >>> balance = await client.get_credit_balance("user123")
            >>> print(f"Credits available: {balance['total_credits_available']}")
        """
        try:
            params = {"user_id": user_id}
            if organization_id:
                params["organization_id"] = organization_id

            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/credits/balance",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get credit balance: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting credit balance: {e}")
            return None

    async def consume_credits(
        self,
        user_id: str,
        credits_to_consume: int,
        service_type: str,
        organization_id: Optional[str] = None,
        usage_record_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Consume credits from a user's subscription

        Args:
            user_id: User ID
            credits_to_consume: Number of credits to consume
            service_type: Type of service (model_inference, storage_minio, etc.)
            organization_id: Optional organization ID
            usage_record_id: Optional usage record ID
            description: Optional description
            metadata: Additional metadata

        Returns:
            ConsumeCreditsResponse data

        Example:
            >>> result = await client.consume_credits(
            ...     user_id="user123",
            ...     credits_to_consume=100,
            ...     service_type="model_inference"
            ... )
            >>> print(f"Remaining: {result['credits_remaining']}")
        """
        try:
            payload = {
                "user_id": user_id,
                "credits_to_consume": credits_to_consume,
                "service_type": service_type
            }
            if organization_id:
                payload["organization_id"] = organization_id
            if usage_record_id:
                payload["usage_record_id"] = usage_record_id
            if description:
                payload["description"] = description
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self._get_base_url()}/api/v1/credits/consume",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to consume credits: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            return None

    # =============================================================================
    # History & Stats
    # =============================================================================

    async def get_subscription_history(
        self,
        subscription_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get subscription history

        Args:
            subscription_id: Subscription ID
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            SubscriptionHistoryResponse data
        """
        try:
            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/subscriptions/{subscription_id}/history",
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get subscription history: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting subscription history: {e}")
            return None

    async def get_subscription_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get subscription service statistics

        Returns:
            SubscriptionStatsResponse data
        """
        try:
            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/subscriptions/stats"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get subscription stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self._get_base_url()}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["SubscriptionServiceClient"]
