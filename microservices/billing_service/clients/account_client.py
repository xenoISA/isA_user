"""
Account Service Client

Client for billing_service to interact with account_service.
Used for validating user existence and getting user info for billing.
"""

import os
import sys
from typing import Optional, Dict, Any

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.account_service.client import AccountServiceClient


class AccountClient:
    """
    Wrapper client for Account Service calls from Billing Service.

    This wrapper provides billing-specific convenience methods
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
    # Billing-specific convenience methods
    # =============================================================================

    async def validate_user_exists(self, user_id: str) -> bool:
        """
        Validate that a user exists in the system.

        Used before creating billing records.

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
        Get user information for billing context.

        Args:
            user_id: User ID

        Returns:
            User account profile or None
        """
        try:
            return await self._client.get_account_profile(user_id)
        except Exception:
            return None

    async def get_user_email(self, user_id: str) -> Optional[str]:
        """
        Get user email for billing notifications.

        Args:
            user_id: User ID

        Returns:
            User email or None
        """
        try:
            profile = await self._client.get_account_profile(user_id)
            if profile:
                return profile.get("email")
            return None
        except Exception:
            return None

    async def get_user_subscription_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user subscription information for billing calculations.

        Args:
            user_id: User ID

        Returns:
            Subscription info dict with plan, status, etc.
        """
        try:
            profile = await self._client.get_account_profile(user_id)
            if profile:
                return {
                    "subscription_plan": profile.get("subscription_plan", "free"),
                    "subscription_status": profile.get("subscription_status", "inactive"),
                    "billing_cycle": profile.get("billing_cycle", "monthly"),
                    "free_tier": profile.get("subscription_plan", "free") == "free"
                }
            return {
                "subscription_plan": "free",
                "subscription_status": "inactive",
                "billing_cycle": "monthly",
                "free_tier": True
            }
        except Exception:
            return {
                "subscription_plan": "free",
                "subscription_status": "inactive",
                "billing_cycle": "monthly",
                "free_tier": True
            }

    async def check_user_active(self, user_id: str) -> bool:
        """
        Check if user account is active.

        Used to determine if billing should proceed.

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

    async def is_free_tier_user(self, user_id: str) -> bool:
        """
        Check if user is on free tier.

        Free tier users may have different billing rules.

        Args:
            user_id: User ID

        Returns:
            True if user is on free tier
        """
        try:
            sub_info = await self.get_user_subscription_info(user_id)
            return sub_info.get("free_tier", True)
        except Exception:
            return True

    # =============================================================================
    # Direct delegation to AccountServiceClient
    # =============================================================================

    async def get_account_profile(self, user_id: str):
        """Get full account profile (delegates to AccountServiceClient)"""
        return await self._client.get_account_profile(user_id)

    async def get_account_by_email(self, email: str):
        """Get account by email (delegates to AccountServiceClient)"""
        return await self._client.get_account_by_email(email)

    async def health_check(self) -> bool:
        """Check Account Service health"""
        return await self._client.health_check()


__all__ = ["AccountClient"]
