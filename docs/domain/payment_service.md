# Payment Service - Domain Context

## Overview

The Payment Service is the **transaction processing and subscription management engine** for the isA_user platform. It provides centralized payment processing, subscription lifecycle management, invoice generation, and refund handling. All monetary transactions in the system flow through the Payment Service, with Stripe integration for secure payment processing.

**Business Context**: Enable secure, reliable payment processing and subscription management for platform services. Payment Service owns the "what to charge and how" - handling subscriptions, payment intents, invoices, and refunds while integrating with Stripe for actual payment processing.

**Core Value Proposition**: Transform business transactions into secure payment flows with comprehensive subscription management, supporting multiple payment methods, recurring billing cycles, and full refund capabilities, enabling transparent monetization and revenue management.

---

## Business Taxonomy

### Core Entities

#### 1. Subscription Plan
**Definition**: A predefined pricing tier that defines features, pricing, and billing terms for platform access.

**Business Purpose**:
- Define tiered service offerings
- Establish pricing structures
- Configure feature access per tier
- Support trial periods
- Enable Stripe product synchronization

**Key Attributes**:
- Plan ID (unique identifier)
- Name (display name)
- Tier (free, basic, pro, enterprise)
- Price (amount in currency)
- Currency (USD, EUR, etc.)
- Billing Cycle (monthly, quarterly, yearly, one_time)
- Features (JSONB - feature flags and limits)
- Credits Included (platform credits)
- Max Users (team size limit)
- Max Storage GB (storage quota)
- Trial Days (trial period length)
- Stripe Product ID (Stripe sync)
- Stripe Price ID (Stripe sync)
- Is Active (availability flag)
- Is Public (visibility flag)

**Subscription Tiers**:
- **Free**: Basic access with limited features
- **Basic**: Standard features for individuals
- **Pro**: Advanced features for professionals
- **Enterprise**: Full features with dedicated support

#### 2. Subscription
**Definition**: A user's active subscription to a specific plan, managing billing cycles and access rights.

**Business Purpose**:
- Track user subscription status
- Manage billing cycles
- Handle subscription lifecycle (trial, active, canceled)
- Enable plan upgrades/downgrades
- Synchronize with Stripe subscriptions

**Key Attributes**:
- Subscription ID (unique identifier)
- User ID (subscriber)
- Organization ID (optional team subscription)
- Plan ID (subscribed plan)
- Status (trialing, active, past_due, canceled, unpaid)
- Tier (inherited from plan)
- Current Period Start/End (billing window)
- Billing Cycle (from plan)
- Trial Start/End (trial window)
- Cancel At Period End (pending cancellation)
- Canceled At (cancellation timestamp)
- Cancellation Reason (user feedback)
- Payment Method ID (default payment method)
- Stripe Subscription ID (Stripe sync)
- Stripe Customer ID (Stripe sync)
- Metadata (JSONB - additional context)

**Subscription Statuses**:
- **Trialing**: User in trial period
- **Active**: Subscription current and paid
- **Past Due**: Payment failed, grace period
- **Canceled**: Subscription terminated
- **Unpaid**: Payment failed, access restricted

#### 3. Payment
**Definition**: A single monetary transaction record representing a payment attempt or completion.

**Business Purpose**:
- Track payment attempts
- Record payment status
- Store processor response
- Enable payment history
- Support refund references

**Key Attributes**:
- Payment ID (unique identifier)
- User ID (payer)
- Organization ID (optional)
- Amount (transaction amount)
- Currency (transaction currency)
- Description (payment purpose)
- Status (pending, requires_action, processing, succeeded, failed, canceled, refunded, partial_refund)
- Payment Method (credit_card, bank_transfer, wallet, stripe)
- Subscription ID (optional link)
- Invoice ID (optional link)
- Processor (payment processor used)
- Processor Payment ID (Stripe PaymentIntent ID)
- Processor Response (JSONB - processor data)
- Failure Reason (error message)
- Failure Code (error code)
- Paid At (success timestamp)
- Failed At (failure timestamp)

**Payment Statuses**:
- **Pending**: Payment initiated
- **Requires Action**: Customer action needed (3DS)
- **Processing**: Payment in progress
- **Succeeded**: Payment completed
- **Failed**: Payment failed
- **Canceled**: Payment canceled
- **Refunded**: Full refund issued
- **Partial Refund**: Partial refund issued

#### 4. Invoice
**Definition**: A billing document detailing charges for a billing period.

**Business Purpose**:
- Generate billing statements
- Track billing periods
- Support payment reconciliation
- Enable invoice downloads
- Comply with accounting requirements

**Key Attributes**:
- Invoice ID (unique identifier)
- Invoice Number (human-readable reference)
- User ID (billed user)
- Organization ID (optional)
- Subscription ID (optional link)
- Status (draft, open, paid, void, uncollectible)
- Amount Total (total invoice amount)
- Amount Paid (paid portion)
- Amount Due (remaining balance)
- Currency (invoice currency)
- Billing Period Start/End (period covered)
- Payment Method ID (payment method used)
- Payment Intent ID (linked payment)
- Line Items (JSONB - itemized charges)
- Stripe Invoice ID (Stripe sync)
- Due Date (payment deadline)
- Paid At (payment timestamp)

**Invoice Statuses**:
- **Draft**: Invoice being prepared
- **Open**: Invoice issued, awaiting payment
- **Paid**: Invoice fully paid
- **Void**: Invoice canceled
- **Uncollectible**: Payment failed permanently

#### 5. Refund
**Definition**: A reversal of a completed payment, returning funds to the customer.

**Business Purpose**:
- Process customer refunds
- Track refund status
- Support partial refunds
- Maintain audit trail
- Comply with regulations

**Key Attributes**:
- Refund ID (unique identifier)
- Payment ID (original payment)
- User ID (refund recipient)
- Amount (refund amount)
- Currency (refund currency)
- Reason (refund reason)
- Status (pending, processing, succeeded, failed, canceled)
- Processor (refund processor)
- Processor Refund ID (Stripe refund ID)
- Processor Response (JSONB - processor data)
- Requested By (user or admin)
- Approved By (admin if applicable)
- Requested At (request timestamp)
- Processed At (processing start)
- Completed At (completion timestamp)

**Refund Statuses**:
- **Pending**: Refund requested
- **Processing**: Refund in progress
- **Succeeded**: Refund completed
- **Failed**: Refund failed
- **Canceled**: Refund canceled

#### 6. Payment Method Info
**Definition**: Stored payment method information for recurring payments.

**Business Purpose**:
- Enable saved payment methods
- Support recurring billing
- Securely reference payment details
- Track default payment method
- Enable quick checkout

**Key Attributes**:
- Method ID (unique identifier)
- User ID (method owner)
- Method Type (credit_card, bank_transfer, wallet)
- Card Brand (visa, mastercard, etc.)
- Card Last4 (masked card number)
- Card Exp Month/Year (expiration)
- Bank Name (for bank transfers)
- Stripe Payment Method ID (Stripe reference)
- Is Default (default flag)
- Is Verified (verification status)

---

## Domain Scenarios

### Scenario 1: Create Subscription
**Actor**: User, Client Application
**Trigger**: User selects a subscription plan
**Flow**:
1. Client calls `POST /api/v1/payment/subscriptions` with:
   - user_id
   - plan_id
   - payment_method_id (optional)
   - trial_days (optional override)
2. Payment Service validates user via Account Service
3. Fetches subscription plan details
4. If user already has active subscription, returns error
5. Calculates trial period if applicable
6. If Stripe configured and payment method provided:
   - Creates or retrieves Stripe Customer
   - Creates Stripe Subscription
   - Stores Stripe IDs
7. Creates local Subscription record
8. Publishes `subscription.created` event
9. Returns SubscriptionResponse with plan details

**Outcome**: User has active subscription, Stripe synchronized, events published

### Scenario 2: Create Payment Intent
**Actor**: User, Client Application
**Trigger**: User initiates payment (one-time or manual)
**Flow**:
1. Client calls `POST /api/v1/payment/payments/intent` with:
   - user_id
   - amount
   - currency
   - description
   - metadata
2. Payment Service validates user via Account Service
3. If Stripe configured:
   - Creates Stripe PaymentIntent
   - Gets client_secret for frontend
4. Creates local Payment record with status "pending"
5. Publishes `payment.intent.created` event
6. Returns PaymentIntentResponse with:
   - payment_intent_id
   - client_secret (for Stripe.js)
   - amount, currency, status

**Outcome**: Payment intent created, ready for confirmation

### Scenario 3: Confirm Payment
**Actor**: Client Application (after Stripe.js confirmation)
**Trigger**: Payment intent confirmed on frontend
**Flow**:
1. Client calls `POST /api/v1/payment/payments/{payment_id}/confirm`
2. Payment Service retrieves payment record
3. If Stripe configured:
   - Confirms PaymentIntent in Stripe
   - Captures payment
4. Updates payment status to "succeeded"
5. Sets paid_at timestamp
6. Publishes `payment.completed` event
7. Returns updated Payment

**Outcome**: Payment confirmed and captured

### Scenario 4: Cancel Subscription
**Actor**: User
**Trigger**: User requests subscription cancellation
**Flow**:
1. Client calls `POST /api/v1/payment/subscriptions/{subscription_id}/cancel` with:
   - immediate (boolean)
   - reason (optional)
2. Payment Service retrieves subscription
3. If Stripe configured:
   - If immediate: Deletes Stripe Subscription
   - If not: Sets cancel_at_period_end = true
4. Updates local subscription:
   - If immediate: Status = "canceled"
   - If not: cancel_at_period_end = true
5. Records cancellation reason
6. Publishes `subscription.canceled` event
7. Returns updated Subscription

**Outcome**: Subscription canceled immediately or at period end

### Scenario 5: Create Refund
**Actor**: User, Admin
**Trigger**: Refund request for completed payment
**Flow**:
1. Client calls `POST /api/v1/payment/refunds` with:
   - payment_id
   - amount (optional, defaults to full)
   - reason
   - requested_by
2. Payment Service validates original payment:
   - Payment must exist
   - Status must be "succeeded"
3. Validates refund amount <= payment amount
4. If Stripe configured:
   - Creates Stripe Refund
   - Gets processor refund ID
5. Creates local Refund record
6. Updates Payment status:
   - If full: "refunded"
   - If partial: "partial_refund"
7. Publishes `payment.refunded` event
8. Returns Refund record

**Outcome**: Refund processed, payment updated

### Scenario 6: Pay Invoice
**Actor**: User
**Trigger**: User pays open invoice
**Flow**:
1. Client calls `POST /api/v1/payment/invoices/{invoice_id}/pay` with:
   - payment_method_id
2. Payment Service retrieves invoice
3. Validates invoice status is "open"
4. Creates PaymentIntent for invoice amount
5. Links PaymentIntent to invoice
6. Processes payment (see Scenario 3)
7. Updates invoice:
   - Status = "paid"
   - paid_at = now
   - amount_paid = amount_total
8. Returns updated Invoice

**Outcome**: Invoice paid, payment recorded

### Scenario 7: Handle Stripe Webhook
**Actor**: Stripe (webhook callback)
**Trigger**: Stripe event (payment success, failure, subscription change)
**Flow**:
1. Stripe sends webhook to `POST /api/v1/payment/webhooks/stripe`
2. Payment Service verifies signature using webhook secret
3. Parses event type and data
4. Handles event based on type:
   - `payment_intent.succeeded`: Confirm payment
   - `payment_intent.payment_failed`: Fail payment
   - `invoice.payment_succeeded`: Mark invoice paid
   - `customer.subscription.created`: Publish event
   - `customer.subscription.deleted`: Publish event
5. Publishes corresponding platform events
6. Returns 200 OK to Stripe

**Outcome**: Platform synchronized with Stripe state

### Scenario 8: Get Payment History
**Actor**: User
**Trigger**: User views payment history
**Flow**:
1. Client calls `GET /api/v1/payment/payments?user_id={user_id}`
2. Payment Service queries payments with filters:
   - user_id
   - Optional: status filter
   - Optional: date range
3. Orders by created_at DESC
4. Applies pagination
5. Calculates total count and total amount
6. Returns PaymentHistoryResponse

**Outcome**: User sees payment history with statistics

---

## Domain Events

### Published Events

#### 1. payment.intent.created
**Trigger**: Payment intent successfully created
**Source**: payment_service
**Payload**:
- payment_intent_id: Payment intent identifier
- user_id: User identifier
- amount: Payment amount
- currency: Payment currency
- metadata: Additional context

**Subscribers**:
- **Analytics Service**: Track payment initiation
- **Audit Service**: Log payment intent

#### 2. payment.completed
**Trigger**: Payment successfully processed
**Source**: payment_service
**Payload**:
- payment_intent_id: Payment intent identifier
- user_id: User identifier
- amount: Payment amount
- currency: Payment currency
- payment_id: Local payment ID
- payment_method: Method used
- metadata: Additional context

**Subscribers**:
- **Wallet Service**: Update balance if applicable
- **Notification Service**: Send payment confirmation
- **Analytics Service**: Track revenue
- **Billing Service**: Record payment for billing

#### 3. payment.failed
**Trigger**: Payment processing fails
**Source**: payment_service
**Payload**:
- payment_intent_id: Payment intent identifier
- user_id: User identifier
- amount: Attempted amount
- currency: Payment currency
- error_message: Failure reason
- error_code: Failure code

**Subscribers**:
- **Notification Service**: Alert user of failure
- **Analytics Service**: Track payment failures
- **Audit Service**: Log payment failure

#### 4. payment.refunded
**Trigger**: Refund successfully processed
**Source**: payment_service
**Payload**:
- refund_id: Refund identifier
- payment_id: Original payment ID
- user_id: User identifier
- amount: Refund amount
- currency: Refund currency
- reason: Refund reason

**Subscribers**:
- **Wallet Service**: Update balance if applicable
- **Notification Service**: Send refund confirmation
- **Analytics Service**: Track refunds

#### 5. subscription.created
**Trigger**: New subscription created
**Source**: payment_service
**Payload**:
- subscription_id: Subscription identifier
- user_id: Subscriber ID
- plan_id: Plan ID
- status: Initial status
- current_period_start: Period start
- current_period_end: Period end
- trial_end: Trial end (if applicable)
- metadata: Additional context

**Subscribers**:
- **Account Service**: Update user tier
- **Notification Service**: Send welcome email
- **Analytics Service**: Track subscription metrics

#### 6. subscription.updated
**Trigger**: Subscription modified (plan change, etc.)
**Source**: payment_service
**Payload**:
- subscription_id: Subscription identifier
- user_id: Subscriber ID
- plan_id: New plan ID
- old_plan_id: Previous plan ID
- status: Current status
- metadata: Additional context

**Subscribers**:
- **Account Service**: Update user tier
- **Notification Service**: Send plan change notification

#### 7. subscription.canceled
**Trigger**: Subscription canceled
**Source**: payment_service
**Payload**:
- subscription_id: Subscription identifier
- user_id: Subscriber ID
- canceled_at: Cancellation timestamp
- plan_id: Canceled plan
- reason: Cancellation reason
- metadata: Additional context

**Subscribers**:
- **Account Service**: Update user tier
- **Notification Service**: Send cancellation confirmation
- **Analytics Service**: Track churn

#### 8. invoice.created
**Trigger**: New invoice generated
**Source**: payment_service
**Payload**:
- invoice_id: Invoice identifier
- user_id: Billed user
- subscription_id: Linked subscription
- amount_due: Amount to pay
- due_date: Payment deadline

**Subscribers**:
- **Notification Service**: Send invoice notification

#### 9. invoice.paid
**Trigger**: Invoice payment received
**Source**: payment_service
**Payload**:
- invoice_id: Invoice identifier
- user_id: Billed user
- amount_paid: Amount received
- payment_intent_id: Payment reference

**Subscribers**:
- **Notification Service**: Send payment receipt
- **Analytics Service**: Track invoice payments

### Subscribed Events

#### 1. order.created
**Source**: order_service
**Purpose**: Create payment for order
**Payload**:
- order_id
- user_id
- total_amount
- currency
- items

**Handler Action**: Creates payment intent for order

#### 2. wallet.balance_changed
**Source**: wallet_service
**Purpose**: Track balance changes
**Payload**:
- user_id
- wallet_type
- old_balance
- new_balance
- change_amount

**Handler Action**: Logs balance change for reconciliation

#### 3. wallet.insufficient_funds
**Source**: wallet_service
**Purpose**: Handle insufficient funds
**Payload**:
- user_id
- required_amount
- available_amount

**Handler Action**: Logs insufficient funds event

#### 4. subscription.usage_exceeded
**Source**: subscription_service
**Purpose**: Handle usage overage
**Payload**:
- subscription_id
- user_id
- usage_type
- limit
- current_usage

**Handler Action**: May trigger overage billing

#### 5. user.deleted
**Source**: account_service
**Purpose**: Clean up on user deletion
**Payload**:
- user_id
- timestamp

**Handler Action**: Cancels subscriptions, archives payment data

#### 6. user.upgraded
**Source**: account_service
**Purpose**: Handle user tier upgrade
**Payload**:
- user_id
- old_tier
- new_tier

**Handler Action**: Updates subscription tier if applicable

---

## Core Concepts

### Payment Lifecycle
1. **Intent Creation**: PaymentIntent created, client_secret returned
2. **Client Confirmation**: Frontend confirms with Stripe.js
3. **Processing**: Payment processed by Stripe
4. **Completion**: Status updated, events published
5. **Reconciliation**: Webhooks ensure consistency

### Subscription Lifecycle
1. **Creation**: User subscribes to plan
2. **Trialing**: Optional trial period
3. **Active**: Recurring billing active
4. **Past Due**: Payment failed, grace period
5. **Canceled**: Subscription terminated

### Stripe Integration Flow
```
Create Payment Intent
       ↓
Get client_secret → Frontend uses Stripe.js
       ↓
User enters payment details
       ↓
Stripe processes payment
       ↓
Webhook: payment_intent.succeeded → Confirm local payment
       ↓
Events published to platform
```

### Refund Processing
- **Full Refund**: Amount = payment amount, status = "refunded"
- **Partial Refund**: Amount < payment amount, status = "partial_refund"
- **Stripe Refund**: Processed via Stripe Refund API
- **Reason Mapping**: Custom reasons mapped to Stripe-accepted values

### Separation of Concerns
**Payment Service owns**:
- Subscription plan management
- Subscription lifecycle
- Payment intent and processing
- Invoice generation and payment
- Refund processing
- Stripe integration

**Payment Service does NOT own**:
- Wallet balance (wallet_service)
- Usage tracking (billing_service)
- Product pricing (product_service)
- User authentication (auth_service)
- User accounts (account_service)

---

## Business Rules (High-Level)

### Subscription Rules
- **BR-SUB-001**: User validated via Account Service before subscription
- **BR-SUB-002**: Only one active subscription per user
- **BR-SUB-003**: Plan must exist and be active
- **BR-SUB-004**: Trial days default to plan's trial_days
- **BR-SUB-005**: Cancellation can be immediate or at period end
- **BR-SUB-006**: Canceled subscriptions can't be updated

### Payment Rules
- **BR-PAY-001**: User validated before payment creation
- **BR-PAY-002**: Amount must be positive
- **BR-PAY-003**: Currency must be valid ISO code
- **BR-PAY-004**: PaymentIntent ID returned from Stripe
- **BR-PAY-005**: Confirmation requires payment exists
- **BR-PAY-006**: Failed payments record error details

### Refund Rules
- **BR-REF-001**: Original payment must exist
- **BR-REF-002**: Payment must be "succeeded" for refund
- **BR-REF-003**: Refund amount <= payment amount
- **BR-REF-004**: Reason mapped to Stripe-accepted values
- **BR-REF-005**: Full refund: payment status = "refunded"
- **BR-REF-006**: Partial refund: payment status = "partial_refund"

### Invoice Rules
- **BR-INV-001**: Invoice must be "open" to pay
- **BR-INV-002**: Payment creates PaymentIntent
- **BR-INV-003**: Successful payment marks invoice "paid"
- **BR-INV-004**: Invoice number unique and sequential

### Webhook Rules
- **BR-WHK-001**: Signature verification required
- **BR-WHK-002**: Event type determines handler
- **BR-WHK-003**: Unknown events logged but ignored
- **BR-WHK-004**: Duplicate events handled idempotently

### Event Publishing Rules
- **BR-EVT-001**: All mutations publish events
- **BR-EVT-002**: Event failures logged but don't block
- **BR-EVT-003**: Events include full context
- **BR-EVT-004**: Timestamps use ISO 8601

---

## Payment Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User validation
- **Product Service**: Product information
- **Stripe**: Payment processing
- **PostgreSQL gRPC Service**: Persistent storage
- **NATS Event Bus**: Event publishing/subscribing
- **Consul**: Service discovery and health checks

### Downstream Consumers
- **Wallet Service**: Balance updates on payments
- **Billing Service**: Payment records for billing
- **Notification Service**: Payment confirmations
- **Analytics Service**: Revenue and subscription metrics
- **Audit Service**: Payment activity logging
- **Account Service**: Subscription tier updates

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Stripe Webhooks**: Event-driven Stripe synchronization
- **Service Discovery**: Consul for dynamic service location
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection
- **Repository Pattern**: PaymentRepository for data access
- **Protocol Interfaces**: PaymentRepositoryProtocol, EventBusProtocol
- **Client Protocols**: AccountClientProtocol, WalletClientProtocol, BillingClientProtocol, ProductClientProtocol
- **Factory Pattern**: create_payment_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Revenue Metrics
- **Total Revenue**: Daily/weekly/monthly payment totals
- **MRR (Monthly Recurring Revenue)**: From subscriptions
- **ARPU**: Average revenue per user
- **Revenue by Plan**: Breakdown by subscription tier

### Subscription Metrics
- **Active Subscriptions**: Count by tier
- **Churn Rate**: % canceled in period (target: <5%)
- **Trial Conversion Rate**: % of trials converting to paid
- **Subscription Growth Rate**: Period-over-period

### Operational Metrics
- **Payment Success Rate**: % succeeded vs failed (target: >95%)
- **Refund Rate**: % of payments refunded (target: <3%)
- **Processing Latency**: PaymentIntent to completion (target: <3s)
- **Webhook Processing Time**: Stripe event handling (target: <200ms)

### System Metrics
- **Service Uptime**: Payment Service availability (target: 99.9%)
- **Stripe API Success Rate**: % successful Stripe calls
- **Database Connectivity**: PostgreSQL health
- **Event Publishing Success**: % of events published

---

## Glossary

**Subscription Plan**: Predefined pricing tier with features and pricing
**Subscription**: User's active subscription to a plan
**Payment**: Single monetary transaction record
**Payment Intent**: Stripe object representing payment attempt
**Invoice**: Billing document for charges
**Refund**: Reversal of completed payment
**Payment Method**: Stored payment instrument
**Client Secret**: Stripe.js token for frontend confirmation
**Webhook**: HTTP callback from Stripe for events
**Recurring Billing**: Automatic periodic charges
**Billing Cycle**: Payment frequency (monthly, yearly, etc.)
**Subscription Tier**: Service level (free, basic, pro, enterprise)
**Churn**: Customer subscription cancellation
**MRR**: Monthly Recurring Revenue from subscriptions
**Event Bus**: NATS messaging for asynchronous events

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Payment Service Team
