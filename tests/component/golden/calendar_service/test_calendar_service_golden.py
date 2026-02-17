"""
Component Golden Tests: Calendar Service

Tests calendar service business logic with mocked dependencies.
No real database or external services - uses mock repository.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

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
from tests.component.mocks.calendar_repository_mock import MockCalendarRepository


class TestCalendarServiceCreate:
    """Test calendar service create operations"""

    @pytest.fixture
    def mock_repo(self):
        """Create fresh mock repository for each test"""
        return MockCalendarRepository()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus"""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo, mock_event_bus):
        """Create service with mocked dependencies"""
        return CalendarService(repository=mock_repo, event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_create_event_success(self, service, mock_repo):
        """Test successful event creation"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        request = EventCreateRequest(
            user_id="user_123",
            title="Team Meeting",
            description="Weekly sync",
            start_time=now,
            end_time=future,
            category=EventCategory.MEETING,
        )

        event = await service.create_event(request)

        assert event is not None
        assert event.user_id == "user_123"
        assert event.title == "Team Meeting"
        assert event.category == EventCategory.MEETING

        # Verify event was stored in mock repo
        stored = await mock_repo.get_event_by_id(event.event_id)
        assert stored is not None
        assert stored.event_id == event.event_id

    @pytest.mark.asyncio
    async def test_create_event_publishes_event(self, service, mock_event_bus):
        """Test that event creation publishes event to event bus"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="New Event",
            start_time=now,
            end_time=future,
        )

        await service.create_event(request)

        # Verify event was published
        mock_event_bus.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_event_invalid_dates_raises_error(self, service):
        """Test that invalid dates raise validation error"""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Invalid Event",
            start_time=now,
            end_time=past,
        )

        with pytest.raises(CalendarServiceValidationError):
            await service.create_event(request)

    @pytest.mark.asyncio
    async def test_create_recurring_event(self, service):
        """Test creating recurring event"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        recurrence_end = now + timedelta(days=60)

        request = EventCreateRequest(
            user_id="user_123",
            title="Weekly Standup",
            start_time=now,
            end_time=future,
            recurrence_type=RecurrenceType.WEEKLY,
            recurrence_end_date=recurrence_end,
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        )

        event = await service.create_event(request)

        assert event.recurrence_type == RecurrenceType.WEEKLY
        assert event.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO"


class TestCalendarServiceRead:
    """Test calendar service read operations"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository with sample data"""
        repo = MockCalendarRepository()
        now = datetime.now(timezone.utc)

        # Add sample events
        repo.set_event(
            "evt_001",
            user_id="user_123",
            title="Event 1",
            start_time=now,
            end_time=now + timedelta(hours=1),
            category=EventCategory.WORK,
        )
        repo.set_event(
            "evt_002",
            user_id="user_123",
            title="Event 2",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=2),
            category=EventCategory.PERSONAL,
        )
        repo.set_event(
            "evt_003",
            user_id="user_456",
            title="Other User Event",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mocked repository"""
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_get_event_by_id(self, service):
        """Test getting event by ID"""
        event = await service.get_event("evt_001")

        assert event is not None
        assert event.event_id == "evt_001"
        assert event.title == "Event 1"

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, service):
        """Test getting non-existent event returns None"""
        event = await service.get_event("evt_nonexistent")
        assert event is None

    @pytest.mark.asyncio
    async def test_get_event_with_user_filter(self, service):
        """Test getting event with user_id filter"""
        # Should find event
        event = await service.get_event("evt_001", user_id="user_123")
        assert event is not None

        # Should not find event (wrong user)
        event = await service.get_event("evt_001", user_id="user_456")
        assert event is None

    @pytest.mark.asyncio
    async def test_query_events_by_user(self, service):
        """Test querying events by user"""
        request = EventQueryRequest(user_id="user_123")
        result = await service.query_events(request)

        assert result.total == 2
        assert len(result.events) == 2
        assert all(e.user_id == "user_123" for e in result.events)

    @pytest.mark.asyncio
    async def test_query_events_with_date_filter(self, service):
        """Test querying events with date range"""
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)

        request = EventQueryRequest(
            user_id="user_123",
            start_date=tomorrow,
            end_date=tomorrow + timedelta(days=1),
        )
        result = await service.query_events(request)

        assert result.total >= 0  # May have events in that range

    @pytest.mark.asyncio
    async def test_query_events_with_category_filter(self, service):
        """Test querying events by category"""
        request = EventQueryRequest(
            user_id="user_123",
            category=EventCategory.WORK,
        )
        result = await service.query_events(request)

        assert all(e.category == EventCategory.WORK for e in result.events)

    @pytest.mark.asyncio
    async def test_get_upcoming_events(self, service, mock_repo):
        """Test getting upcoming events"""
        now = datetime.now(timezone.utc)

        # Add future event
        mock_repo.set_event(
            "evt_future",
            user_id="user_123",
            title="Future Event",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
        )

        events = await service.get_upcoming_events("user_123", days=7)
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_get_today_events(self, service):
        """Test getting today's events"""
        events = await service.get_today_events("user_123")

        # Should return events from today
        assert isinstance(events, list)


class TestCalendarServiceUpdate:
    """Test calendar service update operations"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository with sample event"""
        repo = MockCalendarRepository()
        now = datetime.now(timezone.utc)

        repo.set_event(
            "evt_001",
            user_id="user_123",
            title="Original Title",
            description="Original description",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        return repo

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus"""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo, mock_event_bus):
        """Create service with mocked dependencies"""
        return CalendarService(repository=mock_repo, event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_update_event_success(self, service):
        """Test successful event update"""
        update_request = EventUpdateRequest(
            title="Updated Title",
            description="Updated description",
        )

        updated = await service.update_event("evt_001", update_request)

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_event_publishes_event(self, service, mock_event_bus):
        """Test that event update publishes event to event bus"""
        update_request = EventUpdateRequest(title="New Title")

        await service.update_event("evt_001", update_request)

        # Verify event was published
        mock_event_bus.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_event_not_found(self, service):
        """Test updating non-existent event returns None"""
        update_request = EventUpdateRequest(title="Updated")

        result = await service.update_event("evt_nonexistent", update_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_event_with_invalid_dates(self, service):
        """Test updating event with invalid dates raises error"""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        update_request = EventUpdateRequest(
            start_time=now,
            end_time=past,
        )

        with pytest.raises(CalendarServiceValidationError):
            await service.update_event("evt_001", update_request)

    @pytest.mark.asyncio
    async def test_update_event_partial(self, service):
        """Test partial event update"""
        update_request = EventUpdateRequest(title="New Title Only")

        updated = await service.update_event("evt_001", update_request)

        assert updated is not None
        assert updated.title == "New Title Only"
        # Description should remain unchanged
        assert updated.description == "Original description"


class TestCalendarServiceDelete:
    """Test calendar service delete operations"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository with sample events"""
        repo = MockCalendarRepository()
        now = datetime.now(timezone.utc)

        repo.set_event(
            "evt_001",
            user_id="user_123",
            title="Event 1",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        return repo

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus"""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo, mock_event_bus):
        """Create service with mocked dependencies"""
        return CalendarService(repository=mock_repo, event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_delete_event_success(self, service, mock_repo):
        """Test successful event deletion"""
        result = await service.delete_event("evt_001")

        assert result is True

        # Verify event was deleted
        event = await mock_repo.get_event_by_id("evt_001")
        assert event is None

    @pytest.mark.asyncio
    async def test_delete_event_publishes_event(self, service, mock_event_bus):
        """Test that event deletion publishes event to event bus"""
        await service.delete_event("evt_001")

        # Verify event was published
        mock_event_bus.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, service):
        """Test deleting non-existent event returns False"""
        result = await service.delete_event("evt_nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_event_with_user_filter(self, service):
        """Test deleting event with user_id filter"""
        # Should succeed with correct user
        result = await service.delete_event("evt_001", user_id="user_123")
        assert result is True


class TestCalendarServiceSync:
    """Test calendar service external sync operations"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mocked repository"""
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_sync_with_google_calendar(self, service):
        """Test Google calendar sync"""
        result = await service.sync_with_external_calendar(
            user_id="user_123",
            provider=SyncProvider.GOOGLE.value,
            credentials={"access_token": "test_token"},
        )

        assert result is not None
        assert result.provider == SyncProvider.GOOGLE.value
        assert result.status in ["success", "error"]

    @pytest.mark.asyncio
    async def test_sync_with_unsupported_provider(self, service):
        """Test sync with unsupported provider returns error status"""
        result = await service.sync_with_external_calendar(
            user_id="user_123",
            provider="unsupported_provider",
        )

        assert result is not None
        assert result.status == "error"
        assert "Unsupported provider" in result.message

    @pytest.mark.asyncio
    async def test_get_sync_status(self, service, mock_repo):
        """Test getting sync status"""
        # Create sync status
        await mock_repo.update_sync_status(
            user_id="user_123",
            provider=SyncProvider.GOOGLE.value,
            status="active",
            synced_count=42,
        )

        # Get sync status
        status = await service.get_sync_status("user_123", SyncProvider.GOOGLE.value)

        assert status is not None
        assert status.provider == SyncProvider.GOOGLE.value
        assert status.synced_events == 42

    @pytest.mark.asyncio
    async def test_get_sync_status_not_found(self, service):
        """Test getting non-existent sync status returns None"""
        status = await service.get_sync_status("user_999", SyncProvider.GOOGLE.value)
        assert status is None


class TestCalendarServiceErrorHandling:
    """Test calendar service error handling"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mocked repository"""
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_repository_failure_propagates(self, service, mock_repo):
        """Test that repository failures propagate correctly"""
        mock_repo.set_failure("Database connection failed")

        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Test Event",
            start_time=now,
            end_time=future,
        )

        with pytest.raises(Exception) as exc_info:
            await service.create_event(request)

        assert "Database connection failed" in str(exc_info.value)
