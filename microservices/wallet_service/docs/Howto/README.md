# Wallet Service API Documentation

## Overview
The Wallet Service is a microservice that manages digital wallets, transactions, and credit/token balances. It supports both traditional fiat-style credits and blockchain-based crypto tokens.

## Quick Start

### Service Information
- **Port**: 8209
- **Base URL**: `http://localhost:8209`
- **API Version**: v1
- **API Prefix**: `/api/v1`
- **Status**: ✅ **Fully Operational** (Foreign key constraints resolved)

### Health Check
```bash
curl http://localhost:8209/health
```

### Recent Updates (2025-09-26)
- ✅ **Removed foreign key constraints** for microservices independence
- ✅ **Service autonomy** - can create wallets for any user_id
- ✅ **All core functions tested** and working properly

## Available Guides

### 1. [Create Wallet](./1_Create_Wallet.md)
Learn how to create different types of wallets (fiat, crypto, hybrid) for users.

### 2. [Balance Operations](./2_Balance_Operations.md)
Understand how to check balances, including available balance, locked balance, and total credits.

### 3. [Transaction Operations](./3_Transaction_Operations.md)
Perform transactions: deposits, withdrawals, consumption, transfers, and refunds.

### 4. [Transaction History](./4_Transaction_History.md)
Query transaction history with filtering, pagination, and date ranges.

### 5. [Service Statistics](./5_Service_Statistics.md)
Access comprehensive statistics and analytics at service, user, and wallet levels.

## Core Features

### Wallet Types
- **Fiat Wallets**: Traditional credit/point system
- **Crypto Wallets**: Blockchain-based token storage
- **Hybrid Wallets**: Support both fiat and crypto

### Transaction Types
- **Deposit**: Add funds to wallet
- **Withdraw**: Remove funds from wallet
- **Consume**: Use credits for services
- **Transfer**: Move funds between wallets
- **Refund**: Reverse a previous transaction

### Key Capabilities
- Atomic transactions with rollback support
- Transaction history with full audit trail
- Balance locking for pending operations
- Multi-wallet support per user
- Decimal precision up to 8 places
- Blockchain integration ready

## API Endpoints Summary

### Wallet Management
- `POST /api/v1/wallets` - Create new wallet
- `GET /api/v1/wallets/{wallet_id}` - Get wallet details
- `GET /api/v1/users/{user_id}/wallets` - List user's wallets

### Balance Operations
- `GET /api/v1/wallets/{wallet_id}/balance` - Get wallet balance
- `GET /api/v1/users/{user_id}/credits/balance` - Get total user credits

### Transactions
- `POST /api/v1/wallets/{wallet_id}/deposit` - Deposit funds
- `POST /api/v1/wallets/{wallet_id}/withdraw` - Withdraw funds
- `POST /api/v1/wallets/{wallet_id}/consume` - Consume credits
- `POST /api/v1/wallets/{wallet_id}/transfer` - Transfer to another wallet
- `POST /api/v1/transactions/{transaction_id}/refund` - Refund transaction

### Transaction History
- `GET /api/v1/wallets/{wallet_id}/transactions` - Wallet transactions
- `GET /api/v1/users/{user_id}/transactions` - User's all transactions

### Statistics
- `GET /api/v1/wallet/stats` - Service-wide statistics
- `GET /api/v1/wallets/{wallet_id}/statistics` - Wallet statistics
- `GET /api/v1/users/{user_id}/statistics` - User statistics

## Data Models

### Wallet
```json
{
  "wallet_id": "uuid",
  "user_id": "string",
  "balance": "decimal",
  "locked_balance": "decimal",
  "available_balance": "decimal",
  "currency": "string",
  "wallet_type": "fiat|crypto|hybrid",
  "blockchain_address": "string|null",
  "blockchain_network": "string|null"
}
```

### Transaction
```json
{
  "transaction_id": "uuid",
  "wallet_id": "uuid",
  "user_id": "string",
  "transaction_type": "string",
  "amount": "decimal",
  "balance_before": "decimal",
  "balance_after": "decimal",
  "fee": "decimal",
  "description": "string",
  "created_at": "datetime"
}
```

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message"
}
```

### Common Error Codes
- `400` - Bad Request (invalid parameters, insufficient balance)
- `404` - Not Found (wallet or transaction not found)
- `409` - Conflict (duplicate operation)
- `500` - Internal Server Error

## Integration Examples

### Python
```python
import requests

# Create wallet
response = requests.post(
    "http://localhost:8209/api/v1/wallets",
    json={
        "user_id": "user-123",
        "wallet_type": "fiat",
        "initial_balance": 100.0
    }
)
wallet = response.json()

# Consume credits
response = requests.post(
    f"http://localhost:8209/api/v1/wallets/{wallet['wallet_id']}/consume",
    json={
        "amount": 10.0,
        "service": "api_usage",
        "reason": "API calls"
    }
)
```

### JavaScript
```javascript
// Create wallet
const response = await fetch('http://localhost:8209/api/v1/wallets', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user-123',
    wallet_type: 'fiat',
    initial_balance: 100.0
  })
});
const wallet = await response.json();

// Check balance
const balance = await fetch(`http://localhost:8209/api/v1/wallets/${wallet.wallet_id}/balance`);
const balanceData = await balance.json();
```

## Best Practices

1. **Always handle errors** - Check response status and handle errors gracefully
2. **Use idempotency keys** - Include reference IDs to prevent duplicate transactions
3. **Monitor balances** - Check available balance before operations
4. **Implement retries** - Use exponential backoff for transient failures
5. **Audit transactions** - Keep track of transaction IDs for reconciliation
6. **Cache appropriately** - Balance queries can be cached briefly
7. **Use pagination** - Always paginate when fetching transaction history

## Support

For issues or questions:
1. Check the health endpoint first
2. Review error messages and codes
3. Consult the detailed guides above
4. Check transaction history for audit trail