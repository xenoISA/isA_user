# How to Query Transaction History

## Overview
The Wallet Service maintains complete transaction history with filtering and pagination capabilities. You can query transactions by wallet, user, type, date range, and more.

## 1. Get Wallet Transactions

### Endpoint
```
GET /api/v1/wallets/{wallet_id}/transactions
```

### Query Parameters
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Skip N results for pagination
- `transaction_type`: Filter by type (deposit, withdraw, consume, transfer, refund)
- `start_date`: ISO format date string
- `end_date`: ISO format date string

### Example: Basic Query
```bash
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?limit=5"
```

### Example: Filter by Type
```bash
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?transaction_type=deposit&limit=10"
```

### Example: Date Range
```bash
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?start_date=2025-09-01&end_date=2025-09-30"
```

### Response
```json
{
  "transactions": [
    {
      "transaction_id": "aa150b3c-7b32-4ee4-8c83-bc0276c434e2",
      "wallet_id": "e1cd42e0-1f0e-427c-aae0-41252df580c0",
      "user_id": "test-user-001",
      "transaction_type": "consume",
      "amount": "10.0",
      "balance_before": "120.0",
      "balance_after": "110.0",
      "fee": "0.0",
      "description": "Consumed: 10.0",
      "reference_id": null,
      "created_at": "2025-09-26T06:39:59.031868Z",
      "updated_at": "2025-09-26T06:39:59.040944Z"
    },
    {
      "transaction_id": "14b3084b-fa16-4589-9b2f-35622b03db5a",
      "wallet_id": "e1cd42e0-1f0e-427c-aae0-41252df580c0",
      "user_id": "test-user-001",
      "transaction_type": "withdraw",
      "amount": "30.0",
      "balance_before": "150.0",
      "balance_after": "120.0",
      "description": "Test withdrawal",
      "metadata": {
        "destination": "bank_account"
      },
      "created_at": "2025-09-26T06:39:11.739702Z"
    }
  ],
  "count": 2,
  "limit": 5,
  "offset": 0
}
```

## 2. Get User Transactions (All Wallets)

### Endpoint
```
GET /api/v1/users/{user_id}/transactions
```

### Query Parameters
Same as wallet transactions, plus:
- `wallet_id`: Filter by specific wallet

### Example
```bash
curl -X GET "http://localhost:8209/api/v1/users/user-123/transactions?limit=20"
```

### Response
Returns transactions from all user's wallets combined, sorted by date.

## 3. Transaction Filtering

### By Transaction Type
```bash
# Get only deposits
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?transaction_type=deposit"

# Get only withdrawals
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?transaction_type=withdraw"

# Get only consumptions
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?transaction_type=consume"
```

### By Date Range
```bash
# Transactions in September 2025
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?start_date=2025-09-01T00:00:00Z&end_date=2025-09-30T23:59:59Z"

# Today's transactions
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?start_date=2025-09-26T00:00:00Z"
```

## 4. Pagination

### Example: Page Through Results
```bash
# First page (20 records)
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?limit=20&offset=0"

# Second page
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?limit=20&offset=20"

# Third page
curl -X GET "http://localhost:8209/api/v1/wallets/{wallet_id}/transactions?limit=20&offset=40"
```

## 5. Transaction Details

Each transaction contains:

### Core Fields
- `transaction_id`: Unique identifier
- `wallet_id`: Source wallet
- `user_id`: Owner
- `transaction_type`: Type of transaction
- `amount`: Transaction amount
- `balance_before`: Balance before transaction
- `balance_after`: Balance after transaction
- `fee`: Transaction fee (if any)
- `description`: Human-readable description

### Optional Fields
- `reference_id`: External reference
- `usage_record_id`: Link to usage record
- `from_wallet_id`: Source wallet (for transfers)
- `to_wallet_id`: Destination wallet (for transfers)
- `metadata`: Additional JSON data

### Blockchain Fields (for crypto wallets)
- `blockchain_tx_hash`: Transaction hash
- `blockchain_network`: Network name
- `blockchain_status`: Transaction status
- `blockchain_confirmations`: Number of confirmations
- `gas_fee`: Gas fee paid

### Timestamps
- `created_at`: Transaction creation time
- `updated_at`: Last update time

## 6. Statistics

### Get Wallet Statistics
```
GET /api/v1/wallets/{wallet_id}/statistics
```

### Get User Statistics
```
GET /api/v1/users/{user_id}/statistics
```

### Response
```json
{
  "total_deposits": 250.0,
  "total_withdrawals": 50.0,
  "total_consumed": 40.0,
  "total_transferred_in": 10.0,
  "total_transferred_out": 5.0,
  "transaction_count": 15,
  "period_start": "2025-09-01",
  "period_end": "2025-09-30"
}
```

## Best Practices

1. **Use Pagination**
   - Always paginate large result sets
   - Default limit is 20, max is 100
   - Use offset for page navigation

2. **Filter Efficiently**
   - Use transaction_type to reduce data
   - Apply date ranges for reports
   - Combine filters for specific queries

3. **Cache When Possible**
   - Transaction history is immutable
   - Cache old transactions
   - Only query recent changes

4. **Monitor Performance**
   - Index on common query fields
   - Use appropriate date ranges
   - Avoid unbounded queries

## Error Handling

### Invalid Parameters
```json
{
  "detail": "Invalid date format. Use ISO 8601"
}
```

### No Transactions Found
```json
{
  "transactions": [],
  "count": 0,
  "limit": 20,
  "offset": 0
}
```