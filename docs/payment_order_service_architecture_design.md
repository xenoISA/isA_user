# Payment & Order Service Architecture Design

## 🎯 Overview

Complete event-driven architecture design for payment_service and order_service, including:
- **Events (Async)**: What events to publish and subscribe
- **Clients (Sync)**: What service dependencies to call
- **Missing Events**: Events that should exist but currently don't

---

## 📊 Payment Service Architecture

### 1️⃣ **Events to PUBLISH (Outbound - Async)**

#### Current Events (Already Publishing):
| Event | Trigger | Data | Subscribers |
|-------|---------|------|-------------|
| `payment.completed` | Stripe webhook success | payment_intent_id, user_id, amount, currency | order_service, wallet_service, billing_service |
| `payment.failed` | Stripe webhook failed | payment_intent_id, user_id, amount, error | order_service, notification_service |
| `subscription.created` | Stripe subscription created | subscription_id, user_id, plan_id, status | product_service, billing_service |
| `subscription.canceled` | Stripe subscription canceled | subscription_id, user_id, reason | product_service, notification_service |

#### Missing Events (Should Add):
| Event | Trigger | Data | Subscribers |
|-------|---------|------|-------------|
| `payment.refunded` | Refund processed | payment_id, refund_id, amount, reason | order_service, wallet_service, notification_service |
| `payment.intent.created` | Payment intent created | payment_intent_id, user_id, amount | billing_service, analytics_service |
| `subscription.updated` | Subscription plan changed | subscription_id, old_plan, new_plan | product_service, billing_service |
| `subscription.expired` | Subscription reached end | subscription_id, user_id, expiration_date | product_service, notification_service |
| `subscription.payment_failed` | Subscription payment retry failed | subscription_id, user_id, attempt_count | notification_service, billing_service |
| `invoice.created` | Invoice generated | invoice_id, user_id, amount, due_date | billing_service, notification_service |
| `invoice.paid` | Invoice payment successful | invoice_id, payment_id, amount | billing_service, accounting_service |
| `invoice.overdue` | Invoice past due date | invoice_id, user_id, days_overdue | notification_service, billing_service |

### 2️⃣ **Events to SUBSCRIBE (Inbound - Async)**

#### Current: No subscriptions (❌ Missing!)

#### Should Subscribe To:
| Event | Source | Handler Action |
|-------|--------|----------------|
| `wallet.balance_changed` | wallet_service | Update payment method preferences, retry failed payments |
| `wallet.insufficient_funds` | wallet_service | Pause subscription, send notification |
| `order.created` | order_service | Create payment intent automatically |
| `subscription.usage_exceeded` | product_service | Generate overage invoice |
| `user.deleted` | account_service | Cancel all subscriptions, refund prorated amount |
| `user.upgraded` | account_service | Update subscription tier automatically |

### 3️⃣ **Service Clients (Sync - HTTP)**

#### Current Clients:
```python
# payment_service.py:32-33
from microservices.account_service.client import AccountServiceClient
from microservices.wallet_service.client import WalletServiceClient
```

#### Should Have:
| Client | Usage | Methods Needed |
|--------|-------|----------------|
| `AccountClient` | Validate user, get profile | `get_user()`, `validate_user()`, `get_payment_methods()` |
| `WalletClient` | Check balance, add credits | `get_wallet()`, `add_credits()`, `deduct_credits()`, `get_balance()` |
| `BillingClient` | Create billing records | `create_billing_record()`, `get_billing_history()` |
| `ProductClient` | Get subscription plans | `get_plan()`, `validate_subscription()` |
| `NotificationClient` | Send payment notifications | `send_payment_receipt()`, `send_invoice()` |

---

## 📊 Order Service Architecture

### 1️⃣ **Events to PUBLISH (Outbound - Async)**

#### Current Events (Already Publishing):
| Event | Trigger | Data | Subscribers |
|-------|---------|------|-------------|
| `order.created` | Order created | order_id, user_id, order_type, total_amount, items | payment_service, inventory_service, notification_service |
| `order.canceled` | Order canceled | order_id, user_id, reason, refund_amount | payment_service, wallet_service, notification_service |
| `order.completed` | Order completed | order_id, user_id, total_amount, payment_id | wallet_service, analytics_service, notification_service |

#### Missing Events (Should Add):
| Event | Trigger | Data | Subscribers |
|-------|---------|------|-------------|
| `order.updated` | Order details changed | order_id, changes, updated_fields | payment_service, notification_service |
| `order.expired` | Order not paid in time | order_id, user_id, expired_at | payment_service, notification_service |
| `order.payment_pending` | Awaiting payment | order_id, payment_intent_id, amount | payment_service, notification_service |
| `order.refunded` | Order refund processed | order_id, refund_id, amount | payment_service, wallet_service, accounting_service |
| `order.fulfilled` | Order items delivered | order_id, fulfillment_details | storage_service, notification_service |

### 2️⃣ **Events to SUBSCRIBE (Inbound - Async)**

#### Current Handlers (in main.py - needs migration):
```python
# main.py:67-100
async def handle_payment_completed(event: Event)  # ✅ Exists
async def handle_payment_failed(event: Event)     # ✅ Exists
```

#### Should Subscribe To:
| Event | Source | Handler Action | Status |
|-------|--------|----------------|--------|
| `payment.completed` | payment_service | Complete order, update status | ✅ Exists (needs migration) |
| `payment.failed` | payment_service | Cancel order, notify user | ✅ Exists (needs migration) |
| `payment.refunded` | payment_service | Update order status to refunded | ❌ Missing |
| `wallet.credits_added` | wallet_service | Auto-fulfill pending wallet orders | ❌ Missing |
| `subscription.created` | product_service | Create recurring order record | ❌ Missing |
| `subscription.canceled` | product_service | Cancel pending subscription orders | ❌ Missing |
| `storage.quota_exceeded` | storage_service | Create upgrade order automatically | ❌ Missing |
| `user.deleted` | account_service | Cancel all pending orders | ❌ Missing |

### 3️⃣ **Service Clients (Sync - HTTP)**

#### Current Clients:
```python
# order_service.py:24-27
from microservices.payment_service.client import PaymentServiceClient
from microservices.wallet_service.client import WalletServiceClient
from microservices.account_service.client import AccountServiceClient
from microservices.storage_service.client import StorageServiceClient
```

#### Should Have:
| Client | Usage | Methods Needed |
|--------|-------|----------------|
| `PaymentClient` | Create payment intents, check status | `create_payment_intent()`, `get_payment_status()`, `cancel_payment()` |
| `WalletClient` | Check balance, deduct/add credits | `get_wallet()`, `deduct_credits()`, `add_credits()`, `get_balance()` |
| `AccountClient` | Validate user, get profile | `get_user()`, `validate_user()`, `get_user_tier()` |
| `StorageClient` | Validate storage orders | `get_storage_usage()`, `validate_quota()` |
| `BillingClient` | Create billing records | `create_order_billing_record()` |
| `NotificationClient` | Send order notifications | `send_order_confirmation()`, `send_order_status()` |

---

## 🔄 Event Flow Diagrams

### Payment Flow:
```
User → order_service.create_order()
    ↓ (publishes)
    order.created event
    ↓ (subscribes)
payment_service.handle_order_created()
    ↓ (sync call)
payment_service.create_payment_intent()
    ↓ (Stripe webhook)
payment_service.handle_stripe_webhook()
    ↓ (publishes)
    payment.completed event
    ↓ (subscribes)
order_service.handle_payment_completed()
    ↓
order_service.complete_order()
    ↓ (publishes)
    order.completed event
    ↓ (subscribes)
wallet_service.handle_order_completed()
```

### Subscription Flow:
```
User → payment_service.create_subscription()
    ↓ (sync call)
AccountClient.validate_user()
    ↓ (Stripe API)
Stripe.create_subscription()
    ↓ (publishes)
    subscription.created event
    ↓ (subscribes)
product_service.handle_subscription_created()
    ↓
product_service.activate_features()
```

### Refund Flow:
```
User → payment_service.create_refund()
    ↓ (Stripe API)
Stripe.create_refund()
    ↓ (publishes)
    payment.refunded event
    ↓ (subscribes)
order_service.handle_payment_refunded()
    ↓
order_service.update_status(REFUNDED)
    ↓ (subscribes)
wallet_service.handle_payment_refunded()
    ↓
wallet_service.add_credits()
```

---

## 🏗️ Implementation Plan

### Phase 1: Payment Service

#### Step 1: Create events/ folder
```
microservices/payment_service/events/
├── __init__.py
├── models.py        # 12+ event models
├── publishers.py    # 8+ publishing functions
└── handlers.py      # 6+ event handlers
```

**Event Models to Create:**
- `PaymentCompletedEvent`
- `PaymentFailedEvent`
- `PaymentRefundedEvent`
- `PaymentIntentCreatedEvent`
- `SubscriptionCreatedEvent`
- `SubscriptionCanceledEvent`
- `SubscriptionUpdatedEvent`
- `SubscriptionExpiredEvent`
- `SubscriptionPaymentFailedEvent`
- `InvoiceCreatedEvent`
- `InvoicePaidEvent`
- `InvoiceOverdueEvent`

**Publishers to Create:**
- `publish_payment_completed()`
- `publish_payment_failed()`
- `publish_payment_refunded()`
- `publish_payment_intent_created()`
- `publish_subscription_created()`
- `publish_subscription_canceled()`
- `publish_subscription_updated()`
- `publish_subscription_expired()`
- `publish_invoice_created()`
- `publish_invoice_paid()`

**Handlers to Create:**
- `handle_wallet_balance_changed()`
- `handle_wallet_insufficient_funds()`
- `handle_order_created()`
- `handle_subscription_usage_exceeded()`
- `handle_user_deleted()`
- `handle_user_upgraded()`

#### Step 2: Create clients/ folder
```
microservices/payment_service/clients/
├── __init__.py
├── account_client.py
├── wallet_client.py
├── billing_client.py
├── product_client.py
└── notification_client.py
```

#### Step 3: Refactor payment_service.py
- Remove direct event publishing (lines 835-850, 863-878, 893-908, 919-933)
- Use `events/publishers.py` instead
- Change client initialization to dependency injection

#### Step 4: Update main.py
- Initialize all service clients
- Register event handlers
- Add cleanup for clients

---

### Phase 2: Order Service

#### Step 1: Create events/ folder
```
microservices/order_service/events/
├── __init__.py
├── models.py        # 8+ event models
├── publishers.py    # 5+ publishing functions
└── handlers.py      # 8+ event handlers (MIGRATE from main.py!)
```

**Event Models to Create:**
- `OrderCreatedEvent`
- `OrderUpdatedEvent`
- `OrderCanceledEvent`
- `OrderCompletedEvent`
- `OrderExpiredEvent`
- `OrderPaymentPendingEvent`
- `OrderRefundedEvent`
- `OrderFulfilledEvent`

**Publishers to Create:**
- `publish_order_created()`
- `publish_order_updated()`
- `publish_order_canceled()`
- `publish_order_completed()`
- `publish_order_expired()`

**Handlers to Create (MIGRATE from main.py:67-108):**
- `handle_payment_completed()` ⚠️ MIGRATE
- `handle_payment_failed()` ⚠️ MIGRATE
- `handle_payment_refunded()` (NEW)
- `handle_wallet_credits_added()` (NEW)
- `handle_subscription_created()` (NEW)
- `handle_subscription_canceled()` (NEW)
- `handle_storage_quota_exceeded()` (NEW)
- `handle_user_deleted()` (NEW)

#### Step 2: Create clients/ folder
```
microservices/order_service/clients/
├── __init__.py
├── payment_client.py
├── wallet_client.py
├── account_client.py
├── storage_client.py
├── billing_client.py
└── notification_client.py
```

#### Step 3: Refactor order_service.py
- Remove direct event publishing (lines 121-138, 244-261, 324-342)
- Use `events/publishers.py` instead
- Change client initialization to dependency injection

#### Step 4: Refactor main.py ⚠️ IMPORTANT
- **REMOVE event handlers** (lines 67-108) - migrate to events/handlers.py
- Initialize all service clients
- Register event handlers from events/handlers.py
- Add cleanup for clients

---

## 🎓 Key Architectural Decisions

### 1. Event vs Client Decision Matrix

| Scenario | Use Event (Async) | Use Client (Sync) |
|----------|-------------------|-------------------|
| Order created | ✅ Notify payment_service | |
| Payment completed | ✅ Notify order_service | |
| Validate user | | ✅ AccountClient.validate_user() |
| Check wallet balance | | ✅ WalletClient.get_balance() |
| Send notification | ✅ Publish event | ❌ Don't block request |
| Update analytics | ✅ Publish event | ❌ Don't block request |
| Create payment intent | | ✅ PaymentClient.create_intent() |

**Rule of Thumb:**
- **Async (Events)**: When you don't need immediate response, or notifying multiple services
- **Sync (Clients)**: When you need validation, data before proceeding, or single service call

### 2. Missing Event Priorities

#### High Priority (P0):
- `payment.refunded` - Critical for order refund flow
- `order.expired` - Prevent stale unpaid orders
- `subscription.payment_failed` - Retry logic
- Event handlers in order_service for wallet/subscription events

#### Medium Priority (P1):
- `invoice.created`, `invoice.paid`, `invoice.overdue`
- `order.updated`, `order.fulfilled`
- `subscription.updated`, `subscription.expired`

#### Low Priority (P2):
- Analytics events
- Detailed audit events

---

## 📦 Summary

### Payment Service:
- **Publish**: 10 events (4 current + 6 new)
- **Subscribe**: 6 events (all new)
- **Clients**: 5 clients (2 current + 3 new)

### Order Service:
- **Publish**: 8 events (3 current + 5 new)
- **Subscribe**: 8 events (2 current in main.py + 6 new)
- **Clients**: 6 clients (4 current + 2 new)

### Critical Actions:
1. ⚠️ Migrate order_service event handlers from main.py to events/handlers.py
2. ⚠️ Add payment.refunded event for refund flow
3. ⚠️ Add order.expired event for timeout handling
4. ⚠️ Add subscription event handlers in payment_service
5. ⚠️ Add wallet event handlers in payment_service
