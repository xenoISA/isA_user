"""
Billing Service Client for Payment Service

HTTP client for synchronous communication with billing_service
"""

import httpx
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class BillingClient:
    """Client for billing_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Billing Service client

        Args:
            base_url: Billing service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("billing_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8211"

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"BillingClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create_billing_record(
        self,
        user_id: str,
        amount: Decimal,
        currency: str = "USD",
        payment_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create billing record

        Args:
            user_id: User ID
            amount: Amount
            currency: Currency code
            payment_id: Payment ID
            subscription_id: Subscription ID
            description: Description

        Returns:
            Created billing record
        """
        try:
            payload = {
                "user_id": user_id,
                "amount": float(amount),
                "currency": currency,
                "payment_id": payment_id,
                "subscription_id": subscription_id,
                "description": description,
                "timestamp": datetime.utcnow().isoformat()
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/billing/records",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create billing record: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating billing record: {e}")
            return None

    async def get_billing_history(
        self,
        user_id: str,
        limit: int = 100
    ) -> Optional[list]:
        """
        Get billing history for user

        Args:
            user_id: User ID
            limit: Maximum records to return

        Returns:
            List of billing records
        """
        try:
            params = {"limit": limit}
            response = await self.client.get(
                f"{self.base_url}/api/v1/billing/users/{user_id}/history",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            logger.error(f"Failed to get billing history: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting billing history: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if billing service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
