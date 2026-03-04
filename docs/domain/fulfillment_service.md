# Fulfillment Service - Domain Context

## Service Overview

The Fulfillment Service manages shipping and delivery for physical goods in the isA e-commerce pipeline. It handles shipment creation, label purchasing, tracking, and cancellation, integrating with upstream tax and payment events to orchestrate the end-to-end fulfillment lifecycle.

---

## Business Domain Context

### Domain Definition

**Order Fulfillment** is the practice of preparing, shipping, and tracking physical goods from warehouse to customer. This includes:

- **Shipment Preparation**: Creating shipment records with items and shipping address after tax calculation
- **Label Purchasing**: Generating shipping labels with carrier and tracking information after payment
- **Tracking**: Monitoring shipment status through carrier lifecycle (created → in-transit → delivered)
- **Cancellation**: Handling shipment cancellation with optional shipping refund

### Bounded Context

The Fulfillment Service operates within the **Commerce Fulfillment** bounded context, bounded by:

| Boundary | Description |
|----------|-------------|
| **Upstream** | tax_service (triggers shipment preparation via `tax.calculated`), payment_service (triggers label creation via `payment.completed`), order_service (triggers cancellation via `order.canceled`) |
| **Downstream** | notification_service (delivery notifications to customers), billing_service (shipping cost tracking) |
| **Lateral** | inventory_service (committed inventory for shipment), audit_service (fulfillment audit trail) |

### Domain Entities

| Entity | Description | Lifecycle |
|--------|-------------|-----------|
| **Shipment** | Shipping record for an order with items, address, carrier, and tracking | CREATED → LABEL_PURCHASED → IN_TRANSIT → DELIVERED / FAILED |
| **ShipmentItem** | Individual item within a shipment | Created with parent shipment; immutable |
| **Parcel** | Physical package with weight and dimensions | Created with shipment; immutable |

---

## Terminology (Ubiquitous Language)

### Core Terms

| Term | Definition | Example |
|------|------------|---------|
| **Shipment** | A shipping record tying an order to carrier and tracking info | Shipment `shp_abc123` for order `ORD-456` |
| **Carrier** | Shipping provider responsible for delivery | USPS, FedEx, UPS, DHL |
| **Tracking Number** | Carrier-assigned identifier for package tracking | `trk_a1b2c3d4e5` |
| **Label** | Shipping label with carrier barcode and address | PDF/image URL for label printing |
| **Label URL** | URL to download or print the shipping label | `https://labels.carrier.com/lbl_xyz` |
| **Estimated Delivery** | Projected delivery date based on carrier and service | 5 business days from label creation |

### Shipment Status Terms

| Status | Meaning | Trigger |
|--------|---------|---------|
| **CREATED** | Shipment record exists, awaiting label | After tax calculation completes |
| **LABEL_PURCHASED** | Shipping label generated, ready for carrier pickup | After payment completes |
| **IN_TRANSIT** | Package picked up by carrier, en route | Carrier webhook / tracking update |
| **DELIVERED** | Package delivered to recipient | Carrier delivery confirmation |
| **FAILED** | Shipment cancelled or delivery failed | Manual cancellation or order cancellation |

---

## Business Capabilities

### BR-FUL-001: Create Shipment

**Capability**: Create a shipment record for an order with items and shipping address

**Business Rules**:
- BR-FUL-001.1: Request requires `order_id`, non-empty `items` list, and non-empty `address` dict
- BR-FUL-001.2: `user_id` defaults to "unknown" if not provided
- BR-FUL-001.3: System generates unique `shipment_id` with prefix `shp_`
- BR-FUL-001.4: Initial status is `created`
- BR-FUL-001.5: `fulfillment.shipment.prepared` event is published on success
- BR-FUL-001.6: Missing required fields → 400 Bad Request
- BR-FUL-001.7: Repository unavailable → 503 Service Unavailable

### BR-FUL-002: Create Shipping Label

**Capability**: Generate a shipping label with carrier and tracking information

**Business Rules**:
- BR-FUL-002.1: Shipment must exist (404 if not found)
- BR-FUL-002.2: Status transitions to `label_purchased`
- BR-FUL-002.3: `carrier`, `tracking_number`, and `label_url` are set
- BR-FUL-002.4: `fulfillment.label.created` event is published
- BR-FUL-002.5: If label already exists, returns existing label info (idempotent)
- BR-FUL-002.6: Default carrier is "USPS" via mock provider

### BR-FUL-003: Cancel Shipment

**Capability**: Cancel a shipment and optionally refund shipping costs

**Business Rules**:
- BR-FUL-003.1: Shipment must exist (404 if not found)
- BR-FUL-003.2: Status transitions to `failed` (cancelled)
- BR-FUL-003.3: `cancellation_reason` is recorded (default: "manual_cancellation")
- BR-FUL-003.4: If status was `label_purchased`, `refund_shipping` flag is set to true
- BR-FUL-003.5: `fulfillment.shipment.canceled` event is published
- BR-FUL-003.6: Already-failed shipments return success (idempotent)

### BR-FUL-004: Retrieve Shipment

**Capability**: Look up shipment by order ID or tracking number

**Business Rules**:
- BR-FUL-004.1: GET by order_id returns the most recent shipment for that order
- BR-FUL-004.2: GET by tracking_number returns the shipment with that tracking number
- BR-FUL-004.3: Returns 404 if no matching shipment found
- BR-FUL-004.4: Returns 503 if repository unavailable

---

## State Machine

### Shipment Status Lifecycle

```
CREATED → LABEL_PURCHASED → IN_TRANSIT → DELIVERED
    ↓           ↓
  FAILED      FAILED (canceled)
```

| From | To | Trigger |
|------|----|---------|
| CREATED | LABEL_PURCHASED | Label creation (after payment) |
| CREATED | FAILED | Cancellation (order cancelled before payment) |
| LABEL_PURCHASED | IN_TRANSIT | Carrier pickup |
| LABEL_PURCHASED | FAILED | Cancellation (refund shipping) |
| IN_TRANSIT | DELIVERED | Delivery confirmation |

---

## Domain Events

### Events Published

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `fulfillment.shipment.prepared` | `fulfillment.shipment.prepared` | Shipment created for order | order_id, shipment_id, user_id, items, shipping_address, estimated_weight_grams |
| `fulfillment.label.created` | `fulfillment.label.created` | Shipping label generated | order_id, shipment_id, user_id, carrier, tracking_number, label_url, estimated_delivery |
| `fulfillment.shipment.canceled` | `fulfillment.shipment.canceled` | Shipment cancelled | order_id, shipment_id, user_id, reason, refund_shipping |
| `fulfillment.shipment.failed` | `fulfillment.shipment.failed` | Shipment creation failed | order_id, user_id, error_code, error_message |

### Events Subscribed

| Event | Source | Handler |
|-------|--------|---------|
| `tax.calculated` | tax_service | Prepare shipment after tax is calculated |
| `payment.completed` | payment_service | Create shipping label after payment |
| `order.canceled` | order_service | Cancel shipment if order is cancelled |

---

## Integration Points

### Upstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **tax_service** | Triggers shipment preparation | NATS subscription (`tax.calculated`) | Queue events, retry |
| **payment_service** | Triggers label creation | NATS subscription (`payment.completed`) | Queue events, retry |
| **order_service** | Triggers cancellation | NATS subscription (`order.canceled`) | Queue events, retry |

### Downstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **notification_service** | Delivery status notifications | Async event publishing (future) | Manual tracking lookup |

### Cross-Cutting Dependencies

| Service | Purpose | Integration Pattern |
|---------|---------|---------------------|
| **PostgreSQL** | Primary data store (schema: `fulfillment`) | AsyncPostgresClient |
| **NATS JetStream** | Event pub/sub | core.nats_client |
| **Consul** | Service registration and discovery | isa_common.ConsulRegistry |

---

## Quality Attributes

| Attribute | Target | Rationale |
|-----------|--------|-----------|
| **Availability** | 99.9% | Fulfillment blocks order completion |
| **Latency (Create Shipment)** | p99 < 300ms | Must not block commerce pipeline |
| **Data Durability** | Zero shipment loss | Every shipment must be tracked |
| **Idempotency** | All write operations | Duplicate events must not create duplicate shipments |

---

## Future Considerations

1. **Real carrier integration**: USPS, FedEx, UPS APIs for label generation and tracking
2. **Multi-parcel shipments**: Split orders across multiple packages
3. **Return shipments**: Customer return label generation and tracking
4. **Carrier rate shopping**: Compare rates across carriers for cost optimization
5. **Delivery notifications**: Real-time tracking updates pushed to customers
6. **International shipping**: Customs forms, duties calculation, cross-border compliance

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
**Domain Owner**: Commerce Platform Team
