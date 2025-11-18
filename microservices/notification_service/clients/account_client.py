"""
Account Service Client

HTTP client for synchronous communication with account_service
Provides methods to fetch user account information for notifications
"""

import httpx
import logging
from typing import Optional, Dict, Any
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AccountServiceClient:
    """Client for account_service HTTP API"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize account service client

        Args:
            config_manager: ConfigManager instance for service discovery
        """
        self.config_manager = config_manager or ConfigManager("notification_service")

        # Get account_service endpoint from Consul or use fallback
        self.base_url = self._get_service_url("account_service", "http://localhost:8202")

        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "X-Service-Name": "notification_service"  # Internal service identifier
            }
        )

        logger.info(f"AccountServiceClient initialized with base_url: {self.base_url}")

    def _get_service_url(self, service_name: str, fallback_url: str) -> str:
        """Get service URL from Consul or use fallback"""
        try:
            if self.config_manager:
                url = self.config_manager.get_service_endpoint(service_name)
                if url:
                    return url
        except Exception as e:
            logger.warning(f"Failed to get {service_name} from Consul: {e}")

        logger.info(f"Using fallback URL for {service_name}: {fallback_url}")
        return fallback_url

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information

        Args:
            user_id: User ID

        Returns:
            User profile dict or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/accounts/profile/{user_id}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"User profile not found: {user_id}")
                return None
            else:
                logger.error(f"Failed to get user profile {user_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching user profile {user_id}: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by email

        Args:
            email: User email address

        Returns:
            User profile dict or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/accounts/by-email/{email}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"User not found by email: {email}")
                return None
            else:
                logger.error(f"Failed to get user by email {email}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}")
            return None

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user notification preferences

        Args:
            user_id: User ID

        Returns:
            User preferences dict or None if not found
        """
        try:
            # Get full profile which includes preferences
            profile = await self.get_user_profile(user_id)

            if profile and "preferences" in profile:
                return profile["preferences"]

            return None

        except Exception as e:
            logger.error(f"Error fetching user preferences {user_id}: {e}")
            return None

    async def get_user_contact_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user contact information (email, phone)

        Args:
            user_id: User ID

        Returns:
            Contact info dict with email, phone, etc. or None if not found
        """
        try:
            profile = await self.get_user_profile(user_id)

            if profile:
                return {
                    "email": profile.get("email"),
                    "phone": profile.get("phone"),
                    "full_name": profile.get("full_name"),
                    "display_name": profile.get("display_name"),
                }

            return None

        except Exception as e:
            logger.error(f"Error fetching user contact info {user_id}: {e}")
            return None

    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
        logger.info("AccountServiceClient closed")
