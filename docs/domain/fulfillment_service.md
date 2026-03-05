# Fulfillment Service - Domain Context

## Overview

The Fulfillment Service manages **shipment creation, label generation, and tracking** for the isA_user commerce platform. It coordinates the physical delivery of orders from label purchase through delivery, integrating with shipping carriers via a pluggable provider interface.

**Business Context**: After payment and tax are finalized, physical goods need to be picked, packed, and shipped. The Fulfillment Service owns the shipment lifecycle — from creating a shipment record to generating shipping labels and tracking delivery status.

**Core Value Proposition**: Provide a unified shipment management API with carrier-agnostic label generation, real-time tracking, and full lifecycle visibility from order to delivery.

---

## Business Taxonomy

### Core Entities

#### 1. Shipment
**Definition**: A shipping record linking an order to a physical delivery.

**Business Purpose**:
- Track shipment lifecycle from creation to delivery
- Associate orders with carriers and tracking numbers
- Manage shipping labels and delivery estimates
- Enable shipment cancellation with refund tracking

**Key Attributes**:
- Shipment ID (unique, prefix `shp_`)
- Order ID (reference to the order)
- User ID (customer reference)
- Items (array of SKU ID, quantity, weight_grams)
- Shipping Address (delivery destination)
- Carrier (USPS, UPS, FedEx, etc.)
- Tracking Number (carrier-assigned, prefix `trk_` or `TRK`)
- Label URL (downloadable shipping label)
- Status (created, label_purchased, in_transit, delivered, failed)
- Estimated Delivery (carrier-provided ETA)
- Lifecycle Timestamps (created_at, label_created_at, shipped_at, delivered_at, canceled_at)
- Cancellation Reason (if applicable)
- Metadata (flexible attributes)

#### 2. Parcel
**Definition**: Physical package dimensions and weight.

**Business Purpose**:
- Calculate shipping rates based on weight/dimensions
- Enable carrier rate comparison
- Support multi-parcel shipments

**Key Attributes**:
- Weight (grams)
- Dimensions (length, width, height in cm)

#### 3. Fulfillment Provider
**Definition**: Pluggable shipping carrier integration.

**Business Purpose**:
- Abstract carrier-specific APIs behind a provider interface
- Support multiple carriers without API changes
- Enable testing with mock providers

**Provider Types**:
- **MockFulfillmentProvider**: Test provider with deterministic tracking numbers
- **USPSProvider**: USPS integration (future)
- **UPSProvider**: UPS integration (future)

---

## Domain Scenarios

### Scenario 1: Create Shipment for Order
**Actor**: Order Service / Fulfillment Worker
**Trigger**: Order is ready for shipping (payment + tax complete)
**Flow**:
1. System calls `POST /api/v1/fulfillment/shipments` with order_id, items, address
2. Fulfillment provider creates initial shipment record with tracking number
3. Repository persists shipment with status "created"
4. Items are converted to ShipmentItem models with weight
5. `fulfillment.shipment.prepared` event is published
6. Response includes shipment_id, tracking_number, status "created"

**Outcome**: Shipment record exists, ready for label generation

### Scenario 2: Generate Shipping Label
**Actor**: Warehouse Staff / Automation
**Trigger**: Shipment is ready for carrier pickup
**Flow**:
1. System calls `POST /api/v1/fulfillment/shipments/{shipment_id}/label`
2. If label already exists, returns existing label (idempotent)
3. System generates tracking number and assigns carrier (default: USPS)
4. Repository updates shipment with carrier, tracking_number, status "label_purchased"
5. Estimated delivery is calculated (default: 5 business days)
6. `fulfillment.label.created` event is published
7. Response includes tracking_number, carrier, status "label_created"

**Outcome**: Shipping label is ready for printing and package pickup

### Scenario 3: Cancel Shipment
**Actor**: Customer Support, Order Service
**Trigger**: Customer cancels order or shipment needs to be voided
**Flow**:
1. System calls `POST /api/v1/fulfillment/shipments/{shipment_id}/cancel`
2. If shipment not found, returns 404
3. If already failed/canceled, returns success (idempotent)
4. If label was already purchased, marks `refund_shipping = true`
5. Repository updates status to "failed" with cancellation reason
6. `fulfillment.shipment.canceled` event is published
7. Response includes refund_shipping flag for billing

**Outcome**: Shipment is canceled, billing notified of potential shipping refund

### Scenario 4: Track Shipment by Order
**Actor**: Customer, Customer Support
**Trigger**: Customer wants delivery status
**Flow**:
1. Caller requests `GET /api/v1/fulfillment/shipments/order/{order_id}`
2. Repository returns latest shipment for the order
3. Response includes full shipment details and current status

**Outcome**: Customer has visibility into delivery progress

### Scenario 5: Track Shipment by Tracking Number
**Actor**: Customer, Carrier Integration
**Trigger**: Tracking number lookup
**Flow**:
1. Caller requests `GET /api/v1/fulfillment/shipments/tracking/{tracking_number}`
2. Repository returns shipment matching the tracking number
3. Response includes shipment details and status

**Outcome**: Shipment located by carrier tracking number

---

## Domain Events

### Events Published

| Event | Subject | Payload | When |
|-------|---------|---------|------|
| Shipment Prepared | `fulfillment.shipment.prepared` | order_id, shipment_id, user_id, items[], shipping_address | After shipment creation |
| Label Created | `fulfillment.label.created` | order_id, shipment_id, user_id, carrier, tracking_number, estimated_delivery | After label generation |
| Shipment Canceled | `fulfillment.shipment.canceled` | order_id, shipment_id, user_id, reason, refund_shipping | After cancellation |
| Shipment Failed | `fulfillment.shipment.failed` | order_id, user_id, error_code, error_message | On shipment failure |

### Events Consumed

| Event | Source | Handler Action |
|-------|--------|---------------|
| `tax.calculated` | Tax Service | Trigger shipment preparation |
| `payment.completed` | Payment Service | Confirm shipment readiness |
| `order.canceled` | Order Service | Auto-cancel shipment |

---

## Core Concepts

### Shipment Status Lifecycle

```
CREATED → LABEL_PURCHASED → IN_TRANSIT → DELIVERED
    ↓           ↓
  FAILED      FAILED (canceled)
```

| From | To | Trigger | Reversible |
|------|----|---------|-----------|
| CREATED | LABEL_PURCHASED | Label generation | No |
| CREATED | FAILED | Cancellation | No |
| LABEL_PURCHASED | IN_TRANSIT | Carrier pickup | No |
| LABEL_PURCHASED | FAILED | Cancellation (refund_shipping=true) | No |
| IN_TRANSIT | DELIVERED | Delivery confirmation | No |

### Idempotency
- **Label creation**: If a label already exists, returns existing label without creating a new one
- **Cancellation**: Already-canceled shipments return success without side effects

### Separation of Concerns
- **Service Layer**: Business logic — shipment lifecycle, label generation, cancellation
- **Provider Layer**: Carrier integration (pluggable)
- **Repository Layer**: Persistence via PostgreSQL gRPC
- **Event Layer**: Async NATS publishing, best-effort

---

## Business Rules

| Rule | Description |
|------|-------------|
| BR-FUL-001 | `order_id`, `items`, and `address` are required for shipment creation |
| BR-FUL-002 | Initial shipment status is "created" |
| BR-FUL-003 | Label creation is idempotent — returns existing label if already purchased |
| BR-FUL-004 | Default carrier is USPS, default delivery estimate is 5 days |
| BR-FUL-005 | Cancellation of label_purchased shipment sets refund_shipping=true |
| BR-FUL-006 | Already-failed shipments return success on cancel (idempotent) |
| BR-FUL-007 | Event publishing is best-effort — failures don't block operations |
| BR-FUL-008 | Duplicate shipments for same order are allowed (creates new) |

---

## Fulfillment Service in Ecosystem

### Upstream Dependencies
| Service | Interaction | Purpose |
|---------|------------|---------|
| Tax Service | Event subscription | Triggers shipment after tax calculation |
| Payment Service | Event subscription | Confirms payment before shipping |
| Order Service | Event subscription | Receives cancellation events |
| Fulfillment Provider | Internal call | Carrier integration for tracking/labels |

### Downstream Consumers
| Service | Interaction | Purpose |
|---------|------------|---------|
| Notification Service | Event publishing | Customer shipment/delivery notifications |
| Billing Service | Event publishing | Shipping cost and refund tracking |
| Order Service | API query | Shipment status for order summary |

---

## Success Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Shipment creation latency | <1s | Time to create shipment record |
| Label generation latency | <500ms | Time to generate shipping label |
| Status update latency | <100ms | Time to process status changes |
| Event publishing success | >99.5% | Best-effort event delivery rate |
| Tracking accuracy | >99% | Correct carrier tracking numbers |

---

## Glossary

| Term | Definition |
|------|-----------|
| Shipment | Physical delivery record linking order to carrier |
| Label | Shipping label with carrier barcode and address |
| Tracking Number | Carrier-assigned identifier for package tracking |
| Carrier | Shipping company (USPS, UPS, FedEx) |
| Fulfillment Provider | Pluggable carrier integration abstraction |
| Refund Shipping | Flag indicating shipping cost should be refunded on cancel |
| Parcel | Physical package with weight and dimensions |
