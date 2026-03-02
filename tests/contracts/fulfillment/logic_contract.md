# Fulfillment Service Logic Contract

**Business Rules and Specifications for Fulfillment Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for fulfillment service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Integration Contracts](#integration-contracts)
5. [Error Handling Contracts](#error-handling-contracts)

---

## Business Rules

### Shipment Creation Rules

### BR-FUL-001: Required Fields for Shipment Creation
**Given**: POST /api/v1/fulfillment/shipments request
**When**: Shipment is created
**Then**:
- `order_id` MUST be non-empty string
- `items` MUST be a non-empty list
- `address` MUST be a non-empty dict
- `user_id` defaults to "unknown" if not provided

**Validation Rules**:
- Missing order_id → 400 Bad Request
- Missing items → 400 Bad Request
- Missing address → 400 Bad Request

---

### BR-FUL-002: Shipment ID Generation
**Given**: Valid shipment creation request
**When**: Shipment is created
**Then**:
- System generates unique `shipment_id` with prefix `shp_`
- System generates `tracking_number` with prefix `TRK`
- Initial status is `created`
- `created_at` timestamp is set to current UTC time

---

### BR-FUL-003: Label Creation
**Given**: POST /api/v1/fulfillment/shipments/{shipment_id}/label
**When**: Label is created for an existing shipment
**Then**:
- Shipment status updates to `label_purchased`
- `label_url`, `carrier`, and `tracking_number` are set
- `label_created_at` timestamp is recorded
- `shipment.label_created` event is published

**Edge Cases**:
- Shipment not found → 404 Not Found
- Label already created → still succeeds (idempotent)

---

### BR-FUL-004: Shipment Cancellation
**Given**: POST /api/v1/fulfillment/shipments/{shipment_id}/cancel
**When**: Shipment is canceled
**Then**:
- Status updates to `failed` (canceled)
- `canceled_at` timestamp is set
- `cancellation_reason` is recorded
- `shipment.canceled` event is published
- Default reason is "manual_cancellation"

**Edge Cases**:
- Shipment not found → 404 Not Found
- Already delivered shipment → still processes (no guard)

---

## State Machines

### Shipment Status Lifecycle

```
CREATED → LABEL_PURCHASED → IN_TRANSIT → DELIVERED
    ↓           ↓
  FAILED      FAILED (canceled)
```

| From | To | Trigger |
|------|----|---------|
| CREATED | LABEL_PURCHASED | Label creation |
| CREATED | FAILED | Cancellation |
| LABEL_PURCHASED | IN_TRANSIT | Carrier pickup |
| LABEL_PURCHASED | FAILED | Cancellation |
| IN_TRANSIT | DELIVERED | Delivery confirmation |

---

## Edge Cases

### EC-FUL-001: Duplicate Order Shipment
- Creating a shipment for an order that already has one succeeds (creates new)
- GET by order_id returns the latest shipment

### EC-FUL-002: Repository Unavailable
- If repository is None at request time → 503 Service Unavailable

---

## Integration Contracts

### Event Publishing

| Event | Subject | When |
|-------|---------|------|
| `shipment.prepared` | `fulfillment.shipment.prepared` | After shipment creation |
| `label.created` | `fulfillment.label.created` | After label purchase |
| `shipment.canceled` | `fulfillment.shipment.canceled` | After cancellation |

Event publishing is best-effort (failures logged, not thrown).

### External Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | gRPC | Primary data store |
| NATS | Native | Event publishing |
| Consul | HTTP | Service registration |

---

## Error Handling Contracts

| Condition | HTTP Status | Response |
|-----------|-------------|----------|
| Missing required fields | 400 | `{"detail": "order_id, items, address required"}` |
| Shipment not found | 404 | `{"detail": "Shipment not found"}` |
| Repository unavailable | 503 | `{"detail": "Repository not available"}` |
| Internal error | 500 | `{"detail": "<error message>"}` |
