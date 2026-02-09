"""
Account Service Client

Client for album_service to interact with account_service.
Used for validating user existence for album operations.
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
    Wrapper client for Account Service calls from Album Service.

    This wrapper provides album-specific convenience methods
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
    # Album-specific convenience methods
    # =============================================================================

    async def validate_user_exists(self, user_id: str) -> bool:
        """
        Validate that a user exists in the system.

        Used before album creation and photo operations.

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
        Get user information for album context.

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

        Prevents album operations for suspended/deleted accounts.

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

    async def can_user_share_album(self, user_id: str) -> bool:
        """
        Check if user can share albums (based on subscription).

        Args:
            user_id: User ID

        Returns:
            True if user can share albums
        """
        try:
            profile = await self._client.get_account_profile(user_id)
            if profile:
                # Only paid plans can share albums
                subscription = profile.get("subscription_plan", "free")
                return subscription != "free"
            return False
        except Exception:
            return False

    async def get_user_album_limit(self, user_id: str) -> int:
        """
        Get maximum number of albums user can create.

        Args:
            user_id: User ID

        Returns:
            Maximum album count (-1 for unlimited)
        """
        try:
            profile = await self._client.get_account_profile(user_id)
            if profile:
                subscription = profile.get("subscription_plan", "free")
                limits = {
                    "free": 5,
                    "basic": 50,
                    "premium": 500,
                    "enterprise": -1  # Unlimited
                }
                return limits.get(subscription, 5)
            return 5
        except Exception:
            return 5

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
