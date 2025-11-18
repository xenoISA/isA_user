"""
Task Service Event Handlers

Handles incoming events from other services via NATS
"""

import logging
from typing import Callable, Dict

from core.nats_client import Event

from .models import parse_user_deleted_event

logger = logging.getLogger(__name__)


# =============================================================================
# Event Handlers (Async Functions)
# =============================================================================


async def handle_user_deleted(event: Event, task_repository):
    """
    Handle user.deleted event

    When a user is deleted, cancel all their tasks

    Args:
        event: NATS event object
        task_repository: TaskRepository instance

    Event Data:
        - user_id: str
        - timestamp: str (optional)
        - reason: str (optional)

    Workflow:
        1. Parse event data
        2. Cancel all tasks for the user
        3. Log completion
    """
    try:
        # Parse event data
        event_data = parse_user_deleted_event(event.data)
        user_id = event_data.user_id

        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Handling user.deleted event for user {user_id}")

        # Cancel all tasks for this user
        cancelled_count = await task_repository.cancel_user_tasks(user_id)

        logger.info(
            f"✅ Cancelled {cancelled_count} tasks for deleted user {user_id}"
        )

    except Exception as e:
        logger.error(
            f"❌ Failed to handle user.deleted event: {e}", exc_info=True
        )
        # Don't raise - we don't want to break the event processing chain


# =============================================================================
# Event Handler Registry
# =============================================================================


def get_event_handlers(task_repository) -> Dict[str, Callable]:
    """
    Get all event handlers for task service.

    Returns a dict mapping event patterns to handler functions.
    This is used by main.py to register all event subscriptions.

    Args:
        task_repository: TaskRepository instance

    Returns:
        Dict[str, callable]: Event pattern -> handler function mapping
    """
    return {
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event, task_repository
        ),
        "*.user.deleted": lambda event: handle_user_deleted(event, task_repository),
    }


__all__ = [
    "handle_user_deleted",
    "get_event_handlers",
]
