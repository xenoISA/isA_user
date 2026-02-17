# Account Service 升级快速参考

## 新增文件结构

```
account_service/
├── events/                    # 🆕 事件驱动模块
│   ├── __init__.py
│   ├── models.py             # 5个事件数据模型
│   ├── publishers.py         # 5个事件发布函数
│   └── handlers.py           # 3个事件处理器
│
├── clients/                  # 🆕 服务客户端模块
│   ├── __init__.py
│   ├── organization_client.py
│   ├── billing_client.py
│   └── wallet_client.py
│
├── account_service.py        # ✏️ 已更新 - 使用 publishers
├── main.py                   # ✏️ 已更新 - 注册 handlers + clients
└── docs/
    ├── UPGRADE_ANALYSIS.md   # 🆕 升级分析文档
    ├── UPGRADE_SUMMARY.md    # 🆕 升级总结文档
    └── QUICK_REFERENCE.md    # 🆕 快速参考（本文件）
```

## 如何发布事件

### 方法 1：在 account_service.py 中（推荐）

```python
from .events.publishers import publish_user_created

# 在业务逻辑中
await publish_user_created(
    event_bus=self.event_bus,
    user_id="user_123",
    email="user@example.com",
    name="John Doe",
    subscription_plan="free"
)
```

### 可用的发布函数

```python
from .events.publishers import (
    publish_user_created,           # 用户创建
    publish_user_profile_updated,   # 资料更新
    publish_user_deleted,            # 用户删除
    publish_user_subscription_changed, # 订阅变更
    publish_user_status_changed,     # 状态变更
)
```

## 如何处理接收到的事件

### 在 events/handlers.py 中定义处理器

```python
async def handle_payment_completed(event_data: Dict[str, Any]):
    """处理支付完成事件"""
    user_id = event_data.get("user_id")
    subscription_plan = event_data.get("subscription_plan")
    
    # 实现业务逻辑
    logger.info(f"Payment completed for {user_id}, plan: {subscription_plan}")
```

### 在 main.py 中自动注册

```python
# 已自动完成，不需要手动操作
event_handlers = get_event_handlers()
for event_type, handler in event_handlers.items():
    await event_bus.subscribe(event_type, handler)
```

## 如何使用 Service Clients

### 在业务逻辑中使用

```python
# 在 account_service.py 中添加 client 参数
def __init__(self, event_bus=None, config=None, 
             organization_client=None, billing_client=None):
    self.organization_client = organization_client
    self.billing_client = billing_client

# 使用 client 进行同步调用
async def validate_user_organization(self, user_id: str, org_id: str):
    if self.organization_client:
        org_exists = await self.organization_client.validate_organization_exists(org_id)
        if not org_exists:
            raise AccountValidationError(f"Organization not found: {org_id}")
```

### 在 main.py 中传递 clients（可选改进）

```python
# 当前 clients 在 AccountMicroservice 中初始化
# 如果需要在 AccountService 中使用，可以这样传递：
self.account_service = AccountService(
    event_bus=event_bus, 
    config=config_manager,
    organization_client=self.organization_client,
    billing_client=self.billing_client,
    wallet_client=self.wallet_client
)
```

## 事件列表

### 发布的事件（Publish）

| 事件类型 | 触发时机 | 数据 |
|---------|---------|------|
| `user.created` | 新账户创建 | user_id, email, name, subscription_plan |
| `user.profile_updated` | 资料更新 | user_id, email, name, updated_fields |
| `user.deleted` | 账户删除 | user_id, email, reason |
| `user.subscription_changed` | 订阅变更 | user_id, email, old_plan, new_plan |
| `user.status_changed` | 状态变更 | user_id, is_active, reason |

### 订阅的事件（Subscribe）

| 事件类型 | 来源服务 | 处理器函数 |
|---------|---------|-----------|
| `payment.completed` | billing_service | `handle_payment_completed` |
| `organization.member_added` | organization_service | `handle_organization_member_added` |
| `wallet.created` | wallet_service | `handle_wallet_created` |

## Service Clients API

### OrganizationServiceClient

```python
from .clients import OrganizationServiceClient

client = OrganizationServiceClient()

# 获取组织详情
org = await client.get_organization(org_id)

# 验证组织存在
exists = await client.validate_organization_exists(org_id)

# 获取组织成员
members = await client.get_organization_members(org_id)
```

### BillingServiceClient

```python
from .clients import BillingServiceClient

client = BillingServiceClient()

# 获取订阅状态
subscription = await client.get_subscription_status(user_id)

# 检查支付状态
status = await client.check_payment_status(user_id)

# 获取账单历史
history = await client.get_billing_history(user_id, limit=10)
```

### WalletServiceClient

```python
from .clients import WalletServiceClient

client = WalletServiceClient()

# 获取钱包余额
balance = await client.get_wallet_balance(user_id)

# 获取钱包详情
wallet = await client.get_wallet_info(user_id)

# 检查钱包是否存在
exists = await client.check_wallet_exists(user_id)
```

## 代码示例

### 完整示例：创建账户并发布事件

```python
# account_service.py
async def ensure_account(self, request: AccountEnsureRequest):
    # 1. 验证请求
    self._validate_account_ensure_request(request)
    
    # 2. 创建账户（Repository 层）
    user = await self.account_repo.ensure_account_exists(...)
    
    # 3. 发布事件（Event 层）
    if was_created and self.event_bus:
        await publish_user_created(
            event_bus=self.event_bus,
            user_id=request.user_id,
            email=request.email,
            name=request.name,
            subscription_plan=request.subscription_plan
        )
    
    return account_response, was_created
```

### 完整示例：处理订阅事件

```python
# events/handlers.py
async def handle_payment_completed(event_data: Dict[str, Any]):
    user_id = event_data.get("user_id")
    subscription_plan = event_data.get("subscription_plan")
    
    # TODO: 更新用户订阅状态
    # 需要访问 AccountRepository
    logger.info(f"Processing payment for {user_id}: {subscription_plan}")
```

## 常见问题

### Q: 如何在 handlers.py 中访问 AccountRepository？

A: 有两种方式：
1. 在 main.py 中创建 handler 时注入 repository
2. 在 handler 中直接创建 repository 实例（简单但不推荐）

推荐方式：
```python
# main.py
def create_event_handlers(account_repo):
    async def handle_payment_completed(event_data):
        # 可以访问 account_repo
        await account_repo.update_subscription(...)
    
    return {
        "payment.completed": handle_payment_completed
    }
```

### Q: Service Client 调用失败怎么办？

A: Clients 已内置错误处理，返回 None 或空列表：
```python
org = await client.get_organization(org_id)
if org is None:
    # 组织不存在或调用失败
    logger.warning(f"Could not get organization {org_id}")
```

### Q: 事件发布失败会影响业务流程吗？

A: 不会。所有事件发布都在 try-except 中，失败只会记录日志：
```python
try:
    await publish_user_created(...)
except Exception as e:
    logger.error(f"Failed to publish event: {e}")
    # 业务流程继续执行
```

## 测试命令

### 启动服务
```bash
cd microservices/account_service
python -m uvicorn main:app --reload --port 8001
```

### 测试创建账户（触发事件）
```bash
curl -X POST http://localhost:8001/api/v1/accounts/ensure \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "email": "test@example.com",
    "name": "Test User",
    "subscription_plan": "free"
  }'
```

### 查看日志
```bash
# 查看事件发布日志
grep "Published user.created" logs/account_service.log

# 查看事件订阅日志
grep "Subscribed to event" logs/account_service.log
```

## 下一步

1. ✅ 实现 handlers.py 中的业务逻辑
2. ✅ 在需要的地方集成 service clients
3. ✅ 添加集成测试
4. ✅ 监控事件发布和订阅的健康状态

## 参考文档

- `UPGRADE_ANALYSIS.md` - 详细的升级分析
- `UPGRADE_SUMMARY.md` - 完整的升级总结
- `arch.md` - 架构标准文档（项目根目录）
- `auth_service/` - 参考实现

---

**升级完成时间**: 2025-11-14  
**架构版本**: Event-Driven v2.0  
**遵循标准**: arch.md
