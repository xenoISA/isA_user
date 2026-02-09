"""
Account Service Client

Client for authorization_service to interact with account_service.
Used for validating user existence and retrieving user info for authorization.
"""

import os
import sys
from typing import Optional

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.account_service.client import AccountServiceClient


class AccountClient:
    """
    Wrapper client for Account Service calls from Authorization Service.

    This wrapper provides authorization-specific convenience methods
    while delegating to the actual AccountServiceClient.
    """

    def __init__(self, base_url: str = None, config=None):
        """
        Initialize Account Service client

        Args:
            base_url: Account service base URL (optional, uses service discovery)
            config: ConfigManager instance for service discovery
        """
        self._client = AccountServiceClient(base_url=base_url, config=config)

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Authorization-specific convenience methods
    # =============================================================================

    async def validate_user_exists(self, user_id: str) -> bool:
        """
        Validate that a user exists in the system.

        Used before granting or checking permissions.

        Args:
            user_id: User ID to validate

        Returns:
            True if user exists, False otherwise
        """
        try:
            profile = await self._client.get_account_profile(user_id)
            return profile is not None
        except Exception:
            return False

    async def get_user_info(self, user_id: str) -> Optional[dict]:
        """
        Get user information for authorization context.

        Args:
            user_id: User ID

        Returns:
            User account profile or None
        """
        try:
            return await self._client.get_account_profile(user_id)
        except Exception:
            return None

    async def check_user_active(self, user_id: str) -> bool:
        """
        Check if user account is active.

        Prevents authorization for suspended/deleted accounts.

        Args:
            user_id: User ID

        Returns:
            True if user is active, False otherwise
        """
        try:
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return False

            status = user_info.get("status", "").lower()
            return status == "active"
        except Exception:
            return False

    async def get_user_subscription_status(self, user_id: str) -> Optional[str]:
        """
        Get user subscription status for permission checks.

        Some permissions may be tied to subscription level.

        Args:
            user_id: User ID

        Returns:
            Subscription status string or None
        """
        try:
            profile = await self._client.get_account_profile(user_id)
            if profile:
                return profile.get("subscription_status")
            return None
        except Exception:
            return None

    # =============================================================================
    # Direct delegation to AccountServiceClient
    # =============================================================================

    async def get_account_profile(self, user_id: str):
        """Get full account profile (delegates to AccountServiceClient)"""
        return await self._client.get_account_profile(user_id)

    async def health_check(self) -> bool:
        """Check Account Service health"""
        return await self._client.health_check()


__all__ = ["AccountClient"]
