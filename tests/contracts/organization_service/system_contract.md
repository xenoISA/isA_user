# Organization Service - System Contract (Layer 6)

## Overview

This document defines HOW organization_service implements the 12 standard system patterns. It bridges the Logic Contract (business rules) to actual code implementation.

**Service**: organization_service
**Port**: 8212
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/organization_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── organization_service.py          # Business logic layer
├── organization_repository.py       # Data access layer (AsyncPostgresClient)
├── family_sharing_service.py        # Family sharing business logic
├── family_sharing_repository.py     # Family sharing data access
├── family_sharing_models.py         # Family sharing Pydantic models
├── models.py                        # Pydantic models (Organization, Member, etc.)
├── protocols.py                     # DI interfaces (Protocol classes)
├── factory.py                       # DI factory (create_organization_service, create_family_sharing_service)
├── routes_registry.py               # Consul route metadata
├── client.py                        # Service client for external callers
├── clients/
│   ├── __init__.py
│   └── account_client.py            # Account service client
├── events/
│   ├── __init__.py
│   ├── models.py                    # Event Pydantic models
│   ├── handlers.py                  # NATS event handlers
│   └── publishers.py                # NATS event publishers
└── migrations/
    ├── 001_create_organization_tables.sql
    ├── 002_create_family_sharing_tables.sql
    └── 003_add_album_and_smart_frame_resource_types.sql
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, request validation, DI wiring | FastAPI, OrganizationService, FamilySharingService |
| **Service** | `organization_service.py` | Business logic, access control, event publishing | Repository, EventBus |
| **Service** | `family_sharing_service.py` | Family sharing business logic | FamilySharingRepository, EventBus |
| **Repository** | `organization_repository.py` | Data access, SQL queries | AsyncPostgresClient |
| **Repository** | `family_sharing_repository.py` | Family sharing data access | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription processing | OrganizationService |
| **Events** | `events/publishers.py` | NATS event publishing | Event, EventBus |
| **Models** | `models.py` | Pydantic schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | localhost:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| Account Service | HTTP | User validation | localhost:8202 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
@runtime_checkable
class OrganizationRepositoryProtocol(Protocol):
    async def create_organization(self, organization_data: Dict[str, Any], owner_user_id: str) -> Optional[OrganizationResponse]: ...
    async def get_organization(self, organization_id: str) -> Optional[OrganizationResponse]: ...
    async def update_organization(self, organization_id: str, update_data: Dict[str, Any]) -> Optional[OrganizationResponse]: ...
    async def delete_organization(self, organization_id: str) -> bool: ...
    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]: ...
    async def add_organization_member(self, organization_id: str, user_id: str, role: OrganizationRole, permissions: Optional[List[str]] = None) -> Optional[OrganizationMemberResponse]: ...
    async def update_organization_member(self, organization_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[OrganizationMemberResponse]: ...
    async def remove_organization_member(self, organization_id: str, user_id: str) -> bool: ...
    async def get_organization_member(self, organization_id: str, user_id: str) -> Optional[OrganizationMemberResponse]: ...
    async def get_organization_members(self, organization_id: str, limit: int = 100, offset: int = 0, role_filter: Optional[OrganizationRole] = None, status_filter: Optional[MemberStatus] = None) -> List[OrganizationMemberResponse]: ...
    async def get_user_organization_role(self, organization_id: str, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_organization_member_count(self, organization_id: str) -> int: ...
    async def get_organization_stats(self, organization_id: str) -> Dict[str, Any]: ...
    async def list_all_organizations(self, limit: int = 100, offset: int = 0, search: Optional[str] = None, plan_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[OrganizationResponse]: ...

@runtime_checkable
class FamilySharingRepositoryProtocol(Protocol):
    async def create_sharing(self, sharing_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    async def get_sharing(self, sharing_id: str) -> Optional[Dict[str, Any]]: ...
    async def update_sharing(self, sharing_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    async def delete_sharing(self, sharing_id: str) -> bool: ...
    # ... additional sharing methods

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...

@runtime_checkable
class AccountClientProtocol(Protocol):
    async def get_account(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def validate_user_exists(self, user_id: str) -> bool: ...
```

### Service Constructor Pattern

```python
class OrganizationService:
    def __init__(
        self,
        repository: Optional[OrganizationRepositoryProtocol] = None,
        event_bus=None,
        account_client=None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.account_client = account_client
```

---

## 3. Factory Implementation

```python
def create_organization_service(config=None, event_bus=None, account_client=None) -> OrganizationService:
    from .organization_repository import OrganizationRepository
    repository = OrganizationRepository(config=config)
    return OrganizationService(repository=repository, event_bus=event_bus, account_client=account_client)

def create_family_sharing_service(config=None, event_bus=None) -> FamilySharingService:
    from .family_sharing_repository import FamilySharingRepository
    repository = FamilySharingRepository(config=config)
    return FamilySharingService(repository=repository, event_bus=event_bus)
```

---

## 4. Singleton Management

Uses `OrganizationMicroservice` class pattern with global instance:

```python
class OrganizationMicroservice:
    def __init__(self):
        self.organization_service = None
        self.family_sharing_service = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self): ...
    async def shutdown(self): ...

organization_microservice = OrganizationMicroservice()
```

---

## 5. Service Registration (Consul)

### Routes Registry (`routes_registry.py`)

- **Route count**: 20 routes
- **Base path**: `/api/v1/organization`
- **Categories**: health (4), organization_management (3), member_management (2), context_switching (2), statistics (2), admin (1), family_sharing (6)
- **Tags**: `["v1", "user-microservice", "organization"]`
- **Capabilities**: organization_management, member_management, family_sharing, context_switching, usage_tracking

### Consul Registration

- Health check type: TTL
- TTL heartbeat via `consul_registry.start_maintenance()`
- Deregistration on shutdown

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | `{status, service, port, version}` |
| `/api/v1/organization/health` | No | Same |
| `/api/v1/organization/info` | No | ServiceInfo model |
| `/api/v1/organization/stats` | No | ServiceStats model |

---

## 7. Event System Contract (NATS)

### Published Events

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `organization.created` | `organization.created` | Organization created | organization_id, name, billing_email, plan, created_by |
| `organization.updated` | `organization.updated` | Organization updated | organization_id, name, updated_fields, updated_by |
| `organization.deleted` | `organization.deleted` | Organization deleted | organization_id, name, deleted_by |
| `organization.member_added` | `organization.member_added` | Member added | organization_id, user_id, role, added_by |
| `organization.member_removed` | `organization.member_removed` | Member removed | organization_id, user_id, removed_by |
| `organization.sharing.created` | `organization.sharing.created` | Resource shared | organization_id, sharing_id, resource_type, resource_id |
| `organization.sharing.deleted` | `organization.sharing.deleted` | Sharing revoked | organization_id, sharing_id, resource_type |

### Subscribed Events

| Pattern | Source | Handler |
|---------|--------|---------|
| `account_service.user.deleted` | account_service | Remove user from all organizations |
| `album_service.album.deleted` | album_service | Remove sharing references for album |
| `billing_service.billing.subscription_changed` | billing_service | Update organization plan |

---

## 8. Configuration Contract

```python
config_manager = ConfigManager("organization_service")
config = config_manager.get_service_config()
```

| Variable | Description | Default |
|----------|-------------|---------|
| `ORGANIZATION_SERVICE_PORT` | HTTP port | 8212 |
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `NATS_URL` | NATS server URL | nats://nats:4222 |
| `CONSUL_HOST` | Consul host | consul |
| `CONSUL_PORT` | Consul port | 8500 |

---

## 9. Error Handling Contract

### Custom Exceptions

| Exception | HTTP Status | Usage |
|-----------|-------------|-------|
| OrganizationNotFoundError | 404 | Organization not found |
| OrganizationAccessDeniedError | 403 | Permission denied |
| OrganizationValidationError | 400 | Invalid input |
| OrganizationServiceError | 500 | Internal error |
| DuplicateEntryError | N/A | Duplicate member |
| MemberNotFoundError | N/A | Member not found |

---

## 10. Logging Contract

```python
from core.logger import setup_service_logger
app_logger = setup_service_logger("organization_service")
```

| Category | Level | Example |
|----------|-------|---------|
| Startup | INFO | "Initializing organization microservice..." |
| Consul | INFO | "Service registered with Consul: N routes" |
| Events | INFO | "Subscribed to N event types" |
| Operations | INFO | "Organization created: org_id by user user_id" |
| Degraded | WARNING | "Failed to initialize event bus: {e}" |
| Failure | ERROR | "Failed to initialize organization microservice: {e}" |

---

## 11. Testing Contract

```python
from unittest.mock import AsyncMock
mock_repository = AsyncMock(spec=OrganizationRepositoryProtocol)
mock_event_bus = AsyncMock(spec=EventBusProtocol)
service = OrganizationService(repository=mock_repository, event_bus=mock_event_bus)
```

---

## 12. Deployment Contract

### Lifecycle (Lifespan)

1. Install signal handlers (GracefulShutdown)
2. Consul registration with TTL heartbeat
3. Event bus initialization
4. Create services via factory (organization + family sharing)
5. Subscribe to events (user.deleted, album.deleted, billing.subscription_changed)
6. **yield** (app runs)
7. Initiate shutdown, wait for drain
8. Consul deregistration
9. Event bus close
10. Microservice shutdown

### Database Schema

- Schema: `organization`
- Tables: `organizations`, `organization_members`
- Soft delete pattern for organizations and members

---

## System Contract Checklist

- [x] Architecture follows layer structure (main, service, repository, events)
- [x] Protocols define all dependency interfaces
- [x] Factory creates services with DI
- [x] Singleton via OrganizationMicroservice class
- [x] Consul TTL registration with route metadata
- [x] Health check at /health and /api/v1/organization/health
- [x] 7 published events, 3 subscribed events
- [x] ConfigManager for all configuration
- [x] Custom exceptions with HTTP status mapping
- [x] setup_service_logger for structured logging
- [x] GracefulShutdown with signal handlers
- [x] Lifespan context manager for startup/shutdown

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/organization_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/organization_service/organization_service.py` | Business logic |
| `microservices/organization_service/organization_repository.py` | Data access |
| `microservices/organization_service/family_sharing_service.py` | Family sharing logic |
| `microservices/organization_service/family_sharing_repository.py` | Family sharing data access |
| `microservices/organization_service/protocols.py` | DI interfaces |
| `microservices/organization_service/factory.py` | DI factory |
| `microservices/organization_service/models.py` | Pydantic schemas |
| `microservices/organization_service/routes_registry.py` | Consul metadata |
| `microservices/organization_service/events/handlers.py` | NATS handlers |
| `microservices/organization_service/events/publishers.py` | NATS publishers |
| `microservices/organization_service/events/models.py` | Event schemas |
