from enum import Enum


# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class CalendarEventType(str, Enum):
    """
    Events published by calendar_service.

    Stream: calendar-stream
    Subjects: calendar.>
    """
    EVENT_CREATED = "calendar.event.created"
    EVENT_UPDATED = "calendar.event.updated"
    EVENT_DELETED = "calendar.event.deleted"


class CalendarSubscribedEventType(str, Enum):
    """Events that calendar_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class CalendarStreamConfig:
    """Stream configuration for calendar_service"""
    STREAM_NAME = "calendar-stream"
    SUBJECTS = ["calendar.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "calendar"


