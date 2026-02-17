# Event Service - Product Requirements Document (PRD)

## Document Information

| Field | Value |
|-------|-------|
| Service Name | event_service |
| Version | 1.0.0 |
| Status | Production |
| Last Updated | 2025-12-30 |
| Owner | Platform Team |

---

## 1. Executive Summary

### 1.1 Overview

The Event Service is a unified event management system that serves as the central hub for collecting, storing, processing, and distributing events across the isA platform. It implements event sourcing patterns and provides capabilities for event replay, projections, and real-time subscriptions.

### 1.2 Purpose

The Event Service addresses the following platform needs:

1. **Unified Event Collection**: Aggregate events from multiple sources including frontend applications, backend services, IoT devices, and external integrations (RudderStack)
2. **Event Sourcing**: Maintain a complete audit trail of all system events with support for event replay and state reconstruction
3. **Real-time Processing**: Enable real-time event processing through configurable processors and subscription-based delivery
4. **Analytics Foundation**: Provide event statistics and aggregations for business intelligence and operational monitoring

### 1.3 Key Capabilities

- Event creation (single and batch)
- Multi-source event collection (frontend, backend, IoT, external APIs)
- RudderStack webhook integration for analytics events
- Event querying with flexible filters and pagination
- Event stream management for entity-based event grouping
- Event replay for debugging and state reconstruction
- Event projections for materialized views
- Configurable event processors
- Webhook-based subscriptions for event distribution
- Comprehensive event statistics

---

## 2. User Stories

### 2.1 Developer Stories - Event Creation

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ES-001 | As a backend developer, I want to create events from my service so that business actions are tracked | Event created with unique ID, stored in database, published to NATS |
| ES-002 | As a backend developer, I want to create multiple events in a single request so that I can reduce network overhead | Batch endpoint accepts array of events, all events created atomically |
| ES-003 | As a frontend developer, I want to send user interaction events so that we can track user behavior | Frontend events accepted without authentication, enriched with client info |
| ES-004 | As an integration engineer, I want to receive RudderStack events via webhook so that we consolidate all analytics data | Webhook validates signature, transforms RudderStack format to internal format |

### 2.2 Developer Stories - Event Querying

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ES-005 | As a developer, I want to query events by user ID so that I can debug user-specific issues | Query returns all events for specified user with pagination |
| ES-006 | As a developer, I want to filter events by type, source, and category so that I can narrow down results | Multiple filter criteria can be combined in single query |
| ES-007 | As a developer, I want to filter events by time range so that I can analyze specific periods | Start and end time filters applied correctly |
| ES-008 | As a developer, I want to get event statistics so that I can monitor system health | Statistics include counts by status, source, category, and time periods |

### 2.3 Developer Stories - Event Processing

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ES-009 | As a developer, I want to register event processors so that events trigger automated actions | Processor registered, enabled, and invoked for matching events |
| ES-010 | As a developer, I want to enable/disable processors without deleting them so that I can control processing | Toggle endpoint updates processor state, processing respects state |
| ES-011 | As a developer, I want to replay events for a specific time range so that I can reprocess after bug fixes | Replay creates new processing results, original events preserved |
| ES-012 | As a developer, I want dry-run replay so that I can preview which events would be replayed | Dry-run returns event list without actual processing |

### 2.4 Developer Stories - Event Subscriptions

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ES-013 | As a service developer, I want to subscribe to specific event types so that my service receives relevant events | Subscription created with filters, events delivered to callback URL |
| ES-014 | As a developer, I want to list all subscriptions so that I can audit event routing | List endpoint returns all active subscriptions |
| ES-015 | As a developer, I want to delete subscriptions so that I can clean up unused integrations | Delete endpoint removes subscription, delivery stops immediately |

### 2.5 Developer Stories - Event Projections

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| ES-016 | As a developer, I want to get the current state projection for an entity so that I can see derived state | Projection returns accumulated state from all entity events |
| ES-017 | As a developer, I want projections to update automatically when new events arrive so that state is always current | New events applied to projection, version incremented |

---

## 3. Functional Requirements

### 3.1 Event Creation

#### 3.1.1 Single Event Creation

**Endpoint**: `POST /api/v1/events/create`

**Requirements**:
- Accept event with type, source, category, user_id, and data payload
- Generate unique event_id (UUID v4)
- Set initial status to PENDING
- Persist event to PostgreSQL database
- Add event to processing queue
- Trigger real-time processors asynchronously
- Publish `event.stored` event to NATS event bus
- Return complete event response with generated fields

**Event Sources**:
- `frontend` - User interactions from web/mobile clients
- `backend` - Business logic from microservices
- `system` - Internal system operations
- `iot_device` - Device telemetry and commands
- `external_api` - Third-party integrations
- `scheduled` - Cron jobs and scheduled tasks

**Event Categories**:
- User Actions: `user_action`, `page_view`, `form_submit`, `click`
- Business Events: `user_lifecycle`, `payment`, `order`, `task`
- System Events: `system`, `security`, `performance`, `error`
- IoT Events: `device`, `device_status`, `telemetry`, `command`, `alert`

#### 3.1.2 Batch Event Creation

**Endpoint**: `POST /api/v1/events/batch`

**Requirements**:
- Accept array of event creation requests (up to configurable limit)
- Create all events in sequence
- Each event processed independently (partial success allowed)
- Return array of event responses in same order as requests
- Background publish all events to NATS

#### 3.1.3 Frontend Event Collection

**Endpoint**: `POST /api/v1/events/frontend`

**Requirements**:
- Accept lightweight frontend event model
- No authentication required (public endpoint)
- Capture client context (IP, User-Agent, Referer)
- Construct NATS subject: `events.frontend.{category}.{event_type}`
- Publish directly to NATS JetStream (bypass database for performance)
- Return acceptance response with generated event_id

**Batch Endpoint**: `POST /api/v1/events/frontend/batch`

**Requirements**:
- Accept array of frontend events with optional client_info
- Process all events in single request
- Merge batch client_info with individual event metadata
- Return count and list of generated event_ids

#### 3.1.4 RudderStack Integration

**Endpoint**: `POST /webhooks/rudderstack`

**Requirements**:
- Validate webhook signature if secret configured
- Accept single event or array of events
- Transform RudderStack event format to internal format:
  - Map `event` field to `event_type`
  - Set `event_source` to FRONTEND
  - Categorize based on RudderStack `type` field (page, track, identify)
  - Preserve original timestamps and IDs in metadata
- Process events in background tasks
- Return immediate acceptance response

---

### 3.2 Event Querying

#### 3.2.1 Query Events

**Endpoint**: `POST /api/v1/events/query`

**Filter Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | string | Filter by user ID |
| event_type | string | Filter by event type |
| event_source | EventSource | Filter by source (frontend, backend, etc.) |
| event_category | EventCategory | Filter by category |
| status | EventStatus | Filter by processing status |
| start_time | datetime | Events after this time |
| end_time | datetime | Events before this time |
| limit | int | Max results (1-1000, default 100) |
| offset | int | Pagination offset |

**Response**:
- Array of event responses
- Total count for pagination
- Has_more indicator

#### 3.2.2 Get Single Event

**Endpoint**: `GET /api/v1/events/{event_id}`

**Requirements**:
- Return complete event by ID
- Return 404 if not found
- Include all metadata and processing info

#### 3.2.3 Get Event Statistics

**Endpoint**: `GET /api/v1/events/statistics`

**Statistics Returned**:
- Total events count
- Pending events count
- Processed events count
- Failed events count
- Events by source distribution
- Events by category distribution
- Events by type distribution
- Events today/this week/this month
- Average processing time
- Processing rate percentage
- Error rate percentage
- Top active users
- Top event types

---

### 3.3 Event Processing

#### 3.3.1 Event Processors

**Register Processor**: `POST /api/v1/events/processors`

**Processor Configuration**:
| Field | Type | Description |
|-------|------|-------------|
| processor_name | string | Unique processor identifier |
| processor_type | string | Type of processor (webhook, internal, etc.) |
| enabled | bool | Whether processor is active |
| priority | int | Execution order (higher = first) |
| filters | object | Matching criteria (event_type, event_source) |
| config | object | Processor-specific configuration |

**List Processors**: `GET /api/v1/events/processors`

**Toggle Processor**: `PUT /api/v1/events/processors/{processor_id}/toggle?enabled={bool}`

#### 3.3.2 Background Processing

**Requirements**:
- Background task runs continuously
- Polls for PENDING status events in configurable batches
- Applies all matching enabled processors
- Updates event status to PROCESSED or FAILED
- Records processing results with duration
- Publishes `event.processed.success` or `event.processed.failed` events
- Implements retry logic for failed events

#### 3.3.3 Event Replay

**Endpoint**: `POST /api/v1/events/replay`

**Request Options**:
| Field | Type | Description |
|-------|------|-------------|
| event_ids | array | Specific events to replay |
| stream_id | string | Replay entire stream |
| start_time | datetime | Replay from time |
| end_time | datetime | Replay until time |
| target_service | string | Optional target for replay |
| dry_run | bool | Preview without processing |

**Requirements**:
- Execute replay in background task
- Publish `event.replay.started` event
- Support dry-run mode for preview
- Return immediate response with replay status

---

### 3.4 Event Subscriptions

#### 3.4.1 Create Subscription

**Endpoint**: `POST /api/v1/events/subscriptions`

**Subscription Configuration**:
| Field | Type | Description |
|-------|------|-------------|
| subscriber_name | string | Name of subscribing service |
| subscriber_type | string | Type (service, webhook, etc.) |
| event_types | array | Event types to receive |
| event_sources | array | Sources to filter (optional) |
| event_categories | array | Categories to filter (optional) |
| callback_url | string | Webhook URL for delivery |
| webhook_secret | string | Secret for signing deliveries |
| retry_policy | object | Retry configuration |

#### 3.4.2 List Subscriptions

**Endpoint**: `GET /api/v1/events/subscriptions`

**Requirements**:
- Return all active subscriptions
- Include subscription metadata and filters

#### 3.4.3 Delete Subscription

**Endpoint**: `DELETE /api/v1/events/subscriptions/{subscription_id}`

**Requirements**:
- Remove subscription from active list
- Stop delivery immediately
- Return confirmation

---

### 3.5 Event Streams and Projections

#### 3.5.1 Get Event Stream

**Endpoint**: `GET /api/v1/events/stream/{stream_id}`

**Query Parameters**:
- `from_version`: Optional starting version for partial stream

**Requirements**:
- Return all events for stream ID
- Stream ID format: `{entity_type}:{entity_id}`
- Include stream metadata and version

#### 3.5.2 Get Projection

**Endpoint**: `GET /api/v1/events/projections/{entity_type}/{entity_id}`

**Requirements**:
- Return materialized state for entity
- Projection built from all entity events
- Include version and last event ID
- Cache projections for performance

---

### 3.6 Frontend Event Collection Health

**Endpoint**: `GET /api/v1/events/frontend/health`

**Requirements**:
- Return frontend collection subsystem status
- Include NATS connection status
- No authentication required

---

## 4. Non-Functional Requirements

### 4.1 Performance

| Metric | Requirement |
|--------|-------------|
| Event Creation Latency | < 50ms p95 for single event |
| Batch Creation Throughput | > 1000 events/second |
| Frontend Event Latency | < 20ms p95 (direct to NATS) |
| Query Response Time | < 200ms for 1000 result limit |
| Statistics Calculation | < 500ms |
| Processing Throughput | > 500 events/second per processor |

### 4.2 Scalability

| Aspect | Requirement |
|--------|-------------|
| Horizontal Scaling | Support multiple service instances behind load balancer |
| Event Volume | Handle > 10M events/day |
| Concurrent Connections | Support > 1000 concurrent API clients |
| Subscription Fan-out | Support > 100 active subscriptions |
| Storage Growth | Design for 1 year event retention (configurable) |

### 4.3 Reliability

| Aspect | Requirement |
|--------|-------------|
| Availability | 99.9% uptime |
| Data Durability | Events persisted before acknowledgment |
| At-Least-Once Delivery | Guaranteed delivery to subscribers with retries |
| Processing Guarantees | Failed events retried up to configurable max |
| Graceful Degradation | Continue accepting events if processors fail |

### 4.4 Observability

| Aspect | Requirement |
|--------|-------------|
| Health Endpoints | /health for service status |
| Logging | Structured JSON logging with correlation IDs |
| Metrics | Expose Prometheus metrics |
| Tracing | Support distributed tracing headers |
| Alerting | Alert on processing backlog, error rate |

### 4.5 Security

| Aspect | Requirement |
|--------|-------------|
| API Authentication | Required for management endpoints |
| Frontend Collection | Allow unauthenticated for analytics |
| Webhook Validation | Signature verification for RudderStack |
| Data Privacy | Support PII filtering in event data |
| Audit Trail | All events immutable once stored |

---

## 5. API Surface

### 5.1 Complete Endpoint Reference

| # | Endpoint | Method | Auth | Description |
|---|----------|--------|------|-------------|
| 1 | `/health` | GET | No | Service health check |
| 2 | `/api/v1/events/create` | POST | Yes | Create single event |
| 3 | `/api/v1/events/batch` | POST | Yes | Create batch events |
| 4 | `/api/v1/events/{event_id}` | GET | Yes | Get event by ID |
| 5 | `/api/v1/events/query` | POST | Yes | Query events with filters |
| 6 | `/api/v1/events/statistics` | GET | Yes | Get event statistics |
| 7 | `/api/v1/events/stream/{stream_id}` | GET | Yes | Get event stream |
| 8 | `/api/v1/events/replay` | POST | Yes | Replay events |
| 9 | `/api/v1/events/projections/{entity_type}/{entity_id}` | GET | Yes | Get entity projection |
| 10 | `/api/v1/events/subscriptions` | GET | Yes | List subscriptions |
| 11 | `/api/v1/events/subscriptions` | POST | Yes | Create subscription |
| 12 | `/api/v1/events/subscriptions/{subscription_id}` | DELETE | Yes | Delete subscription |
| 13 | `/api/v1/events/processors` | GET | Yes | List processors |
| 14 | `/api/v1/events/processors` | POST | Yes | Register processor |
| 15 | `/api/v1/events/processors/{processor_id}/toggle` | PUT | Yes | Toggle processor |
| 16 | `/api/v1/events/frontend` | POST | No | Collect frontend event |
| 17 | `/api/v1/events/frontend/batch` | POST | No | Collect frontend batch |
| 18 | `/api/v1/events/frontend/health` | GET | No | Frontend collection health |
| 19 | `/webhooks/rudderstack` | POST | No* | RudderStack webhook |

*RudderStack webhook uses signature-based validation

### 5.2 Request/Response Models

#### EventCreateRequest
```json
{
  "event_type": "user.registered",
  "event_source": "backend",
  "event_category": "user_lifecycle",
  "user_id": "user_123",
  "data": {
    "email": "user@example.com",
    "plan": "premium"
  },
  "metadata": {},
  "context": {}
}
```

#### EventResponse
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "user.registered",
  "event_source": "backend",
  "event_category": "user_lifecycle",
  "user_id": "user_123",
  "data": {},
  "status": "pending",
  "timestamp": "2025-12-30T10:00:00Z",
  "created_at": "2025-12-30T10:00:00Z"
}
```

#### EventQueryRequest
```json
{
  "user_id": "user_123",
  "event_type": "user.registered",
  "event_source": "backend",
  "status": "processed",
  "start_time": "2025-12-01T00:00:00Z",
  "end_time": "2025-12-31T23:59:59Z",
  "limit": 100,
  "offset": 0
}
```

#### EventStatistics
```json
{
  "total_events": 1000000,
  "pending_events": 150,
  "processed_events": 999800,
  "failed_events": 50,
  "events_by_source": {
    "frontend": 600000,
    "backend": 400000
  },
  "events_by_category": {},
  "events_by_type": {},
  "events_today": 5000,
  "events_this_week": 35000,
  "events_this_month": 150000,
  "average_processing_time": 25.5,
  "processing_rate": 99.98,
  "error_rate": 0.005
}
```

---

## 6. Epics and Milestones

### 6.1 Epic 1: Core Event Management (Completed)

| Milestone | Status | Description |
|-----------|--------|-------------|
| M1.1 Event Creation API | Done | Single and batch event creation |
| M1.2 Event Storage | Done | PostgreSQL persistence layer |
| M1.3 Event Querying | Done | Flexible query with filters |
| M1.4 Statistics API | Done | Event aggregations and metrics |

### 6.2 Epic 2: Event Processing (Completed)

| Milestone | Status | Description |
|-----------|--------|-------------|
| M2.1 Processor Registry | Done | Register and manage processors |
| M2.2 Background Processing | Done | Async event processing loop |
| M2.3 Processing Results | Done | Track and store results |
| M2.4 Event Replay | Done | Replay events for reprocessing |

### 6.3 Epic 3: Event Distribution (Completed)

| Milestone | Status | Description |
|-----------|--------|-------------|
| M3.1 NATS Integration | Done | Publish events to event bus |
| M3.2 Subscription Management | Done | Create and manage subscriptions |
| M3.3 Webhook Delivery | Done | HTTP callback delivery |
| M3.4 RudderStack Integration | Done | External analytics webhook |

### 6.4 Epic 4: Frontend Collection (Completed)

| Milestone | Status | Description |
|-----------|--------|-------------|
| M4.1 Frontend API | Done | Lightweight collection endpoint |
| M4.2 Batch Collection | Done | High-throughput batch endpoint |
| M4.3 Direct NATS Publishing | Done | Bypass DB for performance |

### 6.5 Epic 5: Event Sourcing (In Progress)

| Milestone | Status | Description |
|-----------|--------|-------------|
| M5.1 Event Streams | Done | Stream-based event grouping |
| M5.2 Projections | Done | Materialized view support |
| M5.3 Snapshot Support | Planned | Periodic state snapshots |
| M5.4 Time-Travel Queries | Planned | Point-in-time state reconstruction |

### 6.6 Epic 6: Advanced Features (Future)

| Milestone | Status | Description |
|-----------|--------|-------------|
| M6.1 Event Schema Registry | Planned | Schema validation and versioning |
| M6.2 Dead Letter Queue | Planned | Failed event handling |
| M6.3 Event Archival | Planned | Long-term storage policy |
| M6.4 Real-time Streaming | Planned | WebSocket/SSE event streaming |

---

## 7. Success Metrics

### 7.1 Operational Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Event Ingestion Rate | > 1000/sec | Events created per second |
| Processing Latency p95 | < 100ms | Time from creation to processed |
| Error Rate | < 0.1% | Failed events / total events |
| Subscription Delivery Rate | > 99.9% | Successful deliveries / attempts |
| API Availability | > 99.9% | Uptime percentage |

### 7.2 Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Frontend Events Captured | > 95% | Client events received vs sent |
| Analytics Coverage | 100% | Services publishing events |
| Event Replay Success | > 99% | Successful replay operations |
| Query Response Time | < 200ms | Average query latency |

### 7.3 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | > 80% | Unit + integration tests |
| API Documentation | 100% | Endpoints documented |
| Schema Compliance | 100% | Events matching schema |

---

## 8. Dependencies

### 8.1 Infrastructure Dependencies

| Dependency | Purpose | Criticality |
|------------|---------|-------------|
| PostgreSQL (via gRPC) | Event persistence | Critical |
| NATS JetStream | Event streaming | Critical |
| Consul | Service discovery | High |
| Redis | Caching (future) | Medium |

### 8.2 Service Dependencies

| Service | Interaction | Description |
|---------|-------------|-------------|
| account_service | Event consumer | Subscribes to user lifecycle events |
| notification_service | Event consumer | Subscribes to alert events |
| audit_service | Event consumer | Subscribes to security events |
| billing_service | Event consumer | Subscribes to payment events |

### 8.3 Integration Dependencies

| Integration | Protocol | Description |
|-------------|----------|-------------|
| RudderStack | Webhook | Analytics event ingestion |
| Frontend SDK | HTTP | Client-side event collection |
| NATS Event Bus | gRPC | Centralized event publishing |

---

## 9. Appendix

### 9.1 Event Source Definitions

```python
class EventSource(str, Enum):
    FRONTEND = "frontend"           # User interactions
    BACKEND = "backend"             # Business logic
    SYSTEM = "system"               # Internal operations
    IOT_DEVICE = "iot_device"       # Device telemetry
    EXTERNAL_API = "external_api"   # Third-party
    SCHEDULED = "scheduled"         # Cron/scheduled
```

### 9.2 Event Category Definitions

```python
class EventCategory(str, Enum):
    # User Actions
    USER_ACTION = "user_action"
    PAGE_VIEW = "page_view"
    FORM_SUBMIT = "form_submit"
    CLICK = "click"

    # Business Events
    USER_LIFECYCLE = "user_lifecycle"
    PAYMENT = "payment"
    ORDER = "order"
    TASK = "task"

    # System Events
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"

    # IoT Events
    DEVICE = "device"
    DEVICE_STATUS = "device_status"
    TELEMETRY = "telemetry"
    COMMAND = "command"
    ALERT = "alert"
```

### 9.3 Event Status Lifecycle

```
PENDING --> PROCESSING --> PROCESSED
                |
                v
              FAILED --> PENDING (retry)
                |
                v
              ARCHIVED
```

### 9.4 Published Event Types

| Event Type | Description |
|------------|-------------|
| `event.stored` | New event stored in database |
| `event.processed.success` | Event processed successfully |
| `event.processed.failed` | Event processing failed |
| `event.subscription.created` | New subscription registered |
| `event.replay.started` | Event replay initiated |
| `event.projection.created` | New projection created |

### 9.5 Database Schema

**Schema**: `event`

**Tables**:
- `events` - Main event storage
- `event_streams` - Stream metadata
- `event_projections` - Materialized projections
- `event_processors` - Processor configurations
- `event_subscriptions` - Subscription configurations
- `processing_results` - Processing audit trail

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-30 | Platform Team | Initial PRD based on implementation |
