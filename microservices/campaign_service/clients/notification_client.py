"""
Notification Service Client

Client for calling notification_service to deliver campaign messages.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class NotificationClient:
    """Client for notification_service"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("campaign_service")

        host, port = config.discover_service(
            service_name='notification_service',
            default_host='localhost',
            default_port=8270,
            env_host_key='NOTIFICATION_SERVICE_HOST',
            env_port_key='NOTIFICATION_SERVICE_PORT'
        )
        self.base_url = f"http://{host}:{port}"
        self.timeout = 30.0

    async def send_notification(
        self,
        user_id: str,
        channel_type: str,
        content: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a notification via notification_service.

        Args:
            user_id: Recipient user ID
            channel_type: Channel type (email, sms, etc)
            content: Message content
            **kwargs: Additional parameters (campaign_id, message_id, etc)

        Returns:
            Notification response with notification_id
        """
        try:
            request_data = {
                "user_id": user_id,
                "channel_type": channel_type,
                "content": content,
                **kwargs,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/notifications",
                    json=request_data,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error sending notification: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            raise

    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Send batch of notifications.

        Args:
            notifications: List of notification payloads

        Returns:
            Batch response with results
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/notifications/batch",
                    json={"notifications": notifications},
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error sending batch notifications: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Error sending batch notifications: {e}")
            raise

    async def get_notification_status(
        self,
        notification_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get notification delivery status.

        Args:
            notification_id: Notification ID

        Returns:
            Notification status or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/notifications/{notification_id}"
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error getting notification status: {e}")
            return None

    async def cancel_notification(self, notification_id: str) -> bool:
        """
        Cancel a pending notification.

        Args:
            notification_id: Notification ID

        Returns:
            True if cancelled successfully
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/api/v1/notifications/{notification_id}"
                )

                if response.status_code == 404:
                    return False

                response.raise_for_status()
                return True

        except Exception as e:
            logger.error(f"Error cancelling notification: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if notification_service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


__all__ = ["NotificationClient"]
