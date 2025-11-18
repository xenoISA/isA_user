"""
Payment Service Client for Order Service

HTTP client for synchronous communication with payment_service
"""

import httpx
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class PaymentClient:
    """Client for payment_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Payment Service client

        Args:
            base_url: Payment service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("payment_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost"

        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"PaymentClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create_payment_intent(
        self,
        user_id: str,
        amount: Decimal,
        currency: str = "USD",
        order_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create payment intent

        Args:
            user_id: User ID
            amount: Payment amount
            currency: Currency code
            order_id: Associated order ID
            metadata: Additional metadata

        Returns:
            Payment intent data if successful
        """
        try:
            payload = {
                "user_id": user_id,
                "amount": float(amount),
                "currency": currency,
                "metadata": metadata or {}
            }

            if order_id:
                payload["metadata"]["order_id"] = order_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/payment/intents",
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

    async def get_payment_status(self, payment_intent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment status

        Args:
            payment_intent_id: Payment intent ID

        Returns:
            Payment status data
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/payment/intents/{payment_intent_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Payment intent {payment_intent_id} not found")
                return None
            logger.error(f"Failed to get payment status: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            return None

    async def cancel_payment(self, payment_intent_id: str) -> bool:
        """
        Cancel payment intent

        Args:
            payment_intent_id: Payment intent ID

        Returns:
            True if successful
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/payment/intents/{payment_intent_id}/cancel"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel payment: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error canceling payment: {e}")
            return False

    async def create_refund(
        self,
        payment_id: str,
        amount: Decimal,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create refund

        Args:
            payment_id: Payment ID
            amount: Refund amount
            reason: Refund reason

        Returns:
            Refund data if successful
        """
        try:
            payload = {
                "payment_id": payment_id,
                "amount": float(amount),
                "reason": reason
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/payment/refunds",
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

    async def health_check(self) -> bool:
        """Check if payment service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
