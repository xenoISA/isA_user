"""
Account Service Client

Client for wallet_service to interact with account_service.
Used for validating user existence before wallet operations.
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
    Wrapper client for Account Service calls from Wallet Service.

    This wrapper provides wallet-specific convenience methods
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
    # Wallet-specific convenience methods
    # =============================================================================

    async def validate_user_exists(self, user_id: str) -> bool:
        """
        Validate that a user exists in the system.

        Used before creating a wallet or performing wallet operations.

        Args:
            user_id: User ID to validate

        Returns:
            True if user exists, False otherwise

        Example:
            >>> client = AccountClient()
            >>> exists = await client.validate_user_exists("user123")
            >>> if exists:
            ...     # Create wallet
        """
        try:
            profile = await self._client.get_account_profile(user_id)
            return profile is not None and profile.get("success", False)
        except Exception:
            return False

    async def get_user_info(self, user_id: str) -> Optional[dict]:
        """
        Get user information for wallet operations.

        Args:
            user_id: User ID

        Returns:
            User account profile or None

        Example:
            >>> user_info = await client.get_user_info("user123")
            >>> if user_info:
            ...     email = user_info.get("email")
        """
        try:
            result = await self._client.get_account_profile(user_id)
            if result and result.get("success"):
                return result.get("account")
            return None
        except Exception:
            return None

    async def check_user_active(self, user_id: str) -> bool:
        """
        Check if user account is active.

        Prevents wallet operations for suspended/deleted accounts.

        Args:
            user_id: User ID

        Returns:
            True if user is active, False otherwise
        """
        try:
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return False

            # Check account status
            status = user_info.get("status", "").lower()
            return status == "active"
        except Exception:
            return False

    async def get_account(self, user_id: str) -> Optional[dict]:
        """
        Get account by user ID (matches AccountClientProtocol).

        Args:
            user_id: User ID

        Returns:
            Account data dict or None if not found
        """
        try:
            result = await self._client.get_account_profile(user_id)
            if result and result.get("success"):
                return result.get("account") or result
            return None
        except Exception:
            return None

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
