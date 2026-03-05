# Inventory Service - Design Document

## Design Overview

**Service Name**: inventory_service
**Port**: 8252
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2026-03-05

### Design Principles
1. **Reservation-Based**: Time-bound holds prevent overselling
2. **Event-Driven**: NATS events for cross-service coordination
3. **Separation of Concerns**: Service logic has no I/O dependencies
4. **Fail-Open Events**: Event bus unavailability doesn't block operations
5. **Idempotent Release**: Releasing non-existent reservations succeeds gracefully

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Order Service, Payment Service, Customer Support)        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              Inventory Service (Port 8252)                   │
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
│  │      Service Layer (inventory_service.py)              │  │
│  │  - Reservation lifecycle (reserve, commit, release)   │  │
│  │  - Event publishing orchestration                     │  │
│  │  - Input validation                                   │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │      Repository Layer (inventory_repository.py)       │  │
│  │  - Database CRUD operations                           │  │
│  │  - PostgreSQL gRPC communication                      │  │
│  │  - Query construction (parameterized)                 │  │
│  │  - Result parsing                                     │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │      Event Publishing (events/publishers.py)          │  │
│  │  - NATS event bus integration                         │  │
│  │  - Event model construction                           │  │
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
│  inventory   │ │  inventory- │ │  inventory │
│              │ │  stream     │ │  _service  │
│  Tables:     │ │             │ │            │
│  - stock_    │ │  Subjects:  │ │  Health:   │
│    levels    │ │  inventory.>│ │  /health   │
│  - reserva-  │ │             │ │            │
│    tions     │ │             │ │            │
└──────────────┘ └─────────────┘ └────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Inventory Service                         │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service    │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)   │    │   (Data)     │   │
│  │             │    │              │    │              │   │
│  │ - Inventory │    │ - Inventory  │    │ - Inventory  │   │
│  │   Item      │    │   Service    │    │   Repository │   │
│  │ - Inventory │    │              │    │              │   │
│  │   Reserve   │    │              │    │              │   │
│  └─────────────┘    └──────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑           │
│         │                  │                    │           │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              FastAPI Main (main.py)                   │  │
│  │  - Dependency Injection (get_inventory_service)      │  │
│  │  - Route Handlers (4 endpoints + health)             │  │
│  │  - Exception Handlers (HTTPException)                │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Event Publishers                         │  │
│  │  (events/publishers.py, events/models.py)            │  │
│  │  - publish_stock_reserved                            │  │
│  │  - publish_stock_committed                           │  │
│  │  - publish_stock_released                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Event Handlers                           │  │
│  │  (events/handlers.py)                                │  │
│  │  - handle order.created → reserve_inventory          │  │
│  │  - handle payment.completed → commit_reservation     │  │
│  │  - handle order.canceled → release_reservation       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (4 endpoints + 2 health checks)
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                         # Basic health check
GET /api/v1/inventory/health                        # Service health check

# Reservation Operations
POST /api/v1/inventory/reserve                      # Reserve stock
POST /api/v1/inventory/commit                       # Commit reservation
POST /api/v1/inventory/release                      # Release reservation
GET  /api/v1/inventory/reservations/{order_id}      # Get reservation
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global inventory_service, repository, event_bus

    # Startup
    # 1. Initialize repository
    repository = InventoryRepository(config=config_manager)
    await repository.initialize()

    # 2. Initialize NATS event bus
    try:
        event_bus = await get_event_bus("inventory_service")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
        event_bus = None

    # 3. Create service with dependencies
    inventory_service = InventoryService(
        repository=repository,
        event_bus=event_bus,
    )

    # 4. Subscribe to events
    if event_bus:
        handler_map = get_event_handlers(inventory_service)
        for event_pattern, handler_func in handler_map.items():
            await event_bus.subscribe_to_events(
                pattern=event_pattern, handler=handler_func
            )

    # 5. Consul registration
    if config.consul_enabled:
        consul_registry.register(service_port=8252)

    yield  # Service runs

    # Shutdown
    if consul_registry:
        consul_registry.deregister()
    if event_bus:
        await event_bus.close()
    if repository:
        await repository.close()
```

### 2. Service Layer (inventory_service.py)

**Class**: `InventoryService`

**Responsibilities**:
- Reservation lifecycle management
- Input validation (order_id, items)
- Event publishing orchestration
- ReservedItem model conversion

**Constructor Dependencies**:
```python
class InventoryService:
    def __init__(
        self,
        repository: InventoryRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ):
```

**Public Methods**:
| Method | Input | Output | Side Effects |
|--------|-------|--------|-------------|
| `reserve_inventory(order_id, items, user_id)` | Order + items | reservation_id, status, expires_at | DB write, event publish |
| `commit_reservation(order_id, reservation_id?)` | Order ID | order_id, reservation_id, status | DB update, event publish |
| `release_reservation(order_id, reservation_id?, reason?)` | Order ID | order_id, reservation_id, status | DB update, event publish |
| `get_reservation(order_id)` | Order ID | Reservation dict or None | DB read |

### 3. Repository Layer (inventory_repository.py)

**Class**: `InventoryRepository`

**Responsibilities**:
- PostgreSQL CRUD operations via gRPC
- Parameterized queries (SQL injection prevention)
- Schema initialization and migration
- Result parsing to Python dicts

**Key Methods**:
| Method | SQL Operation |
|--------|--------------|
| `create_reservation()` | INSERT INTO inventory.reservations |
| `get_reservation()` | SELECT FROM inventory.reservations WHERE reservation_id = $1 |
| `get_reservation_by_order()` | SELECT FROM inventory.reservations WHERE order_id = $1 |
| `get_active_reservation_for_order()` | SELECT WHERE order_id = $1 AND status = 'active' |
| `commit_reservation()` | UPDATE SET status = 'committed' |
| `release_reservation()` | UPDATE SET status = 'released' |

### 4. Event Layer (events/)

**Publishers** (`events/publishers.py`):
- `publish_stock_reserved()` — after reservation creation
- `publish_stock_committed()` — after reservation commit
- `publish_stock_released()` — after reservation release

**Event Models** (`events/models.py`):
- `StockReservedEvent` — order_id, reservation_id, items, expires_at
- `StockCommittedEvent` — order_id, reservation_id, items
- `StockReleasedEvent` — order_id, reservation_id, items, reason
- `StockFailedEvent` — order_id, error_code, error_message

**Handlers** (`events/handlers.py`):
- Subscribes to `order.created`, `payment.completed`, `order.canceled`
- Routes to service methods for automated operations

**Stream Configuration**:
- Stream: `inventory-stream`
- Subjects: `inventory.>`
- Max messages: 100,000
- Consumer prefix: `inventory`

---

## Data Models

### Pydantic Models (models.py)

```python
class InventoryPolicy(str, Enum):
    INFINITE = "infinite"
    FINITE = "finite"

class ReservationStatus(str, Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"

class InventoryItem(BaseModel):
    sku_id: str
    location_id: Optional[str] = None
    inventory_policy: InventoryPolicy = InventoryPolicy.FINITE
    on_hand: int = Field(default=0, ge=0)
    reserved: int = Field(default=0, ge=0)
    available: int = Field(default=0, ge=0)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class InventoryReservation(BaseModel):
    reservation_id: str
    order_id: str
    sku_id: str
    quantity: int = Field(..., gt=0)
    status: ReservationStatus = ReservationStatus.ACTIVE
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

## Database Schema

### Schema: `inventory`

**Table: `stock_levels`**
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PRIMARY KEY |
| sku_id | VARCHAR(100) | NOT NULL, UNIQUE with location_id |
| location_id | VARCHAR(100) | DEFAULT 'default' |
| inventory_policy | VARCHAR(20) | CHECK IN ('finite', 'infinite') |
| on_hand | INTEGER | DEFAULT 0, >= 0 |
| reserved | INTEGER | DEFAULT 0, >= 0 |
| available | INTEGER | GENERATED (on_hand - reserved) |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | AUTO-UPDATED |
| metadata | JSONB | DEFAULT '{}' |

**Table: `reservations`**
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PRIMARY KEY |
| reservation_id | VARCHAR(100) | UNIQUE, NOT NULL |
| order_id | VARCHAR(100) | NOT NULL |
| user_id | VARCHAR(100) | |
| items | JSONB | NOT NULL, DEFAULT '[]' |
| status | VARCHAR(20) | CHECK IN ('active', 'committed', 'released', 'expired') |
| expires_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | AUTO-UPDATED |
| committed_at | TIMESTAMPTZ | |
| released_at | TIMESTAMPTZ | |
| metadata | JSONB | DEFAULT '{}' |

**Indexes**:
- `idx_stock_levels_sku` — sku_id
- `idx_stock_levels_location` — location_id
- `idx_reservations_order` — order_id
- `idx_reservations_user` — user_id
- `idx_reservations_status` — status
- `idx_reservations_expires` — expires_at (partial: WHERE status = 'active')

---

## Dependency Injection

### Protocols (protocols.py)

```python
@runtime_checkable
class InventoryRepositoryProtocol(Protocol):
    async def create_reservation(self, order_id, user_id, items, expires_in_minutes) -> Dict[str, Any]: ...
    async def get_reservation(self, reservation_id) -> Optional[Dict[str, Any]]: ...
    async def get_reservation_by_order(self, order_id) -> Optional[Dict[str, Any]]: ...
    async def get_active_reservation_for_order(self, order_id) -> Optional[Dict[str, Any]]: ...
    async def commit_reservation(self, reservation_id) -> bool: ...
    async def release_reservation(self, reservation_id) -> bool: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish(self, subject: str, data: Dict[str, Any]) -> None: ...
```

### Factory (factory.py)

```python
def create_inventory_service(
    config: ConfigManager,
    event_bus=None,
) -> InventoryService:
    repository = InventoryRepository(config=config)
    return InventoryService(
        repository=repository,
        event_bus=event_bus,
    )
```

---

## Error Handling

| Condition | Exception | HTTP Status |
|-----------|-----------|-------------|
| Missing order_id or items | ValueError | 400 |
| Missing order_id | ValueError | 400 |
| Reservation not found (commit) | LookupError | 404 |
| Repository unavailable | RuntimeError | 503 |
| Internal error | Exception | 500 |

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | `8252` | Service port |
| `CONSUL_PORT` | `8500` | Consul port |
| `POSTGRES_HOST` | `localhost` | Database host |
| `NATS_URL` | `nats://localhost:4222` | NATS server |
