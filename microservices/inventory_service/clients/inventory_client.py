"""
Inventory Service Client

Canonical typed HTTP client for inventory_service API.
Used by order_service, payment_service, and other consumers.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class InventoryClient:
    """Client for inventory_service API"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("inventory_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8252"

        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"InventoryClient initialized with base_url: {self.base_url}")

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def reserve(
        self, order_id: str, items: List[Dict[str, Any]], user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Reserve inventory for an order."""
        try:
            payload = {"order_id": order_id, "items": items}
            if user_id:
                payload["user_id"] = user_id
            response = await self.client.post(
                f"{self.base_url}/api/v1/inventory/reserve", json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to reserve inventory: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error reserving inventory: {e}")
            return None

    async def commit(
        self, order_id: str, reservation_id: Optional[str] = None
    ) -> bool:
        """Commit an inventory reservation (after payment)."""
        try:
            payload = {"order_id": order_id}
            if reservation_id:
                payload["reservation_id"] = reservation_id
            response = await self.client.post(
                f"{self.base_url}/api/v1/inventory/commit", json=payload
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error committing inventory: {e}")
            return False

    async def release(
        self, order_id: str, reservation_id: Optional[str] = None, reason: str = "manual_release"
    ) -> bool:
        """Release an inventory reservation."""
        try:
            payload = {"order_id": order_id, "reason": reason}
            if reservation_id:
                payload["reservation_id"] = reservation_id
            response = await self.client.post(
                f"{self.base_url}/api/v1/inventory/release", json=payload
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error releasing inventory: {e}")
            return False

    async def check_availability(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Check reservation status for an order."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/inventory/reservations/{order_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to check availability: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if inventory service is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
