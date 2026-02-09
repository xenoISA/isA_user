"""
Inventory Service Client for Order Service
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class InventoryClient:
    """Client for inventory_service"""

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
                self.base_url = "http://localhost"

        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"InventoryClient initialized with base_url: {self.base_url}")

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def reserve(self, order_id: str, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        try:
            payload = {"order_id": order_id, "items": items}
            response = await self.client.post(f"{self.base_url}/api/v1/inventory/reserve", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to reserve inventory: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error reserving inventory: {e}")
            return None

    async def commit(self, order_id: str) -> bool:
        try:
            response = await self.client.post(f"{self.base_url}/api/v1/inventory/commit", json={"order_id": order_id})
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error committing inventory: {e}")
            return False

    async def release(self, order_id: str) -> bool:
        try:
            response = await self.client.post(f"{self.base_url}/api/v1/inventory/release", json={"order_id": order_id})
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error releasing inventory: {e}")
            return False
