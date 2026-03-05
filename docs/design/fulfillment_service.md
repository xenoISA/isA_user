# Fulfillment Service - Design Document

## Design Overview

**Service Name**: fulfillment_service
**Port**: 8254
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2026-03-05

### Design Principles
1. **Carrier Abstraction**: Shipping providers behind pluggable interface
2. **Idempotent Operations**: Label creation and cancellation are safe to retry
3. **Event-Driven**: NATS events for cross-service coordination
4. **Separation of Concerns**: Service logic has no I/O or carrier dependencies
5. **Refund Awareness**: Tracks shipping cost refund eligibility on cancellation

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Order Service, Warehouse, Customer Support)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│            Fulfillment Service (Port 8254)                   │
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
│  │      Service Layer (fulfillment_service.py)           │  │
│  │  - Shipment lifecycle (create, label, cancel)         │  │
│  │  - Idempotency checks                                │  │
│  │  - Refund shipping determination                      │  │
│  │  - Event publishing orchestration                     │  │
│  └────────┬────────────┬─────────────────────────────────┘  │
│           │            │                                     │
│  ┌────────▼────────┐  ┌▼─────────────────────────────────┐  │
│  │  Fulfillment    │  │ Repository                       │  │
│  │  Provider       │  │ (fulfillment_repository.py)      │  │
│  │  (providers/)   │  │  - PostgreSQL gRPC queries       │  │
│  │  - base.py      │  │  - Shipment CRUD                 │  │
│  │  - mock.py      │  │  - Label creation                │  │
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
│  fulfillment │ │  fulfill-   │ │  fulfill-  │
│              │ │  ment-stream│ │  ment_svc  │
│  Tables:     │ │             │ │            │
│  - shipments │ │  Subjects:  │ │  Health:   │
│              │ │  fulfill-   │ │  /health   │
│              │ │  ment.>     │ │            │
└──────────────┘ └─────────────┘ └────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Key Endpoints**:
```python
# Health Checks
GET /health                                              # Basic health check
GET /api/v1/fulfillment/health                           # Service health check

# Shipment Operations
POST /api/v1/fulfillment/shipments                       # Create shipment
POST /api/v1/fulfillment/shipments/{id}/label            # Generate label
POST /api/v1/fulfillment/shipments/{id}/cancel           # Cancel shipment
GET  /api/v1/fulfillment/shipments/order/{order_id}      # Get by order
GET  /api/v1/fulfillment/shipments/tracking/{tracking}   # Get by tracking
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global fulfillment_service, repository, event_bus, provider

    # Startup
    # 1. Initialize repository
    repository = FulfillmentRepository(config=config_manager)
    await repository.initialize()

    # 2. Initialize fulfillment provider
    provider = MockFulfillmentProvider()  # Pluggable

    # 3. Initialize NATS event bus
    try:
        event_bus = await get_event_bus("fulfillment_service")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
        event_bus = None

    # 4. Create service with dependencies
    fulfillment_service = FulfillmentService(
        repository=repository,
        event_bus=event_bus,
        provider=provider,
    )

    # 5. Subscribe to events
    if event_bus:
        handler_map = get_event_handlers(fulfillment_service)
        for event_pattern, handler_func in handler_map.items():
            await event_bus.subscribe_to_events(
                pattern=event_pattern, handler=handler_func
            )

    # 6. Consul registration
    if config.consul_enabled:
        consul_registry.register(service_port=8254)

    yield

    # Shutdown
    if consul_registry:
        consul_registry.deregister()
    if event_bus:
        await event_bus.close()
    if repository:
        await repository.close()
```

### 2. Service Layer (fulfillment_service.py)

**Class**: `FulfillmentService`

**Constructor Dependencies**:
```python
class FulfillmentService:
    def __init__(
        self,
        repository: FulfillmentRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        provider=None,
    ):
```

**Public Methods**:
| Method | Input | Output | Side Effects |
|--------|-------|--------|-------------|
| `create_shipment(order_id, items, address, user_id)` | Order + items + address | shipment_id, tracking, status | DB write, provider call, event publish |
| `create_label(shipment_id)` | Shipment ID | tracking, carrier, status | DB update, event publish |
| `cancel_shipment(shipment_id, reason?)` | Shipment ID | status, refund_shipping | DB update, event publish |
| `get_shipment_by_order(order_id)` | Order ID | Shipment dict or None | DB read |
| `get_shipment_by_tracking(tracking_number)` | Tracking number | Shipment dict or None | DB read |

**Idempotency Logic**:
```python
# Label creation — returns existing if already purchased
if shipment["status"] == "label_purchased":
    return {"shipment_id": ..., "tracking_number": ..., "carrier": ..., "status": "label_created"}

# Cancellation — already-failed returns success
if shipment["status"] == "failed":
    return {"shipment_id": ..., "status": "canceled", "message": "Already canceled"}
```

**Refund Shipping Logic**:
```python
# Only refund shipping if label was already purchased
refund_shipping = shipment["status"] == "label_purchased"
```

### 3. Provider Layer (providers/)

**Base Interface** (`providers/base.py`):
```python
class FulfillmentProviderBase:
    async def create_shipment(self, order_id, items, address) -> Dict[str, Any]:
        """Returns {"tracking_number": str, ...}"""
        raise NotImplementedError
```

**Mock Provider** (`providers/mock.py`):
- Returns deterministic tracking numbers
- No external carrier API calls
- Used for testing and development

### 4. Repository Layer (fulfillment_repository.py)

**Key Methods**:
| Method | SQL Operation |
|--------|--------------|
| `create_shipment()` | INSERT INTO fulfillment.shipments |
| `get_shipment()` | SELECT WHERE shipment_id = $1 |
| `get_shipment_by_order()` | SELECT WHERE order_id = $1 |
| `get_shipment_by_tracking()` | SELECT WHERE tracking_number = $1 |
| `create_label()` | UPDATE SET carrier, tracking_number, status = 'label_purchased' |
| `cancel_shipment()` | UPDATE SET status = 'failed', cancellation_reason |

### 5. Event Layer (events/)

**Publishers** (`events/publishers.py`):
- `publish_shipment_prepared()` — after shipment creation
- `publish_label_created()` — after label generation
- `publish_shipment_canceled()` — after cancellation

**Event Models** (`events/models.py`):
- `ShipmentPreparedEvent` — order_id, shipment_id, items, shipping_address
- `LabelCreatedEvent` — order_id, shipment_id, carrier, tracking_number, estimated_delivery
- `ShipmentCanceledEvent` — order_id, shipment_id, reason, refund_shipping
- `ShipmentFailedEvent` — order_id, error_code, error_message

**Handlers** (`events/handlers.py`):
- Subscribes to `tax.calculated`, `payment.completed`, `order.canceled`
- Routes to service methods for automated operations

**Stream Configuration**:
- Stream: `fulfillment-stream`
- Subjects: `fulfillment.>`
- Max messages: 100,000
- Consumer prefix: `fulfillment`

---

## Data Models

### Pydantic Models (models.py)

```python
class ShipmentStatus(str, Enum):
    CREATED = "created"
    LABEL_PURCHASED = "label_purchased"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"

class Parcel(BaseModel):
    weight_grams: int = Field(..., gt=0)
    dimensions_cm: Dict[str, Any]

class Shipment(BaseModel):
    shipment_id: str
    order_id: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: ShipmentStatus = ShipmentStatus.CREATED
    label_url: Optional[str] = None
    parcels: List[Parcel] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

## Database Schema

### Schema: `fulfillment`

**Table: `shipments`**
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PRIMARY KEY |
| shipment_id | VARCHAR(100) | UNIQUE, NOT NULL |
| order_id | VARCHAR(100) | NOT NULL |
| user_id | VARCHAR(100) | |
| items | JSONB | DEFAULT '[]' |
| shipping_address | JSONB | |
| carrier | VARCHAR(50) | |
| tracking_number | VARCHAR(100) | |
| label_url | TEXT | |
| estimated_delivery | TIMESTAMPTZ | |
| status | VARCHAR(30) | CHECK IN ('created', 'label_purchased', 'in_transit', 'delivered', 'failed') |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | AUTO-UPDATED |
| label_created_at | TIMESTAMPTZ | |
| shipped_at | TIMESTAMPTZ | |
| delivered_at | TIMESTAMPTZ | |
| canceled_at | TIMESTAMPTZ | |
| cancellation_reason | TEXT | |
| metadata | JSONB | DEFAULT '{}' |

**Indexes**:
- `idx_shipments_order` — order_id
- `idx_shipments_user` — user_id
- `idx_shipments_tracking` — tracking_number (partial: WHERE NOT NULL)
- `idx_shipments_status` — status
- `idx_shipments_carrier` — carrier (partial: WHERE NOT NULL)

---

## Dependency Injection

### Protocols (protocols.py)

```python
@runtime_checkable
class FulfillmentRepositoryProtocol(Protocol):
    async def create_shipment(self, order_id, user_id, items, shipping_address, tracking_number, status) -> Dict[str, Any]: ...
    async def get_shipment(self, shipment_id) -> Optional[Dict[str, Any]]: ...
    async def get_shipment_by_order(self, order_id) -> Optional[Dict[str, Any]]: ...
    async def get_shipment_by_tracking(self, tracking_number) -> Optional[Dict[str, Any]]: ...
    async def create_label(self, shipment_id, carrier, tracking_number) -> bool: ...
    async def cancel_shipment(self, shipment_id, reason) -> bool: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish(self, subject: str, data: Dict[str, Any]) -> None: ...
```

### Factory (factory.py)

```python
def create_fulfillment_service(
    config: ConfigManager,
    event_bus=None,
    provider=None,
) -> FulfillmentService:
    repository = FulfillmentRepository(config=config)
    if provider is None:
        provider = MockFulfillmentProvider()
    return FulfillmentService(
        repository=repository,
        event_bus=event_bus,
        provider=provider,
    )
```

---

## Error Handling

| Condition | Exception | HTTP Status |
|-----------|-----------|-------------|
| Missing order_id, items, or address | ValueError | 400 |
| Shipment not found | LookupError | 404 |
| Repository unavailable | RuntimeError | 503 |
| Provider error | Exception | 500 |

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | `8254` | Service port |
| `CONSUL_PORT` | `8500` | Consul port |
| `POSTGRES_HOST` | `localhost` | Database host |
| `NATS_URL` | `nats://localhost:4222` | NATS server |
