# Wallet Service - Domain Context

## Business Taxonomy

### Core Entities

- **Wallet**: A digital container that holds a user's monetary value (credits, tokens, or currency). Each wallet has a unique identifier, belongs to a user, and maintains a balance that can be modified through transactions.

- **Transaction**: A recorded financial operation on a wallet. Transactions capture deposits, withdrawals, consumption, transfers, refunds, and fees. Each transaction is immutable once created and serves as an audit trail.

- **Balance**: The current amount of monetary value in a wallet. Consists of total balance, locked balance (reserved for pending operations), and available balance (total minus locked).

- **Credit**: The internal currency unit used for platform services. 1 Credit = $0.00001 USD (100,000 Credits = $1). Credits can be purchased, earned as bonuses, or allocated through subscriptions.

- **Credit Account**: A ledger entry tracking credits of a specific type (purchased, bonus, referral, promotional) with independent balances and expiration policies.

### Supporting Concepts

- **Wallet Type**: Classification of wallet (FIAT for traditional credits, CRYPTO for blockchain tokens, HYBRID for both).

- **Transaction Type**: The operation category (DEPOSIT, WITHDRAW, CONSUME, REFUND, TRANSFER, REWARD, FEE, BLOCKCHAIN_IN, BLOCKCHAIN_OUT).

- **Reference ID**: External identifier linking a transaction to another system (payment ID, usage record ID, billing record ID).

- **Locked Balance**: Funds temporarily reserved for pending operations that cannot be spent until released.

- **Blockchain Integration**: Optional connection to blockchain networks (Ethereum, BSC, Polygon) for on-chain asset management.

---

## Domain Scenarios

### 1. User Wallet Creation
- **Trigger**: New user registration or explicit wallet creation request
- **Flow**:
  1. Validate user exists in account service
  2. Check if user already has a wallet of requested type
  3. Create wallet with initial balance (typically zero)
  4. Create initial deposit transaction if starting balance > 0
  5. Publish wallet.created event
- **Outcome**: User has a functional wallet ready for transactions
- **Events**: `wallet.created`

### 2. Credit Purchase and Deposit
- **Trigger**: Payment completion event from payment service
- **Flow**:
  1. Receive payment.completed event
  2. Validate payment details (user_id, amount)
  3. Get or create user's primary wallet
  4. Deposit funds into wallet
  5. Create deposit transaction record
  6. Publish wallet.deposited event
- **Outcome**: User's wallet balance increased by payment amount
- **Events**: `wallet.deposited`, `deposit.completed`

### 3. Credit Consumption for Service Usage
- **Trigger**: Billing service calculates usage cost
- **Flow**:
  1. Receive billing.calculated event
  2. Check if free tier or subscription-included (skip if so)
  3. Verify wallet has sufficient balance
  4. Deduct credits from wallet
  5. Create consumption transaction
  6. Publish tokens.deducted or tokens.insufficient event
- **Outcome**: Credits deducted for service usage OR insufficient balance alert
- **Events**: `wallet.consumed`, `tokens.deducted`, `tokens.insufficient`

### 4. Wallet-to-Wallet Transfer
- **Trigger**: User initiates transfer to another user
- **Flow**:
  1. Validate source wallet has sufficient balance
  2. Validate destination wallet exists
  3. Atomically deduct from source, add to destination
  4. Create paired transfer transactions
  5. Publish wallet.transferred event
- **Outcome**: Funds moved between wallets
- **Events**: `wallet.transferred`

### 5. Transaction Refund
- **Trigger**: Refund request for previous transaction
- **Flow**:
  1. Find original transaction
  2. Validate refund amount does not exceed original
  3. Add refund amount back to wallet
  4. Create refund transaction with reference to original
  5. Publish wallet.refunded event
- **Outcome**: Funds returned to user's wallet
- **Events**: `wallet.refunded`

### 6. Balance Inquiry and Statistics
- **Trigger**: User requests balance or transaction history
- **Flow**:
  1. Query wallet for current balance
  2. Calculate available balance (total - locked)
  3. Aggregate transaction statistics if requested
  4. Return balance details with breakdown
- **Outcome**: User sees current financial state
- **Events**: None (read-only operation)

### 7. User Account Deletion (GDPR)
- **Trigger**: User deletion event from account service
- **Flow**:
  1. Receive user.deleted event
  2. Get all wallets for user
  3. Freeze/deactivate each wallet
  4. Anonymize transaction history (keep amounts for accounting)
  5. Mark wallet metadata with deletion timestamp
- **Outcome**: User wallet data anonymized while preserving financial records
- **Events**: None (internal cleanup)

### 8. Subscription Credit Allocation
- **Trigger**: Subscription creation event
- **Flow**:
  1. Receive subscription.created event
  2. Check if subscription includes credits
  3. Deposit subscription credits to wallet
  4. Mark transaction as subscription credit
- **Outcome**: Monthly subscription credits allocated to user
- **Events**: `wallet.deposited`

---

## Domain Events

### Published Events

1. **wallet.created** (EventType.WALLET_CREATED)
   - When: New wallet created for user
   - Data: `{wallet_id, user_id, wallet_type, currency, balance, timestamp}`
   - Consumers: audit_service, notification_service

2. **wallet.deposited** (EventType.WALLET_DEPOSITED)
   - When: Funds deposited to wallet
   - Data: `{wallet_id, user_id, transaction_id, amount, balance_before, balance_after, reference_id, timestamp}`
   - Consumers: notification_service, audit_service

3. **wallet.withdrawn** (EventType.WALLET_WITHDRAWN)
   - When: Funds withdrawn from wallet
   - Data: `{wallet_id, user_id, transaction_id, amount, balance_before, balance_after, destination, timestamp}`
   - Consumers: notification_service, audit_service

4. **wallet.consumed** (EventType.WALLET_CONSUMED)
   - When: Credits consumed for service usage
   - Data: `{wallet_id, user_id, transaction_id, amount, balance_before, balance_after, usage_record_id, timestamp}`
   - Consumers: billing_service, audit_service

5. **wallet.transferred** (EventType.WALLET_TRANSFERRED)
   - When: Funds transferred between wallets
   - Data: `{from_wallet_id, to_wallet_id, from_user_id, to_user_id, amount, from_transaction_id, to_transaction_id, timestamp}`
   - Consumers: notification_service (both users), audit_service

6. **wallet.refunded** (EventType.WALLET_REFUNDED)
   - When: Transaction refunded
   - Data: `{wallet_id, user_id, transaction_id, original_transaction_id, amount, balance_after, reason, timestamp}`
   - Consumers: notification_service, billing_service

7. **wallet.tokens.deducted**
   - When: Token deduction successful after billing
   - Data: `{user_id, billing_record_id, transaction_id, tokens_deducted, balance_before, balance_after, monthly_quota, monthly_used}`
   - Consumers: billing_service, analytics_service, notification_service

8. **wallet.tokens.insufficient**
   - When: Insufficient tokens for billing
   - Data: `{user_id, billing_record_id, tokens_required, tokens_available, tokens_deficit, suggested_action}`
   - Consumers: notification_service, billing_service

9. **wallet.balance.low**
   - When: Balance falls below threshold
   - Data: `{user_id, wallet_id, current_balance, threshold}`
   - Consumers: notification_service

### Consumed Events

1. **payment_service.payment.completed**
   - Purpose: Deposit payment into wallet
   - Handler: Creates deposit transaction

2. **payment_service.payment.refunded**
   - Purpose: Process payment refund
   - Handler: Deposits refund amount

3. **subscription_service.subscription.created**
   - Purpose: Allocate subscription credits
   - Handler: Deposits monthly credits

4. **account_service.user.created**
   - Purpose: Auto-create wallet for new user
   - Handler: Creates default FIAT wallet

5. **account_service.user.deleted**
   - Purpose: GDPR compliance cleanup
   - Handler: Freezes wallets, anonymizes transactions

6. **billing_service.billing.calculated**
   - Purpose: Deduct tokens for usage
   - Handler: Consumes credits from wallet

---

## Core Concepts

### Credit System Architecture

The platform uses a credit-based system where:
- 1 Credit = $0.00001 USD
- 100,000 Credits = $1 USD
- Credits are the atomic unit for all platform transactions

This design enables:
- Micro-transactions without floating-point issues
- Clear audit trail for every credit movement
- Flexible pricing at granular levels
- Cross-service billing through credits

### Balance Consistency Model

Wallet balance follows eventual consistency with strong guarantees:
- All balance changes occur through atomic transactions
- Each transaction records before/after balance
- Transaction sequence provides audit trail
- No direct balance manipulation outside transactions

### Multi-Wallet Support

Users can have multiple wallets of different types:
- **FIAT**: Primary wallet for credits (one per user)
- **CRYPTO**: Blockchain-based wallet for tokens
- **HYBRID**: Combined wallet supporting both

The primary wallet (FIAT type) is automatically created and used for all standard operations.

### Transaction Immutability

Once created, transactions cannot be modified. Corrections are made through:
- Refund transactions (reverses previous transaction)
- Adjustment transactions (administrative corrections)
- Both reference the original transaction

### Event-Driven Financial Operations

Financial operations are coordinated through events:
1. **payment.completed** → wallet.deposited
2. **billing.calculated** → wallet.consumed
3. **user.created** → wallet.created

This ensures loose coupling while maintaining financial consistency.

---

## High-Level Business Rules (35 Rules)

### Wallet Management Rules

**BR-WAL-001: One Primary Wallet Per User**
- Each user MUST have exactly one FIAT wallet
- System auto-creates on user registration
- Prevents duplicate primary wallets

**BR-WAL-002: User Validation Required**
- Wallet creation requires valid user_id
- User must exist in account service
- Prevents orphan wallets

**BR-WAL-003: Wallet Uniqueness by Type**
- User can have at most one wallet per type
- FIAT, CRYPTO, HYBRID are mutually exclusive types
- Duplicate creation returns existing wallet

**BR-WAL-004: Initial Balance Non-Negative**
- Wallet initial balance MUST be >= 0
- Negative initial balance rejected
- Zero is valid initial balance

**BR-WAL-005: Wallet Currency Immutable**
- Currency cannot be changed after creation
- New currency requires new wallet
- Prevents accounting complications

**BR-WAL-006: Wallet Activation State**
- Wallets can be active or frozen
- Frozen wallets reject all operations
- Only admin can freeze/unfreeze

### Balance Rules

**BR-BAL-001: Non-Negative Balance**
- Wallet balance MUST never go negative
- All deduction operations validate before executing
- Insufficient balance returns error

**BR-BAL-002: Available Balance Calculation**
- Available = Total Balance - Locked Balance
- Only available balance can be spent
- Locked balance reserved for pending operations

**BR-BAL-003: Locked Balance Constraints**
- Locked balance MUST be <= Total balance
- Cannot lock more than available
- Locks released after operation completes

**BR-BAL-004: Balance Precision**
- All amounts use Decimal with 8 decimal places
- No floating-point operations on money
- Prevents rounding errors

**BR-BAL-005: Zero Balance Valid**
- Zero balance is valid state
- Empty wallet can receive deposits
- No minimum balance requirement

### Transaction Rules

**BR-TXN-001: Transaction Immutability**
- Transactions MUST NOT be modified after creation
- Only refund creates reversal
- Audit trail preserved

**BR-TXN-002: Transaction Amount Positive**
- Transaction amount MUST be > 0
- Zero amount transactions rejected
- Negative handled by transaction type

**BR-TXN-003: Balance Recording**
- Transaction records balance_before and balance_after
- Enables balance reconstruction from transactions
- Audit trail requirement

**BR-TXN-004: Reference ID Optional But Recommended**
- External reference_id is optional
- Recommended for traceability
- Links to payment, billing, usage records

**BR-TXN-005: Transaction Type Determines Flow**
- DEPOSIT adds to balance
- WITHDRAW, CONSUME subtract from balance
- TRANSFER creates paired transactions
- REFUND adds to balance (reversal)

**BR-TXN-006: Transaction Timestamp UTC**
- All timestamps in UTC timezone
- No local timezone storage
- Consistent cross-region ordering

### Deposit Rules

**BR-DEP-001: Deposit Requires Valid Wallet**
- Wallet must exist and be active
- Frozen wallets reject deposits
- Invalid wallet returns 404

**BR-DEP-002: Deposit Amount Validation**
- Amount MUST be > 0
- Maximum deposit limit enforced (if configured)
- Currency conversion not supported

**BR-DEP-003: Deposit Publishes Event**
- Successful deposit publishes wallet.deposited
- Event includes before/after balance
- Notification service can alert user

### Withdrawal Rules

**BR-WDR-001: Withdrawal Balance Check**
- Amount MUST be <= available_balance
- Insufficient funds returns error
- No overdraft allowed

**BR-WDR-002: Withdrawal Destination Optional**
- Destination (bank/blockchain) is optional
- Internal withdrawals have no destination
- External withdrawals require destination

**BR-WDR-003: Withdrawal Requires Active Wallet**
- Frozen wallets cannot withdraw
- Deleted user wallets frozen
- Must verify wallet status

### Consumption Rules

**BR-CON-001: Consumption Priority**
- Consume from available balance only
- Locked balance not consumable
- Return insufficient if not enough

**BR-CON-002: Usage Record Linkage**
- Consumption can link to usage_record_id
- Enables usage tracking
- Required for billing reconciliation

**BR-CON-003: Free Tier Skip**
- Free tier usage does not deduct
- Check is_free_tier flag in billing event
- Subscription-included also skips

**BR-CON-004: Low Balance Warning**
- Publish warning when balance < threshold
- Configurable threshold per user
- Enables proactive top-up notification

### Transfer Rules

**BR-TRF-001: Transfer Requires Both Wallets**
- Source and destination must exist
- Both must be active
- Same currency required

**BR-TRF-002: Transfer Atomic Operation**
- Debit and credit must both succeed
- Failure rolls back both
- No partial transfers

**BR-TRF-003: Self-Transfer Prohibited**
- Cannot transfer to same wallet
- Different wallets of same user allowed
- Returns error if same wallet_id

**BR-TRF-004: Transfer Creates Paired Transactions**
- Source gets TRANSFER OUT transaction
- Destination gets TRANSFER IN transaction
- Both reference same transfer_id

### Refund Rules

**BR-REF-001: Refund Requires Original Transaction**
- Must reference valid original_transaction_id
- Original must be debit type (withdraw, consume)
- Cannot refund a deposit or refund

**BR-REF-002: Refund Amount Limit**
- Refund amount <= original amount
- Partial refund allowed
- Multiple partial refunds until total

**BR-REF-003: Refund Reason Required**
- Must provide refund reason
- Used for audit and disputes
- Cannot be empty string

**BR-REF-004: Refund Adds to Balance**
- Refund increases wallet balance
- Creates credit transaction
- Returns funds to user

### Event Processing Rules

**BR-EVT-001: Event Idempotency**
- Process each event_id only once
- Track processed event IDs
- Skip duplicates silently

**BR-EVT-002: Event Sequence Handling**
- Events may arrive out of order
- Use timestamps for sequencing
- Handle missing events gracefully

---

## Integration Points

### Upstream Services (Publishers)
- **payment_service**: Payment completion triggers deposit
- **billing_service**: Usage billing triggers consumption
- **subscription_service**: Subscription creation triggers credit allocation
- **account_service**: User lifecycle events

### Downstream Services (Consumers)
- **notification_service**: Alerts for deposits, low balance
- **audit_service**: All financial transactions logged
- **billing_service**: Token deduction status

### Infrastructure Dependencies
- **PostgreSQL**: Transaction and wallet storage
- **NATS**: Event publishing and subscription
- **Consul**: Service discovery
- **Redis**: Event idempotency tracking (optional)

---

## Glossary

| Term | Definition |
|------|------------|
| **Credit** | Platform currency unit (1 Credit = $0.00001 USD) |
| **Token** | Interchangeable term for credit in token context |
| **FIAT Wallet** | Primary wallet for traditional credits |
| **CRYPTO Wallet** | Blockchain-based asset wallet |
| **Locked Balance** | Funds reserved for pending operations |
| **Available Balance** | Balance minus locked balance |
| **Idempotency** | Guarantee that repeat operations have same effect |
| **Transaction** | Immutable record of balance change |
| **Reference ID** | Link to external system (payment, billing) |

---

**End of Domain Context Document**

Total Business Rules: 35
Domain Scenarios: 8
Domain Events: 9 Published, 6 Consumed
