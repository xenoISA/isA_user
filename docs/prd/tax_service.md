# Tax Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Tax Service
**Version**: 1.0.0
**Status**: Production
**Owner**: Platform Commerce Team
**Last Updated**: 2026-03-05

### Vision
Provide accurate, jurisdiction-aware tax calculation for all commerce transactions on the platform, with pluggable provider support for scaling from internal rules to enterprise tax compliance.

### Mission
Calculate tax amounts in real-time during checkout with support for preview (ephemeral) and persistent calculations, ensuring tax compliance and seamless billing integration.

### Target Users
- **Frontend / Cart**: Preview tax estimates during checkout
- **Order Service**: Persist tax calculations for finalized orders
- **Billing Service**: Query tax amounts for invoice generation
- **Finance / Compliance**: Audit tax calculations by order

### Key Differentiators
1. **Preview Mode**: Ephemeral tax estimates without database persistence
2. **Pluggable Providers**: Swap tax engines (mock, internal, Avalara) without API changes
3. **Per-Line Breakdown**: Jurisdiction-specific tax for each line item
4. **Event-Driven**: Auto-calculates tax when inventory is reserved

---

## Product Goals

### Primary Goals
1. **Calculation Accuracy**: 100% correct tax per jurisdiction rules
2. **Low Latency**: Tax calculation <500ms end-to-end
3. **Provider Reliability**: >99% provider success rate
4. **Event Integration**: >99.5% event publishing success rate

### Secondary Goals
1. **Multi-Currency**: Support USD, EUR, and other currencies
2. **Audit Trail**: Full calculation history per order
3. **Provider Flexibility**: Easy addition of new tax providers

---

## Epics and User Stories

### Epic 1: Tax Calculation

**Objective**: Compute accurate tax for items and addresses

#### E1-US1: Calculate Tax for Items
**As a** checkout flow
**I want to** calculate tax for a set of items and address
**So that** the customer sees accurate tax amounts

**Acceptance Criteria**:
- AC1: `POST /api/v1/tax/calculate` accepts items and address
- AC2: Requires non-empty `items` list (400 if missing)
- AC3: Requires non-empty `address` dict (400 if missing)
- AC4: Currency defaults to "USD"
- AC5: Returns total_tax and per-line breakdown
- AC6: Response time <500ms

**API Reference**: `POST /api/v1/tax/calculate`

**Example Request**:
```json
{
  "items": [
    {"sku_id": "sku_widget_01", "quantity": 2, "unit_price": 29.99, "amount": 59.98}
  ],
  "address": {
    "state": "CA",
    "country": "US",
    "zip": "94105"
  },
  "currency": "USD"
}
```

**Example Response** (preview):
```json
{
  "total_tax": 5.40,
  "lines": [
    {
      "line_item_id": "line_0",
      "sku_id": "sku_widget_01",
      "tax_amount": 5.40,
      "rate": 0.09,
      "jurisdiction": "CA",
      "tax_type": "sales"
    }
  ]
}
```

#### E1-US2: Persist Tax Calculation for Order
**As a** Order Service
**I want to** calculate and store tax for a finalized order
**So that** tax amounts are recorded for billing and compliance

**Acceptance Criteria**:
- AC1: When `order_id` is provided, calculation is persisted
- AC2: Response includes `calculation_id` and `order_id`
- AC3: `tax.calculated` event is published
- AC4: Subtotal is computed from items
- AC5: Full tax lines stored with jurisdiction details

**Example Response** (persistent):
```json
{
  "total_tax": 5.40,
  "lines": [...],
  "calculation_id": "calc_abc123",
  "order_id": "ord_xyz789"
}
```

#### E1-US3: Retrieve Tax Calculation
**As a** Billing Service
**I want to** look up tax for an order
**So that** I can include tax on the invoice

**Acceptance Criteria**:
- AC1: `GET /api/v1/tax/calculations/{order_id}` returns stored calculation
- AC2: Includes all tax lines, amounts, and metadata
- AC3: Returns 404 if no calculation exists
- AC4: Response time <50ms

**API Reference**: `GET /api/v1/tax/calculations/{order_id}`

---

### Epic 2: Event-Driven Tax Automation

**Objective**: Auto-calculate tax when inventory is reserved

#### E2-US1: Auto-Calculate on Inventory Reserved
**As a** system
**I want to** automatically calculate tax when inventory is reserved
**So that** tax is ready before payment processing

**Acceptance Criteria**:
- AC1: Subscribes to `inventory.reserved` events
- AC2: Extracts items and shipping address from event
- AC3: Calls calculate_tax with order_id for persistence
- AC4: Publishes `tax.calculated` on success

---

## API Surface

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/tax/calculate` | Calculate tax | JWT |
| GET | `/api/v1/tax/calculations/{order_id}` | Get calculation | JWT |
| GET | `/health` | Health check | None |
| GET | `/api/v1/tax/health` | Service health check | None |

---

## Functional Requirements

| ID | Requirement |
|----|------------|
| FR-001 | System SHALL calculate tax given items and address |
| FR-002 | System SHALL validate items and address are non-empty |
| FR-003 | System SHALL support preview mode (no order_id, no persistence) |
| FR-004 | System SHALL persist calculations when order_id is provided |
| FR-005 | System SHALL publish `tax.calculated` event on persistent calculations |
| FR-006 | System SHALL compute subtotal from item amounts or unit_price * quantity |
| FR-007 | System SHALL support pluggable tax providers |
| FR-008 | System SHALL return per-line tax breakdown with jurisdiction |

## Non-Functional Requirements

| ID | Requirement |
|----|------------|
| NFR-001 | Tax calculation SHALL complete in <500ms (p95) |
| NFR-002 | Retrieval SHALL complete in <50ms (p95) |
| NFR-003 | Service SHALL be available 99.9% of the time |
| NFR-004 | Event publishing SHALL be best-effort (non-blocking) |
| NFR-005 | Service SHALL handle 500+ concurrent calculations |
| NFR-006 | Database queries SHALL use parameterized statements |
| NFR-007 | Service SHALL register with Consul for discovery |

---

## Success Criteria

| Phase | Criteria | Status |
|-------|---------|--------|
| MVP | Calculate tax with mock provider | Complete |
| MVP | Preview and persistent modes | Complete |
| MVP | Event publishing on calculation | Complete |
| V1.1 | Multi-jurisdiction rules (US states) | Planned |
| V1.1 | Avalara provider integration | Planned |
| V1.2 | Tax exemption certificates | Planned |

---

## Out of Scope
- Tax filing and reporting — finance/compliance service
- Tax exemption management — separate service
- Historical rate lookups — tax provider responsibility
- Refund tax recalculation — billing service

---

## Dependencies

| Dependency | Type | Required |
|-----------|------|----------|
| PostgreSQL | Infrastructure | Yes |
| NATS | Infrastructure | No (graceful degradation) |
| Consul | Infrastructure | No (graceful degradation) |
| Tax Provider | Internal | Yes (mock provider as fallback) |
| Inventory Service | Event source | Yes (triggers calculation) |
