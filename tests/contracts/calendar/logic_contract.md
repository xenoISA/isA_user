# Calendar Service - Logic Contract

**Business Rules and Specifications for Calendar Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for calendar_service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)

---

## Business Rules

### Event Creation Rules

### BR-CAL-001: Event ID Generation
**Given**: Valid event creation request
**When**: Event is created
**Then**:
- System generates unique event_id with format `evt_<uuid16>`
- ID is immutable after creation
- ID must be globally unique

**Validation Rules**:
- Format: `evt_[a-f0-9]{16}`
- Cannot be user-provided

---

### BR-CAL-002: Title Validation
**Given**: Title field in event request
**When**: Title is validated
**Then**:
- Title must be 1-255 characters
- Title must not be empty or whitespace-only
- Leading/trailing whitespace is trimmed

**Edge Cases**:
- Empty string → **ValidationError** (400)
- Whitespace only → **ValidationError** (400)
- 256+ characters → **ValidationError** (400)

---

### BR-CAL-003: Time Validation (End > Start)
**Given**: Event creation or update request with start_time and end_time
**When**: Times are validated
**Then**:
- end_time MUST be strictly greater than start_time
- Equal times are NOT allowed

**Edge Cases**:
- end_time < start_time → **ValidationError**: "End time must be after start time"
- end_time == start_time → **ValidationError**: "End time must be after start time"
- end_time > start_time → **Accepted**

---

### BR-CAL-004: All-Day Event Handling
**Given**: Event with `all_day = true`
**When**: Event is created/stored
**Then**:
- Time portion is stored but ignored for display
- Duration spans full calendar day
- Category often defaults to "holiday" or "birthday"

---

### BR-CAL-005: Color Validation
**Given**: Color field in event request
**When**: Color is provided
**Then**:
- Must match format `#RRGGBB` (hex)
- Case insensitive (accepts `#abc123` and `#ABC123`)

**Edge Cases**:
- Invalid format (e.g., "red", "#12345") → **ValidationError**
- Null/empty → **Accepted** (optional field)

---

### BR-CAL-006: Reminders Validation
**Given**: Reminders list in event request
**When**: Reminders are validated
**Then**:
- Maximum 5 reminders per event
- Each reminder must be positive integer (minutes)
- Duplicates allowed (but not recommended)

**Edge Cases**:
- 6+ reminders → **ValidationError**: "maximum 5 reminders allowed"
- Negative value → **ValidationError**: "reminder minutes must be positive"
- Zero → **ValidationError**: "reminder minutes must be positive"
- Empty list → **Accepted**

---

### Event Query Rules

### BR-CAL-010: Query by Date Range
**Given**: Query request with start_date and end_date
**When**: Events are queried
**Then**:
- Return events where: `start_time >= start_date AND end_time <= end_date`
- Results sorted by start_time ASC
- Pagination applied (limit/offset)

---

### BR-CAL-011: Today's Events Query
**Given**: Request for today's events
**When**: Query is executed
**Then**:
- Return events from 00:00:00.000 to 23:59:59.999 UTC of current date
- Sorted by start_time ASC

---

### BR-CAL-012: Upcoming Events Query
**Given**: Request for upcoming events with `days` parameter
**When**: Query is executed
**Then**:
- Return events from NOW to NOW + `days`
- `days` default: 7, range: 1-365
- Sorted by start_time ASC

---

### BR-CAL-013: Category Filter
**Given**: Query with category filter
**When**: Events are queried
**Then**:
- Only return events matching specified category
- Category is case-sensitive enum value

---

### Event Update Rules

### BR-CAL-020: Partial Update Support
**Given**: Event update request
**When**: Only some fields are provided
**Then**:
- Only provided fields are updated
- Unspecified fields retain original values
- `updated_at` is always refreshed

---

### BR-CAL-021: Update Non-Existent Event
**Given**: Update request for non-existent event
**When**: Event ID not found
**Then**:
- Return **404 Not Found**
- No side effects

---

### BR-CAL-022: Time Update Validation
**Given**: Update request with new start_time and/or end_time
**When**: Times are validated
**Then**:
- If both provided: end_time > start_time (same as creation)
- If only one provided: Compare with existing value
- Validation error if constraint violated

---

### Event Deletion Rules

### BR-CAL-030: Hard Delete
**Given**: Delete request for event
**When**: Event exists
**Then**:
- Event is permanently removed from database
- Return 204 No Content
- Publish `calendar.event.deleted` event

---

### BR-CAL-031: Delete Non-Existent Event
**Given**: Delete request for non-existent event
**When**: Event ID not found
**Then**:
- Return **404 Not Found**
- No side effects

---

### External Sync Rules

### BR-CAL-040: Sync Provider Support
**Given**: Sync request with provider
**When**: Provider is validated
**Then**:
- Supported providers: `google_calendar`, `apple_calendar`, `outlook`
- Unsupported provider → **400 Bad Request**

---

### BR-CAL-041: Sync Status Upsert
**Given**: Sync operation completes
**When**: Status is updated
**Then**:
- Insert new record if not exists
- Update existing record (user_id, provider is unique key)
- Record: last_sync_time, synced_events_count, status, error_message

---

### BR-CAL-042: Sync Failure Handling
**Given**: Sync operation fails
**When**: Error occurs
**Then**:
- Update sync_status with status="error", error_message
- Return SyncStatusResponse with error details
- Original events are NOT affected

---

### Recurrence Rules

### BR-CAL-050: Recurrence Type Values
**Given**: Event with recurrence
**When**: Recurrence type is specified
**Then**:
- Valid values: none, daily, weekly, monthly, yearly, custom
- `custom` requires `recurrence_rule` (RRULE format)

---

### BR-CAL-051: Recurrence End Date
**Given**: Recurring event
**When**: recurrence_end_date is specified
**Then**:
- Must be after start_time
- Limits the recurrence pattern

---

### BR-CAL-052: Custom RRULE Validation
**Given**: Event with recurrence_type="custom"
**When**: recurrence_rule is validated
**Then**:
- Must be valid iCalendar RRULE format
- Example: `FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20251231T235959Z`

---

### Sharing Rules

### BR-CAL-060: Event Sharing
**Given**: Event with is_shared=true
**When**: shared_with contains user IDs
**Then**:
- Listed users can view the event
- Only owner can edit/delete

---

### BR-CAL-061: Sharing Permissions
**Given**: Shared event
**When**: Non-owner attempts edit/delete
**Then**:
- **403 Forbidden** (when authorization implemented)
- Currently: Relies on user_id filtering

---

### GDPR Rules

### BR-CAL-070: User Data Deletion
**Given**: User deletion request (from account.user.deleted event)
**When**: Handler processes event
**Then**:
- Delete ALL events for user
- Delete ALL sync_status records for user
- Log deletion count

---

---

## State Machines

### Event Lifecycle (Simple - No Status Field)

```
States:
├── EXISTS     : Event is in database
└── DELETED    : Event removed from database

Transitions:
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  [CREATE] ──► EXISTS ──► [UPDATE] ──► EXISTS            │
│                 │                                        │
│                 │                                        │
│                 └──────► [DELETE] ──► DELETED           │
│                                                         │
└─────────────────────────────────────────────────────────┘

Notes:
- Calendar events use hard delete (no soft delete status)
- Events are either present or removed
- All updates modify existing record in-place
```

### Sync Status State Machine

```
States:
├── PENDING    : Initial/never synced
├── ACTIVE     : Successfully synced
├── ERROR      : Last sync failed
└── SUCCESS    : Sync completed (transient)

Transitions:
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  [INIT] ──► PENDING ──► [SYNC] ──┬──► ACTIVE            │
│                │                  │                      │
│                │                  └──► ERROR             │
│                │                                         │
│                └──► ACTIVE ──► [RESYNC] ──┬──► ACTIVE   │
│                                           │              │
│                                           └──► ERROR    │
│                                                         │
└─────────────────────────────────────────────────────────┘

Transition Rules:
- PENDING → ACTIVE   : Successful first sync
- PENDING → ERROR    : Failed first sync
- ACTIVE → ACTIVE    : Successful resync
- ACTIVE → ERROR     : Failed resync
- ERROR → ACTIVE     : Successful retry
- ERROR → ERROR      : Continued failures
```

---

## Edge Cases

### EC-001: Concurrent Event Modification
- **Input**: Two simultaneous updates to same event
- **Expected**: Last write wins (no version field)
- **Risk**: Race condition possible

### EC-002: Maximum Title Length
- **Input**: Title with exactly 255 characters
- **Expected**: Accepted (boundary value)

### EC-003: Unicode Characters in Title
- **Input**: Title with unicode (emoji, CJK characters)
- **Expected**: Accepted and stored correctly

### EC-004: SQL Injection Attempt
- **Input**: Title containing `'; DROP TABLE--`
- **Expected**: Treated as literal string, no SQL execution

### EC-005: Empty Update Request
- **Input**: Update request with no fields
- **Expected**: No-op, return current state (updated_at refreshed)

### EC-006: Time Zone Boundary
- **Input**: Event at midnight UTC
- **Expected**: Correctly included in "today" query

### EC-007: Very Long Duration Event
- **Input**: Event spanning multiple days
- **Expected**: Accepted, returned in any overlapping date range query

### EC-008: Reminders with Large Values
- **Input**: Reminder of 525600 minutes (1 year)
- **Expected**: Accepted (no upper limit defined)

### EC-009: Multiple Events Same Start Time
- **Input**: Two events with identical start_time
- **Expected**: Both created, returned in order of creation

### EC-010: Sync with No Credentials
- **Input**: Sync request without credentials
- **Expected**: Proceed with default/cached credentials or fail gracefully

### EC-011: External Event ID Collision
- **Input**: Two synced events with same external_event_id
- **Expected**: Upsert behavior (update if exists)

### EC-012: Query with Invalid Date Range
- **Input**: end_date < start_date in query
- **Expected**: Empty result set (not error)

---

## Data Consistency Rules

### DC-001: Timestamp Management
- `created_at`: Set once at creation, never modified
- `updated_at`: Updated on every modification
- `last_synced_at`: Updated after each sync
- All timestamps in UTC (TIMESTAMPTZ)

### DC-002: Field Normalization
- Titles: Trim whitespace, preserve case
- Locations: Trim whitespace, preserve case
- Colors: Store as provided (case preserved)
- IDs: Never modified after generation

### DC-003: Array Field Handling
- `reminders`: Integer array, stored as PostgreSQL INTEGER[]
- `shared_with`: String array, stored as TEXT[]
- Empty arrays stored as `'{}'::integer[]` or `'{}'::text[]`

### DC-004: JSONB Metadata
- `metadata`: JSONB field, defaults to `'{}'::jsonb`
- Merge strategy: Replace entire object on update

### DC-005: Foreign Key Relationships
- `user_id`: Reference to accounts.users (logical, not enforced)
- `organization_id`: Reference to organizations.organizations (optional)
- No cascade delete at DB level (handled in application)

---

## Integration Contracts

### With Account Service

**Event**: `account.user.deleted`
**When**: User is deleted from system
**Handler**: `handle_user_deleted`
**Action**:
- Delete all events for user
- Delete all sync_status records
- Log deletion count

### With Notification Service

**Published Event**: `calendar.event.created`
**When**: After successful event creation
**Subscriber Action**: Create reminder notifications based on `reminders` array

**Published Event**: `calendar.event.updated`
**When**: After successful event update
**Subscriber Action**: Update/recreate reminder notifications

**Published Event**: `calendar.event.deleted`
**When**: After successful event deletion
**Subscriber Action**: Cancel all pending reminders

### Event Payloads

1. **calendar.event.created**
```json
{
  "event_type": "CALENDAR_EVENT_CREATED",
  "source": "calendar_service",
  "data": {
    "event_id": "evt_abc123",
    "user_id": "usr_xyz789",
    "title": "Team Meeting",
    "start_time": "2025-01-15T10:00:00Z",
    "end_time": "2025-01-15T11:00:00Z",
    "timestamp": "2025-01-10T08:00:00Z"
  }
}
```

2. **calendar.event.updated**
```json
{
  "event_type": "CALENDAR_EVENT_UPDATED",
  "source": "calendar_service",
  "data": {
    "event_id": "evt_abc123",
    "user_id": "usr_xyz789",
    "updated_fields": ["title", "start_time"],
    "timestamp": "2025-01-10T09:00:00Z"
  }
}
```

3. **calendar.event.deleted**
```json
{
  "event_type": "CALENDAR_EVENT_DELETED",
  "source": "calendar_service",
  "data": {
    "event_id": "evt_abc123",
    "user_id": "usr_xyz789",
    "timestamp": "2025-01-10T10:00:00Z"
  }
}
```

---

## Error Handling Contracts

### HTTP Error Codes

| Scenario | HTTP Code | Error Type | Message Format |
|----------|-----------|------------|----------------|
| Invalid request body | 422 | ValidationError | `{"detail": [{"loc": [...], "msg": "..."}]}` |
| Invalid time range | 400 | ValidationError | `{"detail": "End time must be after start time"}` |
| Invalid reminders | 400 | ValidationError | `{"detail": "maximum 5 reminders allowed"}` |
| Event not found | 404 | NotFoundError | `{"detail": "Event not found"}` |
| Sync status not found | 404 | NotFoundError | `{"detail": "Sync status not found"}` |
| Unsupported provider | 400 | ValueError | `{"detail": "Unsupported provider: X"}` |
| Server error | 500 | InternalError | `{"detail": "Internal server error"}` |

### Error Response Structure

```json
{
  "detail": "Human-readable error message"
}
```

### Exception Hierarchy

```
CalendarServiceError (base)
├── CalendarServiceValidationError
│   ├── Invalid time range
│   ├── Invalid reminders
│   └── Invalid recurrence
└── CalendarEventNotFoundError
```

---

## Performance SLAs

| Operation | Target Latency | Max Latency |
|-----------|---------------|-------------|
| Create Event | < 100ms | < 500ms |
| Get Event | < 50ms | < 200ms |
| Update Event | < 100ms | < 500ms |
| Delete Event | < 50ms | < 200ms |
| Query Events (date range) | < 200ms | < 1000ms |
| Get Today's Events | < 50ms | < 200ms |
| Get Upcoming Events | < 100ms | < 500ms |
| External Sync | < 5000ms | < 30000ms |
| Get Sync Status | < 50ms | < 200ms |
| Health Check | < 20ms | < 100ms |

---

## Test Coverage Requirements

### Unit Tests Must Cover:
- All BR-CAL-* rules (at least one test each)
- All enum validations
- Time validation edge cases
- Reminder validation

### Component Tests Must Cover:
- Service layer logic with mocked repository
- Event publishing behavior
- Error handling paths

### Integration Tests Must Cover:
- Full HTTP + Database flow
- Date range queries with real data
- Concurrent access patterns

### API Tests Must Cover:
- All 10 endpoints
- All error responses
- Pagination behavior

### Smoke Tests Must Cover:
- Event CRUD cycle
- Today/Upcoming queries
- Health check

---

**End of Logic Contract**
