# Calendar Service - System Contract

**Implementation Patterns and Architecture for Calendar Service**

This document defines HOW calendar_service implements the 12 standard patterns.
Pattern Reference: `.claude/skills/cdd-system-contract/SKILL.md`

---

## Table of Contents

1. [Service Identity](#service-identity)
2. [Architecture Pattern](#architecture-pattern)
3. [Dependency Injection Pattern](#dependency-injection-pattern)
4. [Event Publishing Pattern](#event-publishing-pattern)
5. [Event Subscription Pattern](#event-subscription-pattern)
6. [Client Pattern (Sync)](#client-pattern-sync)
7. [Repository Pattern](#repository-pattern)
8. [Service Registration Pattern](#service-registration-pattern)
9. [Migration Pattern](#migration-pattern)
10. [Lifecycle Pattern](#lifecycle-pattern)
11. [Configuration Pattern](#configuration-pattern)
12. [Logging Pattern](#logging-pattern)

---

## Service Identity

| Property | Value |
|----------|-------|
| **Service Name** | `calendar_service` |
| **Port** | `8240` |
| **Schema** | `calendar` (migrated from public) |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/calendar_service/` |

---

## Architecture Pattern

### File Structure
```
microservices/calendar_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle
├── calendar_service.py        # Business logic layer
├── calendar_repository.py     # Data access layer (PostgreSQL)
├── models.py                  # Pydantic models (CalendarEvent, enums)
├── protocols.py               # DI interfaces
├── factory.py                 # DI factory
├── routes_registry.py         # Consul route registration
├── clients/
│   ├── __init__.py
│   └── account_client.py      # Sync call to account_service
├── events/
│   ├── __init__.py
│   ├── models.py              # Event Pydantic models (empty)
│   ├── publishers.py          # NATS publish (empty - inline in service)
│   └── handlers.py            # NATS subscribe handlers
└── migrations/
    ├── 001_create_calendar_tables.sql
    └── 002_migrate_to_calendar_schema.sql
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring |
| Business | `calendar_service.py` | Event CRUD, validation, sync logic |
| Data | `calendar_repository.py` | PostgreSQL queries, schema operations |
| External | `clients/` | HTTP calls to account_service |
| Async | `events/` | NATS event subscriptions |

---

## Dependency Injection Pattern

### Protocols (`protocols.py`)
```python
from typing import Protocol, runtime_checkable, Dict, Any, Optional, List
from datetime import datetime

@runtime_checkable
class CalendarEventRepositoryProtocol(Protocol):
    """Repository interface for calendar events"""

    async def create_event(self, user_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar event"""
        ...

    async def get_event(self, event_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get event by ID"""
        ...

    async def update_event(self, event_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update event"""
        ...

    async def delete_event(self, event_id: str, user_id: Optional[str] = None) -> bool:
        """Delete event"""
        ...

    async def get_events_by_date_range(
        self, user_id: str, start_date: datetime, end_date: datetime,
        category: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query events by date range"""
        ...

    async def get_today_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get today's events"""
        ...

    async def get_upcoming_events(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events"""
        ...

    async def get_sync_status(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """Get sync status for provider"""
        ...

    async def upsert_sync_status(self, user_id: str, provider: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert sync status"""
        ...

    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user data (GDPR)"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for publishing events"""

    async def publish(self, subject: str, data: Dict[str, Any]) -> None:
        """Publish event to NATS"""
        ...
```

### Factory (`factory.py`)
```python
from core.config_manager import ConfigManager
from .calendar_service import CalendarService
from .calendar_repository import CalendarRepository

def create_calendar_service(
    config: ConfigManager,
    event_bus=None,
) -> CalendarService:
    """Create CalendarService with real dependencies"""
    repository = CalendarRepository(config=config)
    return CalendarService(
        repository=repository,
        event_bus=event_bus,
    )
```

---

## Event Publishing Pattern

### Events Published

| Event | Subject | Trigger | Data |
|-------|---------|---------|------|
| `CALENDAR_EVENT_CREATED` | `calendar.event.created` | After event creation | `event_id`, `user_id`, `title`, `start_time`, `end_time` |
| `CALENDAR_EVENT_UPDATED` | `calendar.event.updated` | After event update | `event_id`, `user_id`, `updated_fields` |
| `CALENDAR_EVENT_DELETED` | `calendar.event.deleted` | After event deletion | `event_id`, `user_id` |

### Event Publishing (inline in `calendar_service.py`)
```python
async def create_event(self, user_id: str, event_data: CreateEventRequest) -> CalendarEventResponse:
    # ... create logic ...

    # Publish event
    if self.event_bus:
        await self.event_bus.publish(
            "calendar.event.created",
            {
                "event_type": "CALENDAR_EVENT_CREATED",
                "source": "calendar_service",
                "data": {
                    "event_id": result["event_id"],
                    "user_id": user_id,
                    "title": event_data.title,
                    "start_time": event_data.start_time.isoformat(),
                    "end_time": event_data.end_time.isoformat(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    return result
```

### Event Payload Examples

**calendar.event.created**
```json
{
  "event_type": "CALENDAR_EVENT_CREATED",
  "source": "calendar_service",
  "data": {
    "event_id": "evt_abc123def456",
    "user_id": "usr_xyz789",
    "title": "Team Meeting",
    "start_time": "2025-01-15T10:00:00Z",
    "end_time": "2025-01-15T11:00:00Z",
    "timestamp": "2025-01-10T08:00:00Z"
  }
}
```

---

## Event Subscription Pattern

### Events Subscribed

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| `user.deleted` | account_service | `handle_user_deleted` | Delete all user calendar data (GDPR) |
| `task_service.task.created` | task_service | `handle_task_created` | Create calendar event for scheduled tasks |
| `task_service.task.completed` | task_service | `handle_task_completed` | Update/mark calendar event as completed |

### Handler (`events/handlers.py`)
```python
class CalendarEventHandlers:
    """Calendar service event handlers"""

    def __init__(self, calendar_service):
        self.service = calendar_service
        self.repository = calendar_service.repository

    def get_event_handler_map(self) -> Dict[str, Callable]:
        return {
            "user.deleted": self.handle_user_deleted,
            "task_service.task.created": self.handle_task_created,
            "task_service.task.completed": self.handle_task_completed,
        }

    async def handle_user_deleted(self, event_data: dict):
        """GDPR compliance - delete all user data"""
        user_id = event_data.get("user_id")
        if user_id:
            deleted_count = await self.repository.delete_user_data(user_id)
            logger.info(f"Deleted {deleted_count} calendar records for user {user_id}")

    async def handle_task_created(self, event_data: dict):
        """Sync scheduled tasks to calendar"""
        # Only sync tasks with schedule or due_date
        if event_data.get("schedule") or event_data.get("due_date"):
            await self.repository.create_event_from_task(
                user_id=event_data["user_id"],
                event_data={...}
            )

    async def handle_task_completed(self, event_data: dict):
        """Update calendar when task completes"""
        await self.repository.update_event_from_task(
            user_id=event_data["user_id"],
            task_id=event_data["task_id"],
            updates={"status": "completed"}
        )
```

---

## Client Pattern (Sync)

### Dependencies (Outbound HTTP Calls)

| Client | Target Service | Purpose |
|--------|----------------|---------|
| `AccountClient` | `account_service:8202` | Verify user exists |

### Client Implementation (`clients/account_client.py`)
```python
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AccountClient:
    """Sync HTTP client for account_service"""

    def __init__(self, base_url: str = "http://localhost:8202"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from account_service"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}",
                headers={"X-Internal-Call": "true"}
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    async def close(self):
        await self.client.aclose()
```

---

## Repository Pattern

### Schema: `calendar` (migrated from public)

### Tables

| Table | Purpose |
|-------|---------|
| `calendar.calendar_events` | Main event storage |
| `calendar.calendar_sync_status` | External calendar sync tracking |

### Database Schema (`001_create_calendar_tables.sql`)

**calendar_events**
```sql
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),

    -- Event details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),

    -- Time information
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    all_day BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Categorization
    category VARCHAR(50) DEFAULT 'other',
    color VARCHAR(7),  -- #RRGGBB format

    -- Recurrence
    recurrence_type VARCHAR(20) DEFAULT 'none',
    recurrence_end_date TIMESTAMP WITH TIME ZONE,
    recurrence_rule TEXT,  -- iCalendar RRULE format

    -- Reminders (JSON array of minutes)
    reminders JSONB DEFAULT '[]'::jsonb,

    -- External sync
    sync_provider VARCHAR(50) DEFAULT 'local',
    external_event_id VARCHAR(255),
    last_synced_at TIMESTAMP WITH TIME ZONE,

    -- Sharing
    is_shared BOOLEAN DEFAULT FALSE,
    shared_with TEXT[],

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**calendar_sync_status**
```sql
CREATE TABLE IF NOT EXISTS calendar_sync_status (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    last_sync_time TIMESTAMP WITH TIME ZONE,
    sync_token TEXT,
    synced_events_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, provider)
);
```

### Indexes
```sql
-- Primary lookups
CREATE INDEX idx_events_user_id ON calendar_events(user_id);
CREATE INDEX idx_events_org_id ON calendar_events(organization_id);
CREATE INDEX idx_events_start_time ON calendar_events(start_time);
CREATE INDEX idx_events_end_time ON calendar_events(end_time);
CREATE INDEX idx_events_category ON calendar_events(category);

-- Composite indexes for common queries
CREATE INDEX idx_events_user_time_range ON calendar_events(user_id, start_time, end_time);
CREATE INDEX idx_events_user_category ON calendar_events(user_id, category);
```

---

## Service Registration Pattern

### Routes Registry (`routes_registry.py`)
```python
SERVICE_ROUTES = [
    {"path": "/health", "methods": ["GET"], "auth_required": False},
    {"path": "/api/v1/events", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/events/{event_id}", "methods": ["GET", "PUT", "DELETE"], "auth_required": True},
    {"path": "/api/v1/events/today", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/events/upcoming", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/sync/{provider}", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/sync/{provider}/status", "methods": ["GET"], "auth_required": True},
]

SERVICE_METADATA = {
    "service_name": "calendar_service",
    "version": "1.0.0",
    "tags": ["v1", "calendar", "events"],
    "capabilities": [
        "event_management",
        "event_query",
        "external_sync",
        "recurrence"
    ]
}
```

### API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/events` | Create event |
| GET | `/api/v1/events` | Query events (date range) |
| GET | `/api/v1/events/{event_id}` | Get single event |
| PUT | `/api/v1/events/{event_id}` | Update event |
| DELETE | `/api/v1/events/{event_id}` | Delete event |
| GET | `/api/v1/events/today` | Today's events |
| GET | `/api/v1/events/upcoming` | Upcoming events |
| POST | `/api/v1/sync/{provider}` | Trigger external sync |
| GET | `/api/v1/sync/{provider}/status` | Get sync status |

---

## Migration Pattern

### Migration Files
```
migrations/
├── 001_create_calendar_tables.sql    # Initial schema (public schema)
└── 002_migrate_to_calendar_schema.sql # Migrate to dedicated schema
```

### Migration Sequence
1. `001_create_calendar_tables.sql` - Creates tables in public schema
2. `002_migrate_to_calendar_schema.sql` - Migrates to `calendar` schema

### Schema Evolution Pattern
- New migrations follow `NNN_description.sql` naming
- Each migration is idempotent (IF NOT EXISTS)
- Triggers auto-update `updated_at` timestamps

---

## Lifecycle Pattern

### Startup Sequence (`main.py`)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize ConfigManager
    config = ConfigManager()

    # 2. Setup logger
    logger = setup_service_logger("calendar_service")

    # 3. Initialize event bus (NATS)
    event_bus = NATSClient()
    await event_bus.connect()

    # 4. Create service via factory
    calendar_service = create_calendar_service(config, event_bus)

    # 5. Register event handlers (subscriptions)
    handlers = CalendarEventHandlers(calendar_service)
    for event_type, handler in handlers.get_event_handler_map().items():
        await event_bus.subscribe(event_type, handler)

    # 6. Initialize service clients
    account_client = AccountClient()

    # 7. Register with Consul
    await register_service_routes(SERVICE_ROUTES, SERVICE_METADATA)

    # 8. Store in app state
    app.state.service = calendar_service
    app.state.account_client = account_client

    logger.info("Calendar service started")

    yield  # App runs

    # Shutdown
    await account_client.close()
    await event_bus.close()
    logger.info("Calendar service stopped")
```

### Shutdown Sequence
1. Deregister from Consul
2. Close service clients (AccountClient)
3. Close event bus (NATS)
4. Log shutdown complete

---

## Configuration Pattern

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CALENDAR_SERVICE_PORT` | `8240` | Service port |
| `CALENDAR_SERVICE_HOST` | `0.0.0.0` | Service host |
| `CONSUL_ENABLED` | `true` | Enable Consul registration |
| `NATS_URL` | `nats://nats:4222` | NATS connection URL |
| `DATABASE_URL` | - | PostgreSQL connection string |

### ConfigManager Usage
```python
from core.config_manager import ConfigManager

config = ConfigManager()

# Access configuration
port = config.get("CALENDAR_SERVICE_PORT", 8240)
nats_url = config.get("NATS_URL", "nats://nats:4222")
db_url = config.get("DATABASE_URL")
```

---

## Logging Pattern

### Logger Setup
```python
from core.logger import setup_service_logger

logger = setup_service_logger("calendar_service")

# Usage examples
logger.info("Event created", extra={"event_id": event_id, "user_id": user_id})
logger.warning(f"Sync failed for provider: {provider}")
logger.error(f"Failed to delete event: {error}", exc_info=True)
```

### Structured Log Fields
- `event_id`: Calendar event identifier
- `user_id`: User performing action
- `provider`: Sync provider (google_calendar, apple_calendar, outlook)
- `operation`: CRUD operation type
- `duration_ms`: Operation duration

---

## Compliance Checklist

- [x] `protocols.py` with DI interfaces (CalendarEventRepositoryProtocol, EventBusProtocol)
- [x] `factory.py` for service creation (create_calendar_service)
- [x] `routes_registry.py` for Consul (SERVICE_ROUTES, SERVICE_METADATA)
- [x] `migrations/` folder with SQL files (001, 002)
- [x] `events/handlers.py` for subscriptions (user.deleted, task.created, task.completed)
- [ ] `events/publishers.py` for publishing (currently inline in service)
- [x] `clients/` for sync dependencies (account_client.py)
- [x] Error handling with custom exceptions (CalendarServiceError hierarchy)
- [x] Structured logging (setup_service_logger)
- [x] ConfigManager usage

---

**Version**: 1.0.0
**Last Updated**: 2025-12-17
**Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md`
