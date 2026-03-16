# Payment Service - System Contract (Layer 6)

## Overview

This document defines HOW payment_service implements the 12 standard system patterns.

**Service**: payment_service
**Port**: 8207
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/payment_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── payment_service.py               # Business logic layer
├── payment_repository.py            # Data access layer (AsyncPostgresClient)
├── models.py                        # Pydantic models (Payment, Subscription, Invoice, etc.)
├── protocols.py                     # DI interfaces (Protocol classes)
├── factory.py                       # DI factory (create_payment_service)
├── routes_registry.py               # Consul route metadata
├── client.py                        # Service client for external callers
├── blockchain_integration.py        # Blockchain payment router
├── crypto_routes.py                 # Crypto payment routes
├── crypto_service.py                # Crypto payment logic
├── crypto_providers/
│   ├── __init__.py
│   ├── base.py                      # Base crypto provider
│   ├── coinbase_commerce.py         # Coinbase Commerce provider
│   └── models.py                    # Crypto provider models
├── clients/
│   ├── __init__.py
│   ├── account_client.py            # Account service client
│   ├── billing_client.py            # Billing service client
│   ├── product_client.py            # Product service client
│   └── wallet_client.py             # Wallet service client
├── events/
│   ├── __init__.py
│   ├── models.py                    # Event Pydantic models
│   ├── handlers.py                  # NATS event handlers
│   └── publishers.py                # NATS event publishers
└── migrations/
    ├── 001_create_payment_schema.sql
    └── 002_add_order_amount_breakdown.sql
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, request validation, DI wiring | FastAPI, PaymentService |
| **Service** | `payment_service.py` | Business logic, Stripe integration, event orchestration | Repository, EventBus, Clients |
| **Repository** | `payment_repository.py` | Data access, SQL queries | AsyncPostgresClient |
| **Events** | `events/handlers.py` | NATS subscription processing | PaymentService |
| **Events** | `events/publishers.py` | NATS event publishing | Event, EventBus |
| **Models** | `models.py` | Pydantic schemas, enums | pydantic |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | postgres:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| Stripe | HTTP | Payment processing | api.stripe.com |
| Account Service | HTTP | User validation | localhost:8202 |
| Wallet Service | HTTP | Balance operations | localhost:8208 |
| Billing Service | HTTP | Usage records | billing_service |
| Product Service | HTTP | Product pricing | localhost:8215 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class PaymentRepositoryProtocol(Protocol):
    async def check_connection(self) -> bool: ...
    async def create_subscription_plan(self, plan: SubscriptionPlan) -> Optional[SubscriptionPlan]: ...
    async def get_subscription_plan(self, plan_id: str) -> Optional[SubscriptionPlan]: ...
    async def create_subscription(self, subscription: Subscription) -> Optional[Subscription]: ...
    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]: ...
    async def create_payment(self, payment: Payment) -> Optional[Payment]: ...
    async def update_payment_status(self, payment_id: str, status: PaymentStatus, ...) -> Optional[Payment]: ...
    async def create_invoice(self, invoice: Invoice) -> Optional[Invoice]: ...
    async def create_refund(self, refund: Refund) -> Optional[Refund]: ...
    async def get_revenue_statistics(self, days: int = 30) -> Dict[str, Any]: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...

class AccountClientProtocol(Protocol):
    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]: ...

class WalletClientProtocol(Protocol):
    async def get_balance(self, user_id: str, wallet_type: str = "main") -> Optional[Dict[str, Any]]: ...
    async def add_funds(self, user_id: str, wallet_type: str, amount: float, ...) -> Dict[str, Any]: ...

class BillingClientProtocol(Protocol):
    async def record_usage(self, user_id: str, product_id: str, ...) -> Dict[str, Any]: ...

class ProductClientProtocol(Protocol):
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]: ...
```

### Custom Exceptions

| Exception | Description |
|-----------|-------------|
| PaymentServiceError | Base exception |
| PaymentNotFoundError | Payment not found |
| PaymentFailedError | Payment processing failed (with error_code, payment_id) |
| SubscriptionNotFoundError | Subscription not found |
| SubscriptionPlanNotFoundError | Plan not found |
| InvoiceNotFoundError | Invoice not found |
| InvoiceNotOpenError | Invoice not in open state |
| RefundNotFoundError | Refund not found |
| RefundNotEligibleError | Payment not eligible for refund |
| RefundAmountExceededError | Refund exceeds payment amount |
| UserValidationError | User validation failed |
| StripeIntegrationError | Stripe API error |
| WebhookVerificationError | Webhook signature invalid |

---

## 3. Factory Implementation

```python
def create_payment_service(config=None, event_bus=None, stripe_secret_key=None) -> PaymentService:
    repository = PaymentRepository(config=config)
    from .clients import AccountClient, WalletClient, BillingClient, ProductClient
    return PaymentService(
        repository=repository, stripe_secret_key=stripe_secret_key,
        event_bus=event_bus, account_client=AccountClient(),
        wallet_client=WalletClient(), billing_client=BillingClient(),
        product_client=ProductClient(), config=config,
    )
```

Note: main.py creates the service directly (not using factory) to pass config_manager and Stripe key explicitly.

---

## 4. Singleton Management

Global variable pattern:
```python
payment_service: Optional[PaymentService] = None
```

---

## 5. Service Registration (Consul)

- **Route count**: 37 routes (including crypto and blockchain)
- **Base path**: `/api/v1/payment`
- **Tags**: `["v1", "user-microservice", "payment", "billing"]`
- **Capabilities**: subscription_management, payment_processing, invoice_management, refund_processing, stripe_integration, webhook_handling, usage_tracking, revenue_analytics, crypto_payments, blockchain_integration
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | HealthResponse |
| `/api/v1/payment/health` | No | HealthResponse |
| `/api/v1/payment/info` | No | ServiceInfo with capabilities |
| `/api/v1/payment/stats` | Yes | ServiceStats with revenue/subscription counts |

---

## 7. Event System Contract (NATS)

### Published Events

| Event | Subject | Trigger |
|-------|---------|---------|
| `payment.initiated` | `payment.initiated` | Payment intent created |
| `payment.completed` | `payment.completed` | Payment confirmed |
| `payment.failed` | `payment.failed` | Payment failed |
| `payment.refunded` | `payment.refunded` | Refund processed |
| `subscription.created` | `subscription.created` | New subscription |
| `subscription.canceled` | `subscription.canceled` | Subscription canceled |
| `subscription.updated` | `subscription.updated` | Subscription changed |
| `invoice.created` | `invoice.created` | Invoice generated |
| `invoice.paid` | `invoice.paid` | Invoice paid |

### Subscribed Events

| Pattern | Source | Handler |
|---------|--------|---------|
| `order_service.order.created` | order_service | Auto-create payment intent |
| `wallet_service.wallet.balance_changed` | wallet_service | Retry failed payments |
| `wallet_service.wallet.insufficient_funds` | wallet_service | Pause subscriptions |
| `product_service.subscription.usage_exceeded` | product_service | Generate overage invoice |
| `account_service.user.deleted` | account_service | Cancel subscriptions, anonymize history |
| `account_service.user.upgraded` | account_service | Upgrade subscription tier |

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `PAYMENT_SERVICE_PORT` | HTTP port | 8207 |
| `STRIPE_SECRET_KEY` | Stripe API key | None |
| `COINBASE_COMMERCE_API_KEY` | Coinbase API key | None |

---

## 9. Error Handling Contract

Rate limiting applied:
- Default: 60 req/min
- `/api/v1/payment/payments/intent`: 30 req/min
- `/api/v1/payment/webhooks`: 120 req/min

---

## 10. Logging Contract

```python
logger = setup_service_logger("payment_service", level=config.log_level.upper())
```

---

## 11. Testing Contract

```python
from unittest.mock import AsyncMock
mock_repo = AsyncMock(spec=PaymentRepositoryProtocol)
service = PaymentService(repository=mock_repo, event_bus=AsyncMock())
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize service clients (Account, Wallet, Billing, Product)
3. Initialize event bus
4. Create repository and PaymentService
5. Register event handlers (6 patterns)
6. Consul TTL registration
7. **yield**
8. Graceful shutdown
9. Close all service clients
10. Consul deregistration
11. Event bus close

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/payment_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/payment_service/payment_service.py` | Business logic |
| `microservices/payment_service/payment_repository.py` | Data access |
| `microservices/payment_service/protocols.py` | DI interfaces |
| `microservices/payment_service/factory.py` | DI factory |
| `microservices/payment_service/models.py` | Pydantic schemas |
| `microservices/payment_service/routes_registry.py` | Consul metadata |
| `microservices/payment_service/events/handlers.py` | NATS handlers |
| `microservices/payment_service/events/models.py` | Event schemas |
| `microservices/payment_service/crypto_routes.py` | Crypto payment routes |
| `microservices/payment_service/blockchain_integration.py` | Blockchain routes |
