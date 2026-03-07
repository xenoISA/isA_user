"""
Fulfillment Service Client

Canonical typed HTTP client for fulfillment_service API.
Used by order_service, payment_service, and other consumers.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class FulfillmentClient:
    """Client for fulfillment_service API"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("fulfillment_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8254"

        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"FulfillmentClient initialized with base_url: {self.base_url}")

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create_shipment(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        address: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a shipment for an order."""
        try:
            payload = {"order_id": order_id, "items": items, "address": address}
            if user_id:
                payload["user_id"] = user_id
            response = await self.client.post(
                f"{self.base_url}/api/v1/fulfillment/shipments", json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create shipment: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating shipment: {e}")
            return None

    async def get_shipment(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get shipment for an order."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/fulfillment/shipments/{order_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get shipment: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting shipment: {e}")
            return None

    async def get_tracking(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Get tracking info by tracking number."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/fulfillment/tracking/{tracking_number}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get tracking: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting tracking: {e}")
            return None

    async def create_label(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Create a shipping label for a shipment."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/fulfillment/shipments/{shipment_id}/label"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to create label: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating label: {e}")
            return None

    async def cancel_shipment(
        self, shipment_id: str, reason: str = "manual_cancellation"
    ) -> Optional[Dict[str, Any]]:
        """Cancel a shipment."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/fulfillment/shipments/{shipment_id}/cancel",
                json={"reason": reason},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to cancel shipment: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error canceling shipment: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if fulfillment service is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
