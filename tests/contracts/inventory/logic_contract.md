# Inventory Service Logic Contract

**Business Rules and Specifications for Inventory Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for inventory service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Integration Contracts](#integration-contracts)
5. [Error Handling Contracts](#error-handling-contracts)

---

## Business Rules

### Reservation Rules

### BR-INV-001: Reserve Inventory
**Given**: POST /api/v1/inventory/reserve request
**When**: Stock reservation is created
**Then**:
- `order_id` and `items` MUST be provided
- System generates unique `reservation_id` with prefix `res_`
- Reservation `status` is set to `active`
- `expires_at` is set to current time + 30 minutes (default)
- `inventory.reserved` event is published

**Validation Rules**:
- Missing order_id → 400 Bad Request
- Missing items → 400 Bad Request

---

### BR-INV-002: Commit Reservation
**Given**: POST /api/v1/inventory/commit request
**When**: Reservation is committed after payment
**Then**:
- `order_id` MUST be provided
- Active reservation for the order is found
- Status updates from `active` to `committed`
- `committed_at` timestamp is set
- `inventory.committed` event is published

**Edge Cases**:
- No active reservation → 404 Not Found
- Already committed → still processes

---

### BR-INV-003: Release Reservation
**Given**: POST /api/v1/inventory/release request
**When**: Reservation is released (order canceled)
**Then**:
- `order_id` MUST be provided
- Active reservation for the order is found
- Status updates from `active` to `released`
- `released_at` timestamp is set
- `inventory.released` event is published

**Edge Cases**:
- No active reservation → 200 OK with `{"order_id": ..., "status": "released", "message": "No active reservation found"}`
- Already released → still processes

---

### BR-INV-004: Reservation Expiry
**Given**: Reservation with `expires_at` in the past
**When**: System checks reservation status
**Then**:
- Status transitions to `expired`
- Stock levels are restored

---

## State Machines

### Reservation Status Lifecycle

```
ACTIVE → COMMITTED (payment confirmed)
   ↓
RELEASED (order canceled)
   ↓
EXPIRED (timeout, 30 min default)
```

| From | To | Trigger |
|------|----|---------|
| ACTIVE | COMMITTED | Payment confirmation |
| ACTIVE | RELEASED | Order cancellation |
| ACTIVE | EXPIRED | Timeout (30 min) |

---

## Edge Cases

### EC-INV-001: Concurrent Reservations
- Multiple reservations for the same order → latest active is used
- get_active_reservation_for_order returns first match with status=active

### EC-INV-002: Repository Unavailable
- If repository is None at request time → 503 Service Unavailable

### EC-INV-003: Event Bus Unavailable
- Event publishing is best-effort (failures logged, not thrown)

---

## Integration Contracts

### Event Publishing

| Event | Subject | When |
|-------|---------|------|
| `inventory.reserved` | `inventory.reserved` | After reservation creation |
| `inventory.committed` | `inventory.committed` | After reservation commit |
| `inventory.released` | `inventory.released` | After reservation release |
| `inventory.failed` | `inventory.failed` | On reservation failure |

### Event Subscriptions

| Event | Source | Handler |
|-------|--------|---------|
| `order.created` | Order Service | Auto-reserve inventory |
| `payment.completed` | Payment Service | Auto-commit reservation |
| `order.canceled` | Order Service | Auto-release reservation |

### External Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | gRPC | Primary data store |
| NATS | Native | Event pub/sub |
| Consul | HTTP | Service registration |

---

## Error Handling Contracts

| Condition | HTTP Status | Response |
|-----------|-------------|----------|
| Missing order_id or items | 400 | `{"detail": "order_id and items are required"}` |
| Missing order_id | 400 | `{"detail": "order_id is required"}` |
| Reservation not found | 404 | `{"detail": "Reservation not found"}` |
| No active reservation (commit) | 404 | `{"detail": "No active reservation found"}` |
| No active reservation (release) | 200 | `{"order_id": ..., "status": "released", "message": "No active reservation found"}` |
| Repository unavailable | 503 | `{"detail": "Repository not available"}` |
| Internal error | 500 | `{"detail": "<error message>"}` |
