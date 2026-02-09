# Event Service - Design Document

## Design Overview

**Service Name**: event_service
**Port**: 8208
**Version**: 1.0.0
**Protocol**: HTTP REST API + NATS Event Publishing
**Last Updated**: 2025-12-30

### Design Principles
1. **Unified Event Management**: Central hub for all platform events from frontend, backend, and IoT sources
2. **Event Sourcing Support**: Full event stream management with versioning and replay capabilities
3. **Multi-Source Integration**: RudderStack, NATS, and direct API event ingestion
4. **Projection-Based Read Models**: Materialized views computed from event streams
5. **Extensible Processing**: Pluggable event processors and subscriptions
6. **High Performance**: Batch processing and async operations for throughput

---

## Architecture Overview

### High-Level Architecture

```
+-------------------------------------------------------------------------+
|                        External Clients                                  |
|   (Frontend Apps, Backend Services, IoT Devices, RudderStack, Analytics) |
+-----------------------------------+-------------------------------------+
                                    | HTTP REST API
                                    | (via API Gateway - JWT validation)
                                    v
+-------------------------------------------------------------------------+
|                     Event Service (Port 8208)                            |
|                                                                          |
|  +--------------------------------------------------------------------+ |
|  |                 FastAPI HTTP Layer (main.py)                        | |
|  |  - Request validation (Pydantic models)                            | |
|  |  - Response formatting                                              | |
|  |  - Error handling & exception handlers                              | |
|  |  - Health checks (/health)                                          | |
|  |  - Lifecycle management (startup/shutdown)                          | |
|  |  - Consul registration with route metadata                          | |
|  |  - Background task management                                       | |
|  +-------------------------------+------------------------------------+ |
|                                  |                                      |
|  +-------------------------------v------------------------------------+ |
|  |              Service Layer (event_service.py)                       | |
|  |  - Event creation and storage                                       | |
|  |  - Event querying with complex filters                              | |
|  |  - Event stream management                                          | |
|  |  - Event replay functionality                                       | |
|  |  - Projection creation and updates                                  | |
|  |  - Subscription management                                          | |
|  |  - Processor orchestration                                          | |
|  |  - Statistics aggregation                                           | |
|  +-------------------------------+------------------------------------+ |
|                                  |                                      |
|  +-------------------------------v------------------------------------+ |
|  |            Repository Layer (event_repository.py)                   | |
|  |  - PostgreSQL gRPC communication                                   | |
|  |  - Query construction (parameterized)                              | |
|  |  - Result parsing (proto JSONB to Python)                          | |
|  |  - CRUD operations for events                                      | |
|  |  - Statistics queries                                               | |
|  |  - Stream and projection persistence                               | |
|  +-------------------------------+------------------------------------+ |
|                                  |                                      |
|  +-------------------------------v------------------------------------+ |
|  |            Event Publishers (events/publishers.py)                  | |
|  |  - event.stored - When event is persisted                          | |
|  |  - event.processed.success - On successful processing              | |
|  |  - event.processed.failed - On processing failure                  | |
|  |  - event.subscription.created - New subscription registered        | |
|  |  - event.replay.started - Replay operation initiated               | |
|  +--------------------------------------------------------------------+ |
+-----------------------------------+-------------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
+-------------------+   +-------------------+   +-------------------+
|    PostgreSQL     |   |       NATS        |   |      Consul       |
|     (gRPC)        |   |    Event Bus      |   |   (Discovery)     |
|                   |   |                   |   |                   |
|  Schema:          |   |  Publishes:       |   |  Service:         |
|    event          |   |    event.>        |   |    event_service  |
|                   |   |                   |   |                   |
|  Tables:          |   |  Subjects:        |   |  Health:          |
|    events         |   |    event.stored   |   |    /health        |
|    event_streams  |   |    event.processed|   |                   |
|    event_         |   |    event.replay   |   |  Tags:            |
|      projections  |   |                   |   |    - event-mgmt   |
|    event_         |   |                   |   |    - sourcing     |
|      processors   |   |                   |   |                   |
|    event_         |   |                   |   |                   |
|      subscriptions|   |                   |   |                   |
|    processing_    |   |                   |   |                   |
|      results      |   |                   |   |                   |
+-------------------+   +-------------------+   +-------------------+
```

### Component Diagram

```
+-------------------------------------------------------------------------+
|                          Event Service                                   |
|                                                                          |
|  +-----------------+    +-----------------+    +---------------------+   |
|  |     Models      |--->|     Service     |--->|     Repository      |   |
|  |   (Pydantic)    |    |   (Business)    |    |      (Data)         |   |
|  |                 |    |                 |    |                     |   |
|  | - Event         |    | - EventService  |    | - EventRepository   |   |
|  | - EventStream   |    |                 |    |                     |   |
|  | - EventSource   |    | Methods:        |    | Methods:            |   |
|  | - EventCategory |    | - create_event()|    | - save_event()      |   |
|  | - EventStatus   |    | - query_events()|    | - get_event()       |   |
|  | - EventCreate   |    | - get_event()   |    | - query_events()    |   |
|  |   Request       |    | - replay_events |    | - update_event()    |   |
|  | - EventQuery    |    | - create_       |    | - get_unprocessed_  |   |
|  |   Request       |    |   projection()  |    |   events()          |   |
|  | - EventResponse |    | - create_       |    | - get_statistics()  |   |
|  | - EventList     |    |   subscription()|    | - save_projection() |   |
|  |   Response      |    | - register_     |    | - save_processor()  |   |
|  | - EventStats    |    |   processor()   |    | - save_subscription |   |
|  | - EventProjectn |    | - get_          |    | - save_processing_  |   |
|  | - EventProcessor|    |   statistics()  |    |   result()          |   |
|  | - EventSubscrptn|    |                 |    |                     |   |
|  | - RudderStack   |    |                 |    |                     |   |
|  |   Event         |    |                 |    |                     |   |
|  +-----------------+    +-----------------+    +---------------------+   |
|          ^                       ^                       ^               |
|          |                       |                       |               |
|  +-------+-----------------------------------------------+-------------+ |
|  |                   FastAPI Main (main.py)                            | |
|  |  - Dependency Injection (get_event_service)                        | |
|  |  - Route Handlers (18+ endpoints)                                   | |
|  |  - Exception Handlers                                               | |
|  |  - Lifespan Management                                              | |
|  |  - Background Tasks (process_pending_events)                        | |
|  +------------------------------+--------------------------------------+ |
|                                 |                                        |
|  +------------------------------v--------------------------------------+ |
|  |                    Event Publishers                                 | |
|  |               (events/publishers.py)                                | |
|  |                                                                     | |
|  |  - EventPublisher class                                            | |
|  |  - publish_event_created() - Event stored notification             | |
|  |  - publish_event_processed() - Processing success                  | |
|  |  - publish_event_failed() - Processing failure                     | |
|  |  - publish_replay_started() - Replay initiated                     | |
|  |  - publish_replay_completed() - Replay finished                    | |
|  +---------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (18+ endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration with route metadata
- NATS event bus integration
- Background task management for event processing

**Key Endpoints**:
```python
# Health Checks
GET /health                                    # Basic health check

# Event Management
POST /api/v1/events/create                     # Create single event
POST /api/v1/events/batch                      # Create batch events
GET  /api/v1/events/{event_id}                 # Get single event by ID
POST /api/v1/events/query                      # Query events with filters
GET  /api/v1/events/statistics                 # Get event statistics

# Event Streams & Replay
GET  /api/v1/events/stream/{stream_id}         # Get event stream
POST /api/v1/events/replay                     # Replay events

# Event Projections
GET  /api/v1/events/projections/{entity_type}/{entity_id}  # Get entity projection

# Event Subscriptions
GET  /api/v1/events/subscriptions              # List all subscriptions
POST /api/v1/events/subscriptions              # Create subscription
DELETE /api/v1/events/subscriptions/{id}       # Delete subscription

# Event Processors
GET  /api/v1/events/processors                 # List all processors
POST /api/v1/events/processors                 # Register processor
PUT  /api/v1/events/processors/{id}/toggle     # Toggle processor

# Frontend Event Collection (Public)
GET  /api/v1/events/frontend/health            # Frontend collection health
POST /api/v1/events/frontend                   # Collect single frontend event
POST /api/v1/events/frontend/batch             # Collect batch frontend events

# Webhooks
POST /webhooks/rudderstack                     # RudderStack webhook endpoint
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_service, event_repository, event_bus, consul_registry

    try:
        # Initialize centralized NATS event bus
        event_bus = await get_event_bus("event_service")
        logger.info("Centralized event bus initialized")

        # Initialize event service with repository
        event_service = EventService(event_bus=event_bus, config_manager=config_manager)
        event_repository = event_service.repository
        await event_repository.initialize()

        # Start background task for pending event processing
        asyncio.create_task(process_pending_events(batch_size))

        # Consul registration
        if config.consul_enabled:
            route_meta = get_routes_for_consul()
            consul_registry = ConsulRegistry(
                service_name="event_service",
                service_port=8208,
                tags=SERVICE_METADATA['tags'],
                meta=consul_meta,
                health_check_type='http'
            )
            consul_registry.register()

        yield

    finally:
        if event_bus:
            await event_bus.close()
        if consul_registry:
            consul_registry.deregister()
        if event_repository:
            await event_repository.close()
```

### 2. Service Layer (event_service.py)

**Class**: `EventService`

**Responsibilities**:
- Business logic execution
- Event creation from multiple sources (API, RudderStack, NATS)
- Event querying with complex filters
- Event stream management
- Event replay functionality
- Projection creation and maintenance
- Subscription management
- Processor orchestration
- Statistics aggregation
- Real-time processor triggering

**Key Methods**:
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

    # Event Creation
    async def create_event(self, request: EventCreateRequest) -> EventResponse:
        """
        Create event from API request.

        1. Create Event object from request
        2. Store event in repository
        3. Add to processing queue
        4. Trigger real-time processors
        5. Publish event.stored to NATS
        6. Return response
        """
        event = Event(
            event_type=request.event_type,
            event_source=request.event_source,
            event_category=request.event_category,
            user_id=request.user_id,
            data=request.data,
            metadata=request.metadata or {},
            context=request.context or {},
            timestamp=datetime.utcnow()
        )

        stored_event = await self.repository.save_event(event)
        await self.processing_queue.put(stored_event)
        asyncio.create_task(self._trigger_realtime_processors(stored_event))

        # Publish event.stored
        if self.event_bus:
            nats_event = NATSEvent(
                event_type="event.stored",
                source="event_service",
                data={
                    "event_id": stored_event.event_id,
                    "event_type": stored_event.event_type,
                    ...
                }
            )
            await self.event_bus.publish_event(nats_event)

        return EventResponse.from_event(stored_event)

    async def create_event_from_rudderstack(self, event: RudderStackEvent) -> EventResponse:
        """
        Create event from RudderStack webhook.

        1. Map RudderStack event fields to unified event format
        2. Categorize event based on type (page, track, etc.)
        3. Store and process
        """
        event = Event(
            event_type=rudderstack_event.event,
            event_source=EventSource.FRONTEND,
            event_category=self._categorize_rudderstack_event(rudderstack_event),
            user_id=rudderstack_event.userId or rudderstack_event.anonymousId,
            data={
                "properties": rudderstack_event.properties,
                "type": rudderstack_event.type,
            },
            context=rudderstack_event.context,
            metadata={...},
            timestamp=datetime.fromisoformat(rudderstack_event.timestamp)
        )
        return await self._store_and_process(event)

    async def create_event_from_nats(self, nats_event: Dict[str, Any]) -> EventResponse:
        """Create event from NATS message."""
        # Map NATS event to unified format
        event = Event(
            event_type=nats_event.get("type", "unknown"),
            event_source=EventSource.BACKEND,
            event_category=self._categorize_nats_event(nats_event),
            ...
        )
        return await self._store_and_process(event)

    # Event Querying
    async def query_events(self, request: EventQueryRequest) -> EventListResponse:
        """
        Query events with filters.

        Supports:
        - user_id, event_type, event_source, event_category
        - status, start_time, end_time
        - limit, offset pagination
        """
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
            events=[EventResponse.from_event(e) for e in events],
            total=total,
            limit=request.limit,
            offset=request.offset,
            has_more=(request.offset + request.limit) < total
        )

    # Event Streams
    async def get_event_stream(self, stream_id: str, from_version: Optional[int] = None) -> EventStream:
        """Get event stream by ID with optional version filter."""
        events = await self.repository.get_event_stream(stream_id, from_version)

        parts = stream_id.split(":")
        entity_type = parts[0] if parts else "unknown"
        entity_id = parts[1] if len(parts) > 1 else stream_id

        return EventStream(
            stream_id=stream_id,
            stream_type=entity_type,
            entity_id=entity_id,
            entity_type=entity_type,
            events=events,
            version=len(events)
        )

    # Event Replay
    async def replay_events(self, request: EventReplayRequest) -> Dict[str, Any]:
        """
        Replay events for reprocessing.

        Supports:
        - Replay by event_ids
        - Replay by stream_id
        - Replay by time range
        - Dry run mode
        - Target service specification
        """
        events = []

        if request.event_ids:
            for event_id in request.event_ids:
                event = await self.repository.get_event(event_id)
                if event:
                    events.append(event)
        elif request.stream_id:
            events = await self.repository.get_event_stream(request.stream_id)
        elif request.start_time and request.end_time:
            events = await self.repository.get_events_by_time_range(
                request.start_time, request.end_time
            )

        # Publish replay started
        if self.event_bus and not request.dry_run:
            await self.event_bus.publish_event(NATSEvent(
                event_type="event.replay.started",
                source="event_service",
                data={"events_count": len(events), ...}
            ))

        if request.dry_run:
            return {"dry_run": True, "events_count": len(events), ...}

        # Actual replay
        replayed, failed = 0, 0
        for event in events:
            try:
                await self._republish_event(event, request.target_service)
                replayed += 1
            except Exception as e:
                failed += 1

        return {"replayed": replayed, "failed": failed, "total": len(events)}

    # Projections
    async def create_projection(
        self,
        projection_name: str,
        entity_id: str,
        entity_type: str
    ) -> EventProjection:
        """
        Create event projection (materialized view from event stream).

        1. Create projection object
        2. Get event stream for entity
        3. Apply each event to build state
        4. Save projection
        5. Publish projection.created
        """
        projection = EventProjection(
            projection_name=projection_name,
            entity_id=entity_id,
            entity_type=entity_type
        )

        stream_id = f"{entity_type}:{entity_id}"
        events = await self.repository.get_event_stream(stream_id)

        for event in events:
            projection = await self._apply_event_to_projection(projection, event)

        await self.repository.save_projection(projection)
        self.projections[projection.projection_id] = projection

        return projection

    # Subscriptions
    async def create_subscription(self, subscription: EventSubscription) -> EventSubscription:
        """
        Create event subscription.

        Subscriptions filter events by:
        - event_types: List of event type patterns
        - event_sources: List of sources (frontend, backend, etc.)
        - event_categories: List of categories
        - callback_url: Webhook delivery endpoint
        """
        await self.repository.save_subscription(subscription)
        self.subscriptions[subscription.subscription_id] = subscription

        # Publish subscription.created
        if self.event_bus:
            await self.event_bus.publish_event(NATSEvent(
                event_type="event.subscription.created",
                source="event_service",
                data={...}
            ))

        return subscription

    # Processors
    async def register_processor(self, processor: EventProcessor) -> EventProcessor:
        """Register event processor with filter configuration."""
        await self.repository.save_processor(processor)
        self.processors[processor.processor_id] = processor
        return processor

    # Statistics
    async def get_statistics(self) -> EventStatistics:
        """Get event statistics with processing rates."""
        stats = await self.repository.get_statistics()

        total = stats.total_events
        if total > 0:
            stats.processing_rate = (stats.processed_events / total) * 100
            stats.error_rate = (stats.failed_events / total) * 100

        return stats

    # Event Categorization
    def _categorize_rudderstack_event(self, event: RudderStackEvent) -> EventCategory:
        """Categorize RudderStack events based on type."""
        event_type = event.type.lower()

        if event_type == "page":
            return EventCategory.PAGE_VIEW
        elif event_type == "track":
            if "form" in event.event.lower():
                return EventCategory.FORM_SUBMIT
            elif "click" in event.event.lower():
                return EventCategory.CLICK
            else:
                return EventCategory.USER_ACTION
        else:
            return EventCategory.USER_ACTION

    def _categorize_nats_event(self, event: Dict[str, Any]) -> EventCategory:
        """Categorize NATS events based on type."""
        event_type = event.get("type", "").lower()

        if "user" in event_type:
            return EventCategory.USER_LIFECYCLE
        elif "payment" in event_type:
            return EventCategory.PAYMENT
        elif "order" in event_type:
            return EventCategory.ORDER
        elif "task" in event_type:
            return EventCategory.TASK
        elif "device" in event_type:
            return EventCategory.DEVICE_STATUS
        else:
            return EventCategory.SYSTEM
```

### 3. Repository Layer (event_repository.py)

**Class**: `EventRepository`

**Responsibilities**:
- PostgreSQL CRUD operations via gRPC
- Query construction (parameterized for SQL injection prevention)
- Result parsing (JSONB to Python dicts)
- Statistics aggregation
- Stream, projection, processor, and subscription persistence

**Key Methods**:
```python
class EventRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("event_service")

        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )

        self.db = AsyncPostgresClient(host=host, port=port, user_id="event_service")
        self.schema = "event"
        self.events_table = "events"
        self.event_streams_table = "event_streams"
        self.event_projections_table = "event_projections"
        self.event_processors_table = "event_processors"
        self.event_subscriptions_table = "event_subscriptions"
        self.processing_results_table = "processing_results"

    async def save_event(self, event: Event) -> Event:
        """Insert event into database"""
        event_dict = {
            'event_id': event.event_id,
            'event_type': event.event_type,
            'event_source': event.event_source.value,
            'event_category': event.event_category.value,
            'user_id': event.user_id,
            'session_id': event.session_id,
            'organization_id': event.organization_id,
            'device_id': event.device_id,
            'correlation_id': event.correlation_id,
            'data': event.data or {},
            'metadata': event.metadata or {},
            'context': event.context or {},
            'properties': event.properties or {},
            'status': event.status.value,
            'processed_at': event.processed_at.isoformat() if event.processed_at else None,
            'processors': event.processors or [],
            'error_message': event.error_message,
            'retry_count': event.retry_count,
            'timestamp': event.timestamp.isoformat(),
            'created_at': event.created_at.isoformat(),
            'updated_at': event.updated_at.isoformat(),
            'version': event.version,
            'schema_version': event.schema_version
        }

        async with self.db:
            count = await self.db.insert_into(self.events_table, [event_dict], schema=self.schema)

        if count and count > 0:
            return event
        raise Exception("Failed to save event")

    async def query_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        event_source: Optional[EventSource] = None,
        event_category: Optional[EventCategory] = None,
        status: Optional[EventStatus] = None,
        correlation_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Event], int]:
        """Query events with filters"""
        conditions = []
        params = []
        param_count = 0

        if user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)

        # ... additional filter conditions ...

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Get total count
        count_query = f'SELECT COUNT(*) as count FROM {self.schema}.{self.events_table} WHERE {where_clause}'
        async with self.db:
            count_result = await self.db.query_row(count_query, params, schema=self.schema)
        total_count = int(count_result.get("count", 0)) if count_result else 0

        # Get events
        query = f'''
            SELECT * FROM {self.schema}.{self.events_table}
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
        '''

        async with self.db:
            results = await self.db.query(query, params, schema=self.schema)

        events = [self._row_to_event(row) for row in results] if results else []
        return events, total_count

    async def get_statistics(self, user_id: Optional[str] = None) -> EventStatistics:
        """Get event statistics"""
        query = f'''
            SELECT
                COUNT(*) as total_events,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_events,
                COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed_events,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_events,
                COUNT(CASE WHEN timestamp >= CURRENT_DATE THEN 1 END) as events_today,
                COUNT(CASE WHEN timestamp >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as events_week,
                COUNT(CASE WHEN timestamp >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as events_month
            FROM {self.schema}.{self.events_table}
            WHERE {where_clause}
        '''

        async with self.db:
            result = await self.db.query_row(query, params, schema=self.schema)

        return EventStatistics(
            total_events=int(result.get("total_events", 0)),
            pending_events=int(result.get("pending_events", 0)),
            processed_events=int(result.get("processed_events", 0)),
            failed_events=int(result.get("failed_events", 0)),
            events_today=int(result.get("events_today", 0)),
            events_this_week=int(result.get("events_week", 0)),
            events_this_month=int(result.get("events_month", 0)),
            ...
        )

    async def get_unprocessed_events(self, limit: int = 100) -> List[Event]:
        """Get pending events for processing"""
        query = f'''
            SELECT * FROM {self.schema}.{self.events_table}
            WHERE status = $1
            ORDER BY timestamp ASC
            LIMIT {limit}
        '''

        async with self.db:
            results = await self.db.query(query, [EventStatus.PENDING.value], schema=self.schema)

        return [self._row_to_event(row) for row in results] if results else []

    def _row_to_event(self, row: Dict) -> Event:
        """Convert database row to Event model"""
        # Handle JSONB fields
        data = row.get('data')
        if isinstance(data, str):
            data = json.loads(data)
        elif not isinstance(data, dict):
            data = {}

        # ... similar handling for metadata, context, properties ...

        return Event(
            event_id=row['event_id'],
            event_type=row['event_type'],
            event_source=EventSource(row['event_source']),
            event_category=EventCategory(row['event_category']),
            user_id=row.get('user_id'),
            session_id=row.get('session_id'),
            data=data,
            metadata=metadata,
            status=EventStatus(row['status']),
            timestamp=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')),
            ...
        )
```

---

## Database Schema Design

### PostgreSQL Schema: `event`

#### Table: event.events

```sql
-- Create event schema
CREATE SCHEMA IF NOT EXISTS event;

-- Events table
CREATE TABLE event.events (
    event_id VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    event_source VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,

    -- Related IDs (no FK constraints - cross-service references)
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    organization_id VARCHAR(255),
    device_id VARCHAR(255),
    correlation_id VARCHAR(255),

    -- Data (JSONB fields with defaults)
    data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    properties JSONB DEFAULT '{}',

    -- Processing info
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    processors TEXT[],
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Version
    version VARCHAR(20) DEFAULT '1.0.0',
    schema_version VARCHAR(20) DEFAULT '1.0.0'
);
```

#### Table: event.event_streams

```sql
-- Event streams table (Event Sourcing)
CREATE TABLE event.event_streams (
    stream_id VARCHAR(255) PRIMARY KEY,
    stream_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,

    events JSONB DEFAULT '[]',
    version INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(entity_type, entity_id)
);
```

#### Table: event.event_projections

```sql
-- Event projections table (Read Models)
CREATE TABLE event.event_projections (
    projection_id VARCHAR(255) PRIMARY KEY,
    projection_name VARCHAR(255) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,

    state JSONB DEFAULT '{}',
    version INTEGER DEFAULT 0,
    last_event_id VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(entity_type, entity_id, projection_name)
);
```

#### Table: event.event_processors

```sql
-- Event processors table
CREATE TABLE event.event_processors (
    processor_id VARCHAR(255) PRIMARY KEY,
    processor_name VARCHAR(255) NOT NULL UNIQUE,
    processor_type VARCHAR(100) NOT NULL,

    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,

    filters JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',

    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table: event.event_subscriptions

```sql
-- Event subscriptions table
CREATE TABLE event.event_subscriptions (
    subscription_id VARCHAR(255) PRIMARY KEY,
    subscriber_name VARCHAR(255) NOT NULL UNIQUE,
    subscriber_type VARCHAR(100) NOT NULL,

    event_types TEXT[],
    event_sources TEXT[],
    event_categories TEXT[],

    callback_url TEXT,
    webhook_secret TEXT,

    enabled BOOLEAN DEFAULT TRUE,
    retry_policy JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table: event.processing_results

```sql
-- Processing results table
CREATE TABLE event.processing_results (
    result_id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL,
    processor_name VARCHAR(255) NOT NULL,

    status VARCHAR(20) NOT NULL,
    message TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms INTEGER
);
```

### Index Strategy

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| `event_id` (PK) | event_id | B-tree | Fast lookup by ID |
| `idx_events_user_id` | user_id | B-tree | User event queries |
| `idx_events_device_id` | device_id | B-tree | Device filtering |
| `idx_events_organization_id` | organization_id | B-tree | Organization filtering |
| `idx_events_session_id` | session_id | B-tree | Session tracking |
| `idx_events_correlation_id` | correlation_id | B-tree | Event correlation |
| `idx_events_type` | event_type | B-tree | Event type filtering |
| `idx_events_source` | event_source | B-tree | Source filtering |
| `idx_events_category` | event_category | B-tree | Category filtering |
| `idx_events_status` | status | B-tree | Status filtering |
| `idx_events_timestamp` | timestamp DESC | B-tree | Time-based queries |
| `idx_events_created_at` | created_at DESC | B-tree | Creation time queries |
| `idx_events_data` | data | GIN | JSONB data queries |
| `idx_events_metadata` | metadata | GIN | JSONB metadata queries |
| `idx_events_user_type` | user_id, event_type | Composite | User + type queries |
| `idx_events_user_timestamp` | user_id, timestamp DESC | Composite | User activity timeline |
| `idx_events_type_status` | event_type, status | Composite | Type + status queries |
| `idx_events_source_category` | event_source, event_category | Composite | Source + category |

---

## API Design

### Event Creation

**POST /api/v1/events/create**
```json
// Request
{
  "event_type": "user.profile_updated",
  "event_source": "backend",
  "event_category": "user_lifecycle",
  "user_id": "user_123",
  "data": {
    "changed_fields": ["name", "email"],
    "old_values": {...},
    "new_values": {...}
  },
  "metadata": {
    "ip_address": "192.168.1.1",
    "user_agent": "..."
  },
  "context": {
    "request_id": "req_abc123"
  }
}

// Response (201 Created)
{
  "event_id": "evt_abc123",
  "event_type": "user.profile_updated",
  "event_source": "backend",
  "event_category": "user_lifecycle",
  "user_id": "user_123",
  "data": {...},
  "status": "pending",
  "timestamp": "2025-12-30T12:00:00Z",
  "created_at": "2025-12-30T12:00:00Z"
}
```

### Event Query

**POST /api/v1/events/query**
```json
// Request
{
  "user_id": "user_123",
  "event_type": "user.profile_updated",
  "event_source": "backend",
  "event_category": "user_lifecycle",
  "status": "processed",
  "start_time": "2025-12-01T00:00:00Z",
  "end_time": "2025-12-31T23:59:59Z",
  "limit": 100,
  "offset": 0
}

// Response (200 OK)
{
  "events": [
    {
      "event_id": "evt_abc123",
      "event_type": "user.profile_updated",
      "event_source": "backend",
      "event_category": "user_lifecycle",
      "user_id": "user_123",
      "data": {...},
      "status": "processed",
      "timestamp": "2025-12-30T12:00:00Z",
      "created_at": "2025-12-30T12:00:00Z"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0,
  "has_more": false
}
```

### Event Subscription

**POST /api/v1/events/subscriptions**
```json
// Request
{
  "subscriber_name": "analytics_service",
  "subscriber_type": "service",
  "event_types": ["user.*", "payment.*"],
  "event_sources": ["backend", "frontend"],
  "event_categories": ["user_lifecycle", "payment"],
  "callback_url": "https://analytics.example.com/webhook",
  "webhook_secret": "secret_key",
  "enabled": true,
  "retry_policy": {
    "max_retries": 3,
    "backoff_seconds": [1, 5, 30]
  }
}

// Response (201 Created)
{
  "subscription_id": "sub_abc123",
  "subscriber_name": "analytics_service",
  "subscriber_type": "service",
  "event_types": ["user.*", "payment.*"],
  "event_sources": ["backend", "frontend"],
  "event_categories": ["user_lifecycle", "payment"],
  "callback_url": "https://analytics.example.com/webhook",
  "enabled": true,
  "created_at": "2025-12-30T12:00:00Z",
  "updated_at": "2025-12-30T12:00:00Z"
}
```

### Event Replay

**POST /api/v1/events/replay**
```json
// Request
{
  "stream_id": "user:user_123",
  "event_ids": null,
  "start_time": "2025-12-01T00:00:00Z",
  "end_time": "2025-12-31T23:59:59Z",
  "target_service": "analytics_service",
  "dry_run": false
}

// Response (202 Accepted)
{
  "status": "replay_started",
  "message": "Event replay has been initiated",
  "dry_run": false
}
```

### Frontend Event Collection

**POST /api/v1/events/frontend**
```json
// Request
{
  "event_type": "button_click",
  "category": "user_interaction",
  "page_url": "https://app.example.com/dashboard",
  "user_id": "user_123",
  "session_id": "sess_abc",
  "data": {
    "button_id": "submit_form",
    "button_text": "Submit"
  },
  "metadata": {
    "device": "desktop",
    "browser": "Chrome"
  }
}

// Response (200 OK)
{
  "status": "accepted",
  "event_id": "evt_frontend_123",
  "message": "Event published to stream"
}
```

---

## Event-Driven Architecture

### Event Publishing

**NATS Subjects**:
```
event.stored                 # Published when event is persisted
event.processed.success      # Published on successful processing
event.processed.failed       # Published on processing failure
event.subscription.created   # Published when subscription is created
event.replay.started         # Published when replay is initiated
event.projection.created     # Published when projection is created
```

### Event Models (events/models.py)

```python
class EventEventType(str, Enum):
    """Events published by event_service."""
    EVENT_STORED = "event.stored"
    EVENT_PROCESSED_SUCCESS = "event.processed.success"
    EVENT_PROCESSED_FAILED = "event.processed.failed"
    SUBSCRIPTION_CREATED = "event.subscription.created"
    REPLAY_STARTED = "event.replay.started"


class EventStreamConfig:
    """Stream configuration for event_service"""
    STREAM_NAME = "event-stream"
    SUBJECTS = ["event.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "event"


class EventCreatedEvent(BaseModel):
    """Event published when a new event is created"""
    event_id: str
    event_type: str
    event_source: str
    event_category: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    timestamp: datetime
    data: Dict[str, Any] = {}


class EventProcessedEvent(BaseModel):
    """Event published when an event is successfully processed"""
    event_id: str
    processor_name: str
    status: str
    processed_at: datetime
    duration_ms: Optional[int] = None
    result: Optional[Dict[str, Any]] = None


class EventFailedEvent(BaseModel):
    """Event published when event processing fails"""
    event_id: str
    processor_name: str
    error_message: str
    error_type: str
    retry_count: int = 0
    failed_at: datetime
    will_retry: bool = False
```

### Event Flow Diagram

```
+------------------+  +------------------+  +------------------+
|    Frontend      |  |    Backend       |  |   IoT Devices    |
|    Apps          |  |    Services      |  |                  |
+--------+---------+  +--------+---------+  +--------+---------+
         |                     |                     |
         | /frontend           | /create             | NATS
         v                     v                     v
+-------------------------------------------------------------------------+
|                           Event Service                                  |
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  |                    Event Ingestion Layer                          |  |
|  |                                                                   |  |
|  |  - Frontend Event Collector (/api/v1/events/frontend)            |  |
|  |  - API Event Creator (/api/v1/events/create)                     |  |
|  |  - RudderStack Webhook (/webhooks/rudderstack)                   |  |
|  |  - NATS Event Subscriber (backend events)                        |  |
|  +--------------------------------+----------------------------------+  |
|                                   |                                     |
|                                   v                                     |
|  +-------------------------------------------------------------------+  |
|  |                    Event Processing Layer                         |  |
|  |                                                                   |  |
|  |  1. Normalize to unified Event model                             |  |
|  |  2. Categorize (source, category)                                |  |
|  |  3. Persist to PostgreSQL                                        |  |
|  |  4. Add to processing queue                                      |  |
|  |  5. Trigger real-time processors                                 |  |
|  |  6. Update projections                                           |  |
|  |  7. Deliver to subscriptions                                     |  |
|  +--------------------------------+----------------------------------+  |
|                                   |                                     |
|                                   v                                     |
|  +-------------------------------------------------------------------+  |
|  |                      NATS Publishing                              |  |
|  |                                                                   |  |
|  |  event.stored             -> All consumers                       |  |
|  |  event.processed.success  -> Monitoring, Analytics               |  |
|  |  event.processed.failed   -> Error tracking, Alerting            |  |
|  |  event.subscription.*     -> Subscription management             |  |
|  |  event.replay.*           -> Replay tracking                     |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------------+
|                           NATS Event Bus                                 |
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  |                    Stream: event-stream                           |  |
|  |                    Subjects: event.>                              |  |
|  |                                                                   |  |
|  |  Consumers:                                                       |  |
|  |  - audit_service (universal audit trail)                         |  |
|  |  - analytics_service (metrics and insights)                      |  |
|  |  - notification_service (user notifications)                     |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## Data Flow Diagrams

### 1. Event Creation Flow (API)

```
Client                    Service                  Repository              PostgreSQL
  |                          |                          |                      |
  |  POST /api/v1/events/create                         |                      |
  |  {event_type, data, ...} |                          |                      |
  |------------------------>|                          |                      |
  |                          |                          |                      |
  |                          |  Validate request        |                      |
  |                          |------+                   |                      |
  |                          |<-----+                   |                      |
  |                          |                          |                      |
  |                          |  Create Event object     |                      |
  |                          |  Generate UUID           |                      |
  |                          |  Set timestamp           |                      |
  |                          |------+                   |                      |
  |                          |<-----+                   |                      |
  |                          |                          |                      |
  |                          |  save_event()            |                      |
  |                          |------------------------->|                      |
  |                          |                          |  INSERT INTO         |
  |                          |                          |  event.events        |
  |                          |                          |--------------------->|
  |                          |                          |                      |
  |                          |                          |  RETURNING *         |
  |                          |                          |<---------------------|
  |                          |  Return stored event     |                      |
  |                          |<-------------------------|                      |
  |                          |                          |                      |
  |                          |  Add to processing_queue |                      |
  |                          |------+                   |                      |
  |                          |<-----+                   |                      |
  |                          |                          |                      |
  |                          |  Publish event.stored    |                      |
  |                          |  to NATS (async)         |                      |
  |                          |------+                   |                      |
  |                          |<-----+                   |                      |
  |                          |                          |                      |
  |  201 Created             |                          |                      |
  |  {event_id, status, ...} |                          |                      |
  |<-------------------------|                          |                      |
```

### 2. Frontend Event Collection Flow

```
Frontend App              Event Service            NATS JetStream
  |                          |                          |
  |  POST /api/v1/events/frontend                       |
  |  {event_type, page_url,  |                          |
  |   user_id, data, ...}    |                          |
  |------------------------->|                          |
  |                          |                          |
  |                          |  Extract client info     |
  |                          |  (IP, User-Agent, ...)   |
  |                          |------+                   |
  |                          |<-----+                   |
  |                          |                          |
  |                          |  Build NATS subject      |
  |                          |  events.frontend.        |
  |                          |    {category}.{type}     |
  |                          |------+                   |
  |                          |<-----+                   |
  |                          |                          |
  |                          |  Publish to JetStream    |
  |                          |------------------------->|
  |                          |                          |
  |                          |  ACK                     |
  |                          |<-------------------------|
  |                          |                          |
  |  200 OK                  |                          |
  |  {status: "accepted",    |                          |
  |   event_id: "..."}       |                          |
  |<-------------------------|                          |
```

### 3. Event Replay Flow

```
Admin                      Service                  Repository
  |                          |                          |
  |  POST /api/v1/events/replay                         |
  |  {stream_id, start_time, |                          |
  |   end_time, dry_run}     |                          |
  |------------------------->|                          |
  |                          |                          |
  |                          |  Query events by filter  |
  |                          |------------------------->|
  |                          |                          |
  |                          |  Return matching events  |
  |                          |<-------------------------|
  |                          |                          |
  |                          |  If dry_run:             |
  |                          |    Return event list     |
  |                          |------+                   |
  |                          |<-----+                   |
  |                          |                          |
  |  200 OK (dry_run)        |                          |
  |  {events_count: N,       |                          |
  |   events: [...]}         |                          |
  |<-------------------------|                          |
  |                          |                          |
  |                          |  If not dry_run:         |
  |                          |    Start background task |
  |                          |    For each event:       |
  |                          |      Republish to target |
  |                          |------+                   |
  |                          |<-----+                   |
  |                          |                          |
  |  202 Accepted            |                          |
  |  {status: "replay_started"}                         |
  |<-------------------------|                          |
```

### 4. Projection Update Flow

```
Event Created              Service                  Repository
  |                          |                          |
  |  Event stored to DB      |                          |
  |------------------------->|                          |
  |                          |                          |
  |                          |  _update_projections()   |
  |                          |------+                   |
  |                          |<-----+                   |
  |                          |                          |
  |                          |  Find related projections|
  |                          |  by entity_id            |
  |                          |------+                   |
  |                          |<-----+                   |
  |                          |                          |
  |                          |  For each projection:    |
  |                          |    Apply event to state  |
  |                          |    Increment version     |
  |                          |    Set last_event_id     |
  |                          |------+                   |
  |                          |<-----+                   |
  |                          |                          |
  |                          |  update_projection()     |
  |                          |------------------------->|
  |                          |                          |
  |                          |  Return updated          |
  |                          |<-------------------------|
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.11+ | Primary language |
| Framework | FastAPI | 0.104+ | HTTP API framework |
| Validation | Pydantic | 2.0+ | Data validation |
| Async Runtime | asyncio | - | Async/await concurrency |
| ASGI Server | uvicorn | 0.23+ | ASGI server |

### Data Storage

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Database | PostgreSQL | 15+ | Primary data store |
| DB Access | AsyncPostgresClient | gRPC | Database communication |
| Schema | `event` | - | Service schema |
| Tables | events, event_streams, event_projections, event_processors, event_subscriptions, processing_results | - | Data tables |

### Event-Driven

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Event Bus | NATS | 2.9+ | Event messaging |
| JetStream | NATS JetStream | - | Persistent event streaming |
| Stream | event-stream | - | Event storage stream |

### Service Discovery

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Registry | Consul | 1.15+ | Service discovery |
| Health Check | HTTP /health | - | Health monitoring |
| Metadata | Route registry | - | API documentation |

---

## Security Considerations

### Authentication
- **JWT Token Validation**: Handled by API Gateway
- **Public Endpoints**: /health, /api/v1/events/frontend/*, /webhooks/rudderstack
- **Protected Endpoints**: All other endpoints require authentication

### Authorization
- **Event Access**: Users can only query their own events (via user_id filter)
- **Admin Endpoints**: Processor and subscription management require admin role
- **Replay Operations**: Replay requires elevated permissions

### Data Protection
- **SQL Injection Prevention**: Parameterized queries via gRPC
- **Input Validation**: Pydantic models validate all inputs
- **Sensitive Data**: Event data may contain PII, handle appropriately
- **Webhook Security**: RudderStack webhook signature validation

### Webhook Security
```python
# RudderStack webhook signature validation
if config.RUDDERSTACK_WEBHOOK_SECRET:
    signature = request.headers.get("X-Signature")
    if not signature or signature != config.RUDDERSTACK_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid signature")
```

---

## Error Handling Strategy

### HTTP Status Codes

| Status | Condition | Example |
|--------|-----------|---------|
| 200 OK | Successful operation | Query returned results |
| 201 Created | New event created | Event stored successfully |
| 202 Accepted | Async operation started | Replay initiated |
| 400 Bad Request | Validation error | Invalid event_type |
| 401 Unauthorized | Missing/invalid token | No JWT provided |
| 404 Not Found | Resource not found | Event ID not found |
| 422 Validation Error | Field validation failed | Invalid date format |
| 500 Internal Error | Database error | PostgreSQL unavailable |
| 503 Service Unavailable | Service dependency down | NATS disconnected |

### Error Response Format
```json
{
  "detail": "Event not found: evt_abc123"
}
```

### Exception Handling
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
```

---

## Scalability Design

### Horizontal Scaling
- **Stateless Service**: No local state, can run multiple instances
- **Database Connection Pooling**: Managed by gRPC client
- **Load Balancing**: Via Consul service discovery

### Event Processing
- **Async Processing Queue**: In-memory queue for event processing
- **Background Tasks**: Periodic processing of pending events
- **Batch Processing**: Configurable batch size for throughput

### Database Optimization
- **Strategic Indexes**: On frequently queried columns
- **Composite Indexes**: For common query patterns
- **GIN Indexes**: For JSONB data and metadata queries
- **Pagination**: All list endpoints use LIMIT/OFFSET

### Caching Strategy (Future)
- **Statistics Cache**: Short TTL for aggregated stats
- **Projection Cache**: In-memory projections
- **Event Deduplication**: Prevent duplicate processing

---

## Integration Points

### NATS Event Bus
- **Connection**: Via centralized event bus (isa_common)
- **Publishing**: event.stored, event.processed.*, event.subscription.*, event.replay.*
- **Subscribing**: Backend events via events.backend.>

### PostgreSQL (gRPC)
- **Service Discovery**: Via Consul or environment variables
- **Connection**: AsyncPostgresClient with gRPC protocol
- **Schema**: Dedicated `event` schema

### Consul
- **Registration**: Service metadata and route information
- **Health Checks**: HTTP health endpoint
- **Discovery**: PostgreSQL and NATS service locations

### RudderStack
- **Webhook**: /webhooks/rudderstack endpoint
- **Authentication**: Signature validation
- **Event Mapping**: RudderStack format to unified event model

### Other Services
- **Account Service**: User context for events
- **Device Service**: Device context for IoT events
- **Organization Service**: Organization context
- **Audit Service**: Consumes all events for audit trail

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | HTTP port | 8208 |
| `SERVICE_NAME` | Service identifier | event_service |
| `LOG_LEVEL` | Logging level | INFO |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS connection URL | nats://isa-nats:4222 |
| `CONSUL_HOST` | Consul host | localhost |
| `CONSUL_PORT` | Consul port | 8500 |
| `CONSUL_ENABLED` | Enable Consul registration | true |
| `RUDDERSTACK_WEBHOOK_SECRET` | Webhook signature secret | - |
| `BATCH_SIZE` | Event processing batch size | 100 |
| `PROCESSING_INTERVAL` | Processing loop interval (seconds) | 5 |

### Health Check

```json
GET /health
{
  "status": "healthy",
  "service": "event_service",
  "version": "1.0.0",
  "timestamp": "2025-12-30T12:00:00Z"
}
```

### Consul Registration

```json
{
  "service_name": "event_service",
  "port": 8208,
  "tags": ["v1", "user-microservice", "event-management", "event-sourcing"],
  "meta": {
    "version": "1.0.0",
    "capabilities": "event_creation,event_query,event_streaming,event_replay,event_subscriptions,event_processors,frontend_collection,rudderstack_integration",
    "route_count": "18",
    "base_path": "/api/v1/events"
  },
  "health_check": {
    "type": "http",
    "path": "/health",
    "interval": "30s"
  }
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: event-service
  template:
    spec:
      containers:
      - name: event-service
        image: isa/event-service:latest
        ports:
        - containerPort: 8208
        env:
        - name: SERVICE_PORT
          value: "8208"
        - name: POSTGRES_HOST
          value: "isa-postgres-grpc"
        - name: NATS_URL
          value: "nats://isa-nats:4222"
        livenessProbe:
          httpGet:
            path: /health
            port: 8208
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8208
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation
- **TestDataFactory**: Zero hardcoded data generation

### Unit Testing
- **Pure Functions**: Event categorization, mapping
- **Model Validation**: Pydantic model tests
- **Service Methods**: Business logic tests

### Component Testing
- **Service Layer**: Business logic with mocked repository
- **Event Publishers**: NATS publishing tests
- **Projection Logic**: State computation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **NATS Publishing**: Event publishing tests
- **End-to-End Flows**: Event creation to processing

### API Testing
- **Endpoint Contracts**: All 18+ endpoints tested
- **Error Handling**: Validation, not found, server errors
- **Pagination**: Page boundaries, empty results

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability

---

**Document Version**: 1.0
**Last Updated**: 2025-12-30
**Maintained By**: Platform Engineering Team
**Related Documents**:
- Domain Context: docs/domain/event_service.md
- PRD: docs/prd/event_service.md
- Data Contract: tests/contracts/event_service/data_contract.py
- Logic Contract: tests/contracts/event_service/logic_contract.md
- System Contract: tests/contracts/event_service/system_contract.md
