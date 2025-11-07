"""
Notification Service Client

Client library for other microservices to interact with notification service
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class NotificationServiceClient:
    """Notification Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Notification Service client

        Args:
            base_url: Notification service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("notification_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8206"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Notification Sending
    # =============================================================================

    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        channels: Optional[List[str]] = None,
        priority: str = "normal",
        data: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send notification to user

        Args:
            user_id: User ID to send notification to
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            channels: Delivery channels (email, push, in_app, sms)
            priority: Priority (low, normal, high, urgent)
            data: Additional data payload (optional)
            template_id: Template ID to use (optional)
            template_data: Template data if using template (optional)

        Returns:
            Notification send result

        Example:
            >>> client = NotificationServiceClient()
            >>> result = await client.send_notification(
            ...     user_id="user123",
            ...     notification_type="album_shared",
            ...     title="Album Shared",
            ...     message="John shared an album with you",
            ...     channels=["email", "push", "in_app"]
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "priority": priority
            }

            if channels:
                payload["channels"] = channels
            if data:
                payload["data"] = data
            if template_id:
                payload["template_id"] = template_id
            if template_data:
                payload["template_data"] = template_data

            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/send",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send notification: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return None

    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Send multiple notifications in batch

        Args:
            notifications: List of notification dictionaries

        Returns:
            Batch send result

        Example:
            >>> notifications = [
            ...     {
            ...         "user_id": "user1",
            ...         "notification_type": "welcome",
            ...         "title": "Welcome",
            ...         "message": "Welcome to our app",
            ...         "channels": ["email"]
            ...     },
            ...     {
            ...         "user_id": "user2",
            ...         "notification_type": "welcome",
            ...         "title": "Welcome",
            ...         "message": "Welcome to our app",
            ...         "channels": ["email"]
            ...     }
            ... ]
            >>> result = await client.send_batch_notifications(notifications)
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/batch",
                json={"notifications": notifications}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send batch notifications: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending batch notifications: {e}")
            return None

    # =============================================================================
    # In-App Notifications
    # =============================================================================

    async def get_in_app_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get user's in-app notifications

        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Maximum notifications to return

        Returns:
            List of in-app notifications

        Example:
            >>> notifications = await client.get_in_app_notifications(
            ...     user_id="user123",
            ...     unread_only=True
            ... )
            >>> for notif in notifications:
            ...     print(f"{notif['title']}: {notif['message']}")
        """
        try:
            params = {"limit": limit}
            if unread_only:
                params["unread_only"] = unread_only

            response = await self.client.get(
                f"{self.base_url}/api/v1/notifications/in-app/{user_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get in-app notifications: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting in-app notifications: {e}")
            return None

    async def mark_notification_read(
        self,
        notification_id: str
    ) -> bool:
        """
        Mark in-app notification as read

        Args:
            notification_id: Notification ID

        Returns:
            True if successful

        Example:
            >>> success = await client.mark_notification_read("notif_123")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/in-app/{notification_id}/read"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to mark notification read: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error marking notification read: {e}")
            return False

    async def archive_notification(
        self,
        notification_id: str
    ) -> bool:
        """
        Archive in-app notification

        Args:
            notification_id: Notification ID

        Returns:
            True if successful

        Example:
            >>> success = await client.archive_notification("notif_123")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/in-app/{notification_id}/archive"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to archive notification: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error archiving notification: {e}")
            return False

    async def get_unread_count(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's unread notification count

        Args:
            user_id: User ID

        Returns:
            Unread count data

        Example:
            >>> count = await client.get_unread_count("user123")
            >>> print(f"Unread: {count['unread_count']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/notifications/in-app/{user_id}/unread-count"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get unread count: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return None

    # =============================================================================
    # Push Notification Subscriptions
    # =============================================================================

    async def subscribe_push(
        self,
        user_id: str,
        endpoint: str,
        keys: Dict[str, str],
        device_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Subscribe to push notifications

        Args:
            user_id: User ID
            endpoint: Push notification endpoint
            keys: Push subscription keys (p256dh, auth)
            device_type: Device type (optional)

        Returns:
            Push subscription data

        Example:
            >>> subscription = await client.subscribe_push(
            ...     user_id="user123",
            ...     endpoint="https://fcm.googleapis.com/...",
            ...     keys={"p256dh": "...", "auth": "..."}
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "endpoint": endpoint,
                "keys": keys
            }

            if device_type:
                payload["device_type"] = device_type

            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/push/subscribe",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to subscribe push: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error subscribing push: {e}")
            return None

    async def get_push_subscriptions(
        self,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get user's push subscriptions

        Args:
            user_id: User ID

        Returns:
            List of push subscriptions

        Example:
            >>> subs = await client.get_push_subscriptions("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/notifications/push/subscriptions/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get push subscriptions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting push subscriptions: {e}")
            return None

    async def unsubscribe_push(
        self,
        user_id: str,
        endpoint: str
    ) -> bool:
        """
        Unsubscribe from push notifications

        Args:
            user_id: User ID
            endpoint: Push endpoint to remove

        Returns:
            True if successful

        Example:
            >>> success = await client.unsubscribe_push(
            ...     user_id="user123",
            ...     endpoint="https://fcm.googleapis.com/..."
            ... )
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/notifications/push/unsubscribe",
                json={
                    "user_id": user_id,
                    "endpoint": endpoint
                }
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to unsubscribe push: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error unsubscribing push: {e}")
            return False

    # =============================================================================
    # Templates
    # =============================================================================

    async def create_template(
        self,
        template_id: str,
        name: str,
        notification_type: str,
        channels: List[str],
        title_template: str,
        message_template: str,
        email_html: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create notification template

        Args:
            template_id: Template identifier
            name: Template name
            notification_type: Type of notification
            channels: Supported channels
            title_template: Title template with placeholders
            message_template: Message template with placeholders
            email_html: HTML template for email (optional)

        Returns:
            Created template

        Example:
            >>> template = await client.create_template(
            ...     template_id="album_shared",
            ...     name="Album Shared Template",
            ...     notification_type="album_shared",
            ...     channels=["email", "in_app"],
            ...     title_template="{{sender_name}} shared an album",
            ...     message_template="{{sender_name}} shared '{{album_name}}' with you"
            ... )
        """
        try:
            payload = {
                "template_id": template_id,
                "name": name,
                "notification_type": notification_type,
                "channels": channels,
                "title_template": title_template,
                "message_template": message_template
            }

            if email_html:
                payload["email_html"] = email_html

            response = await self.client.post(
                f"{self.base_url}/api/v1/notifications/templates",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create template: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return None

    async def get_template(
        self,
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get notification template

        Args:
            template_id: Template ID

        Returns:
            Template data

        Example:
            >>> template = await client.get_template("album_shared")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/notifications/templates/{template_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get template: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting template: {e}")
            return None

    async def list_templates(self) -> Optional[List[Dict[str, Any]]]:
        """
        List all notification templates

        Returns:
            List of templates

        Example:
            >>> templates = await client.list_templates()
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/notifications/templates"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list templates: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return None

    # =============================================================================
    # Notification Queries
    # =============================================================================

    async def get_notifications(
        self,
        user_id: Optional[str] = None,
        notification_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Query notifications

        Args:
            user_id: Filter by user (optional)
            notification_type: Filter by type (optional)
            status: Filter by status (optional)
            limit: Maximum results

        Returns:
            List of notifications

        Example:
            >>> notifications = await client.get_notifications(
            ...     user_id="user123",
            ...     status="sent"
            ... )
        """
        try:
            params = {"limit": limit}

            if user_id:
                params["user_id"] = user_id
            if notification_type:
                params["notification_type"] = notification_type
            if status:
                params["status"] = status

            response = await self.client.get(
                f"{self.base_url}/api/v1/notifications",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get notifications: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return None

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_notification_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get notification statistics

        Returns:
            Notification statistics

        Example:
            >>> stats = await client.get_notification_stats()
            >>> print(f"Total sent: {stats['total_sent']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/notifications/stats"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get notification stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["NotificationServiceClient"]
