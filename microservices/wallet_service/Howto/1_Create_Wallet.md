# How to Create a Digital Wallet

## Overview
The Wallet Service allows you to create and manage digital wallets for users. Each wallet can store credits/tokens and support various transaction types.

## Wallet Types
- **fiat**: Traditional credits/points system
- **crypto**: Blockchain-based tokens
- **hybrid**: Both fiat and crypto support

## API Endpoint
```
POST /api/v1/wallets
```

## Request Format
```json
{
  "user_id": "string",           // Required: User ID
  "name": "string",              // Optional: Wallet name
  "wallet_type": "fiat",         // Required: fiat, crypto, or hybrid
  "initial_balance": 0,          // Optional: Initial balance (default: 0)
  "currency": "CREDIT",          // Optional: Currency type
  "blockchain_address": null,    // Optional: For crypto wallets
  "blockchain_network": null     // Optional: ethereum, bsc, polygon, etc.
}
```

## Example: Create a Fiat Wallet

### Request
```bash
curl -X POST http://localhost:8209/api/v1/wallets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-new",
    "name": "New User Wallet",
    "wallet_type": "fiat",
    "initial_balance": 50.0
  }'
```

### Response
```json
{
  "success": true,
  "message": "Wallet created successfully",
  "wallet_id": "ab2f9670-ef6b-46d0-9d0e-7bd344a35a14",
  "balance": "50.0",
  "transaction_id": null,
  "data": {
    "wallet": {
      "wallet_id": "ab2f9670-ef6b-46d0-9d0e-7bd344a35a14",
      "user_id": "test-user-new",
      "balance": "50.0",
      "locked_balance": "0.0",
      "available_balance": "50.0",
      "currency": "CREDIT",
      "wallet_type": "fiat",
      "last_updated": "2025-09-26T12:23:56.586062Z",
      "blockchain_address": null,
      "blockchain_network": null,
      "on_chain_balance": null,
      "sync_status": null
    }
  }
}
```

## Example: Create a Crypto Wallet

### Request
```bash
curl -X POST http://localhost:8209/api/v1/wallets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-456",
    "name": "ETH Wallet",
    "wallet_type": "crypto",
    "blockchain_address": "0x1234567890abcdef...",
    "blockchain_network": "ethereum"
  }'
```

## Error Handling

### Invalid Wallet Type
```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "wallet_type"],
      "msg": "Input should be 'fiat', 'crypto' or 'hybrid'"
    }
  ]
}
```

### Database Error
```json
{
  "detail": "400: Failed to create wallet"
}
```

## Important Notes

### Service Autonomy (2025-09-26 Update)
- **No user validation required**: The wallet service can create wallets for any user_id
- **Microservices best practice**: Service operates independently without requiring users to exist in other services first
- **Foreign key constraints removed**: Database-level constraints have been removed to maintain service autonomy
- **Graceful degradation**: Service continues to work even if account service is unavailable

### Technical Details
- Each user can have multiple wallets
- Initial balance creates an automatic deposit transaction
- Wallet IDs are UUIDs generated automatically
- All balances support up to 8 decimal places
- User validation happens via API calls (optional) with fallback tolerance