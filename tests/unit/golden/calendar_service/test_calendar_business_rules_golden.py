"""
Unit Golden Tests: Calendar Service Business Rules

Tests all BR-CAL-* business rules from logic_contract.md.
Uses CalendarTestDataFactory for zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from tests.contracts.calendar import (
    CalendarTestDataFactory,
    EventCreateRequestContract,
    EventUpdateRequestContract,
    EventQueryRequestContract,
    EventCategoryContract,
    RecurrenceTypeContract,
    SyncProviderContract,
    EventCreateRequestBuilder,
    EventUpdateRequestBuilder,
    EventQueryRequestBuilder,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# ============================================================================
# BR-CAL-001: Event ID Generation
# ============================================================================

class TestEventIdGeneration:
    """Tests for BR-CAL-001: Event ID Generation"""

    def test_event_id_format_valid(self):
        """BR-CAL-001: Event ID must match format evt_<uuid16>"""
        event_id = CalendarTestDataFactory.make_event_id()

        assert event_id.startswith("evt_")
        assert len(event_id) == 20  # evt_ (4) + 16 hex chars
        # Verify hex characters after prefix
        hex_part = event_id[4:]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_event_id_uniqueness(self):
        """BR-CAL-001: Event IDs must be unique"""
        ids = [CalendarTestDataFactory.make_event_id() for _ in range(100)]
        assert len(ids) == len(set(ids))  # All unique

    def test_user_id_format(self):
        """User IDs follow usr_<uuid12> format"""
        user_id = CalendarTestDataFactory.make_user_id()

        assert user_id.startswith("usr_")
        assert len(user_id) == 16  # usr_ (4) + 12 hex chars

    def test_organization_id_format(self):
        """Organization IDs follow org_<uuid12> format"""
        org_id = CalendarTestDataFactory.make_organization_id()

        assert org_id.startswith("org_")
        assert len(org_id) == 16  # org_ (4) + 12 hex chars


# ============================================================================
# BR-CAL-002: Title Validation
# ============================================================================

class TestTitleValidation:
    """Tests for BR-CAL-002: Title Validation"""

    def test_title_valid_simple(self):
        """BR-CAL-002: Valid title (1-255 characters)"""
        request = CalendarTestDataFactory.make_create_request(
            title="Valid Title"
        )
        assert request.title == "Valid Title"

    def test_title_boundary_1_char(self):
        """BR-CAL-002: Minimum title length is 1 character"""
        request = CalendarTestDataFactory.make_create_request(title="X")
        assert len(request.title) == 1

    def test_title_boundary_255_chars(self):
        """BR-CAL-002: Maximum title length is 255 characters"""
        long_title = "A" * 255
        request = CalendarTestDataFactory.make_create_request(title=long_title)
        assert len(request.title) == 255

    def test_title_empty_raises_error(self):
        """BR-CAL-002: Empty title raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTestDataFactory.make_create_request(
                title=CalendarTestDataFactory.make_invalid_title_empty()
            )
        assert "title" in str(exc_info.value).lower()

    def test_title_whitespace_only_raises_error(self):
        """BR-CAL-002: Whitespace-only title raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTestDataFactory.make_create_request(
                title=CalendarTestDataFactory.make_invalid_title_whitespace()
            )
        assert "title" in str(exc_info.value).lower()

    def test_title_over_255_chars_raises_error(self):
        """BR-CAL-002: Title over 255 characters raises ValidationError"""
        long_title = "A" * 256
        with pytest.raises(ValidationError):
            CalendarTestDataFactory.make_create_request(title=long_title)

    def test_title_whitespace_trimmed(self):
        """BR-CAL-002: Leading/trailing whitespace is trimmed"""
        request = CalendarTestDataFactory.make_create_request(
            title="  Trimmed Title  "
        )
        assert request.title == "Trimmed Title"

    def test_title_with_unicode(self):
        """BR-CAL-002/EC-003: Unicode characters in title are accepted"""
        request = CalendarTestDataFactory.make_create_request(
            title="会议 Meeting 🎉"
        )
        assert "会议" in request.title
        assert "🎉" in request.title

    def test_title_with_special_chars(self):
        """EC-004: Special characters treated as literals"""
        request = CalendarTestDataFactory.make_create_request(
            title="Test'; DROP TABLE--"
        )
        assert "DROP TABLE" in request.title  # Stored as literal


# ============================================================================
# BR-CAL-003: Time Validation (End > Start)
# ============================================================================

class TestTimeValidation:
    """Tests for BR-CAL-003: Time Validation"""

    def test_valid_time_range(self):
        """BR-CAL-003: end_time > start_time is accepted"""
        start, end = CalendarTestDataFactory.make_time_range(duration_hours=2)

        request = CalendarTestDataFactory.make_create_request(
            start_time=start,
            end_time=end
        )

        assert request.end_time > request.start_time

    def test_end_before_start_raises_error(self):
        """BR-CAL-003: end_time < start_time raises ValidationError"""
        start, end = CalendarTestDataFactory.make_invalid_time_range()

        with pytest.raises(ValidationError) as exc_info:
            CalendarTestDataFactory.make_create_request(
                start_time=start,
                end_time=end
            )
        assert "end_time" in str(exc_info.value).lower()

    def test_equal_times_raises_error(self):
        """BR-CAL-003: end_time == start_time raises ValidationError"""
        now = CalendarTestDataFactory.make_timestamp()

        with pytest.raises(ValidationError) as exc_info:
            CalendarTestDataFactory.make_create_request(
                start_time=now,
                end_time=now
            )
        assert "end_time" in str(exc_info.value).lower()

    def test_minimal_duration_accepted(self):
        """BR-CAL-003: Minimal duration (1 second) is accepted"""
        start = CalendarTestDataFactory.make_timestamp()
        end = start + timedelta(seconds=1)

        request = CalendarTestDataFactory.make_create_request(
            start_time=start,
            end_time=end
        )
        assert (request.end_time - request.start_time).total_seconds() == 1

    def test_long_duration_event(self):
        """EC-007: Very long duration event accepted"""
        start = CalendarTestDataFactory.make_timestamp()
        end = start + timedelta(days=7)  # Week-long event

        request = CalendarTestDataFactory.make_create_request(
            start_time=start,
            end_time=end
        )
        assert (request.end_time - request.start_time).days == 7


# ============================================================================
# BR-CAL-004: All-Day Event Handling
# ============================================================================

class TestAllDayEventHandling:
    """Tests for BR-CAL-004: All-Day Event Handling"""

    def test_all_day_event_creation(self):
        """BR-CAL-004: All-day events accepted"""
        request = CalendarTestDataFactory.make_create_request_all_day()
        assert request.all_day is True

    def test_all_day_spans_full_day(self):
        """BR-CAL-004: All-day event duration spans full calendar day"""
        request = CalendarTestDataFactory.make_create_request_all_day()
        duration = request.end_time - request.start_time
        assert duration >= timedelta(hours=23)  # At least 23 hours

    def test_non_all_day_default(self):
        """BR-CAL-004: Default is not all-day"""
        request = CalendarTestDataFactory.make_create_request_minimal()
        assert request.all_day is False


# ============================================================================
# BR-CAL-005: Color Validation
# ============================================================================

class TestColorValidation:
    """Tests for BR-CAL-005: Color Validation"""

    def test_valid_color_format(self):
        """BR-CAL-005: Valid #RRGGBB format accepted"""
        request = CalendarTestDataFactory.make_create_request(
            color=CalendarTestDataFactory.make_color()
        )
        assert request.color.startswith("#")
        assert len(request.color) == 7

    def test_color_uppercase_accepted(self):
        """BR-CAL-005: Uppercase hex accepted"""
        request = CalendarTestDataFactory.make_create_request(color="#ABC123")
        assert request.color == "#ABC123"

    def test_color_lowercase_accepted(self):
        """BR-CAL-005: Lowercase hex accepted"""
        request = CalendarTestDataFactory.make_create_request(color="#abc123")
        assert request.color == "#abc123"

    def test_color_invalid_format_raises_error(self):
        """BR-CAL-005: Invalid format raises ValidationError"""
        with pytest.raises(ValidationError):
            CalendarTestDataFactory.make_create_request(
                color=CalendarTestDataFactory.make_invalid_color()
            )

    def test_color_short_format_raises_error(self):
        """BR-CAL-005: Short format (#RGB) not accepted"""
        with pytest.raises(ValidationError):
            CalendarTestDataFactory.make_create_request(color="#ABC")

    def test_color_null_accepted(self):
        """BR-CAL-005: Null/empty color accepted (optional field)"""
        request = CalendarTestDataFactory.make_create_request(color=None)
        assert request.color is None


# ============================================================================
# BR-CAL-006: Reminders Validation
# ============================================================================

class TestRemindersValidation:
    """Tests for BR-CAL-006: Reminders Validation"""

    def test_valid_reminders(self):
        """BR-CAL-006: Valid reminder list accepted"""
        reminders = CalendarTestDataFactory.make_reminders(count=3)
        request = CalendarTestDataFactory.make_create_request(reminders=reminders)
        assert len(request.reminders) == 3

    def test_maximum_5_reminders(self):
        """BR-CAL-006: Maximum 5 reminders allowed"""
        request = CalendarTestDataFactory.make_create_request(
            reminders=[5, 10, 15, 30, 60]
        )
        assert len(request.reminders) == 5

    def test_over_5_reminders_raises_error(self):
        """BR-CAL-006: 6+ reminders raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTestDataFactory.make_create_request(
                reminders=CalendarTestDataFactory.make_invalid_reminders()
            )
        assert "maximum 5 reminders" in str(exc_info.value).lower()

    def test_negative_reminder_raises_error(self):
        """BR-CAL-006: Negative reminder raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            CalendarTestDataFactory.make_create_request(
                reminders=CalendarTestDataFactory.make_invalid_reminder_negative()
            )
        assert "positive" in str(exc_info.value).lower()

    def test_zero_reminder_raises_error(self):
        """BR-CAL-006: Zero reminder raises ValidationError"""
        with pytest.raises(ValidationError):
            CalendarTestDataFactory.make_create_request(reminders=[0])

    def test_empty_reminders_accepted(self):
        """BR-CAL-006: Empty reminders list accepted"""
        request = CalendarTestDataFactory.make_create_request(reminders=[])
        assert request.reminders == []

    def test_large_reminder_value_accepted(self):
        """EC-008: Large reminder values accepted (1 year = 525600 minutes)"""
        request = CalendarTestDataFactory.make_create_request(
            reminders=[525600]  # 1 year in minutes
        )
        assert 525600 in request.reminders


# ============================================================================
# BR-CAL-010 - BR-CAL-013: Query Rules
# ============================================================================

class TestQueryRules:
    """Tests for BR-CAL-010 through BR-CAL-013: Query Rules"""

    def test_query_with_date_range(self):
        """BR-CAL-010: Query by date range"""
        request = CalendarTestDataFactory.make_query_request_date_range()
        assert request.start_date is not None
        assert request.end_date is not None
        assert request.start_date < request.end_date

    def test_query_with_category_filter(self):
        """BR-CAL-013: Category filter"""
        request = (
            EventQueryRequestBuilder()
            .with_user_id(CalendarTestDataFactory.make_user_id())
            .with_category(EventCategoryContract.MEETING)
            .build()
        )
        assert request.category == EventCategoryContract.MEETING

    def test_query_pagination_defaults(self):
        """BR-CAL-010: Pagination defaults"""
        request = CalendarTestDataFactory.make_query_request()
        assert request.limit == 100
        assert request.offset == 0

    def test_query_limit_minimum(self):
        """Query limit minimum is 1"""
        request = CalendarTestDataFactory.make_query_request(limit=1)
        assert request.limit == 1

    def test_query_limit_maximum(self):
        """Query limit maximum is 1000"""
        request = CalendarTestDataFactory.make_query_request(limit=1000)
        assert request.limit == 1000

    def test_query_limit_below_minimum_raises_error(self):
        """Query limit below 1 raises ValidationError"""
        with pytest.raises(ValidationError):
            CalendarTestDataFactory.make_query_request(limit=0)

    def test_query_limit_above_maximum_raises_error(self):
        """Query limit above 1000 raises ValidationError"""
        with pytest.raises(ValidationError):
            CalendarTestDataFactory.make_query_request(limit=1001)

    def test_query_offset_negative_raises_error(self):
        """Negative offset raises ValidationError"""
        with pytest.raises(ValidationError):
            CalendarTestDataFactory.make_query_request(offset=-1)


# ============================================================================
# BR-CAL-020 - BR-CAL-022: Update Rules
# ============================================================================

class TestUpdateRules:
    """Tests for BR-CAL-020 through BR-CAL-022: Update Rules"""

    def test_partial_update_title_only(self):
        """BR-CAL-020: Partial update with title only"""
        request = EventUpdateRequestBuilder().with_title("New Title").build()

        assert request.title == "New Title"
        assert request.description is None
        assert request.start_time is None

    def test_partial_update_description_only(self):
        """BR-CAL-020: Partial update with description only"""
        request = EventUpdateRequestBuilder().with_description("New Description").build()

        assert request.description == "New Description"
        assert request.title is None

    def test_update_with_valid_time_range(self):
        """BR-CAL-022: Update with valid time range"""
        start = CalendarTestDataFactory.make_timestamp() + timedelta(days=1)
        end = start + timedelta(hours=2)

        request = (
            EventUpdateRequestBuilder()
            .with_time_range(start, end)
            .build()
        )

        assert request.start_time == start
        assert request.end_time == end

    def test_update_category(self):
        """BR-CAL-020: Update category"""
        request = (
            EventUpdateRequestBuilder()
            .with_category(EventCategoryContract.MEETING)
            .build()
        )
        assert request.category == EventCategoryContract.MEETING


# ============================================================================
# BR-CAL-040 - BR-CAL-042: External Sync Rules
# ============================================================================

class TestExternalSyncRules:
    """Tests for BR-CAL-040 through BR-CAL-042: External Sync Rules"""

    def test_google_calendar_provider(self):
        """BR-CAL-040: Google calendar provider supported"""
        request = CalendarTestDataFactory.make_sync_request(
            provider=SyncProviderContract.GOOGLE
        )
        assert request.provider == SyncProviderContract.GOOGLE

    def test_apple_calendar_provider(self):
        """BR-CAL-040: Apple calendar provider supported"""
        request = CalendarTestDataFactory.make_sync_request(
            provider=SyncProviderContract.APPLE
        )
        assert request.provider == SyncProviderContract.APPLE

    def test_outlook_provider(self):
        """BR-CAL-040: Outlook provider supported"""
        request = CalendarTestDataFactory.make_sync_request(
            provider=SyncProviderContract.OUTLOOK
        )
        assert request.provider == SyncProviderContract.OUTLOOK

    def test_sync_with_credentials(self):
        """BR-CAL-040: Sync with credentials"""
        credentials = CalendarTestDataFactory.make_credentials()
        request = CalendarTestDataFactory.make_sync_request(credentials=credentials)

        assert request.credentials is not None
        assert "access_token" in request.credentials


# ============================================================================
# BR-CAL-050 - BR-CAL-052: Recurrence Rules
# ============================================================================

class TestRecurrenceRules:
    """Tests for BR-CAL-050 through BR-CAL-052: Recurrence Rules"""

    def test_recurrence_type_none(self):
        """BR-CAL-050: Recurrence type none"""
        request = CalendarTestDataFactory.make_create_request(
            recurrence_type=RecurrenceTypeContract.NONE
        )
        assert request.recurrence_type == RecurrenceTypeContract.NONE

    def test_recurrence_type_daily(self):
        """BR-CAL-050: Recurrence type daily"""
        request = CalendarTestDataFactory.make_create_request(
            recurrence_type=RecurrenceTypeContract.DAILY
        )
        assert request.recurrence_type == RecurrenceTypeContract.DAILY

    def test_recurrence_type_weekly(self):
        """BR-CAL-050: Recurrence type weekly"""
        request = CalendarTestDataFactory.make_create_request_recurring()
        assert request.recurrence_type == RecurrenceTypeContract.WEEKLY

    def test_recurrence_type_monthly(self):
        """BR-CAL-050: Recurrence type monthly"""
        request = CalendarTestDataFactory.make_create_request(
            recurrence_type=RecurrenceTypeContract.MONTHLY
        )
        assert request.recurrence_type == RecurrenceTypeContract.MONTHLY

    def test_recurrence_type_yearly(self):
        """BR-CAL-050: Recurrence type yearly"""
        request = CalendarTestDataFactory.make_create_request(
            recurrence_type=RecurrenceTypeContract.YEARLY
        )
        assert request.recurrence_type == RecurrenceTypeContract.YEARLY

    def test_recurrence_type_custom(self):
        """BR-CAL-050: Recurrence type custom"""
        request = CalendarTestDataFactory.make_create_request(
            recurrence_type=RecurrenceTypeContract.CUSTOM
        )
        assert request.recurrence_type == RecurrenceTypeContract.CUSTOM

    def test_recurrence_end_date(self):
        """BR-CAL-051: Recurrence end date"""
        request = CalendarTestDataFactory.make_create_request_recurring()
        assert request.recurrence_end_date is not None
        assert request.recurrence_end_date > request.start_time

    def test_custom_rrule(self):
        """BR-CAL-052: Custom RRULE format"""
        rrule = CalendarTestDataFactory.make_rrule()

        request = (
            EventCreateRequestBuilder()
            .with_rrule(rrule)
            .build()
        )

        assert request.recurrence_type == RecurrenceTypeContract.CUSTOM
        assert "FREQ=" in request.recurrence_rule


# ============================================================================
# BR-CAL-060 - BR-CAL-061: Sharing Rules
# ============================================================================

class TestSharingRules:
    """Tests for BR-CAL-060 - BR-CAL-061: Sharing Rules"""

    def test_shared_event_creation(self):
        """BR-CAL-060: Shared event with user IDs"""
        request = CalendarTestDataFactory.make_create_request_shared()

        assert request.is_shared is True
        assert len(request.shared_with) > 0

    def test_private_event_default(self):
        """BR-CAL-060: Default is not shared"""
        request = CalendarTestDataFactory.make_create_request_minimal()
        assert request.is_shared is False
        assert request.shared_with == []

    def test_shared_with_multiple_users(self):
        """BR-CAL-060: Share with multiple users"""
        shared_with = CalendarTestDataFactory.make_shared_with(count=5)
        request = CalendarTestDataFactory.make_create_request(
            is_shared=True,
            shared_with=shared_with
        )

        assert len(request.shared_with) == 5


# ============================================================================
# Event Category Tests
# ============================================================================

class TestEventCategories:
    """Tests for all event categories"""

    def test_category_work(self):
        """Category WORK"""
        assert EventCategoryContract.WORK.value == "work"

    def test_category_personal(self):
        """Category PERSONAL"""
        assert EventCategoryContract.PERSONAL.value == "personal"

    def test_category_meeting(self):
        """Category MEETING"""
        assert EventCategoryContract.MEETING.value == "meeting"

    def test_category_reminder(self):
        """Category REMINDER"""
        assert EventCategoryContract.REMINDER.value == "reminder"

    def test_category_holiday(self):
        """Category HOLIDAY"""
        assert EventCategoryContract.HOLIDAY.value == "holiday"

    def test_category_birthday(self):
        """Category BIRTHDAY"""
        assert EventCategoryContract.BIRTHDAY.value == "birthday"

    def test_category_other(self):
        """Category OTHER (default)"""
        assert EventCategoryContract.OTHER.value == "other"

    def test_all_categories_in_enum(self):
        """All 7 categories exist"""
        assert len(list(EventCategoryContract)) == 7


# ============================================================================
# Request Builder Tests
# ============================================================================

class TestRequestBuilders:
    """Tests for fluent request builders"""

    def test_create_request_builder_fluent(self):
        """EventCreateRequestBuilder fluent API"""
        user_id = CalendarTestDataFactory.make_user_id()

        request = (
            EventCreateRequestBuilder()
            .with_user_id(user_id)
            .with_title("Team Standup")
            .with_description("Daily sync")
            .with_category(EventCategoryContract.MEETING)
            .with_reminders([10, 30])
            .build()
        )

        assert request.user_id == user_id
        assert request.title == "Team Standup"
        assert request.description == "Daily sync"
        assert request.category == EventCategoryContract.MEETING
        assert 10 in request.reminders

    def test_create_request_builder_to_dict(self):
        """EventCreateRequestBuilder build_dict() method"""
        request_dict = (
            EventCreateRequestBuilder()
            .with_title("Test Event")
            .build_dict()
        )

        assert isinstance(request_dict, dict)
        assert "title" in request_dict
        assert "start_time" in request_dict
        assert isinstance(request_dict["start_time"], str)  # ISO format

    def test_update_request_builder_fluent(self):
        """EventUpdateRequestBuilder fluent API"""
        request = (
            EventUpdateRequestBuilder()
            .with_title("Updated Title")
            .with_description("Updated Description")
            .with_category(EventCategoryContract.PERSONAL)
            .build()
        )

        assert request.title == "Updated Title"
        assert request.description == "Updated Description"
        assert request.category == EventCategoryContract.PERSONAL

    def test_query_request_builder_fluent(self):
        """EventQueryRequestBuilder fluent API"""
        user_id = CalendarTestDataFactory.make_user_id()
        start = CalendarTestDataFactory.make_today_start()
        end = CalendarTestDataFactory.make_future_timestamp(7)

        request = (
            EventQueryRequestBuilder()
            .with_user_id(user_id)
            .with_date_range(start, end)
            .with_category(EventCategoryContract.WORK)
            .with_pagination(limit=50, offset=10)
            .build()
        )

        assert request.user_id == user_id
        assert request.start_date == start
        assert request.end_date == end
        assert request.category == EventCategoryContract.WORK
        assert request.limit == 50
        assert request.offset == 10


# ============================================================================
# Sync Provider Tests
# ============================================================================

class TestSyncProviders:
    """Tests for sync provider enum"""

    def test_provider_google(self):
        """Google Calendar provider"""
        assert SyncProviderContract.GOOGLE.value == "google_calendar"

    def test_provider_apple(self):
        """Apple Calendar provider"""
        assert SyncProviderContract.APPLE.value == "apple_calendar"

    def test_provider_outlook(self):
        """Outlook provider"""
        assert SyncProviderContract.OUTLOOK.value == "outlook"

    def test_provider_local(self):
        """Local provider (no sync)"""
        assert SyncProviderContract.LOCAL.value == "local"

    def test_all_providers_in_enum(self):
        """All 4 providers exist"""
        assert len(list(SyncProviderContract)) == 4


# ============================================================================
# Factory Method Tests
# ============================================================================

class TestFactoryMethods:
    """Tests for CalendarTestDataFactory methods"""

    def test_make_timestamp_utc(self):
        """Timestamps are in UTC"""
        ts = CalendarTestDataFactory.make_timestamp()
        assert ts.tzinfo == timezone.utc

    def test_make_past_timestamp(self):
        """Past timestamp is before now"""
        past = CalendarTestDataFactory.make_past_timestamp(days=30)
        now = CalendarTestDataFactory.make_timestamp()
        assert past < now

    def test_make_future_timestamp(self):
        """Future timestamp is after now"""
        future = CalendarTestDataFactory.make_future_timestamp(days=30)
        now = CalendarTestDataFactory.make_timestamp()
        assert future > now

    def test_make_time_range_duration(self):
        """Time range respects duration"""
        start, end = CalendarTestDataFactory.make_time_range(duration_hours=3)
        duration = end - start
        assert duration == timedelta(hours=3)

    def test_make_today_start_midnight(self):
        """Today start is at midnight"""
        today = CalendarTestDataFactory.make_today_start()
        assert today.hour == 0
        assert today.minute == 0
        assert today.second == 0

    def test_make_today_end_end_of_day(self):
        """Today end is at 23:59:59"""
        today = CalendarTestDataFactory.make_today_end()
        assert today.hour == 23
        assert today.minute == 59
        assert today.second == 59

    def test_make_title_unique(self):
        """Titles are unique"""
        titles = [CalendarTestDataFactory.make_title() for _ in range(50)]
        assert len(titles) == len(set(titles))

    def test_make_color_valid_hex(self):
        """Colors are valid hex format"""
        for _ in range(10):
            color = CalendarTestDataFactory.make_color()
            assert color.startswith("#")
            assert len(color) == 7
            # Verify hex chars
            hex_part = color[1:]
            assert all(c in "0123456789ABCDEFabcdef" for c in hex_part)

    def test_make_reminders_count(self):
        """Reminders list has correct count"""
        for count in [1, 2, 3, 4, 5]:
            reminders = CalendarTestDataFactory.make_reminders(count=count)
            assert len(reminders) == count

    def test_make_reminders_max_5(self):
        """Reminders capped at 5 even if more requested"""
        reminders = CalendarTestDataFactory.make_reminders(count=10)
        assert len(reminders) == 5

    def test_make_metadata_structure(self):
        """Metadata has expected structure"""
        metadata = CalendarTestDataFactory.make_metadata()
        assert "source" in metadata
        assert "priority" in metadata
        assert "tags" in metadata
        assert isinstance(metadata["tags"], list)

    def test_make_credentials_structure(self):
        """Credentials have expected structure"""
        credentials = CalendarTestDataFactory.make_credentials()
        assert "access_token" in credentials
        assert "refresh_token" in credentials
        assert "expires_at" in credentials

    def test_make_response_dict(self):
        """Response dict has all required fields"""
        response = CalendarTestDataFactory.make_response()

        required_fields = [
            "event_id", "user_id", "title", "start_time", "end_time",
            "all_day", "category", "recurrence_type", "reminders",
            "is_shared", "created_at"
        ]

        for field in required_fields:
            assert field in response
