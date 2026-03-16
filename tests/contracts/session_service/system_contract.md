# Session Service - System Contract (Layer 6)

## Overview

This document defines HOW session_service implements the 12 standard system patterns.

**Service**: session_service
**Port**: 8205
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/session_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── session_service.py               # Business logic layer
├── session_repository.py            # Data access (SessionRepository + SessionMessageRepository)
├── models.py                        # Pydantic models (Session, SessionMessage, etc.)
├── protocols.py                     # DI interfaces (Protocol classes)
├── factory.py                       # DI factory (create_session_service)
├── routes_registry.py               # Consul route metadata
├── clients/
│   ├── __init__.py
│   ├── account_client.py
│   ├── memory_client.py
│   ├── notification_client.py
│   └── session_client.py
├── events/
│   ├── __init__.py
│   ├── models.py                    # Event Pydantic models
│   ├── handlers.py                  # NATS event handlers (SessionEventHandlers class)
│   └── publishers.py                # NATS event publishers
└── migrations/
    ├── 001_create_sessions_table.sql
    ├── 002_create_session_messages_table.sql
    ├── 003_create_session_memories_table.sql
    ├── 004_fix_decimal_types.sql
    ├── 005_fix_uuid_types.sql
    └── 006_drop_session_memories.sql
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, memory proxy routes | FastAPI, SessionService |
| **Service** | `session_service.py` | Business logic, session lifecycle | SessionRepo, MessageRepo, EventBus |
| **Repository** | `session_repository.py` | Data access (two repositories) | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription (class-based) | SessionService |
| **Models** | `models.py` | Pydantic schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | postgres:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| Memory Service | HTTP (proxy) | Session memory storage | localhost:8223 |
| Account Service | HTTP | User validation | localhost:8202 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
@runtime_checkable
class SessionRepositoryProtocol(Protocol):
    async def create_session(self, session_data: Dict) -> Optional[Session]: ...
    async def get_by_session_id(self, session_id: str) -> Optional[Session]: ...
    async def get_user_sessions(self, user_id: str, active_only=False, limit=50, offset=0) -> List[Session]: ...
    async def update_session_status(self, session_id: str, status: str) -> bool: ...
    async def update_session_activity(self, session_id: str) -> bool: ...
    async def increment_message_count(self, session_id: str, tokens_used=0, cost_usd=0.0) -> bool: ...
    async def expire_old_sessions(self, hours_old=24) -> int: ...

@runtime_checkable
class SessionMessageRepositoryProtocol(Protocol):
    async def create_message(self, message_data: Dict) -> Optional[SessionMessage]: ...
    async def get_session_messages(self, session_id: str, limit=100, offset=0) -> List[SessionMessage]: ...
    async def get_message_by_id(self, message_id: str) -> Optional[SessionMessage]: ...
    async def delete_session_messages(self, session_id: str) -> int: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...

class AccountClientProtocol(Protocol):
    async def get_account_profile(self, user_id: str) -> Optional[Dict]: ...
    async def check_user_exists(self, user_id: str) -> bool: ...

class MemoryClientProtocol(Protocol):
    async def create_session_memory(self, session_id: str, user_id: str, content: str, memory_type: str) -> Optional[Dict]: ...
    async def get_session_memory(self, session_id: str, memory_type: Optional[str] = None) -> List[Dict]: ...
```

### Custom Exceptions

| Exception | HTTP Status |
|-----------|-------------|
| SessionNotFoundError | 404 |
| MessageNotFoundError | 404 |
| MemoryNotFoundError | 404 |
| SessionServiceError | 500 |
| SessionValidationError | 400 |
| DuplicateSessionError | N/A |

---

## 3. Factory Implementation

```python
def create_session_service(config=None, event_bus=None, account_client=None) -> SessionService:
    from .session_repository import SessionRepository, SessionMessageRepository
    session_repository = SessionRepository(config=config)
    message_repository = SessionMessageRepository(config=config)
    if account_client is None:
        from microservices.account_service.client import AccountServiceClient
        account_client = AccountServiceClient()
    return SessionService(session_repo=session_repository, message_repo=message_repository, event_bus=event_bus, account_client=account_client)
```

Also provides `create_session_service_for_testing()` for injecting mocks.

---

## 4. Singleton Management

Uses `SessionMicroservice` class pattern:
```python
class SessionMicroservice:
    def __init__(self):
        self.session_service = None
        self.event_bus = None
        self.consul_registry = None
session_microservice = SessionMicroservice()
```

---

## 5. Service Registration (Consul)

- **Route count**: 14 routes
- **Base path**: `/api/v1/sessions`
- **Tags**: `["v1", "user-microservice", "session", "conversation"]`
- **Capabilities**: session_management, message_management, session_analytics, conversation_tracking, session_persistence, event_driven
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | `{status, service, port, version, timestamp}` |
| `/api/v1/sessions/health` | No | Same |
| `/health/detailed` | No | SessionServiceStatus with database_connected |

---

## 7. Event System Contract (NATS)

### Published Events

| Event | Subject | Trigger |
|-------|---------|---------|
| `session.started` | `session.started` | Session created |
| `session.ended` | `session.ended` | Session ended |
| `session.message_sent` | `session.message_sent` | Message added |
| `session.tokens_used` | `session.tokens_used` | Tokens consumed |

### Subscribed Events

| Pattern | Source | Handler |
|---------|--------|---------|
| `account_service.user.deleted` | account_service | End all user sessions |

Event handler uses class-based pattern (`SessionEventHandlers` with `get_event_handler_map()`).

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `SESSION_SERVICE_PORT` | HTTP port | 8205 |
| `MEMORY_SERVICE_URL` | Memory service URL | http://localhost:8223 |

---

## 9. Error Handling Contract

Exception handlers registered at app level:
```python
@app.exception_handler(SessionValidationError) -> 400
@app.exception_handler(SessionNotFoundError) -> 404
@app.exception_handler(SessionServiceError) -> 500
```

---

## 10. Logging Contract

```python
app_logger = setup_service_logger("session_service")
```

---

## 11. Testing Contract

```python
from .factory import create_session_service_for_testing
service = create_session_service_for_testing(
    session_repo=mock_session_repo,
    message_repo=mock_message_repo,
    event_bus=mock_event_bus,
)
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize event bus
3. Initialize SessionMicroservice (factory creates repos + service)
4. Subscribe to events (class-based handler map)
5. Consul TTL registration
6. **yield**
7. Graceful shutdown
8. Session microservice shutdown (Consul deregister + event bus close)

### Special: Memory Proxy Routes

Session service proxies `/api/v1/sessions/{session_id}/memory` (GET/POST) to memory_service via httpx for SDK compatibility.

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/session_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/session_service/session_service.py` | Business logic |
| `microservices/session_service/session_repository.py` | Data access |
| `microservices/session_service/protocols.py` | DI interfaces |
| `microservices/session_service/factory.py` | DI factory |
| `microservices/session_service/models.py` | Pydantic schemas |
| `microservices/session_service/routes_registry.py` | Consul metadata |
| `microservices/session_service/events/handlers.py` | NATS handlers |
| `microservices/session_service/events/models.py` | Event schemas |
