# Credit Service - Logic Contract

## Business Rules (50 rules)

### Credit Account Rules (BR-ACC-001 to BR-ACC-010)

**BR-ACC-001: User ID Required**
- Credit account MUST have a user_id
- System validates user_id is non-empty string
- Error returned if violated: "user_id is required"
- Example: `{"user_id": ""}` -> 400 Bad Request

**BR-ACC-002: User ID Format**
- User ID MUST be 1-50 characters
- System trims whitespace before validation
- Whitespace-only strings are rejected
- Example: `{"user_id": "   "}` -> 400 Bad Request

**BR-ACC-003: Credit Type Required**
- Credit account MUST have a valid credit_type
- Valid types: promotional, bonus, referral, subscription, compensation
- Invalid type returns 400 Bad Request
- Example: `{"credit_type": "invalid"}` -> 400 Bad Request

**BR-ACC-004: One Account Per User Per Type**
- Each user has maximum ONE account per credit_type
- Duplicate creation returns existing account
- Unique constraint on (user_id, credit_type)

**BR-ACC-005: Account ID Generation**
- Account ID auto-generated as UUID
- Format: `cred_acc_{uuid.uuid4().hex[:24]}`
- Client cannot specify account ID

**BR-ACC-006: Initial Balance Zero**
- New accounts start with balance = 0
- Allocation required to add credits
- total_allocated, total_consumed, total_expired all start at 0

**BR-ACC-007: Balance Cannot Be Negative**
- Account balance MUST be >= 0
- Consumption blocked if would result in negative
- Error: "Insufficient credits"

**BR-ACC-008: Expiration Policy Required**
- Account MUST have expiration_policy
- Default: "fixed_days" with 90 days
- Valid: fixed_days, end_of_month, end_of_year, subscription_period, never

**BR-ACC-009: Account Deactivation**
- Inactive accounts reject all operations except query
- Deactivation sets is_active = false
- Existing credits remain but cannot be used

**BR-ACC-010: Organization Association Optional**
- organization_id links account to organization
- Used for B2B credit allocations
- Optional field for consumer accounts

### Credit Allocation Rules (BR-ALC-001 to BR-ALC-010)

**BR-ALC-001: Amount Must Be Positive**
- Allocation amount MUST be > 0
- Zero or negative amounts rejected with 422
- Example: `{"amount": 0}` -> 422 Validation Error

**BR-ALC-002: Expiration Date Required**
- Allocated credits MUST have expires_at
- Set based on expiration_policy + expiration_days
- Default: NOW() + 90 days

**BR-ALC-003: Campaign Budget Check**
- Before allocation, verify campaign has remaining_budget
- remaining_budget = total_budget - allocated_amount
- If remaining_budget < amount: reject with 402

**BR-ALC-004: Campaign Eligibility Check**
- User must meet campaign eligibility_rules
- Check min_account_age_days, user_tier, new_users_only
- Ineligible user returns 403 Forbidden

**BR-ALC-005: Max Allocations Per User**
- Enforce campaign max_allocations_per_user limit
- Count existing allocations for user from this campaign
- If count >= limit: reject with 409 Duplicate

**BR-ALC-006: Campaign Date Range**
- Campaign must be active (start_date <= NOW() <= end_date)
- Expired campaigns cannot allocate
- Future campaigns cannot allocate

**BR-ALC-007: Allocation ID Generation**
- Allocation ID auto-generated
- Format: `cred_alloc_{uuid.uuid4().hex[:20]}`
- Links campaign, user, account, transaction

**BR-ALC-008: Transaction Created**
- Each allocation creates transaction record
- transaction_type = "allocate"
- Reference links to campaign_id

**BR-ALC-009: Balance Update**
- Account balance += allocation amount
- total_allocated += allocation amount
- Atomic update to prevent race conditions

**BR-ALC-010: Idempotency Handling**
- Duplicate allocations identified by (user_id, campaign_id)
- Second attempt returns existing allocation
- Prevents double-allocation from retries

### Credit Consumption Rules (BR-CON-001 to BR-CON-010)

**BR-CON-001: Amount Must Be Positive**
- Consumption amount MUST be > 0
- Zero or negative amounts rejected with 422
- Example: `{"amount": 0}` -> 422 Validation Error

**BR-CON-002: Sufficient Balance Required**
- Total balance across all accounts MUST >= amount
- If insufficient: return available + deficit
- Error: 402 Payment Required with balance info

**BR-CON-003: FIFO Expiration Order**
- Consume from accounts with soonest expires_at first
- Within same expiration: oldest allocation first
- Maximizes credit utilization before expiration

**BR-CON-004: Credit Type Priority**
- Within same expiration date, consume by priority:
  1. compensation (highest - use free money first)
  2. promotional
  3. bonus
  4. referral
  5. subscription (lowest - preserve subscription value)

**BR-CON-005: Multi-Account Consumption**
- Single consumption may span multiple accounts
- Each account gets separate transaction
- All transactions linked to same billing_record_id

**BR-CON-006: Partial Consumption Supported**
- If insufficient total credits, consume what's available
- Return amount_consumed and deficit
- Caller decides whether to proceed with partial

**BR-CON-007: Billing Reference Required**
- Usage consumption MUST include billing_record_id
- Manual consumption can omit reference
- Enables billing reconciliation

**BR-CON-008: Transaction Created Per Account**
- Each account consumed creates transaction
- transaction_type = "consume"
- Records balance_before and balance_after

**BR-CON-009: Allocation Tracking**
- Update allocation.consumed_amount
- Track remaining_amount = amount - expired - consumed
- Used for expiration calculations

**BR-CON-010: Atomic Multi-Account Update**
- All account updates in single transaction
- Rollback all if any fails
- Prevents partial consumption state

### Credit Expiration Rules (BR-EXP-001 to BR-EXP-010)

**BR-EXP-001: Daily Expiration Processing**
- Expiration job runs daily (default: midnight UTC)
- Queries allocations with expires_at <= NOW()
- Only processes remaining_amount > 0

**BR-EXP-002: Expiration Transaction Created**
- Each expiration creates transaction
- transaction_type = "expire"
- Amount = allocation.remaining_amount

**BR-EXP-003: Balance Updated**
- Account balance -= expired amount
- Account total_expired += expired amount
- Allocation status = "expired" when fully expired

**BR-EXP-004: 7-Day Warning**
- Publish credit.expiring_soon event 7 days before
- Include amount and expires_at
- One warning per allocation

**BR-EXP-005: Expired Credits Cannot Be Consumed**
- Query excludes allocations where expires_at < NOW()
- Balance reflects only unexpired credits
- Ensures accurate availability

**BR-EXP-006: Expiration Is Final**
- Expired credits cannot be restored
- Manual adjustment required to compensate
- Audit trail maintained

**BR-EXP-007: Partial Expiration**
- If allocation partially consumed, only remainder expires
- remaining_amount = amount - consumed_amount - expired_amount
- Accurate tracking of utilization

**BR-EXP-008: Never Expire Policy**
- expiration_policy = "never" skips expiration
- expires_at = NULL for never-expire allocations
- Used rarely for special credits

**BR-EXP-009: Subscription Period Expiration**
- expiration_policy = "subscription_period"
- expires_at = subscription period_end
- Subscription renewal allocates fresh credits

**BR-EXP-010: End of Period Expiration**
- end_of_month: expires at 23:59:59 last day of month
- end_of_year: expires at 23:59:59 December 31
- Timezone handled as UTC

### Credit Transfer Rules (BR-TRF-001 to BR-TRF-010)

**BR-TRF-001: Sufficient Balance Required**
- Sender must have >= transfer amount
- Of the specified credit_type
- Error: 402 Insufficient Credits

**BR-TRF-002: Recipient Must Exist**
- to_user_id must be valid active user
- Validated via Account Service
- Error: 404 User Not Found

**BR-TRF-003: Self-Transfer Prohibited**
- from_user_id != to_user_id
- Error: 400 Bad Request
- Message: "Cannot transfer to self"

**BR-TRF-004: Credit Type Restrictions**
- Some credit types non-transferable
- compensation credits cannot be transferred
- Error: 403 Transfer Not Allowed

**BR-TRF-005: Paired Transactions**
- Transfer creates two transactions:
  - Sender: transaction_type = "transfer_out"
  - Recipient: transaction_type = "transfer_in"
- Linked by transfer_id in metadata

**BR-TRF-006: Balance Updates**
- Sender: balance -= amount
- Recipient: balance += amount
- Atomic update for consistency

**BR-TRF-007: Transfer ID Generated**
- Format: `trf_{uuid.uuid4().hex[:24]}`
- Links both transactions
- Enables transfer tracking

**BR-TRF-008: Account Creation for Recipient**
- If recipient lacks account of type, create it
- Initialize with balance = transfer amount
- Follow normal account creation rules

**BR-TRF-009: Transfer Event Published**
- Publish credit.transferred event
- Include from_user_id, to_user_id, amount
- Enables notification to both parties

**BR-TRF-010: Transfer Limits (Optional)**
- Configurable max transfer per day
- Configurable max transfer per transaction
- Prevents abuse if enabled

### Campaign Rules (BR-CMP-001 to BR-CMP-010)

**BR-CMP-001: Name Required**
- Campaign MUST have name
- 1-100 characters
- Whitespace-only rejected

**BR-CMP-002: Valid Date Range**
- start_date MUST be <= end_date
- Cannot create campaign in the past
- Error: 400 "start_date must be before end_date"

**BR-CMP-003: Positive Budget**
- total_budget MUST be > 0
- credit_amount MUST be > 0
- Error: 422 Validation Error

**BR-CMP-004: Budget Tracking**
- allocated_amount tracks total allocated
- remaining_budget = total_budget - allocated_amount
- Computed or stored depending on implementation

**BR-CMP-005: Budget Exhaustion**
- When remaining_budget < credit_amount: campaign exhausted
- Publish campaign.budget.exhausted event
- Optionally auto-deactivate

**BR-CMP-006: Campaign ID Generation**
- Format: `camp_{uuid.uuid4().hex[:20]}`
- Unique identifier for campaign
- Referenced in allocations

**BR-CMP-007: Active Status Check**
- is_active = false: cannot allocate
- Inactive campaigns remain queryable
- Admin can deactivate anytime

**BR-CMP-008: Eligibility Rules Format**
- JSONB field for flexible rules
- Common: min_account_age_days, user_tier, new_users_only
- Validated against user profile

**BR-CMP-009: Expiration Days**
- Credits allocated from campaign expire in expiration_days
- Default: 90 days
- Range: 1-365 days

**BR-CMP-010: Max Allocations Enforcement**
- max_allocations_per_user default: 1
- Query existing allocations before new allocation
- Prevents multi-claim abuse

### Event Rules (BR-EVT-001 to BR-EVT-010)

**BR-EVT-001: Credit Allocated Event**
- Published after successful allocation
- Includes: allocation_id, user_id, amount, credit_type, expires_at
- Enables notification and analytics

**BR-EVT-002: Credit Consumed Event**
- Published after successful consumption
- Includes: transaction_ids, user_id, amount, billing_record_id
- Enables billing confirmation

**BR-EVT-003: Credit Expired Event**
- Published after expiration processing
- Includes: user_id, amount, credit_type, balance_after
- Per-allocation or batched

**BR-EVT-004: Credit Transferred Event**
- Published after successful transfer
- Includes: from_user_id, to_user_id, amount, credit_type
- Enables notification to both

**BR-EVT-005: Credit Expiring Soon Event**
- Published 7 days before expiration
- Includes: user_id, amount, expires_at
- Enables proactive user notification

**BR-EVT-006: Campaign Budget Exhausted Event**
- Published when campaign budget depleted
- Includes: campaign_id, name, total_budget, allocated_amount
- Enables admin alerting

**BR-EVT-007: User Created Subscription**
- Subscribe to user.created from account_service
- Trigger sign-up bonus allocation
- Idempotent handling

**BR-EVT-008: Subscription Renewed Subscription**
- Subscribe to subscription.renewed from subscription_service
- Allocate monthly subscription credits
- Link to subscription period

**BR-EVT-009: Order Completed Subscription**
- Subscribe to order.completed from order_service
- Process referral credits if referral_code present
- Award to both referrer and referee

**BR-EVT-010: User Deleted Subscription**
- Subscribe to user.deleted from account_service
- Archive credit accounts
- Cancel pending allocations

---

## State Machines (3 machines)

### Credit Allocation State Machine

```
States:
- PENDING: Allocation requested, processing
- COMPLETED: Credits successfully allocated
- FAILED: Allocation failed (budget, eligibility, etc.)
- REVOKED: Credits revoked (admin action)
- EXPIRED: All credits from allocation expired

Transitions:
PENDING -> COMPLETED (allocation successful)
PENDING -> FAILED (validation or budget failure)
COMPLETED -> REVOKED (admin revokes credits)
COMPLETED -> EXPIRED (all remaining credits expired)
FAILED -> (terminal - no transitions out)
REVOKED -> (terminal - no transitions out)
EXPIRED -> (terminal - no transitions out)

Rules:
- PENDING is transient (short duration during processing)
- COMPLETED tracks partial consumption and expiration
- EXPIRED only when remaining_amount = 0 due to expiration
- All transitions update updated_at
```

### Credit Consumption State Machine

```
States:
- INITIATED: Consumption request received
- PLANNING: Calculating FIFO consumption plan
- EXECUTING: Deducting from accounts
- COMPLETED: All deductions successful
- FAILED: Deduction failed (insufficient, error)
- PARTIAL: Some but not all consumed

Transitions:
(start) -> INITIATED
INITIATED -> PLANNING (valid request)
INITIATED -> FAILED (invalid request)
PLANNING -> EXECUTING (plan calculated)
PLANNING -> FAILED (no available credits)
EXECUTING -> COMPLETED (all deductions done)
EXECUTING -> PARTIAL (some deductions done, stopped)
EXECUTING -> FAILED (rollback on error)

Rules:
- Single HTTP request spans all states
- PARTIAL allows caller to accept what's available
- FAILED triggers rollback of any partial changes
- COMPLETED is final success state
```

### Campaign State Machine

```
States:
- DRAFT: Created but not active
- SCHEDULED: Waiting for start_date
- ACTIVE: Currently allocating
- EXHAUSTED: Budget depleted
- EXPIRED: Past end_date
- DEACTIVATED: Manually deactivated

Transitions:
DRAFT -> SCHEDULED (has future start_date)
DRAFT -> ACTIVE (start_date <= now <= end_date)
SCHEDULED -> ACTIVE (start_date reached)
ACTIVE -> EXHAUSTED (remaining_budget < credit_amount)
ACTIVE -> EXPIRED (end_date passed)
ACTIVE -> DEACTIVATED (admin action)
EXHAUSTED -> ACTIVE (budget increased)
EXPIRED -> (terminal)
DEACTIVATED -> ACTIVE (admin reactivates)

Rules:
- Date transitions happen implicitly (query-time check)
- EXHAUSTED can be recovered by budget increase
- EXPIRED cannot be extended (create new campaign)
- DEACTIVATED requires explicit admin action
```

---

## Edge Cases (15 cases)

### EC-001: Concurrent Allocation Attempts
- **Input**: Same user, same campaign, simultaneous requests
- **Expected**: Only one allocation created
- **Actual**: Unique constraint or idempotency check
- **Note**: Return existing allocation for duplicate

### EC-002: Consumption Exhausts Multiple Accounts
- **Input**: Amount > any single account balance
- **Expected**: Consume from multiple accounts in FIFO order
- **Actual**: Multiple transactions, total = requested
- **Note**: All transactions share billing_record_id

### EC-003: Allocation During Campaign Budget Race
- **Input**: Last credit_amount of budget, two concurrent requests
- **Expected**: One succeeds, one fails with budget exhausted
- **Actual**: Atomic budget check and update
- **Note**: Second request gets 402 error

### EC-004: Expiration at Midnight Boundary
- **Input**: expires_at = midnight, query at 00:00:01
- **Expected**: Credit is expired
- **Actual**: Query uses expires_at <= NOW()
- **Note**: Timezone normalized to UTC

### EC-005: Transfer to Non-Existent User
- **Input**: to_user_id not in account_service
- **Expected**: 404 User Not Found
- **Actual**: Validate via AccountClient before transfer
- **Note**: Fail fast, no balance changes

### EC-006: Consumption With Zero Balance
- **Input**: User has no credits, requests consumption
- **Expected**: 402 Insufficient Credits
- **Actual**: Return balance: 0, deficit: requested_amount
- **Note**: No transactions created

### EC-007: Campaign With Zero Remaining Budget
- **Input**: Allocation request when remaining_budget = 0
- **Expected**: 402 Campaign Budget Exhausted
- **Actual**: Check before allocation attempt
- **Note**: Campaign may be auto-deactivated

### EC-008: Partial Expiration of Allocation
- **Input**: 1000 allocated, 600 consumed, expires today
- **Expected**: 400 credits expire, 600 already consumed
- **Actual**: remaining_amount = 1000 - 600 = 400 expires
- **Note**: Accurate accounting

### EC-009: Transfer of Non-Transferable Type
- **Input**: credit_type = "compensation" transfer request
- **Expected**: 403 Transfer Not Allowed
- **Actual**: Check credit_type restrictions
- **Note**: Compensation credits are non-transferable

### EC-010: Account Service Unavailable During Transfer
- **Input**: Transfer request, AccountClient timeout
- **Expected**: 503 Service Unavailable
- **Actual**: Graceful error, no balance changes
- **Note**: Retry recommended

### EC-011: Large Consumption Plan
- **Input**: Consume 100,000 credits from 50 accounts
- **Expected**: All deducted in order
- **Actual**: Batch processing with transaction
- **Note**: Performance may require optimization

### EC-012: Campaign Eligibility Edge
- **Input**: User tier upgraded mid-campaign
- **Expected**: Current tier checked at allocation time
- **Actual**: Real-time eligibility evaluation
- **Note**: No retroactive allocations

### EC-013: Negative Allocation Amount (Attempt)
- **Input**: amount = -100 in allocation request
- **Expected**: 422 Validation Error
- **Actual**: Pydantic validates gt=0
- **Note**: Request rejected before service logic

### EC-014: Duplicate Campaign Name
- **Input**: Create campaign with existing name
- **Expected**: Allowed (name not unique)
- **Actual**: Campaign created with new campaign_id
- **Note**: campaign_id is unique, not name

### EC-015: User Deleted During Consumption
- **Input**: Consumption in progress, user.deleted event arrives
- **Expected**: Current consumption completes
- **Actual**: Account cleanup after transaction
- **Note**: No race condition due to transaction isolation

---

## Data Consistency Rules

### DC-001: Account ID Uniqueness
- account_id is primary key
- Enforced at database level
- UUID generation ensures uniqueness

### DC-002: User-Type Uniqueness
- (user_id, credit_type) is unique constraint
- One account per user per type
- Duplicate creation returns existing

### DC-003: Transaction Immutability
- Transactions cannot be modified after creation
- balance_before, balance_after recorded at creation
- Audit trail preserved

### DC-004: Balance Consistency
- balance = total_allocated - total_consumed - total_expired
- Derived value matches computed value
- Reconciliation possible via transactions

### DC-005: Allocation-Transaction Link
- Each allocation has corresponding transaction
- allocation.transaction_id references transaction
- Enables audit trail

### DC-006: Campaign Budget Tracking
- allocated_amount = SUM(allocation.amount) for campaign
- remaining_budget = total_budget - allocated_amount
- Atomic update prevents over-allocation

### DC-007: FIFO Order Determinism
- Order by (expires_at ASC, created_at ASC)
- Same query produces same order
- Ensures predictable consumption

---

## Integration Contracts

### Account Service Integration
- **Endpoint**: GET /api/v1/users/{user_id}
- **When**: User validation, transfer recipient check
- **Expected Response**: 200 with user details OR 404
- **Error Handling**: Fail-safe - reject operation if unavailable

### Subscription Service Integration
- **Endpoint**: GET /api/v1/subscriptions/user/{user_id}
- **When**: Subscription credit allocation
- **Expected Response**: 200 with subscription details OR 404
- **Error Handling**: Skip allocation if unavailable

### Billing Service Integration
- **Event**: credit.consumed published
- **When**: After credit consumption for billing
- **Payload**: transaction details, billing_record_id
- **Expected Response**: Billing service confirms asynchronously

### Notification Service Integration
- **Event**: credit.allocated, credit.expiring_soon, credit.expired
- **When**: After credit lifecycle events
- **Payload**: Event details for user notification
- **Expected Response**: Notification sent asynchronously

### Order Service Integration
- **Event**: order.completed subscribed
- **When**: Order with referral_code completed
- **Payload**: order details, referral_code
- **Handler**: Allocate referral credits to both parties

---

## Error Handling Contracts

### Account Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 400 | "user_id is required" |
| Invalid credit_type | 400 | "credit_type must be one of: ..." |
| Invalid expiration_policy | 400 | "expiration_policy must be one of: ..." |
| Account not found | 404 | "Credit account not found: {id}" |
| Account inactive | 400 | "Credit account is inactive" |

### Allocation Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Amount <= 0 | 422 | Validation error detail |
| Campaign not found | 404 | "Campaign not found: {id}" |
| Campaign inactive | 400 | "Campaign is not active" |
| Campaign expired | 400 | "Campaign has expired" |
| Budget exhausted | 402 | "Campaign budget exhausted" |
| User ineligible | 403 | "User does not meet eligibility requirements" |
| Max allocations reached | 409 | "Maximum allocations reached for this campaign" |

### Consumption Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Amount <= 0 | 422 | Validation error detail |
| Insufficient credits | 402 | "Insufficient credits" |
| User not found | 404 | "User not found: {id}" |
| No active accounts | 402 | "No credit accounts available" |

### Transfer Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Self-transfer | 400 | "Cannot transfer to self" |
| Insufficient credits | 402 | "Insufficient credits for transfer" |
| Recipient not found | 404 | "Recipient user not found" |
| Non-transferable type | 403 | "Credit type not transferable" |
| Transfer disabled | 403 | "Credit transfers are disabled" |

### Campaign Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Name empty | 400 | "name is required" |
| Invalid date range | 400 | "start_date must be before end_date" |
| Budget <= 0 | 422 | Validation error detail |
| Credit amount <= 0 | 422 | Validation error detail |
| Campaign not found | 404 | "Campaign not found: {id}" |

### Query Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Invalid page | 422 | Validation error (ge=1) |
| Invalid page_size | 422 | Validation error (le=100) |
| Invalid transaction_type filter | 400 | "transaction_type must be one of: ..." |
| Invalid date range | 400 | "start_date must be before end_date" |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Credit Service Team
