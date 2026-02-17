# Session Service - Design Document

## Architecture Overview

### Service Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Session Service                          │
├────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                             │
│  ├─ Route Handlers (CRUD endpoints)                        │
│  ├─ Dependency Injection Setup                             │
│  └─ Lifespan Management (startup/shutdown)                 │
├────────────────────────────────────────────────────────────┤
│  Service Layer (session_service.py)                        │
│  ├─ Business Logic                                          │
│  ├─ Validation Rules                                        │
│  ├─ Metrics Calculation                                     │
│  └─ Event Publishing                                        │
├────────────────────────────────────────────────────────────┤
│  Repository Layer (session_repository.py)                  │
│  ├─ SessionRepository (sessions table)                     │
│  └─ SessionMessageRepository (session_messages table)      │
├────────────────────────────────────────────────────────────┤
│  Dependency Injection (protocols.py)                       │
│  ├─ SessionRepositoryProtocol                              │
│  ├─ SessionMessageRepositoryProtocol                       │
│  ├─ EventBusProtocol                                       │
│  └─ AccountClientProtocol                                  │
├────────────────────────────────────────────────────────────┤
│  Factory (factory.py)                                      │
│  └─ create_session_service() - production instantiation    │
└────────────────────────────────────────────────────────────┘

External Dependencies:
- PostgreSQL via gRPC (data persistence)
- NATS (event publishing)
- Account Service (user validation - fail-open)
- Consul (service discovery)
```

### Component Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │  API        │    │  Session    │
│   Apps      │───>│  Gateway    │───>│  Service    │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                   ┌─────────────────────────┼─────────────────────────┐
                   │                         │                         │
                   ▼                         ▼                         ▼
            ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
            │ PostgreSQL  │          │    NATS     │          │  Account    │
            │   (gRPC)    │          │ Event Bus   │          │  Service    │
            └─────────────┘          └──────┬──────┘          └─────────────┘
                                            │
              ┌─────────────────────────────┼─────────────────────────┐
              │                             │                         │
              ▼                             ▼                         ▼
       ┌─────────────┐              ┌─────────────┐           ┌─────────────┐
       │   Memory    │              │  Billing    │           │  Analytics  │
       │   Service   │              │  Service    │           │   Service   │
       └─────────────┘              └─────────────┘           └─────────────┘
```

---

## Component Design

### Service Layer (session_service.py)

```python
class SessionService:
    """
    Session management business logic service.

    Responsibilities:
    - Session lifecycle management (create, read, update, end)
    - Message persistence and retrieval
    - Metrics tracking and calculation
    - Event publishing for integration
    - Validation and authorization
    """

    def __init__(
        self,
        session_repo: Optional[SessionRepositoryProtocol] = None,
        message_repo: Optional[SessionMessageRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
        config=None,
    ):
        # Lazy initialization via properties
        ...

    # Session Operations
    async def create_session(request: SessionCreateRequest) -> SessionResponse
    async def get_session(session_id: str, user_id: Optional[str]) -> SessionResponse
    async def update_session(session_id: str, request: SessionUpdateRequest, user_id: Optional[str]) -> SessionResponse
    async def end_session(session_id: str, user_id: Optional[str]) -> bool
    async def get_user_sessions(user_id: str, active_only: bool, page: int, page_size: int) -> SessionListResponse
    async def get_session_summary(session_id: str, user_id: Optional[str]) -> SessionSummaryResponse

    # Message Operations
    async def add_message(session_id: str, request: MessageCreateRequest, user_id: Optional[str]) -> MessageResponse
    async def get_session_messages(session_id: str, page: int, page_size: int, user_id: Optional[str]) -> MessageListResponse

    # Statistics
    async def get_service_stats() -> SessionStatsResponse
    async def health_check() -> Dict[str, Any]
```

### Repository Layer

#### SessionRepository

```python
class SessionRepository:
    """Session data access layer"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # PostgreSQL gRPC client setup
        ...

    async def create_session(session_data: Dict[str, Any]) -> Optional[Session]
    async def get_by_session_id(session_id: str) -> Optional[Session]
    async def get_user_sessions(user_id: str, active_only: bool, limit: int, offset: int) -> List[Session]
    async def update_session_status(session_id: str, status: str) -> bool
    async def update_session_activity(session_id: str) -> bool
    async def increment_message_count(session_id: str, tokens_used: int, cost_usd: float) -> bool
    async def expire_old_sessions(hours_old: int) -> int
```

#### SessionMessageRepository

```python
class SessionMessageRepository:
    """Session message data access layer"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # PostgreSQL gRPC client setup
        ...

    async def create_message(message_data: Dict[str, Any]) -> Optional[SessionMessage]
    async def get_session_messages(session_id: str, limit: int, offset: int) -> List[SessionMessage]
```

### Protocol Interfaces (protocols.py)

```python
@runtime_checkable
class SessionRepositoryProtocol(Protocol):
    """Interface for session repository - enables testing with mocks"""

    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Session]: ...
    async def get_by_session_id(self, session_id: str) -> Optional[Session]: ...
    async def get_user_sessions(...) -> List[Session]: ...
    async def update_session_status(self, session_id: str, status: str) -> bool: ...
    async def update_session_activity(self, session_id: str) -> bool: ...
    async def increment_message_count(...) -> bool: ...

@runtime_checkable
class SessionMessageRepositoryProtocol(Protocol):
    """Interface for message repository"""

    async def create_message(self, message_data: Dict[str, Any]) -> Optional[SessionMessage]: ...
    async def get_session_messages(...) -> List[SessionMessage]: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for event publishing"""

    async def publish_event(self, event: Any) -> None: ...

@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for account service client"""

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]: ...
```

---

## Database Schemas

### Schema: session

#### Table: session.sessions

```sql
CREATE SCHEMA IF NOT EXISTS session;

CREATE TABLE IF NOT EXISTS session.sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    conversation_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,6) DEFAULT 0.0,
    session_summary TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX idx_sessions_user_id ON session.sessions(user_id);
CREATE INDEX idx_sessions_status ON session.sessions(status);
CREATE INDEX idx_sessions_is_active ON session.sessions(is_active);
CREATE INDEX idx_sessions_created_at ON session.sessions(created_at DESC);
CREATE INDEX idx_sessions_last_activity ON session.sessions(last_activity DESC);
CREATE INDEX idx_sessions_user_active ON session.sessions(user_id, is_active);
```

#### Table: session.session_messages

```sql
CREATE TABLE IF NOT EXISTS session.session_messages (
    id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL REFERENCES session.sessions(session_id),
    user_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    message_type VARCHAR(30) DEFAULT 'chat',
    message_metadata JSONB DEFAULT '{}',
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_messages_session_id ON session.session_messages(session_id);
CREATE INDEX idx_messages_user_id ON session.session_messages(user_id);
CREATE INDEX idx_messages_created_at ON session.session_messages(created_at ASC);
CREATE INDEX idx_messages_session_created ON session.session_messages(session_id, created_at ASC);
```

---

## Data Flow Diagrams

### Session Creation Flow

```
Client -> POST /api/v1/sessions
  -> RouteHandler (main.py)
    -> SessionService.create_session()
      -> Validate user_id not empty
      -> [Optional] AccountClient.get_account_profile() - fail-open
      -> Generate session_id (UUID) if not provided
      -> SessionRepository.create_session()
        -> PostgreSQL INSERT (via gRPC)
      <- Session object
      -> EventBus.publish_event(SESSION_STARTED)
        -> NATS
    <- SessionResponse
  <- HTTP 200 {session}
```

### Message Addition Flow

```
Client -> POST /api/v1/sessions/{session_id}/messages
  -> RouteHandler (main.py)
    -> SessionService.add_message()
      -> SessionRepository.get_by_session_id()
        -> PostgreSQL SELECT
      <- Session (verify exists and active)
      -> Validate user ownership (user_id)
      -> Validate message (role, content)
      -> SessionMessageRepository.create_message()
        -> PostgreSQL INSERT (via gRPC)
      <- SessionMessage
      -> SessionRepository.increment_message_count()
        -> PostgreSQL UPDATE (metrics)
      -> EventBus.publish_event(SESSION_MESSAGE_SENT)
        -> NATS
      -> [If tokens > 0] EventBus.publish_event(SESSION_TOKENS_USED)
        -> NATS
    <- MessageResponse
  <- HTTP 200 {message}
```

### Session End Flow

```
Client -> DELETE /api/v1/sessions/{session_id}
  -> RouteHandler (main.py)
    -> SessionService.end_session()
      -> SessionRepository.get_by_session_id()
      <- Session (verify exists)
      -> Validate user ownership
      -> SessionRepository.update_session_status("ended")
        -> PostgreSQL UPDATE (status, is_active=false)
      -> EventBus.publish_event(SESSION_ENDED)
        -> NATS (with final metrics)
    <- bool (success)
  <- HTTP 200 {"message": "Session ended successfully"}
```

### Session List Flow

```
Client -> GET /api/v1/sessions?user_id=xxx&active_only=true&page=1&page_size=50
  -> RouteHandler (main.py)
    -> SessionService.get_user_sessions()
      -> SessionRepository.get_user_sessions()
        -> PostgreSQL SELECT with:
          - WHERE user_id = $1
          - [If active_only] AND is_active = true
          - ORDER BY created_at DESC
          - LIMIT $2 OFFSET $3
      <- List[Session]
      -> Convert to SessionListResponse
    <- SessionListResponse
  <- HTTP 200 {sessions, total, page, page_size}
```

---

## Technology Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI (async support)
- **Validation**: Pydantic v2 (models and schemas)
- **Database**: PostgreSQL (via AsyncPostgresClient/gRPC)
- **Event Bus**: NATS (via core.nats_client)
- **Service Discovery**: Consul (via isa_common.consul_client)
- **HTTP Client**: httpx (async) for internal service calls
- **Configuration**: ConfigManager (core.config_manager)
- **Logging**: Python logging (core.logger)

---

## Security Considerations

### Authentication
- JWT token validation at API Gateway level
- X-Internal-Call header for internal service-to-service calls
- Session Service trusts gateway-authenticated requests

### Authorization
- Session ownership validated via user_id parameter
- Sessions only accessible by their owner
- 404 returned for both not found and unauthorized (no info leak)

### Input Validation
- Pydantic models validate all request payloads
- Role enumeration: only "user", "assistant", "system" allowed
- Content required and non-empty for messages
- SQL injection prevented by parameterized queries

### Data Privacy
- Message content stored in database (encrypted at rest)
- Session data isolated by user_id
- Soft delete preserves data for compliance
- GDPR: user.deleted event triggers session cleanup

---

## Event-Driven Architecture

### Published Events

| Event Type | When Published | Payload |
|------------|----------------|---------|
| SESSION_STARTED | Session created | session_id, user_id, metadata, timestamp |
| SESSION_ENDED | Session ended | session_id, user_id, total_messages, total_tokens, total_cost, timestamp |
| SESSION_MESSAGE_SENT | Message added | session_id, message_id, user_id, role, content, message_type, tokens_used, cost_usd, timestamp |
| SESSION_TOKENS_USED | Tokens consumed (> 0) | session_id, user_id, tokens_used, cost_usd, message_id, timestamp |

### Subscribed Events

| Event Pattern | Source | Handler Action |
|---------------|--------|----------------|
| account_service.user.deleted | account_service | End all user sessions, mark for cleanup |

### Event Model Examples

```python
# SESSION_STARTED
{
    "event_type": "SESSION_STARTED",
    "source": "session_service",
    "data": {
        "session_id": "sess_abc123",
        "user_id": "user_12345",
        "metadata": {"platform": "web"},
        "timestamp": "2025-12-15T10:30:00Z"
    }
}

# SESSION_MESSAGE_SENT
{
    "event_type": "SESSION_MESSAGE_SENT",
    "source": "session_service",
    "data": {
        "session_id": "sess_abc123",
        "message_id": "msg_xyz789",
        "user_id": "user_12345",
        "role": "user",
        "content": "Hello, how are you?",
        "message_type": "chat",
        "tokens_used": 10,
        "cost_usd": 0.001,
        "timestamp": "2025-12-15T10:31:00Z"
    }
}
```

---

## Error Handling

### Exception Hierarchy

```python
class SessionServiceError(Exception):
    """Base exception for session service errors"""
    # Maps to HTTP 500

class SessionValidationError(SessionServiceError):
    """Validation error"""
    # Maps to HTTP 400

class SessionNotFoundError(SessionServiceError):
    """Session not found error"""
    # Maps to HTTP 404

class MessageNotFoundError(SessionServiceError):
    """Message not found error"""
    # Maps to HTTP 404

class MemoryNotFoundError(SessionServiceError):
    """Memory not found error (legacy)"""
    # Maps to HTTP 404
```

### HTTP Error Mapping

| Exception | HTTP Code | Response |
|-----------|-----------|----------|
| SessionValidationError | 400 | `{"detail": "error message"}` |
| SessionNotFoundError | 404 | `{"detail": "Session not found: {id}"}` |
| MessageNotFoundError | 404 | `{"detail": "Message not found: {id}"}` |
| SessionServiceError | 500 | `{"detail": "error message"}` |
| Pydantic ValidationError | 422 | `{"detail": [{field errors}]}` |

### Error Response Format

```json
{
    "error": "SessionNotFoundError",
    "detail": "Session not found: sess_nonexistent",
    "timestamp": "2025-12-15T10:30:00Z"
}
```

---

## Performance Considerations

### Database Optimization
- Indexes on user_id, session_id, is_active, created_at
- Composite index on (user_id, is_active) for user session queries
- Pagination enforced to limit result sets
- Parameterized queries prevent SQL injection and enable query caching

### Caching Strategy
- Session data: Consider Redis cache for frequently accessed sessions
- Stats endpoint: Cache aggregate results for 60 seconds
- Message counts: Updated atomically, no separate caching needed

### Connection Pooling
- AsyncPostgresClient manages connection pool
- Pool size configured via environment variables
- Connections reused across requests

### Event Publishing
- Non-blocking async publishing
- Failures logged but don't block main operation
- Retry logic in NATS client

### Memory Management
- Pagination prevents loading large message histories
- Streaming for very large result sets (future)
- Session cleanup via expire_old_sessions job

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=session_service
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8205
LOG_LEVEL=INFO
DEBUG=false

# Database
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061

# NATS Event Bus
NATS_URL=nats://nats:4222

# Consul
CONSUL_ENABLED=true
CONSUL_HOST=consul
CONSUL_PORT=8500

# Feature Flags
ACCOUNT_VALIDATION_ENABLED=true
ACCOUNT_VALIDATION_FAIL_OPEN=true
```

### Health Checks

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8205
  initialDelaySeconds: 10
  periodSeconds: 30

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8205
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Service Registration (Consul)

```json
{
  "service_name": "session_service",
  "version": "1.0.0",
  "tags": ["v1", "user-microservice", "session", "conversation"],
  "capabilities": [
    "session_management",
    "message_management",
    "session_analytics",
    "conversation_tracking",
    "session_persistence",
    "event_driven"
  ],
  "health_check": {
    "type": "http",
    "path": "/health",
    "interval": "30s"
  }
}
```

### Resource Requirements

```yaml
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

---

## Testing Strategy

### Unit Tests (Layer 1)
- Test Pydantic model validation
- Test factory data generation
- No I/O, no mocks needed

### Component Tests (Layer 2)
- Test SessionService with mocked repositories
- Verify business logic and validation
- Verify event publishing calls

### Integration Tests (Layer 3)
- Test with real PostgreSQL
- Test full CRUD lifecycle
- Use X-Internal-Call header

### API Tests (Layer 4)
- Test HTTP endpoints with authentication
- Validate response contracts
- Test error handling

### Smoke Tests (Layer 5)
- End-to-end bash scripts
- Test happy path workflows
- Quick production validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Session Service Team
