# Event Service Logic Contract

**Business Rules and Specifications for Event Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for event service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Invariants](#invariants)
4. [Validation Rules](#validation-rules)
5. [Error Conditions](#error-conditions)
6. [Integration Contracts](#integration-contracts)
7. [Performance SLAs](#performance-slas)

---

## Business Rules

### Event Creation Rules

### BR-EVT-001: Event ID Generation
**Given**: Valid event creation request
**When**: Event is created via create_event
**Then**:
- Event ID automatically generated as UUID4
- Event ID is unique across all events
- Event ID format: UUID string (e.g., `550e8400-e29b-41d4-a716-446655440000`)

**Implementation**:
```python
event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
```

---

### BR-EVT-002: Required Fields on Creation
**Given**: Event creation request
**When**: EventCreateRequest is processed
**Then**:
- `event_type`: Required, non-empty string
- `event_source`: Optional, defaults to `EventSource.BACKEND`
- `event_category`: Optional, defaults to `EventCategory.USER_ACTION`
- `user_id`: Optional, can be None for system events
- `data`: Optional, defaults to empty dict `{}`

**Validation Rules**:
- `event_type`: Must be provided (required field)
- `event_source`: Must be valid EventSource enum value
- `event_category`: Must be valid EventCategory enum value

---

### BR-EVT-003: Default Values on Creation
**Given**: New event creation via create_event
**When**: Event is created
**Then**:
- `status` = `EventStatus.PENDING`
- `metadata` = `{}` if not provided
- `context` = `{}` if not provided
- `timestamp` = current UTC timestamp
- `created_at` = current UTC timestamp
- `updated_at` = current UTC timestamp
- `retry_count` = 0
- `processors` = [] (empty list)
- `version` = "1.0.0"
- `schema_version` = "1.0.0"

**Default Values**:
```python
{
    "status": EventStatus.PENDING,
    "metadata": {},
    "context": {},
    "timestamp": datetime.utcnow(),
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow(),
    "retry_count": 0,
    "processors": [],
    "version": "1.0.0",
    "schema_version": "1.0.0"
}
```

---

### BR-EVT-004: Event Stored Event Publishing
**Given**: Event successfully created and stored
**When**: create_event completes
**Then**:
- Event added to processing queue
- `event.stored` NATS event published (if event_bus available)
- Realtime processors triggered asynchronously

**Event Data**:
```json
{
  "event_id": "uuid",
  "event_type": "user.created",
  "event_source": "backend",
  "event_category": "user_lifecycle",
  "user_id": "user_123",
  "timestamp": "2025-12-30T10:00:00Z"
}
```

---

### BR-EVT-005: RudderStack Event Conversion
**Given**: RudderStack event received via webhook
**When**: create_event_from_rudderstack is called
**Then**:
- `event_source` set to `EventSource.FRONTEND`
- `event_category` determined by `_categorize_rudderstack_event`
- `user_id` set to `userId` or `anonymousId` (fallback)
- Original RudderStack metadata preserved
- Event stored and queued for processing

**Category Mapping**:
- `type="page"` -> `EventCategory.PAGE_VIEW`
- `type="track"` + event contains "form" -> `EventCategory.FORM_SUBMIT`
- `type="track"` + event contains "click" -> `EventCategory.CLICK`
- Default -> `EventCategory.USER_ACTION`

---

### BR-EVT-006: NATS Event Conversion
**Given**: NATS event received from backend service
**When**: create_event_from_nats is called
**Then**:
- `event_source` set to `EventSource.BACKEND`
- `event_category` determined by `_categorize_nats_event`
- `user_id` extracted from `data.user_id`
- Source service metadata preserved

**Category Mapping**:
- event_type contains "user" -> `EventCategory.USER_LIFECYCLE`
- event_type contains "payment" -> `EventCategory.PAYMENT`
- event_type contains "order" -> `EventCategory.ORDER`
- event_type contains "task" -> `EventCategory.TASK`
- event_type contains "device" -> `EventCategory.DEVICE_STATUS`
- Default -> `EventCategory.SYSTEM`

---

### Event Querying Rules

### BR-QRY-001: Query Filter Combinations
**Given**: Event query request with multiple filters
**When**: query_events is called
**Then**:
- All provided filters combined with AND logic
- Missing filters are ignored (not applied)
- Results ordered by timestamp DESC

**Available Filters**:
- `user_id`: Exact match
- `event_type`: Exact match
- `event_source`: Enum value match
- `event_category`: Enum value match
- `status`: Enum value match
- `correlation_id`: Exact match
- `start_time`: Timestamp >= filter
- `end_time`: Timestamp <= filter

---

### BR-QRY-002: Pagination Limits
**Given**: Event query with pagination
**When**: limit and offset specified
**Then**:
- `limit`: Minimum 1, Maximum 1000, Default 100
- `offset`: Minimum 0, Default 0
- Results include total count for pagination UI
- `has_more` calculated as `(offset + limit) < total`

**Validation** (EventQueryRequest):
```python
limit: int = Field(100, ge=1, le=1000)
offset: int = Field(0, ge=0)
```

---

### BR-QRY-003: Event Stream Retrieval
**Given**: Stream ID in format `{entity_type}:{entity_id}`
**When**: get_event_stream is called
**Then**:
- Stream ID parsed into entity_type and entity_id
- Events retrieved for that stream
- Stream version equals event count
- Optional `from_version` filters events

**Stream ID Format**:
```
user:user_123
order:order_456
device:device_789
```

---

### BR-QRY-004: User Events Query
**Given**: User ID
**When**: get_user_events is called
**Then**:
- Returns events for specific user
- Default limit: 100
- Ordered by timestamp (ASC for processing order)

---

### BR-QRY-005: Unprocessed Events Query
**Given**: Query for pending events
**When**: get_unprocessed_events is called
**Then**:
- Returns events with `status=PENDING`
- Ordered by timestamp ASC (oldest first)
- Default limit: 100

**SQL**:
```sql
WHERE status = 'pending' ORDER BY timestamp ASC
```

---

### Event Processing Rules

### BR-PRC-001: Processing Queue Mechanism
**Given**: Event created or queued for processing
**When**: Event enters processing queue
**Then**:
- Event added to asyncio.Queue
- Background task processes queue continuously
- 1 second timeout on queue get (allows graceful shutdown)

**Implementation**:
```python
await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
```

---

### BR-PRC-002: Processing Success Handling
**Given**: Event processed successfully by processor
**When**: mark_event_processed called with SUCCESS status
**Then**:
- `status` set to `EventStatus.PROCESSED`
- `processed_at` set to current timestamp
- Processor name added to `processors` list
- Processing result saved to database
- `event.processed.success` NATS event published

**Event Data**:
```json
{
  "event_id": "uuid",
  "event_type": "user.created",
  "processor_name": "event_processor",
  "duration_ms": 50,
  "timestamp": "2025-12-30T10:00:00Z"
}
```

---

### BR-PRC-003: Processing Failure Handling
**Given**: Event processing fails
**When**: mark_event_processed called with FAILED status
**Then**:
- `status` set to `EventStatus.FAILED`
- `error_message` set from result message
- `retry_count` incremented by 1
- Processor name added to `processors` list
- Processing result saved to database
- `event.processed.failed` NATS event published

**Event Data**:
```json
{
  "event_id": "uuid",
  "event_type": "user.created",
  "processor_name": "event_processor",
  "error_message": "Connection timeout",
  "retry_count": 1,
  "timestamp": "2025-12-30T10:00:00Z"
}
```

---

### BR-PRC-004: Retry Failed Events
**Given**: Failed events exist with retry_count < max_retries
**When**: retry_failed_events is called
**Then**:
- Events with `status=FAILED` and `retry_count < max_retries` retrieved
- Status reset to `PENDING`
- Events re-queued for processing
- Returns count of events queued for retry

**Default max_retries**: 3

---

### BR-PRC-005: Processor Matching
**Given**: Event being processed
**When**: Matching processors to event
**Then**:
- Only enabled processors considered
- Processor filters applied:
  - `event_type` filter: exact match
  - `event_source` filter: exact match
- All matching processors executed

---

### Event Replay Rules

### BR-RPL-001: Replay by Event IDs
**Given**: EventReplayRequest with event_ids list
**When**: replay_events is called
**Then**:
- Each event retrieved by ID
- Events republished to target service
- Failed replays counted and returned

---

### BR-RPL-002: Replay by Stream ID
**Given**: EventReplayRequest with stream_id
**When**: replay_events is called
**Then**:
- All events for stream retrieved
- Events replayed in order
- Stream ordering preserved

---

### BR-RPL-003: Replay by Time Range
**Given**: EventReplayRequest with start_time and end_time
**When**: replay_events is called
**Then**:
- Events within time range retrieved
- Events replayed in chronological order

---

### BR-RPL-004: Dry Run Mode
**Given**: EventReplayRequest with dry_run=true
**When**: replay_events is called
**Then**:
- Events identified but not replayed
- Returns event count and IDs
- No side effects (no republishing)
- No `event.replay.started` event published

**Response**:
```json
{
  "dry_run": true,
  "events_count": 10,
  "events": ["event_id_1", "event_id_2", ...]
}
```

---

### BR-RPL-005: Replay Started Event
**Given**: Replay initiated (not dry_run)
**When**: replay_events starts actual replay
**Then**:
- `event.replay.started` NATS event published
- Includes events_count, stream_id, target_service

**Event Data**:
```json
{
  "events_count": 10,
  "stream_id": "user:user_123",
  "target_service": "billing_service",
  "dry_run": false,
  "timestamp": "2025-12-30T10:00:00Z"
}
```

---

### Subscription Rules

### BR-SUB-001: Subscription Creation
**Given**: Valid EventSubscription
**When**: create_subscription is called
**Then**:
- Subscription ID auto-generated (UUID4)
- Subscription saved to database
- Subscription added to in-memory cache
- `event.subscription.created` NATS event published

---

### BR-SUB-002: Subscription Matching
**Given**: Event being processed
**When**: trigger_subscriptions is called
**Then**:
- Only enabled subscriptions considered
- Event must match ALL specified criteria:
  - `event_types`: event.event_type in list (or empty = all)
  - `event_sources`: event.event_source in list (or None = all)
  - `event_categories`: event.event_category in list (or None = all)

**Matching Logic**:
```python
if subscription.event_types and event.event_type not in subscription.event_types:
    return False
if subscription.event_sources and event.event_source not in subscription.event_sources:
    return False
if subscription.event_categories and event.event_category not in subscription.event_categories:
    return False
return True
```

---

### BR-SUB-003: Subscription Delivery
**Given**: Event matches subscription
**When**: Event is delivered to subscriber
**Then**:
- If `callback_url` specified: HTTP POST to URL (async)
- Delivery executed asynchronously (doesn't block processing)

---

### Projection Rules

### BR-PRJ-001: Projection Creation
**Given**: Projection creation request
**When**: create_projection is called
**Then**:
- Projection ID auto-generated (UUID4)
- Stream ID constructed as `{entity_type}:{entity_id}`
- All stream events applied to projection
- Projection saved to database and memory cache
- `event.projection.created` NATS event published

---

### BR-PRJ-002: Event Application to Projection
**Given**: Event being applied to projection
**When**: _apply_event_to_projection is called
**Then**:
- `state[event_type]` = event.data
- `version` incremented by 1
- `last_event_id` = event.event_id
- `updated_at` = current timestamp

**State Update**:
```python
projection.state[event.event_type] = event.data
projection.version += 1
projection.last_event_id = event.event_id
projection.updated_at = datetime.utcnow()
```

---

### BR-PRJ-003: Projection Caching
**Given**: Projection accessed
**When**: get_projection is called
**Then**:
- Check in-memory cache first
- If not in cache, load from database
- Cache hit is preferred for performance

---

## State Machines

### Event Lifecycle State Machine

```
                    +-----------+
                    |   NEW     |  Event created (transient)
                    +-----+-----+
                          |
                          v
                    +-----------+
    +-------------->|  PENDING  |  Queued for processing
    |               +-----+-----+
    |                     |
    |                     v
    |               +-----------+
    |               |PROCESSING |  Being processed (transient)
    |               +-----+-----+
    |                     |
    |         +-----------+-----------+
    |         |                       |
    |         v                       v
    |   +-----------+           +-----------+
    |   | PROCESSED |           |  FAILED   |
    |   +-----------+           +-----+-----+
    |                                 |
    |                                 | (retry)
    +---------------------------------+

From PROCESSED:
    |
    v
+-----------+
| ARCHIVED  |  (Future: archived to cold storage)
+-----------+
```

**States**:
- **NEW**: Transient state during creation (not persisted)
- **PENDING**: Event queued, awaiting processing (`status="pending"`)
- **PROCESSING**: Actively being processed (transient, not persisted)
- **PROCESSED**: Successfully processed (`status="processed"`)
- **FAILED**: Processing failed (`status="failed"`)
- **ARCHIVED**: Event archived to cold storage (`status="archived"`)

**Valid Transitions**:
- `NEW` -> `PENDING` (event creation)
- `PENDING` -> `PROCESSING` (processing starts)
- `PROCESSING` -> `PROCESSED` (processing succeeds)
- `PROCESSING` -> `FAILED` (processing fails)
- `FAILED` -> `PENDING` (retry triggered)
- `PROCESSED` -> `ARCHIVED` (archival, future feature)

**Transition Triggers**:
- `create_event()` -> NEW -> PENDING
- `_process_event()` -> PENDING -> PROCESSING
- `mark_event_processed(SUCCESS)` -> PROCESSING -> PROCESSED
- `mark_event_processed(FAILED)` -> PROCESSING -> FAILED
- `retry_failed_events()` -> FAILED -> PENDING

---

### ProcessingStatus Enum

```
+-----------+
|  SUCCESS  |  Processing completed successfully
+-----------+

+-----------+
|  FAILED   |  Processing failed with error
+-----------+

+-----------+
|  SKIPPED  |  Processing skipped (not applicable)
+-----------+

+-----------+
|   RETRY   |  Needs retry (transient failure)
+-----------+
```

**Usage**:
- `SUCCESS`: Processor completed without errors
- `FAILED`: Processor encountered an error
- `SKIPPED`: Processor determined event not applicable
- `RETRY`: Transient error, should retry

---

### Subscription Lifecycle

```
+-----------+
|  CREATED  |  Subscription created
+-----+-----+
      |
      v
+-----------+
|  ENABLED  |  Actively matching events
+-----+-----+
      |
      v
+-----------+
| DISABLED  |  Not matching events
+-----------+
```

**States**:
- **CREATED**: Subscription just created
- **ENABLED**: `enabled=True`, actively processing
- **DISABLED**: `enabled=False`, skipped in matching

**Transition Triggers**:
- `create_subscription()` -> CREATED -> ENABLED (if enabled=True)
- Toggle `enabled=False` -> DISABLED
- Toggle `enabled=True` -> ENABLED

---

## Invariants

### INV-001: Event Immutability After Creation
**Rule**: Core event data is immutable after creation

**Immutable Fields** (never change):
- `event_id`
- `event_type`
- `event_source`
- `event_category`
- `user_id`
- `data`
- `metadata`
- `context`
- `timestamp`
- `created_at`
- `version`
- `schema_version`

**Mutable Fields** (updated during processing):
- `status`
- `processed_at`
- `processors` (list)
- `error_message`
- `retry_count`
- `updated_at`

---

### INV-002: Stream Ordering Guarantee
**Rule**: Events in a stream maintain chronological order

- Events ordered by `timestamp` within a stream
- Stream version equals event count
- `from_version` parameter allows resuming from specific point
- Replay preserves original ordering

---

### INV-003: Event ID Uniqueness
**Rule**: Event IDs are globally unique

- UUID4 generation ensures uniqueness
- Database primary key constraint enforces
- No duplicate event_id can exist

---

### INV-004: Processing At-Least-Once
**Rule**: Events are processed at least once

- Failed events can be retried
- Idempotent processors recommended
- Retry count tracks attempts
- Max retries prevents infinite loops

---

### INV-005: Subscription Filter Consistency
**Rule**: Subscription filters applied consistently

- Empty filter = match all
- Non-empty filter = must match at least one
- All filters combined with AND
- Disabled subscriptions never triggered

---

### INV-006: Projection Versioning
**Rule**: Projection version reflects applied events

- Version incremented for each applied event
- `last_event_id` tracks most recent event
- Rebuilding projection replays all events

---

## Validation Rules

### VR-001: EventSource Enum Validation
**Valid Values**:
```python
class EventSource(str, Enum):
    FRONTEND = "frontend"      # Frontend user behavior
    BACKEND = "backend"        # Backend business logic
    SYSTEM = "system"          # System internal
    IOT_DEVICE = "iot_device"  # IoT device
    EXTERNAL_API = "external_api"  # External API
    SCHEDULED = "scheduled"    # Scheduled task
```

**Validation**: Pydantic enum validation at request parsing

---

### VR-002: EventCategory Enum Validation
**Valid Values**:
```python
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
```

---

### VR-003: EventStatus Enum Validation
**Valid Values**:
```python
class EventStatus(str, Enum):
    PENDING = "pending"       # Awaiting processing
    PROCESSING = "processing" # Being processed
    PROCESSED = "processed"   # Successfully processed
    FAILED = "failed"         # Processing failed
    ARCHIVED = "archived"     # Archived
```

---

### VR-004: Pagination Parameter Validation
**Rules**:
```python
limit: int = Field(100, ge=1, le=1000)  # 1-1000, default 100
offset: int = Field(0, ge=0)             # >= 0, default 0
```

**Edge Cases**:
- `limit=0` -> ValidationError
- `limit=1001` -> ValidationError
- `offset=-1` -> ValidationError

---

### VR-005: Event Type Validation
**Rules**:
- Required field (cannot be None)
- Non-empty string
- No format restrictions (free-form)

**Conventions** (not enforced):
- Dot-separated: `user.created`, `order.completed`
- Lowercase with underscores: `payment_processed`

---

### VR-006: RudderStack Event Validation
**Required Fields**:
- `event`: Event name (required)
- `type`: Event type (required)
- `timestamp`: ISO 8601 timestamp (required)

**Optional Fields**:
- `userId`: User ID
- `anonymousId`: Anonymous ID
- `properties`: Event properties dict
- `context`: Context dict

---

### VR-007: Subscription Event Types Validation
**Rules**:
- `event_types`: Required, non-empty list of strings
- `event_sources`: Optional list of EventSource enums
- `event_categories`: Optional list of EventCategory enums

---

## Error Conditions

### ER-001: Event Not Found
**When**: Event ID does not exist in database
**Method**: `get_event`, `mark_event_processed`
**Response**: Returns `None` or `False`
**HTTP Status**: 404 (at API layer)

**Recovery**: Client should verify event_id exists

---

### ER-002: Stream Not Found
**When**: Stream ID has no events
**Method**: `get_event_stream`
**Response**: Returns empty EventStream with events=[]
**HTTP Status**: 404 if stream entity doesn't exist

**Recovery**: Create events for the stream first

---

### ER-003: Projection Not Found
**When**: Projection ID not in cache or database
**Method**: `get_projection`
**Response**: Returns `None`
**HTTP Status**: 404 (at API layer)

**Recovery**: Create projection using `create_projection`

---

### ER-004: Database Connection Error
**When**: PostgreSQL gRPC service unavailable
**Method**: Any repository operation
**Response**: Exception logged, operation fails
**HTTP Status**: 500 or 503

**Recovery**:
- Retry with exponential backoff
- Check PostgreSQL gRPC service health
- Verify Consul service discovery

---

### ER-005: NATS Publishing Error
**When**: Event bus unavailable or publish fails
**Method**: Event publishing in any operation
**Behavior**: Error logged, operation continues
**HTTP Status**: N/A (non-blocking)

**Implementation**:
```python
try:
    await self.event_bus.publish_event(nats_event)
except Exception as e:
    logger.error(f"Failed to publish event: {e}")
    # Operation continues - event publishing is best-effort
```

---

### ER-006: Processing Queue Timeout
**When**: Queue get times out after 1 second
**Method**: `_process_event_queue`
**Behavior**: Loop continues, checks for shutdown
**Recovery**: Normal operation, allows graceful shutdown

---

### ER-007: Processor Execution Error
**When**: Processor throws exception
**Method**: `_execute_processor`
**Behavior**:
- Error logged
- Processing result with FAILED status saved
- Event marked as failed
- Does not affect other processors

---

### ER-008: Subscription Delivery Error
**When**: Webhook delivery fails
**Method**: `_deliver_to_subscriber`
**Behavior**: Error logged, delivery skipped
**Recovery**: Retry policy in subscription config (future)

---

### ER-009: Replay Error
**When**: Event republish fails during replay
**Method**: `replay_events`
**Behavior**:
- Error logged
- Failed count incremented
- Continue with remaining events
**Response**: Returns replayed/failed counts

---

### ER-010: Invalid Event Source/Category
**When**: Invalid enum value provided
**Method**: create_event, create_event_from_*
**Response**: Pydantic ValidationError
**HTTP Status**: 422

---

## Integration Contracts

### PostgreSQL gRPC Service

**Expectations**:
- Service name: `postgres_grpc_service`
- Default host: `isa-postgres-grpc`
- Default port: `50061`
- Protocol: gRPC with AsyncPostgresClient
- Schema: `event`

**Tables**:
- `event.events`: Main events table
- `event.event_streams`: Event streams
- `event.event_projections`: Projections
- `event.event_processors`: Processor configs
- `event.event_subscriptions`: Subscriptions
- `event.processing_results`: Processing results

**Connection**:
```python
self.db = AsyncPostgresClient(host=host, port=port, user_id="event_service")
```

---

### NATS Event Publishing

**Published Events**:
| Event Type | Subject | Trigger |
|------------|---------|---------|
| event.stored | event.stored | Event created |
| event.processed.success | event.processed.success | Processing success |
| event.processed.failed | event.processed.failed | Processing failure |
| event.subscription.created | event.subscription.created | Subscription created |
| event.replay.started | event.replay.started | Replay initiated |
| event.projection.created | event.projection.created | Projection created |

**Stream Configuration**:
```python
STREAM_NAME = "event-stream"
SUBJECTS = ["event.>"]
MAX_MESSAGES = 100000
CONSUMER_PREFIX = "event"
```

---

### Consul Service Discovery

**Expectations**:
- Service registered at startup
- Service name: `event_service`
- Health check endpoint: `/health`
- Discovers `postgres_grpc_service` via Consul

**Service Metadata**:
- `version`: Service version
- `capabilities`: Service capabilities
- `route_count`: Number of API routes

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| create_event | < 50ms | < 200ms |
| get_event | < 30ms | < 100ms |
| query_events | < 100ms | < 500ms |
| get_event_stream | < 100ms | < 500ms |
| get_statistics | < 100ms | < 300ms |
| create_subscription | < 50ms | < 200ms |
| replay_events (dry_run) | < 100ms | < 500ms |
| create_projection | < 200ms | < 1000ms |

### Throughput Targets

- Event creation: 500 req/s
- Event queries: 1000 req/s
- Stream retrieval: 500 req/s
- Subscription matching: 10000 events/s
- Event processing: 1000 events/s

### Resource Limits

- Max concurrent connections: 100
- Max events per query: 1000 (limit parameter)
- Max batch size: 100 (batch endpoint)
- Processing queue size: Unlimited (asyncio.Queue)
- Max retry count: 3 (configurable)

### Processing SLAs

- Event processing latency: < 5 seconds from creation
- Retry interval: Immediate (configurable)
- Failed event retention: Indefinite (until archived)

---

## Test Coverage Requirements

All tests MUST cover:

- Happy path (BR-XXX success scenarios)
- Validation errors (422)
- Not found errors (404)
- State transitions (PENDING -> PROCESSED/FAILED)
- Event publishing (verify published)
- Idempotency (retry handling)
- Subscription matching logic
- Projection building and updating
- Replay dry run and actual replay
- Concurrent event creation
- Processing queue behavior
- Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-30
**Owner**: Event Service Team
