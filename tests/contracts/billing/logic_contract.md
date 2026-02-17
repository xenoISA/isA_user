# Billing Service - Logic Contract

## Business Rules (50 rules)

### Usage Recording Rules (BR-USG-001 to BR-USG-010)

**BR-USG-001: User ID Required**
- Usage record MUST have a user_id
- System validates user_id is non-empty string
- Error returned if violated: "user_id is required"
- Example: `{"user_id": ""}` -> 400 Bad Request

**BR-USG-002: User ID Format**
- User ID MUST be 1-50 characters
- System trims whitespace before validation
- Whitespace-only strings are rejected
- Example: `{"user_id": "   "}` -> 400 Bad Request

**BR-USG-003: Product ID Required**
- Usage record MUST have a product_id
- System validates product_id is non-empty string
- Error returned if violated: "product_id is required"
- Example: `{"product_id": ""}` -> 400 Bad Request

**BR-USG-004: Service Type Validation**
- Service type MUST be valid enum value
- Valid types: model_inference, mcp_service, agent_execution, storage_minio, api_gateway, notification, other
- Invalid type returns 400 Bad Request
- Example: `{"service_type": "invalid"}` -> 400 Bad Request

**BR-USG-005: Usage Amount Non-Negative**
- usage_amount MUST be >= 0
- Zero usage is valid (free tier tracking)
- Negative values rejected with 422
- Example: `{"usage_amount": -100}` -> 422 Validation Error

**BR-USG-006: Usage Record ID Generation**
- Usage record ID auto-generated as UUID
- Format: `usage_{uuid.uuid4().hex[:24]}`
- Client cannot specify usage record ID

**BR-USG-007: Idempotency Handling**
- Duplicate usage events identified by event_id/request_id
- Duplicate events return existing record, not error
- Prevents double-billing from retries

**BR-USG-008: Usage Timestamp**
- usage_timestamp defaults to current UTC if not provided
- Created_at always set to server timestamp
- Distinguishes event time from recording time

**BR-USG-009: Session Association Optional**
- session_id links usage to conversation session
- Optional field for non-session usage
- Enables session-level billing aggregation

**BR-USG-010: Usage Details Optional**
- usage_details is optional JSONB field
- Defaults to empty object `{}`
- Stores model, tokens, latency details

### Cost Calculation Rules (BR-CST-001 to BR-CST-010)

**BR-CST-001: Subscription Check First**
- Subscription coverage checked before billing
- If subscription includes service type: total_cost = 0
- billing_method = "subscription_included"
- Skips further calculation

**BR-CST-002: Free Tier Application**
- Free tier applied after subscription check
- free_tier_remaining calculated per period
- billable_amount = max(0, usage_amount - free_tier_remaining)
- Free tier resets per period (daily/monthly)

**BR-CST-003: Unit Price Lookup**
- Unit price retrieved from Product Service
- Default prices used if service unavailable
- Price varies by service_type and product_id

**BR-CST-004: Total Cost Calculation**
- total_cost = billable_amount × unit_price
- Precision: 6 decimal places minimum
- Rounding: HALF_UP for final display

**BR-CST-005: Currency Handling**
- Default currency is USD
- CNY and CREDIT also supported
- Currency stored with each record

**BR-CST-006: Calculation Response**
- Returns full cost breakdown
- Includes: original_amount, free_tier_applied, billable_amount, total_cost
- Includes suggested_billing_method

**BR-CST-007: Wallet Balance Check**
- Wallet balance fetched from Wallet Service
- Included in calculation response
- Determines if wallet_deduction is available

**BR-CST-008: Credit Balance Check**
- Credit balance fetched from Wallet Service
- Included in calculation response
- Credits preferred over wallet (free money first)

**BR-CST-009: Available Methods List**
- available_billing_methods computed based on balances
- If credits >= total_cost: include credit_consumption
- If wallet >= total_cost: include wallet_deduction
- Always available: payment_charge (if configured)

**BR-CST-010: Zero Cost Response**
- If total_cost = 0 (free tier or subscription)
- Still returns full response
- billing_method = "subscription_included" or none

### Billing Processing Rules (BR-PRC-001 to BR-PRC-010)

**BR-PRC-001: Billing Method Priority**
- Credit consumption checked first
- Wallet deduction checked second
- Payment charge as fallback
- User can override with specific method

**BR-PRC-002: Credit Deduction**
- If billing_method = credit_consumption
- Call WalletService.deduct_credits()
- Record credit_balance_after
- Mark billing_method = "credit_consumption"

**BR-PRC-003: Wallet Deduction**
- If billing_method = wallet_deduction
- Call WalletService.deduct_balance()
- Record wallet_balance_after
- Mark billing_method = "wallet_deduction"

**BR-PRC-004: Payment Charge**
- If billing_method = payment_charge
- Call PaymentService.charge() (future)
- Record payment_transaction_id
- Mark billing_method = "payment_charge"

**BR-PRC-005: Insufficient Funds**
- If selected method has insufficient balance
- Return 402 Payment Required
- Set billing_status = "failed"
- Include balance and required amount in error

**BR-PRC-006: Billing Record Status**
- pending: Created, awaiting processing
- processing: Deduction in progress
- completed: Successfully processed
- failed: Processing failed
- refunded: Amount returned

**BR-PRC-007: Processed At Timestamp**
- processed_at set when status = "completed" or "failed"
- NULL until processing attempted
- Used for billing reconciliation

**BR-PRC-008: Transaction ID Recording**
- wallet_transaction_id: For wallet/credit deductions
- payment_transaction_id: For payment charges
- Enables transaction tracing

**BR-PRC-009: Force Process Option**
- force_process = true bypasses balance check
- Creates record with potential debt
- Administrative use only

**BR-PRC-010: Atomic Processing**
- Balance deduction and record update atomic
- Rollback on partial failure
- Prevents inconsistent state

### Quota Management Rules (BR-QTA-001 to BR-QTA-010)

**BR-QTA-001: Quota Check Before Usage**
- Quota validated before allowing usage
- Returns allowed: true/false
- Includes remaining quota

**BR-QTA-002: Soft Limit Behavior**
- quota_type = soft_limit
- Usage allowed even if exceeded
- Warning message returned
- Event published for alerting

**BR-QTA-003: Hard Limit Behavior**
- quota_type = hard_limit
- Usage blocked if would exceed
- allowed = false returned
- quota.exceeded event published

**BR-QTA-004: Quota Calculation**
- remaining = quota_limit - quota_used
- would_exceed = (quota_used + requested_amount) > quota_limit
- Returns exact remaining amount

**BR-QTA-005: Period Types**
- Supported: daily, weekly, monthly
- Period boundaries calculated automatically
- Quota resets at period start

**BR-QTA-006: Quota Reset**
- auto_reset = true: Automatic reset at period end
- Reset sets quota_used = 0
- last_reset_date updated

**BR-QTA-007: Per-Service Quotas**
- Quotas can be per service_type
- Different limits for different services
- Checked against requested service_type

**BR-QTA-008: Organization Quotas**
- Quotas can apply to organization
- Shared across organization members
- organization_id used for lookup

**BR-QTA-009: Quota Status Response**
- Returns all quotas for user/org
- Includes current_usage, limit, remaining
- Shows next_reset_date

**BR-QTA-010: Suggested Actions**
- If quota exceeded, suggest actions
- "Upgrade subscription", "Wait for reset", etc.
- Helps user resolve situation

### Event Rules (BR-EVT-001 to BR-EVT-010)

**BR-EVT-001: Usage Recorded Event**
- Published after usage successfully recorded
- Includes: record_id, user_id, service_type, quantity
- Enables analytics tracking

**BR-EVT-002: Billing Calculated Event**
- Published after cost calculation
- Includes: original_amount, billable_amount, total_cost
- Enables pre-billing notifications

**BR-EVT-003: Billing Processed Event**
- Published after successful billing
- Includes: total_cost, billing_method, balance_after
- Enables confirmation notifications

**BR-EVT-004: Quota Exceeded Event**
- Published when hard limit hit
- Includes: user_id, service_type, limit, current_usage
- Enables admin alerting

**BR-EVT-005: Billing Error Event**
- Published when processing fails
- Includes: error_type, error_message
- Enables error monitoring

**BR-EVT-006: Event Idempotency**
- Events include event_id for deduplication
- Subscribers track processed events
- Prevents duplicate processing

**BR-EVT-007: Session Tokens Used Subscription**
- Subscribe to session.tokens_used
- Triggers automatic billing for tokens
- Real-time usage capture

**BR-EVT-008: Order Completed Subscription**
- Subscribe to order.completed
- Creates billing record for orders
- Product purchase billing

**BR-EVT-009: Session Ended Subscription**
- Subscribe to session.ended
- Finalizes session billing
- Captures total session cost

**BR-EVT-010: User Deleted Subscription**
- Subscribe to user.deleted
- Archives billing records
- Handles account cleanup

---

## State Machines (3 machines)

### Billing Record State Machine

```
States:
- PENDING: Record created, awaiting processing
- PROCESSING: Payment/deduction in progress
- COMPLETED: Successfully billed
- FAILED: Billing failed (insufficient funds, etc.)
- REFUNDED: Amount returned to user

Transitions:
PENDING -> PROCESSING (processing started)
PROCESSING -> COMPLETED (deduction successful)
PROCESSING -> FAILED (deduction failed)
COMPLETED -> REFUNDED (refund issued)
FAILED -> PROCESSING (retry attempted)
FAILED -> COMPLETED (retry successful)

Terminal States:
- COMPLETED: Normal end state
- REFUNDED: After refund processed

Rules:
- PENDING is initial state for all records
- PROCESSING is transient (short duration)
- FAILED can be retried (non-terminal)
- Only COMPLETED can transition to REFUNDED
- All transitions update updated_at
```

### Billing Method Selection State Machine

```
States:
- CHECK_SUBSCRIPTION: Verify subscription coverage
- CHECK_FREE_TIER: Calculate free tier remaining
- CHECK_CREDITS: Verify credit balance
- CHECK_WALLET: Verify wallet balance
- PAYMENT_REQUIRED: Direct payment needed
- BILLING_READY: Method selected

Transitions:
(start) -> CHECK_SUBSCRIPTION
CHECK_SUBSCRIPTION -> BILLING_READY (subscription covers)
CHECK_SUBSCRIPTION -> CHECK_FREE_TIER (not covered)
CHECK_FREE_TIER -> BILLING_READY (fully free)
CHECK_FREE_TIER -> CHECK_CREDITS (billable amount > 0)
CHECK_CREDITS -> BILLING_READY (sufficient credits)
CHECK_CREDITS -> CHECK_WALLET (insufficient credits)
CHECK_WALLET -> BILLING_READY (sufficient balance)
CHECK_WALLET -> PAYMENT_REQUIRED (insufficient balance)
PAYMENT_REQUIRED -> BILLING_READY (payment available)
PAYMENT_REQUIRED -> ERROR (no payment method)

Rules:
- Subscription checked first (zero cost path)
- Free tier reduces billable amount
- Credits preferred over wallet (free money first)
- Wallet preferred over direct payment
- Each check short-circuits if successful
```

### Quota State Machine

```
States:
- AVAILABLE: Quota has remaining capacity
- WARNING: Approaching limit (soft)
- EXCEEDED: Limit reached (soft)
- BLOCKED: Limit reached (hard)
- RESET_PENDING: Period ended, awaiting reset

Transitions:
AVAILABLE -> WARNING (usage > 80% of limit)
AVAILABLE -> EXCEEDED (usage > limit, soft)
AVAILABLE -> BLOCKED (usage > limit, hard)
WARNING -> AVAILABLE (quota increased)
WARNING -> EXCEEDED (limit reached)
EXCEEDED -> AVAILABLE (quota reset)
BLOCKED -> AVAILABLE (quota reset)
ANY -> RESET_PENDING (period ended)
RESET_PENDING -> AVAILABLE (reset completed)

Rules:
- Soft limit allows EXCEEDED state with warnings
- Hard limit blocks at BLOCKED state
- Reset transitions to AVAILABLE
- Usage tracking is real-time
```

---

## Edge Cases (15 cases)

### EC-001: Concurrent Billing Attempts
- **Input**: Same usage event processed twice simultaneously
- **Expected**: Only one billing record created
- **Actual**: Idempotency key prevents duplicates
- **Note**: Return existing record for duplicate

### EC-002: Insufficient Balance During Processing
- **Input**: Balance drops between check and deduction
- **Expected**: Deduction fails, record marked failed
- **Actual**: Wallet service handles atomically
- **Note**: Retry with fresh balance check

### EC-003: Subscription Expires Mid-Billing
- **Input**: Subscription expires during calculation
- **Expected**: Fall through to paid billing
- **Actual**: Check at billing time, not calculation
- **Note**: Real-time subscription status

### EC-004: Free Tier Exactly Depleted
- **Input**: Usage exactly equals free tier remaining
- **Expected**: total_cost = 0, free_tier_remaining = 0
- **Actual**: Edge case handled correctly
- **Note**: Next usage will be billed

### EC-005: Very Large Usage Amount
- **Input**: usage_amount = 999999999
- **Expected**: Calculation succeeds, large total_cost
- **Actual**: Decimal precision handles large numbers
- **Note**: May exceed balance, requires payment

### EC-006: Zero Usage Amount
- **Input**: usage_amount = 0
- **Expected**: Record created with total_cost = 0
- **Actual**: Valid for tracking purposes
- **Note**: No billing method needed

### EC-007: Multiple Quotas for Same Service
- **Input**: User has both daily and monthly quota
- **Expected**: Most restrictive applies
- **Actual**: Check all applicable quotas
- **Note**: All quotas must allow usage

### EC-008: Quota Reset During Usage
- **Input**: Usage occurs exactly at period boundary
- **Expected**: Use new period's quota
- **Actual**: Atomic reset before check
- **Note**: No double-counting

### EC-009: Wallet Service Unavailable
- **Input**: Wallet service timeout during billing
- **Expected**: Record marked failed, retry later
- **Actual**: Error logged, graceful degradation
- **Note**: Background job retries

### EC-010: Subscription Service Unavailable
- **Input**: Subscription service unreachable
- **Expected**: Assume no subscription (fail-safe)
- **Actual**: Log warning, proceed with billing
- **Note**: May overbill, reconcile later

### EC-011: Product Price Not Found
- **Input**: Product ID has no configured price
- **Expected**: Use default price for service type
- **Actual**: Fallback pricing applied
- **Note**: Log warning for configuration

### EC-012: Billing Record Query Timeout
- **Input**: Large query with many records
- **Expected**: Pagination limits result size
- **Actual**: Max 100 records per page
- **Note**: Client handles pagination

### EC-013: Refund More Than Charged
- **Input**: Refund amount > original amount
- **Expected**: Rejected with validation error
- **Actual**: Check amount before processing
- **Note**: Partial refunds supported

### EC-014: Currency Mismatch
- **Input**: Usage in USD, wallet in CNY
- **Expected**: Currency conversion applied
- **Actual**: Convert at current rate
- **Note**: Exchange rate from config/service

### EC-015: Negative Free Tier (Debt)
- **Input**: Free tier overused (race condition)
- **Expected**: Clamp to zero, bill excess
- **Actual**: free_tier_remaining = max(0, remaining)
- **Note**: Prevents negative free tier

---

## Data Consistency Rules

### DC-001: Billing ID Uniqueness
- billing_id is primary key
- Enforced at database level
- UUID generation ensures uniqueness

### DC-002: Usage Record Reference
- usage_record_id links billing to usage
- One billing record per usage record
- Prevents double billing

### DC-003: User ID Consistency
- Billing.user_id from usage event
- Cannot be modified after creation
- Audit trail preserved

### DC-004: Amount Consistency
- total_amount = usage_amount × unit_price
- Verified at creation time
- Immutable after creation

### DC-005: Balance Consistency
- Wallet/credit balance updated atomically with billing
- Transaction ID links billing to balance change
- Reconciliation possible via transaction IDs

### DC-006: Quota Consistency
- quota_used updated atomically with billing
- Prevents over-allocation
- Reset resets to exact zero

---

## Integration Contracts

### Wallet Service Integration
- **Endpoint**: GET /api/v1/wallets/{user_id}/balance
- **When**: Cost calculation and billing processing
- **Expected Response**: 200 with wallet_balance, credit_balance
- **Error Handling**: Fail-safe - assume zero balance

### Subscription Service Integration
- **Endpoint**: GET /api/v1/subscriptions/user/{user_id}
- **When**: Cost calculation (subscription check)
- **Expected Response**: 200 with subscription details OR 404
- **Error Handling**: Fail-safe - assume no subscription

### Product Service Integration
- **Endpoint**: GET /api/v1/products/{product_id}/pricing
- **When**: Cost calculation (unit price lookup)
- **Expected Response**: 200 with unit_price, free_tier
- **Error Handling**: Use default pricing

### Session Service Integration
- **Event**: session.tokens_used
- **When**: Token consumption in session
- **Payload**: session_id, user_id, tokens_used, cost_usd
- **Expected Response**: Billing records usage asynchronously

### Notification Service Integration
- **Event**: billing.processed, quota.exceeded
- **When**: After billing or quota events
- **Payload**: Event details for user notification
- **Expected Response**: Notification sent asynchronously

---

## Error Handling Contracts

### Usage Recording Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 400 | "user_id is required" |
| Missing product_id | 400 | "product_id is required" |
| Invalid service_type | 400 | "service_type must be one of: ..." |
| Negative usage_amount | 422 | Validation error detail |
| Duplicate event | 200 | Returns existing record |

### Cost Calculation Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 400 | "user_id is required" |
| Missing product_id | 400 | "product_id is required" |
| Negative usage_amount | 422 | Validation error detail |
| Service unavailable | 500 | "Cost calculation failed" |

### Billing Processing Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Usage record not found | 404 | "Usage record not found: {id}" |
| Invalid billing_method | 400 | "billing_method must be one of: ..." |
| Insufficient credits | 402 | "Insufficient credit balance" |
| Insufficient wallet | 402 | "Insufficient wallet balance" |
| Already processed | 409 | "Billing already processed" |

### Quota Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Quota exceeded (hard) | 429 | "Quota exceeded for service_type" |
| Invalid service_type | 400 | "service_type must be one of: ..." |
| Negative requested_amount | 422 | Validation error detail |

### Query Errors
| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Invalid page | 422 | Validation error (ge=1) |
| Invalid page_size | 422 | Validation error (le=100) |
| Invalid status filter | 400 | "status must be one of: ..." |
| Invalid date range | 400 | "start_date must be before end_date" |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Billing Service Team
