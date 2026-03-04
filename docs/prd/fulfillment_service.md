# Fulfillment Service - Product Requirements Document

## Executive Summary

The Fulfillment Service manages shipping and delivery for physical goods in the isA e-commerce platform. It handles the complete shipment lifecycle from preparation through label creation to tracking and cancellation, integrating with upstream commerce events to automate the fulfillment pipeline.

---

## Product Vision

**For** e-commerce operations teams and customers awaiting deliveries
**Who** need reliable shipping management with tracking
**The** Fulfillment Service is a shipment lifecycle management system
**That** automates shipment preparation, label creation, and tracking
**Unlike** manual shipping workflows
**Our product** integrates with the event-driven commerce pipeline to auto-prepare shipments and auto-create labels based on upstream events

---

## Goals and Success Metrics

### Primary Goals

| Goal | Metric | Target |
|------|--------|--------|
| Automate shipment preparation | Shipments auto-created via events | > 95% |
| Reliable label generation | Label creation success rate | > 99.5% |
| End-to-end tracking | Shipments with tracking numbers | 100% |
| Handle cancellations gracefully | Refund-eligible cancellations processed | 100% |

### Key Performance Indicators (KPIs)

| KPI | Definition | Target |
|-----|------------|--------|
| **Preparation Latency** | Time from tax.calculated to shipment created | < 5s |
| **Label Creation Latency** | Time from payment.completed to label created | < 10s |
| **Tracking Coverage** | Shipments with tracking / Total shipments | 100% |
| **Cancellation Success** | Successful cancellations / Cancellation requests | 100% |

---

## User Stories

### Epic 1: Shipment Management

#### US-FUL-001: Create Shipment for Order

**As a** warehouse operator
**I want** a shipment record created when an order is ready
**So that** I can prepare the package for shipping

**Acceptance Criteria**:
- AC-001.1: Accepts order_id, items list, and shipping address
- AC-001.2: Generates unique shipment_id with `shp_` prefix
- AC-001.3: Initial status is `created`
- AC-001.4: `fulfillment.shipment.prepared` event published
- AC-001.5: Missing required fields returns 400
- AC-001.6: Repository unavailable returns 503

**Priority**: P0 - Must Have

---

#### US-FUL-002: Create Shipping Label

**As a** warehouse operator
**I want to** generate a shipping label for a prepared shipment
**So that** the package can be handed to the carrier

**Acceptance Criteria**:
- AC-002.1: Generates carrier assignment and tracking number
- AC-002.2: Status transitions to `label_purchased`
- AC-002.3: `fulfillment.label.created` event published
- AC-002.4: Estimated delivery date calculated (default +5 days)
- AC-002.5: Idempotent — duplicate requests return existing label
- AC-002.6: Shipment not found returns 404

**Priority**: P0 - Must Have

---

#### US-FUL-003: Cancel Shipment

**As a** customer support agent
**I want to** cancel a shipment when an order is cancelled
**So that** the package is not shipped and shipping costs are refunded if applicable

**Acceptance Criteria**:
- AC-003.1: Status transitions to `failed` (cancelled)
- AC-003.2: Cancellation reason recorded
- AC-003.3: If label was purchased, `refund_shipping` flag set to true
- AC-003.4: `fulfillment.shipment.canceled` event published
- AC-003.5: Already-cancelled shipments return success (idempotent)
- AC-003.6: Shipment not found returns 404

**Priority**: P0 - Must Have

---

#### US-FUL-004: Track Shipment

**As a** customer
**I want to** look up my shipment by order ID or tracking number
**So that** I can see the delivery status

**Acceptance Criteria**:
- AC-004.1: GET by order_id returns latest shipment
- AC-004.2: GET by tracking_number returns matching shipment
- AC-004.3: Returns carrier, status, tracking number
- AC-004.4: Returns 404 if not found

**Priority**: P1 - High

---

### Epic 2: Event-Driven Fulfillment

#### US-FUL-005: Auto-Prepare Shipment on Tax Calculated

**As a** commerce pipeline
**I want** shipments to be prepared automatically after tax calculation
**So that** the fulfillment step doesn't require manual intervention

**Acceptance Criteria**:
- AC-005.1: Subscribes to `tax.calculated` events
- AC-005.2: Creates shipment with order items and address
- AC-005.3: Publishes `fulfillment.shipment.prepared` event
- AC-005.4: Skips if shipment already exists for order (idempotent)
- AC-005.5: Publishes `fulfillment.shipment.failed` on error

**Priority**: P0 - Must Have

---

#### US-FUL-006: Auto-Create Label on Payment Completed

**As a** commerce pipeline
**I want** shipping labels created automatically after payment
**So that** orders ship as soon as they're paid

**Acceptance Criteria**:
- AC-006.1: Subscribes to `payment.completed` events
- AC-006.2: Finds shipment for the order
- AC-006.3: Creates label with carrier and tracking
- AC-006.4: Publishes `fulfillment.label.created` event
- AC-006.5: Skips if label already exists (idempotent)

**Priority**: P0 - Must Have

---

#### US-FUL-007: Auto-Cancel on Order Cancelled

**As a** commerce pipeline
**I want** shipments cancelled automatically when orders are cancelled
**So that** we don't ship cancelled orders

**Acceptance Criteria**:
- AC-007.1: Subscribes to `order.canceled` events
- AC-007.2: Cancels shipment and records reason
- AC-007.3: Sets refund_shipping if label was purchased
- AC-007.4: Publishes `fulfillment.shipment.canceled` event
- AC-007.5: No-op if no shipment exists (order cancelled before preparation)

**Priority**: P0 - Must Have

---

## API Specification

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/api/v1/fulfillment/health` | Service health check (API v1) | No |
| POST | `/api/v1/fulfillment/shipments` | Create shipment | Yes |
| POST | `/api/v1/fulfillment/shipments/{id}/label` | Create shipping label | Yes |
| POST | `/api/v1/fulfillment/shipments/{id}/cancel` | Cancel shipment | Yes |
| GET | `/api/v1/fulfillment/shipments/{order_id}` | Get shipment by order | Yes |
| GET | `/api/v1/fulfillment/tracking/{tracking_number}` | Get by tracking number | Yes |

### Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Missing order_id, items, or address |
| 404 | Shipment or tracking number not found |
| 503 | Repository not available |

---

## Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Availability** | 99.9% | Blocks order completion |
| **Response Time** | p99 < 300ms | Commerce pipeline budget |
| **Idempotency** | All operations | Duplicate events must not duplicate shipments |
| **Recovery** | < 30s failover | Order flow continuity |

---

## Dependencies

| Service | Direction | Integration |
|---------|-----------|-------------|
| tax_service | Upstream | `tax.calculated` → prepare shipment |
| payment_service | Upstream | `payment.completed` → create label |
| order_service | Upstream | `order.canceled` → cancel shipment |
| notification_service | Downstream | Delivery notifications (future) |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
**Product Owner**: Commerce Platform Team
