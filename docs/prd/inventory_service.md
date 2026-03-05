# Inventory Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Inventory Service
**Version**: 1.0.0
**Status**: Production
**Owner**: Platform Commerce Team
**Last Updated**: 2026-03-05

### Vision
Prevent overselling and ensure stock consistency across the commerce platform through real-time inventory tracking and time-bound reservation management.

### Mission
Provide a reliable reservation-based inventory system that locks stock during checkout, commits on payment, and automatically releases expired holds — ensuring no customer pays for out-of-stock items.

### Target Users
- **Order Service**: Reserves stock at order creation, releases on cancellation
- **Payment Service**: Triggers commitment of reserved stock after payment
- **Customer Support**: Queries reservation status for troubleshooting
- **Warehouse Systems**: Manages stock levels and location-based inventory

### Key Differentiators
1. **Time-Bound Reservations**: 30-minute auto-expiry prevents inventory deadlocks
2. **Event-Driven Integration**: NATS events trigger reserve/commit/release automatically
3. **Dual Policy Support**: Finite (physical) and infinite (digital) inventory policies
4. **Idempotent Operations**: Release of non-existent reservations returns success

---

## Product Goals

### Primary Goals
1. **Reservation Reliability**: 100% prevention of overselling for finite-stock items
2. **Low Latency**: Reservation creation <100ms, commit/release <50ms
3. **Automatic Expiry**: 100% cleanup of expired reservations
4. **Event Integration**: >99.5% event publishing success rate

### Secondary Goals
1. **Multi-Location**: Support inventory across multiple warehouses
2. **Audit Trail**: Full reservation lifecycle history
3. **Graceful Degradation**: Event bus unavailability doesn't block operations

---

## Epics and User Stories

### Epic 1: Inventory Reservation

**Objective**: Enable stock reservation during checkout flow

#### E1-US1: Reserve Inventory for Order
**As a** Order Service
**I want to** reserve stock for an order
**So that** items are held during payment processing

**Acceptance Criteria**:
- AC1: `POST /api/v1/inventory/reserve` creates reservation
- AC2: Requires `order_id` and `items` (400 if missing)
- AC3: Generates unique `reservation_id` with `res_` prefix
- AC4: Sets status to "active" with 30-minute expiry
- AC5: Publishes `inventory.reserved` event
- AC6: Response includes reservation_id, status, expires_at
- AC7: Response time <100ms

**API Reference**: `POST /api/v1/inventory/reserve`

**Example Request**:
```json
{
  "order_id": "ord_abc123",
  "items": [
    {"sku_id": "sku_widget_01", "quantity": 2, "unit_price": 29.99}
  ],
  "user_id": "usr_xyz789"
}
```

**Example Response**:
```json
{
  "reservation_id": "res_def456",
  "status": "active",
  "expires_at": "2026-03-05T11:30:00Z"
}
```

#### E1-US2: Commit Reservation
**As a** Payment Service
**I want to** commit a reservation after payment
**So that** stock is permanently allocated

**Acceptance Criteria**:
- AC1: `POST /api/v1/inventory/commit` commits reservation
- AC2: Requires `order_id` (400 if missing)
- AC3: Finds active reservation by order_id or reservation_id
- AC4: Updates status to "committed"
- AC5: Publishes `inventory.committed` event
- AC6: Returns 404 if no active reservation found
- AC7: Response time <50ms

**API Reference**: `POST /api/v1/inventory/commit`

**Example Request**:
```json
{
  "order_id": "ord_abc123",
  "reservation_id": "res_def456"
}
```

#### E1-US3: Release Reservation
**As a** Order Service
**I want to** release a reservation on cancellation
**So that** stock returns to available pool

**Acceptance Criteria**:
- AC1: `POST /api/v1/inventory/release` releases reservation
- AC2: Requires `order_id` (400 if missing)
- AC3: If no active reservation, returns 200 with message (idempotent)
- AC4: Updates status to "released"
- AC5: Publishes `inventory.released` event
- AC6: Accepts optional `reason` parameter
- AC7: Response time <50ms

**API Reference**: `POST /api/v1/inventory/release`

#### E1-US4: Get Reservation Status
**As a** Customer Support agent
**I want to** check reservation status for an order
**So that** I can troubleshoot inventory issues

**Acceptance Criteria**:
- AC1: `GET /api/v1/inventory/reservations/{order_id}` returns reservation
- AC2: Returns full reservation details including items and timestamps
- AC3: Returns 404 if no reservation found
- AC4: Response time <50ms

**API Reference**: `GET /api/v1/inventory/reservations/{order_id}`

---

### Epic 2: Event-Driven Automation

**Objective**: Automate inventory operations via event subscriptions

#### E2-US1: Auto-Reserve on Order Created
**As a** system
**I want to** automatically reserve inventory when an order is created
**So that** stock is held without manual intervention

**Acceptance Criteria**:
- AC1: Subscribes to `order.created` events
- AC2: Extracts items and order_id from event payload
- AC3: Calls reserve_inventory internally
- AC4: Publishes `inventory.reserved` on success

#### E2-US2: Auto-Commit on Payment
**As a** system
**I want to** automatically commit when payment completes
**So that** paid orders are permanently allocated

**Acceptance Criteria**:
- AC1: Subscribes to `payment.completed` events
- AC2: Calls commit_reservation with order_id from event
- AC3: Publishes `inventory.committed` on success

#### E2-US3: Auto-Release on Order Cancel
**As a** system
**I want to** automatically release on order cancellation
**So that** canceled orders free their stock

**Acceptance Criteria**:
- AC1: Subscribes to `order.canceled` events
- AC2: Calls release_reservation with order_id from event
- AC3: Publishes `inventory.released` on success

---

## API Surface

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/inventory/reserve` | Reserve stock for order | JWT |
| POST | `/api/v1/inventory/commit` | Commit reservation | JWT |
| POST | `/api/v1/inventory/release` | Release reservation | JWT |
| GET | `/api/v1/inventory/reservations/{order_id}` | Get reservation status | JWT |
| GET | `/health` | Health check | None |
| GET | `/api/v1/inventory/health` | Service health check | None |

---

## Functional Requirements

| ID | Requirement |
|----|------------|
| FR-001 | System SHALL create reservations with unique IDs and 30-minute expiry |
| FR-002 | System SHALL validate order_id and items before reservation |
| FR-003 | System SHALL commit reservations transitioning status to "committed" |
| FR-004 | System SHALL release reservations returning stock to available pool |
| FR-005 | System SHALL handle release of non-existent reservations gracefully |
| FR-006 | System SHALL publish events for all state transitions |
| FR-007 | System SHALL support finite and infinite inventory policies |
| FR-008 | System SHALL find reservations by order_id or reservation_id |

## Non-Functional Requirements

| ID | Requirement |
|----|------------|
| NFR-001 | Reservation creation SHALL complete in <100ms (p95) |
| NFR-002 | Commit and release SHALL complete in <50ms (p95) |
| NFR-003 | Service SHALL be available 99.9% of the time |
| NFR-004 | Event publishing SHALL be best-effort (non-blocking) |
| NFR-005 | Service SHALL handle 1000+ concurrent reservations |
| NFR-006 | Database queries SHALL use parameterized statements |
| NFR-007 | Service SHALL register with Consul for discovery |

---

## Success Criteria

| Phase | Criteria | Status |
|-------|---------|--------|
| MVP | Reserve, commit, release operations working | Complete |
| MVP | Event publishing for all state transitions | Complete |
| MVP | Health check and Consul registration | Complete |
| V1.1 | Automatic expiry background process | Planned |
| V1.1 | Multi-location inventory support | Planned |

---

## Out of Scope
- Stock level management (replenishment, adjustments) — separate stock management service
- Warehouse management (pick/pack workflows) — separate WMS
- Demand forecasting — analytics service
- Returns processing — returns service

---

## Dependencies

| Dependency | Type | Required |
|-----------|------|----------|
| PostgreSQL | Infrastructure | Yes |
| NATS | Infrastructure | No (graceful degradation) |
| Consul | Infrastructure | No (graceful degradation) |
| Order Service | Event source | Yes (triggers operations) |
| Payment Service | Event source | Yes (triggers commit) |
