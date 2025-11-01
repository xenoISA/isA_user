"""
Calendar Service Microservice

日历事件管理微服务 - 提供日历事件管理、外部日历同步等功能
"""

from .client import CalendarServiceClient
from .calendar_service import CalendarService
from .calendar_repository import CalendarRepository
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
    "CalendarRepository",
    "CalendarEvent",
    "EventCreateRequest",
    "EventUpdateRequest",
    "EventResponse",
    "EventCategory",
    "RecurrenceType",
    "SyncProvider"
]

