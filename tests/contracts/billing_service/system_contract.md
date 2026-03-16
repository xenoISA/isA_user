# Billing Service - System Contract (Layer 6)

## Overview

This document defines HOW billing_service implements the 12 standard system patterns.

**Service**: billing_service
**Port**: 8216
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/billing_service/
├── __init__.py
├── main.py                 # FastAPI app, routes, DI setup, lifespan
├── billing_service.py      # Business logic layer
├── billing_repository.py   # Data access layer
├── models.py               # Pydantic models (BillingRecord, BillingQuota, etc.)
├── protocols.py            # DI interfaces (Protocol classes)
├── factory.py              # DI factory (create_billing_service)
├── routes_registry.py      # Consul route metadata
├── client.py               # HTTP client for inter-service calls
├── clients/                # Service client implementations
│   ├── __init__.py
│   ├── product_client.py
│   ├── wallet_client.py
│   └── subscription_client.py
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    ├── publishers.py
    └── subscriber.py
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| product_service | HTTP | Product pricing | via service discovery |
| wallet_service | HTTP | Wallet deduction | via service discovery |
| subscription_service | HTTP | Credit consumption | via service discovery |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class BillingRepositoryProtocol(Protocol):
    async def initialize(self) -> None: ...
    async def close(self) -> None: ...
    async def create_billing_record(self, billing_record: BillingRecord) -> BillingRecord: ...
    async def get_billing_record(self, billing_id: str) -> Optional[BillingRecord]: ...
    async def update_billing_record_status(self, billing_id: str, status: BillingStatus, ...) -> Optional[BillingRecord]: ...
    async def get_user_billing_records(self, user_id: str, ...) -> List[BillingRecord]: ...
    async def create_billing_event(self, billing_event: BillingEvent) -> BillingEvent: ...
    async def get_usage_aggregations(self, ...) -> List[Any]: ...
    async def get_user_quotas(self, user_id: str, ...) -> List[BillingQuota]: ...
    async def list_billing_records(self, ...) -> Tuple[List[BillingRecord], int]: ...

class EventBusProtocol(Protocol): ...
class ProductClientProtocol(Protocol): ...
class WalletClientProtocol(Protocol): ...
class SubscriptionClientProtocol(Protocol): ...
```

### Custom Exceptions

```python
class BillingServiceError(Exception): ...
class ProductPricingNotFoundError(BillingServiceError): ...
class QuotaExceededError(BillingServiceError): ...
class BillingRecordNotFoundError(BillingServiceError): ...
class WalletDeductionFailedError(BillingServiceError): ...
class CreditConsumptionFailedError(BillingServiceError): ...
class InvalidBillingMethodError(BillingServiceError): ...
```

### Factory Implementation (`factory.py`)

```python
def create_billing_service(config=None, event_bus=None) -> BillingService:
    repository = BillingRepository(config=config)
    wallet_client = WalletClient()
    product_client = ProductClient()
    subscription_client = SubscriptionClient()
    return BillingService(
        repository=repository, event_bus=event_bus,
        product_client=product_client, wallet_client=wallet_client,
        subscription_client=subscription_client,
    )
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Subject | Trigger |
|-------|---------|---------|
| `billing.usage_recorded` | `billing.usage_recorded` | Usage recorded and billed |
| `billing.quota_exceeded` | `billing.quota_exceeded` | Quota limit reached |
| `billing.payment_processed` | `billing.payment_processed` | Payment processed |

### Subscribed Events

Event-driven billing subscribes to usage events from other services with durable consumers and configurable delivery policy.

```python
for pattern, handler_func in handler_map.items():
    durable_name = f"billing-{pattern.replace('.', '-').replace('*', 'all')}-consumer"
    await event_bus.subscribe_to_events(
        pattern=pattern, handler=handler_func,
        durable=durable_name, delivery_policy=delivery_policy,
    )
```

---

## 4. Error Handling Pattern

| Exception | HTTP Status |
|-----------|-------------|
| QuotaExceededError | 400 |
| BillingRecordNotFoundError | 404 |
| ValueError | 400/422 |
| BillingServiceError | 500 |
| General Exception | 500 (global handler) |

---

## 5-6. Repository & Client Pattern

Repository uses `initialize()` / `close()` lifecycle. Billing service integrates with product, wallet, and subscription services for pricing lookup, wallet deduction, and credit consumption.

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    "service_name": "billing_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "billing", "usage-tracking"],
    "capabilities": [
        "usage_tracking", "cost_calculation", "billing_processing",
        "quota_management", "billing_analytics", "wallet_deduction",
        "payment_charge", "event_driven_billing"
    ]
}
```

14 routes: health (2), core billing (3), quota (2), query/stats (5), admin (1), info (1).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/health` | No | Basic health check with dependency status |
| `/api/v1/billing/health` | No | API-versioned health check |
| `/api/v1/billing/info` | No | Service information and capabilities |

---

## 9-12. Event System, Configuration, Logging, Deployment

- NATS with durable consumers and configurable delivery policy (`BILLING_CONSUMER_DELIVERY_POLICY`, `BILLING_CONSUMER_SUFFIX`)
- ConfigManager("billing_service") with port 8216
- `setup_service_logger("billing_service")`
- GracefulShutdown with repository `close()` on shutdown

---

## System Contract Checklist

- [x] `protocols.py` defines 6 protocols (Repository, EventBus, Product, Wallet, Subscription clients)
- [x] `factory.py` creates service with all client dependencies
- [x] 7 custom exception types for granular error handling
- [x] Durable NATS consumers for reliable event-driven billing
- [x] Repository lifecycle with `initialize()` and `close()`
- [x] Consul TTL registration with 14 routes and 8 capabilities

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/billing_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/billing_service/billing_service.py` | Business logic |
| `microservices/billing_service/billing_repository.py` | Data access |
| `microservices/billing_service/protocols.py` | DI interfaces |
| `microservices/billing_service/factory.py` | DI factory |
| `microservices/billing_service/routes_registry.py` | Consul metadata |
| `microservices/billing_service/events/` | Event handlers, models, publishers, subscriber |
