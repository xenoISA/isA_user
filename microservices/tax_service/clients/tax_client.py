"""
Tax Service Client

Canonical typed HTTP client for tax_service API.
Used by order_service, payment_service, and other consumers.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class TaxClient:
    """Client for tax_service API"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("tax_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8253"

        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"TaxClient initialized with base_url: {self.base_url}")

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def calculate(
        self,
        items: List[Dict[str, Any]],
        address: Dict[str, Any],
        currency: str = "USD",
        order_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Calculate tax for items."""
        try:
            payload = {
                "items": items,
                "address": address,
                "currency": currency,
            }
            if order_id:
                payload["order_id"] = order_id
            if user_id:
                payload["user_id"] = user_id
            response = await self.client.post(
                f"{self.base_url}/api/v1/tax/calculate", json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to calculate tax: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error calculating tax: {e}")
            return None

    async def get_calculation(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get tax calculation for an order."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/tax/calculations/{order_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get tax calculation: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting tax calculation: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if tax service is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
