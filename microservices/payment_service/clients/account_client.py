"""
Account Service Client for Payment Service

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
            self.config = None
        else:
            # Use ConfigManager for service discovery
            if config is None:
                from core.config_manager import ConfigManager
                config = ConfigManager("payment_service")

            self.config = config
            # Do service discovery on first use, not at init time
            self.base_url = None

        self.client = httpx.AsyncClient(timeout=30.0)

    def _get_base_url(self) -> str:
        """Get base URL with lazy service discovery"""
        if self.base_url:
            return self.base_url

        if self.config:
            try:
                host, port = self.config.discover_service(
                    service_name='account_service',
                    default_host='localhost',
                    default_port=8202,
                    env_host_key='ACCOUNT_SERVICE_HOST',
                    env_port_key='ACCOUNT_SERVICE_PORT'
                )
                self.base_url = f"http://{host}:{port}"
                logger.info(f"AccountClient discovered account_service at: {self.base_url}")
                return self.base_url
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8202"
                return self.base_url

        self.base_url = "http://localhost:8202"
        return self.base_url

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
            User profile if found, None otherwise
        """
        try:
            base_url = self._get_base_url()
            response = await self.client.get(
                f"{base_url}/api/v1/accounts/profile/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"User {user_id} not found in account service")
                return None
            logger.error(f"Failed to get user profile: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User data if found, None otherwise
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

    async def get_payment_methods(self, user_id: str) -> Optional[list]:
        """
        Get user's payment methods

        Args:
            user_id: User ID

        Returns:
            List of payment methods if found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/account/users/{user_id}/payment-methods"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            logger.error(f"Failed to get payment methods: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if account service is healthy"""
        try:
            base_url = self._get_base_url()
            response = await self.client.get(f"{base_url}/health")
            return response.status_code == 200
        except:
            return False
