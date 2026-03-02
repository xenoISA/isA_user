# Tax Service Logic Contract

**Business Rules and Specifications for Tax Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for tax service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [Edge Cases](#edge-cases)
3. [Integration Contracts](#integration-contracts)
4. [Error Handling Contracts](#error-handling-contracts)

---

## Business Rules

### Tax Calculation Rules

### BR-TAX-001: Calculate Tax
**Given**: POST /api/v1/tax/calculate request
**When**: Tax is calculated for items and address
**Then**:
- `items` MUST be a non-empty list
- `address` MUST be a non-empty dict
- `currency` defaults to "USD" if not provided
- Tax provider computes `total_tax` and per-item `lines`
- Result includes calculated tax amounts per line item

**Validation Rules**:
- Missing items → 400 Bad Request
- Missing address → 400 Bad Request

---

### BR-TAX-002: Tax Calculation Persistence
**Given**: Tax calculation request with `order_id`
**When**: Tax is calculated with an order_id present
**Then**:
- Calculation is persisted to database via repository
- Response includes `calculation_id` and `order_id`
- `tax.calculated` event is published

**Edge Cases**:
- No order_id → tax still calculated but NOT persisted
- Response only includes `total_tax` and `lines`

---

### BR-TAX-003: Get Calculation by Order
**Given**: GET /api/v1/tax/calculations/{order_id}
**When**: Retrieving a previously computed tax calculation
**Then**:
- Returns the stored calculation for the order
- Includes all tax lines, amounts, and metadata
- Returns 404 if no calculation exists for the order

---

### BR-TAX-004: Tax Provider Interface
**Given**: Tax calculation request
**When**: Provider calculates tax
**Then**:
- Provider receives items list, address dict, and currency
- Provider returns `{"total_tax": float, "lines": [...]}`
- MockTaxProvider applies a flat rate for testing

---

## Edge Cases

### EC-TAX-001: Zero Tax Scenarios
- Items with zero price → total_tax = 0
- Tax-exempt jurisdiction → total_tax = 0

### EC-TAX-002: Repository Unavailable
- If repository is None → 503 Service Unavailable

### EC-TAX-003: Event Bus Unavailable
- Event publishing is best-effort (failures logged, not thrown)

### EC-TAX-004: International Addresses
- Non-US addresses use default tax rate from provider
- Currency parameter affects display but not calculation logic

---

## Integration Contracts

### Event Publishing

| Event | Subject | When |
|-------|---------|------|
| `tax.calculated` | `tax.calculated` | After successful calculation with order_id |
| `tax.failed` | `tax.failed` | On calculation failure |

### Event Subscriptions

| Event | Source | Handler |
|-------|--------|---------|
| `inventory.reserved` | Inventory Service | Auto-calculate tax for reserved order |

### External Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | gRPC | Calculation persistence |
| NATS | Native | Event pub/sub |
| Consul | HTTP | Service registration |
| Tax Provider | Internal | Tax rate calculation |

---

## Error Handling Contracts

| Condition | HTTP Status | Response |
|-----------|-------------|----------|
| Missing items or address | 400 | `{"detail": "items and address are required"}` |
| Calculation not found | 404 | `{"detail": "Tax calculation not found"}` |
| Repository unavailable | 503 | `{"detail": "Repository not available"}` |
| Provider error | 500 | `{"detail": "<error message>"}` |
