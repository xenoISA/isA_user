# Tax Service - Product Requirements Document

## Executive Summary

The Tax Service computes and persists tax calculations for e-commerce orders. It determines applicable taxes based on shipping addresses and line items, supports pluggable tax providers for different jurisdictions, and integrates into the commerce pipeline via event-driven triggers from the Inventory Service.

---

## Product Vision

**For** e-commerce operations and compliance teams
**Who** need accurate, auditable tax calculations on every transaction
**The** Tax Service is a jurisdiction-aware tax computation engine
**That** calculates per-item tax breakdowns and persists results for audit
**Unlike** hardcoded tax rates
**Our product** uses a pluggable provider pattern supporting US/EU jurisdictions with full audit trail

---

## Goals and Success Metrics

### Primary Goals

| Goal | Metric | Target |
|------|--------|--------|
| Accurate tax calculation | Tax accuracy vs. manual audit | 100% |
| Complete audit trail | Calculations persisted with order_id | 100% |
| Non-blocking checkout | Tax calculation latency (p99) | < 300ms |
| Compliance readiness | Jurisdictions supported | US + EU |

### Key Performance Indicators (KPIs)

| KPI | Definition | Target |
|-----|------------|--------|
| **Calculation Success Rate** | Successful / Total requests | > 99.9% |
| **Persistence Rate** | Persisted / Total with order_id | 100% |
| **Event Delivery Rate** | Events published / Calculations persisted | 100% |
| **Provider Latency** | Provider response time p99 | < 200ms |

---

## User Stories

### Epic 1: Tax Calculation

#### US-TAX-001: Calculate Tax for Order Items

**As a** checkout system
**I want to** calculate tax for a cart of items with a shipping address
**So that** the customer sees the correct total before payment

**Acceptance Criteria**:
- AC-001.1: Accepts items list with quantity and unit_price
- AC-001.2: Accepts shipping address with state/country for jurisdiction
- AC-001.3: Returns total_tax and per-item line breakdown
- AC-001.4: Currency defaults to USD if not specified
- AC-001.5: Missing items or address returns 400
- AC-001.6: Zero-price items return zero tax

**Priority**: P0 - Must Have

---

#### US-TAX-002: Persist Tax Calculation

**As a** compliance officer
**I want** tax calculations tied to orders to be stored
**So that** we have an audit trail for every transaction

**Acceptance Criteria**:
- AC-002.1: Calculations with order_id are persisted to database
- AC-002.2: Each persisted calculation gets a unique calculation_id
- AC-002.3: `tax.calculated` event published after persistence
- AC-002.4: Calculations without order_id are NOT persisted (preview mode)

**Priority**: P0 - Must Have

---

#### US-TAX-003: Retrieve Tax Calculation

**As a** order management system
**I want to** retrieve the tax calculation for a specific order
**So that** I can display tax details and process refunds

**Acceptance Criteria**:
- AC-003.1: GET by order_id returns most recent calculation
- AC-003.2: Includes all tax lines, amounts, and metadata
- AC-003.3: Returns 404 if no calculation exists
- AC-003.4: Returns 503 if repository unavailable

**Priority**: P1 - High

---

### Epic 2: Event-Driven Tax

#### US-TAX-004: Auto-Calculate Tax on Inventory Reserved

**As a** commerce pipeline
**I want** tax to be calculated automatically when inventory is reserved
**So that** the order total is ready before payment

**Acceptance Criteria**:
- AC-004.1: Subscribes to `inventory.reserved` events
- AC-004.2: Extracts items and shipping address from event
- AC-004.3: Calculates tax and persists with order_id
- AC-004.4: Publishes `tax.calculated` event on success
- AC-004.5: Publishes `tax.failed` event on failure
- AC-004.6: Uses default address if none in event metadata

**Priority**: P0 - Must Have

---

### Epic 3: Tax Provider

#### US-TAX-005: Pluggable Tax Provider

**As a** platform engineer
**I want** tax rate logic to be behind a provider interface
**So that** we can swap between mock, Avalara, and other providers

**Acceptance Criteria**:
- AC-005.1: TaxProvider abstract base class defines calculate interface
- AC-005.2: MockTaxProvider returns zero tax (testing)
- AC-005.3: Provider receives items, address, and currency
- AC-005.4: Provider returns standardized response format

**Priority**: P1 - High

---

## API Specification

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | No |
| GET | `/api/v1/tax/health` | Service health check (API v1) | No |
| POST | `/api/v1/tax/calculate` | Calculate tax for items | Yes |
| GET | `/api/v1/tax/calculations/{order_id}` | Get tax calculation by order | Yes |

### Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Missing items or address |
| 404 | Tax calculation not found |
| 503 | Repository not available |
| 500 | Provider error |

---

## Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Availability** | 99.9% | Blocks payment step |
| **Response Time** | p99 < 300ms | Checkout latency budget |
| **Accuracy** | 100% jurisdiction match | Legal compliance |
| **Audit Trail** | All persisted calculations | Tax regulation requirement |

---

## Dependencies

| Service | Direction | Integration |
|---------|-----------|-------------|
| inventory_service | Upstream | `inventory.reserved` → auto-calculate |
| fulfillment_service | Downstream | `tax.calculated` → prepare shipment |
| payment_service | Downstream | Tax included in charge total |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
**Product Owner**: Commerce Platform Team
