# Payment Service - Logic Contract

## Business Rules (60 rules)

### Subscription Plan Rules (BR-PLN-001 to BR-PLN-010)

**BR-PLN-001: Plan ID Required**
- Subscription plan MUST have a plan_id
- System validates plan_id is non-empty string
- Error returned if violated: "plan_id is required"
- Example: `{"plan_id": ""}` -> 400 Bad Request

**BR-PLN-002: Plan Name Required**
- Subscription plan MUST have a name
- System validates name is non-empty string
- Max length: 100 characters
- Example: `{"name": ""}` -> 400 Bad Request

**BR-PLN-003: Tier Validation**
- Tier MUST be valid enum value
- Valid tiers: free, basic, pro, enterprise
- Invalid tier returns 400 Bad Request
- Example: `{"tier": "invalid"}` -> 400 Bad Request

**BR-PLN-004: Billing Cycle Validation**
- Billing cycle MUST be valid enum value
- Valid cycles: monthly, quarterly, yearly, one_time
- Invalid cycle returns 400 Bad Request
- Example: `{"billing_cycle": "invalid"}` -> 400 Bad Request

**BR-PLN-005: Price Non-Negative**
- price MUST be >= 0
- Free tier plans can have price = 0
- Negative values rejected with 422
- Example: `{"price": -9.99}` -> 422 Validation Error

**BR-PLN-006: Features Optional**
- features is optional JSONB field
- Defaults to empty object `{}`
- Stores API limits, storage limits, etc.

**BR-PLN-007: Trial Days Non-Negative**
- trial_days MUST be >= 0
- Defaults to 0 (no trial)
- Example: `{"trial_days": -1}` -> 422 Validation Error

**BR-PLN-008: Stripe Sync Optional**
- stripe_product_id and stripe_price_id optional
- Set when Stripe integration configured
- Enables recurring billing through Stripe

**BR-PLN-009: Plan Visibility**
- is_public controls plan visibility
- Private plans for internal/enterprise use
- Public plans shown in plan listings

**BR-PLN-010: Plan Activation**
- is_active controls plan availability
- Inactive plans cannot be subscribed to
- Existing subscriptions remain active

### Subscription Rules (BR-SUB-001 to BR-SUB-015)

**BR-SUB-001: User ID Required**
- Subscription MUST have a user_id
- System validates user_id is non-empty string
- Error returned if violated: "user_id cannot be empty"
- Example: `{"user_id": ""}` -> 400 Bad Request

**BR-SUB-002: User Validation**
- User validated via Account Service before creation
- Invalid user returns: "User does not exist"
- Fail-open if Account Service unavailable

**BR-SUB-003: Plan ID Required**
- Subscription MUST have a plan_id
- System validates plan_id is non-empty string
- Error returned if violated: "plan_id cannot be empty"
- Example: `{"plan_id": ""}` -> 400 Bad Request

**BR-SUB-004: Plan Existence Check**
- Plan validated to exist and be active
- Error returned if not found: "Subscription plan not found"
- Error returned if inactive: "Plan is not active"

**BR-SUB-005: Single Active Subscription**
- User can have only one active subscription
- Creating new subscription returns error if active exists
- Cancel existing before creating new

**BR-SUB-006: Trial Period Calculation**
- Trial days from request or plan's trial_days
- trial_start = current_time
- trial_end = current_time + trial_days
- Status = "trialing" if trial_days > 0

**BR-SUB-007: Billing Period Calculation**
- current_period_start = current_time
- current_period_end based on billing_cycle:
  - monthly: +30 days
  - quarterly: +90 days
  - yearly: +365 days
  - one_time: infinite

**BR-SUB-008: Subscription Status Values**
- Valid statuses: trialing, active, past_due, canceled, unpaid
- Initial status: trialing (if trial) or active
- Status transitions follow state machine

**BR-SUB-009: Stripe Subscription Sync**
- If Stripe configured and payment_method_id provided
- Create Stripe Customer if not exists
- Create Stripe Subscription with trial
- Store stripe_subscription_id and stripe_customer_id

**BR-SUB-010: Immediate Cancellation**
- immediate = true: Cancel now
- Status set to "canceled"
- canceled_at set to current_time
- In Stripe: Delete subscription

**BR-SUB-011: End-of-Period Cancellation**
- immediate = false (default)
- cancel_at_period_end = true
- Status remains "active" until period ends
- In Stripe: Set cancel_at_period_end

**BR-SUB-012: Cancellation Reason**
- reason field stored with cancellation
- Optional but recommended
- Used for churn analysis

**BR-SUB-013: Plan Change (Upgrade/Downgrade)**
- Update plan_id to new plan
- Adjust billing cycle if different
- Recalculate period_end
- In Stripe: Update subscription

**BR-SUB-014: Subscription Metadata**
- metadata is optional JSONB field
- Defaults to empty object `{}`
- Stores custom attributes

**BR-SUB-015: Organization Subscription**
- organization_id links subscription to org
- Enables team/family subscriptions
- Shared across organization members

### Payment Rules (BR-PAY-001 to BR-PAY-015)

**BR-PAY-001: User ID Required**
- Payment intent MUST have a user_id
- System validates user_id is non-empty string
- Error returned if violated: "user_id cannot be empty"
- Example: `{"user_id": ""}` -> 400 Bad Request

**BR-PAY-002: User Validation**
- User validated via Account Service before creation
- Invalid user returns: "User does not exist"
- Fail-open if Account Service unavailable

**BR-PAY-003: Amount Required and Positive**
- amount MUST be > 0
- Zero amount not allowed for payments
- Error returned: "amount must be greater than 0"
- Example: `{"amount": 0}` -> 422 Validation Error

**BR-PAY-004: Currency Validation**
- Currency MUST be valid ISO code
- Valid currencies: USD, EUR, GBP, CNY
- Invalid currency returns 400 Bad Request
- Example: `{"currency": "INVALID"}` -> 400 Bad Request

**BR-PAY-005: Payment Intent Creation**
- Creates Stripe PaymentIntent via API
- Returns payment_intent_id and client_secret
- Local Payment record created with status "pending"

**BR-PAY-006: Client Secret Security**
- client_secret only returned at creation
- Used by Stripe.js for frontend confirmation
- Never stored after initial response

**BR-PAY-007: Payment Status Values**
- Valid statuses: pending, requires_action, processing, succeeded, failed, canceled, refunded, partial_refund
- Initial status: pending
- Status transitions follow state machine

**BR-PAY-008: Payment Confirmation**
- Confirms PaymentIntent in Stripe (test mode)
- Updates local payment status to "succeeded"
- Sets paid_at timestamp
- Publishes payment.completed event

**BR-PAY-009: Payment Failure**
- Records failure_reason and failure_code
- Updates status to "failed"
- Sets failed_at timestamp
- Publishes payment.failed event

**BR-PAY-010: Processor Payment ID**
- processor_payment_id stores Stripe PaymentIntent ID
- Enables reconciliation with Stripe
- Required for refund processing

**BR-PAY-011: Processor Response Storage**
- processor_response stores full Stripe response
- JSONB field for flexible data
- Used for debugging and audit

**BR-PAY-012: Payment Method Recording**
- payment_method records method type
- credit_card, bank_transfer, wallet, stripe
- From Stripe PaymentIntent

**BR-PAY-013: Payment Description**
- description is optional
- Appears on customer statements
- Max length: 500 characters

**BR-PAY-014: Payment Metadata**
- metadata is optional JSONB field
- Stores subscription_id, invoice_id, etc.
- Enables linking payments to other entities

**BR-PAY-015: Payment History Query**
- Supports filtering by user_id, status, date range
- Ordered by created_at DESC
- Limit configurable (default: 100, max: 500)

### Invoice Rules (BR-INV-001 to BR-INV-010)

**BR-INV-001: Invoice Number Generation**
- Invoice number auto-generated
- Format: INV-YYYYMMDD-{unique_suffix}
- Unique and sequential

**BR-INV-002: User ID Required**
- Invoice MUST have a user_id
- System validates user_id is non-empty string

**BR-INV-003: Amount Due Required**
- amount_due MUST be > 0
- Represents total to collect
- Cannot create zero-amount invoice

**BR-INV-004: Invoice Status Values**
- Valid statuses: draft, open, paid, void, uncollectible
- Initial status: open (or draft if incomplete)
- Status transitions follow state machine

**BR-INV-005: Billing Period Required**
- billing_period_start and billing_period_end required
- Defines period invoice covers
- Used for subscription billing

**BR-INV-006: Line Items**
- line_items stores itemized charges
- JSONB array of {description, amount, quantity}
- Total should match amount_total

**BR-INV-007: Invoice Payment**
- Only "open" invoices can be paid
- Creates PaymentIntent for amount_due
- Updates status to "paid" on success
- Sets paid_at timestamp

**BR-INV-008: Payment Intent Link**
- payment_intent_id links to Payment
- Set when invoice payment initiated
- Enables tracking payment status

**BR-INV-009: Due Date**
- due_date is optional but recommended
- Used for payment reminders
- Past due triggers notifications

**BR-INV-010: Stripe Invoice Sync**
- stripe_invoice_id set if using Stripe
- Enables Stripe-managed invoicing
- Optional based on configuration

### Refund Rules (BR-REF-001 to BR-REF-010)

**BR-REF-001: Payment ID Required**
- Refund MUST have a payment_id
- System validates payment_id is non-empty string
- Error returned: "payment_id cannot be empty"

**BR-REF-002: Payment Existence Check**
- Payment validated to exist
- Error returned if not found: "Payment not found"

**BR-REF-003: Payment Status Check**
- Payment MUST have status "succeeded"
- Cannot refund pending, failed, or already refunded
- Error returned: "Payment not eligible for refund"

**BR-REF-004: Refund Amount Validation**
- amount defaults to payment amount (full refund)
- If specified, must be > 0 and <= payment amount
- Error returned: "Refund amount exceeds payment amount"

**BR-REF-005: Requested By Required**
- requested_by MUST be provided
- Records who initiated refund
- User ID or admin ID

**BR-REF-006: Refund Status Values**
- Valid statuses: pending, processing, succeeded, failed, canceled
- Initial status: pending or processing
- Status transitions follow state machine

**BR-REF-007: Stripe Refund Creation**
- Creates Stripe Refund via API
- Uses processor_payment_id for reference
- Stores processor_refund_id

**BR-REF-008: Reason Mapping**
- Refund reason mapped to Stripe values
- Valid reasons: requested_by_customer, duplicate, fraudulent
- Custom reasons converted appropriately

**BR-REF-009: Payment Status Update**
- Full refund: payment status = "refunded"
- Partial refund: payment status = "partial_refund"
- Links refund to payment record

**BR-REF-010: Refund Approval**
- approved_by optionally records approver
- For admin-approved refunds
- Used for audit trail

### Webhook Rules (BR-WHK-001 to BR-WHK-010)

**BR-WHK-001: Signature Verification Required**
- Stripe-Signature header verified
- Uses webhook secret from configuration
- Invalid signature returns 400 Bad Request

**BR-WHK-002: Event Type Handling**
- Known event types processed
- Unknown events logged but acknowledged
- Returns 200 OK to prevent retries

**BR-WHK-003: Payment Intent Succeeded**
- Event: payment_intent.succeeded
- Action: Confirm local payment record
- Publish: payment.completed event

**BR-WHK-004: Payment Intent Failed**
- Event: payment_intent.payment_failed
- Action: Fail local payment record
- Publish: payment.failed event

**BR-WHK-005: Subscription Created**
- Event: customer.subscription.created
- Action: Sync local subscription if needed
- Publish: subscription.created event

**BR-WHK-006: Subscription Deleted**
- Event: customer.subscription.deleted
- Action: Update local subscription status
- Publish: subscription.canceled event

**BR-WHK-007: Invoice Payment Succeeded**
- Event: invoice.payment_succeeded
- Action: Mark invoice as paid
- Publish: invoice.paid event

**BR-WHK-008: Idempotent Processing**
- Webhook events processed idempotently
- Duplicate events ignored (same event_id)
- Prevents duplicate state changes

**BR-WHK-009: Error Handling**
- Webhook errors logged
- Returns 200 OK to prevent retries
- Internal alerts for critical errors

**BR-WHK-010: Response Format**
- Returns `{"success": true, "event": "event_type"}`
- 200 OK for all processed events
- 400 for signature verification failure

### Event Rules (BR-EVT-001 to BR-EVT-010)

**BR-EVT-001: Payment Intent Created Event**
- Published after PaymentIntent created
- Includes: payment_intent_id, user_id, amount, currency
- Enables payment tracking

**BR-EVT-002: Payment Completed Event**
- Published after successful payment
- Includes: payment_id, user_id, amount, payment_method
- Triggers billing records, notifications

**BR-EVT-003: Payment Failed Event**
- Published after payment failure
- Includes: payment_id, user_id, error_message, error_code
- Enables failure notifications

**BR-EVT-004: Payment Refunded Event**
- Published after successful refund
- Includes: refund_id, payment_id, user_id, amount
- Triggers balance updates, notifications

**BR-EVT-005: Subscription Created Event**
- Published after new subscription
- Includes: subscription_id, user_id, plan_id, status
- Triggers tier updates, welcome emails

**BR-EVT-006: Subscription Updated Event**
- Published after subscription change
- Includes: subscription_id, plan_id, old_plan_id
- Triggers plan change notifications

**BR-EVT-007: Subscription Canceled Event**
- Published after cancellation
- Includes: subscription_id, user_id, reason
- Triggers churn tracking, confirmation

**BR-EVT-008: Invoice Created Event**
- Published after invoice generation
- Includes: invoice_id, user_id, amount_due
- Triggers invoice notifications

**BR-EVT-009: Invoice Paid Event**
- Published after invoice payment
- Includes: invoice_id, user_id, amount_paid
- Triggers payment confirmation

**BR-EVT-010: Event Failure Handling**
- Event publishing failures logged
- Do not block main operation
- Background retry mechanism

---

## State Machines (4 machines)

### Payment State Machine

```
States:
- PENDING: Payment initiated
- REQUIRES_ACTION: Customer action needed (3DS)
- PROCESSING: Payment being processed
- SUCCEEDED: Payment completed
- FAILED: Payment failed
- CANCELED: Payment canceled
- REFUNDED: Fully refunded
- PARTIAL_REFUND: Partially refunded

Transitions:
PENDING -> REQUIRES_ACTION (3DS required)
PENDING -> PROCESSING (confirmation started)
REQUIRES_ACTION -> PROCESSING (customer confirmed)
REQUIRES_ACTION -> CANCELED (timeout/cancel)
PROCESSING -> SUCCEEDED (payment successful)
PROCESSING -> FAILED (payment failed)
SUCCEEDED -> REFUNDED (full refund)
SUCCEEDED -> PARTIAL_REFUND (partial refund)

Terminal States:
- SUCCEEDED: Normal success (can transition to refunded)
- FAILED: Payment failure
- CANCELED: Payment canceled
- REFUNDED: Full refund complete
- PARTIAL_REFUND: Partial refund complete

Rules:
- PENDING is initial state
- REQUIRES_ACTION for 3DS verification
- Only SUCCEEDED can be refunded
```

### Subscription State Machine

```
States:
- TRIALING: In trial period
- ACTIVE: Active and paid
- PAST_DUE: Payment failed, grace period
- CANCELED: Subscription ended
- UNPAID: Payment failed, access restricted

Transitions:
TRIALING -> ACTIVE (trial ends, payment succeeds)
TRIALING -> CANCELED (user cancels during trial)
ACTIVE -> PAST_DUE (payment fails)
ACTIVE -> CANCELED (user cancels)
PAST_DUE -> ACTIVE (payment succeeds)
PAST_DUE -> UNPAID (grace period ends)
PAST_DUE -> CANCELED (admin cancels)
UNPAID -> ACTIVE (payment succeeds)
UNPAID -> CANCELED (final cancellation)

Terminal States:
- CANCELED: Subscription ended

Rules:
- TRIALING for new subscriptions with trial
- PAST_DUE allows recovery
- UNPAID restricts access
- CANCELED is final
```

### Invoice State Machine

```
States:
- DRAFT: Invoice being prepared
- OPEN: Invoice issued, awaiting payment
- PAID: Invoice fully paid
- VOID: Invoice canceled
- UNCOLLECTIBLE: Payment failed permanently

Transitions:
DRAFT -> OPEN (invoice finalized)
DRAFT -> VOID (invoice discarded)
OPEN -> PAID (payment succeeds)
OPEN -> VOID (invoice canceled)
OPEN -> UNCOLLECTIBLE (payment fails repeatedly)

Terminal States:
- PAID: Payment received
- VOID: Invoice canceled
- UNCOLLECTIBLE: Write-off

Rules:
- DRAFT for incomplete invoices
- OPEN is payable state
- Only OPEN can become PAID
```

### Refund State Machine

```
States:
- PENDING: Refund requested
- PROCESSING: Refund being processed
- SUCCEEDED: Refund completed
- FAILED: Refund failed
- CANCELED: Refund canceled

Transitions:
PENDING -> PROCESSING (processing starts)
PENDING -> CANCELED (request canceled)
PROCESSING -> SUCCEEDED (refund successful)
PROCESSING -> FAILED (refund failed)
FAILED -> PROCESSING (retry)

Terminal States:
- SUCCEEDED: Refund complete
- FAILED: Refund failed (can retry)
- CANCELED: Refund canceled

Rules:
- PENDING is initial state
- PROCESSING is transient
- FAILED can be retried
```

---

## Edge Cases (20 cases)

### EC-001: Concurrent Subscription Creation
- **Input**: Same user creates subscription twice simultaneously
- **Expected**: Only one subscription created
- **Actual**: Check for existing active subscription
- **Note**: Return error for duplicate attempt

### EC-002: Payment During Subscription Trial
- **Input**: User pays during trial period
- **Expected**: Trial continues, payment recorded
- **Actual**: Payment and trial independent
- **Note**: Early payment is valid

### EC-003: Trial Expiry Without Payment
- **Input**: Trial ends, no payment method
- **Expected**: Status changes to unpaid
- **Actual**: Webhook triggers status change
- **Note**: Grace period may apply

### EC-004: Partial Refund Multiple Times
- **Input**: Multiple partial refunds totaling > payment
- **Expected**: Reject refund exceeding remaining
- **Actual**: Track total refunded amount
- **Note**: Sum of refunds <= payment amount

### EC-005: Webhook Duplicate Delivery
- **Input**: Same Stripe event delivered twice
- **Expected**: Processed once, second ignored
- **Actual**: Event ID tracked for idempotency
- **Note**: Return 200 OK for both

### EC-006: Payment Intent Expiration
- **Input**: PaymentIntent not confirmed within timeout
- **Expected**: Status remains pending or cancels
- **Actual**: Stripe handles expiration
- **Note**: Client should retry with new intent

### EC-007: Subscription Plan Deactivation
- **Input**: Plan deactivated while user subscribed
- **Expected**: Existing subscriptions continue
- **Actual**: Plan change blocked
- **Note**: No new subscriptions allowed

### EC-008: Currency Conversion
- **Input**: Plan in USD, user wants EUR
- **Expected**: Convert at current rate
- **Actual**: Stripe handles currency
- **Note**: Display converted amount

### EC-009: Zero-Price Plan Subscription
- **Input**: Subscribe to free tier plan
- **Expected**: Subscription created, no payment
- **Actual**: Skip payment processing
- **Note**: Valid subscription without charge

### EC-010: Invoice for Zero Amount
- **Input**: Try to create invoice with amount = 0
- **Expected**: Rejected with validation error
- **Actual**: amount_due > 0 required
- **Note**: No-charge scenarios handled differently

### EC-011: Refund to Different Currency
- **Input**: Refund requested in different currency
- **Expected**: Refund in original payment currency
- **Actual**: Stripe refunds in original currency
- **Note**: Exchange rate may differ

### EC-012: Stripe API Timeout
- **Input**: Stripe API call times out
- **Expected**: Error returned, can retry
- **Actual**: Timeout after 10 seconds
- **Note**: Use exponential backoff

### EC-013: Account Service Unavailable
- **Input**: User validation call fails
- **Expected**: Fail-open, proceed with operation
- **Actual**: Log warning, continue
- **Note**: May need reconciliation later

### EC-014: Large Payment Amount
- **Input**: Amount = 999999.99
- **Expected**: Accepted if within limits
- **Actual**: Stripe handles large amounts
- **Note**: Currency limits apply

### EC-015: Subscription Update During Payment
- **Input**: Plan change while payment processing
- **Expected**: Conflict detected
- **Actual**: Lock subscription during payment
- **Note**: Retry after payment completes

### EC-016: Webhook Secret Rotation
- **Input**: Webhook secret changed, old events arrive
- **Expected**: Signature verification fails
- **Actual**: Return 400 Bad Request
- **Note**: Support multiple secrets during rotation

### EC-017: Refund After Account Deletion
- **Input**: User account deleted, refund requested
- **Expected**: Refund still processed
- **Actual**: Refund to original payment method
- **Note**: Refund independent of account status

### EC-018: Multiple Active Invoices
- **Input**: Create invoice while another is open
- **Expected**: Both invoices remain open
- **Actual**: Multiple open invoices allowed
- **Note**: Each paid independently

### EC-019: Payment Confirmation Timeout
- **Input**: Confirmation times out
- **Expected**: Payment remains pending
- **Actual**: Client retries confirmation
- **Note**: Webhook provides final status

### EC-020: Stripe Test Mode vs Live
- **Input**: Production with test keys
- **Expected**: Operations work in test mode
- **Actual**: Test payments not real
- **Note**: Environment-specific configuration

---

## Data Consistency Rules

### DC-001: Payment ID Uniqueness
- payment_id is primary key
- Enforced at database level
- Uses Stripe PaymentIntent ID format

### DC-002: Subscription ID Uniqueness
- subscription_id is primary key
- UUID generation ensures uniqueness
- Linked to Stripe subscription if applicable

### DC-003: Invoice Number Uniqueness
- invoice_number is unique
- Sequential within date
- Cannot be reused

### DC-004: Refund-Payment Relationship
- refund.payment_id references transactions.payment_id
- One payment can have multiple refunds
- Total refunds <= payment amount

### DC-005: Amount Consistency
- Invoice: amount_due = amount_total - amount_paid
- Refund: amount <= payment.amount - total_refunded
- Verified at operation time

### DC-006: Status Consistency
- Status transitions follow state machines
- Invalid transitions rejected
- Timestamp updated on transition

---

## Integration Contracts

### Account Service Integration
- **Endpoint**: GET /api/v1/accounts/{user_id}
- **When**: Subscription creation, payment creation
- **Expected Response**: 200 with user profile OR 404
- **Error Handling**: Fail-open - proceed with operation

### Wallet Service Integration
- **Endpoint**: POST /api/v1/wallets/{user_id}/add
- **When**: Payment completion (optional)
- **Expected Response**: 200 with balance updated
- **Error Handling**: Log and continue

### Billing Service Integration
- **Endpoint**: POST /api/v1/billing/usage/record
- **When**: Payment completion
- **Expected Response**: 200 billing record created
- **Error Handling**: Log and continue

### Stripe API Integration
- **Operations**: PaymentIntent, Subscription, Refund, Customer
- **When**: All payment operations
- **Expected Response**: Stripe API responses
- **Error Handling**: Retry with backoff, return error

### Event Bus Integration
- **Events**: payment.*, subscription.*, invoice.*
- **When**: All state changes
- **Expected Response**: Event published
- **Error Handling**: Log failure, don't block

---

## Error Handling Contracts

### Subscription Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 400 | "user_id cannot be empty" |
| Missing plan_id | 400 | "plan_id cannot be empty" |
| User not found | 400 | "User does not exist" |
| Plan not found | 404 | "Subscription plan not found" |
| Plan inactive | 400 | "Plan is not active" |
| Active subscription exists | 400 | "User already has active subscription" |
| Subscription not found | 404 | "Subscription not found" |

### Payment Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 400 | "user_id cannot be empty" |
| User not found | 400 | "User does not exist" |
| Invalid amount | 422 | "amount must be greater than 0" |
| Invalid currency | 400 | "currency must be one of: USD, EUR, GBP, CNY" |
| Payment not found | 404 | "Payment not found" |
| Stripe error | 500 | "Payment processing failed: {stripe_error}" |

### Refund Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing payment_id | 400 | "payment_id cannot be empty" |
| Payment not found | 400 | "Payment not found" |
| Payment not succeeded | 400 | "Payment not eligible for refund" |
| Amount exceeds payment | 400 | "Refund amount exceeds payment amount" |
| Stripe refund error | 500 | "Refund processing failed: {stripe_error}" |

### Invoice Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Invoice not found | 404 | "Invoice not found" |
| Invoice not open | 400 | "Invoice is not open for payment" |
| Amount invalid | 422 | "amount_due must be greater than 0" |

### Webhook Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Invalid signature | 400 | "Invalid webhook signature" |
| Missing signature | 400 | "Stripe-Signature header missing" |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Payment Service Team
