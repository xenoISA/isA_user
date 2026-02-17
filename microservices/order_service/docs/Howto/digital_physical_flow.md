# Mixed Digital + Physical Order Flow (Smoke Test)

This guide validates the end-to-end flow across order, payment, inventory, tax, and fulfillment.

## Prereqs
- Order, Payment, Inventory, Tax, Fulfillment services running locally.
- NATS event bus available.
- Stripe test key configured for payment_service (optional for mock).

## 1) Create a physical order

```bash
curl -X POST http://localhost:8210/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_test_001",
    "order_type": "purchase",
    "total_amount": 199.99,
    "currency": "USD",
    "items": [
      {
        "product_id": "product_physical_01",
        "sku_id": "sku_test_physical_01",
        "title": "Smart Frame",
        "quantity": 1,
        "unit_price": 199.99,
        "fulfillment_type": "ship"
      }
    ],
    "shipping_address": {
      "name": "Test User",
      "line1": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "US",
      "phone": "+1-555-0000"
    }
  }'
```

## 2) Verify payment intent attached

```bash
curl http://localhost:8210/api/v1/orders/{order_id}
```

Confirm `payment_intent_id` is set (created by payment_service).

## 3) Simulate payment confirmation (test mode)

```bash
curl -X POST http://localhost:8210/api/v1/orders/{order_id}/complete \
  -H "Content-Type: application/json" \
  -d '{
    "payment_confirmed": true,
    "transaction_id": "pi_test_123"
  }'
```

This triggers:
- inventory commit
- fulfillment shipment creation
- order tracking number update

## 4) Check fulfillment status

```bash
curl http://localhost:8210/api/v1/orders/{order_id}
```

Expect `fulfillment_status` = `shipped` and `tracking_number` present.

## 5) Create a digital-only order (no shipping address)

```bash
curl -X POST http://localhost:8210/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_test_001",
    "order_type": "purchase",
    "total_amount": 9.99,
    "currency": "USD",
    "items": [
      {
        "product_id": "product_digital_01",
        "sku_id": "sku_test_digital_01",
        "title": "Digital Addon",
        "quantity": 1,
        "unit_price": 9.99,
        "fulfillment_type": "digital"
      }
    ]
  }'
```

Digital orders should pass without shipping details.
