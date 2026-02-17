"""Mock Calendar Repository for component testing"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

from microservices.calendar_service.models import EventResponse, EventCategory, RecurrenceType
from microservices.calendar_service.protocols import CalendarEventRepositoryProtocol


class MockCalendarRepository:
    """
    In-memory mock repository implementing CalendarEventRepositoryProtocol.

    Used for component tests - no real database needed.
    """

    def __init__(self):
        self._events: Dict[str, EventResponse] = {}
        self._sync_status: Dict[str, Dict[str, Any]] = {}
        self._should_fail = False
        self._fail_message = ""

    def set_event(self, event_id: str, **kwargs) -> EventResponse:
        """Add an event to the mock store"""
        now = datetime.now(timezone.utc)

        # Ensure required fields have defaults
        event = EventResponse(
            event_id=event_id,
            user_id=kwargs.get('user_id', 'test_user'),
            title=kwargs.get('title', 'Test Event'),
            description=kwargs.get('description'),
            location=kwargs.get('location'),
            start_time=kwargs.get('start_time', now),
            end_time=kwargs.get('end_time', now),
            all_day=kwargs.get('all_day', False),
            category=kwargs.get('category', EventCategory.OTHER),
            color=kwargs.get('color'),
            recurrence_type=kwargs.get('recurrence_type', RecurrenceType.NONE),
            reminders=kwargs.get('reminders', []),
            is_shared=kwargs.get('is_shared', False),
            created_at=kwargs.get('created_at', now),
            updated_at=kwargs.get('updated_at'),
        )
        self._events[event_id] = event
        return event

    def set_failure(self, message: str = "Mock failure"):
        """Configure mock to fail on next operation"""
        self._should_fail = True
        self._fail_message = message

    def reset(self):
        """Reset mock state"""
        self._events.clear()
        self._sync_status.clear()
        self._should_fail = False
        self._fail_message = ""

    async def create_event(self, event_data: Dict[str, Any]) -> Optional[EventResponse]:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        event_id = f"evt_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)

        event = EventResponse(
            event_id=event_id,
            user_id=event_data.get('user_id'),
            title=event_data.get('title'),
            description=event_data.get('description'),
            location=event_data.get('location'),
            start_time=event_data.get('start_time'),
            end_time=event_data.get('end_time'),
            all_day=event_data.get('all_day', False),
            category=event_data.get('category', EventCategory.OTHER),
            color=event_data.get('color'),
            recurrence_type=event_data.get('recurrence_type', RecurrenceType.NONE),
            recurrence_end_date=event_data.get('recurrence_end_date'),
            recurrence_rule=event_data.get('recurrence_rule'),
            reminders=event_data.get('reminders', []),
            is_shared=event_data.get('is_shared', False),
            created_at=now,
            updated_at=now,
        )
        self._events[event_id] = event
        return event

    async def get_event_by_id(
        self, event_id: str, user_id: str = None
    ) -> Optional[EventResponse]:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        event = self._events.get(event_id)

        # Filter by user_id if provided
        if event and user_id and event.user_id != user_id:
            return None

        return event

    async def get_events_by_user(
        self,
        user_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        category: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EventResponse]:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        # Filter events by user
        events = [e for e in self._events.values() if e.user_id == user_id]

        # Filter by date range
        if start_date:
            events = [e for e in events if e.start_time >= start_date]
        if end_date:
            events = [e for e in events if e.end_time <= end_date]

        # Filter by category
        if category:
            events = [e for e in events if e.category == category]

        # Sort by start time
        events.sort(key=lambda x: x.start_time)

        # Apply pagination
        return events[offset:offset + limit]

    async def get_upcoming_events(
        self, user_id: str, days: int = 7
    ) -> List[EventResponse]:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        from datetime import timedelta
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days)

        return await self.get_events_by_user(
            user_id, start_date=now, end_date=end_date
        )

    async def get_today_events(self, user_id: str) -> List[EventResponse]:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        return await self.get_events_by_user(
            user_id, start_date=start_of_day, end_date=end_of_day
        )

    async def update_event(
        self, event_id: str, updates: Dict[str, Any]
    ) -> Optional[EventResponse]:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        event = self._events.get(event_id)
        if not event:
            return None

        # Create updated event
        updated_data = event.dict()
        updated_data.update(updates)
        updated_data['updated_at'] = datetime.now(timezone.utc)

        updated_event = EventResponse(**updated_data)
        self._events[event_id] = updated_event
        return updated_event

    async def delete_event(self, event_id: str, user_id: str = None) -> bool:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        event = self._events.get(event_id)

        # Check user ownership if user_id provided
        if event and user_id and event.user_id != user_id:
            return False

        if event_id in self._events:
            del self._events[event_id]
            return True
        return False

    async def update_sync_status(
        self,
        user_id: str,
        provider: str,
        status: str,
        synced_count: int = 0,
        error_message: str = None,
    ) -> bool:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        key = f"{user_id}:{provider}"
        self._sync_status[key] = {
            "user_id": user_id,
            "provider": provider,
            "status": status,
            "synced_events_count": synced_count,
            "error_message": error_message,
            "last_sync_time": datetime.now(timezone.utc),
        }
        return True

    async def get_sync_status(
        self, user_id: str, provider: str = None
    ) -> Optional[Dict[str, Any]]:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        if provider:
            key = f"{user_id}:{provider}"
            return self._sync_status.get(key)
        else:
            # Return all sync statuses for user
            return [
                v for k, v in self._sync_status.items()
                if k.startswith(f"{user_id}:")
            ]

    async def delete_user_data(self, user_id: str) -> int:
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        # Delete all events for user
        events_to_delete = [
            event_id for event_id, event in self._events.items()
            if event.user_id == user_id
        ]

        for event_id in events_to_delete:
            del self._events[event_id]

        # Delete sync status for user
        sync_to_delete = [
            key for key in self._sync_status.keys()
            if key.startswith(f"{user_id}:")
        ]

        for key in sync_to_delete:
            del self._sync_status[key]

        return len(events_to_delete) + len(sync_to_delete)
