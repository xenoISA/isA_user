# Account Service - System Contract (Layer 6)

## Overview

This document defines HOW account_service implements the 12 standard system patterns. It bridges the Logic Contract (business rules) to actual code implementation.

**Service**: account_service
**Port**: 8202
**Category**: User Microservice
**Version**: 2.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/account_service/
├── __init__.py
├── main.py                 # FastAPI app, routes, DI setup, lifespan
├── account_service.py      # Business logic layer
├── account_repository.py   # Data access layer (AsyncPostgresClient)
├── models.py               # Pydantic models (User, AccountProfile, etc.)
├── protocols.py            # DI interfaces (Protocol classes)
├── factory.py              # DI factory (create_account_service)
├── routes_registry.py      # Consul route metadata
├── client.py               # HTTP client for inter-service calls
├── clients/                # Service client implementations
│   ├── __init__.py
│   ├── billing_client.py
│   ├── organization_client.py
│   ├── subscription_client.py
│   └── wallet_client.py
└── events/
    ├── __init__.py
    ├── models.py           # Event Pydantic models
    ├── handlers.py         # NATS event handlers
    └── publishers.py       # Event publishing helpers
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, request validation, DI wiring | FastAPI, AccountService |
| **Service** | `account_service.py` | Business logic, event orchestration | Repository, EventBus, SubscriptionClient |
| **Repository** | `account_repository.py` | Data access, SQL queries | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription processing | AccountService |
| **Models** | `models.py` | Pydantic schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| billing_service | HTTP | Billing integration | localhost:8216 |
| organization_service | HTTP | Organization data | localhost:8212 |
| subscription_service | HTTP | Subscription data | localhost:8228 |
| wallet_service | HTTP | Wallet data | localhost:8209 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
"""
Account Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from .models import User


class DuplicateEntryError(Exception):
    """Duplicate entry error - defined here to avoid importing repository"""
    pass


class UserNotFoundError(Exception):
    """User not found error - defined here to avoid importing repository"""
    pass


@runtime_checkable
class AccountRepositoryProtocol(Protocol):
    async def get_account_by_id(self, user_id: str) -> Optional[User]: ...
    async def get_account_by_id_include_inactive(self, user_id: str) -> Optional[User]: ...
    async def get_account_by_email(self, email: str) -> Optional[User]: ...
    async def ensure_account_exists(self, user_id: str, email: str, name: str) -> User: ...
    async def update_account_profile(self, user_id: str, update_data: Dict[str, Any]) -> Optional[User]: ...
    async def update_account_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool: ...
    async def activate_account(self, user_id: str) -> bool: ...
    async def deactivate_account(self, user_id: str) -> bool: ...
    async def delete_account(self, user_id: str) -> bool: ...
    async def list_accounts(self, limit: int = 50, offset: int = 0, is_active: Optional[bool] = None, search: Optional[str] = None) -> List[User]: ...
    async def search_accounts(self, query: str, limit: int = 50) -> List[User]: ...
    async def get_account_stats(self) -> Dict[str, Any]: ...
    async def get_accounts_by_ids(self, user_ids: List[str]) -> List[User]: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...


@runtime_checkable
class SubscriptionClientProtocol(Protocol):
    async def get_or_create_subscription(self, user_id: str, tier_code: str) -> Optional[Dict[str, Any]]: ...
```

### Factory Implementation (`factory.py`)

```python
def create_account_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    subscription_client=None,
) -> AccountService:
    from .account_repository import AccountRepository
    repository = AccountRepository(config=config)
    return AccountService(
        repository=repository,
        event_bus=event_bus,
        subscription_client=subscription_client,
    )
```

### Service Constructor Pattern

```python
class AccountService:
    def __init__(
        self,
        repository: AccountRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        subscription_client: Optional[SubscriptionClientProtocol] = None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.subscription_client = subscription_client
```

### Testing with Mocks

```python
from unittest.mock import AsyncMock

mock_repository = AsyncMock(spec=AccountRepositoryProtocol)
mock_event_bus = AsyncMock(spec=EventBusProtocol)
mock_subscription_client = AsyncMock(spec=SubscriptionClientProtocol)

service = AccountService(
    repository=mock_repository,
    event_bus=mock_event_bus,
    subscription_client=mock_subscription_client,
)
```

---

## 3. Event Publishing Pattern

### Event Model Definition (`events/models.py`)

Events published when accounts are created, updated, or deleted.

### Published Events

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `account.created` | `account.created` | New account ensured/created | AccountCreatedEventData |
| `account.updated` | `account.updated` | Profile updated | AccountUpdatedEventData |
| `account.deleted` | `account.deleted` | Account soft-deleted | AccountDeletedEventData |
| `account.status_changed` | `account.status_changed` | Account activated/deactivated | AccountStatusChangedEventData |

---

## 4. Error Handling Pattern

### Custom Exceptions

```python
class AccountNotFoundError(Exception): ...
class AccountValidationError(Exception): ...
class AccountServiceError(Exception): ...
```

### HTTP Error Mapping (`main.py`)

```python
@app.exception_handler(AccountValidationError)
async def validation_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(AccountNotFoundError)
async def not_found_error_handler(request, exc):
    return HTTPException(status_code=404, detail=str(exc))

@app.exception_handler(AccountServiceError)
async def service_error_handler(request, exc):
    return HTTPException(status_code=500, detail=str(exc))
```

### HTTP Status Code Mapping

| Exception | HTTP Status | Error Type |
|-----------|-------------|------------|
| AccountNotFoundError | 404 | NOT_FOUND |
| AccountValidationError | 400 | BAD_REQUEST |
| AccountServiceError | 500 | INTERNAL_ERROR |

---

## 5. Client Pattern (Sync Communication)

### Service Clients (`clients/`)

```python
class OrganizationServiceClient:
    """Async client for organization_service"""
    ...

class BillingServiceClient:
    """Async client for billing_service"""
    ...

class WalletServiceClient:
    """Async client for wallet_service"""
    ...

class SubscriptionServiceClient:
    """Async client for subscription_service"""
    ...
```

### Service Discovery Pattern

```python
class AccountServiceClient:
    def __init__(self, config_manager=None):
        self.base_url = "http://localhost:8202"
```

---

## 6. Repository Pattern (Database Access)

### Repository Implementation (`account_repository.py`)

```python
class AccountRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("account_service")
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id="account_service")
```

### Key Repository Methods

| Method | Purpose | SQL Operation |
|--------|---------|---------------|
| `get_account_by_id()` | Get account by user ID | SELECT |
| `ensure_account_exists()` | Create or return existing | INSERT ON CONFLICT |
| `update_account_profile()` | Update profile fields | UPDATE |
| `update_account_preferences()` | Update preferences JSON | UPDATE |
| `delete_account()` | Soft delete | UPDATE is_active=false |
| `list_accounts()` | List with pagination | SELECT LIMIT OFFSET |
| `search_accounts()` | Search by name/email | SELECT WHERE ILIKE |
| `get_account_stats()` | Aggregate statistics | SELECT COUNT |

---

## 7. Service Registration Pattern (Consul)

### Routes Registry (`routes_registry.py`)

```python
ACCOUNT_SERVICE_ROUTES = [
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Service health check"},
    {"path": "/api/v1/accounts/health", "methods": ["GET"], "auth_required": False, "description": "Service health check (API v1)"},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False, "description": "Detailed health check"},
    {"path": "/api/v1/accounts/ensure", "methods": ["POST"], "auth_required": True, ...},
    {"path": "/api/v1/accounts/profile/{user_id}", "methods": ["GET", "PUT", "DELETE"], "auth_required": True, ...},
    {"path": "/api/v1/accounts/preferences/{user_id}", "methods": ["PUT"], "auth_required": True, ...},
    {"path": "/api/v1/accounts", "methods": ["GET"], "auth_required": True, ...},
    {"path": "/api/v1/accounts/search", "methods": ["GET"], "auth_required": True, ...},
    {"path": "/api/v1/accounts/by-email/{email}", "methods": ["GET"], "auth_required": True, ...},
    {"path": "/api/v1/accounts/status/{user_id}", "methods": ["PUT"], "auth_required": True, ...},
    {"path": "/api/v1/accounts/stats", "methods": ["GET"], "auth_required": True, ...},
]

SERVICE_METADATA = {
    "service_name": "account_service",
    "version": "2.0.0",
    "tags": ["v2", "user-microservice", "account", "identity-anchor"],
    "capabilities": [
        "account_management",
        "profile_management",
        "preferences_management",
        "account_search",
        "status_management",
        "subscription_aggregation"
    ]
}
```

### Consul Registration (in `main.py`)

```python
if config.consul_enabled:
    consul_registry = ConsulRegistry(
        service_name=SERVICE_METADATA["service_name"],
        service_port=config.service_port,
        consul_host=config.consul_host,
        consul_port=config.consul_port,
        tags=SERVICE_METADATA["tags"],
        meta=consul_meta,
        health_check_type="ttl"
    )
    consul_registry.register()
    consul_registry.start_maintenance()
```

---

## 8. Health Check Contract

### Endpoints

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/health` | No | Basic health check |
| `/api/v1/accounts/health` | No | API-versioned health check |
| `/health/detailed` | No | Detailed health with DB connectivity |

### Health Response

```json
{
  "status": "healthy",
  "service": "account_service",
  "port": 8202,
  "version": "1.0.0",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

---

## 9. Event System Contract (NATS)

### Event Handlers (`events/handlers.py`)

Subscriptions are registered during lifespan startup:

```python
event_handlers = get_event_handlers()
for event_type, handler in event_handlers.items():
    await event_bus.subscribe_to_events(event_type, handler)
```

### Subscribed Events

| Pattern | Source | Handler |
|---------|--------|---------|
| Service-specific patterns | Various services | `get_event_handlers()` returns map |

---

## 10. Configuration Contract

### ConfigManager Usage

```python
config_manager = ConfigManager("account_service")
config = config_manager.get_service_config()
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ACCOUNT_SERVICE_PORT` | HTTP port | 8202 |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS server URL | nats://nats:4222 |
| `CONSUL_HOST` | Consul host | consul |
| `CONSUL_PORT` | Consul port | 8500 |
| `LOG_LEVEL` | Logging level | INFO |

---

## 11. Logging Contract

### Logger Setup

```python
from core.logger import setup_service_logger
app_logger = setup_service_logger("account_service")
logger = app_logger
```

### Log Categories

| Category | Level | Example |
|----------|-------|---------|
| Startup | INFO | "Initializing account microservice..." |
| Connection | INFO | "Event bus initialized successfully" |
| Consul | INFO | "Service registered with Consul: N routes" |
| Degraded | WARNING | "Failed to initialize event bus" |
| Failure | ERROR | "Failed to initialize account microservice" |

---

## 12. Deployment Contract

### Lifecycle Pattern (main.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Install signal handlers (GracefulShutdown)
    shutdown_manager.install_signal_handlers()
    # 2. Initialize event bus
    event_bus = await get_event_bus("account_service")
    # 3. Register event handlers
    event_handlers = get_event_handlers()
    # 4. Initialize microservice (factory, clients, Consul)
    await account_microservice.initialize(event_bus=event_bus)
    yield
    # Shutdown sequence
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    await account_microservice.shutdown()
```

### Startup Order

1. Install signal handlers (GracefulShutdown)
2. Initialize NATS event bus
3. Subscribe to events
4. Initialize service clients (organization, billing, wallet, subscription)
5. Create account_service via factory
6. Register with Consul (TTL health check)

### Shutdown Order

1. Initiate graceful shutdown
2. Wait for request drain
3. Deregister from Consul
4. Close service clients
5. Close event bus

---

## System Contract Checklist

### Architecture (Section 1)
- [x] Service follows layer structure (main, service, repository, events)
- [x] Clear separation of concerns between layers
- [x] No circular dependencies

### Dependency Injection (Section 2)
- [x] `protocols.py` defines all dependency interfaces
- [x] `factory.py` creates service with DI
- [x] Service constructor accepts protocol types
- [x] No hardcoded dependencies in service layer

### Event Publishing (Section 3)
- [x] Event models defined in `events/models.py`
- [x] Events published after successful operations
- [x] Publishers in `events/publishers.py`

### Error Handling (Section 4)
- [x] Custom exceptions (AccountNotFoundError, AccountValidationError, AccountServiceError)
- [x] Exception to HTTP status mapping
- [x] Consistent error response format

### Client Pattern (Section 5)
- [x] Service clients for billing, organization, subscription, wallet
- [x] Async httpx-based clients
- [x] Service discovery via ConfigManager

### Repository Pattern (Section 6)
- [x] AsyncPostgresClient via gRPC
- [x] Standard CRUD methods
- [x] Soft delete pattern

### Service Registration - Consul (Section 7)
- [x] `routes_registry.py` defines 11 routes
- [x] SERVICE_METADATA with version and 6 capabilities
- [x] TTL health check type
- [x] Consul registration on startup, deregistration on shutdown

### Health Check (Section 8)
- [x] Basic and detailed health endpoints
- [x] Database connectivity check in detailed health

### Event System (Section 9)
- [x] NATS event bus initialization
- [x] Event handler registration via `get_event_handlers()`
- [x] Event publishing via event bus

### Configuration (Section 10)
- [x] ConfigManager usage at module level
- [x] Environment-based configuration
- [x] Service discovery via ConfigManager

### Logging (Section 11)
- [x] setup_service_logger usage
- [x] Structured logging with context

### Deployment (Section 12)
- [x] FastAPI lifespan context manager
- [x] GracefulShutdown with signal handlers
- [x] Ordered startup and shutdown sequences

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/account_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/account_service/account_service.py` | Business logic |
| `microservices/account_service/account_repository.py` | Data access |
| `microservices/account_service/protocols.py` | DI interfaces |
| `microservices/account_service/factory.py` | DI factory |
| `microservices/account_service/models.py` | Pydantic schemas |
| `microservices/account_service/routes_registry.py` | Consul metadata |
| `microservices/account_service/events/handlers.py` | NATS handlers |
| `microservices/account_service/events/models.py` | Event schemas |
| `microservices/account_service/events/publishers.py` | Event publishers |
