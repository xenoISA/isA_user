# Order Service - Domain Context

## Business Taxonomy

### Core Entities

- **Order**: A transactional record representing a user's intent to purchase products, services, subscriptions, or credits. Contains pricing, payment status, and fulfillment information.

- **Order Item**: Individual line items within an order, representing specific products or services with quantity and pricing.

- **Order Status**: The lifecycle state of an order (pending, processing, completed, failed, cancelled, refunded).

- **Payment Status**: The payment processing state (pending, processing, completed, failed, refunded).

- **Order Type**: Classification of orders (purchase, subscription, credit_purchase, premium_upgrade).

### Supporting Concepts

- **Payment Intent**: External payment processor reference linking order to payment transaction.

- **Subscription Reference**: Link to recurring billing/subscription for subscription-type orders.

- **Wallet Reference**: Target wallet for credit-based transactions.

- **Order Expiration**: Time-bound validity for unpaid orders to prevent stale transactions.

- **Fulfillment Status**: Digital/physical delivery state for order completion.

---

## Domain Scenarios

### Scenario 1: Standard Product Purchase
- **Trigger**: User initiates checkout with items in cart
- **Flow**:
  1. Order created with PENDING status
  2. Payment intent generated via payment service
  3. User completes payment
  4. Order status updated to COMPLETED
  5. Fulfillment initiated
- **Outcome**: Order completed, products delivered
- **Events**: order.created, order.completed

### Scenario 2: Credit/Token Purchase
- **Trigger**: User purchases platform credits
- **Flow**:
  1. Order created with wallet_id reference
  2. Payment processed
  3. Credits added to wallet upon completion
  4. Order marked as completed
- **Outcome**: User wallet balance increased
- **Events**: order.created, order.completed, wallet.credits_added

### Scenario 3: Subscription Order
- **Trigger**: User subscribes to premium tier
- **Flow**:
  1. Order created with subscription_id reference
  2. Initial payment processed
  3. Subscription activated
  4. Recurring billing initiated
- **Outcome**: User gains subscription benefits
- **Events**: order.created, order.completed, subscription.created

### Scenario 4: Order Cancellation
- **Trigger**: User or system cancels pending order
- **Flow**:
  1. Validate order is cancellable (not completed/refunded)
  2. Cancel order with reason
  3. Process refund if applicable
  4. Notify relevant services
- **Outcome**: Order cancelled, refund processed
- **Events**: order.canceled

### Scenario 5: Order Expiration
- **Trigger**: Order timeout reached without payment
- **Flow**:
  1. System detects expired order
  2. Order status set to CANCELLED
  3. Reserved inventory released
  4. User notified
- **Outcome**: Order expired, resources freed
- **Events**: order.expired

### Scenario 6: Payment Failure Handling
- **Trigger**: Payment service reports failed transaction
- **Flow**:
  1. Receive payment.failed event
  2. Update order payment_status to FAILED
  3. Update order status to FAILED
  4. Notify user for retry
- **Outcome**: Order failed, user can retry
- **Events**: order.updated

### Scenario 7: Refund Processing
- **Trigger**: Refund approved for completed order
- **Flow**:
  1. Validate order is refundable
  2. Process refund via payment service
  3. Update order status to REFUNDED
  4. Reverse any credits/subscriptions
- **Outcome**: Funds returned to user
- **Events**: order.refunded

### Scenario 8: User Deletion Cascade
- **Trigger**: User account deleted
- **Flow**:
  1. Receive user.deleted event
  2. Cancel all pending orders
  3. Anonymize PII in historical orders
  4. Maintain financial records for compliance
- **Outcome**: User data processed per GDPR
- **Events**: (internal processing)

---

## Domain Events

### Published Events

1. **order.created** (EventType.ORDER_CREATED)
   - When: New order successfully created
   - Data: order_id, user_id, order_type, total_amount, currency, items
   - Consumers: payment_service, billing_service, notification_service

2. **order.updated** (EventType.ORDER_UPDATED)
   - When: Order status or data modified
   - Data: order_id, user_id, updated_fields, old_status, new_status
   - Consumers: notification_service, analytics_service

3. **order.completed** (EventType.ORDER_COMPLETED)
   - When: Order fully paid and processed
   - Data: order_id, user_id, order_type, total_amount, transaction_id, credits_added
   - Consumers: wallet_service, subscription_service, fulfillment_service

4. **order.canceled** (EventType.ORDER_CANCELED)
   - When: Order cancelled by user or system
   - Data: order_id, user_id, order_type, total_amount, reason, refund_amount
   - Consumers: payment_service, wallet_service, inventory_service

5. **order.expired** (EventType.ORDER_EXPIRED)
   - When: Order timeout without payment
   - Data: order_id, user_id, order_type, total_amount, expired_at
   - Consumers: notification_service, inventory_service

### Consumed Events

1. **payment.completed** from payment_service
   - Action: Auto-complete associated order

2. **payment.failed** from payment_service
   - Action: Mark order as payment failed

3. **payment.refunded** from payment_service
   - Action: Update order to refunded status

4. **subscription.created** from subscription_service
   - Action: Create tracking order for subscription

5. **subscription.canceled** from subscription_service
   - Action: Cancel pending subscription orders

6. **wallet.credits_added** from wallet_service
   - Action: Fulfill credit purchase orders

7. **user.deleted** from account_service
   - Action: Cancel pending orders, anonymize data

---

## Core Concepts

### Order Lifecycle State Machine

Orders follow a defined state machine with valid transitions:

```
                    ┌──────────────┐
                    │   PENDING    │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  PROCESSING  │ │   FAILED     │ │  CANCELLED   │
    └──────┬───────┘ └──────────────┘ └──────────────┘
           │
           ▼
    ┌──────────────┐
    │  COMPLETED   │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   REFUNDED   │
    └──────────────┘
```

### Payment Integration Model

Order service coordinates with payment service through:
- Payment intent creation for new orders
- Status synchronization via events
- Refund orchestration
- Transaction reconciliation

### Order Type Semantics

| Type | Behavior | Required Fields |
|------|----------|-----------------|
| PURCHASE | One-time product purchase | items |
| SUBSCRIPTION | Recurring billing setup | subscription_id |
| CREDIT_PURCHASE | Platform credit acquisition | wallet_id |
| PREMIUM_UPGRADE | Account tier upgrade | subscription_id |

### Currency and Pricing

- All amounts stored as Decimal for precision
- Currency tracked per order (default: USD)
- Supports multi-currency revenue reporting
- Tax and discount amounts tracked separately

---

## High-Level Business Rules (35 rules)

### Order Creation Rules (BR-ORD-001 to BR-ORD-010)

**BR-ORD-001: User ID Required**
- Order MUST have valid user_id
- System validates user exists via account service
- Empty/whitespace user_id rejected

**BR-ORD-002: Positive Amount Required**
- total_amount MUST be > 0
- Zero or negative amounts rejected
- Decimal precision maintained

**BR-ORD-003: Credit Purchase Requires Wallet**
- CREDIT_PURCHASE type MUST have wallet_id
- wallet_id validated against wallet service
- Missing wallet_id returns validation error

**BR-ORD-004: Subscription Order Requires Subscription ID**
- SUBSCRIPTION type MUST have subscription_id
- Links order to recurring billing
- Missing subscription_id rejected

**BR-ORD-005: Default Expiration**
- Orders default to 30-minute expiration
- Custom expires_in_minutes accepted
- Expired orders auto-cancelled

**BR-ORD-006: Initial Status**
- New orders start with status=PENDING
- payment_status defaults to PENDING
- Cannot create in COMPLETED state

**BR-ORD-007: Currency Validation**
- Currency code validated (USD, EUR, etc.)
- Default currency is USD
- Invalid currency rejected

**BR-ORD-008: Items Structure**
- Items must be valid JSON array
- Each item should have product_id, quantity, price
- Empty items allowed (for credit/subscription)

**BR-ORD-009: Metadata Limits**
- Metadata must be valid JSON object
- Size limits enforced
- Sensitive data not stored in metadata

**BR-ORD-010: Idempotency Support**
- Duplicate order detection available
- Same user+items within window detected
- Prevents accidental double orders

### Order Update Rules (BR-ORD-011 to BR-ORD-018)

**BR-ORD-011: Status Transitions**
- Only valid state transitions allowed
- PENDING -> PROCESSING, FAILED, CANCELLED
- PROCESSING -> COMPLETED, FAILED
- COMPLETED -> REFUNDED

**BR-ORD-012: Immutable Completed Orders**
- Completed order amounts cannot change
- Only status can transition to REFUNDED
- Audit trail maintained

**BR-ORD-013: Payment Intent Update**
- payment_intent_id can be set once
- Cannot change after payment initiated
- Links to external payment system

**BR-ORD-014: Metadata Merge**
- Updates merge with existing metadata
- Previous values preserved unless overwritten
- Audit fields auto-appended

**BR-ORD-015: Updated Timestamp**
- updated_at auto-set on any change
- Cannot be manually overridden
- Used for optimistic locking

**BR-ORD-016: Payment Status Sync**
- payment_status updated via events
- Manual updates restricted
- Must reflect actual payment state

**BR-ORD-017: Completion Requirements**
- Order completion requires payment_confirmed=true
- transaction_id should be provided
- credits_added set for credit purchases

**BR-ORD-018: Processing State Duration**
- PROCESSING state time-limited
- Auto-expire to FAILED after timeout
- Prevents stuck orders

### Order Cancellation Rules (BR-ORD-019 to BR-ORD-025)

**BR-ORD-019: Cancellable States**
- Only PENDING and PROCESSING cancellable
- COMPLETED orders require refund flow
- CANCELLED/REFUNDED cannot be cancelled

**BR-ORD-020: Cancellation Reason**
- Reason should be provided
- Stored in order metadata
- Used for analytics and support

**BR-ORD-021: Refund Amount Validation**
- refund_amount <= total_amount
- Partial refunds supported
- Full refund default if not specified

**BR-ORD-022: Wallet Refund Processing**
- Credit purchases refunded to wallet
- Automatic credit restoration
- Transaction recorded

**BR-ORD-023: Payment Refund Coordination**
- External payment refunds coordinated
- Payment service handles actual refund
- Order updated on refund completion

**BR-ORD-024: Cancelled Timestamp**
- cancelled_at set on cancellation
- Cancellation is permanent
- Cannot be undone

**BR-ORD-025: Event Publishing**
- order.canceled event always published
- Contains refund details
- Enables downstream cleanup

### Query and Search Rules (BR-ORD-026 to BR-ORD-030)

**BR-ORD-026: Pagination Limits**
- Maximum 100 orders per page
- Default page size is 50
- Offset-based pagination

**BR-ORD-027: User Isolation**
- Users can only see own orders
- Admin can see all orders
- Service accounts have full access

**BR-ORD-028: Search Scope**
- Search queries order_id, order_type, status
- Partial matching supported
- Case-insensitive search

**BR-ORD-029: Date Range Filtering**
- start_date and end_date filters
- Based on created_at timestamp
- Both inclusive

**BR-ORD-030: Status Filtering**
- Filter by order_status
- Filter by payment_status
- Multiple filters combinable

### Integration Rules (BR-ORD-031 to BR-ORD-035)

**BR-ORD-031: Event Idempotency**
- Event handlers track processed IDs
- Duplicate events safely ignored
- Prevents double processing

**BR-ORD-032: Service Discovery**
- Payment/Wallet URLs from Consul
- Fallback to environment variables
- Health checks before calls

**BR-ORD-033: Async Event Processing**
- Events processed asynchronously
- Failures logged, not propagated
- Retry mechanisms in place

**BR-ORD-034: Cross-Service Consistency**
- Eventually consistent with other services
- Compensation actions on failure
- Saga pattern for complex flows

**BR-ORD-035: Audit Trail**
- All order changes logged
- User actions timestamped
- Compliance with financial regulations

---

## Glossary

| Term | Definition |
|------|------------|
| Order | Transaction record for purchase intent |
| Payment Intent | External payment processor reference |
| Fulfillment | Delivery of purchased goods/services |
| Refund | Return of payment to customer |
| Credit | Platform currency/token for services |
| Subscription | Recurring billing arrangement |
| Saga | Distributed transaction pattern |
| Idempotency | Same operation produces same result |
