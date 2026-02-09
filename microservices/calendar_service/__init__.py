"""
Calendar Service Microservice

日历事件管理微服务 - 提供日历事件管理、外部日历同步等功能

Uses dependency injection pattern:
- Import models and protocols for type safety
- Import factory to create service with real dependencies
- DO NOT import repository directly (it has I/O dependencies)
"""

from .client import CalendarServiceClient
from .calendar_service import CalendarService
from .factory import create_calendar_service
from .protocols import (
    CalendarEventRepositoryProtocol,
    CalendarEventNotFoundError,
    DuplicateEventError,
    InvalidDateRangeError,
)
from .models import (
    CalendarEvent,
    EventCreateRequest,
    EventUpdateRequest,
    EventResponse,
    EventCategory,
    RecurrenceType,
    SyncProvider
)

__version__ = "1.0.0"
__all__ = [
    "CalendarServiceClient",
    "CalendarService",
    "create_calendar_service",
    "CalendarEventRepositoryProtocol",
    "CalendarEventNotFoundError",
    "DuplicateEventError",
    "InvalidDateRangeError",
    "CalendarEvent",
    "EventCreateRequest",
    "EventUpdateRequest",
    "EventResponse",
    "EventCategory",
    "RecurrenceType",
    "SyncProvider"
]

