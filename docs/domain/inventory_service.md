# Inventory Service - Domain Context

## Service Overview

The Inventory Service manages real-time stock levels and inventory reservations for the isA e-commerce pipeline. It supports both physical SKUs (finite stock) and digital items (infinite stock), providing atomic reservation operations that prevent overselling during concurrent order processing.

---

## Business Domain Context

### Domain Definition

**Inventory Management** is the practice of tracking stock levels, reserving inventory for pending orders, and managing the lifecycle of those reservations. This includes:

- **Stock Tracking**: Real-time on-hand, reserved, and available quantities per SKU per location
- **Reservation Management**: Atomic reserve/commit/release operations tied to order lifecycle
- **Policy Enforcement**: Finite vs. infinite inventory policies for physical and digital goods
- **Expiration Handling**: Automatic release of expired reservations to prevent stock lockup

### Bounded Context

The Inventory Service operates within the **Commerce Fulfillment** bounded context, bounded by:

| Boundary | Description |
|----------|-------------|
| **Upstream** | order_service (triggers reservations via `order.created` events), product_service (defines SKUs and inventory policies) |
| **Downstream** | tax_service (receives `inventory.reserved` events to trigger tax calculation), fulfillment_service (depends on committed inventory) |
| **Lateral** | billing_service (usage tracking), audit_service (reservation audit trail) |

### Domain Entities

| Entity | Description | Lifecycle |
|--------|-------------|-----------|
| **InventoryItem** | Stock record for a SKU at a location | Created on first stock receipt; updated on reserve/commit/release |
| **InventoryReservation** | Temporary hold on stock for a pending order | ACTIVE → COMMITTED / RELEASED / EXPIRED |

---

## Terminology (Ubiquitous Language)

### Core Terms

| Term | Definition | Example |
|------|------------|---------|
| **SKU** | Stock Keeping Unit — unique identifier for an inventory item | `sku_widget_001` |
| **On-hand** | Total physical quantity in stock | 100 units |
| **Reserved** | Quantity held for pending orders (not yet shipped) | 15 units |
| **Available** | On-hand minus reserved; quantity available for new orders | 85 units |
| **Reservation** | A temporary hold on inventory for a specific order | Reserve 3 units of SKU-001 for order ORD-123 |
| **Commit** | Finalize a reservation after payment succeeds | Reservation moves to COMMITTED |
| **Release** | Return reserved stock back to available pool | Order cancelled, 3 units returned |
| **Inventory Policy** | Rule governing stock behavior | `finite` (physical goods) or `infinite` (digital goods) |

### Reservation Status Terms

| Status | Meaning | Transition |
|--------|---------|------------|
| **ACTIVE** | Stock is reserved, awaiting payment | Initial state after reserve |
| **COMMITTED** | Payment succeeded, stock allocated for fulfillment | ACTIVE → COMMITTED |
| **RELEASED** | Reservation cancelled, stock returned to available | ACTIVE → RELEASED |
| **EXPIRED** | Reservation timed out, stock auto-released | ACTIVE → EXPIRED (via TTL) |

---

## Business Capabilities

### BR-INV-001: Reserve Inventory

**Capability**: Atomically reserve stock for an order, preventing overselling

**Business Rules**:
- BR-INV-001.1: Reservation requires `order_id`, `sku_id`, and `quantity` (quantity > 0)
- BR-INV-001.2: Available stock must be >= requested quantity (atomic check-and-decrement)
- BR-INV-001.3: On success, `reserved` increments and `available` decrements by quantity
- BR-INV-001.4: Each reservation gets a unique `reservation_id` with prefix `rsv_`
- BR-INV-001.5: Reservations have an `expires_at` timestamp (default 30 minutes)
- BR-INV-001.6: Items with `infinite` policy always succeed regardless of stock levels
- BR-INV-001.7: `inventory.reserved` event is published on success

### BR-INV-002: Commit Reservation

**Capability**: Finalize a reservation after successful payment

**Business Rules**:
- BR-INV-002.1: Only ACTIVE reservations can be committed
- BR-INV-002.2: Status transitions to COMMITTED
- BR-INV-002.3: Reserved quantity decremented from `reserved` field (stock is now sold)
- BR-INV-002.4: `inventory.committed` event is published

### BR-INV-003: Release Reservation

**Capability**: Cancel a reservation and return stock to available pool

**Business Rules**:
- BR-INV-003.1: Only ACTIVE reservations can be released
- BR-INV-003.2: Status transitions to RELEASED
- BR-INV-003.3: `reserved` decrements and `available` increments by reservation quantity
- BR-INV-003.4: `inventory.released` event is published

### BR-INV-004: Reservation Expiry

**Capability**: Automatically release expired reservations to prevent stock lockup

**Business Rules**:
- BR-INV-004.1: Reservations with `expires_at` < current time are eligible for expiry
- BR-INV-004.2: Expired reservations transition to EXPIRED status
- BR-INV-004.3: Stock is returned to available pool (same as release)
- BR-INV-004.4: `inventory.expired` event is published
- BR-INV-004.5: Expiry check runs periodically (background sweep)

---

## Domain Events

### Events Published

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `inventory.reserved` | `inventory.reserved` | Stock reserved for order | order_id, reservation_id, sku_id, quantity, user_id, items |
| `inventory.committed` | `inventory.committed` | Reservation finalized after payment | order_id, reservation_id, sku_id, quantity |
| `inventory.released` | `inventory.released` | Reservation cancelled, stock returned | order_id, reservation_id, sku_id, quantity, reason |
| `inventory.expired` | `inventory.expired` | Reservation auto-expired | order_id, reservation_id, sku_id, quantity |
| `inventory.failed` | `inventory.failed` | Reservation failed (insufficient stock) | order_id, sku_id, requested_quantity, available_quantity, error_message |

### Events Subscribed

| Event | Source | Handler |
|-------|--------|---------|
| `order.created` | order_service | Auto-reserve inventory for order items |
| `payment.completed` | payment_service | Commit reservations for paid order |
| `order.canceled` | order_service | Release reservations for cancelled order |

---

## Integration Points

### Upstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **order_service** | Triggers reservation via events | NATS subscription (`order.created`) | Queue events, retry |
| **product_service** | SKU definitions, inventory policies | Sync HTTP (future) | Use cached policy |

### Downstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **tax_service** | Tax calculation triggered by `inventory.reserved` | Async event publishing | Tax service retries independently |
| **fulfillment_service** | Fulfillment preparation after commit | Async event publishing | Fulfillment retries independently |

### Cross-Cutting Dependencies

| Service | Purpose | Integration Pattern |
|---------|---------|---------------------|
| **PostgreSQL** | Primary data store (schema: `inventory`) | AsyncPostgresClient |
| **NATS JetStream** | Event pub/sub | core.nats_client |
| **Consul** | Service registration and discovery | isa_common.ConsulRegistry |

---

## Quality Attributes

| Attribute | Target | Rationale |
|-----------|--------|-----------|
| **Availability** | 99.9% | Inventory blocks order flow; downtime = lost sales |
| **Latency (Reserve)** | p99 < 200ms | Must not slow checkout |
| **Consistency** | Strong (per-SKU) | Overselling prevention requires atomic operations |
| **Data Durability** | Zero reservation loss | Every reservation must be tracked |

---

## Future Considerations

1. **Multi-location inventory**: Stock across warehouses with location-based allocation
2. **Backorder support**: Allow reservations when stock is zero, fulfilled on restock
3. **Inventory forecasting**: ML-based demand prediction for restock alerts
4. **Bulk operations**: Batch reserve/release for large orders
5. **Real-time stock sync**: Integration with external warehouse management systems

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
**Domain Owner**: Commerce Platform Team
