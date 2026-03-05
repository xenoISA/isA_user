# Fulfillment Service - System Contract

**Implementation Patterns and Architecture for Fulfillment Service**

This document defines HOW fulfillment_service implements the 12 standard patterns.
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
| **Service Name** | `fulfillment_service` |
| **Port** | `8254` |
| **Schema** | `fulfillment` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/fulfillment_service/` |

---

## Architecture Pattern

### File Structure
```
microservices/fulfillment_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle
├── fulfillment_service.py     # Business logic layer
├── fulfillment_repository.py  # Data access layer (PostgreSQL)
├── models.py                  # Pydantic models (Shipment, Parcel, ShipmentStatus)
├── protocols.py               # DI interfaces
├── factory.py                 # DI factory
├── routes_registry.py         # Consul route registration
├── providers/
│   ├── __init__.py
│   ├── base.py                # Fulfillment provider interface
│   └── mock.py                # Mock provider for testing
├── events/
│   ├── __init__.py
│   ├── models.py              # Event Pydantic models
│   ├── publishers.py          # NATS publish helpers
│   └── handlers.py            # NATS subscribe handlers
└── migrations/
    ├── 001_create_fulfillment_schema.sql
    ├── seed_test_data.sql
    ├── cleanup_test_data.sql
    └── manage_test_data.sh
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring |
| Business | `fulfillment_service.py` | Shipment lifecycle, label gen, cancellation |
| Data | `fulfillment_repository.py` | PostgreSQL queries, schema operations |
| Provider | `providers/` | Pluggable carrier integrations |
| Async | `events/` | NATS event publishing and subscriptions |

---

## Dependency Injection Pattern

### Protocols (`protocols.py`)
```python
@runtime_checkable
class FulfillmentRepositoryProtocol(Protocol):
    async def create_shipment(self, order_id: str, user_id: str, items: List[Dict], shipping_address: Dict, tracking_number: str, status: str) -> Dict[str, Any]: ...
    async def get_shipment(self, shipment_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_shipment_by_order(self, order_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_shipment_by_tracking(self, tracking_number: str) -> Optional[Dict[str, Any]]: ...
    async def create_label(self, shipment_id: str, carrier: str, tracking_number: str) -> bool: ...
    async def cancel_shipment(self, shipment_id: str, reason: str) -> bool: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish(self, subject: str, data: Dict[str, Any]) -> None: ...
```

### Factory (`factory.py`)
```python
from core.config_manager import ConfigManager
from .fulfillment_service import FulfillmentService
from .fulfillment_repository import FulfillmentRepository
from .providers.mock import MockFulfillmentProvider

def create_fulfillment_service(
    config: ConfigManager,
    event_bus=None,
    provider=None,
) -> FulfillmentService:
    repository = FulfillmentRepository(config=config)
    if provider is None:
        provider = MockFulfillmentProvider()
    return FulfillmentService(
        repository=repository,
        event_bus=event_bus,
        provider=provider,
    )
```

---

## Event Publishing Pattern

### Events Published

| Event | Subject | Trigger | Data |
|-------|---------|---------|------|
| `SHIPMENT_PREPARED` | `fulfillment.shipment.prepared` | After shipment creation | `order_id`, `shipment_id`, `user_id`, `items[]`, `shipping_address` |
| `LABEL_CREATED` | `fulfillment.label.created` | After label generation | `order_id`, `shipment_id`, `user_id`, `carrier`, `tracking_number`, `estimated_delivery` |
| `SHIPMENT_CANCELED` | `fulfillment.shipment.canceled` | After cancellation | `order_id`, `shipment_id`, `user_id`, `reason`, `refund_shipping` |
| `SHIPMENT_FAILED` | `fulfillment.shipment.failed` | On shipment failure | `order_id`, `user_id`, `error_code`, `error_message` |

### Event Publishing (`events/publishers.py`)
```python
async def publish_shipment_prepared(
    event_bus, order_id, shipment_id, user_id, items, shipping_address
):
    if event_bus:
        event = ShipmentPreparedEvent(
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            items=items,
            shipping_address=shipping_address,
        )
        await event_bus.publish(
            FulfillmentEventType.SHIPMENT_PREPARED.value,
            {"event_type": "SHIPMENT_PREPARED", "source": "fulfillment_service", "data": event.dict()}
        )

async def publish_label_created(
    event_bus, order_id, shipment_id, user_id, carrier, tracking_number, estimated_delivery
):
    if event_bus:
        event = LabelCreatedEvent(
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            carrier=carrier,
            tracking_number=tracking_number,
            estimated_delivery=estimated_delivery,
        )
        await event_bus.publish(
            FulfillmentEventType.LABEL_CREATED.value,
            {"event_type": "LABEL_CREATED", "source": "fulfillment_service", "data": event.dict()}
        )

async def publish_shipment_canceled(
    event_bus, order_id, shipment_id, user_id, reason, refund_shipping
):
    if event_bus:
        event = ShipmentCanceledEvent(
            order_id=order_id,
            shipment_id=shipment_id,
            user_id=user_id,
            reason=reason,
            refund_shipping=refund_shipping,
        )
        await event_bus.publish(
            FulfillmentEventType.SHIPMENT_CANCELED.value,
            {"event_type": "SHIPMENT_CANCELED", "source": "fulfillment_service", "data": event.dict()}
        )
```

### Event Payload Examples

**fulfillment.shipment.prepared**
```json
{
  "event_type": "SHIPMENT_PREPARED",
  "source": "fulfillment_service",
  "data": {
    "order_id": "ord_abc123",
    "shipment_id": "shp_def456",
    "user_id": "usr_xyz789",
    "items": [
      {"sku_id": "sku_widget_01", "quantity": 2, "weight_grams": 500}
    ],
    "shipping_address": {
      "name": "Jane Doe",
      "street": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94105",
      "country": "US"
    },
    "timestamp": "2026-03-05T11:00:00Z"
  }
}
```

**fulfillment.label.created**
```json
{
  "event_type": "LABEL_CREATED",
  "source": "fulfillment_service",
  "data": {
    "order_id": "ord_abc123",
    "shipment_id": "shp_def456",
    "user_id": "usr_xyz789",
    "carrier": "USPS",
    "tracking_number": "trk_a1b2c3d4e5",
    "estimated_delivery": "2026-03-10T18:00:00Z",
    "timestamp": "2026-03-05T12:00:00Z"
  }
}
```

**fulfillment.shipment.canceled**
```json
{
  "event_type": "SHIPMENT_CANCELED",
  "source": "fulfillment_service",
  "data": {
    "order_id": "ord_abc123",
    "shipment_id": "shp_def456",
    "user_id": "usr_xyz789",
    "reason": "customer_requested",
    "refund_shipping": true,
    "timestamp": "2026-03-05T13:00:00Z"
  }
}
```

---

## Event Subscription Pattern

### Events Subscribed

| Event | Source | Handler |
|-------|--------|---------|
| `tax.calculated` | Tax Service | `handle_tax_calculated` → triggers shipment preparation |
| `payment.completed` | Payment Service | `handle_payment_completed` → confirms shipment readiness |
| `order.canceled` | Order Service | `handle_order_canceled` → cancels shipment |

### Handler Registration (`events/handlers.py`)
```python
def get_event_handlers(service: FulfillmentService) -> Dict[str, Callable]:
    return {
        "tax.calculated": lambda data: service.create_shipment(
            order_id=data["order_id"],
            items=data.get("items", []),
            address=data.get("shipping_address", {}),
            user_id=data.get("user_id", "unknown"),
        ),
        "order.canceled": lambda data: service.cancel_shipment(
            shipment_id=data.get("shipment_id", ""),
            reason="order_canceled",
        ),
    }
```

---

## Client Pattern (Sync)

Fulfillment service has **no sync service clients**. All cross-service communication is event-driven. Carrier integration is via the injected provider.

---

## Repository Pattern

### Database Schema

| Table | Schema | Purpose |
|-------|--------|---------|
| `fulfillment.shipments` | `fulfillment` | Shipment records with full lifecycle |

### Key Indexes

| Index | Table | Columns | Notes |
|-------|-------|---------|-------|
| `idx_shipments_order` | shipments | order_id | |
| `idx_shipments_user` | shipments | user_id | |
| `idx_shipments_tracking` | shipments | tracking_number | Partial: WHERE NOT NULL |
| `idx_shipments_status` | shipments | status | |
| `idx_shipments_carrier` | shipments | carrier | Partial: WHERE NOT NULL |

### Database Design Patterns
- **JSONB items**: Multi-item shipments stored as JSONB array
- **JSONB shipping_address**: Full address for shipping label
- **Lifecycle timestamps**: Separate columns for created_at, label_created_at, shipped_at, delivered_at, canceled_at
- **Status CHECK constraint**: Enforces valid status values at database level
- **Partial indexes**: tracking_number and carrier only indexed when non-NULL
- **Auto-updated timestamps**: Trigger-based `updated_at` management

---

## Service Registration Pattern

### Routes Registry (`routes_registry.py`)
```python
SERVICE_METADATA = {
    "service_name": "fulfillment_service",
    "version": "1.0.0",
    "tags": ['fulfillment', 'v1'],
    "capabilities": ['shipment_creation'],
}

ROUTES = [
    {"path": "/health", "methods": ["GET"], "description": "Health check"},
    {"path": "/api/v1/fulfillment/health", "methods": ["GET"], "description": "Service health check (API v1)"},
]
```

### Consul Registration
- Service registers on startup with health check at `/health`
- Deregisters cleanly on shutdown
- Tags: `fulfillment`, `v1`
- Base path: `/api/v1/fulfillment`

---

## Migration Pattern

### Migration Files
| File | Description |
|------|-------------|
| `001_create_fulfillment_schema.sql` | Create schema, shipments table, indexes, triggers |
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
1. Initialize `FulfillmentRepository` with ConfigManager
2. Call `repository.initialize()` (schema setup)
3. Initialize fulfillment provider (MockFulfillmentProvider by default)
4. Initialize NATS event bus (fail-open)
5. Create `FulfillmentService` with injected dependencies
6. Subscribe to events (`tax.calculated`, `payment.completed`, `order.canceled`)
7. Register with Consul (if enabled)

### Shutdown Sequence
1. Deregister from Consul
2. Close NATS event bus
3. Close repository (database connections)

---

## Configuration Pattern

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8254` | Service port |
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
- `service`: `fulfillment_service`
- `order_id`: Included in all shipment operations
- `shipment_id`: Included after creation
- `user_id`: Included when available
- `carrier`: Included after label creation
- `tracking_number`: Included after label creation
- `status`: Shipment status transitions

### Log Levels
| Level | Usage |
|-------|-------|
| INFO | Service initialization, successful operations, label creation |
| WARNING | Event bus unavailable, provider warnings, non-critical failures |
| ERROR | Provider errors, repository errors, unexpected exceptions |

---

## Compliance Checklist

| Pattern | Implemented | Notes |
|---------|------------|-------|
| Service Identity | Yes | Port 8254, schema `fulfillment` |
| Architecture | Yes | main → service → repository + provider + events |
| Dependency Injection | Yes | Protocols + factory |
| Event Publishing | Yes | 4 event types (prepared, label_created, canceled, failed) |
| Event Subscription | Yes | 3 handlers (tax.calculated, payment.completed, order.canceled) |
| Client Pattern | N/A | No sync clients — provider injected directly |
| Repository | Yes | PostgreSQL with schema + 1 table |
| Service Registration | Yes | Consul with routes_registry.py |
| Migration | Yes | 001_create_fulfillment_schema.sql |
| Lifecycle | Yes | Startup/shutdown with async context manager |
| Configuration | Yes | ConfigManager + environment variables |
| Logging | Yes | Structured logging with shipment context |
