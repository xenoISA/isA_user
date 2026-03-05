# Inventory Service - Domain Context

## Overview

The Inventory Service manages **stock levels and reservations** for the isA_user commerce platform. It tracks physical and digital inventory, creates time-bound reservations during the checkout flow, and ensures stock consistency through an event-driven reservation lifecycle.

**Business Context**: Prevent overselling by reserving stock at order creation, committing after payment, and automatically releasing expired reservations. The service supports both finite stock (physical goods) and infinite stock (digital products).

**Core Value Proposition**: Guarantee stock availability during checkout with time-limited reservations that automatically expire, ensuring inventory is never permanently locked by abandoned orders.

---

## Business Taxonomy

### Core Entities

#### 1. Stock Level
**Definition**: Real-time stock record for a specific SKU at a location.

**Business Purpose**:
- Track on-hand, reserved, and available quantities per SKU
- Support multi-location inventory (warehouses, stores)
- Distinguish finite (physical) and infinite (digital) inventory policies
- Provide real-time availability for product catalog

**Key Attributes**:
- SKU ID (unique product identifier)
- Location ID (warehouse or fulfillment center, default: "default")
- Inventory Policy (finite or infinite)
- On Hand (total physical stock)
- Reserved (quantity held by active reservations)
- Available (computed: on_hand - reserved)
- Metadata (flexible attributes)

**Inventory Policies**:
- **FINITE**: Real stock tracking for physical goods — reservations decrement available count
- **INFINITE**: Digital products — reservations always succeed, no stock limits

#### 2. Inventory Reservation
**Definition**: Time-bound hold on inventory for a specific order.

**Business Purpose**:
- Lock stock during checkout to prevent overselling
- Support multi-item reservations per order
- Track reservation lifecycle (active → committed/released/expired)
- Enable automatic expiry of abandoned reservations

**Key Attributes**:
- Reservation ID (unique, prefix `res_`)
- Order ID (reference to the order)
- User ID (customer reference)
- Items (array of SKU ID, quantity, unit price)
- Status (active, committed, released, expired)
- Expires At (default: 30 minutes from creation)
- Created At, Updated At, Committed At, Released At

---

## Domain Scenarios

### Scenario 1: Reserve Inventory at Checkout
**Actor**: Order Service (via event)
**Trigger**: Customer places an order
**Flow**:
1. Order Service publishes `order.created` event
2. Inventory Service receives event and calls `reserve_inventory()`
3. System validates order_id and items are present
4. Repository creates reservation with 30-minute expiry
5. For finite-stock items, available quantity is decremented
6. `inventory.reserved` event is published with reservation details
7. Response includes reservation_id, status "active", and expires_at

**Outcome**: Stock is held for the customer during payment processing

### Scenario 2: Commit Reservation After Payment
**Actor**: Payment Service (via event)
**Trigger**: Payment is successfully processed
**Flow**:
1. Payment Service publishes `payment.completed` event
2. Inventory Service receives event and calls `commit_reservation()`
3. System finds active reservation by order_id
4. Reservation status transitions from "active" to "committed"
5. `inventory.committed` event is published
6. Stock is permanently deducted from on-hand count

**Outcome**: Inventory is permanently allocated to the fulfilled order

### Scenario 3: Release Reservation on Cancellation
**Actor**: Order Service (via event)
**Trigger**: Customer cancels order before payment
**Flow**:
1. Order Service publishes `order.canceled` event
2. Inventory Service receives event and calls `release_reservation()`
3. System finds active reservation by order_id
4. Reservation status transitions to "released"
5. Reserved quantity is restored to available stock
6. `inventory.released` event is published
7. If no active reservation found, returns success with informational message

**Outcome**: Stock is returned to available pool for other customers

### Scenario 4: Automatic Reservation Expiry
**Actor**: System (background process)
**Trigger**: Reservation expires_at timestamp passes
**Flow**:
1. Background process checks for reservations past expiry
2. Expired reservations transition from "active" to "expired"
3. Reserved stock is restored to available quantities
4. No event published (passive expiry)

**Outcome**: Abandoned checkouts don't permanently lock inventory

### Scenario 5: Check Reservation Status
**Actor**: Order Service, Customer Support
**Trigger**: Need to verify reservation state
**Flow**:
1. Caller requests `GET /api/v1/inventory/reservations/{order_id}`
2. Repository returns latest reservation for the order
3. Response includes full reservation details and current status

**Outcome**: Visibility into current reservation state for debugging or customer support

---

## Domain Events

### Events Published

| Event | Subject | Payload | When |
|-------|---------|---------|------|
| Stock Reserved | `inventory.reserved` | order_id, reservation_id, user_id, items[], expires_at | After successful reservation |
| Stock Committed | `inventory.committed` | order_id, reservation_id, user_id, items[] | After payment confirmation |
| Stock Released | `inventory.released` | order_id, reservation_id, user_id, items[], reason | After cancellation/release |
| Stock Failed | `inventory.failed` | order_id, user_id, items[], error_code, error_message | On reservation failure |

### Events Consumed

| Event | Source | Handler Action |
|-------|--------|---------------|
| `order.created` | Order Service | Auto-reserve inventory for order items |
| `payment.completed` | Payment Service | Auto-commit reservation |
| `order.canceled` | Order Service | Auto-release reservation |

---

## Core Concepts

### Reservation Lifecycle State Machine

```
ACTIVE → COMMITTED (payment confirmed)
   ↓
RELEASED (order canceled / manual release)
   ↓
EXPIRED (timeout, 30 min default)
```

| From | To | Trigger | Reversible |
|------|----|---------|-----------|
| ACTIVE | COMMITTED | Payment confirmation | No |
| ACTIVE | RELEASED | Order cancellation | No |
| ACTIVE | EXPIRED | Timeout (30 min) | No |

### Separation of Concerns
- **Service Layer**: Business logic only — no I/O, no HTTP
- **Repository Layer**: All database operations via PostgreSQL gRPC
- **Event Layer**: Async NATS publishing, best-effort (failures logged, not thrown)

---

## Business Rules

| Rule | Description |
|------|-------------|
| BR-INV-001 | `order_id` and `items` are required for reservation |
| BR-INV-002 | Reservations expire after 30 minutes by default |
| BR-INV-003 | Commit requires an active reservation for the order |
| BR-INV-004 | Release of non-existent reservation returns success (idempotent) |
| BR-INV-005 | Event publishing is best-effort — failures don't block operations |
| BR-INV-006 | Infinite-stock items always succeed reservation |
| BR-INV-007 | Available = on_hand - reserved (computed column) |
| BR-INV-008 | Multiple reservations for the same order use the latest active one |

---

## Inventory Service in Ecosystem

### Upstream Dependencies
| Service | Interaction | Purpose |
|---------|------------|---------|
| Order Service | Event subscription | Triggers reserve/release on order events |
| Payment Service | Event subscription | Triggers commit on payment completion |

### Downstream Consumers
| Service | Interaction | Purpose |
|---------|------------|---------|
| Tax Service | Event publishing | Tax calculation triggered after reservation |
| Fulfillment Service | Event publishing | Shipment preparation after commit |
| Billing Service | Event publishing | Usage tracking for inventory operations |

---

## Success Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Reservation latency | <100ms | Time to create a reservation |
| Commit/release latency | <50ms | Time to commit or release |
| Reservation expiry accuracy | 100% | All expired reservations cleaned up |
| Event publishing success | >99.5% | Best-effort event delivery rate |
| Oversell incidents | 0 | No orders accepted beyond available stock |

---

## Glossary

| Term | Definition |
|------|-----------|
| SKU | Stock Keeping Unit — unique product variant identifier |
| Reservation | Time-bound hold on inventory for an order |
| Commit | Permanent allocation of reserved stock after payment |
| Release | Return of reserved stock to available pool |
| Finite stock | Physical goods with real quantity limits |
| Infinite stock | Digital products with no quantity constraints |
| On hand | Total physical stock at a location |
| Available | Stock available for new reservations (on_hand - reserved) |
