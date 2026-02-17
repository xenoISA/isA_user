# Order Service 使用指南

## 服务概述

Order Service 是订单管理微服务，负责处理订单生命周期、记录交易、与支付和钱包服务集成。

**端口**: 8210  
**基础URL**: `http://localhost:8210`  
**版本**: 1.0.0

## 服务架构

Order Service 在微服务架构中的位置：
- **上游服务**: API Gateway, Payment Service  
- **下游服务**: Wallet Service (充值/退款)
- **通信方式**: HTTP REST API
- **服务发现**: Consul

## 快速开始

### 1. 启动服务
```bash
cd microservices/order_service
python main.py

# 或使用模块方式
python -m microservices.order_service.main
```

### 2. 健康检查
```bash
curl http://localhost:8210/health
```

**响应**:
```json
{
  "status": "healthy",
  "service": "order_service", 
  "port": 8210,
  "version": "1.0.0"
}
```

## API 端点测试

### 1. 创建订单 ✅

**请求**:
```bash
curl -X POST http://localhost:8210/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "auth0|test123",
    "order_type": "credit_purchase",
    "total_amount": 99.99,
    "currency": "USD",
    "wallet_id": "wallet_test_001",
    "items": [{"name": "1000 Credits", "amount": 99.99, "quantity": 1}],
    "metadata": {"description": "Credit purchase for API usage"},
    "expires_in_minutes": 30
  }'
```

**实际响应**:
```json
{
  "success": true,
  "order": {
    "order_id": "order_3a279aca570c",
    "user_id": "auth0|test123",
    "order_type": "credit_purchase",
    "status": "pending",
    "total_amount": "99.99",
    "currency": "USD",
    "payment_status": "pending",
    "payment_intent_id": null,
    "subscription_id": null,
    "wallet_id": "wallet_test_001",
    "items": [{"name": "1000 Credits", "amount": 99.99, "quantity": 1}],
    "metadata": {"description": "Credit purchase for API usage"},
    "created_at": "2025-09-20T05:56:52.145615Z",
    "updated_at": "2025-09-20T05:56:52.145615Z",
    "completed_at": null,
    "expires_at": "2025-09-20T06:26:52.145559Z"
  },
  "message": "Order created successfully"
}
```

### 2. 获取订单详情 ✅

**请求**:
```bash
curl http://localhost:8210/api/v1/orders/order_3a279aca570c
```

**实际响应**:
```json
{
  "order_id": "order_3a279aca570c",
  "user_id": "auth0|test123",
  "order_type": "credit_purchase",
  "status": "pending",
  "total_amount": "99.99",
  "currency": "USD",
  "payment_status": "pending",
  "items": [{"name": "1000 Credits", "amount": 99.99, "quantity": 1}],
  "metadata": {"description": "Credit purchase for API usage"},
  "created_at": "2025-09-20T05:56:52.145615Z",
  "updated_at": "2025-09-20T05:56:52.145615Z",
  "expires_at": "2025-09-20T06:26:52.145559Z"
}
```

### 3. 获取用户订单列表 ✅

**请求**:
```bash
curl http://localhost:8210/api/v1/users/auth0%7Ctest123/orders
```

**实际响应**:
```json
{
  "orders": [
    {
      "order_id": "order_3a279aca570c",
      "user_id": "auth0|test123",
      "order_type": "credit_purchase",
      "status": "pending",
      "total_amount": "99.99",
      "currency": "USD",
      "payment_status": "pending",
      "created_at": "2025-09-20T05:56:52.145615Z"
    }
  ],
  "count": 1,
  "limit": 50,
  "offset": 0
}
```

### 4. 更新订单

```bash
curl -X PUT http://localhost:8210/api/v1/orders/order_3a279aca570c \
  -H "Content-Type: application/json" \
  -d '{
    "status": "processing",
    "payment_intent_id": "pi_test_123456"
  }'
```

### 5. 完成订单（与钱包集成）

```bash
curl -X POST http://localhost:8210/api/v1/orders/order_3a279aca570c/complete \
  -H "Content-Type: application/json" \
  -d '{
    "payment_confirmed": true,
    "transaction_id": "txn_test_123",
    "credits_added": 1000.0
  }'
```

### 6. 取消订单

```bash
curl -X POST http://localhost:8210/api/v1/orders/order_3a279aca570c/cancel \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "User requested cancellation",
    "refund_amount": 99.99
  }'
```

### 7. 订单搜索

```bash
curl "http://localhost:8210/api/v1/orders/search?query=credit&limit=10"
```

### 8. 订单统计

```bash
curl http://localhost:8210/api/v1/orders/statistics
```

## 订单类型

### OrderType 枚举
- `purchase` - 普通购买
- `subscription` - 订阅
- `credit_purchase` - 积分购买
- `premium_upgrade` - 高级升级

### OrderStatus 枚举
- `pending` - 待处理
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败
- `cancelled` - 已取消
- `refunded` - 已退款

### PaymentStatus 枚举
- `pending` - 待支付
- `processing` - 支付中
- `completed` - 支付完成
- `failed` - 支付失败
- `refunded` - 已退款

## 微服务集成

### 与 Payment Service 集成
Order Service 在创建订单时会与 Payment Service 通信创建支付意图：

```python
# 内部实现示例
payment_request = {
    "amount": order.total_amount,
    "currency": order.currency,
    "description": f"Order {order.order_id}",
    "user_id": order.user_id,
    "order_id": order.order_id
}
response = await http_client.post("http://localhost:8207/api/payments/intent", json=payment_request)
```

### 与 Wallet Service 集成
完成积分购买订单时，会自动调用 Wallet Service 添加积分：

```python
# 内部实现示例
wallet_request = {
    "user_id": order.user_id,
    "amount": credits_added,
    "order_id": order.order_id,
    "description": f"Credits from order {order.order_id}"
}
response = await http_client.post(f"http://localhost:8209/api/v1/wallets/{wallet_id}/deposit", json=wallet_request)
```

## 完整交易流程

### 积分充值流程
1. **创建订单** → Order Service
2. **创建支付意图** → Payment Service (通过 Order Service)
3. **用户支付** → Payment Gateway
4. **确认支付** → Payment Service
5. **完成订单** → Order Service
6. **添加积分** → Wallet Service (通过 Order Service)

### 流程图
```
用户 → API Gateway → Order Service → Payment Service
                     ↓                ↓
                     Database         Stripe/支付网关
                     ↓
                     Wallet Service → 积分到账
```

## 数据库架构

### orders 表结构
```sql
CREATE TABLE dev.orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE,
    user_id VARCHAR(255),
    order_type VARCHAR(50),
    status VARCHAR(50),
    total_amount DECIMAL(10, 2),
    currency VARCHAR(3),
    payment_status VARCHAR(50),
    payment_intent_id VARCHAR(255),
    subscription_id VARCHAR(255),
    wallet_id VARCHAR(255),
    items JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);
```

## 错误处理

### 常见错误

1. **订单不存在**
```json
{
  "detail": "Order not found"
}
```

2. **验证错误**
```json
{
  "success": false,
  "message": "wallet_id is required for credit purchases",
  "error_code": "VALIDATION_ERROR"
}
```

3. **支付未确认**
```json
{
  "success": false,
  "message": "Payment not confirmed",
  "error_code": "PAYMENT_NOT_CONFIRMED"
}
```

## 开发建议

### 创建积分充值订单示例
```javascript
async function createCreditOrder(userId, amount, credits) {
  const order = await fetch('http://localhost:8210/api/v1/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      order_type: 'credit_purchase',
      total_amount: amount,
      currency: 'USD',
      wallet_id: getUserWalletId(userId),
      items: [{
        name: `${credits} Credits`,
        amount: amount,
        quantity: 1
      }],
      metadata: {
        credits_amount: credits,
        description: 'Credit purchase for API usage'
      },
      expires_in_minutes: 30
    })
  });
  
  return await order.json();
}
```

### 完成订单并添加积分
```javascript
async function completeOrderWithCredits(orderId, paymentId, credits) {
  const response = await fetch(`http://localhost:8210/api/v1/orders/${orderId}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      payment_confirmed: true,
      transaction_id: paymentId,
      credits_added: credits
    })
  });
  
  return await response.json();
}
```

## 服务监控

- **端口**: 8210
- **健康检查**: `/health`
- **详细健康检查**: `/health/detailed`
- **统计信息**: `/api/v1/orders/statistics`
- **服务信息**: `/api/v1/order/info`

## Migration 管理

订单表的 migration 文件位于：
```
microservices/order_service/migrations/001_create_orders_table.sql
```

执行 migration：
```bash
source .env && psql "$DATABASE_URL" < microservices/order_service/migrations/001_create_orders_table.sql
```

## 测试脚本

```bash
#!/bin/bash
# Order Service 完整测试脚本

BASE_URL="http://localhost:8210"

echo "=== 健康检查 ==="
curl -s $BASE_URL/health | jq .

echo -e "\n=== 创建订单 ==="
ORDER_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "order_type": "credit_purchase",
    "total_amount": 49.99,
    "currency": "USD",
    "wallet_id": "wallet_001",
    "items": [{"name": "500 Credits", "amount": 49.99}]
  }')
echo $ORDER_RESPONSE | jq .

ORDER_ID=$(echo $ORDER_RESPONSE | jq -r '.order.order_id')

echo -e "\n=== 获取订单详情 ==="
curl -s $BASE_URL/api/v1/orders/$ORDER_ID | jq .

echo -e "\n=== 获取用户订单 ==="
curl -s $BASE_URL/api/v1/users/test_user_001/orders | jq .

echo -e "\n=== 订单统计 ==="
curl -s $BASE_URL/api/v1/orders/statistics | jq .
```

---

**最后更新**: 2025-09-20 | **服务版本**: 1.0.0 | **状态**: ✅ 运行中