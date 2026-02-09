# Subscription Service - Domain Context

## Overview

The Subscription Service is the **monetization engine** for the isA_user platform. It manages subscription lifecycles, credit allocation, consumption tracking, and tier management. Every billable action in the system passes through this service for credit validation and deduction.

**Business Context**: Enable flexible, credit-based subscription management that supports individual users and organizations with tiered pricing, trial periods, and usage-based billing through a unified credit system.

**Core Value Proposition**: Transform complex subscription and billing logic into a simple credit-based system where 1 Credit = $0.00001 USD, enabling precise usage tracking and fair billing across all platform services.

---

## Business Taxonomy

### Core Entities

#### 1. User Subscription
**Definition**: A contractual agreement between a user/organization and the platform for access to services at a specific tier level.

**Business Purpose**:
- Establish service access rights for users
- Track subscription lifecycle (creation, activation, renewal, cancellation)
- Manage credit allocation and consumption
- Support multiple billing cycles and tier upgrades/downgrades

**Key Attributes**:
- Subscription ID (unique identifier)
- User ID (owner of the subscription)
- Organization ID (optional, for team/enterprise)
- Tier Code (free, pro, max, team, enterprise)
- Status (active, trialing, past_due, canceled, paused, expired)
- Billing Cycle (monthly, yearly, quarterly)
- Credits Allocated/Used/Remaining
- Current Period Start/End
- Auto Renew Flag

**Subscription States**:
- **Active**: Normal operational state, user can consume credits
- **Trialing**: Trial period, full access but no charge yet
- **Past Due**: Payment overdue, service may be limited
- **Canceled**: User canceled, may still be active until period end
- **Paused**: Temporarily paused by user or system
- **Expired**: Subscription period ended, no renewal

#### 2. Subscription Tier
**Definition**: A predefined service level with specific credit allocation, pricing, and features.

**Business Purpose**:
- Define service packages with clear value propositions
- Enable tiered pricing strategy
- Support upgrade/downgrade paths
- Manage feature access control

**Available Tiers**:
| Tier | Monthly Price | Monthly Credits | Rollover | Trial Days |
|------|---------------|-----------------|----------|------------|
| Free | $0 | 1,000,000 | No | 0 |
| Pro | $20 | 30,000,000 | Yes (50%) | 14 |
| Max | $50 | 100,000,000 | Yes (50%) | 14 |
| Team | $25/seat | 50,000,000/seat | Yes (50%) | 14 |
| Enterprise | Custom | Custom | Yes | 30 |

#### 3. Credits
**Definition**: The platform's universal currency for measuring and billing service usage.

**Business Purpose**:
- Provide unified billing across diverse services
- Enable precise usage tracking
- Support fair-use policies
- Allow flexible credit allocation and consumption

**Credit System**:
- 1 Credit = $0.00001 USD
- $1 USD = 100,000 Credits
- All platform services consume credits based on usage
- Credits are allocated per billing period
- Rollover rules apply based on tier

**Credit Types**:
- **Subscription Credits**: Allocated from subscription tier
- **Rollover Credits**: Carried over from previous period
- **Bonus Credits**: Promotional or reward credits

#### 4. Subscription History
**Definition**: An audit trail of all actions and changes to a subscription.

**Business Purpose**:
- Maintain complete audit trail for compliance
- Track subscription changes over time
- Support dispute resolution
- Enable usage analytics and reporting

**Key Actions Tracked**:
- Created, Upgraded, Downgraded, Renewed
- Canceled, Paused, Resumed, Expired
- Credits Allocated, Consumed, Refunded, Rolled Over
- Trial Started, Trial Ended
- Payment Failed, Payment Succeeded

---

## Domain Scenarios

### Scenario 1: New User Subscription Creation
**Trigger**: User selects a subscription tier and completes payment setup

**Flow**:
1. Validate tier code exists and is available
2. Check for existing active subscription
3. Calculate initial credit allocation based on tier and billing cycle
4. Apply trial period if eligible and requested
5. Create subscription record with initial credits
6. Record history entry (CREATED or TRIAL_STARTED)
7. Publish subscription.created event

**Outcome**: User has active subscription with allocated credits

**Events**: `subscription.created`

### Scenario 2: Credit Consumption
**Trigger**: Platform service requests credit deduction for usage

**Flow**:
1. Receive consumption request with user ID and credits amount
2. Lookup user's active subscription
3. Validate sufficient credits available
4. Deduct credits from subscription balance
5. Record history entry (CREDITS_CONSUMED)
6. Publish credits.consumed event

**Outcome**: Credits deducted, remaining balance updated

**Events**: `credits.consumed`

### Scenario 3: Subscription Cancellation
**Trigger**: User requests subscription cancellation

**Flow**:
1. Validate subscription exists and user owns it
2. Determine cancellation type (immediate vs. end of period)
3. Update subscription status and cancellation fields
4. Record history entry (CANCELED)
5. Publish subscription.canceled event
6. If immediate, calculate refund eligibility

**Outcome**: Subscription marked for cancellation or canceled immediately

**Events**: `subscription.canceled`

### Scenario 4: Subscription Renewal
**Trigger**: Current billing period ends and auto_renew is true

**Flow**:
1. Check subscription is active and auto_renew enabled
2. Validate payment method is valid
3. Process payment for next period
4. Calculate rollover credits if applicable
5. Allocate new period credits
6. Update period start/end dates
7. Record history entry (RENEWED)
8. Publish subscription.renewed event

**Outcome**: New billing period started with fresh credits

**Events**: `subscription.renewed`, `credits.allocated`

### Scenario 5: Tier Upgrade
**Trigger**: User requests upgrade to higher tier

**Flow**:
1. Validate new tier is higher than current
2. Calculate prorated price difference
3. Process additional payment
4. Update tier code and credit allocation
5. Record history entry (UPGRADED)
6. Publish subscription.upgraded event

**Outcome**: User on new tier with additional credits

**Events**: `subscription.upgraded`

### Scenario 6: Trial Period End
**Trigger**: Trial end date reached

**Flow**:
1. Check subscription is in trialing status
2. If payment method exists, convert to active
3. If no payment method, prompt user or expire
4. Record history entry (TRIAL_ENDED)
5. Publish subscription.trial_ended event

**Outcome**: Subscription converted to active or expired

**Events**: `subscription.trial_ended`

---

## Domain Events

### 1. subscription.created (EventType.SUBSCRIPTION_CREATED)
**When**: New subscription is created
**Data**:
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "organization_id": null,
  "tier_code": "pro",
  "credits_allocated": 30000000,
  "is_trial": false
}
```
**Consumers**: Billing Service, Notification Service, Analytics Service

### 2. subscription.canceled (EventType.SUBSCRIPTION_CANCELED)
**When**: Subscription is canceled
**Data**:
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "immediate": false,
  "effective_date": "2025-01-31T23:59:59Z"
}
```
**Consumers**: Billing Service, Notification Service

### 3. credits.consumed (EventType.CREDITS_CONSUMED)
**When**: Credits are consumed from subscription
**Data**:
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "credits_consumed": 5000,
  "credits_remaining": 29995000,
  "service_type": "model_inference",
  "usage_record_id": "usage_xyz"
}
```
**Consumers**: Analytics Service, Usage Tracking

### 4. subscription.renewed (EventType.SUBSCRIPTION_RENEWED)
**When**: Subscription is renewed for new period
**Data**:
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "new_period_start": "2025-02-01T00:00:00Z",
  "new_period_end": "2025-02-28T23:59:59Z",
  "credits_allocated": 30000000,
  "credits_rolled_over": 5000000
}
```
**Consumers**: Billing Service, Notification Service

### 5. subscription.upgraded (EventType.SUBSCRIPTION_UPGRADED)
**When**: Subscription tier is upgraded
**Data**:
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "previous_tier": "pro",
  "new_tier": "max",
  "additional_credits": 70000000
}
```
**Consumers**: Billing Service, Feature Service

### 6. credits.low_balance (EventType.CREDITS_LOW_BALANCE)
**When**: Credit balance falls below threshold (e.g., 10%)
**Data**:
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "credits_remaining": 2500000,
  "threshold_percentage": 10
}
```
**Consumers**: Notification Service

---

## Core Concepts

### Concept 1: Credit-Based Billing
The platform uses a universal credit system for all service billing. This enables:
- **Unified Pricing**: All services priced in credits
- **Transparent Usage**: Users see exact credit consumption
- **Flexible Allocation**: Credits can be allocated, consumed, refunded
- **Fair Billing**: Usage-based, not time-based

### Concept 2: Subscription Lifecycle
Subscriptions follow a defined lifecycle:
```
CREATED -> [TRIALING] -> ACTIVE -> [PAUSED] -> CANCELED/EXPIRED
```
- Transitions are tracked in history
- State determines available actions
- Auto-renewal manages continuation

### Concept 3: Credit Rollover
Unused credits may roll over to the next period:
- Only available on paid tiers (Pro, Max, Team, Enterprise)
- Maximum rollover is 50% of monthly allocation
- Rollover credits expire after one period if unused
- Free tier has no rollover

### Concept 4: Multi-Tenant Subscriptions
Subscriptions can be:
- **Individual**: Owned by single user
- **Organization**: Shared across team members
- Team subscriptions support multiple seats
- Organization ID links subscription to org context

---

## High-Level Business Rules (35 rules)

### Subscription Lifecycle Rules (BR-SUB-001 to BR-SUB-010)

**BR-SUB-001: One Active Subscription Per Context**
- A user can have only one active subscription per organization context
- Individual subscription (organization_id = null) is separate from org subscriptions
- System validates before creating new subscription

**BR-SUB-002: Tier Validation Required**
- All tier_code values must match predefined tiers
- Invalid tier codes result in TierNotFoundError
- System caches tier definitions for performance

**BR-SUB-003: Trial Period Eligibility**
- Trial is only available on first subscription
- Trial duration determined by tier (0-30 days)
- Trial can be skipped if user prefers

**BR-SUB-004: Cancellation Preserves Access**
- Default cancellation is at period end
- User retains access until effective_date
- Immediate cancellation terminates access now

**BR-SUB-005: Auto-Renewal Default**
- All subscriptions default to auto_renew = true
- User can disable auto-renewal anytime
- System processes renewal at period end

**BR-SUB-006: Status Transitions**
- CREATED can become TRIALING or ACTIVE
- TRIALING can become ACTIVE or EXPIRED
- ACTIVE can become CANCELED, PAUSED, or EXPIRED
- CANCELED and EXPIRED are terminal states

**BR-SUB-007: Subscription Ownership**
- Only subscription owner can cancel
- Owner is identified by user_id match
- Organization admins can manage org subscriptions

**BR-SUB-008: Period Dates Required**
- current_period_start and current_period_end are mandatory
- Period end determines next billing date
- Period dates must be in UTC timezone

**BR-SUB-009: Paused Subscriptions**
- Pausing freezes credit consumption
- Credits do not expire during pause
- Maximum pause duration: 90 days

**BR-SUB-010: Expired Cleanup**
- Expired subscriptions retained for 30 days
- After 30 days, marked for archival
- History records preserved indefinitely

### Credit Management Rules (BR-CRD-001 to BR-CRD-010)

**BR-CRD-001: Credit Unit Definition**
- 1 Credit = $0.00001 USD (fixed rate)
- Minimum consumption: 1 credit
- Maximum single consumption: 1,000,000,000 credits

**BR-CRD-002: Insufficient Credits Blocking**
- Consumption fails if credits_remaining < credits_to_consume
- System returns InsufficientCreditsError
- No partial consumption allowed

**BR-CRD-003: Credit Allocation Timing**
- Credits allocated at subscription creation
- Credits reallocated at period renewal
- Rollover calculated before new allocation

**BR-CRD-004: Rollover Calculation**
- Rollover = min(credits_remaining, max_rollover_credits)
- max_rollover_credits = 50% of monthly allocation
- Free tier: max_rollover_credits = 0

**BR-CRD-005: Credit Consumption Tracking**
- Every consumption creates history entry
- service_type and usage_record_id tracked
- Enables detailed usage analytics

**BR-CRD-006: Credit Balance Query**
- Balance query returns current state
- Includes subscription and tier info
- No active subscription returns zero balance

**BR-CRD-007: Credits Non-Transferable**
- Credits cannot be transferred between users
- Credits cannot be converted to cash
- Credits expire at subscription end (unless rolled over)

**BR-CRD-008: Consumption Idempotency**
- usage_record_id enables idempotent consumption
- Duplicate requests with same ID are rejected
- Prevents double-charging

**BR-CRD-009: Low Balance Threshold**
- Alert when balance falls below 10%
- Configurable threshold per tier
- Triggers notification event

**BR-CRD-010: Refund Credits**
- Refunds add credits back to balance
- Refund reason required in history
- Cannot exceed original consumption amount

### Billing Cycle Rules (BR-BIL-001 to BR-BIL-010)

**BR-BIL-001: Supported Cycles**
- MONTHLY: 30 days
- QUARTERLY: 90 days (10% discount)
- YEARLY: 365 days (20% discount)

**BR-BIL-002: Price Calculation**
- Monthly base price from tier definition
- Quarterly = monthly * 3 * 0.9
- Yearly = monthly * 12 * 0.8

**BR-BIL-003: Credit Scaling**
- Monthly credits from tier definition
- Quarterly = monthly * 3
- Yearly = monthly * 12

**BR-BIL-004: Team Seat Pricing**
- Team tier: price_per_seat * seats
- Credits scaled by seat count
- Minimum 1 seat required

**BR-BIL-005: Proration on Upgrade**
- Upgrade prorates remaining days
- User pays difference for current period
- Full price from next period

**BR-BIL-006: No Proration on Downgrade**
- Downgrade takes effect at period end
- User keeps current tier until then
- No refund for remaining period

**BR-BIL-007: Currency Support**
- Default currency: USD
- All prices stored in USD
- External conversion for display only

**BR-BIL-008: Trial Pricing**
- Trial period: price_paid = 0
- Full price charged after trial
- Trial does not affect tier pricing

**BR-BIL-009: Payment Method Requirement**
- Required for paid tiers
- Optional during trial
- Must be valid before renewal

**BR-BIL-010: Billing Date Management**
- next_billing_date = current_period_end
- Updated on each renewal
- Null when auto_renew = false

### History and Audit Rules (BR-HST-001 to BR-HST-005)

**BR-HST-001: All Actions Logged**
- Every subscription change creates history entry
- History records are immutable
- Includes who initiated (user, system, admin)

**BR-HST-002: Credit Changes Tracked**
- credits_change positive for allocations
- credits_change negative for consumptions
- credits_balance_after shows resulting balance

**BR-HST-003: State Transitions Recorded**
- previous_status and new_status captured
- previous_tier_code and new_tier_code for tier changes
- Enables full state reconstruction

**BR-HST-004: Metadata Support**
- Each history entry can include metadata
- Stores service-specific details
- JSON format for flexibility

**BR-HST-005: History Pagination**
- Default page_size: 50
- Maximum page_size: 100
- Sorted by created_at descending

---

## Integration Points

### Upstream Services (Consumed by Subscription Service)
- **Product Service**: Tier definitions and pricing
- **Payment Service**: Payment processing and methods
- **Account Service**: User validation

### Downstream Services (Consume from Subscription Service)
- **All Platform Services**: Credit validation and consumption
- **Billing Service**: Invoice generation
- **Notification Service**: Alerts and reminders
- **Analytics Service**: Usage tracking
- **Feature Service**: Tier-based feature access

---

## Error Scenarios

### SubscriptionNotFoundError
- Subscription ID does not exist
- HTTP 404 returned

### SubscriptionValidationError
- Invalid request parameters
- Unauthorized action (not owner)
- HTTP 400 or 403 returned

### InsufficientCreditsError
- Not enough credits for consumption
- HTTP 402 Payment Required returned

### TierNotFoundError
- Invalid tier_code specified
- HTTP 404 returned

### SubscriptionServiceError
- Internal service errors
- Database connection issues
- HTTP 500 returned

---

**Document Statistics**:
- Lines: ~530
- Business Rules: 35
- Domain Scenarios: 6
- Domain Events: 6
