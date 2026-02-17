# Calendar Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Calendar Service
**Version**: 1.0.0
**Status**: Development
**Owner**: isA Platform Team
**Last Updated**: 2025-12-17

### Vision
成为用户跨平台日程管理的统一入口，实现智能时间规划和无缝协作。

### Mission
提供可靠、高效的日历事件管理服务，支持多源日历聚合和智能提醒。

### Target Users
- **Individual Users**: 管理个人日程、设置提醒、同步外部日历
- **Team Members**: 共享团队日程、协调会议时间
- **System Services**: 通过事件订阅响应日历变更
- **Family Members**: 共享家庭活动日程

### Key Differentiators
1. **Multi-Calendar Sync**: 支持 Google、Apple、Outlook 三大日历平台同步
2. **Smart Reminders**: 灵活的多级提醒设置
3. **Recurrence Support**: 完整支持 iCalendar RRULE 重复规则
4. **Event Sharing**: 支持用户间和组织内事件共享
5. **Event-Driven**: 与平台其他服务实时集成

---

## Product Goals

### Primary Goals
1. **Event Management**: 提供完整的 CRUD 操作，响应时间 <100ms
2. **Calendar Sync**: 支持 3 种主流外部日历同步
3. **Query Performance**: 日期范围查询 <200ms
4. **Reminder Integration**: 与 Notification Service 无缝集成
5. **High Availability**: 服务可用性 99.9%

### Secondary Goals
1. **Timezone Support**: 正确处理跨时区事件
2. **Bulk Operations**: 支持批量事件导入
3. **Conflict Detection**: 事件时间冲突检测
4. **Calendar Sharing**: 日历级别共享权限
5. **Offline Support**: 支持离线事件缓存

---

## Epics and User Stories

### Epic 1: Event Management (事件管理)

**Objective**: 提供完整的日历事件 CRUD 操作

#### E1-US1: Create Calendar Event
**As a** user
**I want to** create a new calendar event
**So that** I can track my schedule

**Acceptance Criteria**:
- AC1: POST `/api/v1/calendar/events` creates a new event
- AC2: Title is required, description and location are optional
- AC3: End time must be after start time (validation)
- AC4: Returns 201 with created event including event_id
- AC5: Publishes `calendar.event.created` event to NATS
- AC6: Response time <100ms
- AC7: Supports all-day events with `all_day=true`

**API Reference**: `POST /api/v1/calendar/events`

**Example Request**:
```json
{
  "user_id": "usr_abc123",
  "title": "Team Meeting",
  "description": "Weekly sync",
  "location": "Conference Room A",
  "start_time": "2025-01-15T10:00:00Z",
  "end_time": "2025-01-15T11:00:00Z",
  "category": "meeting",
  "reminders": [15, 60]
}
```

**Example Response**:
```json
{
  "event_id": "evt_xyz789",
  "user_id": "usr_abc123",
  "title": "Team Meeting",
  "description": "Weekly sync",
  "location": "Conference Room A",
  "start_time": "2025-01-15T10:00:00Z",
  "end_time": "2025-01-15T11:00:00Z",
  "all_day": false,
  "category": "meeting",
  "color": null,
  "recurrence_type": "none",
  "reminders": [15, 60],
  "is_shared": false,
  "created_at": "2025-01-10T08:00:00Z",
  "updated_at": null
}
```

#### E1-US2: Time Validation
**As a** user
**I want to** get clear error messages for invalid times
**So that** I can correct my input

**Acceptance Criteria**:
- AC1: End time <= start time returns 400 Bad Request
- AC2: Error message: "End time must be after start time"
- AC3: Invalid datetime format returns 422 Unprocessable Entity
- AC4: Timezone is validated and defaulted to UTC

#### E1-US3: All-Day Events
**As a** user
**I want to** create all-day events
**So that** I can track holidays and birthdays

**Acceptance Criteria**:
- AC1: `all_day=true` creates an all-day event
- AC2: Time portion is ignored for all-day events
- AC3: All-day events display correctly in date range queries
- AC4: Category defaults to "other" if not specified

---

### Epic 2: Event Retrieval (事件查询)

**Objective**: 提供灵活的事件查询能力

#### E2-US1: Get Event by ID
**As a** user
**I want to** retrieve a specific event by ID
**So that** I can view event details

**Acceptance Criteria**:
- AC1: GET `/api/v1/calendar/events/{event_id}` returns event
- AC2: Returns all event fields including reminders
- AC3: Returns 404 if event not found
- AC4: Optional `user_id` query param for authorization
- AC5: Response time <50ms

**API Reference**: `GET /api/v1/calendar/events/{event_id}`

#### E2-US2: Update Event
**As a** user
**I want to** update an existing event
**So that** I can modify my schedule

**Acceptance Criteria**:
- AC1: PUT `/api/v1/calendar/events/{event_id}` updates event
- AC2: Only provided fields are updated (partial update)
- AC3: Time validation applies if times are updated
- AC4: `updated_at` is set to current timestamp
- AC5: Publishes `calendar.event.updated` event
- AC6: Returns updated event
- AC7: Returns 404 if event not found

**API Reference**: `PUT /api/v1/calendar/events/{event_id}`

**Example Request**:
```json
{
  "title": "Team Standup",
  "start_time": "2025-01-15T09:30:00Z"
}
```

#### E2-US3: Delete Event
**As a** user
**I want to** delete an event
**So that** I can remove cancelled activities

**Acceptance Criteria**:
- AC1: DELETE `/api/v1/calendar/events/{event_id}` removes event
- AC2: Returns 204 No Content on success
- AC3: Returns 404 if event not found
- AC4: Publishes `calendar.event.deleted` event
- AC5: Optional `user_id` for authorization

**API Reference**: `DELETE /api/v1/calendar/events/{event_id}`

---

### Epic 3: Date Range Queries (日期范围查询)

**Objective**: 支持按日期范围查询事件

#### E3-US1: Query Events by Date Range
**As a** user
**I want to** query events within a date range
**So that** I can see my calendar for a specific period

**Acceptance Criteria**:
- AC1: GET `/api/v1/calendar/events?user_id=X&start_date=X&end_date=X`
- AC2: Supports optional `category` filter
- AC3: Pagination with `limit` (default 100, max 1000) and `offset`
- AC4: Returns events sorted by start_time
- AC5: Response includes total count and pagination info
- AC6: Response time <200ms

**API Reference**: `GET /api/v1/calendar/events`

**Example Response**:
```json
{
  "events": [
    {
      "event_id": "evt_001",
      "title": "Morning Standup",
      "start_time": "2025-01-15T09:00:00Z",
      "end_time": "2025-01-15T09:15:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 100
}
```

#### E3-US2: Get Today's Events
**As a** user
**I want to** quickly see today's events
**So that** I can plan my day

**Acceptance Criteria**:
- AC1: GET `/api/v1/calendar/today?user_id=X` returns today's events
- AC2: Events from 00:00 to 23:59 of current date (UTC)
- AC3: Sorted by start_time
- AC4: Response time <50ms

**API Reference**: `GET /api/v1/calendar/today`

#### E3-US3: Get Upcoming Events
**As a** user
**I want to** see upcoming events
**So that** I can prepare for future activities

**Acceptance Criteria**:
- AC1: GET `/api/v1/calendar/upcoming?user_id=X&days=7`
- AC2: `days` parameter: 1-365, default 7
- AC3: Returns events from now to N days ahead
- AC4: Sorted by start_time
- AC5: Response time <100ms

**API Reference**: `GET /api/v1/calendar/upcoming`

---

### Epic 4: External Calendar Sync (外部日历同步)

**Objective**: 支持与外部日历服务同步

#### E4-US1: Sync Google Calendar
**As a** user
**I want to** sync my Google Calendar
**So that** I have all my events in one place

**Acceptance Criteria**:
- AC1: POST `/api/v1/calendar/sync?provider=google_calendar`
- AC2: Accepts OAuth credentials in request body
- AC3: Imports events from primary calendar
- AC4: Updates sync_status with result
- AC5: Returns sync summary (events synced, status)

**API Reference**: `POST /api/v1/calendar/sync`

**Example Request**:
```json
{
  "access_token": "ya29.xxx",
  "refresh_token": "1//0xxx"
}
```

**Example Response**:
```json
{
  "provider": "google_calendar",
  "last_synced": "2025-01-15T10:00:00Z",
  "synced_events": 42,
  "status": "success",
  "message": "Successfully synced 42 events"
}
```

#### E4-US2: Sync Apple Calendar
**As a** user
**I want to** sync my Apple iCloud Calendar
**So that** I can access my Apple events

**Acceptance Criteria**:
- AC1: POST `/api/v1/calendar/sync?provider=apple_calendar`
- AC2: Uses CalDAV protocol for sync
- AC3: Updates sync_status

#### E4-US3: Sync Outlook Calendar
**As a** user
**I want to** sync my Outlook Calendar
**So that** I can access my Microsoft events

**Acceptance Criteria**:
- AC1: POST `/api/v1/calendar/sync?provider=outlook`
- AC2: Uses Microsoft Graph API
- AC3: Updates sync_status

#### E4-US4: Get Sync Status
**As a** user
**I want to** check my sync status
**So that** I know if my calendars are up to date

**Acceptance Criteria**:
- AC1: GET `/api/v1/calendar/sync/status?user_id=X`
- AC2: Optional `provider` filter
- AC3: Returns last sync time, event count, status
- AC4: Returns 404 if no sync status exists

**API Reference**: `GET /api/v1/calendar/sync/status`

---

### Epic 5: Recurrence Management (重复事件)

**Objective**: 支持重复事件管理

#### E5-US1: Create Recurring Event
**As a** user
**I want to** create recurring events
**So that** I don't have to create each instance manually

**Acceptance Criteria**:
- AC1: `recurrence_type` supports: none, daily, weekly, monthly, yearly, custom
- AC2: `recurrence_end_date` sets when recurrence stops
- AC3: `recurrence_rule` supports iCalendar RRULE format
- AC4: Events returned in queries include recurrence info

**Example Request**:
```json
{
  "user_id": "usr_abc123",
  "title": "Weekly Team Meeting",
  "start_time": "2025-01-15T10:00:00Z",
  "end_time": "2025-01-15T11:00:00Z",
  "recurrence_type": "weekly",
  "recurrence_end_date": "2025-06-30T23:59:59Z"
}
```

#### E5-US2: Custom Recurrence Rules
**As a** user
**I want to** define custom recurrence patterns
**So that** I can handle complex schedules

**Acceptance Criteria**:
- AC1: `recurrence_type=custom` requires `recurrence_rule`
- AC2: RRULE format: `FREQ=WEEKLY;BYDAY=TU,TH;UNTIL=20250630`
- AC3: Invalid RRULE returns 400 Bad Request

---

### Epic 6: Event-Driven Integration (事件驱动集成)

**Objective**: 通过 NATS 事件与其他服务集成

#### E6-US1: Publish Created Event
**As a** Calendar Service
**I want to** publish calendar.event.created events
**So that** Notification Service can create reminders

**Acceptance Criteria**:
- AC1: Published after successful event creation
- AC2: Payload includes: event_id, user_id, title, start_time, end_time
- AC3: Published to NATS event bus
- AC4: Failure logged but doesn't block operation

#### E6-US2: Publish Updated Event
**As a** Calendar Service
**I want to** publish calendar.event.updated events
**So that** reminders can be updated

**Acceptance Criteria**:
- AC1: Published after successful event update
- AC2: Payload includes: event_id, user_id, updated_fields
- AC3: Notification Service updates reminder schedules

#### E6-US3: Publish Deleted Event
**As a** Calendar Service
**I want to** publish calendar.event.deleted events
**So that** reminders can be cancelled

**Acceptance Criteria**:
- AC1: Published after successful event deletion
- AC2: Payload includes: event_id, user_id
- AC3: Notification Service cancels pending reminders

#### E6-US4: Handle User Deleted Event
**As a** Calendar Service
**I want to** respond to account.user.deleted events
**So that** I can cleanup user data

**Acceptance Criteria**:
- AC1: Subscribe to `*.user.deleted` pattern
- AC2: Delete all events for the user
- AC3: Delete sync status records
- AC4: Log cleanup actions

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8240`
- **Staging**: `https://staging-calendar.isa.ai`
- **Production**: `https://calendar.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Current**: Handled by API Gateway (JWT validation)
- **Header**: `Authorization: Bearer <token>`
- **User Context**: user_id extracted from JWT claims or query param

### Core Endpoints Summary

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/api/v1/calendar/events` | Create event | <100ms |
| GET | `/api/v1/calendar/events/{event_id}` | Get event by ID | <50ms |
| GET | `/api/v1/calendar/events` | List events with filters | <200ms |
| PUT | `/api/v1/calendar/events/{event_id}` | Update event | <100ms |
| DELETE | `/api/v1/calendar/events/{event_id}` | Delete event | <50ms |
| GET | `/api/v1/calendar/today` | Get today's events | <50ms |
| GET | `/api/v1/calendar/upcoming` | Get upcoming events | <100ms |
| POST | `/api/v1/calendar/sync` | Sync external calendar | <5000ms |
| GET | `/api/v1/calendar/sync/status` | Get sync status | <50ms |
| GET | `/health` | Health check | <20ms |

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New event created
- `204 No Content`: Successful deletion
- `400 Bad Request`: Validation error (e.g., invalid times)
- `404 Not Found`: Event not found
- `422 Unprocessable Entity`: Invalid request format
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "detail": "End time must be after start time"
}
```

---

## Functional Requirements

### FR-1: Event CRUD
System SHALL provide create, read, update, delete operations for calendar events

### FR-2: Time Validation
System SHALL validate that end_time > start_time for all events

### FR-3: Date Range Query
System SHALL support querying events by date range with pagination

### FR-4: Today/Upcoming Query
System SHALL provide optimized queries for today's and upcoming events

### FR-5: External Sync
System SHALL support syncing with Google, Apple, and Outlook calendars

### FR-6: Recurrence
System SHALL support recurring events with standard and custom patterns

### FR-7: Event Sharing
System SHALL support sharing events with other users

### FR-8: Event Publishing
System SHALL publish events for all mutations to NATS

### FR-9: Health Checks
System SHALL provide /health endpoint

### FR-10: Category Filtering
System SHALL support filtering events by category

---

## Non-Functional Requirements

### NFR-1: Performance
- **Create Event**: <100ms (p95)
- **Get Event**: <50ms (p95)
- **Query Events**: <200ms (p95)
- **External Sync**: <5000ms (p95)
- **Health Check**: <20ms (p99)

### NFR-2: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **Database Failover**: Automatic with <30s recovery
- **Graceful Degradation**: Event failures don't block operations

### NFR-3: Scalability
- **Concurrent Requests**: 500+ concurrent
- **Events per User**: 10,000+ supported
- **Throughput**: 100 requests/second
- **Database Connections**: Pooled with max 20 connections

### NFR-4: Data Integrity
- **ACID Transactions**: All mutations in PostgreSQL transactions
- **Validation**: Pydantic models validate all inputs
- **Audit Trail**: All changes tracked with timestamps

### NFR-5: Security
- **Authentication**: JWT validation by API Gateway
- **Authorization**: User-scoped data access
- **Input Sanitization**: SQL injection prevention

### NFR-6: Observability
- **Structured Logging**: JSON logs for all operations
- **Tracing**: Request IDs for debugging
- **Health Monitoring**: Database connectivity checked

---

## Dependencies

### External Services

1. **PostgreSQL gRPC Service**: Event data storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `calendar`
   - Tables: `events`, `sync_status`

2. **NATS Event Bus**: Event publishing
   - Host: `isa-nats:4222`
   - Subjects: `calendar.event.created`, `calendar.event.updated`, `calendar.event.deleted`

3. **Consul**: Service discovery
   - Host: `localhost:8500`
   - Service Name: `calendar_service`

4. **External Calendar APIs** (Optional):
   - Google Calendar API
   - Apple CalDAV
   - Microsoft Graph API

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration

---

## Success Criteria

### Phase 1: Core Functionality (Current)
- [x] Event CRUD working
- [x] Date range queries functional
- [x] PostgreSQL storage stable
- [x] Event publishing active
- [x] Health checks implemented
- [x] DI architecture (protocols.py, factory.py)

### Phase 2: Enhanced Features
- [ ] External calendar sync (Google, Apple, Outlook)
- [ ] Recurrence rule parsing
- [ ] Event sharing
- [ ] Comprehensive test coverage

### Phase 3: Production Hardening
- [ ] Performance benchmarks met
- [ ] Load testing completed
- [ ] Monitoring setup

---

## Out of Scope

1. **Push Notifications**: Handled by Notification Service
2. **OAuth Token Storage**: Handled by Auth Service
3. **User Authentication**: Handled by API Gateway
4. **Task Management**: Handled by Task Service
5. **Video Conferencing**: Future feature

---

## Appendix: Request/Response Examples

### 1. Create Event with Recurrence

**Request**:
```bash
curl -X POST http://localhost:8240/api/v1/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_abc123",
    "title": "Daily Standup",
    "start_time": "2025-01-15T09:00:00Z",
    "end_time": "2025-01-15T09:15:00Z",
    "category": "meeting",
    "recurrence_type": "daily",
    "recurrence_end_date": "2025-03-31T23:59:59Z",
    "reminders": [5]
  }'
```

### 2. Query Events with Filters

**Request**:
```bash
curl -X GET "http://localhost:8240/api/v1/calendar/events?user_id=usr_abc123&start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z&category=meeting&limit=50"
```

### 3. Sync Google Calendar

**Request**:
```bash
curl -X POST "http://localhost:8240/api/v1/calendar/sync?user_id=usr_abc123&provider=google_calendar" \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "ya29.xxx",
    "refresh_token": "1//0xxx"
  }'
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Calendar Service Product Team
**Related Documents**:
- Domain Context: docs/domain/calendar_service.md
- Design Doc: docs/design/calendar_service.md
- Data Contract: tests/contracts/calendar/data_contract.py
- Logic Contract: tests/contracts/calendar/logic_contract.md
