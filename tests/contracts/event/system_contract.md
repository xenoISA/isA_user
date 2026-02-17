# Event Service - System Contract

**Implementation Patterns and Architecture for Event Service**

This document defines HOW event_service implements the 12 standard patterns.
Pattern Reference: `.claude/skills/cdd-system-contract/SKILL.md`

---

## Table of Contents

1. [Service Identity](#service-identity)
2. [Service Initialization (Lifespan Pattern)](#1-service-initialization-lifespan-pattern)
3. [Dependency Injection Pattern](#2-dependency-injection-pattern)
4. [Health Checks Pattern](#3-health-checks-pattern)
5. [Configuration Management Pattern](#4-configuration-management-pattern)
6. [Error Handling Pattern](#5-error-handling-pattern)
7. [Logging Strategy Pattern](#6-logging-strategy-pattern)
8. [API Patterns](#7-api-patterns)
9. [Event Publishing Pattern](#8-event-publishing-pattern)
10. [Event Subscription Pattern](#9-event-subscription-pattern)
11. [Service Discovery Pattern](#10-service-discovery-pattern)
12. [Database Access Pattern](#11-database-access-pattern)
13. [Client SDK Pattern](#12-client-sdk-pattern)

---

## Service Identity

| Property | Value |
|----------|-------|
| **Service Name** | `event_service` |
| **Port** | `8230` |
| **Schema** | `event` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/event_service/` |
| **Description** | Unified event management service for event sourcing, collection, and replay |

---

## Architecture Overview

### File Structure
```
microservices/event_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle management
├── event_service.py           # Business logic layer
├── event_repository.py        # Data access layer (PostgreSQL via gRPC)
├── models.py                  # Pydantic models (Event, EventStream, etc.)
├── routes_registry.py         # Consul route registration
├── client.py                  # HTTP client SDK (EventServiceClient)
├── clients/
│   ├── __init__.py
│   └── account_client.py      # Sync call to account_service
└── events/
    ├── __init__.py
    ├── models.py              # Event payload models
    ├── publishers.py          # NATS publish functions
    └── handlers.py            # NATS subscribe handlers
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring, lifespan |
| Business | `event_service.py` | Event CRUD, processing, replay, projections |
| Data | `event_repository.py` | PostgreSQL queries via AsyncPostgresClient (gRPC) |
| External | `clients/` | HTTP calls to other services |
| Async | `events/` | NATS event publishing and subscriptions |
| SDK | `client.py` | Client library for other services |

---

## 1. Service Initialization (Lifespan Pattern)

### Lifespan Context Manager (`main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global event_service, event_repository, nats_client, js, event_bus, consul_registry

    try:
        # 1. Initialize centralized NATS event bus
        try:
            event_bus = await get_event_bus("event_service")
            logger.info("Centralized event bus initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize event bus: {e}")
            event_bus = None

        # 2. Initialize EventService (creates EventRepository internally)
        event_service = EventService(event_bus=event_bus, config_manager=config_manager)
        event_repository = event_service.repository
        await event_repository.initialize()

        # 3. Start background tasks
        batch_size = int(config.get("batch_size", 100))
        asyncio.create_task(process_pending_events(batch_size))

        # 4. Register with Consul (if enabled)
        if config.consul_enabled:
            route_meta = get_routes_for_consul()
            consul_meta = {
                'version': SERVICE_METADATA['version'],
                'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                **route_meta
            }
            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA['service_name'],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA['tags'],
                meta=consul_meta,
                health_check_type='http'
            )
            consul_registry.register()

        yield  # App runs

    finally:
        # Shutdown sequence
        if event_bus:
            await event_bus.close()
        if consul_registry:
            consul_registry.deregister()
        if nats_client:
            await nats_client.close()
        if event_repository:
            await event_repository.close()
```

### Startup Sequence

| Step | Action | Details |
|------|--------|---------|
| 1 | Initialize NATS | `get_event_bus("event_service")` via gRPC |
| 2 | Create EventService | Injects event_bus and config_manager |
| 3 | Initialize Repository | `await event_repository.initialize()` |
| 4 | Start Background Tasks | `process_pending_events()` loop |
| 5 | Consul Registration | Register routes and metadata |
| 6 | Log Startup | "Service started successfully" |

### Shutdown Sequence

| Step | Action | Details |
|------|--------|---------|
| 1 | Close Event Bus | `await event_bus.close()` |
| 2 | Deregister from Consul | `consul_registry.deregister()` |
| 3 | Close NATS Client | `await nats_client.close()` |
| 4 | Close Repository | `await event_repository.close()` |

---

## 2. Dependency Injection Pattern

### Service Initialization

```python
# main.py - Global service instances
event_service: Optional[EventService] = None
event_repository: Optional[EventRepository] = None
nats_client: Optional[NATS] = None
js: Optional[JetStreamContext] = None
event_bus = None
consul_registry: Optional[ConsulRegistry] = None
```

### FastAPI Dependency Functions

```python
async def get_event_service() -> EventService:
    """Get event service instance"""
    if not event_service:
        raise HTTPException(status_code=503, detail="Event service not initialized")
    return event_service

async def get_nats() -> NATS:
    """Get NATS client"""
    if not nats_client:
        raise HTTPException(status_code=503, detail="NATS not connected")
    return nats_client
```

### Usage in Endpoints

```python
@app.post("/api/v1/events/create", response_model=EventResponse)
async def create_event(
    request: EventCreateRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: EventService = Depends(get_event_service)
):
    event = await service.create_event(request)
    # ...
```

### EventService Constructor Pattern

```python
class EventService:
    def __init__(self, event_bus=None, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager if config_manager else ConfigManager("event_service")
        self.repository = EventRepository(config=self.config_manager)
        self.event_bus = event_bus
        self.processors: Dict[str, EventProcessor] = {}
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.projections: Dict[str, EventProjection] = {}
        self.processing_queue = asyncio.Queue()
        self.is_processing = False
```

---

## 3. Health Checks Pattern

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Basic health check |
| `/api/v1/events/frontend/health` | GET | Frontend collection health |

### Health Check Response

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": config.service_name,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Frontend Health Check

```python
@app.get("/api/v1/events/frontend/health")
async def frontend_health():
    return {
        "status": "healthy",
        "service": "frontend-event-collection",
        "nats_connected": nats_client is not None,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## 4. Configuration Management Pattern

### ConfigManager Usage

```python
# Initialize configuration
config_manager = ConfigManager("event_service")
config = config_manager.get_service_config()
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_SERVICE_PORT` | `8230` | Service port |
| `EVENT_SERVICE_HOST` | `0.0.0.0` | Service host |
| `CONSUL_ENABLED` | `true` | Enable Consul registration |
| `CONSUL_HOST` | `localhost` | Consul host |
| `CONSUL_PORT` | `8500` | Consul port |
| `POSTGRES_HOST` | `isa-postgres-grpc` | PostgreSQL gRPC host |
| `POSTGRES_PORT` | `50061` | PostgreSQL gRPC port |
| `NATS_GRPC_HOST` | `isa-nats-grpc` | NATS gRPC host |
| `NATS_GRPC_PORT` | `50056` | NATS gRPC port |
| `RUDDERSTACK_WEBHOOK_SECRET` | - | RudderStack signature verification |
| `batch_size` | `100` | Batch processing size |
| `processing_interval` | `5` | Processing loop interval (seconds) |

### Service Discovery Pattern

```python
# In EventRepository
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061,
    env_host_key='POSTGRES_HOST',
    env_port_key='POSTGRES_PORT'
)
```

### Priority Order

1. Environment variables (highest)
2. Consul service discovery
3. Localhost fallback (lowest)

---

## 5. Error Handling Pattern

### HTTP Status Codes

| Status | When Used | Example |
|--------|-----------|---------|
| `200` | Success | Event retrieved |
| `201` | Created | Event created (via POST) |
| `400` | Bad Request | Invalid webhook signature |
| `401` | Unauthorized | Invalid RudderStack signature |
| `404` | Not Found | Event/Stream/Projection not found |
| `500` | Internal Error | General exception |
| `503` | Service Unavailable | Service not initialized |

### Exception Handling Pattern

```python
@app.get("/api/v1/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, service: EventService = Depends(get_event_service)):
    try:
        event = await service.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return EventResponse(...)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Service Layer Exception Handling

```python
async def create_event(self, request: EventCreateRequest) -> EventResponse:
    try:
        event = Event(...)
        stored_event = await self.repository.save_event(event)
        # ...
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        raise
```

### Repository Layer Error Handling

```python
async def save_event(self, event: Event) -> Event:
    try:
        # Save logic
        return event
    except Exception as e:
        logger.error(f"Error saving event {event.event_id}: {e}")
        raise
```

---

## 6. Logging Strategy Pattern

### Logger Setup

```python
from core.logger import setup_service_logger

app_logger = setup_service_logger("event_service")
logger = app_logger  # backward compatibility
```

### Logging Patterns

```python
# Info - successful operations
logger.info(f"Event created: {stored_event.event_id} - {stored_event.event_type}")
logger.info(f"Service registered with Consul: {route_meta.get('route_count')} routes")

# Warning - non-critical issues
logger.warning(f"Failed to initialize centralized event bus: {e}. Continuing without event publishing.")
logger.warning(f"Failed to register with Consul: {e}")

# Error - failures
logger.error(f"Error saving event {event.event_id}: {e}")
logger.error(f"Failed to publish event.stored event: {e}")
logger.error(f"Error processing event {event.event_id}: {e}")
```

### Print Statements (Startup/Debug)

```python
print(f"[event-service] Initializing event service...")
print(f"[event-service] Using centralized event bus (NATS via gRPC)")
print(f"[event-service] Service started successfully on port {config.service_port}")
print(f"[event-service] Shutting down...")
```

### Structured Log Fields

| Field | Purpose |
|-------|---------|
| `event_id` | Event identifier |
| `event_type` | Type of event |
| `user_id` | User performing action |
| `processor_name` | Event processor name |
| `subscription_id` | Subscription identifier |
| `duration_ms` | Processing duration |

---

## 7. API Patterns

### Request/Response Models

#### Event Create Request
```python
class EventCreateRequest(BaseModel):
    event_type: str
    event_source: Optional[EventSource] = EventSource.BACKEND
    event_category: Optional[EventCategory] = EventCategory.USER_ACTION
    user_id: Optional[str] = None
    data: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
```

#### Event Response
```python
class EventResponse(BaseModel):
    event_id: str
    event_type: str
    event_source: EventSource
    event_category: EventCategory
    user_id: Optional[str]
    data: Dict[str, Any]
    status: EventStatus
    timestamp: datetime
    created_at: datetime
```

#### Event List Response (Pagination)
```python
class EventListResponse(BaseModel):
    events: List[EventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
```

### Pagination Pattern

```python
class EventQueryRequest(BaseModel):
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    event_source: Optional[EventSource] = None
    event_category: Optional[EventCategory] = None
    status: Optional[EventStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
```

### Filtering Pattern

```python
async def query_events(self, request: EventQueryRequest) -> EventListResponse:
    events, total = await self.repository.query_events(
        user_id=request.user_id,
        event_type=request.event_type,
        event_source=request.event_source,
        event_category=request.event_category,
        status=request.status,
        start_time=request.start_time,
        end_time=request.end_time,
        limit=request.limit,
        offset=request.offset
    )
    return EventListResponse(
        events=responses,
        total=total,
        limit=request.limit,
        offset=request.offset,
        has_more=(request.offset + request.limit) < total
    )
```

### API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | No |
| POST | `/api/v1/events/create` | Create event | Yes |
| POST | `/api/v1/events/batch` | Batch create events | Yes |
| GET | `/api/v1/events/{event_id}` | Get single event | Yes |
| POST | `/api/v1/events/query` | Query events with filters | Yes |
| GET | `/api/v1/events/statistics` | Get event statistics | Yes |
| GET | `/api/v1/events/stream/{stream_id}` | Get event stream | Yes |
| POST | `/api/v1/events/replay` | Replay events | Yes |
| GET | `/api/v1/events/projections/{entity_type}/{entity_id}` | Get entity projection | Yes |
| POST | `/api/v1/events/subscriptions` | Create subscription | Yes |
| GET | `/api/v1/events/subscriptions` | List subscriptions | Yes |
| DELETE | `/api/v1/events/subscriptions/{subscription_id}` | Delete subscription | Yes |
| POST | `/api/v1/events/processors` | Register processor | Yes |
| GET | `/api/v1/events/processors` | List processors | Yes |
| PUT | `/api/v1/events/processors/{processor_id}/toggle` | Toggle processor | Yes |
| POST | `/api/v1/events/frontend` | Collect frontend event | No |
| POST | `/api/v1/events/frontend/batch` | Batch frontend events | No |
| GET | `/api/v1/events/frontend/health` | Frontend health | No |
| POST | `/webhooks/rudderstack` | RudderStack webhook | No |

---

## 8. Event Publishing Pattern

### Published Events

| Event Type | Subject | Trigger | Data |
|------------|---------|---------|------|
| `event.stored` | `events.service.event.created` | After event creation | `event_id`, `event_type`, `event_source`, `event_category`, `user_id`, `timestamp` |
| `event.processed.success` | `events.service.event.processed` | After successful processing | `event_id`, `event_type`, `processor_name`, `duration_ms`, `timestamp` |
| `event.processed.failed` | `events.service.event.failed` | After failed processing | `event_id`, `event_type`, `processor_name`, `error_message`, `retry_count`, `timestamp` |
| `event.replay.started` | `events.service.replay.started` | When replay starts | `events_count`, `stream_id`, `target_service`, `dry_run`, `timestamp` |
| `event.subscription.created` | - | After subscription creation | `subscription_id`, `subscriber_name`, `event_types`, `enabled`, `timestamp` |
| `event.projection.created` | - | After projection creation | `projection_id`, `projection_name`, `entity_id`, `entity_type`, `version`, `timestamp` |

### Event Publishing (inline in `event_service.py`)

```python
async def create_event(self, request: EventCreateRequest) -> EventResponse:
    # ... create logic ...
    stored_event = await self.repository.save_event(event)

    # Publish event.stored event
    if self.event_bus:
        try:
            nats_event = NATSEvent(
                event_type="event.stored",
                source="event_service",
                data={
                    "event_id": stored_event.event_id,
                    "event_type": stored_event.event_type,
                    "event_source": stored_event.event_source.value,
                    "event_category": stored_event.event_category.value,
                    "user_id": stored_event.user_id,
                    "timestamp": stored_event.timestamp.isoformat()
                }
            )
            await self.event_bus.publish_event(nats_event)
        except Exception as e:
            logger.error(f"Failed to publish event.stored event: {e}")

    return EventResponse(...)
```

### EventPublisher Class (`events/publishers.py`)

```python
class EventPublisher:
    """Publisher for event service events"""

    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def publish_event_created(
        self,
        event_id: str,
        event_type: str,
        event_source: str,
        event_category: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self.event_bus:
            logger.warning("Event bus not available")
            return False

        try:
            event = EventCreatedEvent(...)
            await self.event_bus.publish(
                subject="events.service.event.created",
                data=event.model_dump(),
                headers={"event_id": event_id, "source": "event_service"}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish event.created: {e}")
            return False
```

### Event Payload Models (`events/models.py`)

```python
class EventCreatedEvent(BaseModel):
    event_id: str
    event_type: str
    event_source: str
    event_category: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = {}

class EventProcessedEvent(BaseModel):
    event_id: str
    processor_name: str
    status: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = None
    result: Optional[Dict[str, Any]] = None

class EventFailedEvent(BaseModel):
    event_id: str
    processor_name: str
    error_message: str
    error_type: str
    retry_count: int = 0
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    will_retry: bool = False
```

### Stream Configuration

```python
class EventStreamConfig:
    STREAM_NAME = "event-stream"
    SUBJECTS = ["event.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "event"
```

---

## 9. Event Subscription Pattern

### Events Subscribed (via NATS)

| Subject Pattern | Handler | Action |
|-----------------|---------|--------|
| `events.backend.>` | `backend_event_handler` | Store backend events |

### Event Handlers (`events/handlers.py`)

```python
class EventHandlers:
    """Event handlers for the event service"""

    def __init__(self, event_service=None):
        self.event_service = event_service

    async def handle_event_created(self, event_data: Dict[str, Any]) -> bool:
        """Handle event.created events from other services"""
        try:
            event_id = event_data.get("event_id")
            event_type = event_data.get("event_type")
            logger.info(f"Handling event.created: event_id={event_id}, type={event_type}")
            return True
        except Exception as e:
            logger.error(f"Error handling event.created: {e}")
            return False

    async def handle_event_processed(self, event_data: Dict[str, Any]) -> bool:
        """Handle event.processed events"""
        # Update processing status, metrics, etc.
        return True

    async def handle_event_failed(self, event_data: Dict[str, Any]) -> bool:
        """Handle event.failed events"""
        # Handle failure (alert, retry logic, DLQ)
        return True

    async def handle_service_event(self, event_data: Dict[str, Any]) -> bool:
        """Generic handler for service events"""
        event_type = event_data.get("event_type")
        if "created" in event_type:
            return await self.handle_event_created(event_data)
        elif "processed" in event_type:
            return await self.handle_event_processed(event_data)
        elif "failed" in event_type:
            return await self.handle_event_failed(event_data)
        return True
```

### NATS Subscription (in `main.py`)

```python
async def subscribe_to_nats_events():
    """Subscribe to NATS events"""
    if not nats_client or not js:
        return

    async def backend_event_handler(msg):
        try:
            data = json.loads(msg.data.decode())
            if event_service:
                await event_service.create_event_from_nats(data)
            await msg.ack()
        except Exception as e:
            print(f"Error processing NATS event: {e}")
            await msg.nak()

    await js.subscribe(
        "events.backend.>",
        cb=backend_event_handler,
        durable="event-service",
        manual_ack=True
    )
```

### Internal Subscription System

```python
async def create_subscription(self, subscription: EventSubscription) -> EventSubscription:
    """Create event subscription"""
    await self.repository.save_subscription(subscription)
    self.subscriptions[subscription.subscription_id] = subscription

    # Publish event
    if self.event_bus:
        nats_event = NATSEvent(
            event_type="event.subscription.created",
            source="event_service",
            data={
                "subscription_id": subscription.subscription_id,
                "subscriber_name": subscription.subscriber_name,
                "event_types": subscription.event_types,
                # ...
            }
        )
        await self.event_bus.publish_event(nats_event)

    return subscription
```

---

## 10. Service Discovery Pattern

### Consul Registration (`routes_registry.py`)

```python
SERVICE_ROUTES = [
    {"path": "/", "methods": ["GET"], "auth_required": False, "description": "Root health check"},
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Service health check"},
    {"path": "/api/v1/events/create", "methods": ["POST"], "auth_required": True, "description": "Create single event"},
    {"path": "/api/v1/events/batch", "methods": ["POST"], "auth_required": True, "description": "Create batch events"},
    {"path": "/api/v1/events/{event_id}", "methods": ["GET"], "auth_required": True, "description": "Get single event by ID"},
    {"path": "/api/v1/events/query", "methods": ["POST"], "auth_required": True, "description": "Query events with filters"},
    {"path": "/api/v1/events/statistics", "methods": ["GET"], "auth_required": True, "description": "Get event statistics"},
    {"path": "/api/v1/events/stream/{stream_id}", "methods": ["GET"], "auth_required": True, "description": "Get event stream"},
    {"path": "/api/v1/events/replay", "methods": ["POST"], "auth_required": True, "description": "Replay events"},
    {"path": "/api/v1/events/projections/{entity_type}/{entity_id}", "methods": ["GET"], "auth_required": True, "description": "Get entity projection"},
    {"path": "/api/v1/events/subscriptions", "methods": ["GET", "POST"], "auth_required": True, "description": "List/create event subscriptions"},
    {"path": "/api/v1/events/subscriptions/{subscription_id}", "methods": ["DELETE"], "auth_required": True, "description": "Delete event subscription"},
    {"path": "/api/v1/events/processors", "methods": ["GET", "POST"], "auth_required": True, "description": "List/register event processors"},
    {"path": "/api/v1/events/processors/{processor_id}/toggle", "methods": ["PUT"], "auth_required": True, "description": "Toggle event processor"},
    {"path": "/api/v1/events/frontend", "methods": ["POST"], "auth_required": False, "description": "Collect single frontend event"},
    {"path": "/api/v1/events/frontend/batch", "methods": ["POST"], "auth_required": False, "description": "Collect batch frontend events"},
    {"path": "/api/v1/events/frontend/health", "methods": ["GET"], "auth_required": False, "description": "Frontend collection health check"},
    {"path": "/webhooks/rudderstack", "methods": ["POST"], "auth_required": False, "description": "RudderStack webhook endpoint"},
]

SERVICE_METADATA = {
    "service_name": "event_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "event-management", "event-sourcing"],
    "capabilities": [
        "event_creation",
        "event_query",
        "event_streaming",
        "event_replay",
        "event_subscriptions",
        "event_processors",
        "frontend_collection",
        "rudderstack_integration"
    ]
}
```

### Consul Metadata Generation

```python
def get_routes_for_consul() -> Dict[str, Any]:
    """Generate compact route metadata for Consul (512 char limit)"""
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/events",
        "health": ",".join(health_routes),
        "events": "|".join(event_routes[:15]),
        "frontend": ",".join(frontend_routes),
        "webhooks": ",".join(webhook_routes),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }
```

### Consul Registration in Lifespan

```python
if config.consul_enabled:
    try:
        route_meta = get_routes_for_consul()
        consul_meta = {
            'version': SERVICE_METADATA['version'],
            'capabilities': ','.join(SERVICE_METADATA['capabilities']),
            **route_meta
        }
        consul_registry = ConsulRegistry(
            service_name=SERVICE_METADATA['service_name'],
            service_port=config.service_port,
            consul_host=config.consul_host,
            consul_port=config.consul_port,
            tags=SERVICE_METADATA['tags'],
            meta=consul_meta,
            health_check_type='http'
        )
        consul_registry.register()
        logger.info(f"Service registered with Consul: {route_meta.get('route_count')} routes")
    except Exception as e:
        logger.warning(f"Failed to register with Consul: {e}")
```

---

## 11. Database Access Pattern

### Repository Pattern (`event_repository.py`)

```python
class EventRepository:
    """Event Repository - using PostgresClient via gRPC"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("event_service")

        # Service discovery for PostgreSQL
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        self.db = AsyncPostgresClient(host=host, port=port, user_id="event_service")
        self.schema = "event"
        self.events_table = "events"
        # ...
```

### Schema: `event`

### Tables

| Table | Purpose |
|-------|---------|
| `event.events` | Main event storage |
| `event.event_streams` | Event stream metadata |
| `event.event_projections` | Entity state projections |
| `event.event_processors` | Processor configurations |
| `event.event_subscriptions` | Event subscription configurations |
| `event.processing_results` | Processing result tracking |

### Key Database Operations

```python
async def save_event(self, event: Event) -> Event:
    """Save event"""
    event_dict = {
        'event_id': event.event_id,
        'event_type': event.event_type,
        'event_source': event.event_source.value,
        'event_category': event.event_category.value,
        'user_id': event.user_id,
        'data': event.data or {},  # Direct dict, not json.dumps()
        # ...
    }
    async with self.db:
        count = await self.db.insert_into(self.events_table, [event_dict], schema=self.schema)
    return event

async def query_events(self, user_id, event_type, ..., limit=100, offset=0) -> Tuple[List[Event], int]:
    """Query events with filters"""
    conditions = []
    params = []
    # Build dynamic WHERE clause
    # ...
    async with self.db:
        count_result = await self.db.query_row(count_query, params, schema=self.schema)
        results = await self.db.query(query, params, schema=self.schema)
    return events, total_count

async def get_event(self, event_id: str) -> Optional[Event]:
    """Get single event by ID"""
    query = f'SELECT * FROM {self.schema}.{self.events_table} WHERE event_id = $1'
    async with self.db:
        result = await self.db.query_row(query, [event_id], schema=self.schema)
    return self._row_to_event(result) if result else None
```

### Row to Model Conversion

```python
def _row_to_event(self, row: Dict) -> Event:
    """Convert database row to Event model"""
    # Handle JSONB fields
    data = row.get('data')
    if isinstance(data, str):
        data = json.loads(data)
    elif not isinstance(data, dict):
        data = {}
    # ... similar for metadata, context, properties

    return Event(
        event_id=row['event_id'],
        event_type=row['event_type'],
        event_source=EventSource(row['event_source']),
        event_category=EventCategory(row['event_category']),
        # ...
    )
```

---

## 12. Client SDK Pattern

### EventServiceClient (`client.py`)

```python
class EventServiceClient:
    """Event Service HTTP client"""

    def __init__(self, base_url: str = None):
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("event_service")
            except Exception as e:
                logger.warning(f"Service discovery failed: {e}")
                import os
                self.base_url = os.getenv("EVENT_SERVICE_URL", "http://localhost:8230")

        self.client = httpx.AsyncClient(timeout=30.0)
```

### Async Context Manager

```python
async def close(self):
    """Close HTTP client"""
    await self.client.aclose()

async def __aenter__(self):
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.close()
```

### Client Methods

| Method | Endpoint | Description |
|--------|----------|-------------|
| `create_event()` | POST `/api/events/create` | Create single event |
| `create_batch_events()` | POST `/api/events/batch` | Create multiple events |
| `get_event()` | GET `/api/events/{event_id}` | Get event by ID |
| `query_events()` | POST `/api/events/query` | Query with filters |
| `get_entity_projection()` | GET `/api/events/projections/{entity_type}/{entity_id}` | Get entity projection |
| `create_subscription()` | POST `/api/events/subscriptions` | Create subscription |
| `list_subscriptions()` | GET `/api/events/subscriptions` | List subscriptions |
| `delete_subscription()` | DELETE `/api/events/subscriptions/{id}` | Delete subscription |
| `replay_events()` | POST `/api/events/replay` | Replay historical events |
| `create_processor()` | POST `/api/events/processors` | Register processor |
| `list_processors()` | GET `/api/events/processors` | List processors |
| `toggle_processor()` | PUT `/api/events/processors/{id}/toggle` | Toggle processor |
| `get_event_statistics()` | GET `/api/events/statistics` | Get statistics |
| `health_check()` | GET `/health` | Health check |

### Usage Example

```python
async with EventServiceClient() as client:
    # Create event
    event = await client.create_event(
        event_type="file.uploaded",
        entity_type="file",
        entity_id="file123",
        user_id="user456",
        data={"filename": "photo.jpg", "size": 1024000}
    )

    # Query events
    result = await client.query_events(
        event_types=["file.uploaded", "file.deleted"],
        user_id="user123",
        limit=50
    )
    for event in result['events']:
        print(f"{event['event_type']}: {event['entity_id']}")

    # Get projection
    projection = await client.get_entity_projection("album", "album123")
```

---

## Data Models Reference

### Event Enums

```python
class EventSource(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    SYSTEM = "system"
    IOT_DEVICE = "iot_device"
    EXTERNAL_API = "external_api"
    SCHEDULED = "scheduled"

class EventCategory(str, Enum):
    # User behavior
    USER_ACTION = "user_action"
    PAGE_VIEW = "page_view"
    FORM_SUBMIT = "form_submit"
    CLICK = "click"
    # Business events
    USER_LIFECYCLE = "user_lifecycle"
    PAYMENT = "payment"
    ORDER = "order"
    TASK = "task"
    # System events
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"
    # IoT events
    DEVICE = "device"
    DEVICE_STATUS = "device_status"
    TELEMETRY = "telemetry"
    COMMAND = "command"
    ALERT = "alert"

class EventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ARCHIVED = "archived"

class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"
```

### Core Event Model

```python
class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    event_source: EventSource
    event_category: EventCategory
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    organization_id: Optional[str] = None
    device_id: Optional[str] = None
    correlation_id: Optional[str] = None
    data: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    context: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    status: EventStatus = EventStatus.PENDING
    processed_at: Optional[datetime] = None
    processors: List[str] = []
    error_message: Optional[str] = None
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    schema_version: str = "1.0.0"
```

---

## Background Processing

### Pending Events Processing Loop

```python
async def process_pending_events(batch_size: int = 100):
    """Process pending events in background"""
    processing_interval = int(config.get("processing_interval", 5))

    while True:
        try:
            if event_service:
                events = await event_service.get_unprocessed_events(limit=batch_size)
                for event in events:
                    try:
                        await event_service.process_event(event)
                    except Exception as e:
                        print(f"Error processing event {event.event_id}: {e}")
            await asyncio.sleep(processing_interval)
        except Exception as e:
            print(f"Error in event processing loop: {e}")
            await asyncio.sleep(processing_interval)
```

### Event Processing Queue

```python
class EventService:
    def __init__(self, ...):
        self.processing_queue = asyncio.Queue()
        self.is_processing = False

    async def _process_event_queue(self):
        """Process event queue"""
        self.is_processing = True
        while self.is_processing:
            try:
                event = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
```

---

## Compliance Checklist

- [x] `main.py` with lifespan management
- [x] `event_service.py` with business logic
- [x] `event_repository.py` with PostgreSQL via gRPC
- [x] `models.py` with Pydantic models
- [x] `routes_registry.py` for Consul (SERVICE_ROUTES, SERVICE_METADATA)
- [x] `client.py` with EventServiceClient SDK
- [x] `events/models.py` for event payload models
- [x] `events/publishers.py` for NATS publish (EventPublisher)
- [x] `events/handlers.py` for NATS subscriptions (EventHandlers)
- [x] Health check endpoints (`/health`, `/api/v1/events/frontend/health`)
- [x] ConfigManager usage for configuration
- [x] Service discovery pattern
- [x] Structured logging (setup_service_logger)
- [x] Background processing (process_pending_events)
- [x] Pagination support (limit, offset, has_more)
- [x] Error handling with HTTPException

---

**Version**: 1.0.0
**Last Updated**: 2025-12-30
**Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md`
