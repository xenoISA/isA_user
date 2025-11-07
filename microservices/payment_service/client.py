"""
Payment Service Client

Client library for other microservices to interact with payment service
"""

import httpx
from core.config_manager import ConfigManager
import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class PaymentServiceClient:
    """Payment Service HTTP client"""

    def __init__(self, base_url: str = None, config: Optional[ConfigManager] = None):
        """
        Initialize Payment Service client

        Args:
            base_url: Payment service base URL, defaults to service discovery
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via ConfigManager
            if config is None:
                config = ConfigManager("payment_service_client")

            try:
                host, port = config.discover_service(
                    service_name='payment_service',
                    default_host='localhost',
                    default_port=8207,
                    env_host_key='PAYMENT_SERVICE_HOST',
                    env_port_key='PAYMENT_SERVICE_PORT'
                )
                self.base_url = f"http://{host}:{port}"
                logger.info(f"Payment service discovered at {self.base_url}")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8207"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Subscription Plans
    # =============================================================================

    async def create_plan(
        self,
        plan_name: str,
        price: float,
        interval: str,
        currency: str = "USD",
        features: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create subscription plan

        Args:
            plan_name: Plan name
            price: Plan price
            interval: Billing interval (monthly, yearly)
            currency: Currency code (default: USD)
            features: Plan features (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created plan

        Example:
            >>> client = PaymentServiceClient()
            >>> plan = await client.create_plan(
            ...     plan_name="Premium Plan",
            ...     price=29.99,
            ...     interval="monthly",
            ...     features=["unlimited_storage", "priority_support"]
            ... )
        """
        try:
            payload = {
                "plan_name": plan_name,
                "price": price,
                "interval": interval,
                "currency": currency
            }

            if features:
                payload["features"] = features
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/plans",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create plan: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            return None

    async def get_plan(
        self,
        plan_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get subscription plan details

        Args:
            plan_id: Plan ID

        Returns:
            Plan details

        Example:
            >>> plan = await client.get_plan("plan123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/plans/{plan_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get plan: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return None

    async def list_plans(
        self
    ) -> Optional[List[Dict[str, Any]]]:
        """
        List all subscription plans

        Returns:
            List of plans

        Example:
            >>> plans = await client.list_plans()
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/plans"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list plans: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing plans: {e}")
            return None

    # =============================================================================
    # Subscriptions
    # =============================================================================

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        payment_method_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create user subscription

        Args:
            user_id: User ID
            plan_id: Subscription plan ID
            payment_method_id: Payment method ID (optional)

        Returns:
            Created subscription

        Example:
            >>> subscription = await client.create_subscription(
            ...     user_id="user123",
            ...     plan_id="plan456"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "plan_id": plan_id
            }

            if payment_method_id:
                payload["payment_method_id"] = payment_method_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/subscriptions",
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

    async def get_user_subscription(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's active subscription

        Args:
            user_id: User ID

        Returns:
            User subscription

        Example:
            >>> subscription = await client.get_user_subscription("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/user/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            return None

    async def update_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update subscription

        Args:
            subscription_id: Subscription ID
            updates: Update data

        Returns:
            Updated subscription

        Example:
            >>> updated = await client.update_subscription(
            ...     subscription_id="sub123",
            ...     updates={"plan_id": "new_plan456"}
            ... )
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}",
                json=updates
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
        immediate: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Cancel subscription

        Args:
            subscription_id: Subscription ID
            immediate: Cancel immediately (default: False, cancel at period end)

        Returns:
            Cancelled subscription

        Example:
            >>> cancelled = await client.cancel_subscription("sub123")
        """
        try:
            payload = {"immediate": immediate}

            response = await self.client.post(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}/cancel",
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
    # Payments
    # =============================================================================

    async def create_payment_intent(
        self,
        user_id: str,
        amount: float,
        currency: str = "USD",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create payment intent

        Args:
            user_id: User ID
            amount: Payment amount
            currency: Currency code (default: USD)
            description: Payment description (optional)
            metadata: Additional metadata (optional)

        Returns:
            Payment intent

        Example:
            >>> intent = await client.create_payment_intent(
            ...     user_id="user123",
            ...     amount=99.99,
            ...     description="Premium subscription"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "amount": amount,
                "currency": currency
            }

            if description:
                payload["description"] = description
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/intent",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create payment intent: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating payment intent: {e}")
            return None

    async def confirm_payment(
        self,
        payment_id: str,
        payment_method_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Confirm payment

        Args:
            payment_id: Payment ID
            payment_method_id: Payment method ID (optional)

        Returns:
            Confirmed payment

        Example:
            >>> payment = await client.confirm_payment("pay123")
        """
        try:
            payload = {}
            if payment_method_id:
                payload["payment_method_id"] = payment_method_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/{payment_id}/confirm",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to confirm payment: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            return None

    async def get_payment_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get user payment history

        Args:
            user_id: User ID
            limit: Result limit (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            Payment history

        Example:
            >>> history = await client.get_payment_history("user123")
        """
        try:
            params = {"limit": limit, "offset": offset}

            response = await self.client.get(
                f"{self.base_url}/api/v1/payments/user/{user_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get payment history: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting payment history: {e}")
            return None

    # =============================================================================
    # Invoices
    # =============================================================================

    async def create_invoice(
        self,
        user_id: str,
        amount: float,
        description: str,
        currency: str = "USD",
        due_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create invoice

        Args:
            user_id: User ID
            amount: Invoice amount
            description: Invoice description
            currency: Currency code (default: USD)
            due_date: Invoice due date (optional)

        Returns:
            Created invoice

        Example:
            >>> invoice = await client.create_invoice(
            ...     user_id="user123",
            ...     amount=149.99,
            ...     description="Annual subscription"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "amount": amount,
                "description": description,
                "currency": currency
            }

            if due_date:
                payload["due_date"] = due_date

            response = await self.client.post(
                f"{self.base_url}/api/v1/invoices",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create invoice: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return None

    async def get_invoice(
        self,
        invoice_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get invoice details

        Args:
            invoice_id: Invoice ID

        Returns:
            Invoice details

        Example:
            >>> invoice = await client.get_invoice("inv123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/invoices/{invoice_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get invoice: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting invoice: {e}")
            return None

    async def pay_invoice(
        self,
        invoice_id: str,
        payment_method_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Pay invoice

        Args:
            invoice_id: Invoice ID
            payment_method_id: Payment method ID (optional)

        Returns:
            Payment result

        Example:
            >>> result = await client.pay_invoice("inv123")
        """
        try:
            payload = {}
            if payment_method_id:
                payload["payment_method_id"] = payment_method_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/invoices/{invoice_id}/pay",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to pay invoice: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error paying invoice: {e}")
            return None

    # =============================================================================
    # Refunds
    # =============================================================================

    async def create_refund(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create refund

        Args:
            payment_id: Payment ID to refund
            amount: Refund amount (optional, full refund if not specified)
            reason: Refund reason (optional)

        Returns:
            Created refund

        Example:
            >>> refund = await client.create_refund(
            ...     payment_id="pay123",
            ...     reason="Customer request"
            ... )
        """
        try:
            payload = {"payment_id": payment_id}

            if amount is not None:
                payload["amount"] = amount
            if reason:
                payload["reason"] = reason

            response = await self.client.post(
                f"{self.base_url}/api/v1/refunds",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create refund: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating refund: {e}")
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
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["PaymentServiceClient"]
