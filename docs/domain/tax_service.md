# Tax Service - Domain Context

## Overview

The Tax Service provides **tax calculation and compliance** for the isA_user commerce platform. It computes tax amounts for orders based on items, shipping addresses, and jurisdictions, supporting both preview (ephemeral) and persistent calculations.

**Business Context**: Accurate tax calculation is a legal requirement for commerce. The Tax Service abstracts jurisdiction-specific tax rules behind a provider interface, enabling pluggable tax engines (internal calculator, Avalara, etc.) while maintaining a consistent API.

**Core Value Proposition**: Compute accurate, jurisdiction-aware tax amounts in real-time during checkout, with optional persistence for audit and billing integration.

---

## Business Taxonomy

### Core Entities

#### 1. Tax Calculation
**Definition**: A computed tax result for a set of items and a shipping address.

**Business Purpose**:
- Calculate total tax for an order
- Break down tax by line item and jurisdiction
- Support preview mode (no persistence) and committed mode (stored)
- Provide audit trail for tax compliance

**Key Attributes**:
- Calculation ID (unique, prefix `calc_`)
- Order ID (reference to the order, optional for previews)
- User ID (customer reference)
- Subtotal (pre-tax total of items)
- Total Tax (computed tax amount)
- Currency (default: USD)
- Tax Lines (per-item breakdown)
- Shipping Address (jurisdiction determination)
- Created At, Updated At
- Metadata (flexible attributes)

#### 2. Tax Line
**Definition**: Tax breakdown for a single line item in an order.

**Business Purpose**:
- Show per-item tax amounts
- Track jurisdiction and tax type per line
- Enable tax rate transparency for customers
- Support multi-jurisdiction orders

**Key Attributes**:
- Line Item ID (reference to order line)
- SKU ID (product reference, optional)
- Tax Amount (computed tax for this line)
- Tax Rate (percentage applied)
- Jurisdiction (state, country, or region)
- Tax Type (sales, VAT, GST, etc.)

#### 3. Tax Provider
**Definition**: Pluggable tax calculation engine.

**Business Purpose**:
- Abstract tax calculation logic behind a provider interface
- Support multiple tax engines (mock, internal, Avalara)
- Enable provider switching without API changes
- Facilitate testing with mock providers

**Provider Types**:
- **MockTaxProvider**: Flat-rate calculator for testing
- **InternalProvider**: Built-in jurisdiction rules (future)
- **AvalaraProvider**: Third-party tax compliance API (future)

---

## Domain Scenarios

### Scenario 1: Tax Preview During Checkout
**Actor**: Frontend / Cart Service
**Trigger**: Customer views cart with shipping address
**Flow**:
1. Cart UI sends items and address to `POST /api/v1/tax/calculate`
2. No `order_id` is provided (preview mode)
3. Tax provider computes rates based on address jurisdiction
4. Provider returns total_tax and per-line breakdown
5. Result is returned but NOT persisted to database
6. No event is published

**Outcome**: Customer sees estimated tax before placing order

### Scenario 2: Tax Calculation with Persistence
**Actor**: Order Service (via event)
**Trigger**: Inventory is reserved for an order
**Flow**:
1. Inventory Service publishes `inventory.reserved` event
2. Tax Service receives event and calls `calculate_tax()` with order_id
3. Provider computes tax based on items and shipping address
4. Subtotal is computed from item amounts
5. Calculation is persisted to database via repository
6. `tax.calculated` event is published with full breakdown
7. Response includes calculation_id and order_id

**Outcome**: Tax is computed, stored for billing, and downstream services are notified

### Scenario 3: Retrieve Tax Calculation
**Actor**: Billing Service, Customer Support
**Trigger**: Need to look up tax for an order
**Flow**:
1. Caller requests `GET /api/v1/tax/calculations/{order_id}`
2. Repository returns stored calculation for the order
3. Response includes full tax lines, amounts, and metadata
4. Returns 404 if no calculation exists

**Outcome**: Tax details available for invoicing, refunds, or customer inquiries

---

## Domain Events

### Events Published

| Event | Subject | Payload | When |
|-------|---------|---------|------|
| Tax Calculated | `tax.calculated` | order_id, calculation_id, user_id, subtotal, total_tax, currency, tax_lines[], shipping_address | After persistent calculation |
| Tax Failed | `tax.failed` | order_id, user_id, error_code, error_message, items[] | On calculation failure |

### Events Consumed

| Event | Source | Handler Action |
|-------|--------|---------------|
| `inventory.reserved` | Inventory Service | Auto-calculate tax for reserved order |

---

## Core Concepts

### Preview vs Persistent Calculation

| Mode | order_id | Persisted | Event Published | Use Case |
|------|----------|-----------|-----------------|----------|
| Preview | Not provided | No | No | Cart/checkout tax estimate |
| Persistent | Provided | Yes | Yes | Order finalization |

### Subtotal Computation
The service computes subtotal from items using:
- `item.amount` if present, OR
- `item.unit_price * item.quantity` as fallback

### Separation of Concerns
- **Service Layer**: Orchestrates provider call, persistence, and event publishing
- **Provider Layer**: Tax rate calculation logic (pluggable)
- **Repository Layer**: Persistence via PostgreSQL gRPC
- **Event Layer**: Async NATS publishing, best-effort

---

## Business Rules

| Rule | Description |
|------|-------------|
| BR-TAX-001 | `items` and `address` are required for calculation |
| BR-TAX-002 | Currency defaults to "USD" if not provided |
| BR-TAX-003 | Calculations without order_id are preview-only (not stored) |
| BR-TAX-004 | Calculations with order_id are persisted and trigger events |
| BR-TAX-005 | Event publishing is best-effort — failures don't block operations |
| BR-TAX-006 | Zero-price items produce zero tax |
| BR-TAX-007 | Tax-exempt jurisdictions return total_tax = 0 |
| BR-TAX-008 | Provider errors return 500 with error details |

---

## Tax Service in Ecosystem

### Upstream Dependencies
| Service | Interaction | Purpose |
|---------|------------|---------|
| Inventory Service | Event subscription | Triggers tax calculation after reservation |
| Tax Provider | Internal call | Computes jurisdiction-specific tax rates |

### Downstream Consumers
| Service | Interaction | Purpose |
|---------|------------|---------|
| Fulfillment Service | Event publishing | Shipment preparation after tax is calculated |
| Billing Service | Event publishing | Invoice generation with tax amounts |
| Order Service | API query | Retrieve tax details for order summary |

---

## Success Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Calculation latency | <500ms | End-to-end tax calculation time |
| Provider success rate | >99% | Tax provider availability |
| Event publishing success | >99.5% | Best-effort event delivery rate |
| Calculation accuracy | 100% | Correct tax per jurisdiction rules |

---

## Glossary

| Term | Definition |
|------|-----------|
| Tax Calculation | Computed tax result for a set of items and address |
| Tax Line | Per-item tax breakdown with rate and jurisdiction |
| Jurisdiction | Geographic region determining tax rules (state, country) |
| Preview | Ephemeral tax estimate without persistence |
| Persistent Calculation | Stored tax result linked to an order |
| Tax Provider | Pluggable engine computing tax rates |
| Subtotal | Pre-tax total of all items in the calculation |
