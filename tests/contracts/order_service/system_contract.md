# Order Service - System Contract (Layer 6)

## Overview

This document defines HOW order_service implements the 12 standard system patterns.

**Service**: order_service
**Port**: 8210
**Category**: User Microservice (E-Commerce)
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/order_service/
├── __init__.py
├── main.py                 # FastAPI app, routes, DI setup, lifespan
├── order_service.py        # Business logic layer
├── order_repository.py     # Data access layer
├── models.py               # Pydantic models (Order, OrderStatus, etc.)
├── protocols.py            # DI interfaces (Protocol classes)
├── factory.py              # DI factory (create_order_service)
├── routes_registry.py      # Consul route metadata
├── clients/                # Service client implementations
│   ├── __init__.py
│   ├── payment_client.py
│   ├── wallet_client.py
│   ├── account_client.py
│   ├── storage_client.py
│   ├── billing_client.py
│   ├── inventory_client.py
│   ├── tax_client.py
│   └── fulfillment_client.py
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    └── publishers.py
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| payment_service | HTTP | Payment processing | localhost:8207 |
| wallet_service | HTTP | Wallet/credit operations | localhost:8209 |
| account_service | HTTP | User validation | localhost:8202 |
| storage_service | HTTP | Digital goods delivery | via service discovery |
| billing_service | HTTP | Invoice generation | localhost:8216 |
| inventory_service | HTTP | Stock management | via service discovery |
| tax_service | HTTP | Tax calculation | via service discovery |
| fulfillment_service | HTTP | Order fulfillment | via service discovery |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class OrderNotFoundError(Exception): ...
class OrderValidationError(Exception): ...
class OrderServiceError(Exception): ...
class DuplicateOrderError(Exception): ...
class PaymentRequiredError(Exception): ...
class InvalidOrderStateError(Exception): ...

@runtime_checkable
class OrderRepositoryProtocol(Protocol):
    async def create_order(self, user_id: str, order_type: OrderType, total_amount: Decimal, ...) -> Order: ...
    async def get_order(self, order_id: str) -> Optional[Order]: ...
    async def update_order(self, order_id: str, ...) -> Optional[Order]: ...
    async def list_orders(self, limit: int = 50, offset: int = 0, ...) -> List[Order]: ...
    async def get_user_orders(self, user_id: str, ...) -> List[Order]: ...
    async def search_orders(self, query: str, ...) -> List[Order]: ...
    async def get_orders_by_payment_intent(self, payment_intent_id: str) -> List[Order]: ...
    async def get_orders_by_subscription(self, subscription_id: str) -> List[Order]: ...
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> bool: ...
    async def complete_order(self, order_id: str, ...) -> bool: ...
    async def get_order_statistics(self) -> Dict[str, Any]: ...

class EventBusProtocol(Protocol): ...
class PaymentClientProtocol(Protocol): ...
class WalletClientProtocol(Protocol): ...
class AccountClientProtocol(Protocol): ...
class BillingClientProtocol(Protocol): ...
class StorageClientProtocol(Protocol): ...
```

### Factory Implementation (`factory.py`)

```python
def create_order_service(config=None, event_bus=None, payment_client=None,
                         wallet_client=None, account_client=None, storage_client=None,
                         billing_client=None, inventory_client=None, tax_client=None,
                         fulfillment_client=None) -> OrderService:
    from .order_repository import OrderRepository
    repository = OrderRepository(config=config)
    return OrderService(
        repository=repository, event_bus=event_bus,
        payment_client=payment_client, wallet_client=wallet_client,
        account_client=account_client, storage_client=storage_client,
        billing_client=billing_client, inventory_client=inventory_client,
        tax_client=tax_client, fulfillment_client=fulfillment_client,
    )
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Trigger |
|-------|---------|
| `order.created` | New order created |
| `order.completed` | Order completed |
| `order.cancelled` | Order cancelled |
| `order.payment_received` | Payment confirmed |

### Subscribed Events

Event handlers registered via `get_event_handlers(order_service)`. Subscribes to payment and fulfillment events.

---

## 4. Error Handling Pattern

```python
@app.exception_handler(OrderValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(OrderNotFoundError)
async def not_found_error_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(OrderServiceError)
async def service_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
```

| Exception | HTTP Status |
|-----------|-------------|
| OrderValidationError | 400 |
| OrderNotFoundError | 404 |
| OrderServiceError | 500 |
| DuplicateOrderError | 409 (implicit) |
| PaymentRequiredError | 402 (implicit) |
| InvalidOrderStateError | 400 (implicit) |

---

## 5-6. Client & Repository Pattern

8 service clients injected via factory: payment, wallet, account, storage, billing, inventory, tax, fulfillment. All clients are initialized in lifespan and closed on shutdown.

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    "service_name": "order_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "order-management", "e-commerce"],
    "capabilities": [
        "order_creation", "order_management", "order_search",
        "order_statistics", "order_cancellation",
        "payment_integration", "subscription_orders"
    ]
}
```

13 routes: health (4), order CRUD (4), search/stats (2), payment/subscription (2), info (1).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/health` | No | Basic health check |
| `/api/v1/orders/health` | No | API-versioned health check |
| `/health/detailed` | No | Detailed health with DB connectivity |
| `/api/v1/order/info` | Yes | Service information |

---

## 9-12. Event System, Configuration, Logging, Deployment

- NATS event bus for order lifecycle events
- ConfigManager("order_service") with port 8210
- `setup_service_logger("order_service")`
- OrderMicroservice class encapsulates service + event_bus lifecycle
- GracefulShutdown with signal handlers
- 8 service clients initialized in lifespan, closed on shutdown

### Startup Order

1. Install signal handlers (GracefulShutdown)
2. Initialize NATS event bus
3. Initialize 8 service clients (payment, wallet, account, storage, billing, inventory, tax, fulfillment)
4. Create order_service via factory
5. Register event handlers
6. Register with Consul (TTL)

### Shutdown Order

1. Initiate graceful shutdown, wait for drain
2. Deregister from Consul
3. Close all service clients
4. Shutdown order microservice (close event bus)

---

## System Contract Checklist

- [x] `protocols.py` defines 6+ protocols (Repository, EventBus, Payment, Wallet, Account, Billing, Storage)
- [x] `factory.py` accepts 8 service client dependencies
- [x] 6 custom exception types for order lifecycle errors
- [x] Exception handlers registered with FastAPI
- [x] Payment and subscription order integration
- [x] OrderMicroservice class pattern
- [x] Consul TTL registration with 13 routes and 7 capabilities
- [x] All 8 service clients closed on shutdown

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/order_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/order_service/order_service.py` | Business logic |
| `microservices/order_service/order_repository.py` | Data access |
| `microservices/order_service/protocols.py` | DI interfaces |
| `microservices/order_service/factory.py` | DI factory |
| `microservices/order_service/routes_registry.py` | Consul metadata |
| `microservices/order_service/events/` | Event handlers, models, publishers |
| `microservices/order_service/clients/` | 8 service clients |
