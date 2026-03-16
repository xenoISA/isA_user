# Product Service - System Contract (Layer 6)

## Overview

This document defines HOW product_service implements the 12 standard system patterns.

**Service**: product_service
**Port**: 8215
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/product_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── product_service.py               # Business logic layer
├── product_repository.py            # Data access layer
├── models.py                        # Pydantic models (Product, PricingModel, etc.)
├── protocols.py                     # DI interfaces (Protocol classes)
├── factory.py                       # DI factory (create_product_service)
├── routes_registry.py               # Consul route metadata
├── client.py                        # Service client for external callers
├── clients/
│   ├── __init__.py
│   ├── account_client.py
│   ├── organization_client.py
│   └── subscription_client.py
├── events/
│   ├── __init__.py
│   ├── models.py
│   ├── handlers.py
│   └── publishers.py
└── migrations/
    ├── 001_migrate_to_product_schema.sql
    ├── 002_add_subscription_tiers_and_cost_definitions.sql
    ├── 003_seed_subscription_tiers_and_costs.sql
    ├── 005_add_commerce_columns_and_variants.sql
    └── 006_backfill_commerce_defaults.sql
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, request validation | FastAPI, ProductService |
| **Service** | `product_service.py` | Business logic, pricing calculations | Repository, EventBus, Clients |
| **Repository** | `product_repository.py` | Data access, SQL queries | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription processing | ProductService |
| **Models** | `models.py` | Pydantic schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | postgres:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| Account Service | HTTP | User validation | localhost:8202 |
| Organization Service | HTTP | Org validation | localhost:8212 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
@runtime_checkable
class ProductRepositoryProtocol(Protocol):
    async def get_product(self, product_id: str) -> Optional[Product]: ...
    async def get_products(self, category=None, product_type=None, is_active=True, limit=100, offset=0) -> List[Product]: ...
    async def create_product(self, product: Product) -> Optional[Product]: ...
    async def get_categories(self) -> List[ProductCategory]: ...
    async def get_product_pricing(self, product_id: str, user_id=None, subscription_id=None) -> Optional[Dict]: ...
    async def create_subscription(self, subscription: UserSubscription) -> UserSubscription: ...
    async def get_subscription(self, subscription_id: str) -> Optional[UserSubscription]: ...
    async def record_product_usage(self, user_id: str, ...) -> str: ...
    async def get_usage_records(self, ...) -> List[Dict]: ...
    async def get_usage_statistics(self, ...) -> Dict[str, Any]: ...
    async def initialize(self) -> None: ...
    async def close(self) -> None: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...
    async def subscribe_to_events(self, pattern: str, handler: Any) -> None: ...
    async def close(self) -> None: ...

class AccountClientProtocol(Protocol):
    async def get_user(self, user_id: str) -> Optional[Dict]: ...
    async def validate_user(self, user_id: str) -> bool: ...

class OrganizationClientProtocol(Protocol):
    async def get_organization(self, organization_id: str) -> Optional[Dict]: ...
```

### Custom Exceptions

| Exception | Description |
|-----------|-------------|
| ProductNotFoundError | Product not found |
| SubscriptionNotFoundError | Subscription not found |
| PlanNotFoundError | Service plan not found |
| UsageRecordingError | Usage recording failed |

---

## 3. Factory Implementation

```python
async def create_product_service(config=None, event_bus=None, account_client=None, organization_client=None) -> ProductService:
    from .product_repository import ProductRepository
    repository = ProductRepository(config=config)
    await repository.initialize()
    return ProductService(repository=repository, event_bus=event_bus, account_client=account_client, organization_client=organization_client)
```

Note: Factory is async because repository requires initialization.

---

## 4. Singleton Management

Global variable pattern:
```python
product_service: Optional[ProductService] = None
repository: Optional[ProductRepository] = None
```

---

## 5. Service Registration (Consul)

- **Route count**: 15 routes
- **Base path**: `/api/v1/product`
- **Tags**: `["v1", "product", "catalog", "subscription", "user-microservice"]`
- **Capabilities**: product_catalog, pricing_management, subscription_management, usage_tracking, quota_management, service_plans
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | Status with database dependency check |
| `/api/v1/product/health` | No | Same |
| `/api/v1/product/info` | No | Service capabilities and supported types |

---

## 7. Event System Contract (NATS)

### Subscribed Events

Event handlers registered via `get_event_handlers(product_service)` pattern.

### Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return HTTPException(status_code=500, detail="Internal server error occurred")
```

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `PRODUCT_SERVICE_PORT` | HTTP port | 8215 |
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |

---

## 9. Error Handling Contract

Consistent try/except pattern in all route handlers, mapping to HTTP 400/404/500 as appropriate.

---

## 10. Logging Contract

```python
logger = setup_service_logger("product_service", level=config.log_level.upper())
```

---

## 11. Testing Contract

```python
from unittest.mock import AsyncMock
mock_repo = AsyncMock(spec=ProductRepositoryProtocol)
service = ProductService(repository=mock_repo, event_bus=AsyncMock())
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize repository with `await repository.initialize()`
3. Initialize service clients (Account, Organization)
4. Initialize event bus
5. Create ProductService
6. Register event handlers
7. Consul TTL registration
8. **yield**
9. Graceful shutdown
10. Consul deregistration
11. Close clients, event bus, repository

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/product_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/product_service/product_service.py` | Business logic |
| `microservices/product_service/product_repository.py` | Data access |
| `microservices/product_service/protocols.py` | DI interfaces |
| `microservices/product_service/factory.py` | DI factory |
| `microservices/product_service/models.py` | Pydantic schemas |
| `microservices/product_service/routes_registry.py` | Consul metadata |
| `microservices/product_service/events/handlers.py` | NATS handlers |
| `microservices/product_service/events/models.py` | Event schemas |
