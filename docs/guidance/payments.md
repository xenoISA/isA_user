# Payments

Payment processing, billing, and financial services.

## Overview

Financial operations are handled by five services:

| Service | Port | Purpose |
|---------|------|---------|
| payment_service | 8207 | Stripe, crypto, payment intents |
| wallet_service | 8208 | Virtual wallets, balances |
| billing_service | 8216 | Invoicing, usage billing |
| subscription_service | 8228 | Subscription lifecycle |
| credit_service | 8229 | Credit system, redemption |

## Payment Service (8207)

### Create Payment Intent

```bash
curl -X POST "http://localhost:8207/api/v1/payments/intent" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 2999,
    "currency": "usd",
    "description": "Pro Plan - Monthly",
    "metadata": {
      "product_id": "prod_123",
      "user_id": "user_456"
    }
  }'
```

Response:
```json
{
  "payment_intent_id": "pi_abc123",
  "client_secret": "pi_abc123_secret_xyz",
  "amount": 2999,
  "currency": "usd",
  "status": "requires_payment_method"
}
```

### Confirm Payment

```bash
curl -X POST "http://localhost:8207/api/v1/payments/intent/pi_abc123/confirm" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_method_id": "pm_card_visa"
  }'
```

### Get Payment History

```bash
curl "http://localhost:8207/api/v1/payments/history" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Process Refund

```bash
curl -X POST "http://localhost:8207/api/v1/payments/pi_abc123/refund" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 2999,
    "reason": "customer_request"
  }'
```

### Cryptocurrency Support

```bash
curl -X POST "http://localhost:8207/api/v1/payments/crypto" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100,
    "currency": "usdc",
    "blockchain": "ethereum",
    "wallet_address": "0x..."
  }'
```

## Wallet Service (8208)

### Get Wallet Balance

```bash
curl "http://localhost:8208/api/v1/wallets/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "wallet_id": "wallet_123",
  "balances": {
    "usd": 15000,
    "credits": 500
  },
  "pending": {
    "usd": 0
  }
}
```

### Add Funds

```bash
curl -X POST "http://localhost:8208/api/v1/wallets/me/deposit" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000,
    "currency": "usd",
    "payment_method_id": "pm_card_visa"
  }'
```

### Transfer Between Users

```bash
curl -X POST "http://localhost:8208/api/v1/wallets/transfer" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_user_id": "user_789",
    "amount": 1000,
    "currency": "usd",
    "note": "Payment for services"
  }'
```

### Transaction History

```bash
curl "http://localhost:8208/api/v1/wallets/me/transactions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Billing Service (8216)

### Create Invoice

```bash
curl -X POST "http://localhost:8216/api/v1/billing/invoices" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "user_456",
    "items": [
      {
        "description": "API Usage - January",
        "quantity": 10000,
        "unit_price": 1
      }
    ],
    "due_date": "2024-02-15"
  }'
```

### Get Invoices

```bash
curl "http://localhost:8216/api/v1/billing/invoices" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Usage-Based Billing

```bash
# Record usage
curl -X POST "http://localhost:8216/api/v1/billing/usage" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "api_calls",
    "quantity": 150,
    "timestamp": "2024-01-28T10:00:00Z"
  }'
```

### Billing Cycles

| Plan | Cycle | Features |
|------|-------|----------|
| Free | - | 1000 API calls/month |
| Pro | Monthly | 50,000 API calls |
| Enterprise | Annual | Unlimited |

## Subscription Service (8228)

### Create Subscription

```bash
curl -X POST "http://localhost:8228/api/v1/subscriptions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan_pro_monthly",
    "payment_method_id": "pm_card_visa"
  }'
```

### Get Subscription

```bash
curl "http://localhost:8228/api/v1/subscriptions/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "subscription_id": "sub_123",
  "plan": {
    "id": "plan_pro_monthly",
    "name": "Pro Monthly",
    "price": 2999,
    "interval": "month"
  },
  "status": "active",
  "current_period_end": "2024-02-28T00:00:00Z",
  "cancel_at_period_end": false
}
```

### Change Plan

```bash
curl -X POST "http://localhost:8228/api/v1/subscriptions/me/change" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_plan_id": "plan_enterprise_annual",
    "prorate": true
  }'
```

### Cancel Subscription

```bash
curl -X POST "http://localhost:8228/api/v1/subscriptions/me/cancel" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "at_period_end": true,
    "reason": "switching_to_competitor"
  }'
```

## Credit Service (8229)

### Get Credits

```bash
curl "http://localhost:8229/api/v1/credits/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "total_credits": 500,
  "available_credits": 450,
  "reserved_credits": 50,
  "expiring_soon": {
    "amount": 100,
    "expires_at": "2024-03-01T00:00:00Z"
  }
}
```

### Purchase Credits

```bash
curl -X POST "http://localhost:8229/api/v1/credits/purchase" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "package": "credits_1000",
    "payment_method_id": "pm_card_visa"
  }'
```

### Use Credits

```bash
curl -X POST "http://localhost:8229/api/v1/credits/consume" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10,
    "reason": "api_premium_feature",
    "metadata": {
      "feature": "image_generation"
    }
  }'
```

### Credit Packages

| Package | Credits | Price |
|---------|---------|-------|
| Starter | 100 | $10 |
| Standard | 500 | $45 |
| Pro | 1000 | $80 |
| Enterprise | 5000 | $350 |

## Webhooks

### Payment Events

```python
# Webhook handler example
@app.post("/webhooks/payments")
async def handle_payment_webhook(request: Request):
    event = await request.json()

    if event["type"] == "payment.succeeded":
        # Handle successful payment
        pass
    elif event["type"] == "payment.failed":
        # Handle failed payment
        pass
    elif event["type"] == "subscription.canceled":
        # Handle subscription cancellation
        pass
```

### Event Types

| Event | Description |
|-------|-------------|
| `payment.succeeded` | Payment completed |
| `payment.failed` | Payment failed |
| `subscription.created` | New subscription |
| `subscription.canceled` | Subscription canceled |
| `invoice.paid` | Invoice paid |
| `refund.created` | Refund processed |

## Python SDK

```python
from isa_user import PaymentClient, WalletClient

payment = PaymentClient("http://localhost:8207")
wallet = WalletClient("http://localhost:8208")

# Create payment intent
intent = await payment.create_intent(
    token=access_token,
    amount=2999,
    currency="usd"
)

# Check wallet balance
balance = await wallet.get_balance(token=access_token)

# Process subscription
subscription = await payment.create_subscription(
    token=access_token,
    plan_id="plan_pro_monthly"
)
```

## Next Steps

- [Storage](./storage) - File management
- [Organizations](./organizations) - Multi-tenant
- [Authentication](./authentication) - Auth details
