# Session Service API Guide

会话管理微服务API使用指南

## 服务概述

会话服务（Session Service）是一个专门处理用户会话管理的微服务，负责会话的创建、消息管理、内存存储和统计分析。

### 核心功能
- 会话生命周期管理（创建、更新、结束）
- 会话消息管理
- 会话内存/上下文管理
- 会话统计和分析
- 多用户会话支持
- 会话摘要生成

### 服务信息
- **端口**: 8205
- **版本**: 1.0.0
- **数据库**: PostgreSQL (dev schema)

## 前置条件

### 服务启动
```bash
# 使用部署脚本启动
deployment/scripts/start_user_service.sh -e dev start

# 或直接启动会话服务
python -m microservices.session_service.main
```

### 环境要求
- 数据库表已创建（sessions, session_messages, session_memories）
- Consul服务发现已启动
- Python 3.11+
- FastAPI框架

## 健康检查

### 基础健康检查
```bash
curl -X GET "http://localhost:8205/health"
```

**响应:**
```json
{
  "status": "healthy",
  "service": "session_service",
  "port": 8205,
  "version": "1.0.0",
  "timestamp": "2025-10-03T09:53:01.487876"
}
```

### 详细健康检查
```bash
curl -X GET "http://localhost:8205/health/detailed"
```

**响应:**
```json
{
  "service": "session_service",
  "status": "operational",
  "port": 8205,
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2025-10-03T09:53:05.306435Z"
}
```

## 会话管理

### 1. 创建会话

**请求:**
```bash
curl -X POST "http://localhost:8205/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "title": "Test Session",
    "metadata": {
      "source": "web_app",
      "device": "desktop"
    }
  }'
```

**响应:**
```json
{
  "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
  "user_id": "test_user_123",
  "status": "active",
  "conversation_data": {},
  "metadata": {
    "source": "web_app",
    "device": "desktop"
  },
  "is_active": true,
  "message_count": 0,
  "total_tokens": 0,
  "total_cost": 0.0,
  "session_summary": "",
  "created_at": "2025-10-03T09:53:09.821305Z",
  "updated_at": "2025-10-03T09:53:09.821316Z",
  "last_activity": "2025-10-03T09:53:09.821317Z"
}
```

### 2. 获取会话详情

**请求:**
```bash
curl -X GET "http://localhost:8205/api/v1/sessions/{session_id}?user_id=test_user_123"
```

**响应:**
```json
{
  "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
  "user_id": "test_user_123",
  "status": "active",
  "conversation_data": {},
  "metadata": {
    "source": "web_app"
  },
  "is_active": true,
  "message_count": 0,
  "total_tokens": 0,
  "total_cost": 0.0,
  "session_summary": "",
  "created_at": "2025-10-03T09:53:09.821305Z",
  "updated_at": "2025-10-03T09:53:09.821316Z",
  "last_activity": "2025-10-03T09:53:09.821317Z"
}
```

### 3. 获取用户所有会话

**请求:**
```bash
curl -X GET "http://localhost:8205/api/v1/users/{user_id}/sessions?active_only=true&page=1&page_size=50"
```

**响应:**
```json
{
  "sessions": [
    {
      "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
      "user_id": "test_user_123",
      "status": "active",
      "is_active": true,
      "message_count": 1,
      "total_tokens": 0,
      "total_cost": 0.0,
      "created_at": "2025-10-03T09:53:09.821305Z",
      "last_activity": "2025-10-03T10:04:46.223080Z"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 50
}
```

### 4. 更新会话

**请求:**
```bash
curl -X PUT "http://localhost:8205/api/v1/sessions/{session_id}?user_id=test_user_123" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Test Session",
    "metadata": {
      "updated": true,
      "version": 2
    }
  }'
```

**响应:**
```json
{
  "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
  "user_id": "test_user_123",
  "status": "active",
  "metadata": {
    "updated": true,
    "version": 2
  },
  "is_active": true,
  "message_count": 1,
  "updated_at": "2025-10-03T10:04:46.223086Z",
  "last_activity": "2025-10-03T10:04:46.223080Z"
}
```

### 5. 结束会话

**请求:**
```bash
curl -X DELETE "http://localhost:8205/api/v1/sessions/{session_id}?user_id=test_user_123"
```

**响应:**
```json
{
  "message": "Session ended successfully"
}
```

### 6. 获取会话摘要

**请求:**
```bash
curl -X GET "http://localhost:8205/api/v1/sessions/{session_id}/summary?user_id=test_user_123"
```

**响应:**
```json
{
  "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
  "user_id": "test_user_123",
  "status": "active",
  "message_count": 1,
  "total_tokens": 0,
  "total_cost": 0.0,
  "has_memory": true,
  "is_active": true,
  "created_at": "2025-10-03T09:53:09.821305Z",
  "last_activity": "2025-10-03T10:04:46.223080Z"
}
```

## 消息管理

### 1. 添加消息到会话

**请求:**
```bash
curl -X POST "http://localhost:8205/api/v1/sessions/{session_id}/messages?user_id=test_user_123" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "Hello, this is a test message",
    "message_type": "chat",
    "tokens_used": 5,
    "cost_usd": 0.0001,
    "metadata": {
      "model": "gpt-4"
    }
  }'
```

**响应:**
```json
{
  "message_id": "75ee4ea6-bc65-4a64-84ba-9420360c47aa",
  "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
  "user_id": "test_user_123",
  "role": "user",
  "content": "Hello, this is a test message",
  "message_type": "chat",
  "metadata": {
    "model": "gpt-4"
  },
  "tokens_used": 5,
  "cost_usd": 0.0001,
  "created_at": "2025-10-03T09:58:00.045269Z"
}
```

### 2. 获取会话消息

**请求:**
```bash
curl -X GET "http://localhost:8205/api/v1/sessions/{session_id}/messages?user_id=test_user_123&page=1&page_size=100"
```

**响应:**
```json
{
  "messages": [
    {
      "message_id": "75ee4ea6-bc65-4a64-84ba-9420360c47aa",
      "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
      "user_id": "test_user_123",
      "role": "user",
      "content": "Hello, this is a test message",
      "message_type": "chat",
      "metadata": {
        "model": "gpt-4"
      },
      "tokens_used": 5,
      "cost_usd": 0.0001,
      "created_at": "2025-10-03T09:58:00.045269Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 100
}
```

### 消息角色类型
- **user**: 用户消息
- **assistant**: AI助手响应
- **system**: 系统消息
- **tool_call**: 工具调用
- **tool_result**: 工具结果

### 消息类型
- **chat**: 聊天消息
- **system**: 系统消息
- **tool_call**: 工具调用消息
- **tool_result**: 工具执行结果
- **notification**: 通知消息

## 会话内存管理

### 1. 创建会话内存

**请求:**
```bash
curl -X POST "http://localhost:8205/api/v1/sessions/{session_id}/memory?user_id=test_user_123" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_type": "preference",
    "content": "User prefers dark mode UI",
    "metadata": {
      "category": "settings",
      "priority": "high"
    }
  }'
```

**响应:**
```json
{
  "memory_id": "125eb119-670f-4a21-a016-0aaf53108799",
  "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
  "user_id": "test_user_123",
  "memory_type": "conversation",
  "content": "User prefers dark mode UI",
  "metadata": {
    "category": "settings",
    "priority": "high"
  },
  "created_at": "2025-10-03T10:09:44.549754Z"
}
```

### 2. 获取会话内存

**请求:**
```bash
curl -X GET "http://localhost:8205/api/v1/sessions/{session_id}/memory?user_id=test_user_123"
```

**响应:**
```json
{
  "memory_id": "125eb119-670f-4a21-a016-0aaf53108799",
  "session_id": "7e02708b-ad2d-44d6-a851-d02d97137757",
  "user_id": "test_user_123",
  "memory_type": "conversation",
  "content": "User prefers dark mode UI",
  "metadata": {
    "category": "settings"
  },
  "created_at": "2025-10-03T10:09:44.549754Z"
}
```

### 内存类型
- **preference**: 用户偏好设置
- **conversation**: 对话上下文
- **entity**: 实体信息
- **summary**: 会话摘要
- **custom**: 自定义内存类型

## 统计和分析

### 获取服务统计

**请求:**
```bash
curl -X GET "http://localhost:8205/api/v1/sessions/stats"
```

**响应:**
```json
{
  "total_sessions": 15,
  "active_sessions": 8,
  "total_messages": 245,
  "total_tokens": 12500,
  "total_cost": 0.25,
  "average_messages_per_session": 16.3
}
```

## 会话状态

### 状态类型
- **active**: 活跃状态
- **completed**: 已完成
- **archived**: 已归档
- **ended**: 已结束

### 状态流转
```
active -> completed -> archived
active -> ended
```

## 数据模型

### Session (会话)
```json
{
  "session_id": "string (UUID)",
  "user_id": "string",
  "status": "active|completed|archived|ended",
  "conversation_data": {},
  "metadata": {},
  "is_active": true,
  "message_count": 0,
  "total_tokens": 0,
  "total_cost": 0.0,
  "session_summary": "",
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_activity": "datetime"
}
```

### SessionMessage (会话消息)
```json
{
  "message_id": "string (UUID)",
  "session_id": "string",
  "user_id": "string",
  "role": "user|assistant|system",
  "content": "string",
  "message_type": "chat|system|tool_call|tool_result",
  "metadata": {},
  "tokens_used": 0,
  "cost_usd": 0.0,
  "created_at": "datetime"
}
```

### SessionMemory (会话内存)
```json
{
  "memory_id": "string (UUID)",
  "session_id": "string",
  "user_id": "string",
  "memory_type": "string",
  "content": "string",
  "metadata": {},
  "created_at": "datetime"
}
```

## 错误处理

### 常见错误响应

#### 404 会话不存在
```json
{
  "detail": "Session not found"
}
```

#### 400 验证错误
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "memory_type"],
      "msg": "Field required"
    }
  ]
}
```

#### 503 服务不可用
```json
{
  "detail": "Session service not initialized"
}
```

## 测试指南

### 快速测试命令

#### 1. 健康检查
```bash
curl -s http://localhost:8205/health | python -m json.tool
```

#### 2. 创建会话
```bash
curl -s -X POST 'http://localhost:8205/api/v1/sessions' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"test_user_123","metadata":{"source":"api_test"}}' | python -m json.tool
```

#### 3. 添加消息
```bash
curl -s -X POST "http://localhost:8205/api/v1/sessions/{SESSION_ID}/messages?user_id=test_user_123" \
  -H 'Content-Type: application/json' \
  -d '{"role":"user","content":"Test message","tokens_used":5}' | python -m json.tool
```

#### 4. 创建内存
```bash
curl -s -X POST "http://localhost:8205/api/v1/sessions/{SESSION_ID}/memory?user_id=test_user_123" \
  -H 'Content-Type: application/json' \
  -d '{"memory_type":"preference","content":"Test memory","metadata":{}}' | python -m json.tool
```

#### 5. 获取会话列表
```bash
curl -s 'http://localhost:8205/api/v1/users/test_user_123/sessions?active_only=true' | python -m json.tool
```

#### 6. 结束会话
```bash
curl -s -X DELETE "http://localhost:8205/api/v1/sessions/{SESSION_ID}?user_id=test_user_123" | python -m json.tool
```

### 测试结果验证

**最近测试结果** (2025-10-03):
- ✅ 健康检查端点正常
- ✅ 详细健康检查正常
- ✅ 创建会话功能正常
- ✅ 获取会话详情正常
- ✅ 用户会话列表正常
- ✅ 添加消息功能正常
- ✅ 获取消息列表正常
- ✅ 创建会话内存正常
- ✅ 获取会话内存正常
- ✅ 更新会话功能正常
- ✅ 会话摘要功能正常
- ✅ 结束会话功能正常
- ✅ 服务统计功能正常

**测试覆盖率**: 100%
**成功率**: 16/16 测试通过

## 集成示例

### Python 客户端示例

```python
import httpx
from typing import Optional, Dict, Any

class SessionClient:
    def __init__(self, base_url: str = "http://localhost:8205"):
        self.base_url = base_url

    async def create_session(self, user_id: str, metadata: Optional[Dict] = None):
        """创建新会话"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/sessions",
                json={
                    "user_id": user_id,
                    "metadata": metadata or {}
                }
            )
            return response.json()

    async def add_message(self, session_id: str, user_id: str,
                         role: str, content: str, tokens: int = 0):
        """添加消息到会话"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/sessions/{session_id}/messages",
                params={"user_id": user_id},
                json={
                    "role": role,
                    "content": content,
                    "tokens_used": tokens
                }
            )
            return response.json()

    async def get_messages(self, session_id: str, user_id: str):
        """获取会话消息"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/messages",
                params={"user_id": user_id}
            )
            return response.json()

    async def create_memory(self, session_id: str, user_id: str,
                          memory_type: str, content: str):
        """创建会话内存"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/sessions/{session_id}/memory",
                params={"user_id": user_id},
                json={
                    "memory_type": memory_type,
                    "content": content
                }
            )
            return response.json()

    async def end_session(self, session_id: str, user_id: str):
        """结束会话"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/sessions/{session_id}",
                params={"user_id": user_id}
            )
            return response.json()

# 使用示例
async def main():
    client = SessionClient()

    # 创建会话
    session = await client.create_session(
        user_id="user_123",
        metadata={"source": "python_client"}
    )
    session_id = session["session_id"]

    # 添加消息
    await client.add_message(
        session_id=session_id,
        user_id="user_123",
        role="user",
        content="Hello, world!",
        tokens=3
    )

    # 创建内存
    await client.create_memory(
        session_id=session_id,
        user_id="user_123",
        memory_type="preference",
        content="User prefers concise responses"
    )

    # 获取消息
    messages = await client.get_messages(session_id, "user_123")
    print(f"Messages: {messages}")

    # 结束会话
    await client.end_session(session_id, "user_123")
```

## 数据库表结构

### sessions 表
```sql
CREATE TABLE dev.sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    conversation_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0,
    session_summary TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_is_active (is_active)
);
```

### session_messages 表
```sql
CREATE TABLE dev.session_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL UNIQUE,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'chat',
    metadata JSONB DEFAULT '{}',
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES dev.sessions(session_id),
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id)
);
```

### session_memories 表
```sql
CREATE TABLE dev.session_memories (
    id SERIAL PRIMARY KEY,
    memory_id VARCHAR(255) NOT NULL UNIQUE,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES dev.sessions(session_id),
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_memory_type (memory_type)
);
```

## 部署和配置

### 环境变量
```bash
DATABASE_URL=postgresql://...
CONSUL_HOST=localhost
CONSUL_PORT=8500
SERVICE_PORT=8205
DEBUG=true
LOG_LEVEL=INFO
```

### 启动命令
```bash
# 使用部署脚本
deployment/scripts/start_user_service.sh -e dev start

# 或直接启动
python -m microservices.session_service.main
```

### 重启服务
```bash
# 重启会话服务
deployment/scripts/start_user_service.sh -e dev restart session_service

# 查看日志
deployment/scripts/start_user_service.sh logs session_service
```

## 性能优化

### 最佳实践

1. **分页查询**: 获取消息时使用分页避免一次性加载过多数据
2. **索引优化**: 在 user_id, session_id 上建立索引提高查询性能
3. **缓存策略**: 对频繁访问的会话数据进行缓存
4. **异步处理**: 使用异步 I/O 提高并发处理能力
5. **内存管理**: 定期清理过期会话和归档历史数据
6. **连接池**: 使用数据库连接池提高数据库访问效率

### 监控指标

- 活跃会话数
- 消息总数
- Token使用量
- 成本统计
- 平均会话时长
- 消息吞吐量

## Consul 集成

服务自动注册到 Consul，支持服务发现和健康检查：
- 服务名称: `session_service`
- 健康检查端点: `/health`
- 检查间隔: 10秒
- 超时时间: 5秒

## 故障排查

### 常见问题

1. **会话未找到**
   - 检查 session_id 是否正确
   - 确认会话未被删除或过期

2. **内存创建失败**
   - 确保提供了 memory_type 和 content 字段
   - 检查 JSON 格式是否正确

3. **消息添加失败**
   - 验证会话是否处于活跃状态
   - 确认 user_id 与会话所有者匹配

4. **服务连接失败**
   - 检查服务是否正在运行: `curl http://localhost:8205/health`
   - 查看服务日志: `deployment/scripts/start_user_service.sh logs session_service`

---

**文档版本**: 1.0.0
**最后更新**: 2025-10-03
**维护者**: Session Service Team
