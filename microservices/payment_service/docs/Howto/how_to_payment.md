# Payment Service 使用指南

## 服务概述
Payment Service 提供完整的支付管理功能，包括订阅管理、支付处理、发票生成和退款处理。

**端口**: 8207  
**基础URL**: `http://localhost:8207`

## 快速开始

### 1. 启动服务
```bash
cd microservices/payment_service
python main.py
```

### 2. 健康检查
```bash
curl http://localhost:8207/health
```

## 真实测试用例

### 测试场景 1: 创建订阅计划并订阅

#### 步骤 1: 创建Pro订阅计划
```bash
curl -X POST http://localhost:8207/api/plans \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pro Plan",
    "tier": "pro",
    "price": 29.99,
    "currency": "USD",
    "billing_cycle": "monthly",
    "features": {
      "api_calls": 10000,
      "storage_gb": 100,
      "support": "priority"
    },
    "credits_included": 1000,
    "trial_days": 14
  }'
```

**实际响应**:
```json
{
  "plan": {
    "id": 1,
    "plan_id": "plan_pro_1758205021.7054584",
    "name": "Pro Plan",
    "description": null,
    "tier": "pro",
    "price": 29.99,
    "currency": "USD",
    "billing_cycle": "monthly",
    "features": {
      "api_calls": 10000,
      "storage_gb": 100,
      "support": "priority"
    },
    "credits_included": 1000,
    "max_users": null,
    "max_storage_gb": null,
    "trial_days": 14,
    "stripe_price_id": null,
    "stripe_product_id": null,
    "is_active": true,
    "is_public": true,
    "created_at": "2025-09-18T20:57:01.705656",
    "updated_at": "2025-09-18T20:57:01.705656"
  },
  "message": "Subscription plan created successfully"
}
```

#### 步骤 2: 创建用户订阅
```bash
curl -X POST http://localhost:8207/api/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "plan_id": "plan_pro_1758205021.7054584"
  }'
```

**实际响应**:
```json
{
  "subscription": {
    "id": 1,
    "subscription_id": "sub_user_123_plan_pro_1758205021.7054584_1758205145.5679572",
    "user_id": "user_123",
    "organization_id": null,
    "plan_id": "plan_pro_1758205021.7054584",
    "status": "trialing",
    "tier": "pro",
    "current_period_start": "2025-09-18T20:59:05.568103",
    "current_period_end": "2025-10-18T20:59:05.568103",
    "billing_cycle": "monthly",
    "trial_start": "2025-09-18T20:59:05.568103",
    "trial_end": "2025-10-02T20:59:05.568103",
    "cancel_at_period_end": false,
    "canceled_at": null,
    "cancellation_reason": null,
    "payment_method_id": null,
    "last_payment_date": null,
    "next_payment_date": "2025-10-02T20:59:05.568103",
    "stripe_subscription_id": null,
    "stripe_customer_id": null,
    "metadata": null,
    "created_at": "2025-09-18T20:59:05.568106",
    "updated_at": "2025-09-18T20:59:05.568106"
  },
  "plan": {
    "id": 1,
    "plan_id": "plan_pro_1758205021.7054584",
    "name": "Pro Plan",
    "description": null,
    "tier": "pro",
    "price": 29.99,
    "currency": "USD",
    "billing_cycle": "monthly",
    "features": {
      "api_calls": 10000,
      "storage_gb": 100,
      "support": "priority"
    },
    "credits_included": 1000,
    "max_users": null,
    "max_storage_gb": null,
    "trial_days": 14,
    "stripe_price_id": null,
    "stripe_product_id": null,
    "is_active": true,
    "is_public": true,
    "created_at": "2025-09-18T20:57:01.705656",
    "updated_at": "2025-09-18T20:57:01.705656"
  },
  "next_invoice": null,
  "payment_method": null
}
```

### 测试场景 2: 支付处理

#### 创建支付意图
```bash
curl -X POST http://localhost:8207/api/payments/intent \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 99.99,
    "currency": "USD",
    "description": "Premium Features Package",
    "user_id": "user_123"
  }'
```

**实际响应**:
```json
{
  "payment_intent_id": "pi_1758205234.567890",
  "client_secret": null,
  "amount": 99.99,
  "currency": "USD",
  "status": "pending",
  "metadata": null
}
```

### 测试场景 3: 获取用户订阅

```bash
curl http://localhost:8207/api/subscriptions/user/user_123
```

**实际响应**:
```json
{
  "subscription": {
    "id": 1,
    "subscription_id": "sub_user_123_plan_pro_1758205021.7054584_1758205145.5679572",
    "user_id": "user_123",
    "plan_id": "plan_pro_1758205021.7054584",
    "status": "trialing",
    "tier": "pro",
    "current_period_start": "2025-09-18T20:59:05.568103",
    "current_period_end": "2025-10-18T20:59:05.568103",
    "trial_end": "2025-10-02T20:59:05.568103"
  },
  "plan": {
    "name": "Pro Plan",
    "price": 29.99,
    "billing_cycle": "monthly",
    "features": {
      "api_calls": 10000,
      "storage_gb": 100,
      "support": "priority"
    }
  }
}
```

### 测试场景 4: 取消订阅

```bash
curl -X POST http://localhost:8207/api/subscriptions/sub_user_123_plan_pro_1758205021.7054584_1758205145.5679572/cancel \
  -H "Content-Type: application/json" \
  -d '{
    "immediate": false,
    "reason": "No longer needed"
  }'
```

**实际响应**:
```json
{
  "subscription": {
    "subscription_id": "sub_user_123_plan_pro_1758205021.7054584_1758205145.5679572",
    "status": "trialing",
    "cancel_at_period_end": true,
    "canceled_at": "2025-09-18T21:05:00.123456"
  },
  "message": "Subscription will be canceled at the end of the current period"
}
```

## 常见错误及解决方案

### 1. 重复订阅错误
**错误**:
```json
{
  "detail": "User already has an active subscription"
}
```
**解决**: 先取消或更新现有订阅

### 2. 计划不存在
**错误**:
```json
{
  "detail": "Subscription plan not found"
}
```
**解决**: 确认plan_id正确或先创建计划

### 3. 支付失败
**错误**:
```json
{
  "detail": "Payment processing failed: Invalid payment method"
}
```
**解决**: 检查支付方式配置

## 数据库表结构

服务使用以下数据库表：
- `dev.payment_plans` - 订阅计划
- `dev.payment_subscriptions` - 用户订阅
- `dev.payments` - 支付记录
- `dev.invoices` - 发票
- `dev.refunds` - 退款
- `dev.payment_methods` - 支付方式

## 环境变量配置

可选配置（在 `.env` 文件中）：
```env
# Stripe集成（可选）
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# 其他支付网关（可选）
ALIPAY_APP_ID=...
WECHAT_PAY_MERCHANT_ID=...
```

**注意**: 即使没有配置Stripe，服务仍可正常运行并记录所有交易。

## 订阅生命周期

1. **创建计划** → 2. **用户订阅** → 3. **试用期** → 4. **付费期** → 5. **续订/取消**

### 订阅状态流转
- `trialing` → `active` (试用期结束后自动转换)
- `active` → `past_due` (付款失败)
- `active` → `canceled` (用户取消)
- `past_due` → `active` (补缴成功)

## API端点汇总

### 订阅计划
- `POST /api/plans` - 创建计划
- `GET /api/plans` - 列出所有计划
- `GET /api/plans/{plan_id}` - 获取特定计划
- `PUT /api/plans/{plan_id}` - 更新计划

### 订阅管理
- `POST /api/subscriptions` - 创建订阅
- `GET /api/subscriptions/user/{user_id}` - 获取用户订阅
- `PUT /api/subscriptions/{subscription_id}` - 更新订阅
- `POST /api/subscriptions/{subscription_id}/cancel` - 取消订阅

### 支付处理
- `POST /api/payments/intent` - 创建支付意图
- `POST /api/payments/{payment_id}/confirm` - 确认支付
- `GET /api/payments/history` - 支付历史

### 发票管理
- `GET /api/invoices` - 列出发票
- `GET /api/invoices/{invoice_id}` - 获取特定发票

### 退款处理
- `POST /api/refunds` - 创建退款
- `POST /api/refunds/{refund_id}/process` - 处理退款

## 测试建议

1. 使用测试用户ID（如 `test_user_001`）
2. 创建不同层级的计划进行测试
3. 测试订阅升级/降级流程
4. 验证并发订阅防护
5. 测试退款金额限制

## 故障排除

### 服务无法启动
- 检查端口8207是否被占用
- 验证数据库连接配置
- 查看日志文件获取详细错误

### 订阅创建失败
- 确认用户没有其他活跃订阅
- 验证计划存在且激活
- 检查请求参数格式

### 支付处理失败
- 验证金额和货币格式
- 检查Stripe配置（如果使用）
- 确认用户和支付方式有效