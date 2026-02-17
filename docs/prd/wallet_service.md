# Wallet Service - Product Requirements Document (PRD)

## Product Overview

The Wallet Service is the financial backbone of the isA platform, managing digital wallets, credit balances, and transaction processing for all users. It provides a secure, scalable, and auditable system for handling platform currency (credits) that power service usage across the ecosystem.

### Value Proposition
- **Users**: Single source of truth for credit balance and transaction history
- **Platform**: Unified billing and consumption tracking across all services
- **Business**: Complete financial audit trail for compliance and analytics

### Key Capabilities
- Digital wallet management (create, read, update)
- Multi-transaction support (deposit, withdraw, consume, transfer, refund)
- Real-time balance tracking with locked/available separation
- Event-driven integration with payment and billing services
- Transaction history and financial statistics
- GDPR-compliant data handling

---

## Target Users

### Primary Users

- **Platform Users**: Individuals and organizations using isA services
  - Need: View balance, track spending, understand credit consumption
  - Interaction: Indirect through billing dashboard, direct for top-up

- **Service Consumers (Internal)**: Other microservices needing credit operations
  - Need: Programmatic credit deduction for usage
  - Interaction: API calls for consume, deposit, balance check

### Secondary Users

- **Billing Service**: Calculates usage costs and triggers consumption
  - Need: Reliable credit deduction with balance verification
  - Interaction: Events and API for consumption operations

- **Payment Service**: Processes payments and triggers deposits
  - Need: Deposit funds after successful payment
  - Interaction: Events for payment completion

- **Notification Service**: Alerts users about wallet events
  - Need: Consume wallet events for user notifications
  - Interaction: Subscribe to wallet events

### Administrative Users

- **Finance Team**: Monitor platform financial health
  - Need: Aggregated statistics, transaction reports
  - Interaction: Statistics endpoints, audit logs

- **Support Team**: Resolve user wallet issues
  - Need: Transaction lookup, balance verification, refund processing
  - Interaction: Admin endpoints for wallet operations

---

## Epics and User Stories

### Epic 1: Wallet Lifecycle Management

**User Stories** (5):

1. As a new user, I want a wallet automatically created when I register so that I can immediately start using platform services.

2. As a user, I want to view my current wallet balance so that I know how many credits I have available.

3. As a user, I want to see the breakdown of my balance (total, locked, available) so that I understand my actual spendable credits.

4. As an admin, I want to freeze a user's wallet so that I can prevent transactions during investigations.

5. As a user, I want my wallet data anonymized when I delete my account so that my financial history is protected under GDPR.

### Epic 2: Credit Deposits

**User Stories** (4):

1. As a user, I want my wallet credited when my payment completes so that I can use the purchased credits immediately.

2. As a subscription user, I want my monthly credit allocation deposited automatically so that I always have my subscription credits available.

3. As a user, I want to receive confirmation when credits are deposited so that I know the transaction succeeded.

4. As a user receiving a refund, I want the refund amount deposited back to my wallet so that I can use those credits again.

### Epic 3: Credit Consumption

**User Stories** (5):

1. As a user, I want credits deducted automatically when I use platform services so that billing is seamless.

2. As a user, I want to be notified when my balance is low so that I can top up before running out.

3. As a user, I want free tier usage to not deduct credits so that I can evaluate services without cost.

4. As a subscription user, I want included usage to not deduct credits so that I get value from my subscription.

5. As a user, I want to see what service consumed my credits so that I understand my spending.

### Epic 4: Wallet Transfers

**User Stories** (4):

1. As a user, I want to transfer credits to another user so that I can share credits with family or team members.

2. As a sender, I want transfer confirmation so that I know the transfer completed successfully.

3. As a receiver, I want to be notified of incoming transfers so that I know credits were received.

4. As a user, I want transfer history showing both sent and received so that I can track all transfers.

### Epic 5: Transaction History and Statistics

**User Stories** (5):

1. As a user, I want to view my transaction history so that I can see all wallet activity.

2. As a user, I want to filter transactions by type (deposits, withdrawals, consumption) so that I can analyze specific activity.

3. As a user, I want to filter transactions by date range so that I can review specific periods.

4. As a user, I want wallet statistics (total deposits, total consumption) so that I understand my usage patterns.

5. As a user, I want to export my transaction history so that I can keep personal records.

### Epic 6: Refund Processing

**User Stories** (4):

1. As a user receiving a refund, I want credits returned to my wallet so that I'm not charged for failed or cancelled services.

2. As support staff, I want to process refunds for users so that I can resolve billing disputes.

3. As a user, I want refund transactions clearly marked with the reason so that I understand why credits were returned.

4. As a user, I want partial refunds supported so that I can receive proportional refunds for partial service delivery.

### Epic 7: Multi-Wallet Support (Future)

**User Stories** (4):

1. As a user, I want separate wallets for different currencies so that I can manage multiple asset types.

2. As a crypto user, I want a blockchain-connected wallet so that I can use on-chain assets.

3. As a user, I want to choose which wallet to use for payments so that I have control over spending.

4. As a user, I want to transfer between my own wallets so that I can manage my funds across wallet types.

---

## API Surface Documentation

### Health Check

#### GET /health
- **Description**: Service health check
- **Auth Required**: No
- **Request Schema**: None
- **Response Schema**:
  ```json
  {
    "status": "healthy",
    "service": "wallet_service",
    "port": 8208,
    "version": "1.0.0",
    "timestamp": "2025-12-16T10:00:00Z"
  }
  ```
- **Error Codes**: 500 (Service unhealthy)

---

### Wallet Management

#### POST /api/v1/wallets
- **Description**: Create new wallet for user
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "user_id": "user_abc123",
    "wallet_type": "fiat",
    "initial_balance": 0,
    "currency": "CREDIT",
    "blockchain_network": null,
    "blockchain_address": null,
    "metadata": {}
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Wallet created successfully",
    "wallet_id": "uuid-wallet-id",
    "balance": 0,
    "data": {
      "wallet": {
        "wallet_id": "uuid-wallet-id",
        "user_id": "user_abc123",
        "wallet_type": "fiat",
        "currency": "CREDIT",
        "balance": 0,
        "locked_balance": 0,
        "available_balance": 0,
        "created_at": "2025-12-16T10:00:00Z"
      }
    }
  }
  ```
- **Error Codes**: 400 (Duplicate wallet), 422 (Validation error), 500 (Server error)
- **Example**:
  ```bash
  curl -X POST http://localhost:8208/api/v1/wallets \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{"user_id": "user_abc123", "wallet_type": "fiat", "currency": "CREDIT"}'
  ```

#### GET /api/v1/wallets/{wallet_id}
- **Description**: Get wallet details by ID
- **Auth Required**: Yes
- **Request Schema**: None (wallet_id in path)
- **Response Schema**:
  ```json
  {
    "wallet_id": "uuid-wallet-id",
    "user_id": "user_abc123",
    "balance": 10000,
    "locked_balance": 500,
    "available_balance": 9500,
    "currency": "CREDIT",
    "wallet_type": "fiat",
    "last_updated": "2025-12-16T10:00:00Z",
    "blockchain_address": null,
    "blockchain_network": null
  }
  ```
- **Error Codes**: 404 (Wallet not found), 500 (Server error)

#### GET /api/v1/wallets?user_id={user_id}
- **Description**: List all wallets for a user
- **Auth Required**: Yes
- **Query Parameters**:
  - `user_id` (required): User ID
  - `wallet_type` (optional): Filter by wallet type
- **Response Schema**:
  ```json
  {
    "wallets": [
      {
        "wallet_id": "uuid-wallet-id",
        "user_id": "user_abc123",
        "wallet_type": "fiat",
        "currency": "CREDIT",
        "balance": 10000,
        "locked_balance": 0,
        "available_balance": 10000
      }
    ],
    "count": 1
  }
  ```
- **Error Codes**: 500 (Server error)

#### GET /api/v1/wallets/{wallet_id}/balance
- **Description**: Get wallet balance details
- **Auth Required**: Yes
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Balance retrieved successfully",
    "wallet_id": "uuid-wallet-id",
    "balance": 9500,
    "data": {
      "balance": 10000,
      "locked_balance": 500,
      "available_balance": 9500,
      "currency": "CREDIT",
      "on_chain_balance": null
    }
  }
  ```
- **Error Codes**: 404 (Wallet not found), 500 (Server error)

---

### Transaction Operations

#### POST /api/v1/wallets/{wallet_id}/deposit
- **Description**: Deposit funds to wallet
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "amount": 10000,
    "description": "Credit purchase",
    "reference_id": "payment_xyz789",
    "metadata": {"source": "stripe"}
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Deposited 10000 successfully",
    "wallet_id": "uuid-wallet-id",
    "balance": 20000,
    "transaction_id": "txn_abc123",
    "data": {
      "transaction": {
        "transaction_id": "txn_abc123",
        "wallet_id": "uuid-wallet-id",
        "transaction_type": "deposit",
        "amount": 10000,
        "balance_before": 10000,
        "balance_after": 20000,
        "created_at": "2025-12-16T10:00:00Z"
      }
    }
  }
  ```
- **Error Codes**: 400 (Invalid amount), 404 (Wallet not found), 500 (Server error)

#### POST /api/v1/wallets/{wallet_id}/withdraw
- **Description**: Withdraw funds from wallet
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "amount": 5000,
    "description": "Withdrawal to bank",
    "destination": "bank_account_xxx",
    "metadata": {}
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Withdrew 5000 successfully",
    "wallet_id": "uuid-wallet-id",
    "balance": 15000,
    "transaction_id": "txn_def456",
    "data": {"transaction": {...}}
  }
  ```
- **Error Codes**: 400 (Insufficient balance), 404 (Wallet not found), 500 (Server error)

#### POST /api/v1/wallets/{wallet_id}/consume
- **Description**: Consume credits from wallet
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "amount": 100,
    "description": "API usage charge",
    "usage_record_id": 12345,
    "metadata": {"service": "ai_service"}
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Consumed 100 successfully",
    "wallet_id": "uuid-wallet-id",
    "balance": 14900,
    "transaction_id": "txn_ghi789",
    "data": {
      "transaction": {...},
      "remaining_balance": 14900
    }
  }
  ```
- **Error Codes**: 400 (Insufficient balance), 404 (Wallet not found), 500 (Server error)

#### POST /api/v1/wallets/credits/consume?user_id={user_id}
- **Description**: Consume credits from user's primary wallet (backward compatibility)
- **Auth Required**: Yes
- **Query Parameters**: `user_id` (required)
- **Request Schema**: Same as /consume
- **Response Schema**: Same as /consume
- **Note**: Auto-creates wallet if not exists

#### POST /api/v1/wallets/{wallet_id}/transfer
- **Description**: Transfer funds between wallets
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "to_wallet_id": "uuid-target-wallet",
    "amount": 1000,
    "description": "Gift to friend",
    "metadata": {}
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Transferred 1000 successfully",
    "wallet_id": "uuid-source-wallet",
    "balance": 13900,
    "transaction_id": "txn_src_123",
    "data": {
      "from_transaction": {...},
      "to_transaction": {...}
    }
  }
  ```
- **Error Codes**: 400 (Insufficient balance, invalid target), 404 (Wallet not found), 500 (Server error)

#### POST /api/v1/transactions/{transaction_id}/refund
- **Description**: Refund a previous transaction
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "original_transaction_id": "txn_original",
    "amount": 50,
    "reason": "Service not delivered",
    "metadata": {}
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Refunded 50 successfully",
    "wallet_id": "uuid-wallet-id",
    "balance": 13950,
    "transaction_id": "txn_refund_123",
    "data": {"transaction": {...}}
  }
  ```
- **Error Codes**: 400 (Invalid refund), 404 (Transaction not found), 500 (Server error)

---

### Transaction History

#### GET /api/v1/wallets/{wallet_id}/transactions
- **Description**: Get wallet transaction history
- **Auth Required**: Yes
- **Query Parameters**:
  - `transaction_type` (optional): Filter by type
  - `start_date` (optional): Start date (ISO 8601)
  - `end_date` (optional): End date (ISO 8601)
  - `limit` (optional, default=50, max=100): Results per page
  - `offset` (optional, default=0): Pagination offset
- **Response Schema**:
  ```json
  {
    "transactions": [
      {
        "transaction_id": "txn_abc123",
        "wallet_id": "uuid-wallet-id",
        "user_id": "user_abc123",
        "transaction_type": "deposit",
        "amount": 10000,
        "balance_before": 0,
        "balance_after": 10000,
        "description": "Initial deposit",
        "created_at": "2025-12-16T10:00:00Z"
      }
    ],
    "count": 1,
    "limit": 50,
    "offset": 0
  }
  ```

#### GET /api/v1/wallets/transactions?user_id={user_id}
- **Description**: Get user transaction history across all wallets
- **Auth Required**: Yes
- **Query Parameters**: Same as above plus `user_id` (required)

---

### Statistics

#### GET /api/v1/wallets/{wallet_id}/statistics
- **Description**: Get wallet statistics
- **Auth Required**: Yes
- **Query Parameters**:
  - `start_date` (optional): Period start
  - `end_date` (optional): Period end
- **Response Schema**:
  ```json
  {
    "wallet_id": "uuid-wallet-id",
    "user_id": "user_abc123",
    "current_balance": 13950,
    "total_deposits": 20000,
    "total_withdrawals": 5000,
    "total_consumed": 1050,
    "total_refunded": 50,
    "total_transfers_in": 0,
    "total_transfers_out": 1000,
    "transaction_count": 5,
    "period_start": null,
    "period_end": null
  }
  ```

#### GET /api/v1/wallets/statistics?user_id={user_id}
- **Description**: Get aggregated statistics for all user wallets
- **Auth Required**: Yes

#### GET /api/v1/wallets/credits/balance?user_id={user_id}
- **Description**: Get user's credit balance (backward compatibility)
- **Auth Required**: Yes
- **Response Schema**:
  ```json
  {
    "success": true,
    "balance": 13950,
    "available_balance": 13950,
    "locked_balance": 0,
    "currency": "CREDIT",
    "wallet_id": "uuid-wallet-id"
  }
  ```

#### GET /api/v1/wallet/stats
- **Description**: Get service statistics
- **Auth Required**: No
- **Response Schema**:
  ```json
  {
    "service": "wallet_service",
    "version": "1.0.0",
    "status": "operational",
    "capabilities": {
      "wallet_management": true,
      "transaction_management": true,
      "blockchain_ready": true
    }
  }
  ```

---

## Functional Requirements

### FR-001: Wallet Creation
- System MUST create wallet with unique wallet_id
- System MUST validate user exists before creation
- System MUST prevent duplicate wallets of same type for user
- System MUST publish wallet.created event on success

### FR-002: Balance Management
- System MUST maintain accurate balance after every transaction
- System MUST calculate available_balance = balance - locked_balance
- System MUST prevent negative balance through validation
- System MUST use Decimal for all monetary calculations

### FR-003: Deposit Processing
- System MUST accept deposits with amount > 0
- System MUST create transaction record for every deposit
- System MUST update balance atomically
- System MUST publish wallet.deposited event

### FR-004: Withdrawal Processing
- System MUST validate sufficient available_balance before withdrawal
- System MUST reject withdrawal if amount > available_balance
- System MUST create transaction record for every withdrawal
- System MUST publish wallet.withdrawn event

### FR-005: Credit Consumption
- System MUST validate sufficient balance before consumption
- System MUST link consumption to usage_record_id when provided
- System MUST publish wallet.consumed event
- System MUST support consumption by wallet_id or user_id

### FR-006: Transfer Processing
- System MUST validate both source and destination wallets
- System MUST ensure atomic transfer (both sides or neither)
- System MUST create paired transactions for transfer
- System MUST publish wallet.transferred event

### FR-007: Refund Processing
- System MUST validate original transaction exists
- System MUST ensure refund amount <= original amount
- System MUST require refund reason
- System MUST publish wallet.refunded event

### FR-008: Transaction History
- System MUST store all transactions immutably
- System MUST support filtering by type, date range
- System MUST support pagination with limit/offset
- System MUST order transactions by created_at descending

### FR-009: Event Processing
- System MUST process each event exactly once (idempotency)
- System MUST handle payment.completed for deposits
- System MUST handle billing.calculated for consumption
- System MUST handle user.deleted for cleanup

### FR-010: Statistics Generation
- System MUST calculate accurate totals per transaction type
- System MUST support date range filtering
- System MUST aggregate across all user wallets when requested

### FR-011: User Validation
- System MUST validate user_id with account service
- System MUST allow operation to proceed if validation unavailable
- System MUST log validation failures

### FR-012: Wallet Status Management
- System MUST support active and frozen states
- System MUST reject operations on frozen wallets
- System MUST track last_updated timestamp

### FR-013: Backward Compatibility
- System MUST support consume by user_id (legacy)
- System MUST auto-create wallet if not exists for user consumption
- System MUST support /credits/balance and /credits/consume endpoints

### FR-014: Error Handling
- System MUST return appropriate HTTP status codes
- System MUST include error message in response
- System MUST log all errors with context

### FR-015: GDPR Compliance
- System MUST handle user.deleted events
- System MUST freeze wallets for deleted users
- System MUST anonymize transaction history while preserving amounts

---

## Non-Functional Requirements

### NFR-001: Performance
- API response time MUST be < 200ms for 95th percentile
- Transaction processing MUST complete < 100ms
- Balance queries MUST return in < 50ms

### NFR-002: Scalability
- System MUST handle 10,000 transactions per minute
- System MUST support horizontal scaling
- System MUST use connection pooling for database

### NFR-003: Availability
- System MUST maintain 99.9% uptime
- System MUST implement health check endpoint
- System MUST gracefully handle dependency failures

### NFR-004: Consistency
- Balance updates MUST be atomic
- Transfers MUST be transactional (all or nothing)
- Transaction records MUST be immutable

### NFR-005: Security
- All endpoints MUST require authentication (except health)
- System MUST validate all input data
- System MUST not expose internal errors in responses

### NFR-006: Auditability
- All transactions MUST have audit trail
- System MUST log all operations
- System MUST publish events for significant operations

### NFR-007: Observability
- System MUST expose health metrics
- System MUST support structured logging
- System MUST integrate with centralized logging

### NFR-008: Data Integrity
- All monetary values MUST use Decimal type
- System MUST prevent floating-point errors
- System MUST validate data constraints at API level

### NFR-009: Event Reliability
- Events MUST be published with retry on failure
- Event handlers MUST be idempotent
- System MUST track processed event IDs

### NFR-010: Backward Compatibility
- API changes MUST maintain backward compatibility
- Deprecated endpoints MUST remain functional
- Version changes MUST be documented

---

## Success Metrics

### Operational Metrics
- **Transaction Success Rate**: > 99.5%
- **API Latency P95**: < 200ms
- **Event Processing Lag**: < 1 second

### Business Metrics
- **Daily Transaction Volume**: Track growth
- **Average Balance**: Monitor platform health
- **Consumption Rate**: Credits used vs deposited

### Reliability Metrics
- **Uptime**: 99.9%
- **Error Rate**: < 0.1%
- **Balance Discrepancy**: 0 (exact)

---

**End of PRD Document**

Total Epics: 7
Total User Stories: 31
API Endpoints: 17
Functional Requirements: 15
Non-Functional Requirements: 10
