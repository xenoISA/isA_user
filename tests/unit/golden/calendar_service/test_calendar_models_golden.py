"""
Unit Golden Tests: Calendar Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.calendar_service.models import (
    CalendarEvent,
    EventCategory,
    EventCreateRequest,
    EventUpdateRequest,
    EventQueryRequest,
    EventResponse,
    EventListResponse,
    RecurrenceType,
    SyncProvider,
    SyncStatusResponse,
)


class TestCalendarEventModel:
    """Test CalendarEvent model validation"""

    def test_calendar_event_creation_with_all_fields(self):
        """Test creating calendar event with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        event = CalendarEvent(
            event_id="evt_123",
            user_id="user_456",
            organization_id="org_789",
            title="Team Meeting",
            description="Quarterly review meeting",
            location="Conference Room A",
            start_time=now,
            end_time=future,
            all_day=False,
            timezone="America/New_York",
            category=EventCategory.MEETING,
            color="#FF5733",
            recurrence_type=RecurrenceType.WEEKLY,
            recurrence_end_date=now + timedelta(days=90),
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
            reminders=[15, 30],
            sync_provider=SyncProvider.GOOGLE,
            external_event_id="google_evt_xyz",
            is_shared=True,
            shared_with=["user_001", "user_002"],
            metadata={"project": "Q4 Review"},
            created_at=now,
            updated_at=now,
        )

        assert event.event_id == "evt_123"
        assert event.user_id == "user_456"
        assert event.title == "Team Meeting"
        assert event.category == EventCategory.MEETING
        assert event.recurrence_type == RecurrenceType.WEEKLY
        assert len(event.reminders) == 2
        assert event.is_shared is True

    def test_calendar_event_with_minimal_fields(self):
        """Test creating calendar event with only required fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        event = CalendarEvent(
            event_id="evt_minimal",
            user_id="user_123",
            title="Quick Note",
            start_time=now,
            end_time=future,
        )

        assert event.event_id == "evt_minimal"
        assert event.all_day is False
        assert event.timezone == "UTC"
        assert event.category == EventCategory.OTHER
        assert event.recurrence_type == RecurrenceType.NONE
        assert event.reminders == []
        assert event.is_shared is False

    def test_calendar_event_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            CalendarEvent(user_id="user_123", title="Test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "event_id" in missing_fields
        assert "start_time" in missing_fields
        assert "end_time" in missing_fields


class TestEventCreateRequest:
    """Test EventCreateRequest model validation"""

    def test_event_create_request_valid(self):
        """Test valid event creation request"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        request = EventCreateRequest(
            user_id="user_123",
            title="New Event",
            start_time=now,
            end_time=future,
            category=EventCategory.WORK,
            reminders=[10, 30],
        )

        assert request.user_id == "user_123"
        assert request.title == "New Event"
        assert request.category == EventCategory.WORK
        assert len(request.reminders) == 2

    def test_event_create_request_with_recurrence(self):
        """Test event creation with recurrence"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Weekly Standup",
            start_time=now,
            end_time=future,
            recurrence_type=RecurrenceType.WEEKLY,
            recurrence_end_date=now + timedelta(days=60),
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO,WE,FR",
        )

        assert request.recurrence_type == RecurrenceType.WEEKLY
        assert request.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO,WE,FR"

    def test_event_create_request_defaults(self):
        """Test default values for optional fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = EventCreateRequest(
            user_id="user_123",
            title="Test Event",
            start_time=now,
            end_time=future,
        )

        assert request.all_day is False
        assert request.timezone == "UTC"
        assert request.category == EventCategory.OTHER
        assert request.recurrence_type == RecurrenceType.NONE
        assert request.reminders == []
        assert request.is_shared is False


class TestEventUpdateRequest:
    """Test EventUpdateRequest model validation"""

    def test_event_update_request_partial(self):
        """Test partial update request"""
        request = EventUpdateRequest(
            title="Updated Title",
            description="New description",
        )

        assert request.title == "Updated Title"
        assert request.description == "New description"
        assert request.start_time is None
        assert request.category is None

    def test_event_update_request_all_fields(self):
        """Test update request with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        request = EventUpdateRequest(
            title="Updated Event",
            description="Updated description",
            location="New Location",
            start_time=now,
            end_time=future,
            all_day=True,
            category=EventCategory.PERSONAL,
            color="#00FF00",
            recurrence_type=RecurrenceType.MONTHLY,
            reminders=[5, 15, 30],
            is_shared=True,
            shared_with=["user_001"],
        )

        assert request.title == "Updated Event"
        assert request.all_day is True
        assert request.category == EventCategory.PERSONAL
        assert len(request.reminders) == 3


class TestEventQueryRequest:
    """Test EventQueryRequest model validation"""

    def test_event_query_request_defaults(self):
        """Test default query parameters"""
        request = EventQueryRequest(user_id="user_123")

        assert request.user_id == "user_123"
        assert request.start_date is None
        assert request.end_date is None
        assert request.category is None
        assert request.limit == 100
        assert request.offset == 0

    def test_event_query_request_with_filters(self):
        """Test query request with filters"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        request = EventQueryRequest(
            user_id="user_123",
            start_date=now,
            end_date=future,
            category=EventCategory.WORK,
            limit=50,
            offset=10,
        )

        assert request.start_date == now
        assert request.end_date == future
        assert request.category == EventCategory.WORK
        assert request.limit == 50
        assert request.offset == 10

    def test_event_query_request_limit_validation(self):
        """Test limit validation (min/max constraints)"""
        # Test minimum limit
        with pytest.raises(ValidationError):
            EventQueryRequest(user_id="user_123", limit=0)

        # Test maximum limit
        with pytest.raises(ValidationError):
            EventQueryRequest(user_id="user_123", limit=1001)

    def test_event_query_request_offset_validation(self):
        """Test offset validation (non-negative)"""
        with pytest.raises(ValidationError):
            EventQueryRequest(user_id="user_123", offset=-1)


class TestEventResponse:
    """Test EventResponse model"""

    def test_event_response_creation(self):
        """Test creating event response"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        response = EventResponse(
            event_id="evt_123",
            user_id="user_456",
            title="Test Event",
            description="Test description",
            location="Test location",
            start_time=now,
            end_time=future,
            all_day=False,
            category=EventCategory.MEETING,
            color="#FF5733",
            recurrence_type=RecurrenceType.NONE,
            reminders=[15],
            is_shared=False,
            created_at=now,
            updated_at=now,
        )

        assert response.event_id == "evt_123"
        assert response.user_id == "user_456"
        assert response.title == "Test Event"
        assert response.category == EventCategory.MEETING


class TestEventListResponse:
    """Test EventListResponse model"""

    def test_event_list_response(self):
        """Test event list response"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        events = [
            EventResponse(
                event_id=f"evt_{i}",
                user_id="user_123",
                title=f"Event {i}",
                description=None,
                location=None,
                start_time=now,
                end_time=future,
                all_day=False,
                category=EventCategory.OTHER,
                color=None,
                recurrence_type=RecurrenceType.NONE,
                reminders=[],
                is_shared=False,
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]

        response = EventListResponse(
            events=events,
            total=3,
            page=1,
            page_size=100,
        )

        assert len(response.events) == 3
        assert response.total == 3
        assert response.page == 1
        assert response.page_size == 100


class TestSyncStatusResponse:
    """Test SyncStatusResponse model"""

    def test_sync_status_response_success(self):
        """Test successful sync status"""
        now = datetime.now(timezone.utc)

        response = SyncStatusResponse(
            provider=SyncProvider.GOOGLE,
            last_synced=now,
            synced_events=42,
            status="success",
            message="Successfully synced 42 events",
        )

        assert response.provider == SyncProvider.GOOGLE
        assert response.synced_events == 42
        assert response.status == "success"

    def test_sync_status_response_error(self):
        """Test error sync status"""
        now = datetime.now(timezone.utc)

        response = SyncStatusResponse(
            provider=SyncProvider.OUTLOOK,
            last_synced=now,
            synced_events=0,
            status="error",
            message="Authentication failed",
        )

        assert response.provider == SyncProvider.OUTLOOK
        assert response.synced_events == 0
        assert response.status == "error"
        assert "Authentication failed" in response.message


class TestEnumTypes:
    """Test enum type definitions"""

    def test_recurrence_type_values(self):
        """Test RecurrenceType enum values"""
        assert RecurrenceType.NONE == "none"
        assert RecurrenceType.DAILY == "daily"
        assert RecurrenceType.WEEKLY == "weekly"
        assert RecurrenceType.MONTHLY == "monthly"
        assert RecurrenceType.YEARLY == "yearly"
        assert RecurrenceType.CUSTOM == "custom"

    def test_event_category_values(self):
        """Test EventCategory enum values"""
        assert EventCategory.WORK == "work"
        assert EventCategory.PERSONAL == "personal"
        assert EventCategory.MEETING == "meeting"
        assert EventCategory.REMINDER == "reminder"
        assert EventCategory.HOLIDAY == "holiday"
        assert EventCategory.BIRTHDAY == "birthday"
        assert EventCategory.OTHER == "other"

    def test_sync_provider_values(self):
        """Test SyncProvider enum values"""
        assert SyncProvider.GOOGLE == "google_calendar"
        assert SyncProvider.APPLE == "apple_calendar"
        assert SyncProvider.OUTLOOK == "outlook"
        assert SyncProvider.LOCAL == "local"
