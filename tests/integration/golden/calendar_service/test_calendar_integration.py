"""
Calendar Service Integration Tests

Tests the CalendarService layer with mocked dependencies (repository, event_bus).
These are NOT HTTP tests - they test the service business logic layer directly.

Uses CalendarTestDataFactory from data contracts (no hardcoded data).
Target: 30-35 tests with full coverage.

Usage:
    pytest tests/integration/golden/calendar_service/test_calendar_integration.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock

from tests.contracts.calendar import (
    CalendarTestDataFactory,
    EventCreateRequestContract,
    EventUpdateRequestContract,
    EventQueryRequestContract,
    EventCategoryContract,
    RecurrenceTypeContract,
    SyncProviderContract,
    EventCreateRequestBuilder,
)

from microservices.calendar_service.calendar_service import (
    CalendarService,
    CalendarServiceValidationError,
)
from microservices.calendar_service.models import (
    EventCreateRequest,
    EventUpdateRequest,
    EventQueryRequest,
    EventCategory,
    RecurrenceType,
    SyncProvider,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_repository():
    """Mock repository for testing service layer"""
    repo = AsyncMock()

    # Default return values
    repo.create_event.return_value = {
        "event_id": CalendarTestDataFactory.make_event_id(),
        "user_id": CalendarTestDataFactory.make_user_id(),
        "title": "Test Event",
        "start_time": datetime.now(timezone.utc),
        "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
        "category": "other",
        "recurrence_type": "none",
        "reminders": [],
        "is_shared": False,
        "all_day": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    return repo


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing"""
    return AsyncMock()


@pytest.fixture
def calendar_service(mock_repository, mock_event_bus):
    """Create CalendarService with mocked dependencies"""
    return CalendarService(repository=mock_repository, event_bus=mock_event_bus)


# ============================================================================
# Event Creation Integration Tests
# ============================================================================

class TestEventCreationIntegration:
    """Integration tests for event creation"""

    @pytest.mark.asyncio
    async def test_create_event_full_flow(self, calendar_service, mock_repository):
        """Full event creation flow with all fields"""
        request_data = CalendarTestDataFactory.make_create_request()

        # Convert contract to service model
        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            description=request_data.description,
            location=request_data.location,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
            all_day=request_data.all_day,
            category=EventCategory(request_data.category.value),
            reminders=request_data.reminders,
        )

        result = await calendar_service.create_event(request)

        assert result is not None
        mock_repository.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_event_publishes_to_event_bus(
        self, calendar_service, mock_event_bus
    ):
        """Event creation publishes event.created to event bus"""
        request_data = CalendarTestDataFactory.make_create_request_minimal()

        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )

        await calendar_service.create_event(request)

        mock_event_bus.publish_event.assert_called()

    @pytest.mark.asyncio
    async def test_create_recurring_event(self, calendar_service, mock_repository):
        """Create recurring event with recurrence rule"""
        request_data = CalendarTestDataFactory.make_create_request_recurring()

        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
            recurrence_type=RecurrenceType(request_data.recurrence_type.value),
            recurrence_end_date=request_data.recurrence_end_date,
        )

        result = await calendar_service.create_event(request)

        assert result is not None
        mock_repository.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_shared_event(self, calendar_service, mock_repository):
        """Create event shared with other users"""
        request_data = CalendarTestDataFactory.make_create_request_shared()

        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
            is_shared=request_data.is_shared,
            shared_with=request_data.shared_with,
        )

        result = await calendar_service.create_event(request)

        assert result is not None
        mock_repository.create_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_all_day_event(self, calendar_service, mock_repository):
        """Create all-day event"""
        request_data = CalendarTestDataFactory.make_create_request_all_day()

        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
            all_day=request_data.all_day,
        )

        result = await calendar_service.create_event(request)

        assert result is not None


# ============================================================================
# Event Read Integration Tests
# ============================================================================

class TestEventReadIntegration:
    """Integration tests for event retrieval"""

    @pytest.mark.asyncio
    async def test_get_event_by_id(self, calendar_service, mock_repository):
        """Retrieve event by ID"""
        event_id = CalendarTestDataFactory.make_event_id()
        user_id = CalendarTestDataFactory.make_user_id()

        mock_repository.get_event_by_id.return_value = {
            "event_id": event_id,
            "user_id": user_id,
            "title": "Test Event",
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "category": "other",
            "recurrence_type": "none",
            "reminders": [],
            "is_shared": False,
            "all_day": False,
            "created_at": datetime.now(timezone.utc),
        }

        result = await calendar_service.get_event(event_id)

        assert result is not None
        assert result.event_id == event_id
        mock_repository.get_event_by_id.assert_called_once_with(event_id, None)

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, calendar_service, mock_repository):
        """Get non-existent event returns None"""
        mock_repository.get_event_by_id.return_value = None

        result = await calendar_service.get_event("nonexistent_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_query_events_by_user(self, calendar_service, mock_repository):
        """Query events for specific user"""
        user_id = CalendarTestDataFactory.make_user_id()

        mock_repository.get_events_by_user.return_value = [
            {
                "event_id": CalendarTestDataFactory.make_event_id(),
                "user_id": user_id,
                "title": "Event 1",
                "start_time": datetime.now(timezone.utc),
                "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
                "category": "work",
                "recurrence_type": "none",
                "reminders": [],
                "is_shared": False,
                "all_day": False,
                "created_at": datetime.now(timezone.utc),
            }
        ]

        request = EventQueryRequest(user_id=user_id)
        result = await calendar_service.query_events(request)

        assert result is not None
        mock_repository.get_events_by_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_today_events(self, calendar_service, mock_repository):
        """Get today's events"""
        user_id = CalendarTestDataFactory.make_user_id()

        mock_repository.get_today_events.return_value = []

        result = await calendar_service.get_today_events(user_id)

        assert isinstance(result, list)
        mock_repository.get_today_events.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_upcoming_events(self, calendar_service, mock_repository):
        """Get upcoming events"""
        user_id = CalendarTestDataFactory.make_user_id()

        mock_repository.get_upcoming_events.return_value = []

        result = await calendar_service.get_upcoming_events(user_id, days=7)

        assert isinstance(result, list)
        mock_repository.get_upcoming_events.assert_called_once()


# ============================================================================
# Event Update Integration Tests
# ============================================================================

class TestEventUpdateIntegration:
    """Integration tests for event updates"""

    @pytest.mark.asyncio
    async def test_update_event_title(self, calendar_service, mock_repository):
        """Update event title"""
        event_id = CalendarTestDataFactory.make_event_id()
        new_title = CalendarTestDataFactory.make_title()

        mock_repository.get_event_by_id.return_value = {
            "event_id": event_id,
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": "Old Title",
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "category": "other",
            "recurrence_type": "none",
            "reminders": [],
            "is_shared": False,
            "all_day": False,
            "created_at": datetime.now(timezone.utc),
        }

        mock_repository.update_event.return_value = {
            "event_id": event_id,
            "title": new_title,
        }

        request = EventUpdateRequest(title=new_title)
        result = await calendar_service.update_event(event_id, request)

        assert result is not None
        mock_repository.update_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_event_publishes_to_event_bus(
        self, calendar_service, mock_repository, mock_event_bus
    ):
        """Event update publishes event.updated to event bus"""
        event_id = CalendarTestDataFactory.make_event_id()

        mock_repository.get_event_by_id.return_value = {
            "event_id": event_id,
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": "Title",
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "category": "other",
            "recurrence_type": "none",
            "reminders": [],
            "is_shared": False,
            "all_day": False,
            "created_at": datetime.now(timezone.utc),
        }

        mock_repository.update_event.return_value = {"event_id": event_id}

        request = EventUpdateRequest(title="Updated")
        await calendar_service.update_event(event_id, request)

        mock_event_bus.publish_event.assert_called()

    @pytest.mark.asyncio
    async def test_update_nonexistent_event(self, calendar_service, mock_repository):
        """Update non-existent event returns None"""
        mock_repository.get_event_by_id.return_value = None

        request = EventUpdateRequest(title="Updated")
        result = await calendar_service.update_event("nonexistent", request)

        assert result is None


# ============================================================================
# Event Deletion Integration Tests
# ============================================================================

class TestEventDeletionIntegration:
    """Integration tests for event deletion"""

    @pytest.mark.asyncio
    async def test_delete_event(self, calendar_service, mock_repository):
        """Delete existing event"""
        event_id = CalendarTestDataFactory.make_event_id()

        mock_repository.delete_event.return_value = True

        result = await calendar_service.delete_event(event_id)

        assert result is True
        mock_repository.delete_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_event_publishes_to_event_bus(
        self, calendar_service, mock_repository, mock_event_bus
    ):
        """Event deletion publishes event.deleted to event bus"""
        event_id = CalendarTestDataFactory.make_event_id()

        mock_repository.delete_event.return_value = True

        await calendar_service.delete_event(event_id)

        mock_event_bus.publish_event.assert_called()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_event(self, calendar_service, mock_repository):
        """Delete non-existent event returns False"""
        mock_repository.delete_event.return_value = False

        result = await calendar_service.delete_event("nonexistent")

        assert result is False


# ============================================================================
# External Sync Integration Tests
# ============================================================================

class TestExternalSyncIntegration:
    """Integration tests for external calendar sync"""

    @pytest.mark.asyncio
    async def test_sync_google_calendar(self, calendar_service, mock_repository):
        """Sync with Google Calendar"""
        user_id = CalendarTestDataFactory.make_user_id()
        credentials = CalendarTestDataFactory.make_credentials()

        result = await calendar_service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            credentials=credentials,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_sync_unsupported_provider(self, calendar_service, mock_repository):
        """Sync with unsupported provider returns error"""
        user_id = CalendarTestDataFactory.make_user_id()

        result = await calendar_service.sync_with_external_calendar(
            user_id=user_id,
            provider="unsupported_provider",
        )

        assert result is not None
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_get_sync_status(self, calendar_service, mock_repository):
        """Get sync status for provider"""
        user_id = CalendarTestDataFactory.make_user_id()
        provider = SyncProvider.GOOGLE.value

        mock_repository.get_sync_status.return_value = {
            "user_id": user_id,
            "provider": provider,
            "status": "active",
            "synced_events_count": 42,
            "last_sync_time": datetime.now(timezone.utc),
        }

        result = await calendar_service.get_sync_status(user_id, provider)

        assert result is not None
        mock_repository.get_sync_status.assert_called_once()


# ============================================================================
# Validation Integration Tests
# ============================================================================

class TestValidationIntegration:
    """Integration tests for validation"""

    @pytest.mark.asyncio
    async def test_create_event_invalid_time_range(self, calendar_service):
        """Create event with end < start raises error"""
        now = CalendarTestDataFactory.make_timestamp()

        request = EventCreateRequest(
            user_id=CalendarTestDataFactory.make_user_id(),
            title="Invalid Event",
            start_time=now,
            end_time=now - timedelta(hours=1),
        )

        with pytest.raises(CalendarServiceValidationError):
            await calendar_service.create_event(request)

    @pytest.mark.asyncio
    async def test_create_event_same_start_end(self, calendar_service):
        """Create event with start == end raises error"""
        now = CalendarTestDataFactory.make_timestamp()

        request = EventCreateRequest(
            user_id=CalendarTestDataFactory.make_user_id(),
            title="Invalid Event",
            start_time=now,
            end_time=now,
        )

        with pytest.raises(CalendarServiceValidationError):
            await calendar_service.create_event(request)

    @pytest.mark.asyncio
    async def test_update_event_invalid_time_range(
        self, calendar_service, mock_repository
    ):
        """Update event with invalid time range raises error"""
        event_id = CalendarTestDataFactory.make_event_id()
        now = CalendarTestDataFactory.make_timestamp()

        mock_repository.get_event_by_id.return_value = {
            "event_id": event_id,
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": "Event",
            "start_time": now,
            "end_time": now + timedelta(hours=1),
            "category": "other",
            "recurrence_type": "none",
            "reminders": [],
            "is_shared": False,
            "all_day": False,
            "created_at": now,
        }

        request = EventUpdateRequest(
            start_time=now + timedelta(hours=2),
            end_time=now,
        )

        with pytest.raises(CalendarServiceValidationError):
            await calendar_service.update_event(event_id, request)


# ============================================================================
# Error Handling Integration Tests
# ============================================================================

class TestErrorHandlingIntegration:
    """Integration tests for error handling"""

    @pytest.mark.asyncio
    async def test_repository_error_propagates(
        self, calendar_service, mock_repository
    ):
        """Repository errors propagate correctly"""
        mock_repository.create_event.side_effect = Exception("Database error")

        request_data = CalendarTestDataFactory.make_create_request_minimal()
        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )

        with pytest.raises(Exception) as exc_info:
            await calendar_service.create_event(request)

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_event_bus_error_handled(
        self, calendar_service, mock_repository, mock_event_bus
    ):
        """Event bus errors don't fail the operation"""
        mock_event_bus.publish_event.side_effect = Exception("NATS error")

        request_data = CalendarTestDataFactory.make_create_request_minimal()
        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )

        # Should not raise even if event bus fails
        result = await calendar_service.create_event(request)
        # Result depends on implementation - may succeed or fail gracefully
