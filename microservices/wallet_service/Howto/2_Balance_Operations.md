# How to Manage Wallet Balances

## Overview
The Wallet Service provides multiple ways to check and manage wallet balances, including getting current balance, available balance, and locked balance.

## 1. Get Wallet Balance

### Endpoint
```
GET /api/v1/wallets/{wallet_id}/balance
```

### Example Request
```bash
curl -X GET http://localhost:8209/api/v1/wallets/e1cd42e0-1f0e-427c-aae0-41252df580c0/balance
```

### Response
```json
{
  "success": true,
  "message": "Balance retrieved successfully",
  "wallet_id": "e1cd42e0-1f0e-427c-aae0-41252df580c0",
  "balance": "100.0",
  "data": {
    "balance": 100.0,
    "locked_balance": 0.0,
    "available_balance": 100.0,
    "currency": "CREDIT",
    "on_chain_balance": null
  }
}
```

## 2. Get User's Total Credits

### Endpoint
```
GET /api/v1/users/{user_id}/credits/balance
```

### Example Request
```bash
curl -X GET http://localhost:8209/api/v1/users/user-123/credits/balance
```

### Response
```json
{
  "success": true,
  "user_id": "user-123",
  "total_balance": 250.0,
  "available_balance": 230.0,
  "locked_balance": 20.0,
  "wallets": [
    {
      "wallet_id": "wallet-1",
      "balance": 150.0,
      "locked_balance": 20.0,
      "currency": "CREDIT"
    },
    {
      "wallet_id": "wallet-2",
      "balance": 100.0,
      "locked_balance": 0.0,
      "currency": "CREDIT"
    }
  ]
}
```

## 3. Get All User Wallets

### Endpoint
```
GET /api/v1/users/{user_id}/wallets
```

### Example Request
```bash
curl -X GET http://localhost:8209/api/v1/users/user-123/wallets
```

### Response
```json
{
  "wallets": [
    {
      "wallet_id": "e1cd42e0-1f0e-427c-aae0-41252df580c0",
      "user_id": "user-123",
      "balance": "110.0",
      "locked_balance": "0.0",
      "available_balance": "110.0",
      "currency": "CREDIT",
      "wallet_type": "fiat",
      "last_updated": "2025-09-26T06:39:59.026806Z"
    }
  ],
  "count": 1
}
```

## 4. Get Specific Wallet Details

### Endpoint
```
GET /api/v1/wallets/{wallet_id}
```

### Example Request
```bash
curl -X GET http://localhost:8209/api/v1/wallets/e1cd42e0-1f0e-427c-aae0-41252df580c0
```

### Response
```json
{
  "success": true,
  "wallet": {
    "wallet_id": "e1cd42e0-1f0e-427c-aae0-41252df580c0",
    "user_id": "user-123",
    "balance": "110.0",
    "locked_balance": "0.0",
    "available_balance": "110.0",
    "currency": "CREDIT",
    "wallet_type": "fiat",
    "created_at": "2025-09-26T06:37:57.042863Z",
    "last_updated": "2025-09-26T06:39:59.026806Z"
  }
}
```

## Balance Types Explained

### 1. **Balance**
Total amount in the wallet, including locked funds.

### 2. **Locked Balance**
Amount reserved for pending transactions or held for specific purposes. Cannot be spent until released.

### 3. **Available Balance**
Amount available for immediate use: `available_balance = balance - locked_balance`

### 4. **On-Chain Balance**
For crypto wallets, the actual balance on the blockchain (may differ from internal balance during sync).

## Error Handling

### Wallet Not Found
```json
{
  "detail": "404: Wallet not found"
}
```

### Invalid Wallet ID
```json
{
  "detail": "Invalid wallet ID format"
}
```

## Best Practices
1. Always check available balance before performing transactions
2. Monitor locked balance for pending operations
3. Use user-level balance endpoint for aggregate views
4. Cache balance queries when appropriate to reduce load