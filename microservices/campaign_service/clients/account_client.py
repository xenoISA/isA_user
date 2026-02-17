"""
Account Service Client

Client for calling account_service to get user data.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AccountClient:
    """Client for account_service"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("campaign_service")

        host, port = config.discover_service(
            service_name='account_service',
            default_host='localhost',
            default_port=8200,
            env_host_key='ACCOUNT_SERVICE_HOST',
            env_port_key='ACCOUNT_SERVICE_PORT'
        )
        self.base_url = f"http://{host}:{port}"
        self.timeout = 30.0

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user communication preferences.

        Returns user's channel preferences for email, SMS, etc.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/accounts/{user_id}/preferences"
                )
                response.raise_for_status()
                data = response.json()
                return data.get("preferences", {})

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"User not found: {user_id}")
                return {}
            logger.error(f"Error getting user preferences: {e}")
            raise

        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {e}")
            return {}

    async def check_channel_eligibility(
        self,
        user_id: str,
        channel_type: str,
    ) -> bool:
        """
        Check if user is eligible for a channel.

        Checks:
        - Valid contact info (email, phone, etc)
        - User has opted in
        - Channel not blocked
        """
        try:
            preferences = await self.get_user_preferences(user_id)

            channel_prefs = {
                "email": "email_opted_in",
                "sms": "sms_opted_in",
                "whatsapp": "whatsapp_opted_in",
                "in_app": "in_app_enabled",
                "webhook": None,  # Always eligible
            }

            pref_key = channel_prefs.get(channel_type)

            if pref_key is None:
                return True  # Default eligible for unknown channels

            return preferences.get(pref_key, False)

        except Exception as e:
            logger.error(f"Error checking channel eligibility: {e}")
            return False

    async def get_user_contact_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user contact information.

        Returns email, phone, etc.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/accounts/{user_id}"
                )
                response.raise_for_status()
                data = response.json()

                account = data.get("account", {})
                return {
                    "email": account.get("email"),
                    "phone": account.get("phone"),
                    "first_name": account.get("first_name"),
                    "last_name": account.get("last_name"),
                    "timezone": account.get("timezone", "UTC"),
                }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"User not found: {user_id}")
                return {}
            logger.error(f"Error getting user contact info: {e}")
            raise

        except Exception as e:
            logger.error(f"Error getting contact info for {user_id}: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if account_service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


__all__ = ["AccountClient"]
