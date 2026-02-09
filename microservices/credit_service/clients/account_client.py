"""
Account Service HTTP Client

Provides async HTTP client for communicating with account_service.
Implements AccountClientProtocol for dependency injection.
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AccountClient:
    """Async HTTP client for account_service"""

    def __init__(self, base_url: str = "http://localhost:8202", config=None):
        """
        Initialize AccountClient

        Args:
            base_url: Base URL for account_service
            config: ConfigManager instance for dynamic configuration
        """
        if config:
            base_url = config.get("ACCOUNT_SERVICE_URL", base_url)
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"AccountClient initialized with base_url: {self.base_url}")

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user from account_service

        Args:
            user_id: User identifier

        Returns:
            User data dictionary or None if not found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                logger.info(f"User not found: {user_id}")
                return None
            response.raise_for_status()
            logger.debug(f"Successfully retrieved user: {user_id}")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting user {user_id}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error getting user {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user {user_id}: {e}", exc_info=True)
            return None

    async def validate_user(self, user_id: str) -> bool:
        """
        Validate user exists and is active

        Args:
            user_id: User identifier

        Returns:
            True if user exists and is active, False otherwise
        """
        user = await self.get_user(user_id)
        if user is None:
            logger.debug(f"User validation failed - user not found: {user_id}")
            return False

        is_valid = user.get("is_active", False)
        if is_valid:
            logger.debug(f"User validated successfully: {user_id}")
        else:
            logger.debug(f"User validation failed - user inactive: {user_id}")

        return is_valid

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()
        logger.info("AccountClient connection closed")
