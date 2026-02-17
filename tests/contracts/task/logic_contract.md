# Task Service - Logic Contract

## Business Rules (50 rules)

### Task Creation Rules (BR-CRT-001 to BR-CRT-010)

**BR-CRT-001: Task ID Generation**
- System MUST generate unique task_id using UUID format
- Format: `tsk_{uuid_hex_24}`
- Task ID is immutable after creation
- Error if collision detected (extremely rare): retry with new UUID

**BR-CRT-002: Task Name Validation**
- Name MUST be 1-255 characters
- Name MUST NOT be empty or whitespace only
- Leading/trailing whitespace is trimmed
- Error: "Task name must be 1-255 characters"

**BR-CRT-003: Task Type Validation**
- Task type MUST be from valid TaskType enum
- Valid types: daily_weather, daily_news, news_monitor, weather_alert, price_tracker, data_backup, todo, reminder, calendar_event, custom
- Task type is immutable after creation
- Error: "Invalid task type"

**BR-CRT-004: User ID Requirement**
- User ID MUST be provided (from JWT token)
- User ID MUST NOT be empty
- No foreign key constraint (cross-service reference)
- Error: "User ID is required"

**BR-CRT-005: Default Status**
- New tasks default to status=PENDING
- Status can be overridden to SCHEDULED if schedule provided
- Invalid initial statuses rejected (RUNNING, COMPLETED, FAILED)
- Example: create with schedule → status=SCHEDULED

**BR-CRT-006: Default Priority**
- Priority defaults to MEDIUM if not specified
- Valid priorities: low, medium, high, urgent
- Error: "Invalid priority level"

**BR-CRT-007: Credits Per Run Validation**
- Credits per run MUST be >= 0
- Stored as DOUBLE PRECISION
- Default: 0.0
- Error: "Credits per run cannot be negative"

**BR-CRT-008: Schedule Configuration**
- Schedule is optional
- If provided, MUST contain valid type (cron/interval)
- Cron expression validated against 5-field format
- Interval must be >= 1 minute
- Error: "Invalid schedule configuration"

**BR-CRT-009: Tags Normalization**
- Tags are trimmed of whitespace
- Empty strings removed from tags list
- Duplicate tags allowed (no deduplication)
- Tags stored as TEXT[] array

**BR-CRT-010: Event Publishing**
- task.created event published on successful creation
- Event includes: task_id, user_id, task_type, name
- Event publishing failure does not rollback creation
- Event is published asynchronously

### Task Update Rules (BR-UPD-001 to BR-UPD-010)

**BR-UPD-001: Owner Verification**
- Only task owner can update task
- Owner = user_id from JWT matches task.user_id
- Error: "Permission denied" (403)

**BR-UPD-002: Immutable Fields**
- task_id CANNOT be changed
- user_id CANNOT be changed
- task_type CANNOT be changed
- created_at CANNOT be changed
- Error: "Field cannot be modified"

**BR-UPD-003: Name Update Validation**
- Same validation as creation (1-255 chars, non-empty)
- Leading/trailing whitespace trimmed
- Error: "Task name must be 1-255 characters"

**BR-UPD-004: Status Transition Validation**
- Status changes must follow valid transitions
- Invalid transitions rejected
- See State Machine section for valid transitions
- Error: "Invalid status transition"

**BR-UPD-005: Updated Timestamp**
- updated_at automatically set to current UTC timestamp
- Cannot be manually overridden
- Precision: microseconds

**BR-UPD-006: Partial Updates**
- Only provided fields are updated
- Null values in request do not clear fields
- Empty strings clear string fields
- Empty dict {} clears JSONB fields

**BR-UPD-007: Deleted Task Update**
- Deleted tasks (deleted_at IS NOT NULL) cannot be updated
- Error: "Task not found" (404)

**BR-UPD-008: Schedule Update**
- Schedule update recalculates next_run_time
- Clearing schedule (null) clears next_run_time
- Status may change based on schedule presence

**BR-UPD-009: Event Publishing**
- task.updated event published on successful update
- Event includes: task_id, user_id, updated_fields[]
- Event publishing failure does not rollback update

**BR-UPD-010: Concurrent Update Handling**
- Last write wins (no optimistic locking)
- updated_at provides informal conflict detection
- Future: Consider optimistic locking with version field

### Task Deletion Rules (BR-DEL-001 to BR-DEL-005)

**BR-DEL-001: Soft Delete**
- Deletion sets deleted_at timestamp
- Data preserved for audit trail
- No hard deletes allowed

**BR-DEL-002: Owner Verification**
- Only task owner can delete task
- Error: "Permission denied" (403)

**BR-DEL-003: Already Deleted**
- Deleting already-deleted task returns success (idempotent)
- No error for double-delete
- deleted_at not updated on re-delete

**BR-DEL-004: Query Exclusion**
- Deleted tasks excluded from list/search queries
- Deleted tasks excluded from analytics
- Direct GET by ID returns 404 for deleted tasks

**BR-DEL-005: Event Publishing**
- task.deleted event published on successful deletion
- Event includes: task_id, user_id, deleted_at

### Task Execution Rules (BR-EXE-001 to BR-EXE-010)

**BR-EXE-001: Executable Status**
- Only tasks with status in [PENDING, SCHEDULED, PAUSED] can be executed
- RUNNING tasks cannot start new execution
- CANCELLED/DELETED tasks cannot execute
- Error: "Task cannot be executed in current state"

**BR-EXE-002: Execution Record Creation**
- Execution record created BEFORE execution starts
- Initial status: RUNNING
- started_at set to current timestamp

**BR-EXE-003: Credits Deduction**
- Credits consumed recorded in execution record
- Credits deducted only after successful completion
- Failed executions may consume partial credits (config-dependent)

**BR-EXE-004: Success Statistics Update**
- On success: run_count++, success_count++
- total_credits_consumed += credits_consumed
- last_run_time = now, last_success_time = now
- last_result = execution result

**BR-EXE-005: Failure Statistics Update**
- On failure: run_count++, failure_count++
- total_credits_consumed += credits_consumed (if any)
- last_run_time = now
- last_error = error message

**BR-EXE-006: Duration Tracking**
- Execution duration_ms = completed_at - started_at
- Stored in milliseconds as INTEGER
- Timeout enforced (default: 30 seconds)

**BR-EXE-007: Result Storage**
- Execution result stored as JSONB
- Result includes task-type-specific data
- Large results may be truncated

**BR-EXE-008: Error Handling**
- error_message: human-readable message
- error_details: structured JSONB with stack trace, context
- Sensitive data excluded from error details

**BR-EXE-009: Event Publishing**
- task.executed event published after completion
- Event includes: task_id, execution_id, status, credits_consumed
- Published for both success and failure

**BR-EXE-010: Concurrent Execution**
- Single task can have one active execution
- Concurrent execute requests queued or rejected
- Execution locking prevents race conditions

### Template Rules (BR-TPL-001 to BR-TPL-010)

**BR-TPL-001: Subscription Level Access**
- Templates filtered by required_subscription_level
- User can access templates at or below their tier
- Hierarchy: free < basic < pro < enterprise

**BR-TPL-002: Template Merging**
- User config merged with template default_config
- User config values override template defaults
- Required fields must be provided by user

**BR-TPL-003: Required Fields Validation**
- Required fields must be present in user config
- Missing required fields: Error 422
- Error: "Required field missing: {field}"

**BR-TPL-004: Active Templates Only**
- Only is_active=true templates returned in queries
- Inactive templates can be queried by ID (admin)
- Template activation is admin-only

**BR-TPL-005: Credits Inheritance**
- Task inherits credits_per_run from template
- User can override if allowed by template config
- Credits >= 0 enforced

**BR-TPL-006: Category Filtering**
- Templates filterable by category
- Valid categories: productivity, monitoring, alerts, calendar, custom
- Case-sensitive matching

**BR-TPL-007: Task Type Filtering**
- Templates filterable by task_type
- Must match valid TaskType enum
- Case-sensitive matching

**BR-TPL-008: Template Schema Validation**
- config_schema defines JSON Schema for validation
- User config validated against schema if present
- Schema validation errors returned as 422

**BR-TPL-009: Template Immutability**
- Template config not stored in task (only at creation time)
- Template changes do not affect existing tasks
- Task stores expanded config after merge

**BR-TPL-010: Template Discovery**
- Templates ordered by category, then name
- Subscription filtering applied server-side
- Client does not see higher-tier templates

### Analytics Rules (BR-ANA-001 to BR-ANA-005)

**BR-ANA-001: User Scope**
- Analytics scoped to authenticated user only
- No cross-user analytics via API
- Admin analytics via separate endpoints

**BR-ANA-002: Time Period**
- days parameter: 1-365 (default: 30)
- Calculations based on created_at/started_at
- Timezone: UTC

**BR-ANA-003: Success Rate Calculation**
- success_rate = (successful_executions / total_executions) * 100
- Returns 0 if total_executions = 0
- Rounded to 2 decimal places

**BR-ANA-004: Deleted Task Exclusion**
- Deleted tasks excluded from task counts
- Execution history included (even for deleted tasks)
- Analytics reflect historical accuracy

**BR-ANA-005: Performance Optimization**
- Analytics queries use aggregation functions
- Complex queries cached with short TTL (5 min)
- Stale data acceptable for analytics

---

## State Machines (4 machines)

### Task Lifecycle State Machine

```
States:
- PENDING: Task created, not yet scheduled
- SCHEDULED: Task queued for automatic execution
- RUNNING: Task currently executing
- COMPLETED: Task successfully completed (for non-recurring)
- FAILED: Task execution failed
- CANCELLED: Task permanently cancelled
- PAUSED: Task temporarily suspended

Transitions:
PENDING → SCHEDULED (schedule configured)
PENDING → RUNNING (manual execution)
PENDING → CANCELLED (user cancellation)
PENDING → PAUSED (user pause)

SCHEDULED → RUNNING (scheduler trigger or manual)
SCHEDULED → PAUSED (user pause)
SCHEDULED → CANCELLED (user cancellation)
SCHEDULED → PENDING (schedule removed)

RUNNING → COMPLETED (execution success, non-recurring)
RUNNING → SCHEDULED (execution success, recurring)
RUNNING → FAILED (execution failure)

COMPLETED → [terminal state]

FAILED → SCHEDULED (retry on schedule for recurring)
FAILED → PENDING (manual retry preparation)

PAUSED → SCHEDULED (user resume with schedule)
PAUSED → PENDING (user resume without schedule)
PAUSED → CANCELLED (user cancellation while paused)

CANCELLED → [terminal state]

Rules:
- CANCELLED and COMPLETED are terminal states
- RUNNING can only transition out via execution completion
- Schedule presence determines target state on resume
```

### Execution Status State Machine

```
States:
- RUNNING: Execution in progress
- COMPLETED: Execution finished successfully
- FAILED: Execution finished with error
- CANCELLED: Execution was cancelled/timed out

Transitions:
RUNNING → COMPLETED (success)
RUNNING → FAILED (error)
RUNNING → CANCELLED (timeout/cancellation)

COMPLETED → [terminal state]
FAILED → [terminal state]
CANCELLED → [terminal state]

Rules:
- All terminal states cannot transition
- RUNNING is the only entry point
- No execution can skip RUNNING state
```

### Subscription Access State Machine

```
States:
- FREE: Basic templates only
- BASIC: Free + Basic templates
- PRO: Free + Basic + Pro templates
- ENTERPRISE: All templates

Transitions:
FREE → BASIC (upgrade)
FREE → PRO (upgrade)
FREE → ENTERPRISE (upgrade)

BASIC → FREE (downgrade)
BASIC → PRO (upgrade)
BASIC → ENTERPRISE (upgrade)

PRO → FREE (downgrade)
PRO → BASIC (downgrade)
PRO → ENTERPRISE (upgrade)

ENTERPRISE → any (downgrade)

Rules:
- Subscription changes take effect immediately
- Existing tasks not affected by downgrade
- New task creation restricted by current tier
```

### Schedule Configuration State Machine

```
States:
- UNSCHEDULED: No schedule configured
- CRON_SCHEDULED: Cron expression schedule
- INTERVAL_SCHEDULED: Interval-based schedule

Transitions:
UNSCHEDULED → CRON_SCHEDULED (cron schedule added)
UNSCHEDULED → INTERVAL_SCHEDULED (interval schedule added)

CRON_SCHEDULED → UNSCHEDULED (schedule removed)
CRON_SCHEDULED → INTERVAL_SCHEDULED (schedule type changed)

INTERVAL_SCHEDULED → UNSCHEDULED (schedule removed)
INTERVAL_SCHEDULED → CRON_SCHEDULED (schedule type changed)

Rules:
- Only one schedule type active at a time
- Schedule removal sets next_run_time to NULL
- Schedule change recalculates next_run_time
```

---

## Edge Cases (15 cases)

**EC-001: Empty Task List**
- Input: User with no tasks
- Expected: Return empty list with count=0
- Actual: `{"tasks": [], "count": 0, "limit": 100, "offset": 0}`

**EC-002: Task with Maximum Name Length**
- Input: Name with exactly 255 characters
- Expected: Accept and store full name
- Actual: Task created successfully

**EC-003: Task with All Optional Fields Null**
- Input: Only required fields (name, task_type)
- Expected: Accept with defaults applied
- Actual: All optional fields have default values

**EC-004: Concurrent Task Creation**
- Input: Two requests creating tasks simultaneously
- Expected: Both tasks created with unique IDs
- Actual: No collision, both succeed

**EC-005: Execution During Task Update**
- Input: Execute task while another thread updates it
- Expected: Execution uses current state at start
- Actual: Execution completes, update reflected after

**EC-006: Delete During Execution**
- Input: Delete task while execution in progress
- Expected: Execution continues, task marked deleted after
- Actual: Running execution completes normally

**EC-007: Template with All Optional Fields**
- Input: Template providing all optional_fields
- Expected: User can override any optional field
- Actual: User config merged with template defaults

**EC-008: Analytics with No Executions**
- Input: User has tasks but no executions
- Expected: success_rate = 0, average_execution_time = 0
- Actual: Zero values for execution-based metrics

**EC-009: Past Due Date on Todo**
- Input: Todo task with due_date in the past
- Expected: Accept but may trigger overdue notification
- Actual: Task created, due_date stored as-is

**EC-010: Schedule Expression Edge Cases**
- Input: Cron "0 0 31 2 *" (Feb 31 doesn't exist)
- Expected: Valid cron syntax but never triggers
- Actual: Accepted, next_run_time calculation handles

**EC-011: Very Large Config Object**
- Input: Config with 1MB+ of data
- Expected: May hit size limits
- Actual: PostgreSQL JSONB handles, but API may reject

**EC-012: Special Characters in Task Name**
- Input: Name with unicode, emoji, special chars
- Expected: Accept all valid UTF-8 characters
- Actual: Task created with special characters preserved

**EC-013: Execution Timeout**
- Input: Task execution exceeds timeout (30s)
- Expected: Execution cancelled, status=CANCELLED
- Actual: timeout error recorded in error_details

**EC-014: Status Update Race Condition**
- Input: Two status updates at same millisecond
- Expected: One wins, no data corruption
- Actual: Last write wins, consistent state

**EC-015: Analytics Query Spanning No Data**
- Input: Analytics query with days=1, no recent data
- Expected: Return valid response with zeros
- Actual: All counts = 0, empty distributions

---

## Data Consistency Rules

**DC-001: Task ID Uniqueness**
- Enforced by UNIQUE constraint on task_id
- Application-level UUID generation
- Collision handling with retry

**DC-002: Execution ID Uniqueness**
- Enforced by UNIQUE constraint on execution_id
- Application-level UUID generation
- Collision handling with retry

**DC-003: Timestamp Consistency**
- All timestamps in UTC timezone
- created_at immutable after insert
- updated_at modified on every update
- deleted_at set once on soft delete

**DC-004: Statistics Integrity**
- run_count = success_count + failure_count
- total_credits_consumed = sum of execution credits
- Counters only increment, never decrement

**DC-005: Foreign Key References**
- task_id in executions references user_tasks.task_id
- No CASCADE delete (preserve execution history)
- Application enforces referential integrity

**DC-006: JSONB Field Normalization**
- Empty object {} stored as empty (not NULL)
- Nested objects preserved as-is
- No automatic key normalization

---

## Integration Contracts

### Account Service Integration
- **Endpoint**: Internal, via user_id from JWT
- **When**: Every authenticated request
- **Payload**: user_id extracted from token
- **Expected Response**: N/A (token contains claims)
- **Error Handling**: 401 if token invalid

### Notification Service Integration
- **Endpoint**: POST /api/v1/notifications
- **When**: Task reminder, execution result
- **Payload**:
  ```json
  {
    "recipient_id": "user_id",
    "notification_type": "task_reminder",
    "subject": "Task Reminder",
    "content": "...",
    "metadata": {"task_id": "..."}
  }
  ```
- **Expected Response**: 200 OK or 202 Accepted
- **Error Handling**: Log and continue (non-critical)

### Calendar Service Integration
- **Endpoint**: POST /api/v1/calendar/events
- **When**: Calendar event task type
- **Payload**:
  ```json
  {
    "user_id": "...",
    "title": "task name",
    "start_time": "ISO8601",
    "end_time": "ISO8601",
    "metadata": {"task_id": "..."}
  }
  ```
- **Expected Response**: 200 OK with event_id
- **Error Handling**: Retry once, then fail task creation

### Wallet Service Integration
- **Endpoint**: POST /api/v1/wallet/deduct
- **When**: Task execution completes
- **Payload**:
  ```json
  {
    "user_id": "...",
    "amount": 0.5,
    "description": "Task execution: task_name",
    "reference_type": "task_execution",
    "reference_id": "execution_id"
  }
  ```
- **Expected Response**: 200 OK
- **Error Handling**: Retry with exponential backoff

---

## Error Handling Contracts

### HTTP Status Code Mapping

| Error Type | HTTP Code | Response Body |
|------------|-----------|---------------|
| Task Not Found | 404 | `{"detail": "Task not found", "task_id": "..."}` |
| Validation Error | 422 | `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` |
| Permission Denied | 403 | `{"detail": "Permission denied", "action": "..."}` |
| Unauthorized | 401 | `{"detail": "Invalid or missing authentication"}` |
| Task Limit Exceeded | 429 | `{"detail": "Task limit exceeded", "limit_type": "..."}` |
| Invalid Status Transition | 400 | `{"detail": "Invalid status transition", "from": "...", "to": "..."}` |
| Template Not Found | 404 | `{"detail": "Template not found", "template_id": "..."}` |
| Subscription Level Required | 403 | `{"detail": "Subscription upgrade required", "required": "..."}` |
| Execution Timeout | 504 | `{"detail": "Task execution timed out", "timeout_ms": 30000}` |
| Internal Error | 500 | `{"detail": "Internal server error"}` |

### Error Response Format

```json
{
  "detail": "Human readable error message",
  "error_code": "ERROR_CODE_CONSTANT",
  "task_id": "tsk_...",
  "execution_id": "exe_...",
  "timestamp": "2025-12-17T10:00:00Z"
}
```

### Retry Behavior

| Operation | Retries | Backoff | Timeout |
|-----------|---------|---------|---------|
| Database query | 3 | Exponential (100ms, 200ms, 400ms) | 30s |
| Event publish | 0 | N/A | 5s |
| External API | 2 | Exponential (500ms, 1s) | 10s |
| Notification | 1 | 1s | 5s |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Task Service Team
