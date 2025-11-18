# 计费流程完整架构文档

## 📋 概述

本文档详细说明 isA 平台的计费系统架构，包括事件驱动流程、服务职责和数据流。

## 🏗️ 架构组件

### 1. 核心服务

```
┌─────────────────────────────────────────────────────────────┐
│                    计费生态系统                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐         │
│  │isA_Model │      │isA_MCP   │      │storage   │         │
│  │(AI推理)  │      │(工具调用)│      │(存储)    │         │
│  └────┬─────┘      └────┬─────┘      └────┬─────┘         │
│       │                 │                  │                │
│       │  usage.recorded 事件                │                │
│       └─────────────────┼──────────────────┘                │
│                         ↓                                   │
│              ┌──────────────────────┐                       │
│              │   NATS Event Bus     │                       │
│              │  (事件总线)          │                       │
│              └──────────┬───────────┘                       │
│                         ↓                                   │
│              ┌──────────────────────┐                       │
│              │  billing_service     │                       │
│              │  (计费服务)          │                       │
│              └──────────┬───────────┘                       │
│                         │                                   │
│           ┌─────────────┼─────────────┐                     │
│           │             │             │                     │
│           ↓             ↓             ↓                     │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│   │product   │  │wallet    │  │订阅      │                │
│   │_service  │  │_service  │  │管理      │                │
│   │(定价)    │  │(扣费)    │  │          │                │
│   └──────────┘  └──────────┘  └──────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. 事件契约层 (isa_common)

```python
# isa_common/events/billing_events.py

事件类型：
├── usage.recorded          # 使用记录事件（源：isA_Model/MCP/storage）
├── billing.calculated      # 计费计算完成（源：billing_service）
├── wallet.tokens.deducted  # Token扣费完成（源：wallet_service）
└── wallet.tokens.insufficient # 余额不足（源：wallet_service）
```

## 🔄 完整计费流程

### 流程 1: AI 模型调用计费

```
用户调用 GPT-4
    ↓
1. isA_Model 执行推理
   ├─ 调用 OpenAI API
   ├─ 获取 token 使用量: {input: 100, output: 200}
   └─ 发布事件到 NATS
   
2. 发布 usage.recorded 事件
   NATS Subject: usage.recorded.gpt-4
   Event Data: {
     "user_id": "usr_123",
     "product_id": "gpt-4",
     "usage_amount": 300,
     "unit_type": "token",
     "usage_details": {
       "input_tokens": 100,
       "output_tokens": 200,
       "provider": "openai",
       "model": "gpt-4",
       "operation": "chat"
     }
   }
   
3. billing_service 监听并处理
   ├─ 调用 product_service 获取定价
   │  GET /api/v1/product/products/gpt-4/pricing
   │  Response: {
   │    "unit_price": 0.00003,  # $0.03 / 1000 tokens
   │    "free_tier_included": 0,
   │    "subscription_included": 10000
   │  }
   ├─ 计算成本
   │  cost_usd = 300 * 0.00003 = $0.009
   │  token_equivalent = 300 tokens
   ├─ 检查订阅包含额度
   │  if subscription_plan == "pro":
   │    已使用 5000/10000 (还剩 5000)
   │    本次使用 300，从订阅额度扣除
   │    is_included_in_subscription = true
   │    cost_usd = 0
   ├─ 创建计费记录
   │  INSERT INTO billing_records ...
   └─ 发布 billing.calculated 事件
   
4. 发布 billing.calculated 事件
   NATS Subject: billing.calculated
   Event Data: {
     "user_id": "usr_123",
     "billing_record_id": "bill_456",
     "usage_event_id": "evt_789",
     "product_id": "gpt-4",
     "actual_usage": 300,
     "unit_type": "token",
     "token_equivalent": 300,
     "cost_usd": 0,
     "is_free_tier": false,
     "is_included_in_subscription": true
   }
   
5. wallet_service 监听并处理
   ├─ 检查计费类型
   │  if is_included_in_subscription:
   │    更新订阅使用量统计
   │    不扣除钱包余额
   │  else if is_free_tier:
   │    更新免费额度使用量
   │  else:
   │    需要扣除 token
   │    token_to_deduct = token_equivalent = 300
   ├─ 获取用户钱包
   │  SELECT * FROM wallets WHERE user_id = 'usr_123'
   │  balance_before = 10000 tokens
   ├─ 扣除 token
   │  balance_after = 10000 - 300 = 9700
   │  UPDATE wallets SET balance = 9700
   ├─ 创建交易记录
   │  INSERT INTO transactions ...
   └─ 发布扣费事件
   
6. 发布 wallet.tokens.deducted 事件
   NATS Subject: wallet.tokens.deducted
   Event Data: {
     "user_id": "usr_123",
     "billing_record_id": "bill_456",
     "transaction_id": "txn_111",
     "tokens_deducted": 300,
     "balance_before": 10000,
     "balance_after": 9700,
     "monthly_quota": 100000,
     "monthly_used": 25300,
     "percentage_used": 25.3
   }
```

### 流程 2: 余额不足处理

```
用户调用 API (余额: 100 tokens)
    ↓
1-3. [同上，计算出需要 500 tokens]
    ↓
4. wallet_service 检查余额
   ├─ balance_available = 100 tokens
   ├─ tokens_required = 500 tokens
   ├─ tokens_deficit = 400 tokens
   └─ 余额不足！
   
5. 发布 wallet.tokens.insufficient 事件
   NATS Subject: wallet.tokens.insufficient
   Event Data: {
     "user_id": "usr_123",
     "billing_record_id": "bill_456",
     "tokens_required": 500,
     "tokens_available": 100,
     "tokens_deficit": 400,
     "suggested_action": "upgrade_plan"
   }
   
6. notification_service 监听并通知用户
   ├─ 发送邮件: "您的余额不足，请充值或升级套餐"
   └─ 推送通知到客户端
   
7. billing_service 监听并标记失败
   ├─ UPDATE billing_records 
   │  SET status = 'insufficient_balance'
   └─ 可选：回滚 isA_Model 的调用（取决于业务规则）
```

### 流程 3: MCP 工具调用计费

```
用户调用 MCP 工具 (web_search)
    ↓
1. isA_MCP 执行工具
   ├─ 调用 Google Search API
   ├─ 可能调用 LLM 处理结果
   └─ 发布事件
   
2. 发布 usage.recorded 事件
   NATS Subject: usage.recorded.mcp-tool-web-search
   Event Data: {
     "user_id": "usr_123",
     "product_id": "mcp-tool-web-search",
     "usage_amount": 1,
     "unit_type": "request",
     "usage_details": {
       "tool_name": "web_search",
       "query": "latest AI news",
       "model_cost_usd": 0.0015,  # 如果调用了 LLM
       "model_tokens": 500,
       "model_product": "gpt-4"
     }
   }
   
3. billing_service 处理
   ├─ 获取工具定价: $0.01/request
   ├─ 计算 LLM 成本: $0.0015
   ├─ 总成本: $0.0115
   ├─ Token 等价值: $0.0115 / $0.00003 ≈ 383 tokens
   └─ 发布 billing.calculated
   
4-6. [同 AI 模型流程]
```

### 流程 4: 存储空间使用计费

```
用户上传 100MB 文件
    ↓
1. storage_service 处理上传
   ├─ 上传到 MinIO
   ├─ 创建文件记录
   └─ 发布事件
   
2. 发布 usage.recorded 事件
   NATS Subject: usage.recorded.storage-minio
   Event Data: {
     "user_id": "usr_123",
     "product_id": "storage-minio",
     "usage_amount": 104857600,  # 100MB in bytes
     "unit_type": "byte",
     "usage_details": {
       "file_id": "file_789",
       "file_size": 104857600,
       "storage_class": "STANDARD",
       "operation": "upload"
     }
   }
   
3. billing_service 处理
   ├─ 获取存储定价: $0.02/GB/month
   ├─ 转换: 100MB = 0.1GB
   ├─ 按小时计费: $0.02 / 30 / 24 ≈ $0.0000278/hour
   ├─ Token 等价值: 约 0.93 tokens/hour
   └─ 每小时扣费一次
```

## 💰 定价策略

### Token 转换率

```
基准: 1 token = $0.00003 (基于 GPT-4 定价)

所有计费最终转换为 token 等价值，便于统一钱包扣费。
```

### 产品定价

| 产品 | 单价 | 单位 | Token 等价值 |
|------|------|------|--------------|
| GPT-4 | $0.03 / 1K | token | 1:1 |
| GPT-3.5 | $0.001 / 1K | token | 1:1 |
| DALL-E 3 | $0.04 | image | 1333 tokens/image |
| Whisper | $0.006 / min | minute | 200 tokens/min |
| MCP Web Search | $0.01 | request | 333 tokens/request |
| MinIO Storage | $0.02 / GB/month | byte | ~0.93 tokens/GB/hour |
| Qdrant Storage | $0.05 / GB/month | byte | ~2.3 tokens/GB/hour |

### 订阅计划

| 计划 | 月费 | 包含 Token | 折扣 |
|------|------|-----------|------|
| Free | $0 | 10,000 | - |
| Starter | $20 | 100,000 | 33% off |
| Pro | $100 | 1,000,000 | 67% off |
| Enterprise | 定制 | 定制 | 定制 |

### 计费优先级

```
1. 免费套餐额度 (Free Tier)
   ↓ (用完后)
2. 订阅包含额度 (Subscription Included)
   ↓ (用完后)
3. 钱包余额扣费 (Pay-as-you-go)
   ↓ (余额不足)
4. 拒绝服务并通知用户
```

## 📊 数据模型

### billing_records 表

```sql
CREATE TABLE billing_records (
    billing_record_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    organization_id VARCHAR(64),
    
    -- 产品信息
    product_id VARCHAR(128) NOT NULL,
    product_category VARCHAR(64),
    
    -- 使用量
    usage_amount DECIMAL(20, 6) NOT NULL,
    unit_type VARCHAR(32) NOT NULL,  -- token, image, minute, request, byte
    
    -- 成本计算
    unit_price DECIMAL(10, 6),
    cost_usd DECIMAL(10, 6),
    token_equivalent DECIMAL(20, 2),
    
    -- 计费分类
    is_free_tier BOOLEAN DEFAULT false,
    is_included_in_subscription BOOLEAN DEFAULT false,
    subscription_id VARCHAR(64),
    
    -- 状态
    status VARCHAR(32) DEFAULT 'pending',  -- pending, completed, failed, insufficient_balance
    
    -- 元数据
    usage_details JSONB,
    usage_event_id VARCHAR(64),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_product_created (product_id, created_at DESC),
    INDEX idx_status (status)
);
```

### wallet transactions 表

```sql
CREATE TABLE transactions (
    transaction_id VARCHAR(64) PRIMARY KEY,
    wallet_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    
    -- 交易类型
    transaction_type VARCHAR(32) NOT NULL,  -- debit, credit, refund
    
    -- 金额
    amount DECIMAL(20, 2) NOT NULL,
    balance_before DECIMAL(20, 2) NOT NULL,
    balance_after DECIMAL(20, 2) NOT NULL,
    
    -- 关联
    billing_record_id VARCHAR(64),
    reference_id VARCHAR(64),
    
    -- 元数据
    description TEXT,
    metadata JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_wallet_created (wallet_id, created_at DESC),
    INDEX idx_user_created (user_id, created_at DESC)
);
```

## 🔍 事件流追踪

### 追踪 ID 链条

```
request_id (用户请求)
    ↓
usage_event_id (使用记录)
    ↓
billing_record_id (计费记录)
    ↓
transaction_id (钱包交易)
```

### 日志关联查询

```sql
-- 查询完整计费链路
SELECT 
    br.billing_record_id,
    br.usage_event_id,
    br.user_id,
    br.product_id,
    br.usage_amount,
    br.cost_usd,
    br.token_equivalent,
    br.status,
    t.transaction_id,
    t.balance_before,
    t.balance_after
FROM billing_records br
LEFT JOIN transactions t ON t.billing_record_id = br.billing_record_id
WHERE br.user_id = 'usr_123'
ORDER BY br.created_at DESC;
```

## 🧪 测试要点

### 集成测试场景

1. **基础计费流程**
   - ✅ 发布 usage.recorded → billing.calculated → tokens.deducted
   - ✅ 验证数据库记录
   - ✅ 验证余额变化

2. **免费套餐测试**
   - ✅ 使用在免费额度内
   - ✅ 超出免费额度后开始扣费

3. **订阅包含测试**
   - ✅ 使用订阅包含额度
   - ✅ 超出订阅额度后扣费

4. **余额不足测试**
   - ✅ 余额不足事件发布
   - ✅ 通知发送
   - ✅ 计费记录标记为失败

5. **多产品计费**
   - ✅ AI 模型 + MCP 工具 + 存储
   - ✅ 不同单位转换为 token

6. **并发测试**
   - ✅ 多个请求同时扣费
   - ✅ 余额计算正确

## 📈 监控指标

### 关键指标

```
- 计费事件处理延迟 (P50, P95, P99)
- 扣费成功率
- 余额不足次数
- 每日总收入
- 按产品分组的使用量
- 订阅转化率
```

### 告警规则

```
1. 计费事件处理失败率 > 1% → 告警
2. 扣费延迟 > 5s → 告警
3. 余额不足率 > 10% → 通知运营
4. 单用户异常高消费 (>日均 10x) → 风控告警
```

## 🔐 安全考虑

### 防止重复计费

```python
# 使用 usage_event_id 作为幂等键
SELECT * FROM billing_records 
WHERE usage_event_id = 'evt_789';

IF EXISTS:
    return  # 已处理，跳过
```

### 并发控制

```python
# 钱包扣费使用乐观锁
UPDATE wallets 
SET balance = balance - 300,
    version = version + 1
WHERE wallet_id = 'wal_123'
  AND version = 5  -- 当前版本
  AND balance >= 300;  -- 确保余额充足

IF affected_rows == 0:
    raise InsufficientBalanceError()
```

## 📚 相关文档

- [事件驱动架构](./event_driven_architecture.md)
- [产品定价策略](./product_pricing.md)
- [钱包系统设计](./wallet_system.md)
- [订阅管理](./subscription_management.md)

---

最后更新: 2025-01-09
版本: 1.0
