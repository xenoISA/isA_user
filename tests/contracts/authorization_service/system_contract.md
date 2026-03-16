# Authorization Service - System Contract (Layer 6)

## Overview

This document defines HOW authorization_service implements the 12 standard system patterns.

**Service**: authorization_service
**Port**: 8203
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/authorization_service/
├── main.py                         # FastAPI app, routes, DI setup, lifespan
├── authorization_service.py        # Business logic layer
├── authorization_repository.py     # Data access layer (AsyncPostgresClient)
├── models.py                       # Pydantic models (ResourcePermission, etc.)
├── protocols.py                    # DI interfaces (Protocol classes)
├── factory.py                      # DI factory (create_authorization_service)
├── routes_registry.py              # Consul route metadata
├── client.py                       # HTTP client for inter-service calls
├── clients/                        # Service client implementations
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    └── publishers.py
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, error handling | FastAPI, AuthorizationService |
| **Service** | `authorization_service.py` | Permission logic, multi-level auth | Repository, EventBus, Config |
| **Repository** | `authorization_repository.py` | Data access, SQL queries | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription processing | AuthorizationService |
| **Models** | `models.py` | Permission schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class AuthorizationException(Exception): ...
class PermissionNotFoundException(AuthorizationException): ...
class UserNotFoundException(AuthorizationException): ...
class OrganizationNotFoundException(AuthorizationException): ...
class InvalidPermissionError(AuthorizationException): ...

@runtime_checkable
class AuthorizationRepositoryProtocol(Protocol):
    async def create_resource_permission(self, permission: ResourcePermission) -> bool: ...
    async def get_resource_permission(self, resource_type: ResourceType, resource_name: str) -> Optional[ResourcePermission]: ...
    async def grant_user_permission(self, permission: UserPermissionRecord) -> bool: ...
    async def revoke_user_permission(self, user_id: str, resource_type: ResourceType, resource_name: str) -> bool: ...
    async def get_user_permission(self, user_id: str, resource_type: ResourceType, resource_name: str) -> Optional[UserPermissionRecord]: ...
    async def list_user_permissions(self, user_id: str, resource_type: Optional[ResourceType] = None) -> List[UserPermissionRecord]: ...
    async def get_organization_permission(self, organization_id: str, resource_type: ResourceType, resource_name: str) -> Optional[OrganizationPermission]: ...
    async def get_user_permission_summary(self, user_id: str) -> Optional[UserPermissionSummary]: ...
    async def log_permission_action(self, audit_log: PermissionAuditLog) -> bool: ...
    async def cleanup_expired_permissions(self) -> int: ...
    async def cleanup(self) -> None: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...
```

### Factory Implementation (`factory.py`)

```python
def create_authorization_service(config=None, event_bus=None) -> AuthorizationService:
    from .authorization_repository import AuthorizationRepository
    repository = AuthorizationRepository(config=config)
    return AuthorizationService(repository=repository, event_bus=event_bus, config=config)
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Subject | Trigger |
|-------|---------|---------|
| `permission.granted` | `permission.granted` | Permission granted to user |
| `permission.revoked` | `permission.revoked` | Permission revoked from user |

### Subscribed Events

Event handlers subscribe to patterns like `*.{event_type}` for relevant authorization events.

---

## 4. Error Handling Pattern

### HTTP Status Code Mapping

| Exception | HTTP Status | Error Type |
|-----------|-------------|------------|
| PermissionNotFoundException | 404 | NOT_FOUND |
| InvalidPermissionError | 400 | BAD_REQUEST |
| AuthorizationException | 500 | INTERNAL_ERROR |
| General Exception | 500 | INTERNAL_ERROR (global handler) |

---

## 5. Client Pattern (Sync Communication)

Authorization service is primarily a **provider** of authorization decisions. Other services call it for access checks.

---

## 6. Repository Pattern (Database Access)

### Key Repository Methods

| Method | Purpose |
|--------|---------|
| `create_resource_permission()` | Define resource permissions |
| `grant_user_permission()` | Grant access to user |
| `revoke_user_permission()` | Revoke user access |
| `get_user_permission_summary()` | Full permission summary |
| `cleanup_expired_permissions()` | TTL-based cleanup |

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    "service_name": "authorization_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "authorization", "permissions"],
    "capabilities": [
        "resource_access_control",
        "permission_management",
        "bulk_operations",
        "multi_level_authorization",
        "subscription_authorization",
        "organization_authorization"
    ]
}
```

13 routes: health (5), core auth (3), permission management (2), bulk operations (2), admin (1).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/health` | No | Basic health check |
| `/api/v1/authorization/health` | No | API-versioned health check |
| `/health/detailed` | No | Detailed health with DB connectivity |
| `/api/v1/authorization/info` | No | Service information |
| `/api/v1/authorization/stats` | No | Service statistics |

---

## 9. Event System Contract (NATS)

```python
from .events import AuthorizationEventHandlers
event_handlers = AuthorizationEventHandlers(authorization_service)
handler_map = event_handlers.get_event_handler_map()
for event_type, handler_func in handler_map.items():
    await event_bus.subscribe_to_events(pattern=f"*.{event_type}", handler=handler_func)
```

---

## 10. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTHORIZATION_SERVICE_PORT` | HTTP port | 8203 |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS server URL | nats://nats:4222 |

---

## 11. Logging Contract

```python
app_logger = setup_service_logger("authorization_service")
```

---

## 12. Deployment Contract

### Startup Order

1. Install signal handlers (GracefulShutdown)
2. Initialize NATS event bus
3. Create authorization_service via factory
4. Subscribe to events
5. Initialize default permissions
6. Register with Consul (TTL)

### Shutdown Order

1. Initiate graceful shutdown, wait for drain
2. Deregister from Consul
3. Close event bus
4. Cleanup authorization_service resources

---

## System Contract Checklist

- [x] `protocols.py` defines AuthorizationRepositoryProtocol and EventBusProtocol
- [x] `factory.py` creates service with DI
- [x] Exception hierarchy (AuthorizationException base)
- [x] Global exception handler in main.py
- [x] Consul TTL registration with 13 routes
- [x] GracefulShutdown with signal handlers
- [x] Default permissions initialized on startup

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/authorization_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/authorization_service/authorization_service.py` | Business logic |
| `microservices/authorization_service/authorization_repository.py` | Data access |
| `microservices/authorization_service/protocols.py` | DI interfaces |
| `microservices/authorization_service/factory.py` | DI factory |
| `microservices/authorization_service/routes_registry.py` | Consul metadata |
| `microservices/authorization_service/events/` | Event handlers, models, publishers |
