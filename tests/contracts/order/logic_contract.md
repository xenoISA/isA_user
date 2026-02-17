# Order Service - Logic Contract

## Business Rules (50 rules)

### Order Creation Rules (BR-ORD-001 to BR-ORD-012)

**BR-ORD-001: User ID Required**
- Order MUST have a non-empty user_id
- System validates user_id is not null, empty, or whitespace
- Error returned: "user_id is required"
- Example: `user_id = ""` -> ValidationError

**BR-ORD-002: User ID Format**
- user_id SHOULD follow pattern `user_{hex_string}`
- System accepts any non-empty string for flexibility
- Validation is lenient for external user IDs

**BR-ORD-003: Positive Amount Required**
- total_amount MUST be greater than 0
- System rejects zero and negative amounts
- Error returned: "total_amount must be positive"
- Example: `total_amount = 0` -> ValidationError

**BR-ORD-004: Amount Precision**
- Amounts stored with 2 decimal places
- System rounds amounts to nearest cent
- Maximum precision: Decimal(15, 2)

**BR-ORD-005: Currency Validation**
- currency MUST be valid ISO 4217 code
- Supported currencies: USD, EUR, GBP, CAD, AUD, JPY, CNY
- Default currency: USD
- Error returned: "Invalid currency: {code}"

**BR-ORD-006: Order Type Validation**
- order_type MUST be one of: purchase, subscription, credit_purchase, premium_upgrade
- System rejects unknown order types
- Error returned: "Invalid order_type"

**BR-ORD-007: Credit Purchase Requires Wallet**
- CREDIT_PURCHASE type MUST have wallet_id
- wallet_id cannot be null or empty
- Error returned: "wallet_id is required for credit purchases"
- Example: `{order_type: "credit_purchase", wallet_id: null}` -> ValidationError

**BR-ORD-008: Subscription Requires Subscription ID**
- SUBSCRIPTION type MUST have subscription_id
- subscription_id cannot be null or empty
- Error returned: "subscription_id is required for subscription orders"
- Example: `{order_type: "subscription", subscription_id: null}` -> ValidationError

**BR-ORD-009: Initial Order Status**
- New orders MUST start with status = "pending"
- Cannot create order in completed, failed, or cancelled state
- payment_status defaults to "pending"

**BR-ORD-010: Order Expiration Default**
- Orders default to 30-minute expiration if not specified
- expires_in_minutes accepts 1-1440 (1 minute to 24 hours)
- System calculates expires_at from creation time

**BR-ORD-011: Order ID Generation**
- order_id auto-generated with format `order_{12_char_hex}`
- ID must be unique across all orders
- Cannot be manually specified on creation

**BR-ORD-012: Items Validation**
- items must be valid JSON array
- Empty items array allowed (for credit/subscription orders)
- Each item should have product_id, quantity, unit_price

### Order Status Transition Rules (BR-ORD-013 to BR-ORD-022)

**BR-ORD-013: Valid Status Values**
- Status MUST be one of: pending, processing, completed, failed, cancelled, refunded
- System rejects unknown status values
- Error returned: "Invalid status"

**BR-ORD-014: Pending Transitions**
- PENDING can transition to: PROCESSING, FAILED, CANCELLED
- Cannot transition directly to COMPLETED or REFUNDED
- Example: `pending -> completed` -> InvalidStateError

**BR-ORD-015: Processing Transitions**
- PROCESSING can transition to: COMPLETED, FAILED, CANCELLED
- Cannot transition back to PENDING
- Example: `processing -> pending` -> InvalidStateError

**BR-ORD-016: Completed Transitions**
- COMPLETED can only transition to: REFUNDED
- Cannot be cancelled after completion
- Example: `completed -> cancelled` -> InvalidStateError

**BR-ORD-017: Failed Terminal State**
- FAILED is a terminal state for payment failures
- No outbound transitions allowed
- Order must be recreated to retry

**BR-ORD-018: Cancelled Terminal State**
- CANCELLED is a terminal state
- No outbound transitions allowed
- Cannot be reactivated or refunded
- Example: `cancelled -> pending` -> InvalidStateError

**BR-ORD-019: Refunded Terminal State**
- REFUNDED is a terminal state
- No outbound transitions allowed
- Represents final disposition of order

**BR-ORD-020: Auto Status Update Timestamps**
- updated_at auto-set on any status change
- completed_at set when status = COMPLETED
- cancelled_at set when status = CANCELLED

**BR-ORD-021: Status History Preservation**
- Previous status preserved in metadata for audit
- All transitions logged with timestamp
- Cannot be manually overridden

**BR-ORD-022: Payment Status Correlation**
- payment_status should correlate with order status
- COMPLETED order should have COMPLETED payment_status
- REFUNDED order should have REFUNDED payment_status

### Order Cancellation Rules (BR-ORD-023 to BR-ORD-030)

**BR-ORD-023: Cancellable States**
- Only PENDING and PROCESSING orders can be cancelled
- COMPLETED, FAILED, CANCELLED, REFUNDED cannot be cancelled
- Error returned: "Cannot cancel order with status: {status}"

**BR-ORD-024: Cancellation Reason**
- Reason should be provided for cancellation
- Stored in cancellation_reason field
- Used for analytics and customer support

**BR-ORD-025: Refund Amount Validation**
- refund_amount cannot exceed total_amount
- Partial refunds allowed (refund_amount < total_amount)
- Full refund if refund_amount not specified or equals total
- Error returned: "Refund amount exceeds order total"

**BR-ORD-026: Automatic Refund Processing**
- If order has payment_intent_id and refund_amount > 0
- System initiates refund through payment service
- Wallet credits restored for credit purchases

**BR-ORD-027: Cancelled Status Finality**
- Once cancelled, order cannot be modified
- Metadata updates still allowed for auditing
- Payment status unchanged after cancellation

**BR-ORD-028: Cancellation Event Publishing**
- order.canceled event always published on cancellation
- Event contains order_id, user_id, reason, refund_amount
- Enables downstream services to react

**BR-ORD-029: Expired Order Handling**
- Expired orders auto-cancelled by system
- cancellation_reason set to "Order expired"
- order.expired event published

**BR-ORD-030: Cancellation By Field**
- cancelled_by tracks who initiated cancellation
- Values: user_id, "system", "admin"
- Used for audit and support

### Order Completion Rules (BR-ORD-031 to BR-ORD-038)

**BR-ORD-031: Payment Confirmation Required**
- payment_confirmed MUST be true to complete order
- False value returns error
- Error returned: "Payment not confirmed"

**BR-ORD-032: Transaction ID Recording**
- transaction_id should be provided on completion
- Links order to payment transaction
- Stored in payment_intent_id if not already set

**BR-ORD-033: Credit Purchase Fulfillment**
- If order_type = CREDIT_PURCHASE and credits_added provided
- System adds credits to user's wallet
- Calls wallet service with amount and order reference

**BR-ORD-034: Completion Timestamp**
- completed_at auto-set on completion
- Cannot be manually overridden
- Used for revenue reporting

**BR-ORD-035: Event Publishing on Completion**
- order.completed event published
- Contains order_id, user_id, transaction_id, credits_added
- Triggers downstream fulfillment

**BR-ORD-036: Idempotent Completion**
- Completing already-completed order is no-op
- Returns success with existing order data
- Does not publish duplicate events

**BR-ORD-037: Payment Status Update**
- payment_status set to COMPLETED on order completion
- Must transition from PENDING or PROCESSING
- Cannot complete if already FAILED

**BR-ORD-038: Order Immutability After Completion**
- Amount, items, order_type cannot be modified
- Only status can transition to REFUNDED
- Metadata updates allowed for auditing

### Query and Search Rules (BR-ORD-039 to BR-ORD-045)

**BR-ORD-039: Pagination Limits**
- page_size cannot exceed 100
- Default page_size is 50
- page starts at 1 (1-indexed)

**BR-ORD-040: User Isolation**
- Regular users can only see their own orders
- Admin users can see all orders
- Service accounts bypass isolation

**BR-ORD-041: Search Query Requirements**
- query cannot be empty or whitespace
- Minimum length: 1 character
- Maximum length: 100 characters

**BR-ORD-042: Search Scope**
- Search matches: order_id, order_type, status
- Case-insensitive matching
- Partial match supported (ILIKE)

**BR-ORD-043: Date Range Filtering**
- start_date and end_date filter by created_at
- Both dates are inclusive
- Missing dates means no constraint on that end

**BR-ORD-044: Multiple Filter Combination**
- All filters combined with AND logic
- Empty filter returns all (within pagination)
- Invalid filter values return validation error

**BR-ORD-045: Sort Order**
- Default sort: created_at DESC (newest first)
- Consistent ordering for pagination
- Cannot be customized via API

### Integration Rules (BR-ORD-046 to BR-ORD-050)

**BR-ORD-046: Event Idempotency**
- Each event has unique event_id
- Processed event IDs tracked in memory
- Duplicate events safely ignored

**BR-ORD-047: Payment Event Processing**
- payment.completed auto-completes matching order
- payment.failed marks order as failed
- payment.refunded marks order as refunded

**BR-ORD-048: User Deletion Handling**
- user.deleted event triggers order cleanup
- Pending orders cancelled
- PII anonymized in historical orders

**BR-ORD-049: Subscription Event Processing**
- subscription.created creates tracking order
- subscription.canceled cancels pending subscription orders
- Links maintained via subscription_id

**BR-ORD-050: Service Resilience**
- External service failures logged, not propagated
- Order operations succeed even if events fail
- Retry mechanisms for critical operations

---

## State Machines (4 machines)

### Order Lifecycle State Machine

```
States:
- PENDING: Order created, awaiting payment
- PROCESSING: Payment in progress
- COMPLETED: Payment confirmed, order fulfilled
- FAILED: Payment or processing failed
- CANCELLED: Order cancelled before completion
- REFUNDED: Completed order refunded

Transitions:
PENDING -> PROCESSING (on payment_initiated)
PENDING -> CANCELLED (on user_cancel or order_expired)
PENDING -> FAILED (on validation_failure)

PROCESSING -> COMPLETED (on payment_completed)
PROCESSING -> FAILED (on payment_failed)
PROCESSING -> CANCELLED (on cancel_request)

COMPLETED -> REFUNDED (on refund_processed)

FAILED -> [terminal]
CANCELLED -> [terminal]
REFUNDED -> [terminal]

Rules:
- PENDING is the only valid initial state
- Terminal states have no outbound transitions
- COMPLETED can only transition to REFUNDED
- All transitions update updated_at timestamp
```

### Payment Status State Machine

```
States:
- PENDING: Awaiting payment initiation
- PROCESSING: Payment being processed
- COMPLETED: Payment successful
- FAILED: Payment failed
- REFUNDED: Payment refunded

Transitions:
PENDING -> PROCESSING (on payment_intent_created)
PENDING -> FAILED (on validation_error)

PROCESSING -> COMPLETED (on payment_success)
PROCESSING -> FAILED (on payment_error)

COMPLETED -> REFUNDED (on refund_success)

FAILED -> [terminal]
REFUNDED -> [terminal]

Rules:
- Should correlate with order status
- COMPLETED payment implies order can be completed
- FAILED payment may allow retry (new payment intent)
```

### Credit Purchase Flow State Machine

```
States:
- INITIATED: Order created with wallet_id
- PAYMENT_PENDING: Awaiting credit card payment
- CREDITING: Adding credits to wallet
- FULFILLED: Credits added successfully
- FAILED: Credit addition failed

Transitions:
INITIATED -> PAYMENT_PENDING (on order_created)
PAYMENT_PENDING -> CREDITING (on payment_completed)
CREDITING -> FULFILLED (on wallet_credits_added)
PAYMENT_PENDING -> FAILED (on payment_failed)
CREDITING -> FAILED (on wallet_error)

Rules:
- wallet_id must be valid
- credits_added recorded in order
- Refund reverses credit addition
```

### Order Expiration Flow

```
States:
- ACTIVE: Order within expiration window
- EXPIRED: Order past expiration time
- CLEANED_UP: Resources released

Transitions:
ACTIVE -> EXPIRED (on expiration_time_reached)
EXPIRED -> CLEANED_UP (on cleanup_job_run)

Rules:
- Only PENDING orders can expire
- PROCESSING orders extend timeout
- Completed/Cancelled orders don't expire
- Expiration publishes order.expired event
```

---

## Edge Cases (15 cases)

**EC-001: Concurrent Order Completion**
- Input: Two simultaneous complete requests for same order
- Expected: First succeeds, second returns success (idempotent)
- Actual behavior: Database transaction ensures consistency

**EC-002: Payment Event Before Order**
- Input: payment.completed event arrives before order exists
- Expected: Event logged as warning, no error
- Actual behavior: Order not found, event ignored

**EC-003: Double Cancellation Request**
- Input: Cancel request on already cancelled order
- Expected: Return error "Cannot cancel order with status: cancelled"
- Actual behavior: Validation prevents double cancellation

**EC-004: Refund Exceeds Total**
- Input: refund_amount = 150 for order with total_amount = 100
- Expected: Validation error "Refund amount exceeds order total"
- Actual behavior: Request rejected before processing

**EC-005: Zero Items Order**
- Input: Order with empty items array for PURCHASE type
- Expected: Order created successfully (items optional)
- Actual behavior: Empty items allowed for flexibility

**EC-006: Very Large Amount**
- Input: total_amount = 9999999999.99 (max decimal)
- Expected: Order created if within database precision
- Actual behavior: Decimal(15,2) supports up to 10^13

**EC-007: Expired Order Completion**
- Input: Complete request on expired order
- Expected: Error "Order has expired"
- Actual behavior: Status check catches expired state

**EC-008: Multiple Payment Intents**
- Input: Update order with new payment_intent_id
- Expected: Previous intent preserved, new one appended to metadata
- Actual behavior: Primary payment_intent_id updated

**EC-009: User Deletion Mid-Order**
- Input: user.deleted event while order is PROCESSING
- Expected: Order cancelled with reason "user_deleted"
- Actual behavior: Pending orders cancelled, processing orders completed

**EC-010: Subscription Cancel Before Order Complete**
- Input: subscription.canceled event for PENDING subscription order
- Expected: Order cancelled with reason "subscription_canceled"
- Actual behavior: Pending subscription orders cancelled

**EC-011: Unicode in Order Metadata**
- Input: metadata with unicode characters, emojis
- Expected: Stored and retrieved correctly
- Actual behavior: JSONB supports full unicode

**EC-012: Null vs Missing Fields**
- Input: Update request with explicit null vs missing field
- Expected: Null clears field, missing preserves existing
- Actual behavior: Pydantic optional fields handle both

**EC-013: Rapid Status Changes**
- Input: Quick sequence: pending -> processing -> completed
- Expected: All transitions logged with timestamps
- Actual behavior: Each update recorded sequentially

**EC-014: Search with Special Characters**
- Input: query = "order_abc%123"
- Expected: Literal search (% not interpreted as wildcard)
- Actual behavior: Parameterized query escapes special chars

**EC-015: Pagination Beyond Data**
- Input: page = 1000 when only 50 orders exist
- Expected: Return empty list with has_next = false
- Actual behavior: Valid empty response, no error

---

## Data Consistency Rules

**DC-001: Order ID Uniqueness**
- order_id MUST be unique across all orders
- Generated using UUID to ensure uniqueness
- Database enforces PRIMARY KEY constraint

**DC-002: Amount Consistency**
- total_amount stored as entered
- final_amount = total_amount - discount_amount + tax_amount
- Amounts never recalculated after creation

**DC-003: Timestamp Consistency**
- created_at never modified after creation
- updated_at updated on every modification
- completed_at/cancelled_at set once, never changed

**DC-004: Status-Payment Correlation**
- Order status and payment_status should be consistent
- COMPLETED order should not have FAILED payment_status
- System does not enforce strict correlation (eventual consistency)

**DC-005: Items Immutability**
- items cannot be modified after order creation
- Represents snapshot of purchase at creation time
- Changes require new order

**DC-006: Currency Immutability**
- currency cannot be changed after creation
- All amounts in same currency per order
- Multi-currency requires separate orders

---

## Integration Contracts

### Payment Service Integration

**Endpoint**: POST /api/payments/intent
- **When**: Order created, payment needed
- **Payload**:
  ```json
  {
    "amount": 99.99,
    "currency": "USD",
    "description": "Order order_xxx",
    "user_id": "user_xxx",
    "order_id": "order_xxx",
    "metadata": {"order_type": "purchase"}
  }
  ```
- **Expected Response**: 200 OK with payment_intent_id
- **Error Handling**: Log warning, continue without payment intent

### Wallet Service Integration

**Endpoint**: POST /api/v1/wallets/{wallet_id}/deposit
- **When**: Credit purchase completed
- **Payload**:
  ```json
  {
    "user_id": "user_xxx",
    "amount": 100.00,
    "order_id": "order_xxx",
    "description": "Credits from order order_xxx",
    "transaction_type": "deposit"
  }
  ```
- **Expected Response**: 200 OK with success: true
- **Error Handling**: Log error, order still marked complete

### Account Service Integration

**Endpoint**: GET /api/v1/accounts/{user_id}/profile
- **When**: Order creation (optional validation)
- **Expected Response**: 200 OK with user profile
- **Error Handling**: Log warning, proceed with order creation

---

## Error Handling Contracts

### HTTP Error Codes

| Error Type | HTTP Code | Error Code | Example Message |
|------------|-----------|------------|-----------------|
| Missing required field | 422 | VALIDATION_ERROR | "user_id is required" |
| Invalid field value | 400 | VALIDATION_ERROR | "total_amount must be positive" |
| Order not found | 404 | ORDER_NOT_FOUND | "Order not found: order_xxx" |
| Invalid state transition | 400 | INVALID_STATUS | "Cannot cancel order with status: completed" |
| Payment not confirmed | 400 | PAYMENT_NOT_CONFIRMED | "Payment not confirmed" |
| Refund exceeds total | 400 | VALIDATION_ERROR | "Refund amount exceeds order total" |
| Database error | 500 | CREATE_ERROR | "Failed to create order" |
| Service unavailable | 503 | SERVICE_ERROR | "Order service not initialized" |

### Error Response Format

```json
{
  "success": false,
  "order": null,
  "message": "Error description",
  "error_code": "ERROR_CODE"
}
```

### Validation Error Format (FastAPI)

```json
{
  "detail": [
    {
      "loc": ["body", "total_amount"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

## Event Contracts

### Published Events

**order.created**
```json
{
  "event_type": "ORDER_CREATED",
  "source": "order_service",
  "data": {
    "order_id": "order_xxx",
    "user_id": "user_xxx",
    "order_type": "purchase",
    "total_amount": 99.99,
    "currency": "USD",
    "payment_intent_id": null,
    "subscription_id": null,
    "wallet_id": null,
    "items": [...],
    "metadata": {}
  }
}
```

**order.completed**
```json
{
  "event_type": "ORDER_COMPLETED",
  "source": "order_service",
  "data": {
    "order_id": "order_xxx",
    "user_id": "user_xxx",
    "order_type": "purchase",
    "total_amount": 99.99,
    "currency": "USD",
    "payment_id": "pi_xxx",
    "transaction_id": "txn_xxx",
    "credits_added": null
  }
}
```

**order.canceled**
```json
{
  "event_type": "ORDER_CANCELED",
  "source": "order_service",
  "data": {
    "order_id": "order_xxx",
    "user_id": "user_xxx",
    "order_type": "purchase",
    "total_amount": 99.99,
    "currency": "USD",
    "cancellation_reason": "User requested",
    "refund_amount": 99.99
  }
}
```

### Consumed Events

**payment.completed** (from payment_service)
- Handler: `handle_payment_completed`
- Action: Find order by payment_intent_id, call complete_order

**payment.failed** (from payment_service)
- Handler: `handle_payment_failed`
- Action: Find order by payment_intent_id, update status to FAILED

**user.deleted** (from account_service)
- Handler: `handle_user_deleted`
- Action: Cancel pending orders, anonymize historical orders
