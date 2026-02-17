"""
Calendar Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

# Import only models (no I/O dependencies)
from .models import EventResponse


# Custom exceptions - defined here to avoid importing repository
class CalendarEventNotFoundError(Exception):
    """Calendar event not found"""
    pass


class DuplicateEventError(Exception):
    """Duplicate event error"""
    pass


class InvalidDateRangeError(Exception):
    """Invalid date range error"""
    pass


@runtime_checkable
class CalendarEventRepositoryProtocol(Protocol):
    """
    Interface for Calendar Event Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_event(self, event_data: Dict[str, Any]) -> Optional[EventResponse]:
        """Create a new calendar event"""
        ...

    async def get_event_by_id(
        self, event_id: str, user_id: str = None
    ) -> Optional[EventResponse]:
        """Get event by ID"""
        ...

    async def get_events_by_user(
        self,
        user_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        category: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EventResponse]:
        """Get events for a user with optional filters"""
        ...

    async def get_upcoming_events(
        self, user_id: str, days: int = 7
    ) -> List[EventResponse]:
        """Get upcoming events for the next N days"""
        ...

    async def get_today_events(self, user_id: str) -> List[EventResponse]:
        """Get today's events"""
        ...

    async def update_event(
        self, event_id: str, updates: Dict[str, Any]
    ) -> Optional[EventResponse]:
        """Update an event"""
        ...

    async def delete_event(self, event_id: str, user_id: str = None) -> bool:
        """Delete an event"""
        ...

    async def update_sync_status(
        self,
        user_id: str,
        provider: str,
        status: str,
        synced_count: int = 0,
        error_message: str = None,
    ) -> bool:
        """Update external calendar sync status"""
        ...

    async def get_sync_status(
        self, user_id: str, provider: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get sync status for external calendars"""
        ...

    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user calendar data (GDPR)"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...

    async def subscribe_to_events(self, pattern: str, handler: Any) -> None:
        """Subscribe to events matching pattern"""
        ...

    async def close(self) -> None:
        """Close the event bus connection"""
        ...
