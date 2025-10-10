"""
MQTT Notification Module for Task Service

This module provides MQTT notification delivery for task events by calling
the gateway's MQTT publish endpoint. The gateway then publishes to the MQTT broker.

Flow:
    task_service → HTTP → gateway → MQTT → user's app

Task Events:
    - Task created (low priority)
    - Task completed (normal priority)
    - Task failed (high priority)
    - Task reminder due (high priority)
    - Task due date approaching (high priority)
    - Task status changed (normal priority)
    - Calendar event soon (high priority)
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class TaskMQTTNotifier:
    """
    MQTT notification channel for task service events.

    This is an HTTP client that forwards task notifications to the gateway,
    which then publishes them to the MQTT broker.
    """

    def __init__(self, gateway_url: str):
        """
        Initialize task MQTT notifier

        Args:
            gateway_url: Base URL of the gateway service
        """
        self.gateway_url = gateway_url
        self.mqtt_endpoint = f"{gateway_url}/api/v1/mqtt/publish/notification"
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"Task MQTT Notifier initialized with gateway: {gateway_url}")

    async def _send_notification(
        self,
        user_id: str,
        notification_data: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal method to send notification via gateway

        Args:
            user_id: Target user ID
            notification_data: Notification payload
            auth_token: Optional JWT token for authentication

        Returns:
            Dict with success status and response data
        """
        payload = {
            "type": "user",
            "user_id": user_id,
            "notification": notification_data
        }

        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            logger.debug(f"Sending task notification to user {user_id} via gateway")
            response = await self.client.post(
                self.mqtt_endpoint,
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Task MQTT notification sent successfully to user {user_id}")
            return {
                "success": True,
                "mqtt_response": result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending task MQTT notification: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "timestamp": datetime.utcnow().isoformat()
            }
        except httpx.RequestError as e:
            logger.error(f"Request error sending task MQTT notification: {e}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def notify_task_created(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        task_type: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification when a new task is created

        Args:
            user_id: Owner of the task
            task_id: Task identifier
            task_name: Name/title of the task
            task_type: Type of task (todo, reminder, calendar_event, etc.)
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        notification = {
            "event": "task_created",
            "priority": "low",
            "title": "New Task Created",
            "message": f"Task '{task_name}' has been created",
            "data": {
                "task_id": task_id,
                "task_name": task_name,
                "task_type": task_type,
                "created_at": datetime.utcnow().isoformat()
            }
        }
        return await self._send_notification(user_id, notification, auth_token)

    async def notify_task_completed(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        task_type: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification when a task is completed

        Args:
            user_id: Owner of the task
            task_id: Task identifier
            task_name: Name/title of the task
            task_type: Type of task
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        notification = {
            "event": "task_completed",
            "priority": "normal",
            "title": "Task Completed",
            "message": f"Task '{task_name}' has been completed successfully",
            "data": {
                "task_id": task_id,
                "task_name": task_name,
                "task_type": task_type,
                "completed_at": datetime.utcnow().isoformat()
            }
        }
        return await self._send_notification(user_id, notification, auth_token)

    async def notify_task_failed(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        task_type: str,
        error_message: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification when a task fails

        Args:
            user_id: Owner of the task
            task_id: Task identifier
            task_name: Name/title of the task
            task_type: Type of task
            error_message: Error description
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        notification = {
            "event": "task_failed",
            "priority": "high",
            "title": "Task Failed",
            "message": f"Task '{task_name}' failed: {error_message}",
            "data": {
                "task_id": task_id,
                "task_name": task_name,
                "task_type": task_type,
                "error": error_message,
                "failed_at": datetime.utcnow().isoformat()
            }
        }
        return await self._send_notification(user_id, notification, auth_token)

    async def notify_task_reminder(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        reminder_time: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification for task reminder

        Args:
            user_id: Owner of the task
            task_id: Task identifier
            task_name: Name/title of the task
            reminder_time: Scheduled reminder time (ISO format)
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        notification = {
            "event": "task_reminder",
            "priority": "high",
            "title": "Task Reminder",
            "message": f"Reminder: {task_name}",
            "data": {
                "task_id": task_id,
                "task_name": task_name,
                "reminder_time": reminder_time,
                "triggered_at": datetime.utcnow().isoformat()
            }
        }
        return await self._send_notification(user_id, notification, auth_token)

    async def notify_task_due(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        due_date: str,
        hours_until_due: int,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification when task due date is approaching

        Args:
            user_id: Owner of the task
            task_id: Task identifier
            task_name: Name/title of the task
            due_date: Task due date (ISO format)
            hours_until_due: Hours remaining until due
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        notification = {
            "event": "task_due_soon",
            "priority": "high",
            "title": "Task Due Soon",
            "message": f"Task '{task_name}' is due in {hours_until_due} hours",
            "data": {
                "task_id": task_id,
                "task_name": task_name,
                "due_date": due_date,
                "hours_until_due": hours_until_due,
                "notified_at": datetime.utcnow().isoformat()
            }
        }
        return await self._send_notification(user_id, notification, auth_token)

    async def notify_calendar_event_soon(
        self,
        user_id: str,
        task_id: str,
        event_title: str,
        event_time: str,
        minutes_before: int,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification for upcoming calendar event

        Args:
            user_id: Owner of the calendar event
            task_id: Task identifier
            event_title: Title of the calendar event
            event_time: Event start time (ISO format)
            minutes_before: Minutes before event starts
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        notification = {
            "event": "calendar_event_soon",
            "priority": "high",
            "title": "Calendar Event Soon",
            "message": f"Event '{event_title}' starts in {minutes_before} minutes",
            "data": {
                "task_id": task_id,
                "event_title": event_title,
                "event_time": event_time,
                "minutes_before": minutes_before,
                "notified_at": datetime.utcnow().isoformat()
            }
        }
        return await self._send_notification(user_id, notification, auth_token)

    async def notify_task_status_changed(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        old_status: str,
        new_status: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification when task status changes

        Args:
            user_id: Owner of the task
            task_id: Task identifier
            task_name: Name/title of the task
            old_status: Previous status
            new_status: New status
            auth_token: Optional JWT token

        Returns:
            Dict with success status
        """
        notification = {
            "event": "task_status_changed",
            "priority": "normal",
            "title": "Task Status Changed",
            "message": f"Task '{task_name}' status changed from {old_status} to {new_status}",
            "data": {
                "task_id": task_id,
                "task_name": task_name,
                "old_status": old_status,
                "new_status": new_status,
                "changed_at": datetime.utcnow().isoformat()
            }
        }
        return await self._send_notification(user_id, notification, auth_token)

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()
        logger.info("Task MQTT Notifier closed")


# Global task MQTT notifier instance (singleton pattern)
_task_notifier: Optional[TaskMQTTNotifier] = None


def get_task_notifier(gateway_url: Optional[str] = None) -> TaskMQTTNotifier:
    """
    Get or create global task MQTT notifier instance

    Args:
        gateway_url: Gateway service URL

    Returns:
        TaskMQTTNotifier instance
    """
    global _task_notifier
    if _task_notifier is None:
        _task_notifier = TaskMQTTNotifier(gateway_url=gateway_url)
    return _task_notifier


async def close_task_notifier():
    """Close and cleanup global task MQTT notifier instance"""
    global _task_notifier
    if _task_notifier is not None:
        await _task_notifier.close()
        _task_notifier = None
