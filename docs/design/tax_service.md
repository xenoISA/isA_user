# Tax Service - Design Document

## Design Overview

**Service Name**: tax_service
**Port**: 8253
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2026-03-05

### Design Principles
1. **Provider Abstraction**: Tax calculation logic behind pluggable interface
2. **Preview vs Persistent**: Support ephemeral estimates and stored calculations
3. **Event-Driven**: NATS events for billing integration
4. **Separation of Concerns**: Service orchestrates; provider calculates; repository stores
5. **Fail-Open Events**: Event bus unavailability doesn't block operations

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Cart Service, Order Service, Billing Service)            │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                Tax Service (Port 8253)                       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              FastAPI HTTP Layer (main.py)              │  │
│  │  - Request validation (Pydantic models)               │  │
│  │  - Response formatting                                │  │
│  │  - Error handling & exception handlers                │  │
│  │  - Health checks (/health)                            │  │
│  │  - Lifecycle management (startup/shutdown)            │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │        Service Layer (tax_service.py)                  │  │
│  │  - Tax calculation orchestration                      │  │
│  │  - Preview vs persistent mode logic                   │  │
│  │  - Subtotal computation                               │  │
│  │  - Event publishing coordination                      │  │
│  └────────┬────────────┬─────────────────────────────────┘  │
│           │            │                                     │
│  ┌────────▼────────┐  ┌▼─────────────────────────────────┐  │
│  │  Tax Provider   │  │ Repository (tax_repository.py)   │  │
│  │  (providers/)   │  │  - PostgreSQL gRPC queries       │  │
│  │  - base.py      │  │  - Calculation persistence       │  │
│  │  - mock.py      │  │  - Result parsing                │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │      Event Publishing (events/publishers.py)          │  │
│  │  - NATS event bus integration                         │  │
│  │  - Async non-blocking publishing                      │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐
│  PostgreSQL  │ │    NATS     │ │   Consul   │
│   (gRPC)     │ │  (Events)   │ │ (Discovery)│
│              │ │             │ │            │
│  Schema:     │ │  Stream:    │ │  Service:  │
│  tax         │ │  tax-stream │ │  tax_      │
│              │ │             │ │  service   │
│  Tables:     │ │  Subjects:  │ │            │
│  - calcula-  │ │  tax.>      │ │  Health:   │
│    tions     │ │             │ │  /health   │
└──────────────┘ └─────────────┘ └────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Key Endpoints**:
```python
# Health Checks
GET /health                                    # Basic health check
GET /api/v1/tax/health                         # Service health check

# Tax Operations
POST /api/v1/tax/calculate                     # Calculate tax
GET  /api/v1/tax/calculations/{order_id}       # Get calculation
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global tax_service, repository, event_bus, provider

    # Startup
    # 1. Initialize repository
    repository = TaxRepository(config=config_manager)
    await repository.initialize()

    # 2. Initialize tax provider
    provider = MockTaxProvider()  # Pluggable

    # 3. Initialize NATS event bus
    try:
        event_bus = await get_event_bus("tax_service")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
        event_bus = None

    # 4. Create service with dependencies
    tax_service = TaxService(
        repository=repository,
        event_bus=event_bus,
        provider=provider,
    )

    # 5. Subscribe to events
    if event_bus:
        handler_map = get_event_handlers(tax_service)
        for event_pattern, handler_func in handler_map.items():
            await event_bus.subscribe_to_events(
                pattern=event_pattern, handler=handler_func
            )

    # 6. Consul registration
    if config.consul_enabled:
        consul_registry.register(service_port=8253)

    yield

    # Shutdown
    if consul_registry:
        consul_registry.deregister()
    if event_bus:
        await event_bus.close()
    if repository:
        await repository.close()
```

### 2. Service Layer (tax_service.py)

**Class**: `TaxService`

**Constructor Dependencies**:
```python
class TaxService:
    def __init__(
        self,
        repository: TaxRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        provider=None,
    ):
```

**Public Methods**:
| Method | Input | Output | Side Effects |
|--------|-------|--------|-------------|
| `calculate_tax(items, address, currency, order_id?, user_id)` | Items + address | Tax result dict | DB write (if order_id), event publish |
| `get_calculation(order_id)` | Order ID | Calculation dict or None | DB read |

**Key Logic — Preview vs Persistent**:
```python
async def calculate_tax(self, items, address, currency="USD", order_id=None, user_id="unknown"):
    result = await self.provider.calculate(items=items, address=address, currency=currency)

    if order_id and self.repository:
        # Persistent mode: store and publish event
        subtotal = self._compute_subtotal(items)
        calculation = await self.repository.create_calculation(...)
        await publish_tax_calculated(...)
        result["calculation_id"] = calculation["calculation_id"]
        result["order_id"] = order_id

    return result  # Preview mode: just return provider result
```

### 3. Provider Layer (providers/)

**Base Interface** (`providers/base.py`):
```python
class TaxProviderBase:
    async def calculate(self, items, address, currency) -> Dict[str, Any]:
        """Returns {"total_tax": float, "lines": [...]}"""
        raise NotImplementedError
```

**Mock Provider** (`providers/mock.py`):
- Applies a flat rate for testing
- Returns deterministic results
- No external dependencies

### 4. Repository Layer (tax_repository.py)

**Key Methods**:
| Method | SQL Operation |
|--------|--------------|
| `create_calculation()` | INSERT INTO tax.calculations |
| `get_calculation_by_order()` | SELECT FROM tax.calculations WHERE order_id = $1 |

### 5. Event Layer (events/)

**Publishers** (`events/publishers.py`):
- `publish_tax_calculated()` — after persistent calculation

**Event Models** (`events/models.py`):
- `TaxCalculatedEvent` — order_id, calculation_id, subtotal, total_tax, tax_lines, address
- `TaxFailedEvent` — order_id, error_code, error_message

**Handlers** (`events/handlers.py`):
- Subscribes to `inventory.reserved`
- Auto-calculates tax for reserved orders

**Stream Configuration**:
- Stream: `tax-stream`
- Subjects: `tax.>`
- Max messages: 100,000
- Consumer prefix: `tax`

---

## Data Models

### Pydantic Models (models.py)

```python
class TaxLine(BaseModel):
    line_item_id: str
    tax_amount: Decimal = Field(..., ge=0)
    jurisdiction: Optional[str] = None
    rate: Optional[Decimal] = None

class TaxCalculation(BaseModel):
    calculation_id: str
    order_id: str
    currency: str = "USD"
    total_tax: Decimal = Field(default=Decimal("0"), ge=0)
    lines: List[TaxLine] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

## Database Schema

### Schema: `tax`

**Table: `calculations`**
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PRIMARY KEY |
| calculation_id | VARCHAR(100) | UNIQUE, NOT NULL |
| order_id | VARCHAR(100) | NOT NULL |
| user_id | VARCHAR(100) | |
| subtotal | DECIMAL(12,2) | DEFAULT 0 |
| total_tax | DECIMAL(12,2) | DEFAULT 0 |
| currency | VARCHAR(3) | DEFAULT 'USD' |
| tax_lines | JSONB | DEFAULT '[]' |
| shipping_address | JSONB | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | AUTO-UPDATED |
| metadata | JSONB | DEFAULT '{}' |

**Indexes**:
- `idx_calculations_order` — order_id
- `idx_calculations_user` — user_id
- `idx_calculations_created` — created_at

---

## Dependency Injection

### Protocols (protocols.py)

```python
@runtime_checkable
class TaxRepositoryProtocol(Protocol):
    async def create_calculation(self, order_id, user_id, subtotal, total_tax, currency, tax_lines, shipping_address) -> Dict[str, Any]: ...
    async def get_calculation_by_order(self, order_id) -> Optional[Dict[str, Any]]: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish(self, subject: str, data: Dict[str, Any]) -> None: ...
```

### Factory (factory.py)

```python
def create_tax_service(
    config: ConfigManager,
    event_bus=None,
    provider=None,
) -> TaxService:
    repository = TaxRepository(config=config)
    if provider is None:
        provider = MockTaxProvider()
    return TaxService(
        repository=repository,
        event_bus=event_bus,
        provider=provider,
    )
```

---

## Error Handling

| Condition | Exception | HTTP Status |
|-----------|-----------|-------------|
| Missing items or address | ValueError | 400 |
| Calculation not found | LookupError | 404 |
| Repository unavailable | RuntimeError | 503 |
| Provider error | Exception | 500 |

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | `8253` | Service port |
| `CONSUL_PORT` | `8500` | Consul port |
| `POSTGRES_HOST` | `localhost` | Database host |
| `NATS_URL` | `nats://localhost:4222` | NATS server |
