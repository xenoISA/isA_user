# Tax Service - Design Document

## Overview

The Tax Service is a FastAPI microservice that computes and persists tax calculations for e-commerce orders. It uses a pluggable provider pattern for tax rate computation, PostgreSQL for persistence, NATS JetStream for event-driven integration, and Consul for service discovery.

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐
│Inventory Service│    │  Checkout UI    │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          │ (inventory.reserved) │ (HTTP POST)
          │                      │
          └──────────┬───────────┘
                     │
        ┌────────────┴────────────┐
        │      Tax Service        │
        │  (FastAPI + PostgreSQL) │
        │       Port: 8253        │
        └────────────┬────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───┴───┐    ┌──────┴──────┐   ┌─────┴─────┐
│ NATS  │    │ PostgreSQL  │   │  Consul   │
│(Events)│    │   (tax)     │   │(Registry) │
└───┬───┘    └─────────────┘   └───────────┘
    │
┌───┴──────────────┐
│fulfillment_service│ (subscribes to tax.calculated)
└──────────────────┘
```

### Core Components

#### 1. API Layer (FastAPI)
- **Health**: `/health`, `/api/v1/tax/health`
- **Calculate**: `POST /api/v1/tax/calculate`
- **Retrieve**: `GET /api/v1/tax/calculations/{order_id}`

#### 2. Repository Layer
- **TaxRepository**: Tax calculation CRUD via AsyncPostgresClient
  - `create_calculation()` — persist with auto-generated calculation_id
  - `get_calculation()` — lookup by calculation_id
  - `get_calculation_by_order()` — lookup by order_id (most recent)
  - `list_calculations()` — filtered list with pagination

#### 3. Provider Layer
- **TaxProvider** (ABC): Abstract interface for tax computation
  - `calculate(items, address, currency) → {total_tax, lines}`
- **MockTaxProvider**: Returns zero tax for all items (testing)
- Future: AvalaraTaxProvider, TaxJarProvider

#### 4. Event System
- **Publishers**: `publish_tax_calculated`, `publish_tax_failed`
- **Handlers**: `handle_inventory_reserved` → auto-calculate tax for reserved order

---

## Database Schema

### Schema: tax

#### calculations (Tax Calculation Records)
```sql
CREATE TABLE tax.calculations (
    id SERIAL PRIMARY KEY,
    calculation_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    subtotal DECIMAL(12,2) DEFAULT 0,
    total_tax DECIMAL(12,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    tax_lines JSONB DEFAULT '[]'::jsonb,
    shipping_address JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_calculations_order` | order_id | Fast lookup by order |
| `idx_calculations_user` | user_id | User-level queries |
| `idx_calculations_created` | created_at | Time-range queries |

### tax_lines JSONB Structure
```json
[
    {
        "line_item_id": "li_abc123",
        "sku_id": "sku_001",
        "tax_amount": 4.38,
        "rate": 0.0875,
        "jurisdiction": "CA",
        "tax_type": "sales_tax"
    }
]
```

---

## Event Architecture

### NATS Stream Configuration

```
Stream: tax-stream
Subjects: tax.>
Consumer Prefix: tax
```

### Events Published

| Event Type | Subject | Data Model |
|------------|---------|------------|
| `tax.calculated` | `tax.calculated` | TaxCalculatedEvent |
| `tax.failed` | `tax.failed` | TaxFailedEvent |

### TaxCalculatedEvent
```python
class TaxCalculatedEvent(BaseModel):
    order_id: str
    calculation_id: str
    user_id: str
    subtotal: float
    total_tax: float
    currency: str = "USD"
    tax_lines: List[TaxLineItem]
    shipping_address: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    timestamp: datetime
```

### Events Subscribed

| Pattern | Source | Handler |
|---------|--------|---------|
| `inventory_service.inventory.reserved` | inventory_service | `handle_inventory_reserved` → auto-calculate |

### Handler Flow: inventory.reserved → tax.calculated

```
inventory.reserved event received
  │
  ├─ Extract order_id, user_id, items, shipping_address
  ├─ Convert items to tax calculation format
  ├─ Calculate subtotal from items
  ├─ Call tax provider: calculate(items, address, currency)
  ├─ Persist calculation to database
  ├─ Publish tax.calculated event
  │
  └─ On failure: publish tax.failed event
```

---

## Data Models

### TaxCalculation
```python
class TaxCalculation(BaseModel):
    calculation_id: str
    order_id: str
    currency: str = "USD"
    total_tax: Decimal = Field(default=Decimal("0"), ge=0)
    lines: List[TaxLine] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### TaxLine
```python
class TaxLine(BaseModel):
    line_item_id: str
    tax_amount: Decimal = Field(..., ge=0)
    jurisdiction: Optional[str] = None
    rate: Optional[Decimal] = None
```

---

## Dependency Injection

### Protocol: TaxRepositoryProtocol
Defines interface for: `create_calculation`, `get_calculation`, `get_calculation_by_order`, `list_calculations`.

### Protocol: EventBusProtocol
Defines interface for: `publish_event`.

### Factory: `create_tax_repository(config)`
Creates TaxRepository with PostgreSQL via ConfigManager service discovery.

---

## Service Registration

### Consul Metadata
```json
{
    "service_name": "tax_service",
    "version": "1.0.0",
    "tags": ["tax", "v1"],
    "capabilities": ["tax_calculation"],
    "port": 8253
}
```

---

## Error Handling

| Scenario | HTTP Status | Behavior |
|----------|-------------|----------|
| Missing items or address | 400 | `{"detail": "items and address are required"}` |
| Calculation not found | 404 | `{"detail": "Tax calculation not found"}` |
| Repository unavailable | 503 | `{"detail": "Repository not available"}` |
| Provider error | 500 | Error message from provider |
| Event publishing failure | Logged | Best-effort, does not fail request |

---

## Deployment

| Config | Default | Env Var |
|--------|---------|---------|
| Port | 8253 | `PORT` |
| PostgreSQL Host | localhost | `POSTGRES_HOST` |
| PostgreSQL Port | 5432 | `POSTGRES_PORT` |
| Consul Enabled | false | `CONSUL_ENABLED` |
| Consul Host | localhost | `CONSUL_HOST` |
| Consul Port | 8500 | `CONSUL_PORT` |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-04
