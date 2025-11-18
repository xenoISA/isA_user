"""
Notification Service Client

Client for task_service to interact with notification_service.
Used for sending task-related notifications to users.
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.notification_service.clients.notification_client import NotificationServiceClient


class NotificationClient:
    """
    Wrapper client for Notification Service calls from Task Service.

    This wrapper provides task-specific convenience methods
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
    # Task-specific convenience methods
    # =============================================================================

    async def notify_task_created(
        self,
        user_id: str,
        task_name: str,
        task_id: str,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that a task has been created.

        Args:
            user_id: User ID
            task_name: Task name
            task_id: Task ID
            channels: Notification channels (default: ["in_app"])

        Returns:
            True if notification sent successfully
        """
        try:
            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="task_created",
                title="Task Created",
                message=f"Task '{task_name}' has been created",
                channels=channels or ["in_app"],
                priority="normal",
                data={"task_id": task_id, "task_name": task_name},
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False

    async def notify_task_completed(
        self,
        user_id: str,
        task_name: str,
        task_id: str,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that a task has completed.

        Args:
            user_id: User ID
            task_name: Task name
            task_id: Task ID
            channels: Notification channels (default: ["in_app", "push"])

        Returns:
            True if notification sent successfully
        """
        try:
            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="task_completed",
                title="Task Completed",
                message=f"Task '{task_name}' has completed successfully",
                channels=channels or ["in_app", "push"],
                priority="normal",
                data={"task_id": task_id, "task_name": task_name},
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False

    async def notify_task_failed(
        self,
        user_id: str,
        task_name: str,
        task_id: str,
        error_message: str,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Notify user that a task has failed.

        Args:
            user_id: User ID
            task_name: Task name
            task_id: Task ID
            error_message: Error message
            channels: Notification channels (default: ["in_app", "email"])

        Returns:
            True if notification sent successfully
        """
        try:
            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="task_failed",
                title="Task Failed",
                message=f"Task '{task_name}' failed: {error_message}",
                channels=channels or ["in_app", "email"],
                priority="high",
                data={
                    "task_id": task_id,
                    "task_name": task_name,
                    "error_message": error_message,
                },
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False

    async def notify_task_reminder(
        self,
        user_id: str,
        task_name: str,
        task_id: str,
        due_date: str,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Send task reminder notification.

        Args:
            user_id: User ID
            task_name: Task name
            task_id: Task ID
            due_date: Task due date
            channels: Notification channels (default: ["in_app", "push", "email"])

        Returns:
            True if notification sent successfully
        """
        try:
            result = await self._client.send_notification(
                user_id=user_id,
                notification_type="task_reminder",
                title="Task Reminder",
                message=f"Reminder: Task '{task_name}' is due on {due_date}",
                channels=channels or ["in_app", "push", "email"],
                priority="normal",
                data={
                    "task_id": task_id,
                    "task_name": task_name,
                    "due_date": due_date,
                },
            )
            return result is not None and result.get("success", False)
        except Exception:
            return False


__all__ = ["NotificationClient"]
