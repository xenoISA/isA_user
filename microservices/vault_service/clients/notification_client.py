"""
Notification Service Client

Client for vault_service to interact with notification_service.
Used for sending vault-related notifications to users.
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.notification_service.client import NotificationServiceClient


class NotificationClient:
    """
    Wrapper client for Notification Service calls from Vault Service.

    This wrapper provides vault-specific convenience methods
    while delegating to the actual NotificationServiceClient.
    """

    def __init__(self, base_url: str = None, config=None):
        """
        Initialize Notification Service client

        Args:
            base_url: Notification service base URL (optional, uses service discovery)
            config: ConfigManager instance for service discovery
        """
        # TODO: Use config for service discovery when available
        self._client = NotificationServiceClient(base_url=base_url)

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Vault-specific convenience methods
    # =============================================================================

    async def notify_secret_shared(
        self,
        user_id: str,
        secret_name: str,
        shared_by: str,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that a secret has been shared with them.

        Args:
            user_id: User ID to notify
            secret_name: Name of the shared secret
            shared_by: User ID who shared the secret
            channels: Notification channels (default: ["in_app", "email"])

        Returns:
            True if notification sent successfully
        """
        try:
            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="secret_shared",
                title="Secret Shared",
                message=f"A secret '{secret_name}' has been shared with you",
                channels=channels or ["in_app", "email"],
                priority="normal",
                data={
                    "secret_name": secret_name,
                    "shared_by": shared_by,
                },
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False

    async def notify_secret_accessed(
        self,
        user_id: str,
        secret_name: str,
        accessed_by: str,
        ip_address: Optional[str] = None,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that their secret has been accessed.

        Args:
            user_id: Secret owner user ID
            secret_name: Name of the accessed secret
            accessed_by: User ID who accessed the secret
            ip_address: IP address of access
            channels: Notification channels (default: ["in_app"])

        Returns:
            True if notification sent successfully
        """
        try:
            message = f"Your secret '{secret_name}' was accessed"
            if ip_address:
                message += f" from IP {ip_address}"

            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="secret_accessed",
                title="Secret Accessed",
                message=message,
                channels=channels or ["in_app"],
                priority="normal",
                data={
                    "secret_name": secret_name,
                    "accessed_by": accessed_by,
                    "ip_address": ip_address,
                },
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False

    async def notify_secret_expiring(
        self,
        user_id: str,
        secret_name: str,
        expires_in_days: int,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that their secret is expiring soon.

        Args:
            user_id: User ID
            secret_name: Name of the expiring secret
            expires_in_days: Number of days until expiration
            channels: Notification channels (default: ["in_app", "email"])

        Returns:
            True if notification sent successfully
        """
        try:
            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="secret_expiring",
                title="Secret Expiring Soon",
                message=f"Your secret '{secret_name}' will expire in {expires_in_days} days",
                channels=channels or ["in_app", "email"],
                priority="high",
                data={
                    "secret_name": secret_name,
                    "expires_in_days": expires_in_days,
                },
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False

    async def notify_unauthorized_access(
        self,
        user_id: str,
        secret_name: str,
        attempted_by: str,
        ip_address: Optional[str] = None,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user of unauthorized access attempt to their secret.

        Args:
            user_id: Secret owner user ID
            secret_name: Name of the secret
            attempted_by: User ID who attempted access
            ip_address: IP address of attempt
            channels: Notification channels (default: ["in_app", "email"])

        Returns:
            True if notification sent successfully
        """
        try:
            message = f"Unauthorized access attempt to your secret '{secret_name}'"
            if ip_address:
                message += f" from IP {ip_address}"

            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="unauthorized_access",
                title="Security Alert: Unauthorized Access",
                message=message,
                channels=channels or ["in_app", "email"],
                priority="urgent",
                data={
                    "secret_name": secret_name,
                    "attempted_by": attempted_by,
                    "ip_address": ip_address,
                },
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False


__all__ = ["NotificationClient"]
