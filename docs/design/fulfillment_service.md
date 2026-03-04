# Fulfillment Service - Design Document

## Overview

The Fulfillment Service is a FastAPI microservice that manages shipping and delivery for the isA e-commerce platform. It handles the complete shipment lifecycle through event-driven orchestration, using PostgreSQL for persistence, NATS JetStream for pipeline integration, and a pluggable provider for carrier operations.

---

## Architecture

### High-Level Architecture

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Tax Service │  │  Payment    │  │   Order     │
│             │  │  Service    │  │  Service    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
  tax.calculated  payment.completed  order.canceled
       │                │                │
       └────────────────┼────────────────┘
                        │
           ┌────────────┴────────────┐
           │   Fulfillment Service   │
           │  (FastAPI + PostgreSQL) │
           │       Port: 8254        │
           └────────────┬────────────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
┌──────┴──────┐  ┌──────┴──────┐  ┌─────┴─────┐
│    NATS     │  │ PostgreSQL  │  │  Consul   │
│  (Events)   │  │(fulfillment)│  │(Registry) │
└─────────────┘  └─────────────┘  └───────────┘
```

### Core Components

#### 1. API Layer (FastAPI)
- **Health**: `/health`, `/api/v1/fulfillment/health`
- **Create Shipment**: `POST /api/v1/fulfillment/shipments`
- **Create Label**: `POST /api/v1/fulfillment/shipments/{id}/label`
- **Cancel Shipment**: `POST /api/v1/fulfillment/shipments/{id}/cancel`
- **Get by Order**: `GET /api/v1/fulfillment/shipments/{order_id}`
- **Get by Tracking**: `GET /api/v1/fulfillment/tracking/{tracking_number}`

#### 2. Repository Layer
- **FulfillmentRepository**: Shipment CRUD via AsyncPostgresClient
  - `create_shipment()` — create with auto-generated shipment_id
  - `get_shipment()` — lookup by shipment_id
  - `get_shipment_by_order()` — lookup by order_id (most recent)
  - `get_shipment_by_tracking()` — lookup by tracking_number
  - `create_label()` — update shipment with carrier/tracking/label
  - `cancel_shipment()` — set status to failed with reason
  - `update_shipment()` — generic status/field update
  - `list_shipments()` — filtered list with pagination

#### 3. Provider Layer
- **MockFulfillmentProvider**: Returns mock shipment/label data for testing
- Future: USPSProvider, FedExProvider, UPSProvider

#### 4. Event System
- **Publishers**: `publish_shipment_prepared`, `publish_label_created`, `publish_shipment_canceled`, `publish_shipment_failed`
- **Handlers**:
  - `handle_tax_calculated` → auto-prepare shipment
  - `handle_payment_completed` → auto-create label
  - `handle_order_canceled` → auto-cancel shipment

---

## Database Schema

### Schema: fulfillment

#### shipments (Shipment Records)
```sql
CREATE TABLE fulfillment.shipments (
    id SERIAL PRIMARY KEY,
    shipment_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    items JSONB DEFAULT '[]'::jsonb,
    shipping_address JSONB,
    carrier VARCHAR(50),
    tracking_number VARCHAR(100),
    label_url TEXT,
    estimated_delivery TIMESTAMPTZ,
    status VARCHAR(30) DEFAULT 'created'
        CHECK (status IN ('created', 'label_purchased', 'in_transit', 'delivered', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    label_created_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_shipments_order` | order_id | Fast lookup by order |
| `idx_shipments_user` | user_id | User-level queries |
| `idx_shipments_tracking` | tracking_number (partial) | Tracking lookup |
| `idx_shipments_status` | status | Status-based filtering |
| `idx_shipments_carrier` | carrier (partial) | Carrier-based queries |

---

## Event Architecture

### NATS Stream Configuration

```
Stream: fulfillment-stream
Subjects: fulfillment.>
Consumer Prefix: fulfillment
```

### Events Published

| Event Type | Subject | Data Model |
|------------|---------|------------|
| `fulfillment.shipment.prepared` | `fulfillment.shipment.prepared` | ShipmentPreparedEvent |
| `fulfillment.label.created` | `fulfillment.label.created` | LabelCreatedEvent |
| `fulfillment.shipment.canceled` | `fulfillment.shipment.canceled` | ShipmentCanceledEvent |
| `fulfillment.shipment.failed` | `fulfillment.shipment.failed` | ShipmentFailedEvent |

### Events Subscribed

| Pattern | Source | Handler |
|---------|--------|---------|
| `tax_service.tax.calculated` | tax_service | `handle_tax_calculated` → prepare shipment |
| `payment_service.payment.completed` | payment_service | `handle_payment_completed` → create label |
| `order_service.order.canceled` | order_service | `handle_order_canceled` → cancel shipment |

### Event-Driven Pipeline Flow

```
order.created → [inventory_service]
    └─ inventory.reserved → [tax_service]
        └─ tax.calculated → [fulfillment_service: prepare shipment]
            └─ payment.completed → [fulfillment_service: create label]
                └─ fulfillment.label.created → [notification_service]
```

```
order.canceled → [fulfillment_service: cancel shipment]
    └─ fulfillment.shipment.canceled → [billing_service: refund if needed]
```

---

## State Machine

### Shipment Status Transitions

```
┌─────────┐  label created  ┌────────────────┐  carrier pickup  ┌────────────┐  delivered  ┌───────────┐
│ CREATED ├────────────────►│LABEL_PURCHASED ├────────────────►│ IN_TRANSIT ├───────────►│ DELIVERED │
└────┬────┘                 └───────┬────────┘                 └────────────┘            └───────────┘
     │                              │
     │ cancelled                    │ cancelled
     │                              │
     └──────────┐    ┌──────────────┘
                │    │
           ┌────▼────▼────┐
           │    FAILED     │
           │  (cancelled)  │
           └──────────────┘
```

---

## Data Models

### Shipment
```python
class Shipment(BaseModel):
    shipment_id: str
    order_id: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: ShipmentStatus = ShipmentStatus.CREATED
    label_url: Optional[str] = None
    parcels: List[Parcel] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### ShipmentStatus
```python
class ShipmentStatus(str, Enum):
    CREATED = "created"
    LABEL_PURCHASED = "label_purchased"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
```

---

## Dependency Injection

### Protocol: FulfillmentRepositoryProtocol
Defines interface for: `create_shipment`, `get_shipment`, `get_shipment_by_order`, `get_shipment_by_tracking`, `update_shipment`, `create_label`, `cancel_shipment`, `list_shipments`.

### Protocol: EventBusProtocol
Defines interface for: `publish_event`.

### Factory: `create_fulfillment_repository(config)`
Creates FulfillmentRepository with PostgreSQL via ConfigManager service discovery.

---

## Service Registration

### Consul Metadata
```json
{
    "service_name": "fulfillment_service",
    "version": "1.0.0",
    "tags": ["fulfillment", "v1"],
    "capabilities": ["shipment_creation"],
    "port": 8254
}
```

---

## Error Handling

| Scenario | HTTP Status | Behavior |
|----------|-------------|----------|
| Missing required fields | 400 | `{"detail": "order_id, items, and address are required"}` |
| Shipment not found | 404 | `{"detail": "Shipment not found"}` |
| Tracking not found | 404 | `{"detail": "Tracking number not found"}` |
| Repository unavailable | 503 | `{"detail": "Repository not available"}` |
| Event publishing failure | Logged | Best-effort, does not fail request |

---

## Idempotency

All operations are designed to be idempotent to handle duplicate NATS events:

| Operation | Idempotency Strategy |
|-----------|---------------------|
| Prepare shipment | Check if shipment exists for order before creating |
| Create label | Check if label already exists, return existing |
| Cancel shipment | Already-failed shipments return success |

---

## Deployment

| Config | Default | Env Var |
|--------|---------|---------|
| Port | 8254 | `PORT` |
| PostgreSQL Host | localhost | `POSTGRES_HOST` |
| PostgreSQL Port | 5432 | `POSTGRES_PORT` |
| Consul Enabled | false | `CONSUL_ENABLED` |
| Consul Host | localhost | `CONSUL_HOST` |
| Consul Port | 8500 | `CONSUL_PORT` |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
