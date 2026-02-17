# Subscription Service - Logic Contract

## Overview

This document defines the business rules, state machines, edge cases, and integration contracts for the Subscription Service.

---

## Business Rules (50 rules)

### Subscription Creation Rules (BR-CRE-001 to BR-CRE-012)

**BR-CRE-001: User ID Required**
- user_id MUST be non-empty string
- System validates before processing
- Error returned if empty: "user_id cannot be empty"

**BR-CRE-002: Tier Code Validation**
- tier_code MUST be one of: free, pro, max, team, enterprise
- Case-insensitive matching (normalized to lowercase)
- Error returned if invalid: "Tier '{tier_code}' not found"

**BR-CRE-003: One Active Subscription Per Context**
- User can have only ONE active subscription per org context
- Individual (org_id=null) is separate from org subscriptions
- Error returned if duplicate: "User already has an active subscription"

**BR-CRE-004: Default Billing Cycle**
- If billing_cycle not specified, defaults to MONTHLY
- Valid values: monthly, quarterly, yearly

**BR-CRE-005: Seats Validation**
- seats MUST be >= 1 and <= 1000
- Default value is 1
- Only meaningful for team/enterprise tiers

**BR-CRE-006: Trial Eligibility**
- Trial only available on paid tiers (pro, max, team, enterprise)
- Free tier has 0 trial days
- Trial can be skipped by setting use_trial=false

**BR-CRE-007: Credit Allocation Calculation**
- Monthly: tier.monthly_credits
- Quarterly: tier.monthly_credits * 3
- Yearly: tier.monthly_credits * 12

**BR-CRE-008: Team Tier Credit Scaling**
- For team tier: credits = monthly_credits * seats
- Price also scales: price = price_per_seat * seats

**BR-CRE-009: Period Calculation**
- Monthly: 30 days from creation
- Quarterly: 90 days from creation
- Yearly: 365 days from creation

**BR-CRE-010: Trial Period Calculation**
- Trial end = creation + tier.trial_days
- Next billing date = trial_end (for trial subscriptions)
- Status = TRIALING during trial

**BR-CRE-011: Price Calculation**
- Monthly: tier.monthly_price_usd
- Quarterly: monthly * 3 * 0.9 (10% discount)
- Yearly: monthly * 12 * 0.8 (20% discount)

**BR-CRE-012: History Recording**
- Every creation MUST record history entry
- Action: CREATED or TRIAL_STARTED
- initiated_by: USER

---

### Credit Consumption Rules (BR-CON-001 to BR-CON-010)

**BR-CON-001: Active Subscription Required**
- User MUST have active subscription to consume credits
- Error: "No active subscription found" (HTTP 404)

**BR-CON-002: Sufficient Credits Required**
- credits_remaining MUST be >= credits_to_consume
- Error: "Insufficient credits. Available: X, Requested: Y" (HTTP 402)

**BR-CON-003: Positive Credits Amount**
- credits_to_consume MUST be > 0
- Maximum: 1,000,000,000 credits per request
- Error for invalid: Pydantic validation error (HTTP 422)

**BR-CON-004: Service Type Required**
- service_type MUST be non-empty string
- Used for usage tracking and analytics

**BR-CON-005: Atomic Deduction**
- Credit deduction MUST be atomic (no partial consumption)
- Use database transaction to prevent race conditions

**BR-CON-006: Balance Update**
- credits_used += credits_to_consume
- credits_remaining -= credits_to_consume
- Both fields updated atomically

**BR-CON-007: History Recording**
- Every consumption MUST record history entry
- Action: CREDITS_CONSUMED
- credits_change: negative value
- credits_balance_after: new remaining balance

**BR-CON-008: Idempotency Support**
- usage_record_id enables idempotent consumption
- Duplicate requests with same ID should be rejected
- Prevents double-charging

**BR-CON-009: Event Publishing**
- credits.consumed event published after successful consumption
- Includes: subscription_id, user_id, credits_consumed, credits_remaining, service_type

**BR-CON-010: Organization Context**
- If organization_id provided, check org subscription
- User can consume from org subscription if member

---

### Subscription Cancellation Rules (BR-CAN-001 to BR-CAN-008)

**BR-CAN-001: Subscription Must Exist**
- subscription_id MUST reference existing subscription
- Error: "Subscription {id} not found" (HTTP 404)

**BR-CAN-002: Ownership Validation**
- Only subscription owner can cancel
- Validate: subscription.user_id == request.user_id
- Error: "Not authorized to cancel this subscription" (HTTP 403)

**BR-CAN-003: Immediate vs End-of-Period**
- immediate=true: Cancel now, status -> CANCELED
- immediate=false: Cancel at period end, cancel_at_period_end=true

**BR-CAN-004: Effective Date Calculation**
- Immediate: effective_date = now
- End-of-period: effective_date = current_period_end

**BR-CAN-005: Auto-Renew Disabled**
- Cancellation MUST set auto_renew = false
- Prevents automatic renewal at period end

**BR-CAN-006: Cancellation Timestamp**
- canceled_at MUST be set to current timestamp
- Records when cancellation was requested

**BR-CAN-007: Reason Recording**
- cancellation_reason stored if provided
- Used for analytics and improvement

**BR-CAN-008: History Recording**
- Action: CANCELED
- Records previous_status, new_status
- Records credits_balance_after

---

### Credit Balance Rules (BR-BAL-001 to BR-BAL-005)

**BR-BAL-001: User ID Required**
- user_id MUST be provided in query
- Returns balance for specified user

**BR-BAL-002: No Subscription Handling**
- If no active subscription found:
- subscription_credits_remaining = 0
- subscription_credits_total = 0
- total_credits_available = 0

**BR-BAL-003: Balance Response Fields**
- subscription_credits_remaining: current remaining
- subscription_credits_total: allocated for period
- subscription_period_end: when credits expire
- tier_code and tier_name included

**BR-BAL-004: Organization Context**
- If organization_id provided, check org subscription
- User may have both individual and org subscriptions

**BR-BAL-005: Read-Only Operation**
- Balance query does not modify any data
- No events published

---

### Tier Rules (BR-TIR-001 to BR-TIR-007)

**BR-TIR-001: Free Tier**
- monthly_price_usd: 0
- monthly_credits: 1,000,000
- credit_rollover: false
- trial_days: 0

**BR-TIR-002: Pro Tier**
- monthly_price_usd: 20
- monthly_credits: 30,000,000
- credit_rollover: true (max 50%)
- trial_days: 14

**BR-TIR-003: Max Tier**
- monthly_price_usd: 50
- monthly_credits: 100,000,000
- credit_rollover: true (max 50%)
- trial_days: 14

**BR-TIR-004: Team Tier**
- monthly_price_usd: 25 per seat
- monthly_credits: 50,000,000 per seat
- credit_rollover: true (max 50%)
- trial_days: 14

**BR-TIR-005: Enterprise Tier**
- monthly_price_usd: custom
- monthly_credits: custom
- credit_rollover: true (unlimited)
- trial_days: 30

**BR-TIR-006: Tier Caching**
- Tier definitions cached in memory
- Loaded at service startup
- No database query for validation

**BR-TIR-007: Tier Immutability**
- Existing subscriptions keep their tier rates
- Tier changes only affect new subscriptions

---

### History Rules (BR-HST-001 to BR-HST-005)

**BR-HST-001: Immutable Records**
- History entries cannot be modified after creation
- Provides audit trail integrity

**BR-HST-002: Pagination**
- Default page_size: 50
- Maximum page_size: 100
- Minimum page: 1

**BR-HST-003: Sort Order**
- Sorted by created_at descending (newest first)

**BR-HST-004: Credit Change Tracking**
- Positive credits_change: credits added
- Negative credits_change: credits consumed/deducted
- credits_balance_after: balance after change

**BR-HST-005: Initiator Tracking**
- initiated_by: USER, SYSTEM, ADMIN, PAYMENT_PROVIDER
- Identifies who triggered the action

---

### Renewal Rules (BR-REN-001 to BR-REN-003)

**BR-REN-001: Auto-Renewal Check**
- Only subscriptions with auto_renew=true are renewed
- checked at period end

**BR-REN-002: Rollover Calculation**
- rollover = min(credits_remaining, max_rollover_credits)
- max_rollover_credits = 50% of monthly_credits (for paid tiers)
- Free tier: no rollover

**BR-REN-003: New Period Credits**
- credits_allocated = tier.monthly_credits + rollover
- credits_remaining = credits_allocated
- credits_rolled_over = rollover amount

---

## State Machines (3 machines)

### Subscription Lifecycle State Machine

```
States:
- CREATED (implicit, transitions immediately)
- TRIALING: In trial period
- ACTIVE: Paid, operational subscription
- PAST_DUE: Payment failed, grace period
- PAUSED: Temporarily suspended
- CANCELED: Marked for cancellation
- EXPIRED: Subscription ended

Transitions:
CREATED -> TRIALING (if use_trial=true)
CREATED -> ACTIVE (if use_trial=false)
TRIALING -> ACTIVE (trial ends, payment succeeds)
TRIALING -> EXPIRED (trial ends, no payment method)
ACTIVE -> PAST_DUE (payment fails)
ACTIVE -> PAUSED (user pauses)
ACTIVE -> CANCELED (user cancels, immediate=false)
ACTIVE -> EXPIRED (user cancels, immediate=true)
PAST_DUE -> ACTIVE (payment succeeds)
PAST_DUE -> EXPIRED (grace period ends)
PAUSED -> ACTIVE (user resumes)
PAUSED -> EXPIRED (pause timeout)
CANCELED -> EXPIRED (period ends)

Terminal States:
- EXPIRED (no further transitions)

Rules:
- EXPIRED subscriptions cannot be reactivated
- Only ACTIVE/TRIALING can consume credits
- PAUSED freezes credit expiration
```

### Credit Balance State Machine

```
States:
- FULL: credits_remaining == credits_allocated
- PARTIAL: 0 < credits_remaining < credits_allocated
- LOW: credits_remaining < 10% of credits_allocated
- DEPLETED: credits_remaining == 0

Transitions:
FULL -> PARTIAL (credits consumed)
PARTIAL -> LOW (threshold crossed)
PARTIAL -> DEPLETED (all consumed)
LOW -> DEPLETED (all consumed)
DEPLETED -> FULL (new period/renewal)
ANY -> FULL (credits allocated)

Events:
- FULL -> PARTIAL: credits.consumed
- PARTIAL -> LOW: credits.low_balance (notification)
- ANY -> DEPLETED: credits.depleted (notification)
```

### Cancellation State Machine

```
States:
- NOT_CANCELED: Normal subscription
- PENDING_CANCEL: cancel_at_period_end=true
- CANCELED: Immediate cancellation

Transitions:
NOT_CANCELED -> PENDING_CANCEL (immediate=false)
NOT_CANCELED -> CANCELED (immediate=true)
PENDING_CANCEL -> CANCELED (period ends)

Rules:
- PENDING_CANCEL still allows credit consumption
- PENDING_CANCEL shows effective_date in future
- CANCELED terminates access immediately
```

---

## Edge Cases (15 cases)

### EC-001: Duplicate Subscription Creation
- Input: Create subscription for user with existing active subscription
- Expected: Error "User already has an active subscription"
- HTTP: 409 Conflict or in response success=false

### EC-002: Consume More Than Available
- Input: credits_to_consume > credits_remaining
- Expected: Error "Insufficient credits"
- HTTP: 402 Payment Required

### EC-003: Cancel Non-Existent Subscription
- Input: Cancel with invalid subscription_id
- Expected: Error "Subscription not found"
- HTTP: 404 Not Found

### EC-004: Cancel Someone Else's Subscription
- Input: Cancel subscription owned by different user
- Expected: Error "Not authorized to cancel"
- HTTP: 403 Forbidden

### EC-005: Balance Query Without Subscription
- Input: Get balance for user with no subscription
- Expected: Success with all credit fields = 0

### EC-006: Create With Invalid Tier
- Input: tier_code = "platinum" (not valid)
- Expected: Error "Tier 'platinum' not found"
- HTTP: 404 Not Found

### EC-007: Concurrent Credit Consumption
- Input: Two simultaneous consume requests
- Expected: Both succeed if sufficient credits, or one fails
- Handling: Atomic database operations

### EC-008: Zero Credits Consumption
- Input: credits_to_consume = 0
- Expected: Validation error (must be > 0)
- HTTP: 422 Unprocessable Entity

### EC-009: Negative Credits Consumption
- Input: credits_to_consume = -1000
- Expected: Validation error (must be > 0)
- HTTP: 422 Unprocessable Entity

### EC-010: Empty User ID
- Input: user_id = "" or whitespace
- Expected: Validation error
- HTTP: 422 Unprocessable Entity

### EC-011: Create Team Subscription Without Org
- Input: tier_code = "team", organization_id = null
- Expected: Success (individual team subscription)
- Note: Unusual but allowed

### EC-012: History for Non-Existent Subscription
- Input: Get history with invalid subscription_id
- Expected: Empty history list (not error)

### EC-013: Consume from PAUSED Subscription
- Input: Consume credits while subscription is PAUSED
- Expected: Error or success based on business decision
- Current: Treated as no active subscription

### EC-014: Cancel Already Canceled Subscription
- Input: Cancel subscription that's already CANCELED
- Expected: Success (idempotent) or error
- Current: Returns current state

### EC-015: Create Subscription During Trial End
- Input: Trial ends while creating new subscription
- Expected: Proper transaction handling
- Handling: Database transaction isolation

---

## Data Consistency Rules

### DC-001: Credit Balance Consistency
- credits_remaining = credits_allocated - credits_used + credits_rolled_over
- System maintains this invariant

### DC-002: Status Consistency
- status reflects actual subscription state
- cancel_at_period_end only true if status allows

### DC-003: Period Date Consistency
- current_period_end > current_period_start
- next_billing_date == current_period_end (for active subscriptions)

### DC-004: Trial Date Consistency
- If is_trial=true: trial_start and trial_end must be set
- trial_end > trial_start

### DC-005: History Consistency
- Sum of credits_change in history equals credits_used
- Each history entry has valid subscription_id

---

## Integration Contracts

### Payment Service Integration
- **Endpoint**: Payment Service API
- **When**: Subscription renewal, upgrade payment
- **Expected Response**: Payment success/failure
- **Error Handling**: Set PAST_DUE on failure, retry policy

### Account Service Integration
- **Endpoint**: GET /api/v1/accounts/{user_id}
- **When**: Validate user exists (optional)
- **Expected Response**: Account data or 404
- **Error Handling**: Proceed without validation if unavailable

### Notification Service Integration
- **Via**: NATS events
- **Events Published**:
  - subscription.created
  - subscription.canceled
  - credits.consumed
  - credits.low_balance
- **Error Handling**: Log and continue if NATS unavailable

### Billing Service Integration
- **Via**: NATS events
- **Events Published**: subscription.created, subscription.canceled
- **Purpose**: Invoice generation, billing records

---

## Error Handling Contracts

### Validation Errors
- Invalid request parameters -> 422 Unprocessable Entity
- Response includes field-level error details

### Business Logic Errors
- Insufficient credits -> 402 Payment Required
- Subscription not found -> 404 Not Found
- Not authorized -> 403 Forbidden
- Duplicate subscription -> 409 Conflict (or success=false)

### System Errors
- Database connection failure -> 500 Internal Server Error
- Event bus unavailable -> Log warning, continue operation
- External service unavailable -> Graceful degradation

### Error Response Format
```json
{
  "success": false,
  "error": "Human readable error message",
  "error_code": "INSUFFICIENT_CREDITS",
  "details": {
    "available": 5000,
    "requested": 10000
  }
}
```

---

## Performance Contracts

### Response Time SLAs
- GET /health: < 10ms p99
- GET /api/v1/subscriptions/credits/balance: < 50ms p99
- POST /api/v1/subscriptions/credits/consume: < 50ms p99
- POST /api/v1/subscriptions: < 200ms p99
- GET /api/v1/subscriptions: < 100ms p99

### Throughput Requirements
- Credit consumption: 10,000 requests/second
- Subscription creation: 1,000 requests/second
- Balance queries: 50,000 requests/second

---

**Document Statistics**:
- Lines: ~750
- Business Rules: 50
- State Machines: 3
- Edge Cases: 15
- Integration Contracts: 4
