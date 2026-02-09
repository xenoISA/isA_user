# Payment Service - Design Document

## Architecture Overview

### Service Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Payment Service                          │
├────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                             │
│  ├─ Route Handlers (plans, subscriptions, payments, etc.)  │
│  ├─ Webhook Handler (Stripe events)                        │
│  ├─ Dependency Injection Setup                             │
│  └─ Lifespan Management (startup/shutdown)                 │
├────────────────────────────────────────────────────────────┤
│  Service Layer (payment_service.py)                        │
│  ├─ Subscription Plan Management                           │
│  ├─ Subscription Lifecycle                                 │
│  ├─ Payment Intent Creation/Confirmation                   │
│  ├─ Invoice Management                                     │
│  ├─ Refund Processing                                      │
│  ├─ Stripe Webhook Handling                                │
│  └─ Event Publishing                                       │
├────────────────────────────────────────────────────────────┤
│  Repository Layer (payment_repository.py)                  │
│  ├─ SubscriptionPlanRepository                             │
│  ├─ SubscriptionRepository                                 │
│  ├─ PaymentRepository                                      │
│  ├─ InvoiceRepository                                      │
│  ├─ RefundRepository                                       │
│  └─ PaymentMethodRepository                                │
├────────────────────────────────────────────────────────────┤
│  Dependency Injection (protocols.py)                       │
│  ├─ PaymentRepositoryProtocol                              │
│  ├─ EventBusProtocol                                       │
│  ├─ AccountClientProtocol                                  │
│  ├─ WalletClientProtocol                                   │
│  ├─ BillingClientProtocol                                  │
│  └─ ProductClientProtocol                                  │
├────────────────────────────────────────────────────────────┤
│  Factory (factory.py)                                      │
│  └─ create_payment_service() - production instantiation    │
└────────────────────────────────────────────────────────────┘

External Dependencies:
- Stripe API (payment processing)
- PostgreSQL via gRPC (data persistence)
- NATS (event publishing/subscribing)
- Account Service (user validation)
- Wallet Service (balance updates)
- Billing Service (billing records)
- Consul (service discovery)
```

### Component Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │   Account   │    │   Wallet    │
│   Apps      │───>│   Service   │    │   Service   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                   │
       │   (REST API)     │ (User Validation) │ (Balance Updates)
       └──────────────────┼───────────────────┘
                          ▼
                   ┌─────────────┐
                   │   Payment   │
                   │   Service   │
                   └──────┬──────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Stripe    │    │ PostgreSQL  │    │    NATS     │
│     API     │    │   (gRPC)    │    │ Event Bus   │
└─────────────┘    └─────────────┘    └─────────────┘
                                             │
                   ┌─────────────────────────┘
                   ▼
       ┌─────────────┐    ┌─────────────┐
       │  Billing    │    │Notification │
       │   Service   │    │  Service    │
       └─────────────┘    └─────────────┘
```

---

## Component Design

### Service Layer (payment_service.py)

```python
class PaymentService:
    """
    Payment orchestration service.

    Responsibilities:
    - Subscription plan and lifecycle management
    - Payment intent creation and confirmation
    - Invoice generation and payment
    - Refund processing
    - Stripe webhook handling
    - Event publishing for integration
    """

    def __init__(
        self,
        repository: PaymentRepository,
        stripe_secret_key: Optional[str] = None,
        event_bus: Optional[EventBusProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
        wallet_client: Optional[WalletClientProtocol] = None,
        billing_client: Optional[BillingClientProtocol] = None,
        product_client: Optional[ProductClientProtocol] = None,
        config: Optional[ConfigManager] = None,
    ):
        # Stripe initialization
        # Client initialization
        ...

    # Subscription Plan Operations
    async def create_subscription_plan(request: CreatePlanRequest) -> SubscriptionPlan
    async def get_subscription_plan(plan_id: str) -> Optional[SubscriptionPlan]
    async def list_subscription_plans(tier: Optional[SubscriptionTier]) -> List[SubscriptionPlan]

    # Subscription Operations
    async def create_subscription(request: CreateSubscriptionRequest) -> SubscriptionResponse
    async def get_user_subscription(user_id: str) -> Optional[SubscriptionResponse]
    async def update_subscription(subscription_id: str, request: UpdateSubscriptionRequest) -> SubscriptionResponse
    async def cancel_subscription(subscription_id: str, request: CancelSubscriptionRequest) -> Subscription

    # Payment Operations
    async def create_payment_intent(request: CreatePaymentIntentRequest) -> PaymentIntentResponse
    async def confirm_payment(payment_id: str, processor_response: Optional[Dict]) -> Payment
    async def fail_payment(payment_id: str, failure_reason: str, failure_code: Optional[str]) -> Payment
    async def get_payment_history(user_id: str, filters: Dict) -> PaymentHistoryResponse

    # Invoice Operations
    async def create_invoice(user_id: str, subscription_id: Optional[str], amount_due: Decimal, due_date: Optional[datetime], line_items: List[Dict]) -> Invoice
    async def get_invoice(invoice_id: str) -> Optional[InvoiceResponse]
    async def pay_invoice(invoice_id: str, payment_method_id: str) -> Invoice

    # Refund Operations
    async def create_refund(request: CreateRefundRequest) -> Refund
    async def process_refund(refund_id: str, approved_by: Optional[str]) -> Refund

    # Webhook Handling
    async def handle_stripe_webhook(payload: bytes, sig_header: str) -> Dict[str, Any]

    # Statistics
    async def get_revenue_stats(start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]
    async def get_subscription_stats() -> Dict[str, Any]
```

### Repository Layer

#### PaymentRepository

```python
class PaymentRepository:
    """Payment data access layer"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # PostgreSQL gRPC client setup
        ...

    # Connection
    async def check_connection() -> bool

    # Subscription Plans
    async def create_subscription_plan(plan: SubscriptionPlan) -> Optional[SubscriptionPlan]
    async def get_subscription_plan(plan_id: str) -> Optional[SubscriptionPlan]
    async def list_subscription_plans(tier: Optional[SubscriptionTier], is_public: bool) -> List[SubscriptionPlan]

    # Subscriptions
    async def create_subscription(subscription: Subscription) -> Optional[Subscription]
    async def get_subscription(subscription_id: str) -> Optional[Subscription]
    async def get_user_subscription(user_id: str) -> Optional[Subscription]
    async def get_user_active_subscription(user_id: str) -> Optional[Subscription]
    async def update_subscription(subscription_id: str, updates: Dict) -> Optional[Subscription]
    async def cancel_subscription(subscription_id: str, immediate: bool, reason: Optional[str]) -> Optional[Subscription]

    # Payments
    async def create_payment(payment: Payment) -> Optional[Payment]
    async def get_payment(payment_id: str) -> Optional[Payment]
    async def update_payment_status(payment_id: str, status: PaymentStatus, processor_response: Optional[Dict]) -> Optional[Payment]
    async def get_user_payments(user_id: str, limit: int, status: Optional[PaymentStatus]) -> List[Payment]

    # Payment Methods
    async def save_payment_method(method: PaymentMethodInfo) -> Optional[PaymentMethodInfo]
    async def get_user_payment_methods(user_id: str) -> List[PaymentMethodInfo]
    async def get_user_default_payment_method(user_id: str) -> Optional[PaymentMethodInfo]

    # Invoices
    async def create_invoice(invoice: Invoice) -> Optional[Invoice]
    async def get_invoice(invoice_id: str) -> Optional[Invoice]
    async def mark_invoice_paid(invoice_id: str, payment_intent_id: str) -> Optional[Invoice]

    # Refunds
    async def create_refund(refund: Refund) -> Optional[Refund]
    async def update_refund_status(refund_id: str, status: RefundStatus) -> bool
    async def process_refund(refund_id: str, approved_by: Optional[str]) -> Optional[Refund]

    # Statistics
    async def get_revenue_statistics(days: int) -> Dict[str, Any]
    async def get_subscription_statistics() -> Dict[str, Any]
```

### Protocol Interfaces (protocols.py)

```python
@runtime_checkable
class PaymentRepositoryProtocol(Protocol):
    """Interface for payment repository - enables testing with mocks"""

    async def check_connection(self) -> bool: ...
    async def create_subscription_plan(self, plan: SubscriptionPlan) -> Optional[SubscriptionPlan]: ...
    async def get_subscription_plan(self, plan_id: str) -> Optional[SubscriptionPlan]: ...
    async def create_subscription(self, subscription: Subscription) -> Optional[Subscription]: ...
    async def get_user_active_subscription(self, user_id: str) -> Optional[Subscription]: ...
    async def create_payment(self, payment: Payment) -> Optional[Payment]: ...
    async def get_payment(self, payment_id: str) -> Optional[Payment]: ...
    async def update_payment_status(self, payment_id: str, status: PaymentStatus, processor_response: Optional[Dict]) -> Optional[Payment]: ...
    async def create_invoice(self, invoice: Invoice) -> Optional[Invoice]: ...
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]: ...
    async def create_refund(self, refund: Refund) -> Optional[Refund]: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for event publishing"""

    async def publish_event(self, event: Any) -> None: ...

@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for account service client"""

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def validate_user(self, user_id: str) -> bool: ...

@runtime_checkable
class WalletClientProtocol(Protocol):
    """Interface for wallet service client"""

    async def get_balance(self, user_id: str, wallet_type: str) -> Optional[Dict[str, Any]]: ...
    async def add_funds(self, user_id: str, wallet_type: str, amount: float, description: str, reference_id: str) -> Dict[str, Any]: ...
    async def consume(self, user_id: str, wallet_type: str, amount: float, description: str, reference_id: str) -> Dict[str, Any]: ...
```

---

## Database Schemas

### Schema: payment

#### Table: payment.subscription_plans

```sql
CREATE SCHEMA IF NOT EXISTS payment;

CREATE TABLE IF NOT EXISTS payment.subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    tier VARCHAR(20) NOT NULL,
    price_usd DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    billing_cycle VARCHAR(20) NOT NULL,
    features JSONB DEFAULT '{}',
    credits_included INTEGER DEFAULT 0,
    max_users INTEGER,
    max_storage_gb INTEGER,
    trial_days INTEGER DEFAULT 0,
    stripe_product_id VARCHAR(100),
    stripe_price_id VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_plans_tier ON payment.subscription_plans(tier);
CREATE INDEX idx_plans_is_active ON payment.subscription_plans(is_active);
```

#### Table: payment.subscriptions

```sql
CREATE TABLE IF NOT EXISTS payment.subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    plan_id VARCHAR(50) NOT NULL REFERENCES payment.subscription_plans(plan_id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    tier VARCHAR(20) NOT NULL,
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    billing_cycle VARCHAR(20) NOT NULL,
    trial_start TIMESTAMP WITH TIME ZONE,
    trial_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMP WITH TIME ZONE,
    cancellation_reason TEXT,
    payment_method_id VARCHAR(100),
    last_payment_date TIMESTAMP WITH TIME ZONE,
    next_payment_date TIMESTAMP WITH TIME ZONE,
    stripe_subscription_id VARCHAR(100),
    stripe_customer_id VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscriptions_user_id ON payment.subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON payment.subscriptions(status);
CREATE INDEX idx_subscriptions_stripe_id ON payment.subscriptions(stripe_subscription_id);
CREATE INDEX idx_subscriptions_user_status ON payment.subscriptions(user_id, status);
```

#### Table: payment.transactions

```sql
CREATE TABLE IF NOT EXISTS payment.transactions (
    id SERIAL PRIMARY KEY,
    payment_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_method VARCHAR(20) NOT NULL,
    subscription_id VARCHAR(50),
    invoice_id VARCHAR(50),
    processor VARCHAR(20) DEFAULT 'stripe',
    processor_payment_id VARCHAR(100),
    processor_response JSONB DEFAULT '{}',
    failure_reason TEXT,
    failure_code VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_user_id ON payment.transactions(user_id);
CREATE INDEX idx_transactions_status ON payment.transactions(status);
CREATE INDEX idx_transactions_processor_id ON payment.transactions(processor_payment_id);
CREATE INDEX idx_transactions_created_at ON payment.transactions(created_at DESC);
```

#### Table: payment.invoices

```sql
CREATE TABLE IF NOT EXISTS payment.invoices (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(50) UNIQUE NOT NULL,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    subscription_id VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    amount_total DECIMAL(18,2) NOT NULL,
    amount_paid DECIMAL(18,2) DEFAULT 0,
    amount_due DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    billing_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    billing_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    payment_method_id VARCHAR(100),
    payment_intent_id VARCHAR(100),
    line_items JSONB DEFAULT '[]',
    stripe_invoice_id VARCHAR(100),
    due_date TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoices_user_id ON payment.invoices(user_id);
CREATE INDEX idx_invoices_status ON payment.invoices(status);
CREATE INDEX idx_invoices_due_date ON payment.invoices(due_date);
```

#### Table: payment.refunds

```sql
CREATE TABLE IF NOT EXISTS payment.refunds (
    id SERIAL PRIMARY KEY,
    refund_id VARCHAR(50) UNIQUE NOT NULL,
    payment_id VARCHAR(50) NOT NULL REFERENCES payment.transactions(payment_id),
    user_id VARCHAR(50) NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processor VARCHAR(20) DEFAULT 'stripe',
    processor_refund_id VARCHAR(100),
    processor_response JSONB DEFAULT '{}',
    requested_by VARCHAR(50),
    approved_by VARCHAR(50),
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_refunds_payment_id ON payment.refunds(payment_id);
CREATE INDEX idx_refunds_user_id ON payment.refunds(user_id);
CREATE INDEX idx_refunds_status ON payment.refunds(status);
```

#### Table: payment.payment_methods

```sql
CREATE TABLE IF NOT EXISTS payment.payment_methods (
    id SERIAL PRIMARY KEY,
    method_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    method_type VARCHAR(20) NOT NULL,
    card_brand VARCHAR(20),
    card_last4 VARCHAR(4),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    bank_name VARCHAR(100),
    bank_account_last4 VARCHAR(4),
    external_account_id VARCHAR(100),
    stripe_payment_method_id VARCHAR(100),
    is_default BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_methods_user_id ON payment.payment_methods(user_id);
CREATE INDEX idx_payment_methods_is_default ON payment.payment_methods(user_id, is_default);
```

---

## Data Flow Diagrams

### Subscription Creation Flow

```
Client -> POST /api/v1/payment/subscriptions
  -> RouteHandler (main.py)
    -> PaymentService.create_subscription()
      -> AccountClient.get_account_profile(user_id)
      <- [If not found] Raise ValueError("User does not exist")
      -> PaymentRepository.get_subscription_plan(plan_id)
      <- [If not found] Raise ValueError("Plan not found")
      -> Calculate trial period (if applicable)
      -> [If Stripe configured AND payment_method_id]
        -> stripe.Customer.list/create()
        <- customer.id
        -> stripe.Subscription.create()
        <- stripe_subscription.id
      -> PaymentRepository.create_subscription()
      <- Subscription
      -> EventBus.publish_event(subscription.created)
    <- SubscriptionResponse
  <- HTTP 201 {subscription, plan}
```

### Payment Intent Flow

```
Client -> POST /api/v1/payment/payments/intent
  -> RouteHandler (main.py)
    -> PaymentService.create_payment_intent()
      -> AccountClient.get_account_profile(user_id)
      <- [If not found] Raise ValueError("User does not exist")
      -> [If Stripe configured]
        -> stripe.PaymentIntent.create(
            amount=amount*100,  # cents
            currency=currency,
            automatic_payment_methods={enabled: True}
          )
        <- payment_intent {id, client_secret}
      -> PaymentRepository.create_payment(
          payment_id=payment_intent.id,
          status="pending"
        )
      -> EventBus.publish_event(payment.intent.created)
    <- PaymentIntentResponse {
        payment_intent_id,
        client_secret,
        amount, currency, status
      }
  <- HTTP 200 {payment intent with client_secret}
```

### Payment Confirmation Flow

```
Client -> POST /api/v1/payment/payments/{payment_id}/confirm
  -> RouteHandler (main.py)
    -> PaymentService.confirm_payment(payment_id)
      -> PaymentRepository.get_payment(payment_id)
      <- [If not found] Raise ValueError("Payment not found")
      -> [If Stripe configured]
        -> stripe.PaymentIntent.confirm(
            payment_id,
            payment_method="pm_card_visa"  # Test mode
          )
        <- stripe_intent {status}
      -> PaymentRepository.update_payment_status(
          payment_id,
          status="succeeded",
          paid_at=now()
        )
      <- Payment
      -> EventBus.publish_event(payment.completed)
    <- Payment
  <- HTTP 200 {payment}
```

### Refund Processing Flow

```
Client -> POST /api/v1/payment/refunds
  -> RouteHandler (main.py)
    -> PaymentService.create_refund(request)
      -> PaymentRepository.get_payment(payment_id)
      <- [If not found] Raise ValueError("Payment not found")
      <- [If status != "succeeded"] Raise ValueError("Not eligible")
      -> Validate refund_amount <= payment.amount
      -> [If Stripe configured]
        -> stripe.Refund.create(
            payment_intent=processor_payment_id,
            amount=refund_amount*100,  # cents (if partial)
            reason="requested_by_customer"
          )
        <- stripe_refund {id}
      -> PaymentRepository.create_refund(refund)
      -> PaymentRepository.update_payment_status(
          payment_id,
          status="refunded" | "partial_refund"
        )
      -> EventBus.publish_event(payment.refunded)
    <- Refund
  <- HTTP 200 {refund}
```

### Stripe Webhook Flow

```
Stripe -> POST /api/v1/payment/webhooks/stripe
  -> RouteHandler (main.py)
    -> PaymentService.handle_stripe_webhook(payload, sig_header)
      -> stripe.Webhook.construct_event(
          payload, sig_header, webhook_secret
        )
      <- [If invalid signature] Raise ValueError("Invalid signature")
      <- event {type, data}
      -> [Switch event.type]
        -> "payment_intent.succeeded":
          -> PaymentService.confirm_payment(event.data.id)
          -> EventBus.publish_event(payment.completed)
        -> "payment_intent.payment_failed":
          -> PaymentService.fail_payment(event.data.id, error)
          -> EventBus.publish_event(payment.failed)
        -> "customer.subscription.created":
          -> EventBus.publish_event(subscription.created)
        -> "customer.subscription.deleted":
          -> EventBus.publish_event(subscription.canceled)
        -> "invoice.payment_succeeded":
          -> PaymentRepository.mark_invoice_paid()
    <- {success: True, event: event_type}
  <- HTTP 200
```

---

## Technology Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI (async support)
- **Validation**: Pydantic v2 (models and schemas)
- **Payment Processor**: Stripe (stripe-python)
- **Database**: PostgreSQL (via AsyncPostgresClient/gRPC)
- **Event Bus**: NATS (via core.nats_client)
- **Service Discovery**: Consul (via isa_common.consul_client)
- **HTTP Client**: httpx (async) for internal service calls
- **Configuration**: ConfigManager (core.config_manager)
- **Logging**: Python logging (core.logger)

---

## Security Considerations

### Payment Security (PCI Compliance)
- NO card details stored in payment service
- Card data handled by Stripe.js on frontend
- Only Stripe PaymentIntent IDs stored locally
- Stripe handles PCI DSS compliance
- Webhook signatures verified for authenticity

### Authentication
- JWT token validation at API Gateway level
- X-Internal-Call header for internal service-to-service calls
- Payment Service trusts gateway-authenticated requests
- Webhook requests verified via Stripe signature

### Authorization
- Payment records isolated by user_id
- Only record owner can view their payments
- Admin role required for refund processing (optional)
- 404 returned for both not found and unauthorized

### Input Validation
- Pydantic models validate all request payloads
- Amount must be positive
- Currency must be valid ISO code
- SQL injection prevented by parameterized queries

### Secrets Management
- Stripe secret key via environment variable
- Webhook secret via environment variable
- Never logged or exposed in responses
- Test mode keys use "sk_test_" prefix

### Data Privacy
- Payment records stored encrypted at rest
- User data isolated by user_id
- GDPR: user.deleted event triggers cleanup
- Audit trail maintained for compliance

---

## Event-Driven Architecture

### Published Events

| Event Type | When Published | Payload |
|------------|----------------|---------|
| payment.intent.created | PaymentIntent created | payment_intent_id, user_id, amount, currency, metadata |
| payment.completed | Payment succeeded | payment_intent_id, user_id, amount, currency, payment_id, payment_method, metadata |
| payment.failed | Payment failed | payment_intent_id, user_id, amount, currency, error_message, error_code |
| payment.refunded | Refund processed | refund_id, payment_id, user_id, amount, currency, reason |
| subscription.created | Subscription created | subscription_id, user_id, plan_id, status, period_start, period_end, trial_end, metadata |
| subscription.updated | Subscription modified | subscription_id, user_id, plan_id, old_plan_id, status, metadata |
| subscription.canceled | Subscription canceled | subscription_id, user_id, canceled_at, plan_id, reason, metadata |
| invoice.created | Invoice generated | invoice_id, user_id, subscription_id, amount_due, due_date |
| invoice.paid | Invoice paid | invoice_id, user_id, amount_paid, payment_intent_id |

### Subscribed Events

| Event Pattern | Source | Handler Action |
|---------------|--------|----------------|
| order.created | order_service | Create payment intent for order |
| wallet.balance_changed | wallet_service | Log balance change for reconciliation |
| wallet.insufficient_funds | wallet_service | Log insufficient funds event |
| subscription.usage_exceeded | subscription_service | May trigger overage billing |
| user.deleted | account_service | Cancel subscriptions, archive payment data |
| user.upgraded | account_service | Update subscription tier if applicable |

### Event Model Examples

```python
# payment.completed
{
    "event_type": "payment.completed",
    "source": "payment_service",
    "data": {
        "payment_intent_id": "pi_abc123",
        "user_id": "user_12345",
        "amount": 29.99,
        "currency": "USD",
        "payment_id": "pi_abc123",
        "payment_method": "credit_card",
        "metadata": {},
        "timestamp": "2025-12-16T10:30:00Z"
    }
}

# subscription.created
{
    "event_type": "subscription.created",
    "source": "payment_service",
    "data": {
        "subscription_id": "sub_xyz789",
        "user_id": "user_12345",
        "plan_id": "plan_pro_monthly",
        "status": "trialing",
        "current_period_start": "2025-12-16T00:00:00Z",
        "current_period_end": "2025-12-30T00:00:00Z",
        "trial_end": "2025-12-30T00:00:00Z",
        "metadata": {},
        "timestamp": "2025-12-16T10:30:00Z"
    }
}
```

---

## Error Handling

### Exception Hierarchy

```python
class PaymentServiceError(Exception):
    """Base exception for payment service errors"""
    # Maps to HTTP 500

class PaymentNotFoundError(PaymentServiceError):
    """Payment not found"""
    # Maps to HTTP 404

class PaymentFailedError(PaymentServiceError):
    """Payment processing failed"""
    # Maps to HTTP 400

class SubscriptionNotFoundError(PaymentServiceError):
    """Subscription not found"""
    # Maps to HTTP 404

class SubscriptionPlanNotFoundError(PaymentServiceError):
    """Subscription plan not found"""
    # Maps to HTTP 404

class InvoiceNotFoundError(PaymentServiceError):
    """Invoice not found"""
    # Maps to HTTP 404

class InvoiceNotOpenError(PaymentServiceError):
    """Invoice not open for payment"""
    # Maps to HTTP 400

class RefundNotEligibleError(PaymentServiceError):
    """Payment not eligible for refund"""
    # Maps to HTTP 400

class RefundAmountExceededError(PaymentServiceError):
    """Refund amount exceeds payment amount"""
    # Maps to HTTP 400

class UserValidationError(PaymentServiceError):
    """User validation failed"""
    # Maps to HTTP 400

class StripeIntegrationError(PaymentServiceError):
    """Stripe API error"""
    # Maps to HTTP 500

class WebhookVerificationError(PaymentServiceError):
    """Webhook signature verification failed"""
    # Maps to HTTP 400
```

### HTTP Error Mapping

| Exception | HTTP Code | Response |
|-----------|-----------|----------|
| UserValidationError | 400 | `{"detail": "User does not exist"}` |
| PaymentFailedError | 400 | `{"detail": "Payment failed", "error_code": "card_declined"}` |
| RefundNotEligibleError | 400 | `{"detail": "Payment not eligible for refund", "payment_status": "pending"}` |
| RefundAmountExceededError | 400 | `{"detail": "Refund amount exceeds payment", "payment_amount": 29.99, "requested": 50.00}` |
| PaymentNotFoundError | 404 | `{"detail": "Payment not found: {id}"}` |
| SubscriptionNotFoundError | 404 | `{"detail": "Subscription not found: {id}"}` |
| StripeIntegrationError | 500 | `{"detail": "Stripe error: {message}"}` |

---

## Performance Considerations

### Database Optimization
- Indexes on user_id, payment_id, status, created_at
- Composite index on (user_id, status) for user queries
- Index on processor_payment_id for Stripe lookups
- Pagination enforced to limit result sets

### Stripe API
- Connection pooling via stripe-python
- Retry logic with exponential backoff
- Timeout configuration (10 seconds)
- Error handling for rate limits

### Caching Strategy
- Subscription plan details: Cache for 15 minutes
- User subscription status: Cache for 5 minutes
- Statistics: Cache aggregate results for 60 seconds

### Connection Pooling
- AsyncPostgresClient manages connection pool
- Pool size configured via environment variables
- Connections reused across requests
- Graceful degradation on pool exhaustion

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=payment_service
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8207
LOG_LEVEL=INFO
DEBUG=false

# Database
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061

# NATS Event Bus
NATS_URL=nats://nats:4222

# Consul
CONSUL_ENABLED=true
CONSUL_HOST=consul
CONSUL_PORT=8500

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_xxx  # Use sk_live_ for production
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Service Clients
ACCOUNT_SERVICE_URL=http://account_service:8201
WALLET_SERVICE_URL=http://wallet_service:8210
BILLING_SERVICE_URL=http://billing_service:8216
PRODUCT_SERVICE_URL=http://product_service:8212
```

### Health Checks

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8207
  initialDelaySeconds: 10
  periodSeconds: 30

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8207
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Service Registration (Consul)

```json
{
  "service_name": "payment_service",
  "version": "1.0.0",
  "tags": ["v1", "payment", "subscription", "stripe"],
  "capabilities": [
    "subscription_management",
    "payment_processing",
    "invoice_generation",
    "refund_processing",
    "stripe_integration",
    "event_driven"
  ],
  "health_check": {
    "type": "http",
    "path": "/health",
    "interval": "30s"
  }
}
```

### Resource Requirements

```yaml
resources:
  requests:
    cpu: 200m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

---

## Testing Strategy

### Unit Tests (Layer 1)
- Test Pydantic model validation
- Test data factory generators
- Test enum values and conversions
- No I/O, no mocks needed

### Component Tests (Layer 2)
- Test PaymentService with mocked repositories
- Verify subscription creation logic
- Verify payment flow logic
- Verify refund eligibility checks
- Verify event publishing calls

### Integration Tests (Layer 3)
- Test with real PostgreSQL
- Test full payment lifecycle
- Test Stripe test mode integration
- Use X-Internal-Call header

### API Tests (Layer 4)
- Test HTTP endpoints
- Validate response contracts
- Test error handling
- Test pagination

### Smoke Tests (Layer 5)
- End-to-end bash scripts
- Test happy path subscription
- Test payment intent creation
- Quick production validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Payment Service Team
