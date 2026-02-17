# Audit Service Logic Contract

**Business Rules and Specifications for Audit Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for audit service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)
7. [Performance SLAs](#performance-slas)

---

## Business Rules

### Audit Event Logging Rules

### BR-AUD-001: Required Action Field
**Given**: Audit event creation request
**When**: Event is created via log_event
**Then**:
- Action field MUST be non-empty string
- Action cannot be whitespace-only
- Maximum length: 255 characters
- Action describes what was done in human-readable form

**Validation Rules**:
- `action`: Required, min_length=1, max_length=255
- Strip whitespace, then check not empty
- Applied on both API and NATS event logging

**Edge Cases**:
- Empty action → **ValidationError("action cannot be empty")**
- Whitespace-only action → **ValidationError("action cannot be whitespace")**
- Action > 255 chars → **ValidationError("action max 255 characters")**

---

### BR-AUD-002: Valid Event Type
**Given**: Audit event creation request
**When**: event_type is validated
**Then**:
- Event type MUST be from EventType enum
- Invalid event type → **ValidationError**
- Case-sensitive matching

**Valid Event Types**:
```python
[
    "user_login", "user_logout", "user_register", "user_update", "user_delete",
    "permission_grant", "permission_revoke", "permission_update",
    "resource_create", "resource_update", "resource_delete", "resource_access",
    "organization_create", "organization_update", "organization_delete",
    "organization_join", "organization_leave",
    "system_error", "system_config_change",
    "security_alert", "security_violation",
    "compliance_check"
]
```

**Edge Cases**:
- "invalid_type" → **ValidationError("invalid event_type")**
- "USER_LOGIN" (uppercase) → **ValidationError** (case-sensitive)
- null/None → **ValidationError("event_type is required")**

---

### BR-AUD-003: Valid Category
**Given**: Audit event creation request
**When**: category is validated
**Then**:
- Category MUST be from AuditCategory enum
- Invalid category → **ValidationError**

**Valid Categories**:
```python
["authentication", "authorization", "data_access", "configuration",
 "security", "compliance", "system"]
```

**Default**: If not provided, determined from event_type pattern

---

### BR-AUD-004: Valid Severity
**Given**: Audit event creation request
**When**: severity is validated
**Then**:
- Severity MUST be from EventSeverity enum: low, medium, high, critical
- Default severity: `low`

**Validation Rules**:
- Valid values: "low", "medium", "high", "critical"
- Case-sensitive
- Default applied if not provided

---

### BR-AUD-005: Automatic Event ID Generation
**Given**: Audit event creation request
**When**: Event is created
**Then**:
- System generates unique event_id (UUID)
- Format: `audit_{uuid_hex}`
- ID is immutable after creation
- IDs are globally unique

**Implementation**:
```python
event_id = f"audit_{uuid.uuid4().hex}"
```

---

### BR-AUD-006: Automatic Timestamp Assignment
**Given**: Audit event creation request
**When**: timestamp not provided
**Then**:
- System sets timestamp to current UTC time
- Format: ISO 8601 with timezone
- created_at also set to current UTC time

**Implementation**:
```python
timestamp = datetime.now(timezone.utc)
created_at = datetime.now(timezone.utc)
```

---

### BR-AUD-007: Compliance Flag Assignment
**Given**: Audit event creation
**When**: Event is persisted
**Then**:
- GDPR flag applied for user deletion/update events
- SOX flag applied for resource/permission changes
- HIPAA flag applied for health-related resource access
- Flags stored in compliance_flags array

**Rules**:
| Event Type Pattern | Compliance Flag |
|-------------------|-----------------|
| user_delete, user_update | GDPR |
| resource_update, permission_* | SOX |
| resource_access (health context) | HIPAA |

---

### BR-AUD-008: Retention Policy Assignment
**Given**: Audit event creation
**When**: Event is persisted
**Then**:
- Retention policy based on category
- Security events: 7_years
- Authentication events: 3_years
- Other events: 1_year
- Policy applied at creation, immutable

**Retention Mapping**:
```python
{
    "security": "7_years",     # 2555 days
    "authentication": "3_years", # 1095 days
    "authorization": "3_years",
    "compliance": "7_years",
    "data_access": "1_year",   # 365 days
    "configuration": "1_year",
    "system": "1_year"
}
```

---

### BR-AUD-009: Event Immutability
**Given**: Audit event exists in database
**When**: Update or modification attempted
**Then**:
- System MUST reject updates
- Events cannot be modified after creation
- Only deletion via cleanup is allowed
- Ensures audit trail integrity

**Error**: **ImmutableRecordError("Audit events cannot be modified")**

---

### BR-AUD-010: Metadata Validation
**Given**: Audit event with metadata field
**When**: Metadata is validated
**Then**:
- Metadata MUST be valid JSON object or null
- Empty object {} is valid
- Stored as JSONB in PostgreSQL

**Edge Cases**:
- null → Stored as {}
- {} → Valid
- {"key": "value"} → Valid
- Invalid JSON → **ValidationError**

---

### Query Validation Rules

### BR-QRY-001: Query Limit Maximum
**Given**: Audit event query request
**When**: limit parameter is validated
**Then**:
- Limit MUST be between 1 and 1000
- Default: 100
- Limit > 1000 → **ValidationError**
- Limit <= 0 → **ValidationError**

**Validation Rules**:
- `limit`: ge=1, le=1000, default=100
- Error message: "Query limit cannot exceed 1000"

---

### BR-QRY-002: Query Offset Validation
**Given**: Audit event query request
**When**: offset parameter is validated
**Then**:
- Offset MUST be non-negative integer
- Default: 0
- Offset < 0 → **ValidationError**

**Validation Rules**:
- `offset`: ge=0, default=0
- Error message: "Offset must be non-negative"

---

### BR-QRY-003: Time Range Maximum
**Given**: Audit event query with time range
**When**: start_time and end_time are validated
**Then**:
- Time range MUST NOT exceed 365 days
- start_time MUST be before end_time
- Error if range > 365 days

**Validation Rules**:
- Check: `(end_time - start_time).days <= 365`
- Error: "Time range cannot exceed 365 days"

---

### BR-QRY-004: Time Order Validation
**Given**: Audit query with start_time and end_time
**When**: Times are validated
**Then**:
- start_time MUST be earlier than end_time
- Reversed times → **ValidationError**

**Error**: "start_time must be before end_time"

---

### BR-QRY-005: Query Result Ordering
**Given**: Audit event query executed
**When**: Results are returned
**Then**:
- Default order: timestamp DESC (newest first)
- Most recent events returned first
- Consistent ordering within pagination

---

### Batch Logging Rules

### BR-BAT-001: Batch Size Limit
**Given**: Batch audit event logging request
**When**: Batch size is validated
**Then**:
- Maximum 100 events per batch
- Empty batch → **ValidationError**
- Batch > 100 → **ValidationError**

**Validation Rules**:
- `events`: min_length=1, max_length=100
- Error: "Maximum 100 events per batch"

---

### BR-BAT-002: Partial Failure Handling
**Given**: Batch logging with mixed valid/invalid events
**When**: Batch is processed
**Then**:
- Valid events are logged successfully
- Invalid events are rejected with error details
- Returns summary: successful_count, failed_count
- Partial failures don't block successful events

**Response Structure**:
```json
{
    "successful_count": 8,
    "failed_count": 2,
    "results": [
        {"id": "audit_xxx", "success": true},
        {"error": "Invalid event_type", "success": false}
    ]
}
```

---

### BR-BAT-003: Batch Event Independence
**Given**: Multiple events in batch
**When**: Batch is processed
**Then**:
- Each event processed independently
- One event failure doesn't affect others
- All valid events persisted

---

### User Activity Rules

### BR-ACT-001: Activity Days Range
**Given**: User activity query
**When**: days parameter is validated
**Then**:
- Days MUST be between 1 and 365
- Default: 30 days
- Days outside range → **ValidationError**

**Validation Rules**:
- `days`: ge=1, le=365, default=30
- Error: "Days must be between 1 and 365"

---

### BR-ACT-002: Activity Limit
**Given**: User activity query
**When**: limit parameter is validated
**Then**:
- Limit MUST be between 1 and 1000
- Default: 100 activities

---

### BR-ACT-003: Activity Summary Calculation
**Given**: User activity summary request
**When**: Summary is generated
**Then**:
- total_activities: Count of all activities in period
- success_count: Count where status = SUCCESS
- failure_count: Count where status = FAILURE
- last_activity: Most recent activity timestamp
- most_common_activities: Top N activity types

**Calculation**:
```python
{
    "total_activities": count(*),
    "success_count": count(status='success'),
    "failure_count": count(status='failure'),
    "last_activity": max(timestamp),
    "most_common_activities": group by action, count desc limit 5
}
```

---

### BR-ACT-004: Risk Score Calculation
**Given**: User activity summary request
**When**: Risk score is calculated
**Then**:
- Risk score: 0-100 based on activity patterns
- Factors: failure rate, unusual activities, security events
- Higher score = higher risk

**Risk Thresholds**:
```python
{
    "low": 0-30,
    "medium": 31-60,
    "high": 61-80,
    "critical": 81-100
}
```

---

### Security Alert Rules

### BR-SEC-001: Required Severity
**Given**: Security alert creation request
**When**: Alert is created
**Then**:
- Severity MUST be specified
- Typically HIGH or CRITICAL for alerts
- Error if severity missing

---

### BR-SEC-002: Threat Level Calculation
**Given**: Security alert with severity
**When**: Alert is created
**Then**:
- Threat level calculated from severity
- high severity → threat_level = "high"
- critical severity → threat_level = "critical"
- medium severity → threat_level = "medium"
- low severity → threat_level = "low"

---

### BR-SEC-003: Investigation Status Default
**Given**: New security alert created
**When**: Alert is persisted
**Then**:
- investigation_status = "open" (default)
- detected_at = current timestamp
- resolved_at = null

---

### BR-SEC-004: High Severity Logging
**Given**: Security alert with HIGH or CRITICAL severity
**When**: Alert is created
**Then**:
- System logs warning message
- Warning includes: threat_type, source_ip, description
- Enables alerting integration

---

### BR-SEC-005: Security Event Query Days
**Given**: Security event query
**When**: days parameter is validated
**Then**:
- Days MUST be between 1 and 90
- Default: 7 days
- Security events typically queried short-term

---

### Compliance Reporting Rules

### BR-COM-001: Supported Standards
**Given**: Compliance report request
**When**: compliance_standard is validated
**Then**:
- Standard MUST be: GDPR, SOX, or HIPAA
- Unsupported standard → **ValidationError**

**Supported Standards**:
```python
{
    "GDPR": {
        "retention_days": 2555,  # 7 years
        "required_fields": ["user_id", "action", "timestamp", "ip_address"],
        "sensitive_events": ["user_delete", "user_update"]
    },
    "SOX": {
        "retention_days": 2555,
        "required_fields": ["user_id", "action", "timestamp"],
        "sensitive_events": ["resource_update", "permission_update"]
    },
    "HIPAA": {
        "retention_days": 2190,  # 6 years
        "required_fields": ["user_id", "action", "timestamp", "resource_type"],
        "sensitive_events": ["resource_access", "user_update"]
    }
}
```

---

### BR-COM-002: Period Validation
**Given**: Compliance report request
**When**: period_start and period_end are validated
**Then**:
- period_end MUST be after period_start
- Reversed dates → **ValidationError**

---

### BR-COM-003: Compliance Score Calculation
**Given**: Compliance report generation
**When**: Score is calculated
**Then**:
- Formula: (compliant_events / total_events) * 100
- Score range: 0-100
- Compliant = has all required fields, sensitive events have justification

**Implementation**:
```python
compliance_score = (compliant_events / total_events) * 100 if total_events > 0 else 100.0
```

---

### BR-COM-004: Risk Level Assessment
**Given**: Compliance report with score
**When**: Risk level is assessed
**Then**:
- Score < 80 → risk_level = "high"
- Score 80-89 → risk_level = "medium"
- Score >= 90 → risk_level = "low"

---

### BR-COM-005: Required Fields Check
**Given**: Event analyzed for compliance
**When**: Required fields checked
**Then**:
- Check all required_fields are present and non-null
- Missing required field → event marked non-compliant
- Record in findings list

---

### BR-COM-006: Sensitive Event Justification
**Given**: Sensitive event for compliance standard
**When**: Event analyzed
**Then**:
- Sensitive events SHOULD have justification in metadata
- Missing justification → finding recorded
- Not necessarily non-compliant, but flagged

---

### Event Processing Rules (NATS)

### BR-EVT-001: Wildcard Subscription
**Given**: Audit service starts
**When**: NATS connection established
**Then**:
- Subscribe to pattern `*.*` (all events)
- Capture ALL events from ALL services
- Universal audit coverage

---

### BR-EVT-002: Event Type Mapping
**Given**: NATS event received
**When**: Event is processed
**Then**:
- Map NATS event type to audit EventType
- Determine category based on event source
- Assign severity based on event patterns

**Mapping Rules**:
| NATS Pattern | Audit EventType | Category |
|-------------|-----------------|----------|
| user.created | USER_REGISTER | AUTHENTICATION |
| user.logged_in | USER_LOGIN | AUTHENTICATION |
| user.deleted | USER_DELETE | AUTHENTICATION |
| organization.* | ORGANIZATION_* | AUTHORIZATION |
| file.shared | PERMISSION_GRANT | AUTHORIZATION |
| device.* | RESOURCE_* | DATA_ACCESS |
| payment.* | RESOURCE_UPDATE | CONFIGURATION |

---

### BR-EVT-003: Severity Classification
**Given**: NATS event being mapped
**When**: Severity is determined
**Then**:
- HIGH: Events containing "deleted", "removed", "failed", "offline"
- MEDIUM: Events containing "updated", "shared", "member_added"
- LOW: All other events

---

### BR-EVT-004: Idempotent Event Processing
**Given**: NATS event received
**When**: Event ID already processed
**Then**:
- Skip processing (no duplicate audit entry)
- Log debug message for traceability
- Return without error

**Implementation**:
```python
if event.id in self.processed_event_ids:
    logger.debug(f"Event {event.id} already processed, skipping")
    return
```

---

### BR-EVT-005: Processed Event Cache Management
**Given**: Events being processed
**When**: Cache size exceeds limit
**Then**:
- Limit cache to 10,000 entries
- Remove oldest entries when limit exceeded
- Prevent memory overflow

**Implementation**:
```python
if len(self.processed_event_ids) > 10000:
    self.processed_event_ids = set(list(self.processed_event_ids)[5000:])
```

---

### BR-EVT-006: User ID Extraction
**Given**: NATS event with user context
**When**: user_id is extracted
**Then**:
- Check event.data["user_id"] first
- Fallback to event.data["shared_by"]
- Default to "system" if not found

---

### BR-EVT-007: Resource Info Extraction
**Given**: NATS event with resource context
**When**: Resource info is extracted
**Then**:
- Extract resource_type from event type prefix
- Extract resource_id from event data
- Extract resource_name if available

---

### Data Cleanup Rules

### BR-CLN-001: Retention Days Validation
**Given**: Data cleanup request
**When**: retention_days is validated
**Then**:
- Minimum: 30 days (prevent accidental data loss)
- Maximum: 2555 days (7 years)
- Default: 365 days

---

### BR-CLN-002: Cleanup Execution
**Given**: Valid cleanup request
**When**: Cleanup is executed
**Then**:
- Delete events older than cutoff date
- Cutoff = now - retention_days
- Respect compliance retention policies (don't delete if required)
- Return count of deleted events

---

### BR-CLN-003: Admin Authorization
**Given**: Cleanup endpoint accessed
**When**: Authorization checked
**Then**:
- MUST have admin privileges
- Regular users cannot trigger cleanup
- Log cleanup operation for audit trail

---

---

## State Machines

### 1. Security Event Investigation State Machine

```
                    ┌─────────────┐
                    │    OPEN     │◄────────────────────────┐
                    └──────┬──────┘                         │
                           │ investigate()                  │
                           ▼                                │
                    ┌─────────────┐                         │
          ┌─────────│INVESTIGATING│─────────┐               │
          │         └─────────────┘         │               │
          │                                 │               │
          │ resolve()                       │ determine_    │
          │                                 │ false_positive│
          ▼                                 ▼               │
┌─────────────┐                    ┌─────────────────┐      │
│  RESOLVED   │                    │ FALSE_POSITIVE  │      │
└─────────────┘                    └─────────────────┘      │
                                           │                │
                                           │ reopen()       │
                                           └────────────────┘
```

**States**:
| State | Description | Allowed Actions |
|-------|-------------|-----------------|
| OPEN | New security event, awaiting investigation | investigate |
| INVESTIGATING | Analyst reviewing the event | resolve, mark_false_positive |
| RESOLVED | Security event confirmed and handled | none (terminal) |
| FALSE_POSITIVE | Event determined to be non-threat | reopen |

**Transitions**:
| From | To | Trigger | Conditions | Event Published |
|------|-----|---------|------------|-----------------|
| OPEN | INVESTIGATING | investigate() | Analyst assigned | security.investigating |
| INVESTIGATING | RESOLVED | resolve() | Root cause identified | security.resolved |
| INVESTIGATING | FALSE_POSITIVE | determine_false_positive() | No actual threat | security.false_positive |
| FALSE_POSITIVE | OPEN | reopen() | New evidence found | security.reopened |

**Invariants**:
1. RESOLVED is terminal - no transitions out
2. State changes update investigation_status field
3. Timestamps recorded: detected_at, resolved_at
4. All transitions logged in audit trail

---

### 2. Compliance Report State Machine

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   DRAFT     │────►│    FINAL    │────►│  PUBLISHED  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       │ cancel()          │ archive()
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  CANCELLED  │     │  ARCHIVED   │
└─────────────┘     └─────────────┘
```

**States**:
| State | Description | Allowed Actions |
|-------|-------------|-----------------|
| DRAFT | Report being generated/reviewed | finalize, cancel |
| FINAL | Report complete, ready for publishing | publish, archive |
| PUBLISHED | Report shared with auditors | archive |
| CANCELLED | Report generation cancelled | none |
| ARCHIVED | Report stored for historical reference | none |

**Transitions**:
| From | To | Trigger | Conditions |
|------|-----|---------|------------|
| DRAFT | FINAL | finalize() | All sections complete |
| DRAFT | CANCELLED | cancel() | User cancels |
| FINAL | PUBLISHED | publish() | Approved by compliance officer |
| FINAL | ARCHIVED | archive() | Superseded by newer report |
| PUBLISHED | ARCHIVED | archive() | Retention period passed |

---

### 3. Audit Event Lifecycle State Machine

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RECEIVED   │────►│  VALIDATED  │────►│  PERSISTED  │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
                           │ validation_failed │ retention_expired
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  REJECTED   │     │   DELETED   │
                    └─────────────┘     └─────────────┘
```

**States**:
| State | Description |
|-------|-------------|
| RECEIVED | Event received from API or NATS |
| VALIDATED | Event passed all validation rules |
| PERSISTED | Event stored in database |
| REJECTED | Event failed validation |
| DELETED | Event removed after retention period |

**Invariants**:
1. Events are immutable once PERSISTED
2. REJECTED events logged for debugging
3. DELETED only via automated cleanup
4. No manual state transitions allowed

---

### 4. Real-Time Analysis State Machine

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   QUEUED    │────►│  ANALYZING      │────►│  COMPLETED  │
└─────────────┘     └────────┬────────┘     └─────────────┘
                             │
                             │ anomaly_detected
                             ▼
                      ┌─────────────┐
                      │  ALERTED    │
                      └─────────────┘
```

**States**:
| State | Description |
|-------|-------------|
| QUEUED | High-severity event awaiting analysis |
| ANALYZING | Pattern matching and anomaly detection |
| COMPLETED | Analysis finished, no issues found |
| ALERTED | Anomaly detected, security alert created |

---

## Edge Cases

### Input Validation Edge Cases

**EC-001: Empty String vs Null Action**
- **Input**: action = "" vs action = null
- **Expected Behavior**:
  - Empty string: **ValidationError("action cannot be empty")**
  - Null: **ValidationError("action is required")**
- **Implementation**: Separate validators for required vs non-empty

---

**EC-002: Whitespace-Only Action**
- **Input**: action = "   " (only spaces)
- **Expected Behavior**: **ValidationError("action cannot be whitespace only")**
- **Implementation**: Strip and check length > 0

---

**EC-003: Maximum Length Boundary**
- **Input**: action = "x" * 255 (exactly max)
- **Expected Behavior**: Accept (255 chars allowed)
- **Input**: action = "x" * 256 (max + 1)
- **Expected Behavior**: **ValidationError("action max 255 characters")**

---

**EC-004: Unicode Characters in Action**
- **Input**: action = "User action 中文 \u4e2d\u6587"
- **Expected Behavior**: Accept (valid UTF-8)
- **Note**: Count characters, not bytes

---

**EC-005: Special Characters in Action**
- **Input**: action = "Action!@#$%^&*() test"
- **Expected Behavior**: Accept (special chars allowed)
- **Note**: No character restrictions beyond length

---

### Query Edge Cases

**EC-006: Empty Filter Arrays**
- **Input**: event_types = [], categories = []
- **Expected Behavior**: No filtering applied (return all)
- **Implementation**: Skip filter if array empty

---

**EC-007: Query Limit at Boundary**
- **Input**: limit = 1000 (max)
- **Expected Behavior**: Accept, return up to 1000 results
- **Input**: limit = 1001
- **Expected Behavior**: **ValidationError("limit cannot exceed 1000")**

---

**EC-008: Time Range at Boundary**
- **Input**: 365-day range (exactly max)
- **Expected Behavior**: Accept
- **Input**: 366-day range
- **Expected Behavior**: **ValidationError("Time range cannot exceed 365 days")**

---

**EC-009: Offset Larger Than Total**
- **Input**: offset = 10000 when total_count = 100
- **Expected Behavior**: Return empty results, total_count = 100
- **Note**: Valid query, just no results at that offset

---

### Concurrency Edge Cases

**EC-010: Concurrent Audit Event Creation**
- **Input**: Multiple simultaneous events with different IDs
- **Expected Behavior**: All events created successfully
- **Implementation**: UUID generation ensures uniqueness

---

**EC-011: Duplicate NATS Event Processing**
- **Input**: Same NATS event delivered twice (redelivery)
- **Expected Behavior**: Second event skipped (idempotent)
- **Implementation**: Check processed_event_ids cache

---

**EC-012: Cache Overflow**
- **Input**: 10,001+ unique events processed
- **Expected Behavior**: Oldest 5,000 entries pruned
- **Note**: May result in reprocessing very old events (acceptable)

---

### Security Alert Edge Cases

**EC-013: Security Alert Without Source IP**
- **Input**: Security alert with source_ip = null
- **Expected Behavior**: Accept (source_ip optional)
- **Note**: Some security events may not have IP context

---

**EC-014: Rapid Security Alerts**
- **Input**: Multiple alerts in quick succession
- **Expected Behavior**: All alerts created, each with unique ID
- **Consideration**: May indicate ongoing attack pattern

---

### Compliance Edge Cases

**EC-015: Empty Period (No Events)**
- **Input**: Compliance report for period with zero events
- **Expected Behavior**:
  - total_events = 0
  - compliance_score = 100 (no violations if no events)
  - findings = []

---

**EC-016: All Events Non-Compliant**
- **Input**: Period where all events missing required fields
- **Expected Behavior**:
  - compliance_score = 0
  - risk_level = "high"
  - findings list all non-compliant events

---

---

## Data Consistency Rules

### DC-001: Event ID Format Consistency
- **Format**: `audit_{uuid_hex}` (lowercase)
- **Example**: `audit_a1b2c3d4e5f6789012345678`
- **Generated**: Server-side only
- **Immutable**: After creation, never changes

---

### DC-002: Timestamp Consistency
- **Timezone**: All timestamps stored in UTC
- **Format**: ISO 8601 with timezone info
- **Fields**:
  - `timestamp`: When event occurred (can be provided)
  - `created_at`: When record created (system-generated)
- **Immutable**: created_at never changes

---

### DC-003: Event Type Lowercase
- **Rule**: All event_type values stored lowercase
- **Example**: "user_login" not "USER_LOGIN"
- **Enforcement**: Enum validation ensures consistency

---

### DC-004: Category Lowercase
- **Rule**: All category values stored lowercase
- **Example**: "authentication" not "AUTHENTICATION"
- **Enforcement**: Enum validation

---

### DC-005: Severity Lowercase
- **Rule**: All severity values stored lowercase
- **Example**: "high" not "HIGH"
- **Enforcement**: Enum validation

---

### DC-006: Status Consistency
- **Values**: "success", "failure", "pending", "error"
- **Default**: "success"
- **Derived**: From request.success boolean

---

### DC-007: Metadata JSON Normalization
- **Rule**: Empty metadata stored as {} not null
- **Encoding**: JSON/JSONB
- **Nested**: Arbitrary depth supported

---

### DC-008: Compliance Flags Array
- **Format**: Array of uppercase strings
- **Values**: ["GDPR", "SOX", "HIPAA"]
- **Default**: Empty array []

---

### DC-009: Tags Array Consistency
- **Format**: Array of lowercase strings
- **Example**: ["security", "authentication", "user"]
- **Duplicate**: Allowed but discouraged
- **Empty**: [] allowed

---

### DC-010: Retention Policy Values
- **Values**: "1_year", "3_years", "7_years"
- **Default**: Based on category
- **Immutable**: Set at creation

---

---

## Integration Contracts

### NATS Event Subscription Contract

**Subscription Pattern**: `*.*`
**Purpose**: Capture all events from all services

**Expected Event Format**:
```json
{
  "id": "uuid",
  "type": "service.action",
  "source": "service_name",
  "timestamp": "ISO8601",
  "data": {
    "user_id": "optional",
    "...": "event-specific fields"
  }
}
```

**Processing Contract**:
| Received Field | Mapped To | Fallback |
|----------------|-----------|----------|
| id | metadata.nats_event_id | Generate new |
| type | action | Required |
| source | metadata.nats_event_source | "unknown" |
| data.user_id | user_id | "system" |

---

### PostgreSQL gRPC Contract

**Service**: `postgres_grpc_service`
**Default Host**: `isa-postgres-grpc`
**Default Port**: `50061`

**Discovery**:
```python
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061
)
```

**Operations**:
| Operation | Method | Expected Latency |
|-----------|--------|-----------------|
| Insert Event | execute() | < 50ms |
| Query Events | query() | < 200ms |
| Delete Events | execute() | < 500ms |

---

### Consul Service Registration Contract

**Service Name**: `audit_service`
**Port**: `8204`

**Registration Metadata**:
```json
{
  "service_name": "audit_service",
  "port": 8204,
  "tags": ["v1", "governance-microservice", "audit", "compliance"],
  "meta": {
    "version": "1.0.0",
    "route_count": "15",
    "base_path": "/api/v1/audit"
  }
}
```

**Health Check**:
- **Path**: `/health`
- **Method**: HTTP GET
- **Interval**: 30 seconds
- **Timeout**: 5 seconds

---

### Event Publishing Contract (audit.event_recorded)

**Subject**: `audit.event_recorded`
**When**: Critical audit event recorded (high/critical severity)

**Payload Schema**:
```json
{
  "event_id": "audit_uuid",
  "event_type": "string",
  "category": "string",
  "severity": "high|critical",
  "user_id": "string|null",
  "action": "string",
  "success": "boolean",
  "recorded_at": "ISO8601"
}
```

**Guarantees**:
- At-least-once delivery
- Non-blocking (fire-and-forget)
- Failure logged but doesn't block operation

---

---

## Error Handling Contracts

### HTTP Status Code Mapping

| Error Type | HTTP Status | Error Code | Description |
|------------|-------------|------------|-------------|
| ValidationError | 422 | VALIDATION_ERROR | Input validation failed |
| NotFoundError | 404 | NOT_FOUND | Resource not found |
| AuthenticationError | 401 | UNAUTHORIZED | Missing/invalid auth |
| AuthorizationError | 403 | FORBIDDEN | Insufficient permissions |
| RateLimitError | 429 | RATE_LIMITED | Too many requests |
| ServiceUnavailable | 503 | SERVICE_UNAVAILABLE | Dependency down |
| InternalError | 500 | INTERNAL_ERROR | Unexpected server error |
| ImmutableRecordError | 400 | IMMUTABLE_RECORD | Cannot modify audit event |
| InvalidStateTransition | 400 | INVALID_STATE | Invalid state change |

---

### Error Response Format

**Standard Error**:
```json
{
  "detail": "Human-readable error message"
}
```

**Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "action"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

### Validation Error Details

**Missing Required Field**:
```json
{
  "detail": [
    {
      "loc": ["body", "event_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Invalid Enum Value**:
```json
{
  "detail": [
    {
      "loc": ["body", "severity"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

**Limit Exceeded**:
```json
{
  "detail": "Query limit cannot exceed 1000"
}
```

---

### Service Unavailable Handling

**Database Unavailable**:
```json
{
  "detail": "Database connection unavailable"
}
```
- **Status**: 503
- **Retry-After**: 30 seconds suggested

**NATS Unavailable**:
- Event logging continues without publishing
- Events marked for retry publishing
- No user-facing error (graceful degradation)

---

---

## Performance SLAs

### Response Time Targets

| Operation | Target (p95) | Max Acceptable |
|-----------|--------------|----------------|
| Log Single Event | < 200ms | 500ms |
| Batch Log (100 events) | < 500ms | 1000ms |
| Query Events (100 results) | < 200ms | 500ms |
| User Activities | < 200ms | 500ms |
| User Activity Summary | < 150ms | 300ms |
| Security Alert Creation | < 100ms | 200ms |
| Security Event List | < 150ms | 300ms |
| Compliance Report | < 30s | 60s |
| Health Check | < 50ms | 100ms |
| Data Cleanup | < 60s | 120s |

---

### Throughput Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Event Ingestion | > 1000 events/sec | Via API |
| NATS Processing | > 5000 events/sec | Wildcard subscription |
| Concurrent Queries | 500 simultaneous | Query endpoints |
| Compliance Reports | 10 concurrent | Report generation |

---

### Availability Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Service Uptime | 99.99% | Monthly |
| Database Connectivity | 99.99% | Continuous |
| Event Bus Connectivity | 99.99% | Continuous |
| Successful Event Logging | 99.9% | Daily |

---

### Data Retention Targets

| Category | Retention Period | Compliance Requirement |
|----------|------------------|----------------------|
| Security Events | 7 years | SOX, GDPR, HIPAA |
| Authentication Events | 3 years | GDPR |
| Authorization Events | 3 years | SOX |
| Compliance Events | 7 years | All standards |
| General Events | 1 year | Internal policy |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-22
**Maintained By**: Security & Compliance Engineering Team
**Related Documents**:
- Domain Context: docs/domain/audit_service.md
- PRD: docs/prd/audit_service.md
- Design: docs/design/audit_service.md
- Data Contract: tests/contracts/audit_service/data_contract.py
- System Contract: tests/contracts/audit_service/system_contract.md
