# Telemetry Service - Logic Contract

## Overview

This document defines the business rules, state machines, edge cases, and integration contracts for the Telemetry Service. All implementations and tests MUST conform to these specifications.

**Service**: telemetry_service
**Port**: 8218
**Version**: 1.0.0
**Last Updated**: 2025-12-18

---

## Business Rules

### Data Ingestion Rules (BR-ING-001 to BR-ING-015)

**BR-ING-001: Timestamp Requirement**
- **Given**: Device sends telemetry data point
- **When**: timestamp field is provided
- **Then**: timestamp MUST be valid ISO 8601 datetime
- **Validation**: On all ingestion operations
- **Error**: ValidationError("Invalid timestamp format")
- **Example**:
  - Valid: "2025-12-18T10:00:00Z"
  - Invalid: "2025-12-18", "invalid", null

**BR-ING-002: Timestamp Future Limit**
- **Given**: Device sends telemetry data point
- **When**: timestamp is in the future
- **Then**: timestamp MUST NOT exceed 5 minutes ahead
- **Reason**: Prevent clock drift issues
- **Error**: ValidationError("Timestamp cannot be more than 5 minutes in the future")

**BR-ING-003: Timestamp Past Limit**
- **Given**: Device sends telemetry data point
- **When**: timestamp is in the past
- **Then**: timestamp MUST NOT exceed retention period (default 90 days)
- **Reason**: Respect data retention policies
- **Error**: ValidationError("Timestamp exceeds retention period")

**BR-ING-004: Device ID Requirement**
- **Given**: Device sends telemetry data
- **When**: device_id path parameter
- **Then**: device_id MUST be non-empty string (1-100 chars)
- **Validation**: Path parameter validation
- **Error**: ValidationError("device_id is required")

**BR-ING-005: Metric Name Requirement**
- **Given**: Device sends telemetry data point
- **When**: metric_name field is provided
- **Then**: metric_name MUST be 1-100 characters, non-empty
- **Validation**: On all ingestion operations
- **Error**: ValidationError("metric_name must be 1-100 characters")
- **Example**:
  - Valid: "temperature", "cpu_usage", "battery_level"
  - Invalid: "", "x" * 101

**BR-ING-006: Metric Name Format**
- **Given**: Device sends telemetry data point
- **When**: metric_name contains characters
- **Then**: metric_name SHOULD follow snake_case convention
- **Allowed**: Alphanumeric, underscore, dot, dash
- **Note**: Not enforced, but recommended
- **Example**: "cpu_usage", "disk.read_bytes", "sensor-001"

**BR-ING-007: Value Type Consistency**
- **Given**: Device sends telemetry data point
- **When**: metric definition exists for metric_name
- **Then**: value type MUST match metric definition data_type
- **Check**: If metric_def.data_type = "numeric", value must be int/float
- **Error**: TelemetryError("Value type mismatch for metric {name}")
- **Note**: If no metric definition, any type accepted

**BR-ING-008: Value Range Validation**
- **Given**: Device sends numeric telemetry data
- **When**: metric definition has min_value or max_value
- **Then**: value MUST be within defined range
- **Check**: min_value <= value <= max_value
- **Behavior**: Log warning, still ingest (configurable)
- **Error**: Warning logged, data ingested

**BR-ING-009: Batch Size Limit**
- **Given**: Gateway sends batch ingestion request
- **When**: data_points array provided
- **Then**: batch size MUST be 1-1000 data points
- **Validation**: Request validation
- **Error**: ValidationError("Batch size must be 1-1000")

**BR-ING-010: Partial Batch Failure**
- **Given**: Gateway sends batch with some invalid points
- **When**: Some data points fail validation
- **Then**: Valid points MUST be ingested, failures tracked
- **Response**: {ingested_count: N, failed_count: M, errors: [...]}
- **Success**: Return 200 if any points ingested

**BR-ING-011: Idempotent Upsert**
- **Given**: Same data point sent multiple times
- **When**: (timestamp, device_id, metric_name) matches existing
- **Then**: System MUST upsert (update if exists)
- **Behavior**: Latest value overwrites previous
- **Use Case**: Safe retry without duplicates

**BR-ING-012: Unit Specification**
- **Given**: Device sends telemetry data point
- **When**: unit field is provided
- **Then**: unit MUST be max 20 characters
- **Optional**: Unit is not required
- **Examples**: "celsius", "percent", "bytes", "ms"

**BR-ING-013: Tags Format**
- **Given**: Device sends telemetry data point
- **When**: tags field is provided
- **Then**: tags MUST be key-value string pairs
- **Limit**: Max 20 tags per data point
- **Key/Value**: 1-50 chars / 1-100 chars
- **Use Case**: Filtering and categorization

**BR-ING-014: Metadata Size Limit**
- **Given**: Device sends telemetry data point
- **When**: metadata field is provided
- **Then**: metadata JSON MUST be under 10KB
- **Type**: Any valid JSON object
- **Use Case**: Extended context and diagnostics

**BR-ING-015: Quality Score**
- **Given**: Device sends telemetry data point
- **When**: quality field is provided
- **Then**: quality MUST be integer 0-100
- **Default**: 100 (trusted source)
- **Use Case**: Filter unreliable readings in analytics

---

### Metric Definition Rules (BR-MET-001 to BR-MET-010)

**BR-MET-001: Metric Name Uniqueness**
- **Given**: Admin creates metric definition
- **When**: metric name provided
- **Then**: name MUST be unique across all definitions
- **Scope**: Global uniqueness
- **Error**: MetricError("Metric with name '{name}' already exists")

**BR-MET-002: Data Type Immutability**
- **Given**: Metric definition exists
- **When**: Update requested
- **Then**: data_type CANNOT be changed
- **Reason**: Prevent type confusion in historical data
- **Solution**: Delete and recreate for type change

**BR-MET-003: Data Type Values**
- **Given**: Admin creates metric definition
- **When**: data_type field provided
- **Then**: data_type MUST be one of valid enum values
- **Valid**: numeric, string, boolean, json, binary, geolocation, timestamp
- **Error**: ValidationError("Invalid data_type")

**BR-MET-004: Metric Type Values**
- **Given**: Admin creates metric definition
- **When**: metric_type field provided
- **Then**: metric_type MUST be one of valid enum values
- **Valid**: gauge, counter, histogram, summary
- **Default**: gauge
- **Error**: ValidationError("Invalid metric_type")

**BR-MET-005: Retention Period Limits**
- **Given**: Admin creates metric definition
- **When**: retention_days field provided
- **Then**: retention_days MUST be 1-3650 days
- **Default**: 90 days
- **Error**: ValidationError("retention_days must be 1-3650")

**BR-MET-006: Aggregation Interval Limits**
- **Given**: Admin creates metric definition
- **When**: aggregation_interval field provided
- **Then**: aggregation_interval MUST be 1-86400 seconds
- **Default**: 60 seconds (1 minute)
- **Error**: ValidationError("aggregation_interval must be 1-86400")

**BR-MET-007: Min/Max Value Consistency**
- **Given**: Admin creates metric definition with bounds
- **When**: Both min_value and max_value provided
- **Then**: min_value MUST be < max_value
- **Validation**: On create and update
- **Error**: MetricError("min_value must be less than max_value")

**BR-MET-008: Creator Attribution**
- **Given**: Admin creates metric definition
- **When**: Definition saved
- **Then**: created_by MUST be set to requesting user_id
- **Immutable**: Cannot be changed after creation
- **Use Case**: Audit trail and ownership

**BR-MET-009: Soft Delete Behavior**
- **Given**: Admin deletes metric definition
- **When**: Historical data exists for metric
- **Then**: Definition deleted, data retained per retention
- **Behavior**: New data for deleted metric rejected
- **Note**: Does NOT cascade delete telemetry data

**BR-MET-010: Event Publication**
- **Given**: Metric definition created
- **When**: Database transaction commits
- **Then**: System MUST publish metric.defined event
- **Timing**: After commit, before response
- **Consumers**: audit_service, analytics_service

---

### Alert Rule Rules (BR-ALR-001 to BR-ALR-015)

**BR-ALR-001: Rule Name Requirement**
- **Given**: User creates alert rule
- **When**: name field provided
- **Then**: name MUST be 1-200 characters, non-empty
- **Validation**: On create and update
- **Error**: ValidationError("name must be 1-200 characters")

**BR-ALR-002: Condition Operator Validation**
- **Given**: User creates alert rule
- **When**: condition field provided
- **Then**: condition MUST be valid comparison operator
- **Valid**: >, <, >=, <=, ==, !=
- **Error**: ValidationError("Invalid condition operator")

**BR-ALR-003: Threshold Value Type**
- **Given**: User creates alert rule
- **When**: threshold_value provided
- **Then**: threshold_value stored as string for flexibility
- **Reason**: Support numeric, string, and boolean comparisons
- **Conversion**: Parsed based on metric data_type during evaluation

**BR-ALR-004: Evaluation Window Limits**
- **Given**: User creates alert rule
- **When**: evaluation_window provided
- **Then**: evaluation_window MUST be 60-3600 seconds
- **Default**: 300 seconds (5 minutes)
- **Error**: ValidationError("evaluation_window must be 60-3600 seconds")

**BR-ALR-005: Trigger Count Range**
- **Given**: User creates alert rule
- **When**: trigger_count provided
- **Then**: trigger_count MUST be 1-100
- **Default**: 1 (trigger on first violation)
- **Use Case**: Reduce false positives with higher counts

**BR-ALR-006: Alert Level Requirement**
- **Given**: User creates alert rule
- **When**: level field provided
- **Then**: level MUST be valid AlertLevel enum
- **Valid**: info, warning, error, critical, emergency
- **Default**: warning
- **Error**: ValidationError("Invalid alert level")

**BR-ALR-007: Cooldown Period Limits**
- **Given**: User creates alert rule
- **When**: cooldown_minutes provided
- **Then**: cooldown_minutes MUST be 1-1440 minutes
- **Default**: 15 minutes
- **Purpose**: Prevent alert storms

**BR-ALR-008: Auto-Resolve Configuration**
- **Given**: User creates alert rule
- **When**: auto_resolve is enabled
- **Then**: auto_resolve_timeout MUST be 300-86400 seconds
- **Default**: auto_resolve=True, timeout=3600 (1 hour)
- **Behavior**: Alert auto-resolves when condition clears

**BR-ALR-009: Device Targeting**
- **Given**: User creates alert rule
- **When**: device_ids or device_groups provided
- **Then**: Rule evaluated only for matching devices
- **Empty Lists**: Rule applies to ALL devices
- **Use Case**: Targeted monitoring per device

**BR-ALR-010: Notification Channels Validation**
- **Given**: User creates alert rule
- **When**: notification_channels provided
- **Then**: Channels should exist in notification_service
- **Behavior**: Invalid channels ignored with warning
- **Examples**: ["email", "slack", "pagerduty"]

**BR-ALR-011: Real-Time Evaluation**
- **Given**: Telemetry data ingested
- **When**: Data matches enabled alert rules
- **Then**: Rules MUST be evaluated synchronously
- **Timing**: During ingestion, before response
- **Note**: Alert creation is async (doesn't block ingestion)

**BR-ALR-012: Rule Statistics Tracking**
- **Given**: Alert rule triggers
- **When**: Alert created successfully
- **Then**: Rule statistics MUST be updated
- **Fields**: total_triggers++, last_triggered = now()
- **Use Case**: Rule effectiveness analysis

**BR-ALR-013: Rule Enable/Disable**
- **Given**: User toggles rule enabled status
- **When**: enabled = false
- **Then**: Rule MUST NOT be evaluated during ingestion
- **Immediate**: Change takes effect immediately
- **Stateless**: No impact on existing alerts

**BR-ALR-014: Event Publication**
- **Given**: Alert rule created
- **When**: Database transaction commits
- **Then**: System MUST publish alert.rule.created event
- **Timing**: After commit, before response
- **Consumers**: audit_service, notification_service

**BR-ALR-015: Metric Name Flexibility**
- **Given**: User creates alert rule
- **When**: metric_name provided
- **Then**: metric_name can reference undefined metric
- **Use Case**: Create rules before metric definitions exist
- **Behavior**: Rule waits for matching data to arrive

---

### Alert Management Rules (BR-ALM-001 to BR-ALM-010)

**BR-ALM-001: Alert Status Values**
- **Given**: Alert exists
- **When**: Status checked
- **Then**: status MUST be one of valid AlertStatus enum
- **Valid**: active, acknowledged, resolved, suppressed
- **Initial**: active

**BR-ALM-002: Acknowledgement Transition**
- **Given**: User acknowledges alert
- **When**: Alert status is active
- **Then**: Status changes to acknowledged
- **Side Effects**:
  - acknowledged_by = user_id
  - acknowledged_at = now()
- **Error**: StateTransitionError if not active

**BR-ALM-003: Resolution Transition**
- **Given**: User resolves alert
- **When**: Alert status is active or acknowledged
- **Then**: Status changes to resolved
- **Side Effects**:
  - resolved_by = user_id
  - resolved_at = now()
  - resolution_note = provided note
- **Event**: alert.resolved published

**BR-ALM-004: Auto-Resolution**
- **Given**: Alert rule has auto_resolve=True
- **When**: Condition clears for auto_resolve_timeout duration
- **Then**: Alert MUST auto-resolve
- **resolved_by**: "system"
- **resolution_note**: "Auto-resolved: condition cleared"

**BR-ALM-005: Cooldown Enforcement**
- **Given**: Alert rule triggers
- **When**: Same rule triggered within cooldown_minutes
- **Then**: New alert MUST NOT be created
- **Scope**: Per rule, per device combination
- **Reset**: Cooldown resets after alert resolution

**BR-ALM-006: Alert Deduplication**
- **Given**: Alert condition met multiple times
- **When**: Active alert exists for same rule/device
- **Then**: Do NOT create duplicate alert
- **Behavior**: Update existing alert if needed

**BR-ALM-007: Status Transition Validation**
- **Given**: Alert status change requested
- **When**: Transition not in allowed transitions
- **Then**: System MUST reject with error
- **Error**: StateTransitionError("Cannot transition from X to Y")

**BR-ALM-008: Terminal State Protection**
- **Given**: Alert in resolved or suppressed state
- **When**: Acknowledge requested
- **Then**: System MUST reject transition
- **Reason**: Cannot acknowledge already resolved alert

**BR-ALM-009: Event on Alert Trigger**
- **Given**: Alert condition met
- **When**: New alert created
- **Then**: System MUST publish alert.triggered event
- **Priority**: High (immediate notification required)
- **Consumers**: notification_service, audit_service

**BR-ALM-010: Event on Alert Resolution**
- **Given**: Alert resolved
- **When**: Status changes to resolved
- **Then**: System MUST publish alert.resolved event
- **Includes**: resolution_note, resolved_by
- **Consumers**: notification_service, audit_service

---

### Query Rules (BR-QRY-001 to BR-QRY-010)

**BR-QRY-001: Time Range Requirement**
- **Given**: User queries telemetry data
- **When**: Query parameters provided
- **Then**: start_time and end_time MUST be provided
- **Validation**: Required fields
- **Error**: ValidationError("start_time and end_time required")

**BR-QRY-002: Time Range Order**
- **Given**: User queries telemetry data
- **When**: start_time and end_time provided
- **Then**: end_time MUST be > start_time
- **Error**: QueryError("end_time must be after start_time")

**BR-QRY-003: Time Range Maximum**
- **Given**: User queries telemetry data
- **When**: Time range exceeds 90 days
- **Then**: System MAY reject or paginate
- **Limit**: Configurable, default 90 days
- **Error**: QueryError("Time range exceeds maximum")

**BR-QRY-004: Metric Filter Requirement**
- **Given**: User queries telemetry data
- **When**: Query parameters provided
- **Then**: At least one metric_name MUST be specified
- **Error**: QueryError("At least one metric required")

**BR-QRY-005: Result Limit Enforcement**
- **Given**: User queries telemetry data
- **When**: Query returns large result set
- **Then**: Results MUST be limited to 10,000 points max
- **Default**: 1000 points
- **Pagination**: Use offset for more

**BR-QRY-006: Aggregation Interval Requirement**
- **Given**: User queries with aggregation
- **When**: aggregation type specified
- **Then**: interval MUST also be specified
- **Error**: QueryError("Aggregation requires interval")

**BR-QRY-007: Aggregation Type Values**
- **Given**: User queries with aggregation
- **When**: aggregation type specified
- **Then**: Type MUST be valid AggregationType enum
- **Valid**: avg, min, max, sum, count, median, p95, p99
- **Error**: QueryError("Unknown aggregation type")

**BR-QRY-008: Empty Results Handling**
- **Given**: User queries telemetry data
- **When**: No data matches criteria
- **Then**: Return empty array, not error
- **Response**: {data_points: [], count: 0}

**BR-QRY-009: Device Filtering**
- **Given**: User queries telemetry data
- **When**: device_ids provided
- **Then**: Results filtered to specified devices
- **Empty**: Query all accessible devices

**BR-QRY-010: Query Timeout**
- **Given**: User queries telemetry data
- **When**: Query execution time exceeds limit
- **Then**: Query MUST timeout after 30 seconds
- **Error**: QueryError("Query timeout exceeded")

---

### Real-Time Streaming Rules (BR-RTS-001 to BR-RTS-010)

**BR-RTS-001: Subscription Filter Requirement**
- **Given**: User creates real-time subscription
- **When**: Subscription parameters provided
- **Then**: At least one of device_ids OR metric_names required
- **Error**: SubscriptionError("At least one filter required")

**BR-RTS-002: Device List Limit**
- **Given**: User creates real-time subscription
- **When**: device_ids provided
- **Then**: Maximum 100 devices per subscription
- **Error**: ValidationError("Maximum 100 devices per subscription")

**BR-RTS-003: Metric List Limit**
- **Given**: User creates real-time subscription
- **When**: metric_names provided
- **Then**: Maximum 50 metrics per subscription
- **Error**: ValidationError("Maximum 50 metrics per subscription")

**BR-RTS-004: Frequency Throttling**
- **Given**: User creates real-time subscription
- **When**: max_frequency provided
- **Then**: max_frequency MUST be 100-10000 milliseconds
- **Default**: 1000ms (1 second)
- **Purpose**: Prevent client overload

**BR-RTS-005: Subscription ID Generation**
- **Given**: User creates real-time subscription
- **When**: Subscription created
- **Then**: System generates 32-char hex subscription_id
- **Method**: secrets.token_hex(16)
- **Use**: WebSocket connection and unsubscribe

**BR-RTS-006: WebSocket URL Format**
- **Given**: Subscription created
- **When**: Response returned
- **Then**: websocket_url MUST be /ws/telemetry/{subscription_id}
- **Full URL**: Client constructs from base URL

**BR-RTS-007: Connection Timeout**
- **Given**: Subscription created
- **When**: WebSocket not connected within 60 seconds
- **Then**: Subscription MAY be cleaned up
- **Idle**: Connections close after 5 minutes idle

**BR-RTS-008: In-Memory Storage**
- **Given**: Subscription created
- **When**: Server state checked
- **Then**: Subscriptions stored in memory only
- **Note**: Lost on server restart
- **Recovery**: Client must resubscribe

**BR-RTS-009: Filter Matching**
- **Given**: Data point ingested
- **When**: Checking subscriptions
- **Then**: Match device_id AND metric_name filters
- **Empty Filter**: Matches all for that dimension

**BR-RTS-010: Cleanup on Disconnect**
- **Given**: WebSocket connection closes
- **When**: Client disconnects or times out
- **Then**: Subscription MUST be removed immediately
- **Explicit**: DELETE endpoint also removes

---

### Authorization Rules (BR-AUTH-001 to BR-AUTH-005)

**BR-AUTH-001: Authentication Requirement**
- **Given**: API request received
- **When**: Accessing any endpoint except /health
- **Then**: Authentication MUST be provided
- **Methods**: JWT Bearer Token, API Key
- **Error**: 401 Unauthorized

**BR-AUTH-002: Internal Service Calls**
- **Given**: Service-to-service call
- **When**: X-Internal-Call: true header present
- **Then**: Authentication bypassed
- **Security**: Should be network-restricted
- **Use Case**: Trusted internal communication

**BR-AUTH-003: User Context Extraction**
- **Given**: Authenticated request
- **When**: Processing begins
- **Then**: user_id MUST be extracted from auth context
- **Use**: Audit trail, ownership tracking

**BR-AUTH-004: Rate Limiting (Future)**
- **Given**: API request received
- **When**: Rate limit exceeded
- **Then**: Return 429 Too Many Requests
- **Limits**: Per device (100 pts/sec), per user (1000 calls/hr)
- **Status**: Not yet implemented

**BR-AUTH-005: Health Endpoint Exception**
- **Given**: Request to /health or /health/detailed
- **When**: No authentication provided
- **Then**: Request MUST be allowed
- **Use Case**: Load balancer health checks

---

## State Machines

### 1. Alert Lifecycle State Machine

```
                    ┌─────────────────────────────────────────────────────┐
                    │                    ALERT LIFECYCLE                   │
                    └─────────────────────────────────────────────────────┘

                              ┌────────────────┐
          Alert Triggered     │                │
          ─────────────────►  │     ACTIVE     │
                              │                │
                              └───────┬────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    │ acknowledge()   │ resolve()       │ auto_resolve()
                    ▼                 │                 │
           ┌────────────────┐         │                 │
           │                │         │                 │
           │  ACKNOWLEDGED  │         │                 │
           │                │         │                 │
           └───────┬────────┘         │                 │
                   │                  │                 │
                   │ resolve()        │                 │
                   │                  │                 │
                   ▼                  ▼                 ▼
           ┌──────────────────────────────────────────────┐
           │                                              │
           │                  RESOLVED                    │
           │                                              │
           └──────────────────────────────────────────────┘

                              ┌────────────────┐
           Manual Suppression │                │
           ─────────────────► │   SUPPRESSED   │
           (maintenance)      │                │
                              └───────┬────────┘
                                      │ unsuppress()
                                      ▼
                              ┌────────────────┐
                              │     ACTIVE     │
                              └────────────────┘
```

**States**:
| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| ACTIVE | Alert fired, condition currently true | acknowledge, resolve, suppress |
| ACKNOWLEDGED | Someone investigating | resolve |
| RESOLVED | Issue fixed, alert closed (terminal) | none |
| SUPPRESSED | Temporarily muted (maintenance) | unsuppress |

**Transitions**:
| From | To | Trigger | Side Effects | Event |
|------|-----|---------|--------------|-------|
| ACTIVE | ACKNOWLEDGED | acknowledge(user, note) | acknowledged_by, acknowledged_at set | none |
| ACTIVE | RESOLVED | resolve(user, note) | resolved_by, resolved_at set | alert.resolved |
| ACTIVE | RESOLVED | auto_resolve() | resolved_by="system" | alert.resolved |
| ACTIVE | SUPPRESSED | suppress(user) | suppressed_by, suppressed_at set | none |
| ACKNOWLEDGED | RESOLVED | resolve(user, note) | resolved_by, resolved_at set | alert.resolved |
| SUPPRESSED | ACTIVE | unsuppress(user) | Clear suppression fields | none |

**Invariants**:
1. RESOLVED is terminal - no transitions out
2. Only ACTIVE alerts can be acknowledged
3. Both ACTIVE and ACKNOWLEDGED can be resolved
4. Auto-resolve only applies to ACTIVE alerts
5. All transitions record timestamp and actor

---

### 2. Alert Rule State Machine

```
                    ┌─────────────────────────────────────────────────────┐
                    │                ALERT RULE LIFECYCLE                  │
                    └─────────────────────────────────────────────────────┘

                              ┌────────────────┐
          Rule Created        │                │
          ─────────────────►  │    ENABLED     │ ◄───── enable()
                              │                │           │
                              └───────┬────────┘           │
                                      │                    │
                                      │ disable()          │
                                      ▼                    │
                              ┌────────────────┐           │
                              │                │───────────┘
                              │   DISABLED     │
                              │                │
                              └───────┬────────┘
                                      │
                                      │ delete()
                                      ▼
                              ┌────────────────┐
                              │                │
                              │    DELETED     │
                              │   (removed)    │
                              └────────────────┘
```

**States**:
| State | Description | Behavior |
|-------|-------------|----------|
| ENABLED | Rule active, evaluating data | Checks incoming data, triggers alerts |
| DISABLED | Rule paused, not evaluating | Ignored during data ingestion |
| DELETED | Rule removed | No longer exists in system |

**Transitions**:
| From | To | Trigger | Immediate | Event |
|------|-----|---------|-----------|-------|
| ENABLED | DISABLED | disable() | Stop evaluation | none |
| DISABLED | ENABLED | enable() | Start evaluation | none |
| ENABLED | DELETED | delete() | Remove from DB | none |
| DISABLED | DELETED | delete() | Remove from DB | none |

**Invariants**:
1. Only ENABLED rules participate in alert evaluation
2. Enable/disable is immediate (no queued evaluations)
3. Delete removes rule but keeps historical alerts
4. Default state on creation: ENABLED

---

### 3. Real-Time Subscription Lifecycle

```
                    ┌─────────────────────────────────────────────────────┐
                    │            SUBSCRIPTION LIFECYCLE                    │
                    └─────────────────────────────────────────────────────┘

                              ┌────────────────┐
          POST /subscribe     │                │
          ─────────────────►  │    CREATED     │
                              │  (in memory)   │
                              └───────┬────────┘
                                      │
                                      │ WebSocket connect
                                      ▼
                              ┌────────────────┐
                              │                │
                              │    ACTIVE      │ ◄───── Data pushed
                              │  (streaming)   │
                              └───────┬────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    │ disconnect      │ unsubscribe     │ idle_timeout
                    ▼                 ▼                 ▼
           ┌──────────────────────────────────────────────┐
           │                                              │
           │                  CLEANED UP                  │
           │              (removed from memory)           │
           └──────────────────────────────────────────────┘
```

**States**:
| State | Description | Behavior |
|-------|-------------|----------|
| CREATED | Subscription registered | Waiting for WebSocket connection |
| ACTIVE | WebSocket connected | Data pushed when matching |
| CLEANED UP | Subscription removed | No longer exists |

**Transitions**:
| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| CREATED | ACTIVE | WebSocket connect | Start pushing data |
| CREATED | CLEANED UP | Connection timeout (60s) | Remove from memory |
| ACTIVE | CLEANED UP | WebSocket disconnect | Remove from memory |
| ACTIVE | CLEANED UP | DELETE /subscribe/{id} | Close WebSocket, remove |
| ACTIVE | CLEANED UP | Idle timeout (5min) | Close WebSocket, remove |

**Invariants**:
1. Subscriptions are ephemeral (in-memory only)
2. Server restart loses all subscriptions
3. Client responsible for reconnection
4. One subscription = one WebSocket connection

---

### 4. Metric Definition Lifecycle

```
                    ┌─────────────────────────────────────────────────────┐
                    │              METRIC DEFINITION LIFECYCLE             │
                    └─────────────────────────────────────────────────────┘

                              ┌────────────────┐
          POST /metrics       │                │
          ─────────────────►  │    ACTIVE      │ ◄───── update()
                              │  (validates)   │
                              └───────┬────────┘
                                      │
                                      │ delete()
                                      ▼
                              ┌────────────────┐
                              │                │
                              │    DELETED     │
                              │  (soft delete) │
                              └────────────────┘
```

**States**:
| State | Description | Behavior |
|-------|-------------|----------|
| ACTIVE | Definition active | Validates incoming data against bounds |
| DELETED | Definition removed | New data for metric rejected |

**Invariants**:
1. data_type is immutable after creation
2. Delete does NOT cascade to telemetry data
3. Historical data retained per retention policy
4. Unique name constraint always enforced

---

## Edge Cases

### Input Validation Edge Cases

**EC-001: Empty String vs Null Metric Name**
- **Input**: metric_name = "" vs metric_name = null
- **Expected Behavior**:
  - Empty string: ValidationError("metric_name cannot be empty")
  - Null/missing: ValidationError("metric_name is required")
- **Implementation**: Pydantic Field(..., min_length=1)

**EC-002: Whitespace-Only Metric Name**
- **Input**: metric_name = "   " (only spaces)
- **Expected Behavior**: ValidationError("metric_name cannot be whitespace only")
- **Implementation**: Strip and check length > 0

**EC-003: Metric Name at Boundary**
- **Input**: metric_name = "x" * 100 (exactly max)
- **Expected Behavior**: Accept (100 chars allowed)
- **Input**: metric_name = "x" * 101 (max + 1)
- **Expected Behavior**: ValidationError("metric_name max 100 characters")

**EC-004: Unicode in Metric Names**
- **Input**: metric_name = "temp_\u6e29\u5ea6" (Chinese characters)
- **Expected Behavior**: Accept (valid UTF-8)
- **Note**: Character count, not byte count

**EC-005: Value Type Mismatch**
- **Input**: value = "hello" when metric data_type = numeric
- **Expected Behavior**:
  - If metric definition exists: TelemetryError("Value type mismatch")
  - If no definition: Accept (schema-free)
- **Implementation**: Check metric definition if exists

---

### Timestamp Edge Cases

**EC-006: Timestamp Exactly at Future Limit**
- **Input**: timestamp = now() + 5 minutes exactly
- **Expected Behavior**: Accept (boundary inclusive)
- **Input**: timestamp = now() + 5 minutes + 1 second
- **Expected Behavior**: ValidationError("Timestamp too far in future")

**EC-007: Timestamp at Retention Boundary**
- **Input**: timestamp = now() - 90 days exactly
- **Expected Behavior**: Accept (boundary inclusive)
- **Input**: timestamp = now() - 90 days - 1 second
- **Expected Behavior**: ValidationError("Timestamp exceeds retention")

**EC-008: Duplicate Timestamp (Upsert)**
- **Input**: Same (timestamp, device_id, metric_name) twice
- **Expected Behavior**: Second write overwrites first (upsert)
- **Implementation**: ON CONFLICT DO UPDATE

---

### Alert Evaluation Edge Cases

**EC-009: Alert Rule with Empty Device Filter**
- **Input**: Alert rule with device_ids = []
- **Expected Behavior**: Rule applies to ALL devices
- **Implementation**: Skip device filter check if empty

**EC-010: Threshold at Boundary Value**
- **Input**: condition = ">", threshold = 90, value = 90
- **Expected Behavior**: NO alert (90 is not > 90)
- **Input**: condition = ">=", threshold = 90, value = 90
- **Expected Behavior**: Alert triggered (90 >= 90)

**EC-011: Alert Already Active (Deduplication)**
- **Input**: Same rule triggers again while alert active
- **Expected Behavior**: NO new alert created (deduplicated)
- **Implementation**: Check for active alert before creating

**EC-012: Alert Rule Disabled During Evaluation**
- **Input**: Rule disabled while batch being processed
- **Expected Behavior**: Remaining evaluations skipped
- **Implementation**: Check enabled status per data point

---

### Concurrency Edge Cases

**EC-013: Concurrent Data Point Inserts**
- **Input**: Two simultaneous inserts with same key
- **Expected Behavior**: Both succeed (upsert), last-write-wins
- **Implementation**: PostgreSQL ON CONFLICT

**EC-014: Concurrent Alert Resolution**
- **Input**: Two users resolve same alert simultaneously
- **Expected Behavior**: First succeeds, second gets StateTransitionError
- **Implementation**: Check status before update

**EC-015: Subscription Cleanup Race**
- **Input**: Unsubscribe called while data being pushed
- **Expected Behavior**: Clean termination, no errors
- **Implementation**: Guard against missing subscription

---

### Integration Edge Cases

**EC-016: NATS Unavailable During Ingestion**
- **Input**: Data ingested while NATS down
- **Expected Behavior**:
  - Data still stored (ingestion succeeds)
  - Event publishing logged for retry
  - Alert evaluation continues
- **Implementation**: Async event publishing, don't block

**EC-017: Database Timeout During Query**
- **Input**: Complex query exceeds 30s timeout
- **Expected Behavior**: QueryError("Query timeout exceeded")
- **HTTP Status**: 504 Gateway Timeout

**EC-018: WebSocket Client Slow Consumer**
- **Input**: Client can't keep up with data rate
- **Expected Behavior**:
  - Rate limited by max_frequency
  - Buffer fills, oldest dropped
  - Connection may be closed if too slow
- **Implementation**: Server-side throttling

---

## Data Consistency Rules

**DC-001: Timestamp Normalization**
- All timestamps stored in UTC
- Millisecond precision supported
- Format: ISO 8601 with timezone
- Applied: Before storage, after retrieval

**DC-002: Metric Name Normalization**
- No case normalization (case-sensitive)
- Leading/trailing whitespace stripped
- Allows: alphanumeric, underscore, dot, dash
- Applied: Before validation

**DC-003: ID Format Consistency**
- device_id: Provided by client
- metric_id: `met_<uuid_hex[:12]>`
- rule_id: `rule_<uuid_hex[:12]>`
- alert_id: `alert_<uuid_hex[:12]>`
- subscription_id: `<hex_32>` (secrets.token_hex(16))

**DC-004: Value Type Routing**
- Numeric values → value_numeric column
- String values → value_string column
- Boolean values → value_boolean column
- JSON/dict values → value_json column
- Based on: Python type(value)

**DC-005: Timestamp Fields**
- created_at: Set on creation, immutable
- updated_at: Updated on every modification
- triggered_at: Set when alert fires
- resolved_at: Set when alert resolves
- All timestamps: UTC, ISO 8601

**DC-006: Soft Delete Pattern**
- Metric definitions: Physical delete
- Alert rules: Physical delete
- Alerts: Keep for audit (resolved status)
- Telemetry data: Retention-based cleanup

**DC-007: Quality Score Default**
- If quality not provided: Default to 100
- Quality 100 = trusted source
- Quality < 50 = unreliable, may be filtered
- Range: 0-100 integer

---

## Integration Contracts

### Device Service Integration

**Purpose**: Validate device existence (optional)

**Endpoint**: `GET /api/v1/devices/{device_id}`
**Header**: `X-Internal-Call: true`

**Success Response** (200):
```json
{
  "device_id": "device_abc123",
  "status": "active"
}
```

**Not Found Response** (404):
```json
{
  "detail": "Device not found"
}
```

**Error Handling**:
| Status | Action |
|--------|--------|
| 200 | Continue ingestion |
| 404 | Accept data anyway (device may be new) |
| 500 | Continue ingestion (graceful degradation) |
| Timeout | Continue ingestion |

**Note**: Device validation is optional for ingestion flexibility.

---

### Notification Service Integration

**Purpose**: Send alert notifications

**Event Subject**: `telemetry_service.alert.triggered`

**Event Payload**:
```json
{
  "event_id": "evt_uuid",
  "event_type": "alert.triggered",
  "timestamp": "2025-12-18T10:00:00Z",
  "source_service": "telemetry_service",
  "correlation_id": "corr_uuid",
  "alert_id": "alert_abc123",
  "rule_id": "rule_xyz789",
  "rule_name": "High CPU Usage",
  "device_id": "device_001",
  "metric_name": "cpu_usage",
  "level": "warning",
  "current_value": "95.5",
  "threshold_value": "90",
  "notification_channels": ["slack", "email"]
}
```

**Consumer Behavior**:
- notification_service subscribes to `telemetry_service.alert.*`
- Routes to channels specified in notification_channels
- Handles delivery failures internally

---

### Audit Service Integration

**Purpose**: Log telemetry operations and alerts

**Published Events**:
| Subject | When |
|---------|------|
| telemetry_service.telemetry.data.received | Data ingested |
| telemetry_service.metric.defined | Metric definition created |
| telemetry_service.alert.rule.created | Alert rule created |
| telemetry_service.alert.triggered | Alert fires |
| telemetry_service.alert.resolved | Alert resolved |

**Event Base Schema**:
```json
{
  "event_id": "uuid",
  "event_type": "telemetry.data.received",
  "timestamp": "ISO8601",
  "source_service": "telemetry_service",
  "correlation_id": "optional-uuid",
  "user_id": "user who triggered",
  "data": { ... }
}
```

---

### Account Service Integration

**Purpose**: Handle user deletion (GDPR compliance)

**Subscribed Event**: `account_service.user.deleted`

**Event Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "user.deleted",
  "user_id": "user_123",
  "timestamp": "2025-12-18T10:00:00Z"
}
```

**Handler Behavior**:
1. Disable alert rules created by user
2. Anonymize user references in alerts
3. Keep telemetry data (not user PII)
4. Log GDPR compliance action

---

### Event Publishing Contract

**NATS Connection**: `nats://isa-nats:4222`

**Subject Pattern**: `{service}.{entity}.{action}`

**Examples**:
- `telemetry_service.telemetry.data.received`
- `telemetry_service.metric.defined`
- `telemetry_service.alert.triggered`
- `telemetry_service.alert.resolved`

**Payload Structure**:
```json
{
  "event_id": "uuid",
  "event_type": "{entity}.{action}",
  "timestamp": "ISO8601",
  "source_service": "telemetry_service",
  "correlation_id": "optional-uuid",
  "data": {
    // Entity-specific data
  }
}
```

**Guarantees**:
- At-least-once delivery
- No ordering guarantee across subjects
- Consumer idempotency required

**Failure Handling**:
- Log failed publishes
- Continue processing (don't block)
- Background retry for critical events

---

## Error Handling Contracts

### HTTP Status Code Mapping

| Error Type | HTTP Status | Error Code | Description |
|------------|-------------|------------|-------------|
| ValidationError | 422 | VALIDATION_ERROR | Field validation failed |
| NotFoundError | 404 | NOT_FOUND | Resource not found |
| DuplicateError | 409 | DUPLICATE | Resource already exists |
| StateTransitionError | 400 | INVALID_STATE | Invalid state transition |
| TelemetryError | 400 | TELEMETRY_ERROR | Telemetry-specific error |
| MetricError | 400 | METRIC_ERROR | Metric definition error |
| AlertError | 400 | ALERT_ERROR | Alert rule error |
| QueryError | 400 | QUERY_ERROR | Query parameter error |
| SubscriptionError | 400 | SUBSCRIPTION_ERROR | Subscription error |
| AuthenticationError | 401 | UNAUTHORIZED | Missing/invalid auth |
| AuthorizationError | 403 | FORBIDDEN | Insufficient permissions |
| RateLimitError | 429 | RATE_LIMITED | Too many requests |
| ServiceUnavailable | 503 | SERVICE_UNAVAILABLE | Dependency unavailable |
| InternalError | 500 | INTERNAL_ERROR | Unexpected error |

---

### Error Response Format

**Standard Error Response**:
```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Validation failed",
  "detail": {
    "field": "metric_name",
    "value": "",
    "constraint": "min_length=1"
  },
  "status_code": 422
}
```

**Pydantic Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "metric_name"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "timestamp"],
      "msg": "invalid datetime format",
      "type": "value_error.datetime"
    }
  ]
}
```

**State Transition Error**:
```json
{
  "success": false,
  "error": "StateTransitionError",
  "message": "Cannot transition from resolved to acknowledged",
  "detail": {
    "current_state": "resolved",
    "target_state": "acknowledged",
    "allowed_transitions": []
  },
  "status_code": 400
}
```

**Not Found Error**:
```json
{
  "success": false,
  "error": "NotFoundError",
  "message": "Alert rule not found",
  "detail": {
    "resource_type": "AlertRule",
    "resource_id": "rule_xyz"
  },
  "status_code": 404
}
```

---

### Error Handling Principles

1. **Never expose internal details**: Stack traces only in logs, not responses
2. **Consistent format**: All errors follow same structure
3. **Actionable messages**: Tell user what to fix
4. **Request ID**: Include correlation_id for debugging
5. **Graceful degradation**: Partial failures don't block success
6. **Idempotent handling**: Same error for same invalid input

---

## Summary

| Category | Count |
|----------|-------|
| Business Rules | 50 |
| State Machines | 4 |
| Edge Cases | 18 |
| Data Consistency Rules | 7 |
| Integration Contracts | 5 |
| Error Types | 14 |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Telemetry Service Team
**Related Documents**:
- Domain Context: docs/domain/telemetry_service.md
- PRD: docs/prd/telemetry_service.md
- Design: docs/design/telemetry_service.md
- Data Contract: tests/contracts/telemetry_service/data_contract.py
- System Contract: tests/contracts/telemetry_service/system_contract.md
