# Tax Service - Domain Context

## Service Overview

The Tax Service calculates tax for e-commerce orders based on shipping addresses and line items. It supports US and EU jurisdictions through a pluggable provider interface, persists calculations for audit and retrieval, and integrates into the commerce pipeline via event-driven triggers from the Inventory Service.

---

## Business Domain Context

### Domain Definition

**Tax Calculation** is the practice of computing applicable taxes for commercial transactions based on item classification, jurisdiction rules, and shipping destination. This includes:

- **Tax Rate Determination**: Jurisdiction-based tax rate lookup (state, county, city, country)
- **Line-Item Breakdown**: Per-item tax calculation with jurisdiction and rate details
- **Persistence**: Storing calculations tied to orders for audit, refund, and compliance
- **Event-Driven Calculation**: Automatic tax computation triggered by inventory reservation

### Bounded Context

The Tax Service operates within the **Commerce Fulfillment** bounded context, bounded by:

| Boundary | Description |
|----------|-------------|
| **Upstream** | inventory_service (triggers tax calculation via `inventory.reserved` events), order_service (provides order and item data) |
| **Downstream** | fulfillment_service (awaits tax calculation before shipment preparation), payment_service (includes tax in total charge) |
| **Lateral** | billing_service (usage tracking), audit_service (tax audit trail) |

### Domain Entities

| Entity | Description | Lifecycle |
|--------|-------------|-----------|
| **TaxCalculation** | Tax computation result for an order | Created on calculation; immutable once stored |
| **TaxLine** | Per-line-item tax breakdown within a calculation | Created with parent calculation; immutable |

---

## Terminology (Ubiquitous Language)

### Core Terms

| Term | Definition | Example |
|------|------------|---------|
| **Tax Calculation** | Complete tax computation for an order | $8.75 tax on $100 order to CA |
| **Tax Line** | Per-item breakdown showing tax amount, rate, and jurisdiction | Item A: $4.38 at 8.75% (CA state) |
| **Jurisdiction** | Tax authority area (state, county, city, country) | "CA" (California), "DE" (Germany) |
| **Tax Rate** | Percentage applied to taxable amount | 8.75% for California sales tax |
| **Subtotal** | Pre-tax total of all items | Sum of (unit_price * quantity) for all items |
| **Total Tax** | Sum of all tax lines | Sum of tax_amount across all TaxLine entries |
| **Tax Provider** | Pluggable backend that computes tax rates | MockTaxProvider (testing), AvalaraTaxProvider (production) |
| **Shipping Address** | Destination address used to determine jurisdiction | `{state: "CA", zip: "94102", country: "US"}` |

### Event Terms

| Event | Meaning |
|-------|---------|
| **tax.calculated** | Tax successfully computed and persisted for an order |
| **tax.failed** | Tax calculation failed (provider error, missing data) |

---

## Business Capabilities

### BR-TAX-001: Calculate Tax

**Capability**: Compute tax for a set of items and a shipping address

**Business Rules**:
- BR-TAX-001.1: Request requires non-empty `items` list and non-empty `address` dict
- BR-TAX-001.2: `currency` defaults to "USD" if not provided
- BR-TAX-001.3: Tax provider computes `total_tax` and per-item `lines`
- BR-TAX-001.4: Missing items → 400 Bad Request
- BR-TAX-001.5: Missing address → 400 Bad Request
- BR-TAX-001.6: Result includes calculated tax amounts per line item

### BR-TAX-002: Tax Calculation Persistence

**Capability**: Store tax calculations tied to orders for audit and retrieval

**Business Rules**:
- BR-TAX-002.1: Calculations with `order_id` are persisted to the database
- BR-TAX-002.2: Each persisted calculation gets a unique `calculation_id` with prefix `tax_`
- BR-TAX-002.3: Response includes `calculation_id` and `order_id` when persisted
- BR-TAX-002.4: `tax.calculated` event is published after persistence
- BR-TAX-002.5: Calculations without `order_id` are computed but NOT persisted (preview mode)

### BR-TAX-003: Retrieve Calculation by Order

**Capability**: Look up a previously computed tax calculation by order ID

**Business Rules**:
- BR-TAX-003.1: Returns the most recent calculation for the given order
- BR-TAX-003.2: Includes all tax lines, amounts, and metadata
- BR-TAX-003.3: Returns 404 if no calculation exists for the order
- BR-TAX-003.4: Returns 503 if repository is unavailable

### BR-TAX-004: Tax Provider Interface

**Capability**: Pluggable provider pattern for tax rate computation

**Business Rules**:
- BR-TAX-004.1: Provider receives items list, address dict, and currency
- BR-TAX-004.2: Provider returns `{"total_tax": float, "lines": [...]}`
- BR-TAX-004.3: MockTaxProvider returns zero tax for all items (testing only)
- BR-TAX-004.4: Production providers implement the `TaxProvider` abstract base class

---

## Domain Events

### Events Published

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `tax.calculated` | `tax.calculated` | Tax successfully computed with order_id | order_id, calculation_id, user_id, subtotal, total_tax, currency, tax_lines, shipping_address |
| `tax.failed` | `tax.failed` | Tax calculation failed | order_id, user_id, error_code, error_message, items |

### Events Subscribed

| Event | Source | Handler |
|-------|--------|---------|
| `inventory.reserved` | inventory_service | Auto-calculate tax for reserved order items |

---

## Integration Points

### Upstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **inventory_service** | Triggers tax calculation via `inventory.reserved` event | NATS subscription | Queue events, retry |

### Downstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **fulfillment_service** | Awaits `tax.calculated` before shipment preparation | Async event publishing | Fulfillment retries independently |
| **payment_service** | Includes tax in total order charge | Async event / sync HTTP | Payment uses last known tax |

### Cross-Cutting Dependencies

| Service | Purpose | Integration Pattern |
|---------|---------|---------------------|
| **PostgreSQL** | Primary data store (schema: `tax`) | AsyncPostgresClient |
| **NATS JetStream** | Event pub/sub | core.nats_client |
| **Consul** | Service registration and discovery | isa_common.ConsulRegistry |

---

## Quality Attributes

| Attribute | Target | Rationale |
|-----------|--------|-----------|
| **Availability** | 99.9% | Tax blocks payment; downtime = stalled orders |
| **Latency (Calculate)** | p99 < 300ms | Must not slow checkout flow |
| **Accuracy** | 100% correct jurisdiction mapping | Tax compliance is legally required |
| **Data Durability** | Zero calculation loss | Audit trail required for compliance |

---

## Future Considerations

1. **Real tax provider integration**: Avalara, TaxJar, or Vertex for production tax rates
2. **Tax exemption certificates**: Support for B2B tax-exempt customers
3. **Multi-currency tax**: Tax calculation in local currency for international orders
4. **Tax refund support**: Partial/full tax refund on order cancellation or return
5. **Nexus management**: Track tax nexus obligations across jurisdictions

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
**Domain Owner**: Commerce Platform Team
