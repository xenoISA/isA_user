# Session Service - Product Requirements Document (PRD)

## Product Overview

The Session Service provides conversation state management for the isA_user platform, enabling persistent AI conversation sessions with message history, metrics tracking, and lifecycle management.

**Product Goal**: Deliver a robust, scalable session management system that enables seamless AI conversations while providing comprehensive usage metrics for analytics, billing, and user experience optimization.

**Key Capabilities**:
- Session lifecycle management (create, read, update, end)
- Message persistence with full conversation history
- Real-time metrics tracking (tokens, costs, message counts)
- Event-driven architecture for service integration
- Pagination for large conversation histories

---

## Target Users

### Primary Users

#### 1. End Users (via Client Applications)
- **Description**: Individuals using AI assistants through mobile/web apps
- **Needs**: Seamless conversation experience, session history, conversation resumption
- **Goals**: Efficient AI interactions without losing context

#### 2. Client Applications (API Consumers)
- **Description**: Mobile apps, web apps, and integrations consuming Session API
- **Needs**: Reliable session creation, message persistence, metrics retrieval
- **Goals**: Build responsive AI-powered user experiences

### Secondary Users

#### 3. Internal Services
- **Description**: Memory Service, Billing Service, Analytics Service
- **Needs**: Real-time session events, accurate metrics, message content
- **Goals**: Process session data for memory, billing, and analytics

#### 4. Platform Administrators
- **Description**: DevOps, support team, product managers
- **Needs**: Service health monitoring, usage statistics, debugging tools
- **Goals**: Ensure platform reliability and understand usage patterns

---

## Epics and User Stories

### Epic 1: Session Lifecycle Management
**Goal**: Enable users to create, manage, and end conversation sessions

**User Stories**:
- As a user, I want to start a new conversation session so that I can interact with the AI assistant
- As a user, I want to resume a previous session so that I can continue where I left off
- As a user, I want to end a session explicitly so that I know the conversation is complete
- As a system, I want to expire inactive sessions so that resources are properly released
- As an admin, I want to view session statistics so that I can monitor platform usage

### Epic 2: Message Management
**Goal**: Enable reliable message persistence and retrieval within sessions

**User Stories**:
- As a user, I want to send messages in a session so that I can communicate with the AI
- As a user, I want to view my conversation history so that I can review past interactions
- As a client app, I want to retrieve messages in pages so that I can handle large conversations
- As a developer, I want message metadata stored so that I can access tool calls and results
- As a system, I want to track message role so that conversations can be properly displayed

### Epic 3: Metrics and Analytics
**Goal**: Provide comprehensive session and message metrics

**User Stories**:
- As a user, I want to see my token usage so that I understand resource consumption
- As a billing system, I want accurate cost data so that I can charge appropriately
- As a product manager, I want session statistics so that I can analyze user behavior
- As a user, I want to see session summaries so that I can quickly review my conversations
- As DevOps, I want service health metrics so that I can ensure reliability

### Epic 4: Event Integration
**Goal**: Enable event-driven integration with other services

**User Stories**:
- As a memory service, I want session.message_sent events so that I can update context
- As a billing service, I want session.tokens_used events so that I can track consumption
- As an analytics service, I want session lifecycle events so that I can measure engagement
- As an account service, I want to notify on user deletion so that sessions are cleaned up

### Epic 5: Security and Authorization
**Goal**: Ensure sessions are properly secured and isolated per user

**User Stories**:
- As a user, I want only my sessions visible to me so that my conversations are private
- As a system, I want to validate user ownership so that unauthorized access is prevented
- As a security team, I want session access logged so that we have audit trails
- As a compliance officer, I want session data deletion capability for GDPR compliance

---

## API Surface Documentation

### Health Check Endpoints

#### GET /health
**Description**: Basic health check
**Auth Required**: No
**Request**: None
**Response**:
```json
{
  "status": "healthy",
  "service": "session_service",
  "port": 8205,
  "version": "1.0.0",
  "timestamp": "2025-12-15T10:30:00Z"
}
```
**Error Codes**: 500 (Service Unavailable)

#### GET /health/detailed
**Description**: Detailed health check with database status
**Auth Required**: No
**Response**:
```json
{
  "service": "session_service",
  "status": "operational",
  "port": 8205,
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2025-12-15T10:30:00Z"
}
```

### Session Management Endpoints

#### POST /api/v1/sessions
**Description**: Create new session
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "session_id": "sess_optional_custom_id",
  "conversation_data": {"topic": "coding help"},
  "metadata": {"platform": "web", "client_version": "2.0"}
}
```
**Response Schema**:
```json
{
  "session_id": "sess_abc123",
  "user_id": "user_12345",
  "status": "active",
  "conversation_data": {"topic": "coding help"},
  "metadata": {"platform": "web", "client_version": "2.0"},
  "is_active": true,
  "message_count": 0,
  "total_tokens": 0,
  "total_cost": 0.0,
  "session_summary": "",
  "created_at": "2025-12-15T10:30:00Z",
  "updated_at": "2025-12-15T10:30:00Z",
  "last_activity": "2025-12-15T10:30:00Z"
}
```
**Error Codes**: 400 (Bad Request), 422 (Validation Error), 500 (Internal Error)
**Example**:
```bash
curl -X POST http://localhost:8205/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_12345"}'
```

#### GET /api/v1/sessions/{session_id}
**Description**: Get session by ID
**Auth Required**: Yes
**Path Parameters**:
- session_id: Session identifier
**Query Parameters**:
- user_id: (optional) User ID for authorization
**Response Schema**: Same as POST response
**Error Codes**: 404 (Not Found), 500 (Internal Error)
**Example**:
```bash
curl http://localhost:8205/api/v1/sessions/sess_abc123?user_id=user_12345
```

#### PUT /api/v1/sessions/{session_id}
**Description**: Update session
**Auth Required**: Yes
**Path Parameters**:
- session_id: Session identifier
**Query Parameters**:
- user_id: (optional) User ID for authorization
**Request Schema**:
```json
{
  "status": "completed",
  "conversation_data": {"topic": "coding help", "resolved": true},
  "metadata": {"satisfaction": "high"}
}
```
**Response Schema**: Updated session object
**Error Codes**: 400 (Bad Request), 404 (Not Found), 422 (Validation Error), 500 (Internal Error)

#### DELETE /api/v1/sessions/{session_id}
**Description**: End session
**Auth Required**: Yes
**Path Parameters**:
- session_id: Session identifier
**Query Parameters**:
- user_id: (optional) User ID for authorization
**Response Schema**:
```json
{
  "message": "Session ended successfully"
}
```
**Error Codes**: 404 (Not Found), 500 (Internal Error)
**Example**:
```bash
curl -X DELETE http://localhost:8205/api/v1/sessions/sess_abc123?user_id=user_12345
```

#### GET /api/v1/sessions
**Description**: List user sessions
**Auth Required**: Yes
**Query Parameters**:
- user_id: (required) User ID to filter sessions
- active_only: (optional, default: false) Only return active sessions
- page: (optional, default: 1) Page number
- page_size: (optional, default: 50, max: 100) Items per page
**Response Schema**:
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "user_id": "user_12345",
      "status": "active",
      "is_active": true,
      "message_count": 10,
      "total_tokens": 1500,
      "total_cost": 0.15,
      "created_at": "2025-12-15T10:30:00Z",
      "last_activity": "2025-12-15T10:35:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 50
}
```
**Error Codes**: 422 (Validation Error), 500 (Internal Error)
**Example**:
```bash
curl "http://localhost:8205/api/v1/sessions?user_id=user_12345&active_only=true&page=1&page_size=20"
```

#### GET /api/v1/sessions/{session_id}/summary
**Description**: Get session summary with metrics
**Auth Required**: Yes
**Path Parameters**:
- session_id: Session identifier
**Query Parameters**:
- user_id: (optional) User ID for authorization
**Response Schema**:
```json
{
  "session_id": "sess_abc123",
  "user_id": "user_12345",
  "status": "active",
  "message_count": 10,
  "total_tokens": 1500,
  "total_cost": 0.15,
  "has_memory": false,
  "is_active": true,
  "created_at": "2025-12-15T10:30:00Z",
  "last_activity": "2025-12-15T10:35:00Z"
}
```
**Error Codes**: 404 (Not Found), 500 (Internal Error)

#### GET /api/v1/sessions/stats
**Description**: Get session service statistics
**Auth Required**: Yes
**Response Schema**:
```json
{
  "total_sessions": 1520,
  "active_sessions": 45,
  "total_messages": 45000,
  "total_tokens": 15000000,
  "total_cost": 1500.50,
  "average_messages_per_session": 29.6
}
```
**Error Codes**: 500 (Internal Error)

### Message Management Endpoints

#### POST /api/v1/sessions/{session_id}/messages
**Description**: Add message to session
**Auth Required**: Yes
**Path Parameters**:
- session_id: Session identifier
**Query Parameters**:
- user_id: (optional) User ID for authorization
**Request Schema**:
```json
{
  "role": "user",
  "content": "How do I implement a binary search in Python?",
  "message_type": "chat",
  "metadata": {"source": "keyboard"},
  "tokens_used": 15,
  "cost_usd": 0.001
}
```
**Response Schema**:
```json
{
  "message_id": "msg_xyz789",
  "session_id": "sess_abc123",
  "user_id": "user_12345",
  "role": "user",
  "content": "How do I implement a binary search in Python?",
  "message_type": "chat",
  "metadata": {"source": "keyboard"},
  "tokens_used": 15,
  "cost_usd": 0.001,
  "created_at": "2025-12-15T10:31:00Z"
}
```
**Error Codes**: 400 (Bad Request - invalid role), 404 (Session Not Found), 422 (Validation Error), 500 (Internal Error)
**Example**:
```bash
curl -X POST http://localhost:8205/api/v1/sessions/sess_abc123/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Hello!", "message_type": "chat"}'
```

#### GET /api/v1/sessions/{session_id}/messages
**Description**: Get session messages
**Auth Required**: Yes
**Path Parameters**:
- session_id: Session identifier
**Query Parameters**:
- user_id: (optional) User ID for authorization
- page: (optional, default: 1) Page number
- page_size: (optional, default: 100, max: 200) Items per page
**Response Schema**:
```json
{
  "messages": [
    {
      "message_id": "msg_001",
      "session_id": "sess_abc123",
      "user_id": "user_12345",
      "role": "user",
      "content": "Hello!",
      "message_type": "chat",
      "metadata": {},
      "tokens_used": 5,
      "cost_usd": 0.0005,
      "created_at": "2025-12-15T10:30:00Z"
    },
    {
      "message_id": "msg_002",
      "session_id": "sess_abc123",
      "user_id": "user_12345",
      "role": "assistant",
      "content": "Hello! How can I help you today?",
      "message_type": "chat",
      "metadata": {},
      "tokens_used": 10,
      "cost_usd": 0.001,
      "created_at": "2025-12-15T10:30:05Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 100
}
```
**Error Codes**: 404 (Session Not Found), 500 (Internal Error)
**Example**:
```bash
curl "http://localhost:8205/api/v1/sessions/sess_abc123/messages?page=1&page_size=50"
```

---

## Functional Requirements

### Session Management

**FR-001**: System MUST allow creating new sessions with user_id
- Accept optional session_id for client-specified IDs
- Generate UUID if session_id not provided
- Initialize default metrics (zeros)

**FR-002**: System MUST retrieve session by session_id
- Return full session details including metrics
- Validate user ownership via user_id parameter

**FR-003**: System MUST update session status and metadata
- Support status transitions (active -> ended/completed)
- Preserve existing data when partially updating

**FR-004**: System MUST end sessions cleanly
- Set is_active = false
- Set status = "ended"
- Publish session.ended event

**FR-005**: System MUST list sessions with pagination
- Filter by user_id (required)
- Filter by active_only (optional)
- Support page and page_size parameters

**FR-006**: System MUST provide session summary with metrics
- Include message_count, total_tokens, total_cost
- Include activity timestamps

### Message Management

**FR-007**: System MUST add messages to active sessions
- Validate session exists and is active
- Validate role is one of: user, assistant, system
- Validate content is non-empty

**FR-008**: System MUST update session metrics on message add
- Increment message_count
- Add tokens_used to total_tokens
- Add cost_usd to total_cost
- Update last_activity timestamp

**FR-009**: System MUST retrieve messages with pagination
- Order by created_at ASC (oldest first)
- Support page and page_size parameters
- Include all message metadata

### Event Publishing

**FR-010**: System MUST publish session.started event on creation
- Include session_id, user_id, metadata, timestamp

**FR-011**: System MUST publish session.ended event on end
- Include final metrics (messages, tokens, cost)

**FR-012**: System MUST publish session.message_sent event on message add
- Include full message details including content

**FR-013**: System MUST publish session.tokens_used when tokens > 0
- Include tokens_used and cost_usd

### Statistics and Health

**FR-014**: System MUST provide service statistics
- Total sessions, active sessions
- Total messages, tokens, cost
- Average messages per session

**FR-015**: System MUST provide health check endpoints
- Basic health: /health
- Detailed health: /health/detailed with DB status

---

## Non-Functional Requirements

### Performance

**NFR-001**: Session creation MUST complete within 200ms (p95)

**NFR-002**: Message addition MUST complete within 100ms (p95)

**NFR-003**: Session retrieval MUST complete within 50ms (p95)

**NFR-004**: Message list (100 items) MUST complete within 150ms (p95)

**NFR-005**: Service MUST support 1000 concurrent sessions

### Scalability

**NFR-006**: Service MUST scale horizontally behind load balancer

**NFR-007**: Database queries MUST use proper indexing

**NFR-008**: Event publishing MUST be non-blocking

### Reliability

**NFR-009**: Service uptime MUST be 99.9%

**NFR-010**: Event publishing failures MUST NOT block operations

**NFR-011**: Account service unavailability MUST NOT block session creation (fail-open)

### Security

**NFR-012**: All session data MUST be isolated per user

**NFR-013**: Session access MUST validate user ownership

**NFR-014**: Message content MUST be stored securely

---

## Success Metrics

### Adoption Metrics
- **Daily Active Sessions**: Sessions created per day
- **Average Session Duration**: Time from creation to end
- **Messages Per Session**: Average conversation length

### Performance Metrics
- **API Latency**: p50, p95, p99 response times
- **Error Rate**: % of requests returning 5xx
- **Throughput**: Requests per second

### Business Metrics
- **Token Consumption**: Daily/monthly token usage
- **Cost Accumulation**: Total platform cost from sessions
- **User Engagement**: Sessions per user per day

### Operational Metrics
- **Service Availability**: Uptime percentage
- **Database Connection Pool**: Active/idle connections
- **Event Publishing Rate**: Events per second

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Session Service Team
