# Wallet Service Logic Contract

**Business Rules and Specifications for Wallet Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for wallet service behavior.

**Credit System**: 1 Credit = $0.00001 USD (100,000 Credits = $1 USD)

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)
7. [Performance SLAs](#performance-slas)

---

## Business Rules

### Wallet Management Rules

### BR-WAL-001: One Primary FIAT Wallet Per User
**Given**: Valid wallet creation request with wallet_type=FIAT
**When**: User already has a FIAT wallet
**Then**:
- Creation fails with informative message
- Returns existing wallet_id
- `success=False` in response
- No duplicate wallet created

**Validation Rules**:
- Each user can have only ONE FIAT wallet
- Multiple CRYPTO or HYBRID wallets allowed
- Primary wallet auto-created on user.created event

**Edge Cases**:
- Duplicate FIAT request → Returns existing wallet info
- CRYPTO wallet when FIAT exists → Allowed

---

### BR-WAL-002: User Validation Before Creation
**Given**: Wallet creation request
**When**: User does not exist in account_service
**Then**:
- Warning logged
- Creation may proceed (graceful degradation)
- account_client failure doesn't block wallet creation

**Validation Rules**:
- `user_id`: Required, non-empty string
- User validation is best-effort (if client available)
- No strict enforcement (allows service independence)

**Implementation**:
```python
async def validate_user_exists(self, user_id: str) -> bool:
    if not self.account_client:
        logger.warning("Account client not configured, skipping validation")
        return True  # Allow operation to proceed
    try:
        user = await self.account_client.get_account(user_id)
        return user is not None
    except Exception:
        return True  # Graceful degradation
```

---

### BR-WAL-003: Wallet Uniqueness by Type
**Given**: Wallet creation request for existing user
**When**: User already has wallet of requested type
**Then**:
- FIAT: Returns existing wallet (BR-WAL-001)
- CRYPTO: Creates new wallet (multiple allowed)
- HYBRID: Creates new wallet (multiple allowed)

**Unique Constraint**:
- (user_id, wallet_type) for FIAT only
- No constraint for CRYPTO/HYBRID

---

### BR-WAL-004: Initial Balance Validation
**Given**: Wallet creation with initial_balance
**When**: initial_balance is negative
**Then**:
- **422 Validation Error** from Pydantic
- Rejected before reaching service
- Error: "initial_balance must be >= 0"

**Validation Rules**:
```python
initial_balance: Decimal = Field(ge=0, default=Decimal(0))
```

**Initial Transaction**:
- If initial_balance > 0, creates DEPOSIT transaction
- Transaction description: "Initial wallet funding"
- Transaction metadata: `{"initial_funding": True}`

---

### BR-WAL-005: Currency Immutability
**Given**: Existing wallet
**When**: Attempting to change currency
**Then**:
- Currency cannot be changed after creation
- Update operations ignore currency field
- New currency requires new wallet

**Reason**: Prevents accounting complications, maintains audit integrity

---

### BR-WAL-006: Wallet Types
**Given**: Wallet creation request
**When**: wallet_type specified
**Then**:
- `FIAT`: Traditional credits/points (default)
- `CRYPTO`: Blockchain-based tokens
- `HYBRID`: Both fiat and crypto

**Validation**:
```python
wallet_type: str = Field(pattern="^(fiat|crypto|hybrid)$")
```

---

### Balance Rules

### BR-BAL-001: Non-Negative Balance Invariant
**Given**: Any balance-modifying operation
**When**: Operation would result in negative balance
**Then**:
- Operation fails
- Returns `success=False`
- Message: "Insufficient balance"
- No transaction created
- Balance remains unchanged

**Critical Rule**: Balance MUST NEVER go negative

**Implementation**:
```python
if wallet.available_balance < amount:
    return None  # Repository returns None on insufficient balance
```

---

### BR-BAL-002: Available Balance Calculation
**Given**: Wallet with balance and locked_balance
**When**: Available balance queried
**Then**:
- `available_balance = balance - locked_balance`
- Only available_balance can be spent
- Locked balance reserved for pending operations

**Formula**:
```python
available_balance = total_balance - locked_balance
```

**Spending Check**:
```python
if wallet.available_balance < amount:
    return None  # Insufficient funds
```

---

### BR-BAL-003: Locked Balance Constraints
**Given**: Lock balance request
**When**: Attempting to lock funds
**Then**:
- Locked balance MUST be <= Total balance
- Cannot lock more than available
- Locks released after operation completes

**Invariant**: `locked_balance <= balance`

---

### BR-BAL-004: Balance Precision
**Given**: Any monetary operation
**When**: Amounts are calculated
**Then**:
- 8 decimal places for all amounts
- Use Decimal type (no floating point)
- No rounding errors in calculations

**Precision**:
```python
amount: Decimal = Field(decimal_places=8)
```

---

### BR-BAL-005: Zero Balance Validity
**Given**: Wallet with zero balance
**When**: Operations attempted
**Then**:
- Zero balance is valid state
- Deposits allowed
- Withdrawals/Consumes fail (BR-BAL-001)
- No minimum balance requirement

---

### Transaction Rules

### BR-TXN-001: Transaction Immutability
**Given**: Created transaction
**When**: Modification attempted
**Then**:
- Transactions MUST NOT be modified after creation
- Only refund creates reversal
- No DELETE or UPDATE on transactions
- Audit trail preserved forever

**Exception**: Blockchain status updates allowed for pending transactions

---

### BR-TXN-002: Transaction Amount Positive
**Given**: Transaction creation
**When**: Amount specified
**Then**:
- Transaction amount MUST be > 0
- Zero amount transactions rejected
- Negative handled by transaction_type

**Validation**:
```python
amount: Decimal = Field(gt=0)
```

---

### BR-TXN-003: Balance Recording
**Given**: Any transaction
**When**: Transaction created
**Then**:
- Records `balance_before` (pre-operation balance)
- Records `balance_after` (post-operation balance)
- Enables balance reconstruction from transactions
- Audit trail requirement

**Example**:
```json
{
  "amount": 100,
  "balance_before": 500,
  "balance_after": 600,
  "transaction_type": "deposit"
}
```

---

### BR-TXN-004: Reference ID Linkage
**Given**: Transaction with external reference
**When**: reference_id provided
**Then**:
- Links to external systems (payment_id, billing_record_id)
- Optional but recommended for traceability
- Used for idempotency checks
- Enables cross-service reconciliation

**Usage**:
- Deposit from payment: `reference_id = payment_id`
- Consume for billing: `usage_record_id` set
- Transfer: Both transactions share reference

---

### BR-TXN-005: Transaction Type Flow
**Given**: Transaction type
**When**: Transaction processed
**Then**:
- `DEPOSIT`: Adds to balance
- `WITHDRAW`: Subtracts from balance
- `CONSUME`: Subtracts from balance
- `REFUND`: Adds to balance (reversal)
- `TRANSFER`: Creates paired transactions (out/in)
- `REWARD`: Adds to balance
- `FEE`: Subtracts from balance

**Balance Changes**:
| Type | Balance Change |
|------|----------------|
| DEPOSIT | +amount |
| WITHDRAW | -amount |
| CONSUME | -amount |
| REFUND | +amount |
| TRANSFER (out) | -amount |
| TRANSFER (in) | +amount |
| REWARD | +amount |
| FEE | -amount |

---

### BR-TXN-006: UTC Timestamp Requirement
**Given**: Transaction creation
**When**: Timestamps recorded
**Then**:
- All timestamps in UTC timezone
- ISO 8601 format for events
- PostgreSQL TIMESTAMPTZ storage
- Consistent cross-region ordering

**Implementation**:
```python
created_at = datetime.now(timezone.utc).isoformat()
```

---

### Deposit Rules

### BR-DEP-001: Deposit Requires Valid Wallet
**Given**: Deposit request
**When**: Wallet does not exist
**Then**:
- Returns `success=False`
- Message: "Wallet not found"
- No transaction created

**Validation**:
```python
wallet = await self.repository.get_wallet(wallet_id)
if not wallet:
    return WalletResponse(success=False, message="Wallet not found")
```

---

### BR-DEP-002: Deposit Amount Validation
**Given**: Deposit request
**When**: Amount validated
**Then**:
- Amount MUST be > 0
- No maximum limit (configurable in future)
- No currency conversion

**Validation**:
```python
amount: Decimal = Field(gt=0)
```

---

### BR-DEP-003: Deposit Event Publishing
**Given**: Successful deposit
**When**: Transaction completed
**Then**:
- Publishes `wallet.deposited` event
- Event includes: wallet_id, user_id, amount, balance_before, balance_after
- Event failure logged but doesn't block operation

**Event Data**:
```json
{
  "wallet_id": "wallet_123",
  "user_id": "user_456",
  "transaction_id": "txn_789",
  "amount": 100.0,
  "balance_before": 500.0,
  "balance_after": 600.0,
  "reference_id": "payment_abc",
  "timestamp": "2025-12-15T10:00:00Z"
}
```

---

### Withdrawal Rules

### BR-WDR-001: Withdrawal Balance Check
**Given**: Withdrawal request
**When**: Amount > available_balance
**Then**:
- Returns `success=False`
- Message: "Insufficient balance or withdrawal failed"
- No transaction created
- No balance change

**Check**:
```python
if wallet.available_balance < amount:
    return None
```

---

### BR-WDR-002: Withdrawal Destination Optional
**Given**: Withdrawal request
**When**: Destination specified
**Then**:
- Destination stored in transaction metadata
- Optional for internal withdrawals
- Required for external (bank/blockchain)
- Stored as `{"destination": "..."}` in metadata

---

### BR-WDR-003: Withdrawal Event Publishing
**Given**: Successful withdrawal
**When**: Transaction completed
**Then**:
- Publishes `wallet.withdrawn` event
- Event includes: wallet_id, user_id, amount, destination
- Enables notification triggers

---

### Consumption Rules

### BR-CON-001: Consumption from Available Balance
**Given**: Consume request
**When**: Processing consumption
**Then**:
- Deducts from available_balance only
- Locked balance not consumable
- Returns `success=False` if insufficient

---

### BR-CON-002: Usage Record Linkage
**Given**: Consume request with usage_record_id
**When**: Transaction created
**Then**:
- Links to billing/usage tracking
- Enables reconciliation with billing_service
- Stored in transaction record

---

### BR-CON-003: Free Tier Handling
**Given**: billing.calculated event
**When**: is_free_tier=true
**Then**:
- No wallet deduction
- Skip consumption logic
- Log for analytics only

**Implementation**:
```python
if billing_data.is_free_tier:
    logger.info(f"Free tier usage, no wallet deduction")
    return
```

---

### BR-CON-004: Low Balance Warning
**Given**: Consumption reduces balance
**When**: Balance < threshold (configurable)
**Then**:
- Publish `wallet.balance.low` event
- Enable proactive top-up notification
- Threshold per user (future feature)

---

### Transfer Rules

### BR-TRF-001: Transfer Requires Both Wallets
**Given**: Transfer request
**When**: Validating transfer
**Then**:
- Source wallet must exist
- Destination wallet must exist
- Both must be active
- Same currency required

---

### BR-TRF-002: Transfer Atomicity
**Given**: Transfer between wallets
**When**: Executing transfer
**Then**:
- Debit and credit must both succeed
- Failure rolls back both
- No partial transfers
- Single atomic operation

**Implementation**:
```python
result = await self.repository.transfer(
    from_wallet_id, to_wallet_id, amount
)
# Returns (from_transaction, to_transaction) or None
```

---

### BR-TRF-003: Self-Transfer Prohibition
**Given**: Transfer request
**When**: from_wallet_id == to_wallet_id
**Then**:
- Operation rejected
- Returns `success=False`
- Message: "Cannot transfer to same wallet"

**Note**: Different wallets of same user allowed

---

### BR-TRF-004: Paired Transactions
**Given**: Successful transfer
**When**: Transactions created
**Then**:
- Source wallet: TRANSFER transaction (debit)
- Destination wallet: TRANSFER transaction (credit)
- Both reference same transfer
- Direction tracked in metadata

**Metadata**:
- Source: `{"direction": "out"}`
- Destination: `{"direction": "in"}`

---

### Refund Rules

### BR-REF-001: Refund Requires Original Transaction
**Given**: Refund request
**When**: Validating refund
**Then**:
- Must reference valid original_transaction_id
- Original transaction must exist
- Original must be debit type (withdraw, consume)
- Cannot refund a deposit or another refund

---

### BR-REF-002: Refund Amount Limit
**Given**: Refund request with amount
**When**: Amount specified
**Then**:
- Refund amount MUST be <= original amount
- Partial refund allowed
- Multiple partial refunds allowed until total
- Full refund if amount=None

**Validation**:
```python
if refund_amount > Decimal(str(original['amount'])):
    return None  # Cannot refund more than original
```

---

### BR-REF-003: Refund Reason Required
**Given**: Refund request
**When**: Creating refund
**Then**:
- `reason` field is required
- Used for audit and dispute resolution
- Cannot be empty string
- Stored in transaction metadata

**Validation**:
```python
reason: str = Field(..., min_length=1)
```

---

### BR-REF-004: Refund Adds to Balance
**Given**: Successful refund
**When**: Processing refund
**Then**:
- Adds refund amount to wallet balance
- Creates REFUND transaction
- Links to original via reference_id

---

### Event Processing Rules

### BR-EVT-001: Event Idempotency
**Given**: Incoming event from NATS
**When**: Processing event
**Then**:
- Check if event_id already processed
- Skip duplicate events silently
- Track processed event IDs in memory
- Cleanup old IDs to prevent memory bloat

**Implementation**:
```python
if _is_event_processed(event.id):
    logger.debug(f"Event {event.id} already processed, skipping")
    return
```

---

### BR-EVT-002: Event Sequence Handling
**Given**: Multiple events arrive
**When**: Events arrive out of order
**Then**:
- Use timestamps for sequencing
- Handle missing events gracefully
- No strict ordering requirement
- Each event processed independently

---

### BR-EVT-003: Event-Driven Operations
**Given**: Upstream service publishes event
**When**: Wallet service receives event
**Then**:
- `payment.completed` → Deposit into wallet
- `payment.refunded` → Deposit refund amount
- `subscription.created` → Allocate subscription credits
- `user.created` → Auto-create FIAT wallet
- `user.deleted` → Freeze wallets, anonymize transactions
- `billing.calculated` → Deduct tokens

---

---

## State Machines

### Wallet Lifecycle State Machine

```
┌─────────┐
│   NEW   │ Wallet creation initiated
└────┬────┘
     │
     ▼
┌─────────┐
│ ACTIVE  │ Wallet operational
└────┬────┘
     │
     └────► FROZEN (user deleted, admin action)

From FROZEN:
     │
     └────► ACTIVE (admin reactivation)
```

**States**:
- **NEW**: Temporary during creation (not persisted)
- **ACTIVE**: Wallet is operational, `is_active=true`
- **FROZEN**: Wallet deactivated, `is_active=false`

**Valid Transitions**:
- `NEW` → `ACTIVE` (wallet creation)
- `ACTIVE` → `FROZEN` (user deletion, admin freeze)
- `FROZEN` → `ACTIVE` (admin reactivation)
- `ACTIVE` → `ACTIVE` (transactions - no state change)

**Transition Triggers**:
- `create_wallet()` → NEW → ACTIVE
- `user.deleted event` → ACTIVE → FROZEN
- `admin reactivation` → FROZEN → ACTIVE

---

### Transaction State Machine

```
┌─────────┐
│ PENDING │ Transaction initiated (blockchain)
└────┬────┘
     │
     ├────► COMPLETED (success)
     │
     └────► FAILED (blockchain rejection)
```

**States**:
- **PENDING**: Waiting for blockchain confirmation
- **COMPLETED**: Transaction finalized
- **FAILED**: Transaction rejected

**Note**: Most off-chain transactions go directly to COMPLETED

---

### Balance State Machine

```
┌──────────────────┐
│  SUFFICIENT      │ available_balance >= requested_amount
└────────┬─────────┘
         │
         ├────► SUFFICIENT (deposit increases)
         │
         └────► INSUFFICIENT (withdrawal/consume depletes)

From INSUFFICIENT:
         │
         └────► SUFFICIENT (deposit, refund)
```

**States**:
- **SUFFICIENT**: Can process debit operations
- **INSUFFICIENT**: Cannot process debit operations

**Detection**:
```python
available_balance = balance - locked_balance
if available_balance >= amount:
    # SUFFICIENT
else:
    # INSUFFICIENT
```

---

## Edge Cases

### Balance Edge Cases

### EC-001: Exact Balance Withdrawal
**Scenario**: Withdrawal amount exactly equals available_balance
**Expected**:
- Operation succeeds
- Balance becomes 0
- Transaction created
- No error

**Example**:
```
Balance: 100
Withdrawal: 100
Result: Balance = 0 (success)
```

---

### EC-002: Concurrent Deposit and Withdrawal
**Scenario**: Two operations happen simultaneously
**Expected**:
- Database handles concurrency
- Both operations succeed or one fails
- Final balance is consistent
- No negative balance possible

**Solution**: Database-level row locking

---

### EC-003: Withdrawal Exceeds Balance by 0.00000001
**Scenario**: Withdrawal amount is 1 unit more than available
**Expected**:
- Operation fails
- `success=False`
- Message: "Insufficient balance"
- No partial withdrawal

**Precision**: 8 decimal places enforced

---

### EC-004: Large Balance Operations
**Scenario**: Balance or amount exceeds normal range (>1 billion)
**Expected**:
- Decimal(20,8) handles up to 10^12
- No overflow errors
- Precision maintained

---

### Transaction Edge Cases

### EC-005: Refund More Than Original Amount
**Scenario**: Refund request with amount > original transaction amount
**Expected**:
- Operation fails
- Returns None from repository
- `success=False`
- Original balance unchanged

---

### EC-006: Refund Already Refunded Transaction
**Scenario**: Attempting to refund a REFUND transaction
**Expected**:
- Validation fails
- Cannot refund a refund
- Original transaction type must be debit

---

### EC-007: Transfer to Non-Existent Wallet
**Scenario**: Transfer to wallet_id that doesn't exist
**Expected**:
- Operation fails
- `success=False`
- Message: "Transfer failed - check wallet IDs"
- Source balance unchanged

---

### EC-008: Transfer to Same Wallet
**Scenario**: from_wallet_id == to_wallet_id
**Expected**:
- Should be rejected
- `success=False`
- No transactions created

---

### Event Edge Cases

### EC-009: Duplicate Event Processing
**Scenario**: Same event.id received twice
**Expected**:
- First processing succeeds
- Second processing skipped
- No duplicate transactions
- Idempotency maintained

---

### EC-010: Event with Invalid User ID
**Scenario**: user.created event for non-existent user_id
**Expected**:
- Wallet still created
- Warning logged
- Graceful handling

---

### EC-011: Payment Event Without Wallet
**Scenario**: payment.completed event but user has no wallet
**Expected**:
- Warning logged
- Event marked as processed
- No error thrown

---

### EC-012: Out-of-Order Events
**Scenario**: billing.calculated arrives before payment.completed
**Expected**:
- Each event processed independently
- billing.calculated may fail (insufficient balance)
- payment.completed creates deposit
- Eventual consistency

---

### Wallet Creation Edge Cases

### EC-013: Create Second FIAT Wallet
**Scenario**: User already has FIAT wallet, requests another
**Expected**:
- Returns existing wallet info
- `success=False`
- Message: "User already has a fiat wallet"
- wallet_id of existing wallet returned

---

### EC-014: Create Wallet with Initial Balance
**Scenario**: WalletCreate with initial_balance > 0
**Expected**:
- Wallet created
- Initial DEPOSIT transaction created
- Balance set to initial_balance
- Transaction description: "Initial wallet funding"

---

### EC-015: Create Crypto Wallet Without Blockchain Info
**Scenario**: wallet_type=crypto but no blockchain_address
**Expected**:
- Wallet created (address can be set later)
- blockchain_address = None
- Can be updated via blockchain sync

---

---

## Data Consistency Rules

### Transaction Boundaries

**Rule**: Each repository method operates in its own transaction
- `create_wallet`: Single transaction
- `deposit`: Single transaction (update balance + create transaction)
- `withdraw`: Single transaction
- `consume`: Single transaction
- `transfer`: Single transaction (atomic debit + credit)
- `refund`: Single transaction

**Implementation**:
```python
async with self.db:
    await self.db.execute(...)
```

---

### Balance-Transaction Consistency

**Rule**: Balance MUST match sum of transactions
- Deposit increases balance
- Withdrawal/Consume decreases balance
- Refund increases balance
- Transfer creates balanced pair

**Invariant**:
```
current_balance = initial_balance + SUM(deposits) - SUM(withdrawals)
                  - SUM(consumes) + SUM(refunds)
```

---

### Concurrent Update Handling

**Rule**: Optimistic concurrency with balance checks
- Check balance before debit
- Update fails if balance insufficient
- No race conditions due to atomic updates

**Solution**: Check-then-update in single query

---

### Event Publishing Consistency

**Rule**: Events published after database commit
- Database transaction commits first
- Event published after success
- Event failure doesn't rollback transaction
- Eventually consistent with subscribers

---

### Audit Trail Preservation

**Rule**: All operations leave audit trail
- Transactions never deleted
- Transactions never modified
- Balance changes tracked via balance_before/after
- Timestamps in UTC

---

---

## Integration Contracts

### PostgreSQL gRPC Service

**Expectations**:
- Service name: `postgres_grpc_service`
- Default host: `isa-postgres-grpc`
- Default port: `50061`
- Protocol: gRPC with AsyncPostgresClient
- Schema: `wallet`
- Tables: `wallets`, `transactions`

**Connection**:
```python
self.db = AsyncPostgresClient(host=host, port=port, user_id='wallet_service')
```

---

### NATS Event Publishing

**Published Events**:
| Event Type | Subject |
|------------|---------|
| WALLET_CREATED | `wallet_service.wallet.created` |
| WALLET_DEPOSITED | `wallet_service.wallet.deposited` |
| WALLET_WITHDRAWN | `wallet_service.wallet.withdrawn` |
| WALLET_CONSUMED | `wallet_service.wallet.consumed` |
| WALLET_TRANSFERRED | `wallet_service.wallet.transferred` |
| WALLET_REFUNDED | `wallet_service.wallet.refunded` |
| TOKENS_DEDUCTED | `wallet_service.wallet.tokens.deducted` |
| TOKENS_INSUFFICIENT | `wallet_service.wallet.tokens.insufficient` |

---

### NATS Event Subscriptions

**Subscribed Events**:
| Pattern | Handler |
|---------|---------|
| `payment_service.payment.completed` | handle_payment_completed |
| `payment_service.payment.refunded` | handle_payment_refunded |
| `subscription_service.subscription.created` | handle_subscription_created |
| `account_service.user.created` | handle_user_created |
| `account_service.user.deleted` | handle_user_deleted |
| `billing_service.billing.calculated` | handle_billing_calculated |

---

### Account Service Client

**Usage**: User validation before wallet operations

**Methods**:
- `get_account(user_id)`: Returns account or None
- `validate_user_exists(user_id)`: Returns bool

**Behavior**: Graceful degradation if unavailable

---

### Consul Service Discovery

**Registration**:
- Service name: `wallet_service`
- Port: `8213`
- Health check: `/health`

**Discovery**:
- Discovers `postgres_grpc_service`
- Discovers `account_service`

---

---

## Error Handling Contracts

### WalletNotFoundError

**When Raised**:
- `get_wallet`: Wallet ID not found
- `deposit/withdraw/consume`: Wallet not found

**HTTP Status**: 404 Not Found

**Response**:
```json
{
  "detail": "Wallet not found"
}
```

---

### InsufficientBalanceError

**When Raised**:
- `withdraw`: Balance insufficient
- `consume`: Balance insufficient
- `transfer`: Source balance insufficient

**HTTP Status**: 400 Bad Request

**Response**:
```json
{
  "detail": "Insufficient balance"
}
```

---

### DuplicateWalletError

**When Raised**:
- `create_wallet`: FIAT wallet already exists

**HTTP Status**: 400 Bad Request

**Response**:
```json
{
  "success": false,
  "message": "User already has a fiat wallet",
  "wallet_id": "existing_wallet_id"
}
```

---

### WalletValidationError

**When Raised**:
- Invalid amount (zero, negative)
- Missing required fields
- Invalid wallet_type

**HTTP Status**: 400 Bad Request (or 422 from Pydantic)

---

### WalletServiceError

**When Raised**:
- Unexpected errors
- Database connection failures
- Generic operation failures

**HTTP Status**: 500 Internal Server Error

---

### HTTP Status Code Mappings

| Error Type | HTTP Status | Example Scenario |
|------------|-------------|------------------|
| WalletNotFoundError | 404 | Wallet ID not found |
| InsufficientBalanceError | 400 | Withdrawal > balance |
| DuplicateWalletError | 400 | Second FIAT wallet |
| WalletValidationError | 400/422 | Invalid amount |
| WalletServiceError | 500 | Database failure |
| Pydantic ValidationError | 422 | Negative amount |

---

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| create_wallet | < 100ms | < 500ms |
| get_wallet | < 50ms | < 200ms |
| get_balance | < 50ms | < 200ms |
| deposit | < 100ms | < 300ms |
| withdraw | < 100ms | < 300ms |
| consume | < 100ms | < 300ms |
| transfer | < 150ms | < 500ms |
| refund | < 100ms | < 300ms |
| get_transactions | < 150ms | < 500ms |
| get_statistics | < 200ms | < 1000ms |

### Throughput Targets

- Wallet creation: 100 req/s
- Balance queries: 1000 req/s
- Deposits/Withdrawals: 500 req/s
- Transfers: 200 req/s
- Transaction history: 500 req/s

### Resource Limits

- Max concurrent connections: 100
- Max transactions per query: 100 (limit)
- Max wallets per user: Unlimited (except FIAT)
- Transaction metadata size: < 10KB

---

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Not found errors (404)
- ✅ Insufficient balance scenarios
- ✅ Event publishing (verify published)
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Idempotency (duplicate event handling)
- ✅ Concurrent operations
- ✅ Transfer atomicity
- ✅ Refund constraints
- ✅ Balance consistency
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-16
**Owner**: Wallet Service Team
