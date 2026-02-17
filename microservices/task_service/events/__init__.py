"""
Task Service Event Handlers

Standard Structure:
- models.py: Event data models (Pydantic)
- handlers.py: Event handlers (subscribe to events from other services)
- publishers.py: Event publishers (publish events to other services)
"""

# Event Handlers
from .handlers import get_event_handlers, handle_user_deleted

# Event Models
from .models import (
    TaskCompletedEventData,
    TaskCreatedEventData,
    TaskFailedEventData,
    UserDeletedEventData,
)

# Event Publishers
from .publishers import (
    publish_task_completed,
    publish_task_created,
    publish_task_failed,
)

__all__ = [
    # Event Handlers
    "get_event_handlers",
    "handle_user_deleted",
    # Event Models
    "UserDeletedEventData",
    "TaskCreatedEventData",
    "TaskCompletedEventData",
    "TaskFailedEventData",
    # Event Publishers
    "publish_task_created",
    "publish_task_completed",
    "publish_task_failed",
]
