# Subscription Service - System Contract (Layer 6)

## Overview

This document defines HOW subscription_service implements the 12 standard system patterns.

**Service**: subscription_service
**Port**: 8228
**Category**: Billing Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/subscription_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── subscription_service.py          # Business logic layer
├── subscription_repository.py       # Data access layer
├── models.py                        # Pydantic models (UserSubscription, etc.)
├── protocols.py                     # DI interfaces
├── factory.py                       # DI factory
├── routes_registry.py               # Consul route metadata
├── client.py                        # Service client
├── clients/
│   ├── __init__.py
│   ├── product_client.py
│   └── wallet_client.py
├── events/
│   ├── __init__.py
│   ├── models.py                    # Rich event type enum (20+ types)
│   ├── handlers.py                  # SubscriptionEventHandlers class
│   └── publishers.py
└── migrations/
    └── 001_create_subscription_schema.sql
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | postgres:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
@runtime_checkable
class SubscriptionRepositoryProtocol(Protocol):
    async def initialize(self) -> None: ...
    async def close(self) -> None: ...
    async def create_subscription(self, subscription: UserSubscription) -> Optional[UserSubscription]: ...
    async def get_subscription(self, subscription_id: str) -> Optional[UserSubscription]: ...
    async def get_user_subscription(self, user_id: str, organization_id=None, active_only=True) -> Optional[UserSubscription]: ...
    async def get_subscriptions(self, user_id=None, organization_id=None, status=None, tier_code=None, limit=50, offset=0) -> List[UserSubscription]: ...
    async def update_subscription(self, subscription_id: str, update_data: Dict) -> Optional[UserSubscription]: ...
    async def consume_credits(self, subscription_id: str, credits: int) -> bool: ...
    async def allocate_credits(self, subscription_id: str, credits: int, rollover=0) -> bool: ...
    async def add_history(self, history: SubscriptionHistory) -> Optional[SubscriptionHistory]: ...
    async def get_subscription_history(self, subscription_id: str, limit=50, offset=0) -> List[SubscriptionHistory]: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...
```

### Custom Exceptions

| Exception | HTTP Status |
|-----------|-------------|
| SubscriptionServiceError | 500 |
| SubscriptionNotFoundError | 404 |
| SubscriptionValidationError | 400/403 |
| InsufficientCreditsError | 402 |
| TierNotFoundError | 404 |

---

## 3. Factory Implementation

```python
def create_subscription_service(config=None, event_bus=None) -> SubscriptionService:
    from .subscription_repository import SubscriptionRepository
    repository = SubscriptionRepository(config=config)
    return SubscriptionService(repository=repository, event_bus=event_bus)
```

---

## 4. Singleton Management

Uses `SubscriptionMicroservice` class pattern:
```python
class SubscriptionMicroservice:
    def __init__(self):
        self.subscription_service = None
        self.event_bus = None
        self.consul_registry = None
subscription_microservice = SubscriptionMicroservice()
```

Service requires `await self.subscription_service.initialize()` after creation.

---

## 5. Service Registration (Consul)

- **Route count**: 11 routes
- **Base path**: `/api/v1/subscriptions`
- **Tags**: `["v1", "subscription", "credits", "billing", "microservice"]`
- **Capabilities**: subscription_management, credit_allocation, credit_consumption, subscription_history, tier_management
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | `{status, service, port, version, timestamp}` |
| `/api/v1/subscriptions/health` | No | Same |
| `/health/detailed` | No | HealthResponse with database_connected |

---

## 7. Event System Contract (NATS)

### Published Events (20+ types)

| Category | Events |
|----------|--------|
| Lifecycle | subscription.created, updated, canceled, paused, resumed, renewed, expired |
| Tier | subscription.upgraded, subscription.downgraded |
| Trial | subscription.trial.started, trial.ending_soon, trial.ended |
| Credits | subscription.credits.allocated, consumed, low, depleted, rolled_over |
| Payment | subscription.payment.succeeded, failed, refunded |

### Subscribed Events

| Pattern | Source | Handler |
|---------|--------|---------|
| `billing.credits.consume` | billing_service | Consume credits from subscription |
| `payment.succeeded` | payment_service | Handle successful payment |
| `payment.failed` | payment_service | Handle failed payment |
| `account.created` | account_service | Auto-create free subscription |

Event handler uses class-based pattern (`SubscriptionEventHandlers` with `get_event_handler_map()`).

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `SUBSCRIPTION_SERVICE_PORT` | HTTP port | 8228 |

---

## 9. Error Handling Contract

Exception handlers registered at app level:
```python
@app.exception_handler(SubscriptionValidationError) -> 400
@app.exception_handler(SubscriptionNotFoundError) -> 404
@app.exception_handler(InsufficientCreditsError) -> 402
@app.exception_handler(SubscriptionServiceError) -> 500
```

---

## 10. Logging Contract

```python
app_logger = setup_service_logger("subscription_service")
```

---

## 11. Testing Contract

```python
mock_repo = AsyncMock(spec=SubscriptionRepositoryProtocol)
service = SubscriptionService(repository=mock_repo, event_bus=AsyncMock())
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize event bus
3. Create SubscriptionMicroservice (factory + `await initialize()`)
4. Subscribe to events (class-based handler map)
5. Consul TTL registration
6. **yield**
7. Graceful shutdown
8. Subscription microservice shutdown

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/subscription_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/subscription_service/subscription_service.py` | Business logic |
| `microservices/subscription_service/subscription_repository.py` | Data access |
| `microservices/subscription_service/protocols.py` | DI interfaces |
| `microservices/subscription_service/factory.py` | DI factory |
| `microservices/subscription_service/models.py` | Pydantic schemas |
| `microservices/subscription_service/routes_registry.py` | Consul metadata |
| `microservices/subscription_service/events/handlers.py` | NATS handlers |
| `microservices/subscription_service/events/models.py` | Event schemas (20+ types) |
