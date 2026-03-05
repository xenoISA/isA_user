# Inventory Service - System Contract

**Implementation Patterns and Architecture for Inventory Service**

This document defines HOW inventory_service implements the 12 standard patterns.
Pattern Reference: `.claude/skills/cdd-system-contract/SKILL.md`

---

## Table of Contents

1. [Service Identity](#service-identity)
2. [Architecture Pattern](#architecture-pattern)
3. [Dependency Injection Pattern](#dependency-injection-pattern)
4. [Event Publishing Pattern](#event-publishing-pattern)
5. [Event Subscription Pattern](#event-subscription-pattern)
6. [Client Pattern (Sync)](#client-pattern-sync)
7. [Repository Pattern](#repository-pattern)
8. [Service Registration Pattern](#service-registration-pattern)
9. [Migration Pattern](#migration-pattern)
10. [Lifecycle Pattern](#lifecycle-pattern)
11. [Configuration Pattern](#configuration-pattern)
12. [Logging Pattern](#logging-pattern)

---

## Service Identity

| Property | Value |
|----------|-------|
| **Service Name** | `inventory_service` |
| **Port** | `8252` |
| **Schema** | `inventory` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/inventory_service/` |

---

## Architecture Pattern

### File Structure
```
microservices/inventory_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle
├── inventory_service.py       # Business logic layer
├── inventory_repository.py    # Data access layer (PostgreSQL)
├── models.py                  # Pydantic models (InventoryItem, InventoryReservation)
├── protocols.py               # DI interfaces
├── factory.py                 # DI factory
├── routes_registry.py         # Consul route registration
├── events/
│   ├── __init__.py
│   ├── models.py              # Event Pydantic models
│   ├── publishers.py          # NATS publish helpers
│   └── handlers.py            # NATS subscribe handlers
└── migrations/
    ├── 001_create_inventory_schema.sql
    ├── seed_test_data.sql
    ├── cleanup_test_data.sql
    └── manage_test_data.sh
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring |
| Business | `inventory_service.py` | Reserve, commit, release lifecycle |
| Data | `inventory_repository.py` | PostgreSQL queries, schema operations |
| Async | `events/` | NATS event publishing and subscriptions |

---

## Dependency Injection Pattern

### Protocols (`protocols.py`)
```python
@runtime_checkable
class InventoryRepositoryProtocol(Protocol):
    async def create_reservation(self, order_id: str, user_id: str, items: List[Dict], expires_in_minutes: int) -> Dict[str, Any]: ...
    async def get_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_reservation_by_order(self, order_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_active_reservation_for_order(self, order_id: str) -> Optional[Dict[str, Any]]: ...
    async def commit_reservation(self, reservation_id: str) -> bool: ...
    async def release_reservation(self, reservation_id: str) -> bool: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish(self, subject: str, data: Dict[str, Any]) -> None: ...
```

### Factory (`factory.py`)
```python
from core.config_manager import ConfigManager
from .inventory_service import InventoryService
from .inventory_repository import InventoryRepository

def create_inventory_service(
    config: ConfigManager,
    event_bus=None,
) -> InventoryService:
    repository = InventoryRepository(config=config)
    return InventoryService(
        repository=repository,
        event_bus=event_bus,
    )
```

---

## Event Publishing Pattern

### Events Published

| Event | Subject | Trigger | Data |
|-------|---------|---------|------|
| `STOCK_RESERVED` | `inventory.reserved` | After reservation creation | `order_id`, `reservation_id`, `user_id`, `items[]`, `expires_at` |
| `STOCK_COMMITTED` | `inventory.committed` | After reservation commit | `order_id`, `reservation_id`, `user_id`, `items[]` |
| `STOCK_RELEASED` | `inventory.released` | After reservation release | `order_id`, `reservation_id`, `user_id`, `items[]`, `reason` |
| `STOCK_FAILED` | `inventory.failed` | On reservation failure | `order_id`, `user_id`, `items[]`, `error_code`, `error_message` |

### Event Publishing (`events/publishers.py`)
```python
async def publish_stock_reserved(
    event_bus, order_id, reservation_id, user_id, items, expires_at
):
    if event_bus:
        event = StockReservedEvent(
            order_id=order_id,
            reservation_id=reservation_id,
            user_id=user_id,
            items=items,
            expires_at=expires_at,
        )
        await event_bus.publish(
            InventoryEventType.STOCK_RESERVED.value,
            {"event_type": "STOCK_RESERVED", "source": "inventory_service", "data": event.dict()}
        )
```

### Event Payload Examples

**inventory.reserved**
```json
{
  "event_type": "STOCK_RESERVED",
  "source": "inventory_service",
  "data": {
    "order_id": "ord_abc123",
    "reservation_id": "res_def456",
    "user_id": "usr_xyz789",
    "items": [
      {"sku_id": "sku_widget_01", "quantity": 2, "unit_price": 29.99}
    ],
    "expires_at": "2026-03-05T11:30:00Z",
    "timestamp": "2026-03-05T11:00:00Z"
  }
}
```

---

## Event Subscription Pattern

### Events Subscribed

| Event | Source | Handler |
|-------|--------|---------|
| `order.created` | Order Service | `handle_order_created` → calls `reserve_inventory()` |
| `payment.completed` | Payment Service | `handle_payment_completed` → calls `commit_reservation()` |
| `order.canceled` | Order Service | `handle_order_canceled` → calls `release_reservation()` |

### Handler Registration (`events/handlers.py`)
```python
def get_event_handlers(service: InventoryService) -> Dict[str, Callable]:
    return {
        "order.created": lambda data: service.reserve_inventory(
            order_id=data["order_id"], items=data["items"], user_id=data.get("user_id", "unknown")
        ),
        "payment.completed": lambda data: service.commit_reservation(
            order_id=data["order_id"]
        ),
        "order.canceled": lambda data: service.release_reservation(
            order_id=data["order_id"], reason="order_canceled"
        ),
    }
```

---

## Client Pattern (Sync)

Inventory service has **no sync service clients**. All cross-service communication is event-driven.

---

## Repository Pattern

### Database Schema

| Table | Schema | Purpose |
|-------|--------|---------|
| `inventory.stock_levels` | `inventory` | SKU stock tracking per location |
| `inventory.reservations` | `inventory` | Order reservations with lifecycle |

### Key Indexes

| Index | Table | Columns | Notes |
|-------|-------|---------|-------|
| `idx_stock_levels_sku` | stock_levels | sku_id | |
| `idx_stock_levels_location` | stock_levels | location_id | |
| `idx_reservations_order` | reservations | order_id | |
| `idx_reservations_user` | reservations | user_id | |
| `idx_reservations_status` | reservations | status | |
| `idx_reservations_expires` | reservations | expires_at | Partial: WHERE status = 'active' |

### Database Design Patterns
- **Computed columns**: `available` = `on_hand - reserved` (GENERATED ALWAYS AS)
- **JSONB items**: Multi-item reservations stored as JSONB array
- **Auto-updated timestamps**: Trigger-based `updated_at` management
- **Partial indexes**: Active reservation expiry index for efficient cleanup

---

## Service Registration Pattern

### Routes Registry (`routes_registry.py`)
```python
SERVICE_METADATA = {
    "service_name": "inventory_service",
    "version": "1.0.0",
    "tags": ['inventory', 'v1'],
    "capabilities": ['inventory_reservation', 'inventory_commit', 'inventory_release'],
}

ROUTES = [
    {"path": "/health", "methods": ["GET"], "description": "Health check"},
    {"path": "/api/v1/inventory/health", "methods": ["GET"], "description": "Service health check (API v1)"},
]
```

### Consul Registration
- Service registers on startup with health check at `/health`
- Deregisters cleanly on shutdown
- Tags: `inventory`, `v1`
- Base path: `/api/v1/inventory`

---

## Migration Pattern

### Migration Files
| File | Description |
|------|-------------|
| `001_create_inventory_schema.sql` | Create schema, tables (stock_levels, reservations), indexes, triggers |
| `seed_test_data.sql` | Test data for development |
| `cleanup_test_data.sql` | Remove test data |
| `manage_test_data.sh` | Shell helper for test data lifecycle |

### Schema Evolution
- Migrations are numbered sequentially (001, 002, ...)
- Each migration is idempotent (`CREATE IF NOT EXISTS`, `DROP IF EXISTS`)
- Applied during repository initialization

---

## Lifecycle Pattern

### Startup Sequence
1. Initialize `InventoryRepository` with ConfigManager
2. Call `repository.initialize()` (schema setup)
3. Initialize NATS event bus (fail-open)
4. Create `InventoryService` with injected dependencies
5. Subscribe to events (`order.created`, `payment.completed`, `order.canceled`)
6. Register with Consul (if enabled)

### Shutdown Sequence
1. Deregister from Consul
2. Close NATS event bus
3. Close repository (database connections)

---

## Configuration Pattern

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8252` | Service port |
| `CONSUL_PORT` | `8500` | Consul port |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `NATS_URL` | `nats://localhost:4222` | NATS server URL |

### ConfigManager Usage
- ConfigManager is initialized from environment variables
- Passed to repository and factory constructors
- Provides database connection parameters and service settings

---

## Logging Pattern

### Logger Setup
```python
logger = logging.getLogger(__name__)
```

### Structured Fields
- `service`: `inventory_service`
- `order_id`: Included in all reservation operations
- `reservation_id`: Included after creation
- `user_id`: Included when available
- `status`: Reservation status transitions

### Log Levels
| Level | Usage |
|-------|-------|
| INFO | Service initialization, successful operations |
| WARNING | Event bus unavailable, non-critical failures |
| ERROR | Repository errors, unexpected exceptions |

---

## Compliance Checklist

| Pattern | Implemented | Notes |
|---------|------------|-------|
| Service Identity | Yes | Port 8252, schema `inventory` |
| Architecture | Yes | main → service → repository + events |
| Dependency Injection | Yes | Protocols + factory |
| Event Publishing | Yes | 4 event types (reserved, committed, released, failed) |
| Event Subscription | Yes | 3 handlers (order.created, payment.completed, order.canceled) |
| Client Pattern | N/A | No sync clients — event-driven only |
| Repository | Yes | PostgreSQL with schema + 2 tables |
| Service Registration | Yes | Consul with routes_registry.py |
| Migration | Yes | 001_create_inventory_schema.sql |
| Lifecycle | Yes | Startup/shutdown with async context manager |
| Configuration | Yes | ConfigManager + environment variables |
| Logging | Yes | Structured logging with operation context |
