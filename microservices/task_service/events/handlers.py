"""
Task Service Event Handlers

Handles incoming events from other services via NATS
"""

import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType

logger = logging.getLogger(__name__)


class TaskEventHandler:
    """
    Handles events subscribed by Task Service

    Subscribes to:
    - user.deleted: Cancel all tasks for deleted user
    """

    def __init__(self, task_repository):
        """
        Initialize event handler

        Args:
            task_repository: TaskRepository instance for data access
        """
        self.task_repo = task_repository

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle user.deleted event

        When a user is deleted, cancel all their tasks

        Args:
            event_data: Event data containing user_id

        Returns:
            bool: True if handled successfully
        """
        try:
            user_id = event_data.get('user_id')
            if not user_id:
                logger.warning("user.deleted event missing user_id")
                return False

            logger.info(f"Handling user.deleted event for user {user_id}")

            # Cancel all tasks for this user
            cancelled_count = await self.task_repo.cancel_user_tasks(user_id)

            logger.info(f"Cancelled {cancelled_count} tasks for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle user.deleted event: {e}", exc_info=True)
            return False

    async def handle_event(self, event: Event) -> bool:
        """
        Route event to appropriate handler

        Args:
            event: The event to handle

        Returns:
            bool: True if handled successfully
        """
        try:
            event_type = event.type

            if event_type == EventType.USER_DELETED.value:
                return await self.handle_user_deleted(event.data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to handle event: {e}", exc_info=True)
            return False

    def get_subscriptions(self) -> list:
        """
        Get list of event types this handler subscribes to

        Returns:
            list: List of event type values to subscribe to
        """
        return [
            EventType.USER_DELETED.value,
        ]
