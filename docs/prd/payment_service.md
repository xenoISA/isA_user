# Payment Service - Product Requirements Document (PRD)

## Product Overview

The Payment Service provides subscription management, payment processing, invoice generation, and refund handling for the isA_user platform, enabling secure transaction processing with Stripe integration.

**Product Goal**: Deliver a reliable, secure payment system that manages subscriptions, processes payments through Stripe, generates invoices, and handles refunds while providing comprehensive transaction history and statistics.

**Key Capabilities**:
- Subscription plan management and lifecycle
- Payment intent creation and confirmation with Stripe
- Invoice generation and payment tracking
- Refund processing (full and partial)
- Stripe webhook handling for event synchronization
- Revenue and subscription statistics

---

## Target Users

### Primary Users

#### 1. End Users (via Client Applications)
- **Description**: Individuals subscribing to platform services and making payments
- **Needs**: Easy subscription management, secure payments, transaction history
- **Goals**: Subscribe to plans, make payments, view invoices, request refunds

#### 2. Frontend Applications
- **Description**: Web and mobile applications handling payment flows
- **Needs**: Payment intents with client_secret, subscription management APIs
- **Goals**: Complete checkout flows, display subscription status, show payment history

### Secondary Users

#### 3. Finance and Business Teams
- **Description**: Revenue operations, financial analysts, accounting
- **Needs**: Revenue metrics, subscription statistics, invoice records
- **Goals**: Monitor revenue, track MRR, analyze churn, reconcile payments

#### 4. Internal Services
- **Description**: Account Service, Billing Service, Notification Service
- **Needs**: Payment events, subscription status, invoice notifications
- **Goals**: Update user tiers, record billing, send notifications

#### 5. Platform Administrators
- **Description**: DevOps, support team, billing operations
- **Needs**: Service health, payment debugging, refund processing
- **Goals**: Ensure payment reliability, resolve payment issues, process refunds

---

## Epics and User Stories

### Epic 1: Subscription Plan Management
**Goal**: Enable creation and management of subscription plans

**User Stories**:
- As an admin, I want to create subscription plans so that users can subscribe
- As a user, I want to view available plans so that I can choose one
- As a product manager, I want to configure plan features so that tiers are differentiated
- As a system, I want plans synced with Stripe so that billing is automated
- As an admin, I want to activate/deactivate plans so that I can control availability

### Epic 2: Subscription Lifecycle
**Goal**: Enable complete subscription management for users

**User Stories**:
- As a user, I want to subscribe to a plan so that I get platform access
- As a user, I want to view my subscription so that I know my status
- As a user, I want to upgrade/downgrade my plan so that I can change tiers
- As a user, I want to cancel my subscription so that I stop being charged
- As a user, I want trial periods so that I can try before paying
- As a system, I want subscription synced with Stripe so that billing is accurate

### Epic 3: Payment Processing
**Goal**: Enable secure payment processing through Stripe

**User Stories**:
- As a user, I want to initiate payments so that I can pay for services
- As a frontend, I want client_secret so that I can use Stripe.js
- As a user, I want payments confirmed so that my transaction completes
- As a user, I want payment history so that I can see past transactions
- As a system, I want payment status tracked so that records are accurate

### Epic 4: Invoice Management
**Goal**: Enable invoice generation and payment

**User Stories**:
- As a user, I want invoices generated so that I have billing records
- As a user, I want to view my invoices so that I can see charges
- As a user, I want to pay invoices so that my account is current
- As finance, I want invoice numbers so that records are trackable
- As a user, I want invoice details so that I understand charges

### Epic 5: Refund Processing
**Goal**: Enable refund requests and processing

**User Stories**:
- As a user, I want to request refunds so that I can get money back
- As an admin, I want to process refunds so that user issues are resolved
- As a user, I want partial refunds supported so that appropriate amounts are returned
- As a system, I want refunds processed in Stripe so that funds are returned
- As a user, I want refund status so that I know when to expect funds

### Epic 6: Webhook Integration
**Goal**: Enable real-time Stripe event synchronization

**User Stories**:
- As a system, I want webhooks handled so that payment status is synchronized
- As a system, I want subscription events processed so that status is current
- As a system, I want invoice events handled so that payments are tracked
- As a system, I want webhook signatures verified so that events are authentic
- As a system, I want events published so that other services react

---

## API Surface Documentation

### Health Check Endpoints

#### GET /health
**Description**: Basic health check
**Auth Required**: No
**Response**:
```json
{
  "status": "healthy",
  "service": "payment_service",
  "port": 8207,
  "version": "1.0.0",
  "timestamp": "2025-12-16T10:30:00Z"
}
```

#### GET /health/detailed
**Description**: Detailed health check with Stripe and database status
**Response**:
```json
{
  "service": "payment_service",
  "status": "operational",
  "port": 8207,
  "stripe_test_mode": true,
  "database_connected": true,
  "account_client_available": true,
  "wallet_client_available": true,
  "timestamp": "2025-12-16T10:30:00Z"
}
```

### Subscription Plan Endpoints

#### GET /api/v1/payment/plans
**Description**: List available subscription plans
**Auth Required**: Yes
**Query Parameters**:
- tier: (optional) Filter by tier (free, basic, pro, enterprise)
- is_public: (optional, default: true) Filter by visibility
**Response**:
```json
{
  "plans": [
    {
      "plan_id": "plan_pro_monthly",
      "name": "Pro Monthly",
      "tier": "pro",
      "price": 29.99,
      "currency": "USD",
      "billing_cycle": "monthly",
      "features": {"api_calls": 10000, "storage_gb": 100},
      "trial_days": 14,
      "is_active": true
    }
  ]
}
```

#### POST /api/v1/payment/plans
**Description**: Create subscription plan
**Auth Required**: Yes (Admin)
**Request**:
```json
{
  "plan_id": "plan_pro_monthly",
  "name": "Pro Monthly",
  "tier": "pro",
  "price": 29.99,
  "billing_cycle": "monthly",
  "features": {"api_calls": 10000},
  "trial_days": 14
}
```
**Response**: Created plan object
**Error Codes**: 400 (Bad Request), 422 (Validation Error)

### Subscription Endpoints

#### POST /api/v1/payment/subscriptions
**Description**: Create new subscription
**Auth Required**: Yes
**Request**:
```json
{
  "user_id": "user_12345",
  "plan_id": "plan_pro_monthly",
  "payment_method_id": "pm_card_visa",
  "trial_days": 14,
  "metadata": {"source": "web"}
}
```
**Response**:
```json
{
  "subscription": {
    "subscription_id": "sub_xyz789",
    "user_id": "user_12345",
    "plan_id": "plan_pro_monthly",
    "status": "trialing",
    "tier": "pro",
    "current_period_start": "2025-12-16T00:00:00Z",
    "current_period_end": "2025-12-30T00:00:00Z",
    "trial_end": "2025-12-30T00:00:00Z",
    "stripe_subscription_id": "sub_stripe_abc"
  },
  "plan": {...}
}
```
**Error Codes**: 400 (Bad Request), 404 (Plan Not Found), 422 (Validation Error)

#### GET /api/v1/payment/subscriptions/{user_id}
**Description**: Get user's current subscription
**Auth Required**: Yes
**Response**: SubscriptionResponse object or null

#### PUT /api/v1/payment/subscriptions/{subscription_id}
**Description**: Update subscription (plan change, etc.)
**Request**:
```json
{
  "plan_id": "plan_enterprise_monthly",
  "cancel_at_period_end": false,
  "metadata": {"upgrade_reason": "growth"}
}
```
**Response**: Updated SubscriptionResponse

#### POST /api/v1/payment/subscriptions/{subscription_id}/cancel
**Description**: Cancel subscription
**Request**:
```json
{
  "immediate": false,
  "reason": "No longer needed"
}
```
**Response**: Canceled Subscription object

### Payment Endpoints

#### POST /api/v1/payment/payments/intent
**Description**: Create payment intent
**Auth Required**: Yes
**Request**:
```json
{
  "user_id": "user_12345",
  "amount": 29.99,
  "currency": "USD",
  "description": "Pro Monthly Subscription",
  "metadata": {"subscription_id": "sub_xyz"}
}
```
**Response**:
```json
{
  "payment_intent_id": "pi_abc123",
  "client_secret": "pi_abc123_secret_xyz",
  "amount": 29.99,
  "currency": "USD",
  "status": "pending",
  "metadata": {...}
}
```
**Error Codes**: 400 (Bad Request), 422 (Validation Error), 500 (Stripe Error)

#### POST /api/v1/payment/payments/{payment_id}/confirm
**Description**: Confirm payment (after Stripe.js confirmation)
**Response**: Updated Payment object with status "succeeded"

#### POST /api/v1/payment/payments/{payment_id}/fail
**Description**: Mark payment as failed
**Request**:
```json
{
  "failure_reason": "Card declined",
  "failure_code": "card_declined"
}
```
**Response**: Updated Payment object

#### GET /api/v1/payment/payments
**Description**: Get payment history
**Query Parameters**:
- user_id: User ID
- status: (optional) Filter by status
- start_date, end_date: (optional) Date range
- limit: (optional, default: 100) Max results
**Response**:
```json
{
  "payments": [...],
  "total_count": 15,
  "total_amount": 449.85,
  "filters_applied": {...}
}
```

### Invoice Endpoints

#### POST /api/v1/payment/invoices
**Description**: Create invoice
**Request**:
```json
{
  "user_id": "user_12345",
  "subscription_id": "sub_xyz",
  "amount_due": 29.99,
  "due_date": "2025-12-30T00:00:00Z",
  "line_items": [
    {"description": "Pro Plan", "amount": 29.99}
  ]
}
```
**Response**: Created Invoice object

#### GET /api/v1/payment/invoices/{invoice_id}
**Description**: Get invoice details
**Response**:
```json
{
  "invoice": {
    "invoice_id": "inv_abc123",
    "invoice_number": "INV-20251216-user12",
    "user_id": "user_12345",
    "status": "open",
    "amount_total": 29.99,
    "amount_due": 29.99,
    "due_date": "2025-12-30T00:00:00Z",
    "line_items": [...]
  },
  "payment": null
}
```

#### POST /api/v1/payment/invoices/{invoice_id}/pay
**Description**: Pay invoice
**Request**:
```json
{
  "payment_method_id": "pm_card_visa"
}
```
**Response**: Updated Invoice with status "paid"

### Refund Endpoints

#### POST /api/v1/payment/refunds
**Description**: Create refund
**Request**:
```json
{
  "payment_id": "pi_abc123",
  "amount": 29.99,
  "reason": "Customer request",
  "requested_by": "user_12345"
}
```
**Response**:
```json
{
  "refund_id": "re_xyz789",
  "payment_id": "pi_abc123",
  "user_id": "user_12345",
  "amount": 29.99,
  "status": "processing",
  "reason": "Customer request",
  "processor_refund_id": "re_stripe_abc"
}
```
**Error Codes**: 400 (Payment Not Found), 400 (Not Eligible), 400 (Amount Exceeded), 500 (Stripe Error)

#### POST /api/v1/payment/refunds/{refund_id}/process
**Description**: Process pending refund
**Request**:
```json
{
  "approved_by": "admin_user"
}
```
**Response**: Updated Refund with status "succeeded"

### Webhook Endpoints

#### POST /api/v1/payment/webhooks/stripe
**Description**: Stripe webhook handler
**Auth Required**: Stripe signature verification
**Headers**:
- Stripe-Signature: Webhook signature
**Response**: 200 OK on success

### Statistics Endpoints

#### GET /api/v1/payment/stats/revenue
**Description**: Get revenue statistics
**Query Parameters**:
- start_date, end_date: (optional) Date range
- days: (optional, default: 30) Days to analyze
**Response**:
```json
{
  "total_revenue": 15420.50,
  "payment_count": 520,
  "average_payment": 29.66,
  "daily_revenue": {...},
  "period_days": 30
}
```

#### GET /api/v1/payment/stats/subscriptions
**Description**: Get subscription statistics
**Response**:
```json
{
  "active_subscriptions": 485,
  "tier_distribution": {
    "free": 200,
    "basic": 150,
    "pro": 100,
    "enterprise": 35
  },
  "churn_rate": 3.5,
  "canceled_last_30_days": 17
}
```

---

## Functional Requirements

### Subscription Plans

**FR-001**: System MUST create subscription plans with tier and pricing
- Accept plan_id, name, tier, price, billing_cycle
- Support feature configuration
- Sync with Stripe Product/Price

**FR-002**: System MUST list available plans
- Filter by tier and visibility
- Return active plans only by default

### Subscriptions

**FR-003**: System MUST create subscriptions with user validation
- Validate user via Account Service
- Check for existing active subscription
- Create Stripe Subscription if configured

**FR-004**: System MUST manage subscription lifecycle
- Support trial periods
- Handle status transitions (trialing -> active -> canceled)
- Support immediate and end-of-period cancellation

**FR-005**: System MUST sync subscriptions with Stripe
- Create Stripe Customer if not exists
- Create Stripe Subscription
- Store Stripe IDs for reconciliation

### Payments

**FR-006**: System MUST create payment intents via Stripe
- Validate user before creation
- Return client_secret for Stripe.js
- Create local payment record

**FR-007**: System MUST confirm payments
- Update payment status to "succeeded"
- Confirm in Stripe if configured
- Publish payment.completed event

**FR-008**: System MUST handle payment failures
- Record failure reason and code
- Update status to "failed"
- Publish payment.failed event

### Invoices

**FR-009**: System MUST create invoices for billing periods
- Generate unique invoice numbers
- Include line items
- Set due date

**FR-010**: System MUST process invoice payments
- Create PaymentIntent for amount due
- Update invoice status on payment
- Record payment_intent_id

### Refunds

**FR-011**: System MUST create refunds for succeeded payments
- Validate payment eligibility
- Support full and partial refunds
- Process via Stripe Refund API

**FR-012**: System MUST update payment status on refund
- Full refund: status = "refunded"
- Partial refund: status = "partial_refund"
- Publish payment.refunded event

### Webhooks

**FR-013**: System MUST verify Stripe webhook signatures
- Use webhook secret for verification
- Reject invalid signatures

**FR-014**: System MUST handle Stripe events
- payment_intent.succeeded: Confirm payment
- payment_intent.payment_failed: Fail payment
- customer.subscription.created/deleted: Publish events
- invoice.payment_succeeded: Mark invoice paid

### Event Publishing

**FR-015**: System MUST publish events for all operations
- subscription.created/updated/canceled
- payment.intent.created/completed/failed/refunded
- invoice.created/paid

---

## Non-Functional Requirements

### Performance

**NFR-001**: Payment intent creation MUST complete within 2000ms (p95)

**NFR-002**: Subscription creation MUST complete within 3000ms (p95)

**NFR-003**: Refund processing MUST complete within 2000ms (p95)

**NFR-004**: Health check MUST complete within 20ms (p99)

**NFR-005**: Service MUST handle 100 payment requests per second

### Reliability

**NFR-006**: Service uptime MUST be 99.9%

**NFR-007**: Stripe API failures MUST be handled gracefully

**NFR-008**: Event publishing failures MUST NOT block payment operations

**NFR-009**: Webhook processing MUST be idempotent

### Security

**NFR-010**: Card details MUST NOT be stored (PCI compliance)

**NFR-011**: Webhook signatures MUST be verified

**NFR-012**: Payment data MUST be user-scoped

**NFR-013**: Stripe secret key MUST be stored securely (env var)

### Data Integrity

**NFR-014**: Payment records MUST be immutable after completion

**NFR-015**: Refund amounts MUST NOT exceed payment amounts

**NFR-016**: Subscription changes MUST be atomic

---

## Success Metrics

### Revenue Metrics
- **Total Revenue**: Daily/weekly/monthly payment totals
- **MRR**: Monthly Recurring Revenue from subscriptions
- **ARPU**: Average revenue per user
- **Revenue by Plan**: Breakdown by subscription tier

### Subscription Metrics
- **Active Subscriptions**: Count by tier
- **Churn Rate**: % canceled in period (target: <5%)
- **Trial Conversion**: % of trials converting to paid
- **Subscription Growth**: Period-over-period

### Operational Metrics
- **Payment Success Rate**: % succeeded vs failed (target: >95%)
- **Refund Rate**: % of payments refunded (target: <3%)
- **Webhook Processing Time**: Time to handle Stripe events (target: <200ms)
- **API Latency**: p50, p95, p99 response times

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Payment Service Team
