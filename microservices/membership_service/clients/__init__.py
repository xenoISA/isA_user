"""
Membership Service Clients

HTTP clients for external service calls.
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AccountClient:
    """Sync HTTP client for account_service"""

    def __init__(self, base_url: str = "http://localhost:8202"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from account_service (optional validation)"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to validate user {user_id}: {e}")
            return None  # Graceful degradation

    async def close(self):
        await self.client.aclose()


__all__ = ["AccountClient"]
