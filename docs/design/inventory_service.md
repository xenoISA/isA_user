# Inventory Service - Design Document

## Overview

The Inventory Service is a FastAPI microservice that provides real-time stock management and atomic reservation operations for the isA e-commerce platform. It uses PostgreSQL for persistence, NATS JetStream for event-driven integration, and Consul for service discovery.

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Order Service  │    │ Payment Service │    │  Other Services │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │     API Gateway          │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   Inventory Service      │
                    │   (FastAPI + PostgreSQL) │
                    │       Port: 8252         │
                    └────────────┬────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
    ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
    │    NATS     │      │  PostgreSQL │      │   Consul    │
    │ (Event Bus) │      │ (inventory) │      │ (Registry)  │
    └──────┬──────┘      └─────────────┘      └─────────────┘
           │
    ┌──────┴──────┐
    │ tax_service │  (subscribes to inventory.reserved)
    └─────────────┘
```

### Core Components

#### 1. API Layer (FastAPI)
- **Health**: `/health`, `/api/v1/inventory/health`
- **Reserve**: `POST /api/v1/inventory/reserve`
- **Commit**: `POST /api/v1/inventory/commit`
- **Release**: `POST /api/v1/inventory/release`
- **Stock Query**: `GET /api/v1/inventory/stock/{sku_id}`
- **Reservation Query**: `GET /api/v1/inventory/reservations/{order_id}`

#### 2. Repository Layer
- **InventoryRepository**: Stock CRUD and atomic reservation operations via AsyncPostgresClient

#### 3. Provider Layer
- **MockInventoryProvider**: Returns mock reservation data for testing

#### 4. Event System
- **Publishers**: `publish_inventory_reserved`, `publish_inventory_committed`, `publish_inventory_released`, `publish_inventory_failed`
- **Handlers**: `handle_order_created` (auto-reserve), `handle_payment_completed` (auto-commit), `handle_order_canceled` (auto-release)

---

## Database Schema

### Schema: inventory

#### 1. items (Stock Levels)
```sql
CREATE TABLE inventory.items (
    id SERIAL PRIMARY KEY,
    sku_id VARCHAR(100) UNIQUE NOT NULL,
    location_id VARCHAR(100),
    inventory_policy VARCHAR(20) DEFAULT 'finite',
    on_hand INTEGER DEFAULT 0 CHECK (on_hand >= 0),
    reserved INTEGER DEFAULT 0 CHECK (reserved >= 0),
    available INTEGER DEFAULT 0 CHECK (available >= 0),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
```

#### 2. reservations (Order Reservations)
```sql
CREATE TABLE inventory.reservations (
    id SERIAL PRIMARY KEY,
    reservation_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    sku_id VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'committed', 'released', 'expired')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| `idx_items_sku` | items | sku_id | Fast stock lookup by SKU |
| `idx_items_location` | items | location_id | Location-based queries |
| `idx_reservations_order` | reservations | order_id | Find reservations by order |
| `idx_reservations_sku` | reservations | sku_id | Find reservations by SKU |
| `idx_reservations_status` | reservations | status | Filter active/expired |
| `idx_reservations_expires` | reservations | expires_at | Expiry sweep queries |

---

## Event Architecture

### NATS Stream Configuration

```
Stream: inventory-stream
Subjects: inventory.>
Consumer Prefix: inventory
```

### Events Published

| Event Type | Subject | Data Model |
|------------|---------|------------|
| `inventory.reserved` | `inventory.reserved` | InventoryReservedEvent |
| `inventory.committed` | `inventory.committed` | InventoryCommittedEvent |
| `inventory.released` | `inventory.released` | InventoryReleasedEvent |
| `inventory.expired` | `inventory.expired` | InventoryExpiredEvent |
| `inventory.failed` | `inventory.failed` | InventoryFailedEvent |

### Events Subscribed

| Pattern | Source | Handler |
|---------|--------|---------|
| `order_service.order.created` | order_service | `handle_order_created` → auto-reserve |
| `payment_service.payment.completed` | payment_service | `handle_payment_completed` → auto-commit |
| `order_service.order.canceled` | order_service | `handle_order_canceled` → auto-release |

---

## Data Models

### InventoryItem
```python
class InventoryItem(BaseModel):
    sku_id: str
    location_id: Optional[str] = None
    inventory_policy: InventoryPolicy = InventoryPolicy.FINITE  # finite | infinite
    on_hand: int = Field(default=0, ge=0)
    reserved: int = Field(default=0, ge=0)
    available: int = Field(default=0, ge=0)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### InventoryReservation
```python
class InventoryReservation(BaseModel):
    reservation_id: str
    order_id: str
    sku_id: str
    quantity: int = Field(..., gt=0)
    status: ReservationStatus = ReservationStatus.ACTIVE
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

## Dependency Injection

### Protocol: InventoryRepositoryProtocol
Defines the interface for all repository operations (create/get/update items, create/get/update reservations, list operations).

### Protocol: EventBusProtocol
Defines the interface for event publishing (`publish_event`).

### Factory: `create_inventory_repository(config)`
Creates InventoryRepository with real PostgreSQL dependencies via ConfigManager service discovery.

---

## Service Registration

### Consul Metadata
```json
{
    "service_name": "inventory_service",
    "version": "1.0.0",
    "tags": ["inventory", "v1"],
    "capabilities": ["stock_management"],
    "port": 8252
}
```

---

## Error Handling

| Scenario | HTTP Status | Behavior |
|----------|-------------|----------|
| Missing required fields | 400 | Validation error with field details |
| Insufficient stock | 409 | Error with available quantity |
| Reservation/SKU not found | 404 | Not found error |
| Repository unavailable | 503 | Service unavailable |
| Event publishing failure | Logged | Best-effort, does not fail request |

---

## Deployment

| Config | Default | Env Var |
|--------|---------|---------|
| Port | 8252 | `PORT` |
| PostgreSQL Host | localhost | `POSTGRES_HOST` |
| PostgreSQL Port | 5432 | `POSTGRES_PORT` |
| Consul Enabled | false | `CONSUL_ENABLED` |
| Consul Host | localhost | `CONSUL_HOST` |
| Consul Port | 8500 | `CONSUL_PORT` |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
