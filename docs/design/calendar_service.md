# Calendar Service - Design Document

## Design Overview

**Service Name**: calendar_service
**Port**: 8240
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-17

### Design Principles
1. **Time-Centric Design**: All operations centered around datetime handling with timezone support
2. **Multi-Source Integration**: Support for external calendar providers (Google, Apple, Outlook)
3. **Event-Driven Synchronization**: Loose coupling via NATS events
4. **Separation of Concerns**: Calendar owns events, Notification owns reminders
5. **ACID Guarantees**: PostgreSQL transactions for data integrity
6. **Graceful Degradation**: External sync and event failures don't block operations

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Mobile App, Web App, Device Service, Task Service)      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 Calendar Service (Port 8240)                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - Response formatting                                │ │
│  │  - Error handling & exception handlers                │ │
│  │  - Health checks (/health)                            │ │
│  │  - Lifecycle management (startup/shutdown)            │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Service Layer (calendar_service.py)              │ │
│  │  - Business logic (event CRUD)                        │ │
│  │  - Time validation (end > start)                      │ │
│  │  - External calendar sync                             │ │
│  │  - Event publishing orchestration                     │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Repository Layer (calendar_repository.py)        │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - GDPR data deletion                                 │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Event Publishing (events/)                        │ │
│  │  - NATS event bus integration                         │ │
│  │  - calendar.event.* subjects                          │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐
│  PostgreSQL  │ │    NATS     │ │   Consul   │
│   (gRPC)     │ │  (Events)   │ │ (Discovery)│
│              │ │             │ │            │
│  Schema:     │ │  Subjects:  │ │  Service:  │
│  calendar    │ │ calendar.*  │ │  calendar_ │
│              │ │             │ │  service   │
│  Tables:     │ │  Publishers:│ │            │
│  - events    │ │  - created  │ │  Health:   │
│  - sync_     │ │  - updated  │ │  /health   │
│    status    │ │  - deleted  │ │            │
└──────────────┘ └─────────────┘ └────────────┘

External Calendar APIs (Optional):
┌──────────────────────────────────────────┐
│ Google Calendar API │ Apple CalDAV │ MS Graph │
└──────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Calendar Service                        │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐    │
│  │   Models    │───→│   Service   │───→│ Repository   │    │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │    │
│  │             │    │             │    │              │    │
│  │ CalendarEvt │    │ CalendarSvc │    │ CalendarRepo │    │
│  │ EventCreate │    │             │    │              │    │
│  │ EventUpdate │    │             │    │              │    │
│  │ EventQuery  │    │             │    │              │    │
│  │ SyncStatus  │    │             │    │              │    │
│  └─────────────┘    └─────────────┘    └──────────────┘    │
│         ↑                  ↑                    ↑            │
│         │                  │                    │            │
│  ┌──────┴──────────────────┴────────────────────┴────────┐ │
│  │              FastAPI Main (main.py)                    │ │
│  │  - Dependency Injection (create_calendar_service)     │ │
│  │  - Route Handlers (10 endpoints)                      │ │
│  │  - Exception Handlers                                 │ │
│  └────────────────────────┬───────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐ │
│  │              Factory + Protocols (DI)                   │ │
│  │  (factory.py, protocols.py)                            │ │
│  │  - create_calendar_service (production)                │ │
│  │  - CalendarEventRepositoryProtocol (interface)         │ │
│  │  - EventBusProtocol (interface)                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (10 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup

**Key Endpoints**:
```python
# Health Check
GET /health                                  # Basic health check

# Event CRUD
POST /api/v1/calendar/events                 # Create event
GET  /api/v1/calendar/events/{event_id}      # Get by ID
GET  /api/v1/calendar/events                 # List with filters
PUT  /api/v1/calendar/events/{event_id}      # Update event
DELETE /api/v1/calendar/events/{event_id}    # Delete event

# Query Shortcuts
GET /api/v1/calendar/today                   # Today's events
GET /api/v1/calendar/upcoming                # Upcoming events

# External Sync
POST /api/v1/calendar/sync                   # Sync external calendar
GET  /api/v1/calendar/sync/status            # Get sync status
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus("calendar_service")
    await microservice.initialize()

    # Subscribe to events
    from .events import CalendarEventHandlers
    event_handlers = CalendarEventHandlers(service)
    for event_type, handler in event_handlers.get_event_handler_map().items():
        await event_bus.subscribe_to_events(pattern=f"*.{event_type}", handler=handler)

    # Consul registration
    if config.consul_enabled:
        consul_registry.register()

    yield

    # Shutdown
    await microservice.shutdown()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (calendar_service.py)

**Class**: `CalendarService`

**Responsibilities**:
- Business logic execution
- Time validation (end > start)
- Event publishing coordination
- External calendar sync orchestration

**Key Methods**:
```python
class CalendarService:
    def __init__(
        self,
        repository: CalendarEventRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None
    ):
        self.repo = repository
        self.event_bus = event_bus

    async def create_event(self, request: EventCreateRequest) -> EventResponse:
        """Create calendar event with validation"""
        # 1. Validate end_time > start_time
        if request.end_time <= request.start_time:
            raise CalendarServiceValidationError("End time must be after start time")

        # 2. Create in database
        event = await self.repo.create_event(request.dict())

        # 3. Publish event
        if self.event_bus:
            await self._publish_event_created(event)

        return event

    async def get_event(self, event_id: str, user_id: str = None) -> EventResponse:
        """Get event by ID"""
        return await self.repo.get_event_by_id(event_id, user_id)

    async def query_events(self, request: EventQueryRequest) -> EventListResponse:
        """Query events with filters and pagination"""
        events = await self.repo.get_events_by_user(
            user_id=request.user_id,
            start_date=request.start_date,
            end_date=request.end_date,
            category=request.category.value if request.category else None,
            limit=request.limit,
            offset=request.offset
        )
        return EventListResponse(events=events, total=len(events), ...)

    async def update_event(self, event_id: str, request: EventUpdateRequest, user_id: str) -> EventResponse:
        """Update event with validation"""
        # Validate, update, publish event
        pass

    async def delete_event(self, event_id: str, user_id: str) -> bool:
        """Delete event and publish deletion event"""
        pass

    async def get_today_events(self, user_id: str) -> List[EventResponse]:
        """Get events for today"""
        return await self.repo.get_today_events(user_id)

    async def get_upcoming_events(self, user_id: str, days: int = 7) -> List[EventResponse]:
        """Get upcoming events for N days"""
        return await self.repo.get_upcoming_events(user_id, days)

    async def sync_with_external_calendar(self, user_id: str, provider: str, credentials: dict) -> SyncStatusResponse:
        """Sync with external calendar provider"""
        if provider == "google_calendar":
            synced_count = await self._sync_google_calendar(user_id, credentials)
        elif provider == "apple_calendar":
            synced_count = await self._sync_apple_calendar(user_id, credentials)
        elif provider == "outlook":
            synced_count = await self._sync_outlook_calendar(user_id, credentials)

        await self.repo.update_sync_status(user_id, provider, "active", synced_count)
        return SyncStatusResponse(...)
```

**Custom Exceptions**:
```python
class CalendarServiceError(Exception):
    """Base exception for calendar service"""
    pass

class CalendarServiceValidationError(CalendarServiceError):
    """Validation error (e.g., invalid time range)"""
    pass
```

### 3. Repository Layer (calendar_repository.py)

**Class**: `CalendarRepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- GDPR data deletion

**Key Methods**:
```python
class CalendarRepository:
    def __init__(self, config: ConfigManager = None):
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id='calendar_service')
        self.schema = "calendar"
        self.table_name = "calendar_events"
        self.sync_table = "calendar_sync_status"

    async def create_event(self, event_data: Dict[str, Any]) -> EventResponse:
        """Create calendar event"""
        event_id = f"evt_{uuid.uuid4().hex[:16]}"
        query = f"""
            INSERT INTO {self.schema}.{self.table_name} (
                event_id, user_id, title, description, location,
                start_time, end_time, all_day, category, recurrence_type, ...
            ) VALUES ($1, $2, ...) RETURNING *
        """
        async with self.db:
            results = await self.db.query(query, params=[...])
        return EventResponse(**results[0])

    async def get_event_by_id(self, event_id: str, user_id: str = None) -> EventResponse:
        """Get event by ID with optional user filter"""
        pass

    async def get_events_by_user(self, user_id: str, start_date, end_date, category, limit, offset) -> List[EventResponse]:
        """Query events with filters"""
        pass

    async def get_today_events(self, user_id: str) -> List[EventResponse]:
        """Get today's events (00:00 - 23:59 UTC)"""
        pass

    async def get_upcoming_events(self, user_id: str, days: int) -> List[EventResponse]:
        """Get events from now to N days ahead"""
        pass

    async def update_event(self, event_id: str, updates: Dict) -> EventResponse:
        """Update event fields dynamically"""
        pass

    async def delete_event(self, event_id: str, user_id: str = None) -> bool:
        """Delete event (hard delete)"""
        pass

    async def update_sync_status(self, user_id, provider, status, synced_count, error_message) -> bool:
        """Upsert sync status (ON CONFLICT)"""
        pass

    async def get_sync_status(self, user_id: str, provider: str = None) -> Dict:
        """Get sync status for user/provider"""
        pass

    async def delete_user_data(self, user_id: str) -> int:
        """GDPR: Delete all user calendar data"""
        pass
```

---

## Database Schema Design

### PostgreSQL Schema: `calendar`

#### Table: calendar.calendar_events

```sql
CREATE SCHEMA IF NOT EXISTS calendar;

CREATE TABLE IF NOT EXISTS calendar.calendar_events (
    -- Primary Key
    event_id VARCHAR(255) PRIMARY KEY,

    -- Ownership
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Event Details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(500),

    -- Time Information
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    all_day BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Categorization
    category VARCHAR(50) DEFAULT 'other',
    color VARCHAR(7),  -- #RRGGBB

    -- Recurrence
    recurrence_type VARCHAR(20) DEFAULT 'none',
    recurrence_end_date TIMESTAMPTZ,
    recurrence_rule TEXT,  -- iCalendar RRULE

    -- Reminders (array of minutes)
    reminders INTEGER[] DEFAULT '{}',

    -- External Sync
    sync_provider VARCHAR(50) DEFAULT 'local',
    external_event_id VARCHAR(255),
    last_synced_at TIMESTAMPTZ,

    -- Sharing
    is_shared BOOLEAN DEFAULT FALSE,
    shared_with TEXT[] DEFAULT '{}',

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_calendar_events_user_id ON calendar.calendar_events(user_id);
CREATE INDEX idx_calendar_events_start_time ON calendar.calendar_events(start_time);
CREATE INDEX idx_calendar_events_end_time ON calendar.calendar_events(end_time);
CREATE INDEX idx_calendar_events_category ON calendar.calendar_events(category);
CREATE INDEX idx_calendar_events_sync_provider ON calendar.calendar_events(sync_provider);
```

#### Table: calendar.calendar_sync_status

```sql
CREATE TABLE IF NOT EXISTS calendar.calendar_sync_status (
    user_id VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    last_sync_time TIMESTAMPTZ,
    synced_events_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (user_id, provider)
);

CREATE INDEX idx_sync_status_user_id ON calendar.calendar_sync_status(user_id);
CREATE INDEX idx_sync_status_provider ON calendar.calendar_sync_status(provider);
```

### Index Strategy

1. **Primary Key** (`event_id`): Clustered index for fast lookups
2. **User ID Index**: Filter events by user
3. **Time Indexes**: Range queries on start_time/end_time
4. **Category Index**: Filter by event category
5. **Sync Provider Index**: Filter by external source

---

## Event-Driven Architecture

### Event Publishing

**NATS Subjects**:
```
calendar.event.created     # New event created
calendar.event.updated     # Event fields updated
calendar.event.deleted     # Event deleted
```

### Event Payloads

```python
# calendar.event.created
{
    "event_id": "evt_abc123",
    "user_id": "usr_xyz789",
    "title": "Team Meeting",
    "start_time": "2025-01-15T10:00:00Z",
    "end_time": "2025-01-15T11:00:00Z",
    "timestamp": "2025-01-10T08:00:00Z"
}

# calendar.event.updated
{
    "event_id": "evt_abc123",
    "user_id": "usr_xyz789",
    "updated_fields": ["title", "start_time"],
    "timestamp": "2025-01-10T09:00:00Z"
}

# calendar.event.deleted
{
    "event_id": "evt_abc123",
    "user_id": "usr_xyz789",
    "timestamp": "2025-01-10T10:00:00Z"
}
```

### Event Subscribers

| Event | Subscriber | Action |
|-------|------------|--------|
| `calendar.event.created` | Notification Service | Create reminders |
| `calendar.event.updated` | Notification Service | Update reminders |
| `calendar.event.deleted` | Notification Service | Cancel reminders |
| `account.user.deleted` | Calendar Service | Delete user events |

### Event Flow Diagram

```
User creates event
    │
    ↓
POST /api/v1/calendar/events
    │
    ↓
┌──────────────────┐
│  CalendarService │
│                  │
│  1. Validate     │
│  2. Create       │───→ PostgreSQL (calendar.calendar_events)
│  3. Publish      │         │
└──────────────────┘         │ Success
       │                     ↓
       │              Return EventResponse
       │
       │ calendar.event.created
       ↓
┌─────────────────┐
│   NATS Bus      │
└────────┬────────┘
         │
         ├──→ Notification Service (create reminders)
         ├──→ Audit Service (log creation)
         └──→ Analytics Service (track usage)
```

---

## Data Flow Diagrams

### 1. Create Event Flow

```
User → POST /api/v1/calendar/events
    │
    ↓
┌─────────────────────────────────┐
│  CalendarService.create_event   │
│                                 │
│  Step 1: Validate times         │
│    end_time > start_time        │
│    If invalid → 400 Bad Request │
│                                 │
│  Step 2: Create event           │
│    repository.create_event() ───┼──→ PostgreSQL: INSERT
│                            ←────┤    RETURNING *
│                                 │
│  Step 3: Publish event          │
│    publish_event_created() ─────┼──→ NATS: calendar.event.created
│                                 │
└─────────────────────────────────┘
    │
    │ Return EventResponse (201 Created)
    ↓
User receives event with event_id
```

### 2. Query Events Flow

```
User → GET /api/v1/calendar/events?user_id=X&start_date=Y&end_date=Z
    │
    ↓
┌─────────────────────────────────┐
│  CalendarService.query_events   │
│                                 │
│  repository.get_events_by_user()│───→ PostgreSQL:
│    user_id=X                    │       SELECT * FROM calendar.calendar_events
│    start_date=Y                 │       WHERE user_id = $1
│    end_date=Z                   │         AND start_time >= $2
│    category=optional            │         AND end_time <= $3
│    limit=100, offset=0          │       ORDER BY start_time ASC
│                            ←────┤       LIMIT 100 OFFSET 0
│    Result: List[EventResponse]  │
│                                 │
│  Return EventListResponse       │
│    events, total, page, size    │
└─────────────────────────────────┘
    │
    │ Return 200 OK
    ↓
User receives paginated event list
```

### 3. External Sync Flow

```
User → POST /api/v1/calendar/sync?provider=google_calendar
    │
    ↓
┌───────────────────────────────────────────┐
│  CalendarService.sync_with_external_cal   │
│                                           │
│  Step 1: Identify provider                │
│    google_calendar → _sync_google()       │
│                                           │
│  Step 2: Call external API                │
│    (Google Calendar API) ─────────────────┼──→ External Service
│                                      ←────┤    Events list
│                                           │
│  Step 3: Import events                    │
│    repository.create_event() (per event)  │
│                                           │
│  Step 4: Update sync status               │
│    repository.update_sync_status() ───────┼──→ PostgreSQL: UPSERT
│                                           │
│  Return SyncStatusResponse                │
│    provider, last_synced, count, status   │
└───────────────────────────────────────────┘
    │
    ↓
User receives sync summary
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `calendar`
- **Tables**: `calendar_events`, `calendar_sync_status`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `calendar.event.*`
- **Publishers**: Calendar Service
- **Subscribers**: Notification, Audit, Analytics

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Dependency Injection
- **Protocols**: `CalendarEventRepositoryProtocol`, `EventBusProtocol`
- **Factory**: `create_calendar_service()`
- **ConfigManager**: Environment-based configuration

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **Time Validation**: end_time > start_time enforced
- **SQL Injection**: Parameterized queries via gRPC

### Access Control
- **User Isolation**: Events filtered by user_id
- **JWT Authentication**: Handled by API Gateway
- **Optional user_id**: For authorization checks

### Data Privacy
- **GDPR Compliance**: delete_user_data() for right to erasure
- **Hard Delete**: Events are physically deleted (not soft delete)

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New event created
- `204 No Content`: Successful deletion
- `400 Bad Request`: Validation error (e.g., invalid times)
- `404 Not Found`: Event not found
- `500 Internal Server Error`: Database error

### Error Response Format
```json
{
  "detail": "End time must be after start time"
}
```

---

## Testing Strategy

### Test Pyramid
- **Unit Tests**: Model validation, time calculations
- **Component Tests**: Service logic with mocked repository
- **Integration Tests**: HTTP + Database
- **API Tests**: Full endpoint testing with JWT
- **Smoke Tests**: E2E bash scripts

### Key Test Scenarios
1. Create event with valid/invalid times
2. Query events by date range
3. Update event fields
4. Delete event
5. Get today/upcoming events
6. External sync (mocked)
7. GDPR data deletion

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Calendar Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/calendar_service.md
- PRD: docs/prd/calendar_service.md
- Data Contract: tests/contracts/calendar/data_contract.py
- Logic Contract: tests/contracts/calendar/logic_contract.md
- System Contract: tests/contracts/calendar/system_contract.md
