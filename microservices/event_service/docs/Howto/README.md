# Event Service - 统一事件管理服务

## 概述

Event Service 是 isA_Cloud 微服务架构中的核心事件处理组件，实现了统一的事件驱动架构，支持：

- 🎯 **前端事件采集** - 用户行为、业务操作、系统事件
- 🔄 **服务间通信** - 微服务之间的异步消息传递
- 📊 **事件存储查询** - 持久化事件数据和分析查询
- 🚀 **高性能处理** - NATS JetStream 支持的实时事件流

## 架构设计

### 核心架构

```
前端事件 ↘
业务事件  → NATS JetStream (事件源) → Event Service (持久化) → 查询API
系统事件 ↗                        ↓
                                其他微服务订阅
```

### 事件分类

- `events.frontend.user_interaction.*` - 前端用户交互事件
- `events.frontend.business_action.*` - 前端业务操作事件  
- `events.frontend.system_event.*` - 前端系统事件
- `events.backend.service.*` - 后端服务间通信事件

## 服务启动

### 环境要求

- Python 3.11+
- NATS Server with JetStream
- PostgreSQL (Supabase)

### 启动命令

```bash
# 从项目根目录启动
python -m microservices.event_service.main
```

### 环境变量

```bash
# NATS 配置
NATS_URL=nats://localhost:4222
NATS_USERNAME=isa_user_service
NATS_PASSWORD=service123

# 数据库配置
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
DB_SCHEMA=dev

# 服务配置
EVENT_SERVICE_HOST=0.0.0.0
EVENT_SERVICE_PORT=8230
```

## API 使用指南

### 1. 健康检查

#### 服务健康检查
```bash
curl http://localhost:8230/health
```

**响应示例：**
```json
{
  "status": "healthy",
  "service": "event-service",
  "version": "1.0.0",
  "timestamp": "2025-09-28T04:11:59.929021"
}
```

#### 前端采集健康检查
```bash
curl http://localhost:8230/api/frontend/health
```

**响应示例：**
```json
{
  "status": "healthy",
  "service": "frontend-event-collection",
  "nats_connected": true,
  "timestamp": "2025-09-28T04:11:59.929021"
}
```

### 2. 前端事件采集

#### 单个事件采集

**端点：** `POST /api/frontend/events`

```bash
curl -X POST http://localhost:8230/api/frontend/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "page_view",
    "category": "user_interaction",
    "page_url": "https://example.com/dashboard",
    "user_id": "user123",
    "session_id": "session456",
    "data": {
      "page_title": "Dashboard",
      "load_time": 1.5,
      "referrer": "https://google.com"
    },
    "metadata": {
      "browser": "Chrome",
      "version": "120.0"
    }
  }'
```

**响应示例：**
```json
{
  "status": "accepted",
  "event_id": "0fa7e146-c28f-47ff-a86b-abd77ebeb5e7",
  "message": "Event published to stream"
}
```

#### 批量事件采集

**端点：** `POST /api/frontend/events/batch`

```bash
curl -X POST http://localhost:8230/api/frontend/events/batch \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type": "button_click",
        "category": "user_interaction",
        "page_url": "https://example.com/dashboard",
        "user_id": "user123",
        "session_id": "session456",
        "data": {"button_id": "save_btn", "action": "save_profile"},
        "metadata": {"element_text": "Save Changes"}
      },
      {
        "event_type": "form_submit",
        "category": "business_action",
        "page_url": "https://example.com/profile",
        "user_id": "user123",
        "session_id": "session456",
        "data": {"form_name": "user_profile", "fields_count": 5},
        "metadata": {"validation_passed": "true"}
      }
    ],
    "client_info": {
      "browser": "Chrome",
      "version": "120.0",
      "device": "desktop",
      "screen_resolution": "1920x1080"
    }
  }'
```

**响应示例：**
```json
{
  "status": "accepted",
  "processed_count": 2,
  "event_ids": ["92d2f70e-9d0b-4f09-8fc0-3273f158a8bf", "8eae4579-d77a-494d-9661-739bbd0b60d3"],
  "message": "Batch of 2 events published to stream"
}
```

### 3. 后端事件创建

#### 服务间事件

**端点：** `POST /api/events/create`

```bash
curl -X POST http://localhost:8230/api/events/create \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user_registered",
    "event_source": "backend",
    "event_category": "user_action",
    "user_id": "user123",
    "data": {
      "email": "user@example.com",
      "registration_method": "email"
    }
  }'
```

**响应示例：**
```json
{
  "event_id": "f6d8d85b-cc7c-4771-b6fa-5bc29227cb17",
  "event_type": "user_registered",
  "event_source": "backend",
  "event_category": "user_action",
  "user_id": "user123",
  "data": {"email": "user@example.com", "registration_method": "email"},
  "status": "pending",
  "timestamp": "2025-09-28T03:55:03.316846",
  "created_at": "2025-09-28T03:55:03.316917"
}
```

#### 批量后端事件

**端点：** `POST /api/events/batch`

**注意：** 请求体应该是事件数组，不是对象包裹的数组

```bash
curl -X POST http://localhost:8230/api/events/batch \
  -H "Content-Type: application/json" \
  -d '[
    {
      "event_type": "user.logout",
      "source": "web",
      "category": "user",
      "user_id": "user123",
      "data": {"reason": "manual"}
    },
    {
      "event_type": "product.view",
      "source": "web",
      "category": "product",
      "user_id": "user123",
      "data": {"product_id": "prod_456"}
    }
  ]'
```

**响应示例：**
```json
[
  {
    "event_id": "e2153986-2588-470c-b73c-11ae96514b8b",
    "event_type": "user.logout",
    "event_source": "backend",
    "event_category": "user_action",
    "user_id": "user123",
    "data": {"reason": "manual"},
    "status": "pending",
    "timestamp": "2025-10-01T02:34:11.167002",
    "created_at": "2025-10-01T02:34:11.167089"
  },
  {
    "event_id": "8398a539-4a2e-4a5e-9867-22f49f92ea2f",
    "event_type": "product.view",
    "event_source": "backend",
    "event_category": "user_action",
    "user_id": "user123",
    "data": {"product_id": "prod_456"},
    "status": "pending",
    "timestamp": "2025-10-01T02:34:11.189752",
    "created_at": "2025-10-01T02:34:11.189777"
  }
]
```

## 事件模型

### 前端事件字段

```python
{
  "event_type": str,        # 事件类型：page_view, button_click, form_submit 等
  "category": str,          # 事件分类：user_interaction, business_action, system_event
  "page_url": str,          # 页面URL（可选）
  "user_id": str,           # 用户ID（可选）
  "session_id": str,        # 会话ID（可选）
  "data": dict,             # 事件数据
  "metadata": dict          # 元数据
}
```

### 自动添加的字段

服务会自动添加以下字段：

```python
{
  "event_id": str,          # UUID 事件ID
  "event_source": "frontend", # 事件源
  "timestamp": str,         # ISO格式时间戳
  "client_info": {          # 客户端信息
    "ip": str,              # 客户端IP
    "user_agent": str,      # User-Agent
    "referer": str          # Referer
  }
}
```

## 常见事件类型

### 用户交互事件 (user_interaction)

- `page_view` - 页面浏览
- `button_click` - 按钮点击
- `link_click` - 链接点击
- `scroll` - 页面滚动
- `focus` - 元素聚焦
- `blur` - 元素失焦

### 业务操作事件 (business_action)

- `form_submit` - 表单提交
- `purchase` - 购买操作
- `registration` - 用户注册
- `login` - 用户登录
- `logout` - 用户登出
- `subscription` - 订阅操作

### 系统事件 (system_event)

- `api_error` - API错误
- `performance_issue` - 性能问题
- `network_error` - 网络错误
- `js_error` - JavaScript错误
- `timeout` - 超时事件

## 最佳实践

### 1. 事件命名规范

- 使用小写字母和下划线
- 动词 + 名词形式：`button_click`, `form_submit`
- 保持一致性和描述性

### 2. 数据结构设计

```python
# 好的例子
{
  "event_type": "product_purchased",
  "category": "business_action",
  "data": {
    "product_id": "prod_123",
    "quantity": 2,
    "price": 99.99,
    "currency": "USD"
  }
}

# 避免的例子
{
  "event_type": "click",  # 太泛泛
  "data": "some string"   # 非结构化数据
}
```

### 3. 批量处理优化

- 前端缓存事件，定期批量发送
- 建议批量大小：10-50个事件
- 网络错误时本地存储重试

### 4. 错误处理

```javascript
// 前端示例
async function trackEvent(event) {
  try {
    const response = await fetch('/api/frontend/events', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(event)
    });
    
    if (!response.ok) {
      // 存储到本地，稍后重试
      localStorage.setItem('pending_events', JSON.stringify([event]));
    }
  } catch (error) {
    console.warn('Event tracking failed:', error);
    // 不应影响用户体验
  }
}
```

## 监控和运维

### 关键指标

- **事件处理速度** - 每秒处理的事件数
- **NATS连接状态** - 连接健康度
- **错误率** - 失败事件百分比
- **延迟** - 事件处理延迟

### 日志查看

```bash
# 查看服务日志
tail -f /var/log/event-service.log

# 查看错误日志
grep ERROR /var/log/event-service.log
```

### 故障排查

1. **NATS连接问题**
   - 检查NATS服务器状态
   - 验证认证信息
   - 检查网络连通性

2. **数据库连接问题**
   - 验证DATABASE_URL
   - 检查数据库权限
   - 确认Schema存在

3. **性能问题**
   - 监控事件处理队列
   - 检查批量大小设置
   - 优化数据库查询

## 开发指南

### 添加新的事件类型

1. 在前端定义事件结构
2. 确定合适的category
3. 添加到文档中
4. 测试端到端流程

### 扩展API功能

参考现有代码结构：

```python
@app.post("/api/custom/endpoint")
async def custom_handler(
    request: CustomRequest,
    service: EventService = Depends(get_event_service)
):
    # 实现自定义逻辑
    pass
```

## 测试结果

### ✅ 功能验证通过 (2025-10-01)

#### 服务健康检查
- ✅ `GET /health` - 服务健康状态正常
- ✅ `GET /api/frontend/health` - NATS连接状态: `nats_connected: true`

#### 后端事件功能
- ✅ `POST /api/events/create` - 单个事件创建成功
  - 测试事件ID: `a4abf5f1-193a-43ab-986b-e00824f9d086`
  - 状态: `pending`

- ✅ `POST /api/events/batch` - 批量事件创建成功
  - 格式要求: 请求体为数组 `[...]`
  - 测试结果: 成功创建2个事件

#### 前端事件功能
- ✅ `POST /api/frontend/events` - 单个前端事件采集成功
  - 测试事件ID: `5833fd88-1285-4561-b16d-e8651a8d4086`
  - 状态: `"Event published to stream"`

- ✅ `POST /api/frontend/events/batch` - 批量前端事件采集成功
  - 测试结果: 成功处理2个事件
  - 事件IDs: `f35862ee-bbff-4c82-91f1-57d02381cbbf`, `65d4c467-4e23-4a12-b41f-ea73d11034ef`

### 依赖要求

**前端事件采集功能需要 NATS 连接**:
- NATS Server 必须运行在 `localhost:4222`
- 如果 NATS 未连接，前端事件端点将返回: `"Event stream not available"`
- 后端事件功能不依赖 NATS，可独立工作

### 服务管理命令

```bash
# 重启服务（普通模式）
./scripts/start_all_services.sh restart event_service

# 重启服务（开发模式 - 自动重载）
./scripts/start_all_services.sh dev event_service

# 查看服务日志
./scripts/start_all_services.sh logs event_service

# 查看服务状态
./scripts/start_all_services.sh status
```

## 相关文档

- [NATS JetStream 文档](https://docs.nats.io/jetstream)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [微服务架构指南](../../../docs/microservices.md)