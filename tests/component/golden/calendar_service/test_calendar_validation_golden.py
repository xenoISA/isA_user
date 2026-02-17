"""
Component Golden Tests: Calendar Service Validation

Tests business rule validation logic with mocked repository.
"""
import pytest
from datetime import datetime, timezone, timedelta

from microservices.calendar_service.calendar_service import (
    CalendarService,
    CalendarServiceValidationError,
)
from microservices.calendar_service.models import (
    EventCreateRequest,
    EventUpdateRequest,
    EventCategory,
    RecurrenceType,
)
from tests.component.golden.calendar_service.mocks import MockCalendarRepository

pytestmark = [pytest.mark.component, pytest.mark.golden]


class TestEventDateValidation:
    """Test event date/time validation rules"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        mock_repo = MockCalendarRepository()
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_create_event_with_valid_dates(self, service):
        """Test creating event with valid start/end times"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        request = EventCreateRequest(
            user_id="user_123",
            title="Valid Event",
            start_time=now,
            end_time=future,
        )

        event = await service.create_event(request)
        assert event is not None
        assert event.title == "Valid Event"

    @pytest.mark.asyncio
    async def test_create_event_end_time_before_start_time(self, service):
        """Test that end time before start time raises validation error"""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Invalid Event",
            start_time=now,
            end_time=past,
        )

        with pytest.raises(CalendarServiceValidationError) as exc_info:
            await service.create_event(request)

        assert "End time must be after start time" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_event_same_start_and_end_time(self, service):
        """Test that same start and end time raises validation error"""
        now = datetime.now(timezone.utc)

        request = EventCreateRequest(
            user_id="user_123",
            title="Invalid Event",
            start_time=now,
            end_time=now,
        )

        with pytest.raises(CalendarServiceValidationError) as exc_info:
            await service.create_event(request)

        assert "End time must be after start time" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_event_with_valid_dates(self, service):
        """Test updating event with valid start/end times"""
        # Create initial event
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        create_request = EventCreateRequest(
            user_id="user_123",
            title="Original Event",
            start_time=now,
            end_time=future,
        )
        event = await service.create_event(create_request)

        # Update with valid dates
        new_start = now + timedelta(days=1)
        new_end = new_start + timedelta(hours=2)

        update_request = EventUpdateRequest(
            start_time=new_start,
            end_time=new_end,
        )

        updated = await service.update_event(event.event_id, update_request)
        assert updated is not None
        assert updated.start_time == new_start
        assert updated.end_time == new_end

    @pytest.mark.asyncio
    async def test_update_event_invalid_dates(self, service):
        """Test updating event with invalid start/end times"""
        # Create initial event
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        create_request = EventCreateRequest(
            user_id="user_123",
            title="Original Event",
            start_time=now,
            end_time=future,
        )
        event = await service.create_event(create_request)

        # Try to update with invalid dates
        new_start = now + timedelta(days=1)
        new_end = now  # End before start

        update_request = EventUpdateRequest(
            start_time=new_start,
            end_time=new_end,
        )

        with pytest.raises(CalendarServiceValidationError) as exc_info:
            await service.update_event(event.event_id, update_request)

        assert "End time must be after start time" in str(exc_info.value)


class TestRecurrenceValidation:
    """Test recurrence rule validation"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        mock_repo = MockCalendarRepository()
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_create_recurring_event(self, service):
        """Test creating recurring event"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        recurrence_end = now + timedelta(days=30)

        request = EventCreateRequest(
            user_id="user_123",
            title="Daily Standup",
            start_time=now,
            end_time=future,
            recurrence_type=RecurrenceType.DAILY,
            recurrence_end_date=recurrence_end,
            recurrence_rule="FREQ=DAILY;INTERVAL=1",
        )

        event = await service.create_event(request)
        assert event is not None
        assert event.recurrence_type == RecurrenceType.DAILY


class TestEventCategoryValidation:
    """Test event category validation"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        mock_repo = MockCalendarRepository()
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_create_event_with_each_category(self, service):
        """Test creating events with each category type"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        categories = [
            EventCategory.WORK,
            EventCategory.PERSONAL,
            EventCategory.MEETING,
            EventCategory.REMINDER,
            EventCategory.HOLIDAY,
            EventCategory.BIRTHDAY,
            EventCategory.OTHER,
        ]

        for category in categories:
            request = EventCreateRequest(
                user_id="user_123",
                title=f"{category.value} event",
                start_time=now,
                end_time=future,
                category=category,
            )

            event = await service.create_event(request)
            assert event is not None
            assert event.category == category


class TestEventSharingValidation:
    """Test event sharing validation"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        mock_repo = MockCalendarRepository()
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_create_shared_event(self, service):
        """Test creating shared event"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Team Event",
            start_time=now,
            end_time=future,
            is_shared=True,
            shared_with=["user_456", "user_789"],
        )

        event = await service.create_event(request)
        assert event is not None
        assert event.is_shared is True

    @pytest.mark.asyncio
    async def test_create_private_event(self, service):
        """Test creating private event"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Private Event",
            start_time=now,
            end_time=future,
            is_shared=False,
        )

        event = await service.create_event(request)
        assert event is not None
        assert event.is_shared is False


class TestReminderValidation:
    """Test reminder validation"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        mock_repo = MockCalendarRepository()
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_create_event_with_reminders(self, service):
        """Test creating event with multiple reminders"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Important Meeting",
            start_time=now,
            end_time=future,
            reminders=[5, 15, 30, 60],
        )

        event = await service.create_event(request)
        assert event is not None
        assert len(event.reminders) == 4
        assert 5 in event.reminders
        assert 60 in event.reminders

    @pytest.mark.asyncio
    async def test_create_event_without_reminders(self, service):
        """Test creating event without reminders"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Simple Event",
            start_time=now,
            end_time=future,
        )

        event = await service.create_event(request)
        assert event is not None
        assert event.reminders == []


class TestAllDayEventValidation:
    """Test all-day event validation"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        mock_repo = MockCalendarRepository()
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_create_all_day_event(self, service):
        """Test creating all-day event"""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Conference Day",
            start_time=today,
            end_time=tomorrow,
            all_day=True,
        )

        event = await service.create_event(request)
        assert event is not None
        assert event.all_day is True

    @pytest.mark.asyncio
    async def test_create_timed_event(self, service):
        """Test creating timed event"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        request = EventCreateRequest(
            user_id="user_123",
            title="Timed Event",
            start_time=now,
            end_time=future,
            all_day=False,
        )

        event = await service.create_event(request)
        assert event is not None
        assert event.all_day is False
