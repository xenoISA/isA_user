# Tax Service - System Contract

**Implementation Patterns and Architecture for Tax Service**

This document defines HOW tax_service implements the 12 standard patterns.
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
| **Service Name** | `tax_service` |
| **Port** | `8253` |
| **Schema** | `tax` |
| **Version** | `1.0.0` |
| **Reference Implementation** | `microservices/tax_service/` |

---

## Architecture Pattern

### File Structure
```
microservices/tax_service/
├── __init__.py
├── main.py                    # FastAPI app + lifecycle
├── tax_service.py             # Business logic layer
├── tax_repository.py          # Data access layer (PostgreSQL)
├── models.py                  # Pydantic models (TaxCalculation, TaxLine)
├── protocols.py               # DI interfaces
├── factory.py                 # DI factory
├── routes_registry.py         # Consul route registration
├── providers/
│   ├── __init__.py
│   ├── base.py                # Tax provider interface
│   └── mock.py                # Mock tax provider for testing
├── events/
│   ├── __init__.py
│   ├── models.py              # Event Pydantic models
│   ├── publishers.py          # NATS publish helpers
│   └── handlers.py            # NATS subscribe handlers
└── migrations/
    ├── 001_create_tax_schema.sql
    ├── seed_test_data.sql
    ├── cleanup_test_data.sql
    └── manage_test_data.sh
```

### Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|----------------|
| HTTP | `main.py` | Routes, validation, DI wiring |
| Business | `tax_service.py` | Calculation orchestration, preview vs persistent |
| Data | `tax_repository.py` | PostgreSQL queries, schema operations |
| Provider | `providers/` | Pluggable tax calculation engines |
| Async | `events/` | NATS event publishing and subscriptions |

---

## Dependency Injection Pattern

### Protocols (`protocols.py`)
```python
@runtime_checkable
class TaxRepositoryProtocol(Protocol):
    async def create_calculation(self, order_id: str, user_id: str, subtotal: float, total_tax: float, currency: str, tax_lines: List[Dict], shipping_address: Dict) -> Dict[str, Any]: ...
    async def get_calculation_by_order(self, order_id: str) -> Optional[Dict[str, Any]]: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish(self, subject: str, data: Dict[str, Any]) -> None: ...
```

### Factory (`factory.py`)
```python
from core.config_manager import ConfigManager
from .tax_service import TaxService
from .tax_repository import TaxRepository
from .providers.mock import MockTaxProvider

def create_tax_service(
    config: ConfigManager,
    event_bus=None,
    provider=None,
) -> TaxService:
    repository = TaxRepository(config=config)
    if provider is None:
        provider = MockTaxProvider()
    return TaxService(
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
| `TAX_CALCULATED` | `tax.calculated` | After persistent calculation | `order_id`, `calculation_id`, `user_id`, `subtotal`, `total_tax`, `currency`, `tax_lines[]`, `shipping_address` |
| `TAX_FAILED` | `tax.failed` | On calculation failure | `order_id`, `user_id`, `error_code`, `error_message`, `items[]` |

### Event Publishing (`events/publishers.py`)
```python
async def publish_tax_calculated(
    event_bus, order_id, calculation_id, user_id, subtotal, total_tax, currency, tax_lines, shipping_address
):
    if event_bus:
        event = TaxCalculatedEvent(
            order_id=order_id,
            calculation_id=calculation_id,
            user_id=user_id,
            subtotal=subtotal,
            total_tax=total_tax,
            currency=currency,
            tax_lines=tax_lines,
            shipping_address=shipping_address,
        )
        await event_bus.publish(
            TaxEventType.TAX_CALCULATED.value,
            {"event_type": "TAX_CALCULATED", "source": "tax_service", "data": event.dict()}
        )
```

### Event Payload Examples

**tax.calculated**
```json
{
  "event_type": "TAX_CALCULATED",
  "source": "tax_service",
  "data": {
    "order_id": "ord_abc123",
    "calculation_id": "calc_def456",
    "user_id": "usr_xyz789",
    "subtotal": 59.98,
    "total_tax": 5.40,
    "currency": "USD",
    "tax_lines": [
      {
        "line_item_id": "line_0",
        "sku_id": "sku_widget_01",
        "tax_amount": 5.40,
        "tax_rate": 0.09,
        "jurisdiction": "CA",
        "tax_type": "sales"
      }
    ],
    "shipping_address": {"state": "CA", "country": "US", "zip": "94105"},
    "timestamp": "2026-03-05T11:00:00Z"
  }
}
```

---

## Event Subscription Pattern

### Events Subscribed

| Event | Source | Handler |
|-------|--------|---------|
| `inventory.reserved` | Inventory Service | `handle_inventory_reserved` → calls `calculate_tax()` with order_id |

### Handler Registration (`events/handlers.py`)
```python
def get_event_handlers(service: TaxService) -> Dict[str, Callable]:
    return {
        "inventory.reserved": lambda data: service.calculate_tax(
            items=data.get("items", []),
            address=data.get("shipping_address", {}),
            order_id=data["order_id"],
            user_id=data.get("user_id", "unknown"),
        ),
    }
```

---

## Client Pattern (Sync)

Tax service has **no sync service clients**. Tax provider is injected via constructor, not called over HTTP.

---

## Repository Pattern

### Database Schema

| Table | Schema | Purpose |
|-------|--------|---------|
| `tax.calculations` | `tax` | Tax calculation results per order |

### Key Indexes

| Index | Table | Columns | Notes |
|-------|-------|---------|-------|
| `idx_calculations_order` | calculations | order_id | |
| `idx_calculations_user` | calculations | user_id | |
| `idx_calculations_created` | calculations | created_at | |

### Database Design Patterns
- **JSONB tax_lines**: Per-item tax breakdown stored as JSONB array
- **JSONB shipping_address**: Address used for jurisdiction determination
- **DECIMAL(12,2)**: Precise currency amounts for subtotal and total_tax
- **Auto-updated timestamps**: Trigger-based `updated_at` management

---

## Service Registration Pattern

### Routes Registry (`routes_registry.py`)
```python
SERVICE_METADATA = {
    "service_name": "tax_service",
    "version": "1.0.0",
    "tags": ['tax', 'v1'],
    "capabilities": ['tax_calculation'],
}

ROUTES = [
    {"path": "/health", "methods": ["GET"], "description": "Health check"},
    {"path": "/api/v1/tax/health", "methods": ["GET"], "description": "Service health check (API v1)"},
]
```

### Consul Registration
- Service registers on startup with health check at `/health`
- Deregisters cleanly on shutdown
- Tags: `tax`, `v1`
- Base path: `/api/v1/tax`

---

## Migration Pattern

### Migration Files
| File | Description |
|------|-------------|
| `001_create_tax_schema.sql` | Create schema, calculations table, indexes, triggers |
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
1. Initialize `TaxRepository` with ConfigManager
2. Call `repository.initialize()` (schema setup)
3. Initialize tax provider (MockTaxProvider by default)
4. Initialize NATS event bus (fail-open)
5. Create `TaxService` with injected dependencies
6. Subscribe to events (`inventory.reserved`)
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
| `PORT` | `8253` | Service port |
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
- `service`: `tax_service`
- `order_id`: Included in persistent calculations
- `calculation_id`: Included after persistence
- `user_id`: Included when available
- `total_tax`: Included in calculation results

### Log Levels
| Level | Usage |
|-------|-------|
| INFO | Service initialization, successful calculations |
| WARNING | Event bus unavailable, non-critical failures |
| ERROR | Provider errors, repository errors, unexpected exceptions |

---

## Compliance Checklist

| Pattern | Implemented | Notes |
|---------|------------|-------|
| Service Identity | Yes | Port 8253, schema `tax` |
| Architecture | Yes | main → service → repository + provider + events |
| Dependency Injection | Yes | Protocols + factory |
| Event Publishing | Yes | 2 event types (calculated, failed) |
| Event Subscription | Yes | 1 handler (inventory.reserved) |
| Client Pattern | N/A | No sync clients — provider injected directly |
| Repository | Yes | PostgreSQL with schema + 1 table |
| Service Registration | Yes | Consul with routes_registry.py |
| Migration | Yes | 001_create_tax_schema.sql |
| Lifecycle | Yes | Startup/shutdown with async context manager |
| Configuration | Yes | ConfigManager + environment variables |
| Logging | Yes | Structured logging with calculation context |
