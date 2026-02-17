# Account Service 升级分析

## 当前状态
- ✅ 有基础的 event bus 集成（在 account_service.py 中）
- ❌ 缺少标准的 events/ 文件夹结构
- ❌ 缺少 clients/ 文件夹用于同步调用
- ❌ 事件发布逻辑散落在业务代码中

## 异步操作 (Events - NATS)

### 1. 发布事件 (Publishers)
Account Service 需要发布以下事件：

#### USER_CREATED
- **触发时机**: 新账户创建成功后
- **数据**: user_id, email, name, subscription_plan, timestamp
- **订阅者**: 
  - billing_service (创建账单记录)
  - wallet_service (创建钱包)
  - notification_service (发送欢迎邮件)
  - memory_service (初始化用户记忆)

#### USER_PROFILE_UPDATED
- **触发时机**: 用户资料更新后
- **数据**: user_id, updated_fields, email, name, timestamp
- **订阅者**: 
  - notification_service (通知用户)
  - audit_service (记录审计日志)

#### USER_DELETED
- **触发时机**: 账户删除（软删除）后
- **数据**: user_id, email, reason, timestamp
- **订阅者**: 
  - wallet_service (冻结钱包)
  - billing_service (停止计费)
  - notification_service (发送确认邮件)
  - memory_service (归档记忆)
  - device_service (解绑设备)

#### USER_SUBSCRIPTION_CHANGED
- **触发时机**: 订阅计划变更后
- **数据**: user_id, old_plan, new_plan, timestamp
- **订阅者**: 
  - billing_service (调整计费)
  - authorization_service (更新权限)
  - notification_service (发送通知)

### 2. 订阅事件 (Handlers)
Account Service 需要监听以下事件：

#### PAYMENT_COMPLETED (from billing_service)
- **处理逻辑**: 如果是订阅支付，更新用户订阅状态
- **数据**: user_id, payment_type, subscription_plan

#### ORGANIZATION_MEMBER_ADDED (from organization_service)
- **处理逻辑**: 记录用户加入组织的信息
- **数据**: organization_id, user_id, role

## 同步操作 (Clients - HTTP)

### 需要的 Service Clients

#### 1. OrganizationServiceClient
- **用途**: 验证组织存在、获取组织信息
- **方法**:
  - `get_organization(org_id)` - 获取组织详情
  - `validate_organization_exists(org_id)` - 验证组织是否存在

#### 2. BillingServiceClient
- **用途**: 查询用户账单状态、订阅信息
- **方法**:
  - `get_subscription_status(user_id)` - 获取订阅状态
  - `check_payment_status(user_id)` - 检查支付状态

#### 3. WalletServiceClient
- **用途**: 查询用户钱包余额（用于显示在账户信息中）
- **方法**:
  - `get_wallet_balance(user_id)` - 获取钱包余额

## 升级步骤

### Phase 1: 创建标准结构
1. ✅ 创建 `events/` 文件夹
   - models.py - 事件数据模型
   - publishers.py - 事件发布方法
   - handlers.py - 事件订阅处理器
   - __init__.py - 导出所有内容

2. ✅ 创建 `clients/` 文件夹
   - organization_client.py
   - billing_client.py
   - wallet_client.py
   - __init__.py

### Phase 2: 重构业务逻辑
1. 将 account_service.py 中的事件发布代码移到 publishers.py
2. 在 main.py 的 lifespan 中注册事件处理器
3. 在需要的地方使用 clients 进行同步调用

### Phase 3: 测试验证
1. 测试事件发布和订阅
2. 测试同步调用
3. 端到端集成测试

## 架构对比

### 升级前
```
account_service/
├── account_service.py  (业务逻辑 + 事件发布混在一起)
├── main.py             (路由定义)
└── models.py
```

### 升级后
```
account_service/
├── events/
│   ├── __init__.py
│   ├── models.py       (事件数据模型)
│   ├── publishers.py   (发布事件)
│   └── handlers.py     (处理订阅)
├── clients/
│   ├── __init__.py
│   ├── organization_client.py
│   ├── billing_client.py
│   └── wallet_client.py
├── account_service.py  (纯业务逻辑，调用 publishers)
├── main.py             (路由 + 注册 handlers)
└── models.py
```

## 参考实现
- ✅ auth_service - 完整的 events + clients 结构
- ✅ wallet_service - 标准的事件驱动架构
- ✅ arch.md - 架构标准文档
