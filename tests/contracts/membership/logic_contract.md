# Membership Service - Logic Contract

## Overview

This document defines the business rules, state machines, edge cases, and integration contracts for the Membership Service.

---

## Business Rules (50 rules)

### Enrollment Rules (BR-ENR-001 to BR-ENR-012)

**BR-ENR-001: User ID Required**
- user_id MUST be non-empty string
- System validates before processing
- Error returned if empty: "user_id cannot be empty"

**BR-ENR-002: One Active Membership Per User**
- User can have only ONE active/pending membership
- Individual (org_id=null) is separate from org memberships
- Error returned if duplicate: "User already has active membership"

**BR-ENR-003: Initial Tier Assignment**
- New memberships ALWAYS start at Bronze tier
- No tier skipping on initial enrollment
- Tier upgrades earned through activity only

**BR-ENR-004: Enrollment Bonus Configuration**
- Enrollment bonus determined by promo_code
- Default bonus: 0 points if no promo code
- Bonus points count toward points_balance only (not tier_points)

**BR-ENR-005: Membership ID Format**
- Format: mem_{uuid_hex_16}
- Example: mem_abc123def456gh78
- System-generated, immutable

**BR-ENR-006: Enrollment Source Tracking**
- enrollment_source captured for analytics
- Valid sources: web_signup, mobile_app, referral, promotion, customer_service
- Defaults to "api" if not specified

**BR-ENR-007: Initial Status**
- New memberships created with status = "active"
- No pending state for standard enrollments
- Pending only for special approval flows

**BR-ENR-008: Expiration Date Calculation**
- expiration_date = enrolled_at + 365 days
- Calculated at enrollment time
- Can be extended on renewal

**BR-ENR-009: Auto-Renew Default**
- All memberships default to auto_renew = true
- User can disable auto-renewal anytime

**BR-ENR-010: History Recording**
- Every enrollment MUST record history entry
- Action: ENROLLED
- initiated_by: USER

**BR-ENR-011: Event Publishing**
- membership.enrolled event published after successful enrollment
- Includes: membership_id, user_id, tier_code, enrollment_bonus

**BR-ENR-012: Promo Code Validation**
- Promo codes optional but validated if provided
- Invalid promo codes result in warning (not failure)
- Bonus still applied if code valid

---

### Point Earning Rules (BR-PNT-001 to BR-PNT-010)

**BR-PNT-001: Active Membership Required**
- User MUST have active membership to earn points
- Error: "No active membership found" (HTTP 404)

**BR-PNT-002: Positive Points Amount**
- points_amount MUST be > 0
- Maximum: 10,000,000 points per request
- Error for invalid: Pydantic validation error (HTTP 422)

**BR-PNT-003: Source Required**
- source field MUST be non-empty
- Identifies earning activity (order_completed, signup_bonus, etc.)

**BR-PNT-004: Tier Multiplier Application**
- Final points = base_points * tier_multiplier
- Multipliers: Bronze=1.0x, Silver=1.25x, Gold=1.5x, Platinum=2.0x, Diamond=3.0x
- Applied automatically based on current tier

**BR-PNT-005: Atomic Point Addition**
- Point addition MUST be atomic (no partial operations)
- Use database transaction to prevent race conditions

**BR-PNT-006: Balance Update**
- points_balance += final_points (after multiplier)
- tier_points += base_points (before multiplier)
- lifetime_points += final_points

**BR-PNT-007: History Recording**
- Every point earning MUST record history entry
- Action: POINTS_EARNED
- points_change: positive value
- balance_after: new balance

**BR-PNT-008: Tier Check Trigger**
- After point earning, check tier upgrade eligibility
- If tier_points crosses threshold, upgrade tier
- Tier upgrade is immediate (no delay)

**BR-PNT-009: Event Publishing**
- points.earned event published after successful earning
- Includes: membership_id, user_id, points_earned, multiplier, balance_after

**BR-PNT-010: Reference ID for Idempotency**
- reference_id enables idempotent point earning
- Duplicate requests with same ID should be detected
- Prevents double-awarding

---

### Point Redemption Rules (BR-RDM-001 to BR-RDM-008)

**BR-RDM-001: Active Membership Required**
- User MUST have active membership to redeem points
- Error: "No active membership found" (HTTP 404)

**BR-RDM-002: Sufficient Points Required**
- points_balance MUST be >= points_amount
- Error: "Insufficient points. Available: X, Requested: Y" (HTTP 402)

**BR-RDM-003: Positive Redemption Amount**
- points_amount MUST be > 0
- Maximum: 10,000,000 points per request

**BR-RDM-004: Reward Code Required**
- reward_code MUST be non-empty
- Identifies what points are redeemed for

**BR-RDM-005: Atomic Point Deduction**
- Point deduction MUST be atomic (no partial operations)
- Verify balance, deduct, record history in single transaction

**BR-RDM-006: Balance Update**
- points_balance -= points_amount
- tier_points NOT affected (already counted when earned)
- lifetime_points NOT affected

**BR-RDM-007: History Recording**
- Every redemption MUST record history entry
- Action: POINTS_REDEEMED
- points_change: negative value
- reward_code included

**BR-RDM-008: Event Publishing**
- points.redeemed event published after successful redemption
- Includes: membership_id, user_id, points_redeemed, reward_code, balance_after

---

### Tier Rules (BR-TIR-001 to BR-TIR-010)

**BR-TIR-001: Bronze Tier**
- qualification_threshold: 0 tier_points
- point_multiplier: 1.0x
- Default tier for all new members

**BR-TIR-002: Silver Tier**
- qualification_threshold: 5,000 tier_points
- point_multiplier: 1.25x
- Unlocks: Priority Support

**BR-TIR-003: Gold Tier**
- qualification_threshold: 20,000 tier_points
- point_multiplier: 1.5x
- Unlocks: Free Shipping

**BR-TIR-004: Platinum Tier**
- qualification_threshold: 50,000 tier_points
- point_multiplier: 2.0x
- Unlocks: Exclusive Access

**BR-TIR-005: Diamond Tier**
- qualification_threshold: 100,000 tier_points
- point_multiplier: 3.0x
- Unlocks: VIP Concierge

**BR-TIR-006: Tier Upgrade Immediate**
- Tier upgrade happens immediately when threshold crossed
- No waiting period for upgrades
- New benefits available instantly

**BR-TIR-007: Tier Downgrade at Evaluation**
- Tier downgrade evaluated at end of qualification period
- 30-day grace period before demotion
- User notified before downgrade

**BR-TIR-008: Tier Caching**
- Tier definitions cached in memory
- Loaded at service startup
- No database query for tier lookup

**BR-TIR-009: Tier History Recording**
- Tier changes record history entry
- Action: TIER_UPGRADED or TIER_DOWNGRADED
- previous_tier and new_tier captured

**BR-TIR-010: Tier Event Publishing**
- membership.tier_upgraded event on upgrade
- membership.tier_downgraded event on downgrade
- Includes: membership_id, previous_tier, new_tier

---

### Benefit Rules (BR-BNF-001 to BR-BNF-005)

**BR-BNF-001: Tier-Based Availability**
- Benefits tied to current tier only
- Tier downgrade removes higher-tier benefits

**BR-BNF-002: Usage Limit Enforcement**
- Some benefits have usage limits per period
- Limit checked before use allowed

**BR-BNF-003: Unlimited Benefits**
- Some benefits are unlimited (usage_limit = null)
- Always available while at qualifying tier

**BR-BNF-004: Usage Tracking**
- Every benefit use recorded in history
- Action: BENEFIT_USED
- Includes benefit_code

**BR-BNF-005: Benefit Event Publishing**
- benefit.used event published on use
- Includes: membership_id, user_id, benefit_code

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

**BR-HST-004: Point Change Tracking**
- Positive points_change: points added
- Negative points_change: points deducted
- balance_after: balance after change

**BR-HST-005: Initiator Tracking**
- initiated_by: USER, SYSTEM, ADMIN, SERVICE
- Identifies who triggered the action

---

### Membership Lifecycle Rules (BR-LFC-001 to BR-LFC-005)

**BR-LFC-001: Suspension**
- Only active memberships can be suspended
- Reason required for suspension
- Benefits frozen during suspension

**BR-LFC-002: Reactivation**
- Only suspended memberships can be reactivated
- Benefits restored on reactivation

**BR-LFC-003: Cancellation**
- User can cancel active/pending membership
- forfeit_points determines point handling
- Points forfeited or can be redeemed before cancel

**BR-LFC-004: Expiration**
- Expired memberships lose benefits
- Points may be forfeited based on config
- Can renew to reactivate

**BR-LFC-005: Renewal**
- Extends expiration_date by 365 days
- Tier evaluated on renewal
- auto_renew triggers automatic renewal

---

## State Machines (3 machines)

### Membership Status State Machine

```
States:
- PENDING: Awaiting activation
- ACTIVE: Full benefits available
- SUSPENDED: Temporarily frozen
- EXPIRED: Period ended
- CANCELED: User-canceled

Transitions:
PENDING -> ACTIVE (activation)
ACTIVE -> SUSPENDED (suspension)
ACTIVE -> CANCELED (user cancellation)
ACTIVE -> EXPIRED (period end, no renewal)
SUSPENDED -> ACTIVE (reactivation)
SUSPENDED -> CANCELED (canceled while suspended)
EXPIRED -> ACTIVE (renewal)

Terminal States:
- CANCELED (final, no reactivation)

Rules:
- Only ACTIVE can earn/redeem points
- SUSPENDED freezes all point activity
- EXPIRED retains point balance for renewal
```

### Tier Progression State Machine

```
States:
- BRONZE: Entry tier (0+ tier_points)
- SILVER: 5,000+ tier_points
- GOLD: 20,000+ tier_points
- PLATINUM: 50,000+ tier_points
- DIAMOND: 100,000+ tier_points

Transitions:
BRONZE -> SILVER (5,000 tier_points)
SILVER -> GOLD (20,000 tier_points)
GOLD -> PLATINUM (50,000 tier_points)
PLATINUM -> DIAMOND (100,000 tier_points)

Downgrade Transitions (at evaluation):
SILVER -> BRONZE (< 5,000 tier_points in period)
GOLD -> SILVER (< 20,000 tier_points in period)
PLATINUM -> GOLD (< 50,000 tier_points in period)
DIAMOND -> PLATINUM (< 100,000 tier_points in period)

Rules:
- Upgrades immediate on threshold cross
- Downgrades only at evaluation period end
- 30-day grace period before downgrade
```

### Points Balance State Machine

```
States:
- ZERO: points_balance == 0
- POSITIVE: points_balance > 0
- LOW: points_balance < 1000

Transitions:
ZERO -> POSITIVE (points earned)
POSITIVE -> ZERO (all points redeemed/expired)
POSITIVE -> LOW (balance drops below 1000)
LOW -> POSITIVE (points earned)
LOW -> ZERO (remaining redeemed/expired)

Events:
- ZERO -> POSITIVE: points.earned
- POSITIVE -> ZERO: points.depleted (notification)
- POSITIVE -> LOW: points.low_balance (notification)
```

---

## Edge Cases (15 cases)

### EC-001: Duplicate Enrollment Attempt
- Input: Enroll user with existing active membership
- Expected: Error "User already has active membership"
- HTTP: 409 Conflict

### EC-002: Earn Points Without Membership
- Input: Earn points for user without membership
- Expected: Error "No active membership found"
- HTTP: 404 Not Found

### EC-003: Redeem More Than Balance
- Input: points_amount > points_balance
- Expected: Error "Insufficient points"
- HTTP: 402 Payment Required

### EC-004: Get Non-Existent Membership
- Input: Get with invalid membership_id
- Expected: Error "Membership not found"
- HTTP: 404 Not Found

### EC-005: Zero Points Earning
- Input: points_amount = 0
- Expected: Validation error (must be > 0)
- HTTP: 422 Unprocessable Entity

### EC-006: Negative Points Earning
- Input: points_amount = -1000
- Expected: Validation error (must be > 0)
- HTTP: 422 Unprocessable Entity

### EC-007: Empty User ID
- Input: user_id = "" or whitespace
- Expected: Validation error
- HTTP: 422 Unprocessable Entity

### EC-008: Suspend Already Suspended
- Input: Suspend membership already suspended
- Expected: Error or idempotent success
- Current: Returns current state

### EC-009: Cancel Already Canceled
- Input: Cancel membership already canceled
- Expected: Error "Membership already canceled"
- HTTP: 400 Bad Request

### EC-010: Earn Points on Suspended Membership
- Input: Earn points while membership suspended
- Expected: Error "Membership is suspended"
- HTTP: 403 Forbidden

### EC-011: Redeem on Expired Membership
- Input: Redeem points while membership expired
- Expected: Error "Membership is expired"
- HTTP: 403 Forbidden

### EC-012: Tier Upgrade Race Condition
- Input: Two point earnings crossing tier threshold simultaneously
- Expected: Both succeed, tier upgrade once
- Handling: Atomic database operations

### EC-013: History for Non-Existent Membership
- Input: Get history with invalid membership_id
- Expected: Empty history list (not error)

### EC-014: Benefit Use Over Limit
- Input: Use benefit when usage_limit reached
- Expected: Error "Benefit usage limit exceeded"
- HTTP: 403 Forbidden

### EC-015: Benefit Not Available at Tier
- Input: Use gold benefit on silver membership
- Expected: Error "Benefit not available at your tier"
- HTTP: 403 Forbidden

---

## Data Consistency Rules

### DC-001: Points Balance Consistency
- points_balance = SUM(positive point changes) - SUM(negative point changes)
- System maintains this invariant

### DC-002: Tier Points Consistency
- tier_points accumulate base points (before multiplier)
- Used for tier qualification

### DC-003: Lifetime Points Consistency
- lifetime_points = total points ever earned (after multiplier)
- Never decremented (even on expiration)

### DC-004: Status Consistency
- status reflects actual membership state
- Only valid transitions allowed

### DC-005: History Consistency
- Sum of points_change in history equals lifetime changes
- Each history entry has valid membership_id

---

## Integration Contracts

### Order Service Integration
- **Via**: NATS events
- **Event**: order.completed
- **When**: Order completed
- **Handler**: Calculate points from order value
- **Action**: Award points with tier multiplier

### Account Service Integration
- **Via**: HTTP (optional)
- **Endpoint**: GET /api/v1/users/{user_id}
- **When**: Enrollment validation
- **Error Handling**: Proceed without validation if unavailable

### Notification Service Integration
- **Via**: NATS events
- **Events Published**:
  - membership.enrolled
  - membership.tier_upgraded
  - points.earned (milestones)
  - points.low_balance
- **Error Handling**: Log and continue if NATS unavailable

### Authorization Service Integration
- **Via**: NATS events
- **Events Published**: membership.tier_upgraded, membership.tier_downgraded
- **Purpose**: Update tier-based permissions

---

## Error Handling Contracts

### Validation Errors
- Invalid request parameters -> 422 Unprocessable Entity
- Response includes field-level error details

### Business Logic Errors
- Insufficient points -> 402 Payment Required
- Membership not found -> 404 Not Found
- Duplicate membership -> 409 Conflict
- Not authorized -> 403 Forbidden

### System Errors
- Database connection failure -> 500 Internal Server Error
- Event bus unavailable -> Log warning, continue operation
- External service unavailable -> Graceful degradation

### Error Response Format
```json
{
  "success": false,
  "error": "Human readable error message",
  "error_code": "INSUFFICIENT_POINTS",
  "details": {
    "available": 500,
    "requested": 1000
  }
}
```

---

## Performance Contracts

### Response Time SLAs
- GET /health: < 10ms p99
- GET /api/v1/memberships/points/balance: < 30ms p99
- POST /api/v1/memberships/points/earn: < 50ms p99
- POST /api/v1/memberships/points/redeem: < 50ms p99
- POST /api/v1/memberships: < 200ms p99
- GET /api/v1/memberships: < 100ms p99

### Throughput Requirements
- Point earning: 50,000 requests/second
- Point redemption: 10,000 requests/second
- Balance queries: 100,000 requests/second
- Enrollment: 1,000 requests/second

---

**Document Statistics**:
- Lines: ~750
- Business Rules: 50
- State Machines: 3
- Edge Cases: 15
- Integration Contracts: 4
