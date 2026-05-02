"""
Event Service - Events Module

This module contains event models, publishers, and handlers for the event service.
"""

from .handlers import (
    EventHandlers,
    handle_event_created,
    handle_event_failed,
    handle_event_processed,
)
from .models import (
    EventCreatedEvent,
    EventFailedEvent,
    EventModel,
    EventProcessedEvent,
)
from .publishers import (
    EventPublisher,
    publish_event_created,
    publish_event_failed,
    publish_event_processed,
)

__all__ = [
    # Re-export from models
    "EventModel",
    "EventCreatedEvent",
    "EventProcessedEvent",
    "EventFailedEvent",
    # Re-export from publishers
    "EventPublisher",
    "publish_event_created",
    "publish_event_processed",
    "publish_event_failed",
    # Re-export from handlers
    "EventHandlers",
    "handle_event_created",
    "handle_event_processed",
    "handle_event_failed",
]
