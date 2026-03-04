# Inventory Service - Product Requirements Document

## Executive Summary

The Inventory Service provides real-time stock management and reservation capabilities for the isA e-commerce platform. It ensures accurate stock tracking, prevents overselling through atomic reservation operations, and integrates with the order-to-fulfillment pipeline via event-driven communication.

---

## Product Vision

**For** e-commerce operations teams and order processing systems
**Who** need reliable inventory tracking and reservation management
**The** Inventory Service is a real-time stock management system
**That** provides atomic reserve/commit/release operations with automatic expiry
**Unlike** simple stock counters
**Our product** prevents overselling through atomic operations, supports both physical and digital inventory, and integrates seamlessly into the event-driven commerce pipeline

---

## Goals and Success Metrics

### Primary Goals

| Goal | Metric | Target |
|------|--------|--------|
| Prevent overselling | Oversell incidents | 0 |
| Enable real-time stock visibility | Stock accuracy | 100% |
| Support order flow without bottlenecks | Reservation latency (p99) | < 200ms |
| Prevent stock lockup from abandoned carts | Expired reservation auto-release rate | 100% |

### Key Performance Indicators (KPIs)

| KPI | Definition | Target |
|-----|------------|--------|
| **Reservation Success Rate** | Successful reservations / Total attempts | > 99.5% |
| **Commit Latency** | Time from payment to commit | < 100ms |
| **Expiry Coverage** | Expired reservations released / Total expired | 100% |
| **Stock Accuracy** | Actual stock = reported stock | 100% |

---

## User Stories

### Epic 1: Inventory Reservation

#### US-INV-001: Reserve Stock for Order

**As a** order processing system
**I want to** reserve inventory when an order is created
**So that** items are held for the customer during checkout

**Acceptance Criteria**:
- AC-001.1: Reserve request requires order_id, sku_id, and quantity (> 0)
- AC-001.2: Reservation succeeds if available stock >= requested quantity
- AC-001.3: Available stock decremented atomically on reservation
- AC-001.4: Reservation has unique ID with `rsv_` prefix
- AC-001.5: Reservation expires after configurable TTL (default 30 minutes)
- AC-001.6: `inventory.reserved` event published on success
- AC-001.7: Insufficient stock returns clear error with available quantity

**Priority**: P0 - Must Have

---

#### US-INV-002: Commit Reservation After Payment

**As a** payment processing system
**I want to** commit inventory reservations after successful payment
**So that** reserved stock is permanently allocated to the order

**Acceptance Criteria**:
- AC-002.1: Only ACTIVE reservations can be committed
- AC-002.2: Status transitions to COMMITTED
- AC-002.3: `inventory.committed` event published
- AC-002.4: Invalid reservation ID returns 404

**Priority**: P0 - Must Have

---

#### US-INV-003: Release Reservation on Cancellation

**As a** order management system
**I want to** release reservations when an order is cancelled
**So that** stock returns to the available pool

**Acceptance Criteria**:
- AC-003.1: Only ACTIVE reservations can be released
- AC-003.2: Available stock incremented by reservation quantity
- AC-003.3: `inventory.released` event published
- AC-003.4: Cancellation reason recorded

**Priority**: P0 - Must Have

---

#### US-INV-004: Auto-Expire Stale Reservations

**As a** operations team
**I want** expired reservations to auto-release
**So that** abandoned carts don't lock up stock permanently

**Acceptance Criteria**:
- AC-004.1: Reservations past `expires_at` are automatically expired
- AC-004.2: Stock returned to available pool
- AC-004.3: `inventory.expired` event published
- AC-004.4: Background sweep runs periodically

**Priority**: P1 - High

---

### Epic 2: Stock Management

#### US-INV-005: Track Stock Levels

**As a** warehouse operator
**I want to** view current stock levels per SKU
**So that** I can manage replenishment

**Acceptance Criteria**:
- AC-005.1: Shows on_hand, reserved, and available for each SKU
- AC-005.2: Supports filtering by location_id
- AC-005.3: Supports finite and infinite inventory policies

**Priority**: P1 - High

---

#### US-INV-006: Digital Item Infinite Stock

**As a** product manager
**I want** digital items to have infinite inventory
**So that** digital goods are never out of stock

**Acceptance Criteria**:
- AC-006.1: Items with `infinite` policy always succeed reservation
- AC-006.2: No stock level tracking needed for infinite items
- AC-006.3: Policy set per SKU via inventory_policy field

**Priority**: P1 - High

---

## API Specification

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/api/v1/inventory/health` | Service health check (API v1) | No |
| POST | `/api/v1/inventory/reserve` | Reserve inventory for order | Yes |
| POST | `/api/v1/inventory/commit` | Commit reservation after payment | Yes |
| POST | `/api/v1/inventory/release` | Release reservation | Yes |
| GET | `/api/v1/inventory/stock/{sku_id}` | Get stock levels for SKU | Yes |
| GET | `/api/v1/inventory/reservations/{order_id}` | Get reservations for order | Yes |

### Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Missing required fields or invalid quantity |
| 404 | Reservation or SKU not found |
| 409 | Insufficient stock for reservation |
| 503 | Repository unavailable |

---

## Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Availability** | 99.9% | Blocks order flow |
| **Response Time** | p99 < 200ms | Checkout latency budget |
| **Consistency** | Strong per-SKU | Overselling prevention |
| **Recovery** | < 30s failover | Order flow continuity |

---

## Dependencies

| Service | Direction | Integration |
|---------|-----------|-------------|
| order_service | Upstream | `order.created` → reserve |
| payment_service | Upstream | `payment.completed` → commit |
| tax_service | Downstream | `inventory.reserved` → calculate tax |
| fulfillment_service | Downstream | Committed inventory → ship |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
**Product Owner**: Commerce Platform Team
