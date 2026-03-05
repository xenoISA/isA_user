# Fulfillment Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Fulfillment Service
**Version**: 1.0.0
**Status**: Production
**Owner**: Platform Commerce Team
**Last Updated**: 2026-03-05

### Vision
Manage the complete shipment lifecycle — from order fulfillment to delivery tracking — with carrier-agnostic integrations and real-time event-driven status updates.

### Mission
Provide a unified shipment management API that creates shipments, generates shipping labels, tracks delivery, and handles cancellations with full visibility for customers and operations.

### Target Users
- **Order Service**: Triggers shipment creation after payment
- **Warehouse Staff**: Generates shipping labels for packages
- **Customer Support**: Queries shipment status, processes cancellations
- **Customers**: Tracks delivery via tracking number
- **Billing Service**: Receives shipping cost and refund events

### Key Differentiators
1. **Idempotent Label Creation**: Re-requesting a label returns existing one
2. **Carrier-Agnostic**: Pluggable provider interface for multiple carriers
3. **Refund Awareness**: Tracks whether shipping costs need refunding on cancel
4. **Full Lifecycle Tracking**: Created → Label → In Transit → Delivered

---

## Product Goals

### Primary Goals
1. **Shipment Reliability**: 100% of paid orders get shipment records
2. **Label Generation**: <500ms label creation latency
3. **Tracking Accuracy**: >99% correct tracking numbers
4. **Event Integration**: >99.5% event publishing success rate

### Secondary Goals
1. **Multi-Carrier**: Support USPS, UPS, FedEx through providers
2. **Rate Shopping**: Compare carrier rates (future)
3. **Batch Labels**: Generate labels for multiple shipments (future)

---

## Epics and User Stories

### Epic 1: Shipment Management

**Objective**: Create and manage shipments for orders

#### E1-US1: Create Shipment
**As a** Order Service
**I want to** create a shipment for an order
**So that** the order can be fulfilled and shipped

**Acceptance Criteria**:
- AC1: `POST /api/v1/fulfillment/shipments` creates shipment
- AC2: Requires `order_id`, `items`, and `address` (400 if missing)
- AC3: Generates unique `shipment_id` with `shp_` prefix
- AC4: Gets initial tracking info from fulfillment provider
- AC5: Sets status to "created"
- AC6: Publishes `fulfillment.shipment.prepared` event
- AC7: Response time <1s

**API Reference**: `POST /api/v1/fulfillment/shipments`

**Example Request**:
```json
{
  "order_id": "ord_abc123",
  "items": [
    {"sku_id": "sku_widget_01", "quantity": 2, "weight_grams": 500}
  ],
  "address": {
    "name": "Jane Doe",
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105",
    "country": "US"
  },
  "user_id": "usr_xyz789"
}
```

**Example Response**:
```json
{
  "shipment_id": "shp_def456",
  "order_id": "ord_abc123",
  "status": "created",
  "tracking_number": "TRK1234567890"
}
```

#### E1-US2: Generate Shipping Label
**As a** warehouse operator
**I want to** generate a shipping label for a shipment
**So that** the package can be picked up by the carrier

**Acceptance Criteria**:
- AC1: `POST /api/v1/fulfillment/shipments/{shipment_id}/label` creates label
- AC2: If label already exists, returns existing (idempotent)
- AC3: Assigns carrier (default: USPS) and tracking number
- AC4: Updates status to "label_purchased"
- AC5: Publishes `fulfillment.label.created` event
- AC6: Returns 404 if shipment not found
- AC7: Response time <500ms

**API Reference**: `POST /api/v1/fulfillment/shipments/{shipment_id}/label`

**Example Response**:
```json
{
  "shipment_id": "shp_def456",
  "tracking_number": "trk_a1b2c3d4e5",
  "carrier": "USPS",
  "status": "label_created"
}
```

#### E1-US3: Cancel Shipment
**As a** Customer Support agent
**I want to** cancel a shipment
**So that** the order cancellation is reflected in fulfillment

**Acceptance Criteria**:
- AC1: `POST /api/v1/fulfillment/shipments/{shipment_id}/cancel` cancels shipment
- AC2: Already-canceled returns success (idempotent)
- AC3: If label was purchased, sets `refund_shipping = true`
- AC4: Updates status to "failed" with reason
- AC5: Publishes `fulfillment.shipment.canceled` event
- AC6: Returns 404 if shipment not found

**API Reference**: `POST /api/v1/fulfillment/shipments/{shipment_id}/cancel`

**Example Request**:
```json
{
  "reason": "customer_requested"
}
```

**Example Response**:
```json
{
  "shipment_id": "shp_def456",
  "status": "canceled",
  "refund_shipping": true
}
```

### Epic 2: Shipment Tracking

**Objective**: Enable shipment lookup by order or tracking number

#### E2-US1: Get Shipment by Order
**As a** customer
**I want to** check my order's shipment status
**So that** I know when to expect delivery

**Acceptance Criteria**:
- AC1: `GET /api/v1/fulfillment/shipments/order/{order_id}` returns shipment
- AC2: Returns latest shipment for the order
- AC3: Includes full details (carrier, tracking, status, timestamps)
- AC4: Returns 404 if no shipment exists
- AC5: Response time <50ms

#### E2-US2: Get Shipment by Tracking Number
**As a** customer
**I want to** look up a shipment by tracking number
**So that** I can track my package

**Acceptance Criteria**:
- AC1: `GET /api/v1/fulfillment/shipments/tracking/{tracking_number}` returns shipment
- AC2: Returns full shipment details
- AC3: Returns 404 if not found
- AC4: Response time <50ms

---

## API Surface

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/fulfillment/shipments` | Create shipment | JWT |
| POST | `/api/v1/fulfillment/shipments/{id}/label` | Generate label | JWT |
| POST | `/api/v1/fulfillment/shipments/{id}/cancel` | Cancel shipment | JWT |
| GET | `/api/v1/fulfillment/shipments/order/{order_id}` | Get by order | JWT |
| GET | `/api/v1/fulfillment/shipments/tracking/{tracking}` | Get by tracking | JWT |
| GET | `/health` | Health check | None |
| GET | `/api/v1/fulfillment/health` | Service health check | None |

---

## Functional Requirements

| ID | Requirement |
|----|------------|
| FR-001 | System SHALL create shipments with unique IDs and tracking numbers |
| FR-002 | System SHALL validate order_id, items, and address before creation |
| FR-003 | System SHALL generate shipping labels with carrier assignment |
| FR-004 | System SHALL support idempotent label creation |
| FR-005 | System SHALL cancel shipments with reason tracking |
| FR-006 | System SHALL track refund_shipping flag when label was purchased |
| FR-007 | System SHALL publish events for all lifecycle transitions |
| FR-008 | System SHALL support lookup by order_id and tracking_number |

## Non-Functional Requirements

| ID | Requirement |
|----|------------|
| NFR-001 | Shipment creation SHALL complete in <1s (p95) |
| NFR-002 | Label generation SHALL complete in <500ms (p95) |
| NFR-003 | Queries SHALL complete in <50ms (p95) |
| NFR-004 | Service SHALL be available 99.9% of the time |
| NFR-005 | Event publishing SHALL be best-effort (non-blocking) |
| NFR-006 | Service SHALL handle 500+ concurrent shipments |
| NFR-007 | Service SHALL register with Consul for discovery |

---

## Success Criteria

| Phase | Criteria | Status |
|-------|---------|--------|
| MVP | Create shipment, generate label, cancel | Complete |
| MVP | Event publishing for all transitions | Complete |
| MVP | Lookup by order and tracking number | Complete |
| V1.1 | Multi-carrier provider support | Planned |
| V1.1 | Carrier rate comparison | Planned |
| V1.2 | Batch label generation | Planned |
| V1.2 | Return shipment management | Planned |

---

## Out of Scope
- Carrier rate negotiation — procurement
- Returns and reverse logistics — returns service
- Warehouse pick/pack workflows — WMS
- International customs and duties — customs service
- Delivery scheduling — last-mile service

---

## Dependencies

| Dependency | Type | Required |
|-----------|------|----------|
| PostgreSQL | Infrastructure | Yes |
| NATS | Infrastructure | No (graceful degradation) |
| Consul | Infrastructure | No (graceful degradation) |
| Fulfillment Provider | Internal | Yes (mock provider as fallback) |
| Tax Service | Event source | Triggers shipment preparation |
| Payment Service | Event source | Confirms payment |
| Order Service | Event source | Cancellation events |
