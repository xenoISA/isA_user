# Commerce

Order management and product catalog services.

## Overview

Commerce capabilities are handled by two services:

| Service | Port | Purpose |
|---------|------|---------|
| order_service | 8210 | Order lifecycle, fulfillment |
| product_service | 8215 | Product catalog, pricing |

## Order Service (8210)

### Create Order

```bash
curl -X POST "http://localhost:8210/api/v1/orders" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "product_id": "prod_123",
        "quantity": 2,
        "unit_price": 2999
      }
    ],
    "payment_method_id": "pm_card_visa",
    "shipping_address": {
      "line1": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "postal_code": "94102",
      "country": "US"
    },
    "metadata": {
      "source": "web"
    }
  }'
```

Response:
```json
{
  "order_id": "ord_abc123",
  "status": "pending",
  "items": [
    {
      "product_id": "prod_123",
      "name": "Pro Plan",
      "quantity": 2,
      "unit_price": 2999,
      "subtotal": 5998
    }
  ],
  "subtotal": 5998,
  "tax": 540,
  "total": 6538,
  "currency": "usd",
  "created_at": "2024-01-28T10:30:00Z"
}
```

### Get Order

```bash
curl "http://localhost:8210/api/v1/orders/ord_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Orders

```bash
curl "http://localhost:8210/api/v1/orders?status=completed&limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Search Orders

```bash
curl "http://localhost:8210/api/v1/orders/search?q=pro+plan&from=2024-01-01" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Order

```bash
curl -X PUT "http://localhost:8210/api/v1/orders/ord_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": {
      "line1": "456 Oak Ave",
      "city": "San Francisco",
      "state": "CA",
      "postal_code": "94103",
      "country": "US"
    }
  }'
```

### Complete Order

```bash
curl -X POST "http://localhost:8210/api/v1/orders/ord_abc123/complete" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fulfillment_details": {
      "tracking_number": "1Z999AA10123456784",
      "carrier": "ups"
    }
  }'
```

### Cancel Order

```bash
curl -X POST "http://localhost:8210/api/v1/orders/ord_abc123/cancel" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "customer_request",
    "refund": true
  }'
```

### Get Order Statistics

```bash
curl "http://localhost:8210/api/v1/orders/statistics" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "total_orders": 1500,
  "total_revenue": 4500000,
  "orders_by_status": {
    "pending": 50,
    "processing": 25,
    "completed": 1400,
    "cancelled": 25
  },
  "average_order_value": 3000,
  "period": "all_time"
}
```

### Get Orders by Payment

```bash
curl "http://localhost:8210/api/v1/payments/pi_abc123/orders" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Orders by Subscription

```bash
curl "http://localhost:8210/api/v1/subscriptions/sub_123/orders" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Order Status

| Status | Description |
|--------|-------------|
| `pending` | Order created, awaiting payment |
| `paid` | Payment received |
| `processing` | Order being prepared |
| `shipped` | Order shipped |
| `delivered` | Order delivered |
| `completed` | Order fulfilled |
| `cancelled` | Order cancelled |
| `refunded` | Order refunded |

## Product Service (8215)

### Create Product

```bash
curl -X POST "http://localhost:8215/api/v1/products" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pro Plan",
    "description": "Professional features for power users",
    "type": "subscription",
    "category": "software",
    "pricing": {
      "type": "recurring",
      "amount": 2999,
      "currency": "usd",
      "interval": "month"
    },
    "features": [
      "Unlimited API calls",
      "Priority support",
      "Advanced analytics"
    ],
    "metadata": {
      "tier": "professional"
    }
  }'
```

Response:
```json
{
  "product_id": "prod_abc123",
  "name": "Pro Plan",
  "type": "subscription",
  "category": "software",
  "pricing": {
    "type": "recurring",
    "amount": 2999,
    "currency": "usd",
    "interval": "month"
  },
  "active": true,
  "created_at": "2024-01-28T10:30:00Z"
}
```

### Get Product

```bash
curl "http://localhost:8215/api/v1/products/prod_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Products

```bash
curl "http://localhost:8215/api/v1/products?category=software&active=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Product

```bash
curl -X PUT "http://localhost:8215/api/v1/products/prod_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pro Plan Plus",
    "pricing": {
      "amount": 3999
    }
  }'
```

### Get Product Pricing

```bash
curl "http://localhost:8215/api/v1/products/prod_abc123/pricing" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "product_id": "prod_abc123",
  "pricing_tiers": [
    {
      "tier": "starter",
      "amount": 999,
      "features": ["Basic features"]
    },
    {
      "tier": "pro",
      "amount": 2999,
      "features": ["All starter features", "Priority support"]
    },
    {
      "tier": "enterprise",
      "amount": 9999,
      "features": ["All pro features", "Dedicated support", "SLA"]
    }
  ],
  "billing_cycles": ["monthly", "annual"],
  "annual_discount": 20
}
```

### Create Subscription (via Product)

```bash
curl -X POST "http://localhost:8215/api/v1/subscriptions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "prod_abc123",
    "tier": "pro",
    "billing_cycle": "monthly",
    "payment_method_id": "pm_card_visa"
  }'
```

### Get User Subscription

```bash
curl "http://localhost:8215/api/v1/subscriptions/sub_123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Product Types

| Type | Description |
|------|-------------|
| `one_time` | Single purchase product |
| `subscription` | Recurring subscription |
| `metered` | Usage-based billing |
| `credit_pack` | Credit package |

### Product Categories

| Category | Examples |
|----------|----------|
| `software` | SaaS plans, licenses |
| `service` | Professional services |
| `physical` | Physical goods |
| `digital` | Digital downloads |
| `credit` | Platform credits |

### Pricing Models

```json
{
  "one_time": {
    "type": "one_time",
    "amount": 9999,
    "currency": "usd"
  },
  "recurring": {
    "type": "recurring",
    "amount": 2999,
    "currency": "usd",
    "interval": "month"
  },
  "metered": {
    "type": "metered",
    "unit_amount": 1,
    "currency": "usd",
    "unit": "api_call"
  },
  "tiered": {
    "type": "tiered",
    "tiers": [
      {"up_to": 1000, "unit_amount": 10},
      {"up_to": 10000, "unit_amount": 8},
      {"up_to": null, "unit_amount": 5}
    ]
  }
}
```

## Python SDK

```python
from isa_user import OrderClient, ProductClient

orders = OrderClient("http://localhost:8210")
products = ProductClient("http://localhost:8215")

# Create product
product = await products.create(
    token=access_token,
    name="Pro Plan",
    type="subscription",
    pricing={
        "type": "recurring",
        "amount": 2999,
        "interval": "month"
    }
)

# Create order
order = await orders.create(
    token=access_token,
    items=[{
        "product_id": product.product_id,
        "quantity": 1
    }],
    payment_method_id="pm_card_visa"
)

# Get order status
status = await orders.get(token=access_token, order_id=order.order_id)

# Complete order
await orders.complete(
    token=access_token,
    order_id=order.order_id,
    fulfillment_details={"tracking": "123"}
)

# Get order statistics
stats = await orders.get_statistics(token=access_token)
```

## Webhooks

### Order Events

```python
@app.post("/webhooks/orders")
async def handle_order_webhook(request: Request):
    event = await request.json()

    if event["type"] == "order.created":
        # New order created
        pass
    elif event["type"] == "order.paid":
        # Payment confirmed
        pass
    elif event["type"] == "order.completed":
        # Order fulfilled
        pass
    elif event["type"] == "order.cancelled":
        # Order cancelled
        pass
```

### Event Types

| Event | Description |
|-------|-------------|
| `order.created` | New order |
| `order.paid` | Payment received |
| `order.processing` | Being prepared |
| `order.shipped` | Shipped |
| `order.completed` | Fulfilled |
| `order.cancelled` | Cancelled |
| `product.created` | New product |
| `product.updated` | Product changed |

## Next Steps

- [Payments](./payments) - Payment processing
- [Utilities](./utilities) - Calendar & weather
- [Operations](./operations) - Tasks & events
