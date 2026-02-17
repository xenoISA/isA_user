"""
Calendar Service - Data Contract

Pydantic schemas, test data factory, and request builders.
Zero hardcoded data - all test data generated through factory methods.

Usage:
    from tests.contracts.calendar.data_contract import (
        CalendarTestDataFactory,
        EventCreateRequestContract,
        EventResponseContract,
    )
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from enum import Enum
import secrets
import uuid


# ============================================================================
# Enums
# ============================================================================

class RecurrenceTypeContract(str, Enum):
    """Event recurrence type"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class EventCategoryContract(str, Enum):
    """Event category"""
    WORK = "work"
    PERSONAL = "personal"
    MEETING = "meeting"
    REMINDER = "reminder"
    HOLIDAY = "holiday"
    BIRTHDAY = "birthday"
    OTHER = "other"


class SyncProviderContract(str, Enum):
    """External calendar provider"""
    GOOGLE = "google_calendar"
    APPLE = "apple_calendar"
    OUTLOOK = "outlook"
    LOCAL = "local"


class SyncStatusContract(str, Enum):
    """Sync status"""
    ACTIVE = "active"
    ERROR = "error"
    PENDING = "pending"
    SUCCESS = "success"


# ============================================================================
# Request Contracts
# ============================================================================

class EventCreateRequestContract(BaseModel):
    """Contract for event creation requests"""
    user_id: str = Field(..., min_length=1, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, max_length=500, description="Event location")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    all_day: bool = Field(False, description="Is all-day event")
    timezone: str = Field("UTC", description="Timezone")
    category: EventCategoryContract = Field(EventCategoryContract.OTHER, description="Category")
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Color (#RRGGBB)")
    recurrence_type: RecurrenceTypeContract = Field(RecurrenceTypeContract.NONE, description="Recurrence")
    recurrence_end_date: Optional[datetime] = Field(None, description="Recurrence end date")
    recurrence_rule: Optional[str] = Field(None, description="iCalendar RRULE")
    reminders: List[int] = Field(default_factory=list, description="Reminder minutes")
    is_shared: bool = Field(False, description="Is shared")
    shared_with: List[str] = Field(default_factory=list, description="Shared user IDs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Title must not be empty or whitespace only"""
        if not v or not v.strip():
            raise ValueError("title cannot be empty or whitespace")
        return v.strip()

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        """End time must be after start time"""
        start_time = info.data.get('start_time')
        if start_time and v <= start_time:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator('reminders')
    @classmethod
    def validate_reminders(cls, v: List[int]) -> List[int]:
        """Reminders must be positive integers, max 5"""
        if len(v) > 5:
            raise ValueError("maximum 5 reminders allowed")
        for r in v:
            if r <= 0:
                raise ValueError("reminder minutes must be positive")
        return v


class EventUpdateRequestContract(BaseModel):
    """Contract for event update requests"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    category: Optional[EventCategoryContract] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    recurrence_type: Optional[RecurrenceTypeContract] = None
    recurrence_end_date: Optional[datetime] = None
    reminders: Optional[List[int]] = None
    is_shared: Optional[bool] = None
    shared_with: Optional[List[str]] = None


class EventQueryRequestContract(BaseModel):
    """Contract for event query requests"""
    user_id: str = Field(..., description="User ID")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category: Optional[EventCategoryContract] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class SyncRequestContract(BaseModel):
    """Contract for external sync requests"""
    user_id: str = Field(..., description="User ID")
    provider: SyncProviderContract = Field(..., description="Calendar provider")
    credentials: Optional[Dict[str, Any]] = Field(None, description="OAuth credentials")


# ============================================================================
# Response Contracts
# ============================================================================

class EventResponseContract(BaseModel):
    """Event response contract - validates API responses"""
    event_id: str = Field(..., description="Unique event identifier")
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    all_day: bool = Field(..., description="Is all-day event")
    category: EventCategoryContract = Field(..., description="Category")
    color: Optional[str] = Field(None, description="Color")
    recurrence_type: RecurrenceTypeContract = Field(..., description="Recurrence type")
    recurrence_end_date: Optional[datetime] = None
    recurrence_rule: Optional[str] = None
    reminders: List[int] = Field(..., description="Reminder minutes")
    is_shared: bool = Field(..., description="Is shared")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class EventListResponseContract(BaseModel):
    """Event list response contract"""
    events: List[EventResponseContract]
    total: int
    page: int = 1
    page_size: int = 100


class SyncStatusResponseContract(BaseModel):
    """Sync status response contract"""
    provider: str = Field(..., description="Calendar provider")
    last_synced: Optional[datetime] = None
    synced_events: int = Field(0, description="Number of synced events")
    status: str = Field(..., description="Sync status")
    message: Optional[str] = None


# ============================================================================
# Test Data Factory - Zero Hardcoded Data
# ============================================================================

class CalendarTestDataFactory:
    """
    Test data factory for calendar_service.

    All methods generate UNIQUE data using UUIDs/secrets.
    NEVER use hardcoded test data in tests - always use this factory.

    Methods: 40+ factory methods for complete test coverage.
    """

    # === ID Generators ===

    @staticmethod
    def make_event_id() -> str:
        """Generate valid event ID"""
        return f"evt_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"usr_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_external_event_id() -> str:
        """Generate external event ID (for sync)"""
        return f"ext_{uuid.uuid4().hex}"

    # === Time Generators ===

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current UTC timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days: int = 30) -> datetime:
        """Generate past timestamp"""
        return datetime.now(timezone.utc) - timedelta(days=days)

    @staticmethod
    def make_future_timestamp(days: int = 30) -> datetime:
        """Generate future timestamp"""
        return datetime.now(timezone.utc) + timedelta(days=days)

    @staticmethod
    def make_start_time(hours_from_now: int = 1) -> datetime:
        """Generate event start time"""
        return datetime.now(timezone.utc) + timedelta(hours=hours_from_now)

    @staticmethod
    def make_end_time(start_time: datetime, duration_hours: int = 1) -> datetime:
        """Generate event end time based on start time"""
        return start_time + timedelta(hours=duration_hours)

    @staticmethod
    def make_time_range(duration_hours: int = 1) -> tuple:
        """Generate start/end time pair"""
        start = CalendarTestDataFactory.make_start_time()
        end = CalendarTestDataFactory.make_end_time(start, duration_hours)
        return (start, end)

    @staticmethod
    def make_today_start() -> datetime:
        """Generate start of today (UTC)"""
        now = datetime.now(timezone.utc)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def make_today_end() -> datetime:
        """Generate end of today (UTC)"""
        now = datetime.now(timezone.utc)
        return now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # === Field Generators ===

    @staticmethod
    def make_title() -> str:
        """Generate unique event title"""
        return f"Event {secrets.token_hex(4)}"

    @staticmethod
    def make_meeting_title() -> str:
        """Generate meeting title"""
        return f"Meeting {secrets.token_hex(4)}"

    @staticmethod
    def make_description() -> str:
        """Generate event description"""
        return f"Description for event {secrets.token_hex(4)}"

    @staticmethod
    def make_location() -> str:
        """Generate event location"""
        locations = ["Conference Room A", "Conference Room B", "Online", "Office"]
        return f"{locations[secrets.randbelow(len(locations))]} {secrets.token_hex(2)}"

    @staticmethod
    def make_color() -> str:
        """Generate valid color (#RRGGBB)"""
        return f"#{secrets.token_hex(3).upper()}"

    @staticmethod
    def make_timezone() -> str:
        """Generate timezone"""
        timezones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
        return timezones[secrets.randbelow(len(timezones))]

    @staticmethod
    def make_category() -> EventCategoryContract:
        """Generate random category"""
        categories = list(EventCategoryContract)
        return categories[secrets.randbelow(len(categories))]

    @staticmethod
    def make_recurrence_type() -> RecurrenceTypeContract:
        """Generate random recurrence type"""
        types = list(RecurrenceTypeContract)
        return types[secrets.randbelow(len(types))]

    @staticmethod
    def make_reminders(count: int = 2) -> List[int]:
        """Generate reminder minutes list"""
        options = [5, 10, 15, 30, 60, 120, 1440]
        return [options[secrets.randbelow(len(options))] for _ in range(min(count, 5))]

    @staticmethod
    def make_rrule() -> str:
        """Generate iCalendar RRULE string"""
        return f"FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL={datetime.now().strftime('%Y%m%d')}T235959Z"

    @staticmethod
    def make_shared_with(count: int = 2) -> List[str]:
        """Generate list of shared user IDs"""
        return [CalendarTestDataFactory.make_user_id() for _ in range(count)]

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate event metadata"""
        return {
            "source": "test",
            "priority": secrets.randbelow(5) + 1,
            "tags": [f"tag_{secrets.token_hex(2)}" for _ in range(2)]
        }

    @staticmethod
    def make_sync_provider() -> SyncProviderContract:
        """Generate random sync provider"""
        providers = list(SyncProviderContract)
        return providers[secrets.randbelow(len(providers))]

    @staticmethod
    def make_credentials() -> Dict[str, Any]:
        """Generate OAuth credentials (mock)"""
        return {
            "access_token": f"ya29.{secrets.token_hex(32)}",
            "refresh_token": f"1//{secrets.token_hex(32)}",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }

    # === Request Generators ===

    @staticmethod
    def make_create_request(**overrides) -> EventCreateRequestContract:
        """Generate valid event creation request"""
        start, end = CalendarTestDataFactory.make_time_range()
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": CalendarTestDataFactory.make_title(),
            "description": CalendarTestDataFactory.make_description(),
            "location": CalendarTestDataFactory.make_location(),
            "start_time": start,
            "end_time": end,
            "all_day": False,
            "timezone": "UTC",
            "category": EventCategoryContract.OTHER,
            "reminders": [15, 60],
            "is_shared": False,
            "shared_with": [],
        }
        defaults.update(overrides)
        return EventCreateRequestContract(**defaults)

    @staticmethod
    def make_create_request_minimal(**overrides) -> EventCreateRequestContract:
        """Generate minimal event creation request (required fields only)"""
        start, end = CalendarTestDataFactory.make_time_range()
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": CalendarTestDataFactory.make_title(),
            "start_time": start,
            "end_time": end,
        }
        defaults.update(overrides)
        return EventCreateRequestContract(**defaults)

    @staticmethod
    def make_create_request_all_day(**overrides) -> EventCreateRequestContract:
        """Generate all-day event creation request"""
        today = CalendarTestDataFactory.make_today_start()
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": CalendarTestDataFactory.make_title(),
            "start_time": today,
            "end_time": today + timedelta(days=1),
            "all_day": True,
            "category": EventCategoryContract.HOLIDAY,
        }
        defaults.update(overrides)
        return EventCreateRequestContract(**defaults)

    @staticmethod
    def make_create_request_recurring(**overrides) -> EventCreateRequestContract:
        """Generate recurring event creation request"""
        start, end = CalendarTestDataFactory.make_time_range()
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": CalendarTestDataFactory.make_meeting_title(),
            "start_time": start,
            "end_time": end,
            "recurrence_type": RecurrenceTypeContract.WEEKLY,
            "recurrence_end_date": CalendarTestDataFactory.make_future_timestamp(90),
            "category": EventCategoryContract.MEETING,
        }
        defaults.update(overrides)
        return EventCreateRequestContract(**defaults)

    @staticmethod
    def make_create_request_shared(**overrides) -> EventCreateRequestContract:
        """Generate shared event creation request"""
        start, end = CalendarTestDataFactory.make_time_range()
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": CalendarTestDataFactory.make_title(),
            "start_time": start,
            "end_time": end,
            "is_shared": True,
            "shared_with": CalendarTestDataFactory.make_shared_with(2),
        }
        defaults.update(overrides)
        return EventCreateRequestContract(**defaults)

    @staticmethod
    def make_update_request(**overrides) -> EventUpdateRequestContract:
        """Generate valid event update request"""
        defaults = {
            "title": CalendarTestDataFactory.make_title(),
        }
        defaults.update(overrides)
        return EventUpdateRequestContract(**defaults)

    @staticmethod
    def make_query_request(**overrides) -> EventQueryRequestContract:
        """Generate event query request"""
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return EventQueryRequestContract(**defaults)

    @staticmethod
    def make_query_request_date_range(**overrides) -> EventQueryRequestContract:
        """Generate query request with date range"""
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "start_date": CalendarTestDataFactory.make_today_start(),
            "end_date": CalendarTestDataFactory.make_future_timestamp(7),
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return EventQueryRequestContract(**defaults)

    @staticmethod
    def make_sync_request(**overrides) -> SyncRequestContract:
        """Generate sync request"""
        defaults = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "provider": SyncProviderContract.GOOGLE,
            "credentials": CalendarTestDataFactory.make_credentials(),
        }
        defaults.update(overrides)
        return SyncRequestContract(**defaults)

    # === Response Generators (for mocking) ===

    @staticmethod
    def make_response(**overrides) -> Dict[str, Any]:
        """Generate event response dict (for mock returns)"""
        now = datetime.now(timezone.utc)
        start, end = CalendarTestDataFactory.make_time_range()
        defaults = {
            "event_id": CalendarTestDataFactory.make_event_id(),
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": CalendarTestDataFactory.make_title(),
            "description": CalendarTestDataFactory.make_description(),
            "location": CalendarTestDataFactory.make_location(),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "all_day": False,
            "category": EventCategoryContract.OTHER.value,
            "color": None,
            "recurrence_type": RecurrenceTypeContract.NONE.value,
            "recurrence_end_date": None,
            "recurrence_rule": None,
            "reminders": [15],
            "is_shared": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_sync_status_response(**overrides) -> Dict[str, Any]:
        """Generate sync status response dict"""
        now = datetime.now(timezone.utc)
        defaults = {
            "provider": SyncProviderContract.GOOGLE.value,
            "last_synced": now.isoformat(),
            "synced_events": secrets.randbelow(100),
            "status": "success",
            "message": "Sync completed successfully",
        }
        defaults.update(overrides)
        return defaults

    # === Invalid Data Generators ===

    @staticmethod
    def make_invalid_title_empty() -> str:
        """Generate invalid title (empty)"""
        return ""

    @staticmethod
    def make_invalid_title_whitespace() -> str:
        """Generate invalid title (whitespace only)"""
        return "   "

    @staticmethod
    def make_invalid_event_id() -> str:
        """Generate invalid event ID"""
        return "invalid_format_no_prefix"

    @staticmethod
    def make_invalid_color() -> str:
        """Generate invalid color"""
        return "not-a-color"

    @staticmethod
    def make_invalid_time_range() -> tuple:
        """Generate invalid time range (end before start)"""
        end = datetime.now(timezone.utc)
        start = end + timedelta(hours=1)  # Start after end = invalid
        return (start, end)

    @staticmethod
    def make_invalid_reminders() -> List[int]:
        """Generate invalid reminders (too many)"""
        return [5, 10, 15, 30, 60, 120]  # 6 reminders > max 5

    @staticmethod
    def make_invalid_reminder_negative() -> List[int]:
        """Generate invalid reminder (negative)"""
        return [-5, 10]


# ============================================================================
# Request Builders (Fluent API)
# ============================================================================

class EventCreateRequestBuilder:
    """
    Builder for event creation requests.

    Usage:
        request = (
            EventCreateRequestBuilder()
            .with_title("Team Meeting")
            .with_category(EventCategoryContract.MEETING)
            .with_reminders([15, 60])
            .build()
        )
    """

    def __init__(self):
        start, end = CalendarTestDataFactory.make_time_range()
        self._user_id = CalendarTestDataFactory.make_user_id()
        self._organization_id: Optional[str] = None
        self._title = CalendarTestDataFactory.make_title()
        self._description: Optional[str] = None
        self._location: Optional[str] = None
        self._start_time = start
        self._end_time = end
        self._all_day = False
        self._timezone = "UTC"
        self._category = EventCategoryContract.OTHER
        self._color: Optional[str] = None
        self._recurrence_type = RecurrenceTypeContract.NONE
        self._recurrence_end_date: Optional[datetime] = None
        self._recurrence_rule: Optional[str] = None
        self._reminders: List[int] = []
        self._is_shared = False
        self._shared_with: List[str] = []
        self._metadata: Optional[Dict[str, Any]] = None

    def with_user_id(self, value: str) -> 'EventCreateRequestBuilder':
        self._user_id = value
        return self

    def with_organization_id(self, value: str) -> 'EventCreateRequestBuilder':
        self._organization_id = value
        return self

    def with_title(self, value: str) -> 'EventCreateRequestBuilder':
        self._title = value
        return self

    def with_description(self, value: str) -> 'EventCreateRequestBuilder':
        self._description = value
        return self

    def with_location(self, value: str) -> 'EventCreateRequestBuilder':
        self._location = value
        return self

    def with_start_time(self, value: datetime) -> 'EventCreateRequestBuilder':
        self._start_time = value
        return self

    def with_end_time(self, value: datetime) -> 'EventCreateRequestBuilder':
        self._end_time = value
        return self

    def with_time_range(self, start: datetime, end: datetime) -> 'EventCreateRequestBuilder':
        self._start_time = start
        self._end_time = end
        return self

    def with_all_day(self, value: bool = True) -> 'EventCreateRequestBuilder':
        self._all_day = value
        return self

    def with_timezone(self, value: str) -> 'EventCreateRequestBuilder':
        self._timezone = value
        return self

    def with_category(self, value: EventCategoryContract) -> 'EventCreateRequestBuilder':
        self._category = value
        return self

    def with_color(self, value: str) -> 'EventCreateRequestBuilder':
        self._color = value
        return self

    def with_recurrence(self, rtype: RecurrenceTypeContract, end_date: datetime = None) -> 'EventCreateRequestBuilder':
        self._recurrence_type = rtype
        self._recurrence_end_date = end_date
        return self

    def with_rrule(self, value: str) -> 'EventCreateRequestBuilder':
        self._recurrence_rule = value
        self._recurrence_type = RecurrenceTypeContract.CUSTOM
        return self

    def with_reminders(self, value: List[int]) -> 'EventCreateRequestBuilder':
        self._reminders = value
        return self

    def with_shared(self, shared_with: List[str]) -> 'EventCreateRequestBuilder':
        self._is_shared = True
        self._shared_with = shared_with
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'EventCreateRequestBuilder':
        self._metadata = value
        return self

    def with_invalid_title(self) -> 'EventCreateRequestBuilder':
        self._title = CalendarTestDataFactory.make_invalid_title_empty()
        return self

    def with_invalid_time_range(self) -> 'EventCreateRequestBuilder':
        start, end = CalendarTestDataFactory.make_invalid_time_range()
        self._start_time = start
        self._end_time = end
        return self

    def build(self) -> EventCreateRequestContract:
        """Build the request contract"""
        return EventCreateRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            title=self._title,
            description=self._description,
            location=self._location,
            start_time=self._start_time,
            end_time=self._end_time,
            all_day=self._all_day,
            timezone=self._timezone,
            category=self._category,
            color=self._color,
            recurrence_type=self._recurrence_type,
            recurrence_end_date=self._recurrence_end_date,
            recurrence_rule=self._recurrence_rule,
            reminders=self._reminders,
            is_shared=self._is_shared,
            shared_with=self._shared_with,
            metadata=self._metadata,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary (for API calls)"""
        data = self.build().model_dump()
        # Convert datetime to ISO string for API
        for key in ['start_time', 'end_time', 'recurrence_end_date']:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data


class EventUpdateRequestBuilder:
    """Builder for event update requests"""

    def __init__(self):
        self._title: Optional[str] = None
        self._description: Optional[str] = None
        self._location: Optional[str] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._all_day: Optional[bool] = None
        self._category: Optional[EventCategoryContract] = None
        self._color: Optional[str] = None
        self._recurrence_type: Optional[RecurrenceTypeContract] = None
        self._recurrence_end_date: Optional[datetime] = None
        self._reminders: Optional[List[int]] = None
        self._is_shared: Optional[bool] = None
        self._shared_with: Optional[List[str]] = None

    def with_title(self, value: str) -> 'EventUpdateRequestBuilder':
        self._title = value
        return self

    def with_description(self, value: str) -> 'EventUpdateRequestBuilder':
        self._description = value
        return self

    def with_location(self, value: str) -> 'EventUpdateRequestBuilder':
        self._location = value
        return self

    def with_time_range(self, start: datetime, end: datetime) -> 'EventUpdateRequestBuilder':
        self._start_time = start
        self._end_time = end
        return self

    def with_category(self, value: EventCategoryContract) -> 'EventUpdateRequestBuilder':
        self._category = value
        return self

    def with_reminders(self, value: List[int]) -> 'EventUpdateRequestBuilder':
        self._reminders = value
        return self

    def build(self) -> EventUpdateRequestContract:
        """Build the request contract"""
        return EventUpdateRequestContract(
            title=self._title,
            description=self._description,
            location=self._location,
            start_time=self._start_time,
            end_time=self._end_time,
            all_day=self._all_day,
            category=self._category,
            color=self._color,
            recurrence_type=self._recurrence_type,
            recurrence_end_date=self._recurrence_end_date,
            reminders=self._reminders,
            is_shared=self._is_shared,
            shared_with=self._shared_with,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary, excluding None values"""
        data = self.build().model_dump(exclude_none=True)
        # Convert datetime to ISO string for API
        for key in ['start_time', 'end_time', 'recurrence_end_date']:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data


class EventQueryRequestBuilder:
    """Builder for event query requests"""

    def __init__(self):
        self._user_id = CalendarTestDataFactory.make_user_id()
        self._start_date: Optional[datetime] = None
        self._end_date: Optional[datetime] = None
        self._category: Optional[EventCategoryContract] = None
        self._limit = 100
        self._offset = 0

    def with_user_id(self, value: str) -> 'EventQueryRequestBuilder':
        self._user_id = value
        return self

    def with_date_range(self, start: datetime, end: datetime) -> 'EventQueryRequestBuilder':
        self._start_date = start
        self._end_date = end
        return self

    def with_category(self, value: EventCategoryContract) -> 'EventQueryRequestBuilder':
        self._category = value
        return self

    def with_pagination(self, limit: int, offset: int) -> 'EventQueryRequestBuilder':
        self._limit = limit
        self._offset = offset
        return self

    def build(self) -> EventQueryRequestContract:
        return EventQueryRequestContract(
            user_id=self._user_id,
            start_date=self._start_date,
            end_date=self._end_date,
            category=self._category,
            limit=self._limit,
            offset=self._offset,
        )

    def build_dict(self) -> Dict[str, Any]:
        data = self.build().model_dump(exclude_none=True)
        for key in ['start_date', 'end_date']:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "RecurrenceTypeContract",
    "EventCategoryContract",
    "SyncProviderContract",
    "SyncStatusContract",
    # Request Contracts
    "EventCreateRequestContract",
    "EventUpdateRequestContract",
    "EventQueryRequestContract",
    "SyncRequestContract",
    # Response Contracts
    "EventResponseContract",
    "EventListResponseContract",
    "SyncStatusResponseContract",
    # Factory
    "CalendarTestDataFactory",
    # Builders
    "EventCreateRequestBuilder",
    "EventUpdateRequestBuilder",
    "EventQueryRequestBuilder",
]
