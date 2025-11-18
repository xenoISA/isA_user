# OTA & Telemetry Services 架构升级分析

生成时间: 2025-11-13

## 📊 当前状态分析

### OTA Service (ota_service/)

**当前架构问题:**

❌ **Events 不完整**:
- ✅ 有 `events/handlers.py` (订阅 device.deleted)
- ❌ 缺少 `events/models.py` (事件数据模型)
- ❌ 缺少 `events/publishers.py` (事件发布函数)
- ❌ 事件发布散落在 `ota_service.py` 中 (直接创建 Event 对象)

❌ **Clients 缺失**:
- ❌ 完全没有 `clients/` 文件夹
- ❌ 在 `ota_service.py` 中直接导入和使用其他服务客户端:
  - Line 79: `async with StorageServiceClient()` (直接导入使用)
  - Line 372: `async with DeviceServiceClient()` (直接导入使用)
- ❌ 缺少 notification_client 实现 (虽然初始化了但未使用)

❌ **事件发布位置**:
- Line 158-177: `ota_service.py` - firmware.uploaded 事件
- Line 286-306: `ota_service.py` - campaign.created 事件
- Line 333-350: `ota_service.py` - campaign.started 事件
- Line 523-540: `ota_service.py` - update.cancelled 事件
- Line 573-590: `ota_service.py` - rollback.initiated 事件

**当前 Event Handlers (handlers.py):**
- ✅ handle_device_deleted() - 处理设备删除事件

---

### Telemetry Service (telemetry_service/)

**当前架构问题:**

❌ **Events 不完整**:
- ✅ 有 `events/handlers.py` (订阅 device.deleted)
- ❌ 缺少 `events/models.py` (事件数据模型)
- ❌ 缺少 `events/publishers.py` (事件发布函数)
- ❌ 事件发布散落在 `telemetry_service.py` 中 (直接创建 Event 对象)

❌ **Clients 缺失**:
- ❌ 完全没有 `clients/` 文件夹
- ✅ 目前不需要调用其他服务 (数据接收端)

❌ **事件发布位置**:
- Line 75-87: `telemetry_service.py` - telemetry.data.received 事件
- Line 145-162: `telemetry_service.py` - metric.defined 事件
- Line 230-249: `telemetry_service.py` - alert.rule.created 事件
- Line 711-730: `telemetry_service.py` - alert.triggered 事件 (from dict)
- Line 767-786: `telemetry_service.py` - alert.triggered 事件 (from object)

❌ **main.py 事件发布**:
- Line 824-841: `main.py` - alert.resolved 事件 ⚠️

**当前 Event Handlers (handlers.py):**
- ✅ handle_device_deleted() - 禁用已删除设备的警报规则

---

## 🎯 升级目标

按照 arch.md 标准，两个服务需要:

### 1️⃣ **Events 完整结构**

```
events/
├── __init__.py          # 导出所有 event 组件
├── models.py            # Pydantic event 数据模型
├── publishers.py        # 事件发布函数 (本服务发出)
└── handlers.py          # 事件处理器 (订阅其他服务) ✅ 已存在
```

### 2️⃣ **Clients 服务客户端**

```
clients/
├── __init__.py          # 导出所有 client
├── device_client.py     # 设备服务客户端
├── storage_client.py    # 存储服务客户端
└── notification_client.py  # 通知服务客户端
```

---

## 📋 详细升级计划

### **OTA Service 升级计划**

#### Phase 1: 创建 Events 结构

**1. events/models.py - 5个事件模型**

基于当前发布的事件:
- `FirmwareUploadedEvent` - 固件上传完成
- `CampaignCreatedEvent` - 更新活动创建
- `CampaignStartedEvent` - 更新活动启动
- `UpdateCancelledEvent` - 更新取消
- `RollbackInitiatedEvent` - 回滚启动

**2. events/publishers.py - 5个发布函数**

```python
async def publish_firmware_uploaded(...)
async def publish_campaign_created(...)
async def publish_campaign_started(...)
async def publish_update_cancelled(...)
async def publish_rollback_initiated(...)
```

**3. 更新 events/__init__.py**

导出所有事件模型和发布函数

#### Phase 2: 创建 Clients 结构

**1. clients/device_client.py**

方法:
- `get_device(device_id)` - 获取设备信息
- `get_device_firmware_version(device_id)` - 获取当前固件版本
- `check_firmware_compatibility(device_id, model, min_hw_version)` - 检查兼容性
- `health_check()` - 健康检查

**2. clients/storage_client.py**

方法:
- `upload_firmware(firmware_id, file_content, filename, user_id, metadata)` - 上传固件到存储
- `get_firmware_download_url(firmware_id)` - 获取下载链接
- `delete_firmware(firmware_id)` - 删除固件
- `health_check()` - 健康检查

**3. clients/notification_client.py**

方法:
- `send_campaign_notification(user_ids, campaign_data)` - 发送活动通知
- `send_update_notification(device_id, update_data)` - 发送更新通知
- `send_alert(user_ids, alert_data)` - 发送警报
- `health_check()` - 健康检查

**4. clients/__init__.py**

导出所有客户端

#### Phase 3: 重构 ota_service.py

**修改点:**

1. **Import 更改** (Line 18-40):
   - 删除: `from core.nats_client import Event, EventType, ServiceSource`
   - 添加: `from .events.publishers import (...)`
   - 添加: `from .clients import (...)`

2. **构造函数改造** (Line 33-43):
```python
def __init__(
    self,
    event_bus=None,
    config=None,
    device_client=None,
    storage_client=None,
    notification_client=None
):
    self.device_client = device_client
    self.storage_client = storage_client
    self.notification_client = notification_client
    self.event_bus = event_bus
    self.repository = OTARepository(config=config)
```

3. **替换事件发布** (5处):
   - Line 160-174 → `await publish_firmware_uploaded(...)`
   - Line 288-303 → `await publish_campaign_created(...)`
   - Line 335-347 → `await publish_campaign_started(...)`
   - Line 525-537 → `await publish_update_cancelled(...)`
   - Line 575-587 → `await publish_rollback_initiated(...)`

4. **替换客户端调用** (2处):
   - Line 79-100: 用 `self.storage_client.upload_firmware(...)`
   - Line 372-392: 用 `self.device_client.get_device(...)`

#### Phase 4: 重构 main.py

**修改点:**

1. **添加全局客户端变量** (Line 42后):
```python
device_client = None
storage_client = None
notification_client = None
```

2. **更新 OTAMicroservice.initialize()** (Line 48-51):
```python
async def initialize(
    self,
    event_bus=None,
    config=None,
    device_client=None,
    storage_client=None,
    notification_client=None
):
    self.event_bus = event_bus
    self.service = OTAService(
        event_bus=event_bus,
        config=config,
        device_client=device_client,
        storage_client=storage_client,
        notification_client=notification_client
    )
```

3. **lifespan 初始化客户端** (Line 81后):
```python
# Initialize service clients
try:
    from .clients import DeviceClient, StorageClient, NotificationClient

    device_client = DeviceClient(config=config_manager)
    storage_client = StorageClient(config=config_manager)
    notification_client = NotificationClient(config=config_manager)

    logger.info("✅ Service clients initialized")
except Exception as e:
    logger.warning(f"⚠️  Failed to initialize clients: {e}")

# Pass clients to microservice
await microservice.initialize(
    event_bus=event_bus,
    config=config_manager,
    device_client=device_client,
    storage_client=storage_client,
    notification_client=notification_client
)
```

4. **lifespan cleanup 添加客户端关闭** (Line 140后):
```python
# Close clients
if device_client:
    await device_client.close()
if storage_client:
    await storage_client.close()
if notification_client:
    await notification_client.close()
```

---

### **Telemetry Service 升级计划**

#### Phase 1: 创建 Events 结构

**1. events/models.py - 4个事件模型**

基于当前发布的事件:
- `TelemetryDataReceivedEvent` - 遥测数据接收
- `MetricDefinedEvent` - 指标定义创建
- `AlertRuleCreatedEvent` - 警报规则创建
- `AlertTriggeredEvent` - 警报触发
- `AlertResolvedEvent` - 警报解决

**2. events/publishers.py - 5个发布函数**

```python
async def publish_telemetry_data_received(...)
async def publish_metric_defined(...)
async def publish_alert_rule_created(...)
async def publish_alert_triggered(...)
async def publish_alert_resolved(...)
```

**3. 更新 events/__init__.py**

导出所有事件模型和发布函数

#### Phase 2: Clients (可选)

Telemetry Service 目前是**数据接收端**，不主动调用其他服务:
- ❌ 不需要 device_client (通过事件接收设备信息)
- ❌ 不需要 notification_client (通过事件发布警报)

**结论: 暂不创建 clients/ 文件夹**

如果未来需要主动调用其他服务,可以添加:
- `notification_client.py` - 发送警报通知
- `device_client.py` - 验证设备信息

#### Phase 3: 重构 telemetry_service.py

**修改点:**

1. **Import 更改** (Line 23):
   - 删除: `from core.nats_client import Event, EventType, ServiceSource`
   - 添加: `from .events.publishers import (...)`

2. **替换事件发布** (4处):
   - Line 75-87 → `await publish_telemetry_data_received(...)`
   - Line 147-160 → `await publish_metric_defined(...)`
   - Line 231-247 → `await publish_alert_rule_created(...)`
   - Line 712-729 → `await publish_alert_triggered(...)` (from dict)
   - Line 768-784 → `await publish_alert_triggered(...)` (from object)

#### Phase 4: 重构 main.py

**修改点:**

1. **移除 main.py 中的事件发布** (Line 824-841):
   - ⚠️ **CRITICAL**: `alert.resolved` 事件发布在 main.py 中
   - 需要移到 `telemetry_service.py` 或创建专门方法

**选项 A: 在 telemetry_service.py 添加方法**
```python
async def resolve_alert(self, alert_id: str, resolved_by: str, note: str) -> bool:
    # 更新警报状态
    success = await self.repository.update_alert(...)

    # 发布事件
    if success and self.event_bus:
        await publish_alert_resolved(...)

    return success
```

**选项 B: 保留在 main.py 但使用 publisher**
```python
# In main.py resolve_alert endpoint
from .events.publishers import publish_alert_resolved

success = await microservice.service.repository.update_alert(...)
if success and microservice.event_bus:
    await publish_alert_resolved(
        event_bus=microservice.event_bus,
        alert_id=alert_id,
        ...
    )
```

**推荐: 选项 A** - 将业务逻辑移到 service 层

---

## 📊 升级优先级

### High Priority (必须完成)

1. ✅ **OTA Service**:
   - events/models.py (5 events)
   - events/publishers.py (5 publishers)
   - clients/ 完整结构 (3 clients)
   - ota_service.py 重构
   - main.py 重构

2. ✅ **Telemetry Service**:
   - events/models.py (5 events)
   - events/publishers.py (5 publishers)
   - telemetry_service.py 重构
   - main.py 重构 (移动 alert.resolved 逻辑)

### Medium Priority (建议完成)

3. ⚠️ **Telemetry Service Clients** (如需要):
   - notification_client.py - 主动发送警报通知
   - device_client.py - 验证设备信息

---

## 🎯 升级后的架构对比

### OTA Service

**Before:**
```
ota_service/
├── events/
│   ├── handlers.py           ✅ (订阅 1 事件)
│   └── __init__.py
├── ota_service.py            ❌ 散落 5 处事件发布, 2 处直接客户端调用
└── main.py                   ✅ 注册订阅
```

**After:**
```
ota_service/
├── events/
│   ├── models.py             ✅ 5 event models
│   ├── publishers.py         ✅ 5 publishers
│   ├── handlers.py           ✅ 1 handler (device.deleted)
│   └── __init__.py           ✅ 导出 models + publishers
├── clients/
│   ├── device_client.py      ✅ DeviceClient
│   ├── storage_client.py     ✅ StorageClient
│   ├── notification_client.py ✅ NotificationClient
│   └── __init__.py           ✅ 导出 clients
├── ota_service.py            ✅ 使用 publishers + clients
└── main.py                   ✅ 初始化 clients, 注册handlers
```

### Telemetry Service

**Before:**
```
telemetry_service/
├── events/
│   ├── handlers.py           ✅ (订阅 1 事件)
│   └── __init__.py
├── telemetry_service.py      ❌ 散落 4 处事件发布
└── main.py                   ❌ 1 处事件发布 (alert.resolved)
```

**After:**
```
telemetry_service/
├── events/
│   ├── models.py             ✅ 5 event models
│   ├── publishers.py         ✅ 5 publishers
│   ├── handlers.py           ✅ 1 handler (device.deleted)
│   └── __init__.py           ✅ 导出 models + publishers
├── telemetry_service.py      ✅ 使用 publishers (包括 resolve_alert)
└── main.py                   ✅ 纯 API 端点
```

---

## ⚠️ 注意事项

### OTA Service

1. **StorageServiceClient / DeviceServiceClient**:
   - 当前直接在 `ota_service.py` 中 import
   - 需要确认这些客户端的完整路径
   - 可能需要从其他服务复制或创建新的客户端

2. **notification_client**:
   - 当前初始化但未实际使用
   - 需要设计完整的通知发送方法

3. **事件发布频率**:
   - firmware.uploaded, campaign.* 等事件可能触发频繁
   - 确保 publisher 函数性能优化

### Telemetry Service

1. **alert.resolved 逻辑移动**:
   - 当前在 main.py 的 endpoint 中
   - 需要移到 telemetry_service.py
   - 保持 API 端点简洁

2. **alert.triggered 重复代码**:
   - 有两个 _trigger_alert 方法 (from dict / from object)
   - 重构后统一使用 publisher 函数

3. **未来扩展**:
   - 如需主动通知功能,再添加 notification_client
   - 如需设备验证,再添加 device_client

---

## 📅 实施步骤

### Step 1: OTA Service
1. 创建 events/models.py (5 events)
2. 创建 events/publishers.py (5 publishers)
3. 更新 events/__init__.py
4. 创建 clients/ (3 clients)
5. 重构 ota_service.py
6. 重构 main.py
7. 语法检查

### Step 2: Telemetry Service
1. 创建 events/models.py (5 events)
2. 创建 events/publishers.py (5 publishers)
3. 更新 events/__init__.py
4. 重构 telemetry_service.py (添加 resolve_alert 方法)
5. 重构 main.py (使用 service.resolve_alert)
6. 语法检查

### Step 3: 测试验证
1. 启动服务检查初始化
2. 测试事件发布/订阅
3. 测试服务间调用
4. 验证日志输出

---

## ✅ 完成标准

两个服务都满足 arch.md 标准:
- ✅ Events 集中管理 (models, publishers, handlers)
- ✅ Clients 集中管理 (如需要)
- ✅ main.py 只负责初始化和注册
- ✅ 业务逻辑使用 publishers 发布事件
- ✅ 所有语法检查通过
