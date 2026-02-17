# Session Service - Domain Context

## Overview

The Session Service is the **conversation state manager** for the isA_user platform. It provides centralized session management, message persistence, and conversation metrics tracking. Every AI conversation in the system is organized within a session context.

**Business Context**: Enable seamless, stateful AI conversations that can be paused, resumed, and analyzed. Session Service owns the "when and what" of conversations - tracking session lifecycle, message history, token usage, and costs.

**Core Value Proposition**: Transform transient AI interactions into persistent, queryable conversation records with comprehensive metrics tracking, enabling analytics, billing, and user experience optimization.

---

## Business Taxonomy

### Core Entities

#### 1. Session (Conversation Context)
**Definition**: A unique conversation context representing a user's interaction session with the AI system.

**Business Purpose**:
- Establish conversation boundaries (start/end)
- Group related messages together
- Track conversation metrics (tokens, costs)
- Enable conversation persistence and resumption
- Support analytics and billing

**Key Attributes**:
- Session ID (unique identifier)
- User ID (owner of the session)
- Status (active, completed, ended, archived, expired)
- Conversation Data (JSONB - flexible session context)
- Metadata (JSONB - custom session attributes)
- Is Active (boolean - session operational state)
- Message Count (total messages in session)
- Total Tokens (cumulative token usage)
- Total Cost (cumulative cost in USD)
- Session Summary (AI-generated session summary)
- Created At (session start timestamp)
- Updated At (last modification timestamp)
- Last Activity (last message timestamp)

**Session States**:
- **Active**: Ongoing conversation, user can add messages
- **Completed**: User marked session as complete
- **Ended**: Session explicitly ended by user/system
- **Archived**: Session preserved but no longer active
- **Expired**: Session auto-expired due to inactivity

#### 2. Session Message
**Definition**: An individual message within a conversation session.

**Business Purpose**:
- Record conversation turns (user/assistant/system)
- Track per-message metrics (tokens, cost)
- Enable conversation replay and analysis
- Support RAG and memory systems
- Preserve full conversation history

**Key Attributes**:
- Message ID (unique identifier)
- Session ID (parent session reference)
- User ID (message owner)
- Role (user, assistant, system)
- Content (message text content)
- Message Type (chat, system, tool_call, tool_result, notification)
- Metadata (JSONB - tool calls, embeddings, etc.)
- Tokens Used (token count for this message)
- Cost USD (cost for this message)
- Created At (message timestamp)

**Message Roles**:
- **user**: Human user input
- **assistant**: AI assistant response
- **system**: System prompts and instructions

**Message Types**:
- **chat**: Regular conversation message
- **system**: System-level instruction
- **tool_call**: AI tool/function call
- **tool_result**: Tool execution result
- **notification**: System notification

#### 3. Session Summary
**Definition**: Lightweight session overview for listing and search.

**Business Purpose**:
- Optimize list/search endpoint performance
- Provide essential session info without full message history
- Enable efficient session browsing
- Support dashboard displays

**Key Attributes**:
- Session ID
- User ID
- Status
- Message Count
- Total Tokens
- Total Cost
- Has Memory (boolean - memory service integration)
- Is Active
- Created At
- Last Activity

#### 4. Session Statistics
**Definition**: Aggregated metrics for session service health and usage.

**Business Purpose**:
- Monitor service utilization
- Track resource consumption
- Support capacity planning
- Enable billing reconciliation
- Provide analytics dashboards

**Key Metrics**:
- Total Sessions
- Active Sessions
- Total Messages
- Total Tokens
- Total Cost
- Average Messages Per Session

---

## Domain Scenarios

### Scenario 1: Session Creation and Initialization
**Actor**: User, Client Application
**Trigger**: User starts a new conversation or AI interaction
**Flow**:
1. Client application calls `POST /api/v1/sessions` with user_id
2. Session Service validates user exists via Account Service (fail-open)
3. Session Service generates unique session_id (or uses provided)
4. Creates session record in PostgreSQL with:
   - status = "active"
   - is_active = true
   - message_count = 0
   - total_tokens = 0
   - total_cost = 0.0
5. Publishes `session.started` event to NATS
6. Returns session response to client
7. Memory Service listens and prepares session memory context

**Outcome**: New session created, events published, ready for messages

### Scenario 2: Message Exchange in Session
**Actor**: User, AI Assistant
**Trigger**: User sends message in active session
**Flow**:
1. Client calls `POST /api/v1/sessions/{session_id}/messages` with:
   - role: "user"
   - content: message text
   - tokens_used: token count
   - cost_usd: message cost
2. Session Service validates session exists and is active
3. Session Service validates user ownership (authorization)
4. Creates message record in PostgreSQL
5. Updates session metrics:
   - message_count += 1
   - total_tokens += tokens_used
   - total_cost += cost_usd
   - last_activity = now()
6. Publishes `session.message_sent` event
7. If tokens_used > 0, publishes `session.tokens_used` event
8. Memory Service captures message for context
9. Returns message response

**Outcome**: Message persisted, session metrics updated, events published

### Scenario 3: Session Listing and Pagination
**Actor**: User, Client Application
**Trigger**: User views conversation history
**Flow**:
1. Client calls `GET /api/v1/sessions?user_id={user_id}&active_only=false`
2. Session Service queries PostgreSQL with filters:
   - user_id = provided
   - active_only filter (if true, is_active = true)
3. Orders by created_at DESC
4. Applies pagination (page, page_size)
5. Returns list of session summaries
6. Client displays session list with pagination

**Outcome**: User can browse all sessions with pagination

### Scenario 4: Session Message Retrieval
**Actor**: User, Client Application
**Trigger**: User opens existing conversation to continue or review
**Flow**:
1. Client calls `GET /api/v1/sessions/{session_id}/messages`
2. Session Service validates session exists
3. Validates user ownership
4. Queries messages ordered by created_at ASC
5. Applies pagination (page, page_size)
6. Returns message list with metadata
7. Client renders conversation thread

**Outcome**: Full conversation history available for display/continuation

### Scenario 5: Session Ending and Cleanup
**Actor**: User, System
**Trigger**: User explicitly ends conversation or session expires
**Flow**:
1. Client calls `DELETE /api/v1/sessions/{session_id}`
2. Session Service validates session exists and user ownership
3. Updates session status to "ended"
4. Sets is_active = false
5. Publishes `session.ended` event with:
   - total_messages
   - total_tokens
   - total_cost
6. Billing Service captures final metrics for invoicing
7. Memory Service archives session memory
8. Returns success confirmation

**Outcome**: Session properly closed, metrics finalized, resources released

### Scenario 6: Session Summary and Analytics
**Actor**: User, Dashboard
**Trigger**: User views session statistics
**Flow**:
1. Client calls `GET /api/v1/sessions/{session_id}/summary`
2. Session Service fetches session data
3. Calculates summary metrics
4. Returns SessionSummaryResponse with:
   - session metadata
   - message count
   - token usage
   - cost totals
   - activity timestamps
5. Dashboard displays session analytics

**Outcome**: User has visibility into session metrics

### Scenario 7: Service Statistics Monitoring
**Actor**: DevOps, Monitoring System
**Trigger**: Scheduled health/metrics check
**Flow**:
1. Monitoring calls `GET /api/v1/sessions/stats`
2. Session Service executes aggregate queries:
   - COUNT(*) total sessions
   - COUNT(*) WHERE is_active = true
   - SUM(message_count)
   - SUM(total_tokens)
   - SUM(total_cost)
3. Calculates average messages per session
4. Returns SessionStatsResponse
5. Monitoring system logs metrics
6. Alerts if thresholds exceeded

**Outcome**: Real-time service health visibility

### Scenario 8: User Account Deletion Cascade
**Actor**: Account Service (via event)
**Trigger**: User deletes their account
**Flow**:
1. Account Service publishes `user.deleted` event
2. Session Service event handler receives event
3. Fetches all sessions for user_id
4. Ends all active sessions
5. Optionally marks sessions for GDPR cleanup
6. Logs cleanup completion

**Outcome**: User session data cleaned up on account deletion

---

## Domain Events

### Published Events

#### 1. session.started (EventType.SESSION_STARTED)
**Trigger**: New session successfully created via `POST /api/v1/sessions`
**Source**: session_service
**Payload**:
- session_id: Unique session identifier
- user_id: Session owner
- metadata: Session metadata
- timestamp: Creation timestamp

**Subscribers**:
- **Memory Service**: Initialize session memory context
- **Analytics Service**: Track session creation metrics
- **Audit Service**: Log session start

#### 2. session.ended (EventType.SESSION_ENDED)
**Trigger**: Session ended via `DELETE /api/v1/sessions/{session_id}`
**Source**: session_service
**Payload**:
- session_id: Session identifier
- user_id: Session owner
- total_messages: Final message count
- total_tokens: Total tokens consumed
- total_cost: Total cost in USD
- timestamp: End timestamp

**Subscribers**:
- **Billing Service**: Process final session cost
- **Memory Service**: Archive session memory
- **Analytics Service**: Track session metrics
- **Audit Service**: Log session completion

#### 3. session.message_sent (EventType.SESSION_MESSAGE_SENT)
**Trigger**: Message added via `POST /api/v1/sessions/{session_id}/messages`
**Source**: session_service
**Payload**:
- session_id: Session identifier
- message_id: Message identifier
- user_id: Message owner
- role: Message role (user/assistant/system)
- content: Message content (for memory)
- message_type: Message type
- tokens_used: Token count
- cost_usd: Message cost
- timestamp: Message timestamp

**Subscribers**:
- **Memory Service**: Process message for memory storage
- **Analytics Service**: Track message metrics
- **Billing Service**: Record usage for billing

#### 4. session.tokens_used (EventType.SESSION_TOKENS_USED)
**Trigger**: Tokens consumed when message with tokens_used > 0 is added
**Source**: session_service
**Payload**:
- session_id: Session identifier
- user_id: User identifier
- tokens_used: Token count
- cost_usd: Cost in USD
- message_id: Related message
- timestamp: Usage timestamp

**Subscribers**:
- **Billing Service**: Track token consumption
- **Wallet Service**: Deduct credits
- **Analytics Service**: Track usage patterns

### Subscribed Events

#### 1. account_service.user.deleted
**Source**: account_service
**Purpose**: Clean up sessions when user account is deleted

**Payload**:
- user_id: Deleted user ID
- timestamp: Deletion timestamp

**Handler Action**: Ends all active sessions for the user, marks for cleanup

---

## Core Concepts

### Session Lifecycle
1. **Creation**: Client initiates session -> Session Service creates record -> Publishes event
2. **Active**: User exchanges messages -> Messages persisted -> Metrics updated
3. **Idle**: No activity -> Session remains active until timeout
4. **Ended**: User/system ends session -> Status updated -> Final event published
5. **Expired**: Auto-expired after inactivity threshold (configurable)
6. **Archived**: Long-term storage for historical access

### Message Flow
```
User -> Client App -> Session Service -> PostgreSQL
                                     -> NATS (events)

NATS -> Memory Service (process message)
     -> Billing Service (track usage)
     -> Analytics Service (metrics)
```

### Session Ownership and Authorization
- **Ownership**: Sessions belong to a single user (user_id)
- **Authorization**: Only session owner can access session data
- **Soft Authorization**: user_id passed as query parameter, validated against session
- **Gateway Authorization**: JWT token validation at API gateway level

### Metrics Tracking
- **Per-Message**: tokens_used, cost_usd tracked for each message
- **Per-Session**: Running totals maintained (message_count, total_tokens, total_cost)
- **Service-Level**: Aggregates available via stats endpoint
- **Real-time Updates**: Metrics updated on each message

### Event-Driven Architecture
- All session mutations publish events to NATS
- Memory Service subscribes for context management
- Billing Service subscribes for usage tracking
- Loose coupling enables horizontal scaling

### Separation of Concerns
**Session Service owns**:
- Session lifecycle (create, end, expire)
- Message persistence (CRUD)
- Session metrics (tokens, cost, count)
- Session state (status, activity)

**Session Service does NOT own**:
- User authentication (auth_service)
- User identity (account_service)
- AI processing (external AI service)
- Session memory/context (memory_service)
- Billing/invoicing (billing_service)
- Token deduction (wallet_service)

---

## Business Rules (High-Level)

### Session Creation Rules
- **BR-SES-001**: User ID is required for session creation
- **BR-SES-002**: Session ID auto-generated if not provided (UUID)
- **BR-SES-003**: Default status is "active" on creation
- **BR-SES-004**: Default is_active is true on creation
- **BR-SES-005**: Default metrics (message_count, tokens, cost) are zero
- **BR-SES-006**: Multiple sessions per user are allowed
- **BR-SES-007**: Account existence check is fail-open (doesn't block if unavailable)

### Session Access Rules
- **BR-ACC-001**: Only session owner can access session data
- **BR-ACC-002**: Session access returns 404 if session not found OR not owned by user
- **BR-ACC-003**: Inactive sessions can still be read (not modified)
- **BR-ACC-004**: user_id authorization check is required for all operations

### Message Rules
- **BR-MSG-001**: Session must exist and be active to add messages
- **BR-MSG-002**: Role must be one of: user, assistant, system
- **BR-MSG-003**: Content is required and cannot be empty
- **BR-MSG-004**: tokens_used defaults to 0 if not provided
- **BR-MSG-005**: cost_usd defaults to 0.0 if not provided
- **BR-MSG-006**: Message creation updates session metrics atomically
- **BR-MSG-007**: Messages are ordered by created_at ASC (oldest first)

### Session Status Rules
- **BR-STS-001**: Session status transitions: active -> ended/completed/expired
- **BR-STS-002**: Ending a session sets is_active = false
- **BR-STS-003**: Ended sessions cannot have new messages added
- **BR-STS-004**: Status changes trigger session.ended event (for end state)
- **BR-STS-005**: Expired status set by background job for inactive sessions

### Metrics Rules
- **BR-MET-001**: message_count incremented on each message add
- **BR-MET-002**: total_tokens accumulated from each message's tokens_used
- **BR-MET-003**: total_cost accumulated from each message's cost_usd
- **BR-MET-004**: last_activity updated on every message add
- **BR-MET-005**: Metrics cannot be decremented (append-only)

### Query Rules
- **BR-QRY-001**: List sessions requires user_id parameter
- **BR-QRY-002**: Default pagination: page=1, page_size=50
- **BR-QRY-003**: Max page_size for sessions: 100
- **BR-QRY-004**: Max page_size for messages: 200
- **BR-QRY-005**: Sessions ordered by created_at DESC (newest first)
- **BR-QRY-006**: Messages ordered by created_at ASC (oldest first)

### Event Publishing Rules
- **BR-EVT-001**: All session mutations publish corresponding events
- **BR-EVT-002**: Event publishing failures are logged but don't block operations
- **BR-EVT-003**: session.message_sent includes content for memory service
- **BR-EVT-004**: session.tokens_used only published when tokens > 0
- **BR-EVT-005**: Events use ISO 8601 timestamps

### Data Consistency Rules
- **BR-CON-001**: Session creation is atomic (PostgreSQL transaction)
- **BR-CON-002**: Message creation and metrics update are atomic
- **BR-CON-003**: Session deletion is soft (status change, not data removal)
- **BR-CON-004**: User deletion cascades to session cleanup (via events)

---

## Session Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User validation (fail-open)
- **Auth Service**: JWT token validation (at gateway)
- **PostgreSQL gRPC Service**: Persistent storage
- **NATS Event Bus**: Event publishing
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and authorization

### Downstream Consumers
- **Memory Service**: Session memory context management
- **Billing Service**: Usage tracking and invoicing
- **Wallet Service**: Token/credit deduction
- **Analytics Service**: Usage metrics and reporting
- **Audit Service**: Session activity logging

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection
- **Repository Pattern**: SessionRepository, SessionMessageRepository
- **Protocol Interfaces**: SessionRepositoryProtocol, EventBusProtocol
- **Factory Pattern**: create_session_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Session Quality Metrics
- **Average Session Duration**: Time from creation to end
- **Average Messages Per Session**: Message count distribution
- **Session Completion Rate**: % of sessions explicitly ended vs expired
- **Active Session Count**: Real-time active session gauge

### Performance Metrics
- **Session Creation Latency**: Time from request to response (target: <200ms)
- **Message Add Latency**: Time to persist message (target: <100ms)
- **Session Fetch Latency**: Time to retrieve session (target: <50ms)
- **Message List Latency**: Time for paginated messages (target: <150ms)

### Resource Metrics
- **Total Tokens Consumed**: Daily/weekly/monthly token usage
- **Total Cost Accumulated**: Session cost totals
- **Storage Utilization**: Message storage growth rate
- **Event Throughput**: Events published per second

### Availability Metrics
- **Service Uptime**: Session Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success rate
- **Event Publishing Success**: % of events successfully published

---

## Glossary

**Session**: Conversation context containing messages and metrics
**Message**: Individual turn in a conversation (user/assistant/system)
**Role**: Message sender type (user, assistant, system)
**Message Type**: Message category (chat, system, tool_call, etc.)
**Active Session**: Session with is_active = true, accepts new messages
**Ended Session**: Session explicitly closed, is_active = false
**Expired Session**: Session auto-closed due to inactivity
**Token**: AI model token unit for measuring content length
**Cost USD**: Monetary cost for AI processing
**Session Metrics**: Aggregate statistics (message_count, total_tokens, total_cost)
**Event Bus**: NATS messaging system for asynchronous events
**Memory Service**: Service handling conversation context and memory
**Fail-Open**: Continue operation if dependent service unavailable

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Session Service Team
