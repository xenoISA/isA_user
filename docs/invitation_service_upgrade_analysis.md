# Invitation Service 架构升级分析

生成时间: 2025-11-13

## 📊 当前状态分析

### Invitation Service (invitation_service/)

**当前架构问题:**

⚠️ **Events 部分完成**:
- ✅ 已有 `events/` 文件夹
- ✅ 已有 `events/handlers.py` (事件订阅处理器)
- ❌ 缺少 `events/models.py` (事件数据模型)
- ❌ 缺少 `events/publishers.py` (事件发布函数)
- ❌ `events/__init__.py` 只导出 handlers，缺少 models 和 publishers

❌ **Clients 错误位置**:
- ❌ `client.py` 在根目录 (应该在 `clients/` 文件夹)
- ❌ 没有 `clients/` 文件夹结构

**Invitation Service 特点**:
- 🎯 **发布者 + 订阅者**: 既发布事件，也订阅事件
- 📝 **发布 4 个事件**: invitation.sent, expired, accepted, cancelled
- 🔍 **订阅 2 个事件**: organization.deleted, user.deleted
- 📊 **提供 HTTP API**: 供其他服务调用邀请功能

**事件发布位置** (invitation_service.py):
- Line 111-127: 发布 `invitation.sent` 事件
- Line 164-178: 发布 `invitation.expired` 事件
- Line 258-274: 发布 `invitation.accepted` 事件
- Line 341-355: 发布 `invitation.cancelled` 事件

**事件订阅位置** (events/handlers.py):
- Line 38-66: `handle_organization_deleted()` - 处理组织删除
- Line 68-97: `handle_user_deleted()` - 处理用户删除

**总计: 4个事件发布需要重构**

---

## 🎯 升级计划

### Phase 1: 完善 Events 结构

**1. events/models.py - 4个事件模型**

基于当前发布的事件:
- `InvitationSentEvent` - 邀请已发送
- `InvitationExpiredEvent` - 邀请已过期
- `InvitationAcceptedEvent` - 邀请已接受
- `InvitationCancelledEvent` - 邀请已取消

**2. events/publishers.py - 4个发布函数**

```python
async def publish_invitation_sent(...)
async def publish_invitation_expired(...)
async def publish_invitation_accepted(...)
async def publish_invitation_cancelled(...)
```

**3. 更新 events/__init__.py**

导出所有事件模型、发布函数和处理器

**4. 保留 events/handlers.py**

已有的事件订阅处理器保持不变

### Phase 2: 创建 Clients 结构

**1. 移动 client.py → clients/invitation_client.py**

供其他服务调用的客户端

**2. 创建 clients/__init__.py**

导出客户端

### Phase 3: 重构 invitation_service.py

**修改点**:

1. **Import 更改** (Line 22):
   - 删除: `from core.nats_client import Event, EventType, ServiceSource`
   - 添加: `from .events.publishers import (...)`

2. **替换事件发布** (4处):
   - Line 111-127 → `await publish_invitation_sent(...)`
   - Line 164-178 → `await publish_invitation_expired(...)`
   - Line 258-274 → `await publish_invitation_accepted(...)`
   - Line 341-355 → `await publish_invitation_cancelled(...)`

### Phase 4: 更新 main.py

**修改点**:

1. **保持现有逻辑**: main.py 已正确注册事件订阅
2. **无需修改**: 事件订阅逻辑保持不变

---

## 📋 详细升级步骤

### Step 1: 创建 events/models.py

定义4个事件模型

### Step 2: 创建 events/publishers.py

创建4个发布函数

### Step 3: 更新 events/__init__.py

导出所有组件（models, publishers, handlers）

### Step 4: 创建 clients/ 文件夹并移动文件

```bash
mkdir -p microservices/invitation_service/clients
mv microservices/invitation_service/client.py \
   microservices/invitation_service/clients/invitation_client.py
```

### Step 5: 创建 clients/__init__.py

导出客户端

### Step 6: 重构 invitation_service.py

- 更新 imports
- 替换 4 处事件发布

### Step 7: 语法检查

验证所有文件语法正确

---

## 🎯 升级后的架构对比

### Before:
```
invitation_service/
├── events/
│   ├── handlers.py             ✅ 事件订阅处理器
│   └── __init__.py             ⚠️  只导出 handlers
├── invitation_service.py       ❌ 包含事件发布逻辑 (4 处)
├── client.py                   ❌ 在根目录
└── main.py                     ✅ 注册事件订阅
```

### After:
```
invitation_service/
├── events/
│   ├── models.py               ✅ 4 event models
│   ├── publishers.py           ✅ 4 publishers
│   ├── handlers.py             ✅ 事件订阅处理器 (保持不变)
│   └── __init__.py             ✅ 导出 models + publishers + handlers
├── clients/
│   ├── invitation_client.py    ✅ 供其他服务调用 (moved from root)
│   └── __init__.py             ✅ 导出 clients
├── invitation_service.py       ✅ 使用 publishers
└── main.py                     ✅ 保持不变
```

---

## ⚠️ 注意事项

### Invitation Service 架构特点

1. **双角色模式**:
   - **发布者**: 发布 4 个邀请相关事件
   - **订阅者**: 订阅 organization.deleted 和 user.deleted 事件

2. **4个事件发布**:
   - `invitation.sent` - 邀请发送成功
   - `invitation.expired` - 邀请过期
   - `invitation.accepted` - 用户接受邀请
   - `invitation.cancelled` - 邀请被取消

3. **2个事件订阅**:
   - `organization.deleted` - 取消该组织的所有待处理邀请
   - `user.deleted` - 取消该用户发送的所有邀请

### 升级重点

1. **events/models.py**:
   - 定义4个事件数据模型
   - 包含所有必要的字段

2. **events/publishers.py**:
   - 4个发布函数
   - 接收 event_bus 和相关参数
   - 构建并发布事件

3. **events/handlers.py**:
   - **保持不变**（已经符合标准）
   - 处理订阅的事件

4. **invitation_service.py 修改**:
   - 更新 imports
   - 替换 4 处事件发布调用
   - 保持业务逻辑不变

5. **clients/ 文件夹**:
   - 移动 client.py
   - 更新导入路径（在其他服务中）

---

## 📅 实施步骤

### Step 1: 创建 events/ 结构
1. 创建 events/models.py (4 events)
2. 创建 events/publishers.py (4 publishers)
3. 更新 events/__init__.py

### Step 2: 创建 clients/ 结构
1. 移动 client.py → clients/invitation_client.py
2. 创建 clients/__init__.py

### Step 3: 重构 invitation_service.py
1. 更新 imports
2. 替换 4 处事件发布

### Step 4: 测试验证
1. 语法检查所有文件
2. 验证事件发布功能
3. 验证事件订阅功能

---

## ✅ 完成标准

Invitation Service 满足 arch.md 标准:
- ✅ Events 集中管理 (models, publishers, handlers in events/)
- ✅ Clients 集中管理 (invitation_client in clients/)
- ✅ main.py 只负责初始化和注册
- ✅ 业务逻辑使用 publishers 发布事件
- ✅ 所有语法检查通过
- ✅ 事件发布和订阅功能正常工作

---

## 📝 与其他服务的区别

| 特性 | Memory Service | Audit Service | Compliance Service | Invitation Service |
|------|----------------|---------------|-------------------|-------------------|
| **Events Models** | ✅ (8个) | ❌ | ✅ (3个) | ✅ (4个) |
| **Events Publishers** | ✅ (8个) | ❌ | ✅ (3个) | ✅ (4个) |
| **Events Handlers** | ✅ (2个订阅) | ✅ (订阅所有) | ❌ | ✅ (2个订阅) |
| **Clients** | ❌ | ✅ (1个) | ✅ (2个) | ✅ (1个) |
| **角色** | 发布者+订阅者 | 纯订阅者 | 纯发布者 | 发布者+订阅者 |

---

## 🚀 开始升级

准备好执行升级步骤了吗？我会按照以下顺序进行：

1. ✅ 创建 events/models.py
2. ✅ 创建 events/publishers.py
3. ✅ 更新 events/__init__.py
4. ✅ 移动并创建 clients/ 结构
5. ✅ 重构 invitation_service.py
6. ✅ 语法检查
