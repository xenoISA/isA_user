"""
Account Service Client for Order Service

HTTP client for synchronous communication with account_service
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AccountClient:
    """Client for account_service"""

    def __init__(self, base_url: Optional[str] = None, config=None):
        """
        Initialize Account Service client

        Args:
            base_url: Account service base URL
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via Consul
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("account_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8200"

        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"AccountClient initialized with base_url: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user account profile

        Args:
            user_id: User ID

        Returns:
            User profile if found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/account/users/{user_id}/profile"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"User {user_id} not found")
                return None
            logger.error(f"Failed to get account profile: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting account profile: {e}")
            return None

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User data if found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/account/users/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"User {user_id} not found")
                return None
            logger.error(f"Failed to get user: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    async def get_user_tier(self, user_id: str) -> Optional[str]:
        """
        Get user subscription tier

        Args:
            user_id: User ID

        Returns:
            User tier (basic, premium, enterprise, etc.)
        """
        profile = await self.get_account_profile(user_id)
        if profile:
            return profile.get('tier', 'basic')
        return None

    async def validate_user(self, user_id: str) -> bool:
        """
        Validate if user exists

        Args:
            user_id: User ID

        Returns:
            True if user exists
        """
        user = await self.get_user(user_id)
        return user is not None

    async def health_check(self) -> bool:
        """Check if account service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
