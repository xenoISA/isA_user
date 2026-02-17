# Session Service - Logic Contract

## Business Rules (50 rules)

### Session Creation Rules (BR-SES-001 to BR-SES-010)

**BR-SES-001: User ID Required**
- Session MUST have a user_id
- System validates user_id is non-empty string
- Error returned if violated: "user_id is required"
- Example: `{"user_id": ""}` -> 400 Bad Request

**BR-SES-002: User ID Format**
- User ID MUST be 1-50 characters
- System trims whitespace before validation
- Whitespace-only strings are rejected
- Example: `{"user_id": "   "}` -> 400 Bad Request

**BR-SES-003: Session ID Auto-Generation**
- Session ID auto-generated if not provided
- Generated as UUID: `sess_{uuid.uuid4().hex[:24]}`
- Example: `sess_a1b2c3d4e5f6g7h8i9j0k1l2`

**BR-SES-004: Custom Session ID**
- Client MAY provide custom session_id
- Custom ID MUST be non-empty if provided
- Empty string session_id rejected
- Example: `{"session_id": "my-custom-id"}` -> accepted

**BR-SES-005: Default Session Status**
- New sessions have status = "active"
- New sessions have is_active = true
- Status set automatically on creation

**BR-SES-006: Default Session Metrics**
- message_count initialized to 0
- total_tokens initialized to 0
- total_cost initialized to 0.0
- session_summary initialized to empty string

**BR-SES-007: Session Timestamps**
- created_at set to current UTC timestamp
- updated_at set to current UTC timestamp
- last_activity set to current UTC timestamp

**BR-SES-008: Conversation Data Optional**
- conversation_data is optional JSONB field
- Defaults to empty object `{}`
- Accepts any valid JSON structure

**BR-SES-009: Session Metadata Optional**
- metadata is optional JSONB field
- Defaults to empty object `{}`
- Typical fields: platform, client_version

**BR-SES-010: Account Validation Fail-Open**
- Account service check is best-effort
- If account service unavailable, session creation proceeds
- Warning logged for potential non-existent user
- Ensures service resilience

### Session Access Rules (BR-ACC-001 to BR-ACC-008)

**BR-ACC-001: Session Ownership**
- Sessions belong to a single user (user_id)
- Only session owner can access session data
- user_id parameter used for authorization

**BR-ACC-002: Session Not Found Response**
- 404 returned for both:
  - Session does not exist
  - Session exists but user_id doesn't match
- No information leak about session existence

**BR-ACC-003: Inactive Session Read Access**
- Ended/expired sessions can still be read
- Only write operations blocked for inactive sessions
- Enables historical conversation review

**BR-ACC-004: Session Query Authorization**
- GET /api/v1/sessions requires user_id parameter
- Only sessions matching user_id returned
- Cannot query other users' sessions

**BR-ACC-005: Session Modify Authorization**
- PUT/DELETE require user ownership validation
- user_id query parameter checked against session owner
- Unauthorized access returns 404 (not 403)

**BR-ACC-006: Message Access Authorization**
- Messages inherit session authorization
- Must validate session ownership before message access
- Same 404 response for unauthorized access

**BR-ACC-007: Internal Service Access**
- X-Internal-Call header bypasses user auth
- Used for service-to-service communication
- Gateway validates for external requests

**BR-ACC-008: Summary Access Authorization**
- Session summary follows same auth rules
- user_id parameter required for verification
- Returns 404 for unauthorized access

### Message Rules (BR-MSG-001 to BR-MSG-012)

**BR-MSG-001: Session Existence Required**
- Message can only be added to existing session
- 404 returned if session_id not found
- Session must exist before adding messages

**BR-MSG-002: Active Session Required**
- Messages can only be added to active sessions
- Ended/expired sessions reject new messages
- Error: "Session not found" (same as not existing)

**BR-MSG-003: Role Validation**
- Role MUST be one of: user, assistant, system
- Invalid role returns 400 Bad Request
- Error: "role must be one of: user, assistant, system"

**BR-MSG-004: Content Required**
- Content MUST be non-empty string
- Whitespace-only content rejected
- Error: "content is required"

**BR-MSG-005: Message Type Validation**
- Message type MUST be valid enum value
- Valid types: chat, system, tool_call, tool_result, notification
- Default: "chat" if not specified

**BR-MSG-006: Tokens Default**
- tokens_used defaults to 0 if not provided
- MUST be non-negative integer
- Negative values rejected with 422

**BR-MSG-007: Cost Default**
- cost_usd defaults to 0.0 if not provided
- MUST be non-negative float
- Negative values rejected with 422

**BR-MSG-008: Message ID Generation**
- Message ID auto-generated as UUID
- Format: `msg_{uuid.uuid4().hex[:24]}`
- Client cannot specify message ID

**BR-MSG-009: Message User ID**
- Message user_id set from session owner
- Not from request (inherited from session)
- Ensures message ownership consistency

**BR-MSG-010: Message Timestamp**
- created_at set to current UTC timestamp
- Represents when message was persisted
- Used for ordering in retrieval

**BR-MSG-011: Message Order**
- Messages ordered by created_at ASC
- Oldest messages first in list
- Preserves conversation chronology

**BR-MSG-012: Message Metadata Optional**
- metadata is optional JSONB field
- Defaults to empty object `{}`
- Stores tool calls, processing info, etc.

### Session Status Rules (BR-STS-001 to BR-STS-008)

**BR-STS-001: Status Enumeration**
- Valid statuses: active, completed, ended, archived, expired
- Invalid status rejected with 400/422
- Status changes validated against enum

**BR-STS-002: Status Transition: Active to Ended**
- DELETE endpoint sets status = "ended"
- Also sets is_active = false
- Triggers session.ended event

**BR-STS-003: Status Transition: Active to Completed**
- PUT with status = "completed" allowed
- is_active remains true (can still add messages)
- User-marked completion status

**BR-STS-004: Status Transition: Active to Archived**
- PUT with status = "archived" allowed
- Preserves session for historical access
- May set is_active = false

**BR-STS-005: Status Transition: Active to Expired**
- Background job sets status = "expired"
- Based on last_activity timeout
- Sets is_active = false

**BR-STS-006: Ended Session Immutability**
- Ended sessions cannot be modified
- No new messages allowed
- Status cannot change from ended

**BR-STS-007: Status Change Events**
- session.ended event published on end
- Includes final metrics (messages, tokens, cost)
- Enables downstream processing

**BR-STS-008: Activity Update on Status Change**
- updated_at set on any status change
- last_activity NOT updated on status change
- Distinguishes modification from activity

### Metrics Rules (BR-MET-001 to BR-MET-008)

**BR-MET-001: Message Count Increment**
- message_count incremented by 1 per message
- Atomic operation with message creation
- Cannot be decremented

**BR-MET-002: Token Accumulation**
- total_tokens += message.tokens_used
- Accumulated from each message
- Running total maintained

**BR-MET-003: Cost Accumulation**
- total_cost += message.cost_usd
- Accumulated from each message
- Precision: 6 decimal places

**BR-MET-004: Activity Update**
- last_activity updated on each message add
- Set to current UTC timestamp
- Tracks actual conversation activity

**BR-MET-005: Updated At Tracking**
- updated_at set on any session modification
- Includes status changes, metadata updates
- Broader than last_activity

**BR-MET-006: Metrics Append-Only**
- Metrics cannot be decremented
- No message deletion reduces counts
- Ensures billing accuracy

**BR-MET-007: Metrics Atomicity**
- Message add + metrics update is atomic
- Database transaction ensures consistency
- Prevents partial updates

**BR-MET-008: Stats Aggregation**
- Service stats computed from all sessions
- Includes: total_sessions, active_sessions, etc.
- Average calculated: total_messages / total_sessions

### Query Rules (BR-QRY-001 to BR-QRY-008)

**BR-QRY-001: User ID Required for Session List**
- GET /api/v1/sessions requires user_id parameter
- Missing user_id returns 422 Validation Error
- Prevents listing all system sessions

**BR-QRY-002: Active Only Filter**
- active_only=true filters is_active=true
- Default: active_only=false (all sessions)
- Applies to session list endpoint

**BR-QRY-003: Pagination Default**
- Sessions: page=1, page_size=50 default
- Messages: page=1, page_size=100 default
- Offset calculated: (page - 1) * page_size

**BR-QRY-004: Max Page Size - Sessions**
- Session page_size max: 100
- Exceeding returns 422 Validation Error
- Protects database from large queries

**BR-QRY-005: Max Page Size - Messages**
- Message page_size max: 200
- Exceeding returns 422 Validation Error
- Allows larger message batches

**BR-QRY-006: Session Sort Order**
- Sessions sorted by created_at DESC
- Newest sessions first
- Consistent ordering for pagination

**BR-QRY-007: Message Sort Order**
- Messages sorted by created_at ASC
- Oldest messages first
- Preserves conversation flow

**BR-QRY-008: Page Number Validation**
- Page MUST be >= 1
- Zero or negative returns 422
- No upper limit (may return empty)

---

## State Machines (3 machines)

### Session Lifecycle State Machine

```
States:
- ACTIVE: Session is operational, accepts messages
- COMPLETED: User-marked complete, may still accept messages
- ENDED: Explicitly ended, no new messages
- ARCHIVED: Preserved for history, no new messages
- EXPIRED: Auto-expired due to inactivity

Transitions:
ACTIVE -> COMPLETED (user marks complete)
ACTIVE -> ENDED (DELETE endpoint called)
ACTIVE -> ARCHIVED (admin/system archives)
ACTIVE -> EXPIRED (inactivity timeout)
COMPLETED -> ENDED (user explicitly ends)
COMPLETED -> ARCHIVED (system archives)

Terminal States:
- ENDED: Cannot transition further
- EXPIRED: Cannot transition further (auto-cleanup may delete)

Rules:
- ACTIVE is the only state that guarantees message acceptance
- COMPLETED allows messages (soft completion)
- ENDED, ARCHIVED, EXPIRED block new messages
- All transitions update updated_at timestamp
- Only ENDED triggers session.ended event
```

### Message Lifecycle State Machine

```
States:
- CREATED: Message persisted in database

Note: Messages have a simple lifecycle - once created, they are immutable.

Transitions:
(none) -> CREATED (message added to session)

Rules:
- Messages cannot be updated after creation
- Messages cannot be deleted individually
- Content is immutable once persisted
- Metadata is immutable once persisted
```

### Session Metrics State Machine

```
States:
- ZERO: Initial state (all metrics = 0)
- ACCUMULATING: Metrics increasing with messages
- FROZEN: Session ended, metrics finalized

Transitions:
ZERO -> ACCUMULATING (first message added)
ACCUMULATING -> ACCUMULATING (additional messages)
ACCUMULATING -> FROZEN (session ended)
ZERO -> FROZEN (session ended with no messages)

Rules:
- Metrics only increase, never decrease
- FROZEN state means no more metric changes
- Final metrics included in session.ended event
```

---

## Edge Cases (15 cases)

### EC-001: Session with Custom ID Already Exists
- **Input**: Create session with existing custom session_id
- **Expected**: Database error (primary key conflict)
- **Actual**: 500 Internal Error or unique constraint violation
- **Note**: Client should handle retry with different ID

### EC-002: Concurrent Message Additions
- **Input**: Multiple messages added simultaneously to same session
- **Expected**: All messages persisted, metrics correctly accumulated
- **Actual**: Database transactions ensure consistency
- **Note**: Message order determined by created_at

### EC-003: Very Long Message Content
- **Input**: Message content exceeds typical length (>100KB)
- **Expected**: Accepted if within TEXT column limits
- **Actual**: PostgreSQL TEXT type accepts very large strings
- **Note**: Consider application-level limits for performance

### EC-004: Unicode in Message Content
- **Input**: Message with emojis, CJK characters, RTL text
- **Expected**: Correctly stored and retrieved
- **Actual**: PostgreSQL TEXT with UTF-8 encoding handles all Unicode
- **Note**: Content displayed correctly without corruption

### EC-005: Empty Conversation Data / Metadata
- **Input**: `{"conversation_data": null}` or `{"metadata": null}`
- **Expected**: Stored as empty object `{}`
- **Actual**: Pydantic default_factory handles null -> {}
- **Note**: Consistent empty state representation

### EC-006: Session Access After Account Deletion
- **Input**: user.deleted event processed, then session accessed
- **Expected**: Session marked as ended, still readable
- **Actual**: Sessions soft-ended, data preserved for audit
- **Note**: GDPR compliance may require eventual hard delete

### EC-007: Token/Cost Precision
- **Input**: cost_usd = 0.0000001 (7 decimal places)
- **Expected**: Truncated to 6 decimal places (DECIMAL(10,6))
- **Actual**: Database rounds to stored precision
- **Note**: Slight precision loss for very small values

### EC-008: Zero Tokens Message
- **Input**: Message with tokens_used = 0, cost_usd = 0.0
- **Expected**: Message accepted, no tokens_used event published
- **Actual**: session.tokens_used event skipped when tokens = 0
- **Note**: Reduces unnecessary event traffic

### EC-009: Session List with No Results
- **Input**: GET /sessions for user with no sessions
- **Expected**: Empty list response, total = 0
- **Actual**: `{"sessions": [], "total": 0, "page": 1, "page_size": 50}`
- **Note**: Not an error condition

### EC-010: Message List for Empty Session
- **Input**: GET /sessions/{id}/messages for session with no messages
- **Expected**: Empty list response, total = 0
- **Actual**: `{"messages": [], "total": 0, "page": 1, "page_size": 100}`
- **Note**: Valid new session state

### EC-011: Page Beyond Available Data
- **Input**: page=100 when only 10 sessions exist
- **Expected**: Empty list response (no error)
- **Actual**: Returns empty sessions list
- **Note**: Client handles empty pages gracefully

### EC-012: Account Service Timeout
- **Input**: Account service unreachable during session creation
- **Expected**: Session created anyway (fail-open)
- **Actual**: Warning logged, session proceeds
- **Note**: Service resilience prioritized

### EC-013: NATS Event Bus Unavailable
- **Input**: Event publishing fails during session creation
- **Expected**: Session created, event failure logged
- **Actual**: Non-blocking event publishing
- **Note**: Events are best-effort, not transactional

### EC-014: Rapid Session Creation
- **Input**: 100+ sessions created per second
- **Expected**: All sessions created successfully
- **Actual**: Rate limited by database connection pool
- **Note**: May need rate limiting for abuse prevention

### EC-015: Session Summary for Ended Session
- **Input**: GET /sessions/{id}/summary for ended session
- **Expected**: Summary returned with final metrics
- **Actual**: Works correctly, has_memory = false
- **Note**: Historical session analysis supported

---

## Data Consistency Rules

### DC-001: Session ID Uniqueness
- session_id is primary key
- Enforced at database level
- UUID generation ensures uniqueness

### DC-002: Message-Session Relationship
- session_id in messages references sessions table
- Foreign key constraint (logical, may not be enforced in gRPC)
- Orphan messages prevented by validation

### DC-003: User ID Consistency
- Session.user_id immutable after creation
- Message.user_id inherited from session
- Cross-user data mixing prevented

### DC-004: Timestamp Ordering
- created_at <= updated_at (always)
- created_at <= last_activity (always)
- Message created_at >= session created_at

### DC-005: Metrics Consistency
- message_count = actual count of messages (verify with query)
- total_tokens = sum of all message tokens_used
- total_cost = sum of all message cost_usd

---

## Integration Contracts

### Memory Service Integration
- **Event**: session.message_sent
- **When**: After each message is persisted
- **Payload**: Includes message content for memory processing
- **Expected Response**: Memory service processes asynchronously
- **Error Handling**: Event publishing failure logged, not blocking

### Billing Service Integration
- **Event**: session.tokens_used, session.ended
- **When**: Token consumption and session completion
- **Payload**: user_id, tokens_used, cost_usd
- **Expected Response**: Billing records usage asynchronously
- **Error Handling**: Events are fire-and-forget

### Account Service Integration
- **Endpoint**: GET /api/v1/accounts/profile/{user_id}
- **When**: Session creation (validation)
- **Expected Response**: 200 with user profile OR 404
- **Error Handling**: Fail-open - proceed if unavailable

---

## Error Handling Contracts

### Session Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Session not found | 404 | "Session not found: {session_id}" |
| User ID mismatch | 404 | "Session not found: {session_id}" |
| Missing user_id | 400/422 | "user_id is required" |
| Invalid status | 422 | "status must be one of: ..." |
| Session ended | 404 | "Session not found: {session_id}" |

### Message Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Session not found | 404 | "Session not found: {session_id}" |
| Invalid role | 400 | "role must be one of: user, assistant, system" |
| Empty content | 400 | "content is required" |
| Negative tokens | 422 | Validation error detail |
| Session not active | 404 | "Session not found: {session_id}" |

### Query Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 422 | Validation error (required field) |
| Invalid page | 422 | Validation error (ge=1) |
| Invalid page_size | 422 | Validation error (le=100 or le=200) |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Session Service Team
