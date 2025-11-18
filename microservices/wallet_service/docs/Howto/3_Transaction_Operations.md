# How to Perform Wallet Transactions

## Overview
The Wallet Service supports various transaction types: deposit, withdraw, consume, transfer, and refund. Each transaction is atomic and maintains transaction history.

## 1. Deposit (Add Funds)

### Endpoint
```
POST /api/v1/wallets/{wallet_id}/deposit
```

### Request Format
```json
{
  "amount": 50.0,
  "source": "payment",
  "reference": "payment-123",
  "description": "Purchase credits"
}
```

### Example
```bash
curl -X POST http://localhost:8209/api/v1/wallets/ab2f9670-ef6b-46d0-9d0e-7bd344a35a14/deposit \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 25.0,
    "source": "test",
    "description": "Test deposit"
  }'
```

### Response
```json
{
  "success": true,
  "message": "Deposited 25.0 successfully",
  "wallet_id": "ab2f9670-ef6b-46d0-9d0e-7bd344a35a14",
  "balance": "75.0",
  "transaction_id": "84700125-21d9-4467-8abc-eae6d0d45d28",
  "data": {
    "transaction": {
      "transaction_id": "84700125-21d9-4467-8abc-eae6d0d45d28",
      "wallet_id": "ab2f9670-ef6b-46d0-9d0e-7bd344a35a14",
      "user_id": "test-user-new",
      "transaction_type": "deposit",
      "amount": "25.0",
      "balance_before": "50.0",
      "balance_after": "75.0",
      "fee": "0.0",
      "description": "Test deposit",
      "blockchain_status": "completed",
      "created_at": "2025-09-26T12:27:30.340157Z"
    }
  }
}
```

## 2. Withdraw (Remove Funds)

### Endpoint
```
POST /api/v1/wallets/{wallet_id}/withdraw
```

### Request Format
```json
{
  "amount": 30.0,
  "destination": "bank_account",
  "reference": "withdraw-456",
  "description": "Withdrawal to bank"
}
```

### Example
```bash
curl -X POST http://localhost:8209/api/v1/wallets/{wallet_id}/withdraw \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 30.0,
    "destination": "bank_account",
    "reference": "withdraw-456",
    "description": "Test withdrawal"
  }'
```

## 3. Consume Credits

### Endpoint
```
POST /api/v1/wallets/{wallet_id}/consume
```

### Request Format
```json
{
  "amount": 10.0,
  "service": "api_usage",
  "reason": "API calls",
  "usage_record_id": 12345  // Optional: integer ID
}
```

### Example
```bash
curl -X POST http://localhost:8209/api/v1/wallets/ab2f9670-ef6b-46d0-9d0e-7bd344a35a14/consume \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 15.0,
    "service": "test_service",
    "reason": "Testing consume"
  }'
```

### Response
```json
{
  "success": true,
  "message": "Consumed 15.0 successfully",
  "wallet_id": "ab2f9670-ef6b-46d0-9d0e-7bd344a35a14",
  "balance": "60.0",
  "transaction_id": "09dca44a-7dcc-4692-93ab-48c76b46afa4",
  "data": {
    "transaction": {
      "transaction_id": "09dca44a-7dcc-4692-93ab-48c76b46afa4",
      "wallet_id": "ab2f9670-ef6b-46d0-9d0e-7bd344a35a14",
      "user_id": "test-user-new",
      "transaction_type": "consume",
      "amount": "15.0",
      "balance_before": "75.0",
      "balance_after": "60.0",
      "description": "Consumed: 15.0"
    },
    "remaining_balance": 60.0
  }
}

### Alternative: Consume by User ID
```
POST /api/v1/users/{user_id}/credits/consume
```

This endpoint automatically finds the user's primary wallet.

## 4. Transfer Between Wallets

### Endpoint
```
POST /api/v1/wallets/{wallet_id}/transfer
```

### Request Format
```json
{
  "to_wallet_id": "target-wallet-id",
  "amount": 25.0,
  "description": "Transfer to friend",
  "fee": 0.5  // Optional: transfer fee
}
```

### Example
```bash
curl -X POST http://localhost:8209/api/v1/wallets/{wallet_id}/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "to_wallet_id": "target-wallet-id",
    "amount": 25.0,
    "description": "Payment transfer"
  }'
```

## 5. Refund Transaction

### Endpoint
```
POST /api/v1/transactions/{transaction_id}/refund
```

### Request Format
```json
{
  "reason": "Service not delivered",
  "amount": null  // Optional: partial refund amount
}
```

### Example
```bash
curl -X POST http://localhost:8209/api/v1/transactions/{transaction_id}/refund \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Customer request"
  }'
```

## Transaction States

### Successful Transaction
- **blockchain_status**: "completed"
- **balance_before**: Previous balance
- **balance_after**: New balance after transaction

### Failed Transaction
Returns HTTP error with appropriate message:
```json
{
  "detail": "400: Insufficient balance"
}
```

## Error Handling

### Insufficient Balance
```json
{
  "detail": "400: Insufficient balance: requested 100.0 but available is 50.0"
}
```

### Invalid Amount
```json
{
  "detail": "Amount must be positive"
}
```

### Wallet Not Found
```json
{
  "detail": "404: Wallet not found"
}
```

### Transaction Already Refunded
```json
{
  "detail": "400: Transaction already refunded"
}
```

## Best Practices

1. **Always check balance before operations**
   - Use available_balance for withdrawal/transfer
   - Consider locked_balance for pending operations

2. **Use appropriate transaction types**
   - `deposit` for adding funds
   - `withdraw` for cash out
   - `consume` for service usage
   - `transfer` for wallet-to-wallet

3. **Include descriptive metadata**
   - Always add description for audit trail
   - Use reference IDs for external system integration

4. **Handle errors gracefully**
   - Check for insufficient balance
   - Verify wallet ownership
   - Validate amount formats

5. **Monitor transaction history**
   - Keep track of transaction IDs
   - Use filters for reporting
   - Implement reconciliation