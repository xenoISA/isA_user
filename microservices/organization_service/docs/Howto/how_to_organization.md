# Organization Service API Guide

组织管理微服务API使用指南

## 服务概述

组织服务（Organization Service）是一个专门处理组织管理、成员管理和多租户支持的微服务。

### 核心功能
- 组织创建、更新、删除
- 成员管理（添加、移除、角色管理）
- 权限控制（所有者、管理员、成员、访客）
- 上下文切换（个人/组织）
- 使用量统计和分析

### 服务信息
- **端口**: 8212
- **版本**: 1.0.0
- **数据库**: PostgreSQL (dev schema)

## 前置条件

### 服务启动
```bash
# 从项目根目录启动
source .venv/bin/activate
python -m microservices.organization_service.main
```

### 环境要求
- 数据库表已创建（运行migration）
- Consul服务发现已启动
- 认证服务可用（用于JWT验证）

## 健康检查

### 基础健康检查
```bash
curl -X GET "http://localhost:8212/health"
```

**响应:**
```json
{
  "status": "healthy",
  "service": "organization_service",
  "port": 8212,
  "version": "1.0.0"
}
```

### 服务信息
```bash
curl -X GET "http://localhost:8212/info"
```

**响应:**
```json
{
  "service": "organization_service",
  "version": "1.0.0",
  "description": "Organization management microservice",
  "capabilities": {
    "organization_management": true,
    "member_management": true,
    "role_management": true,
    "context_switching": true,
    "usage_tracking": true,
    "multi_tenant": true
  },
  "endpoints": {
    "health": "/health",
    "organizations": "/api/v1/organizations",
    "members": "/api/v1/organizations/{org_id}/members",
    "context": "/api/v1/organizations/context",
    "stats": "/api/v1/organizations/{org_id}/stats"
  }
}
```

## 认证

所有API端点都需要认证。支持两种方式：

### 1. Header方式（推荐）
```bash
curl -H "X-User-Id: test_user_2" [其他参数]
```

### 2. JWT Token方式
```bash
curl -H "Authorization: Bearer your-jwt-token" [其他参数]
```

## 组织管理

### 创建组织

**请求:**
```bash
curl -X POST "http://localhost:8212/api/v1/organizations" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_2" \
  -d '{
    "name": "Acme Corporation",
    "display_name": "Acme Corp",
    "description": "A sample organization for testing",
    "industry": "Technology",
    "size": "50-100",
    "website": "https://acme.com",
    "billing_email": "billing@acme.com",
    "plan": "professional"
  }'
```

**响应:**
```json
{
  "organization_id": "org_abc123def456",
  "name": "Acme Corporation",
  "display_name": "Acme Corp",
  "description": "A sample organization for testing",
  "industry": "Technology",
  "size": "50-100",
  "website": "https://acme.com",
  "billing_email": "billing@acme.com",
  "plan": "professional",
  "status": "active",
  "member_count": 1,
  "credits_pool": 0,
  "settings": {},
  "metadata": {},
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:00:00Z"
}
```

### 获取组织信息

**请求:**
```bash
curl -X GET "http://localhost:8212/api/v1/organizations/org_abc123def456" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "organization_id": "org_abc123def456",
  "name": "Acme Corporation",
  "display_name": "Acme Corp",
  "plan": "professional",
  "status": "active",
  "member_count": 3,
  "credits_pool": 1000,
  "created_at": "2025-01-20T10:00:00Z"
}
```

### 更新组织

**请求:**
```bash
curl -X PUT "http://localhost:8212/api/v1/organizations/org_abc123def456" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_2" \
  -d '{
    "display_name": "Acme Corporation Ltd",
    "description": "Updated description"
  }'
```

### 删除组织

**请求:**
```bash
curl -X DELETE "http://localhost:8212/api/v1/organizations/org_abc123def456" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "message": "Organization deleted successfully"
}
```

### 获取用户组织列表

**请求:**
```bash
curl -X GET "http://localhost:8212/api/v1/users/organizations" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "organizations": [
    {
      "organization_id": "org_abc123def456",
      "name": "Acme Corporation",
      "user_role": "owner",
      "member_count": 3,
      "plan": "professional",
      "status": "active"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

## 成员管理

### 添加组织成员

**请求:**
```bash
curl -X POST "http://localhost:8212/api/v1/organizations/org_abc123def456/members" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_2" \
  -d '{
    "user_id": "test_user_3",
    "role": "admin",
    "department": "Engineering",
    "title": "Senior Developer",
    "permissions": ["read_all", "write_own"]
  }'
```

**响应:**
```json
{
  "user_id": "test_user_3",
  "organization_id": "org_abc123def456",
  "email": "user3@example.com",
  "name": "Test User 3",
  "role": "admin",
  "department": "Engineering",
  "title": "Senior Developer",
  "status": "active",
  "permissions": ["read_all", "write_own"],
  "joined_at": "2025-01-20T10:30:00Z"
}
```

### 获取组织成员列表

**请求:**
```bash
curl -X GET "http://localhost:8212/api/v1/organizations/org_abc123def456/members?limit=50&offset=0&role=admin" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "members": [
    {
      "user_id": "test_user_2",
      "email": "user2@example.com",
      "name": "Test User 2",
      "role": "owner",
      "status": "active",
      "joined_at": "2025-01-20T10:00:00Z"
    },
    {
      "user_id": "test_user_3",
      "email": "user3@example.com",
      "name": "Test User 3",
      "role": "admin",
      "department": "Engineering",
      "status": "active",
      "joined_at": "2025-01-20T10:30:00Z"
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

### 更新组织成员

**请求:**
```bash
curl -X PUT "http://localhost:8212/api/v1/organizations/org_abc123def456/members/test_user_3" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_2" \
  -d '{
    "role": "member",
    "title": "Lead Developer"
  }'
```

### 移除组织成员

**请求:**
```bash
curl -X DELETE "http://localhost:8212/api/v1/organizations/org_abc123def456/members/test_user_3" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "message": "Member removed successfully"
}
```

## 上下文切换

### 切换到组织上下文

**请求:**
```bash
curl -X POST "http://localhost:8212/api/v1/organizations/context" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_2" \
  -d '{
    "organization_id": "org_abc123def456"
  }'
```

**响应:**
```json
{
  "context_type": "organization",
  "organization_id": "org_abc123def456",
  "organization_name": "Acme Corporation",
  "user_role": "owner",
  "permissions": ["*"],
  "credits_available": 1000
}
```

### 切换到个人上下文

**请求:**
```bash
curl -X POST "http://localhost:8212/api/v1/organizations/context" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_2" \
  -d '{
    "organization_id": null
  }'
```

**响应:**
```json
{
  "context_type": "individual",
  "organization_id": null,
  "organization_name": null,
  "user_role": null,
  "permissions": [],
  "credits_available": null
}
```

## 统计信息

### 获取组织统计

**请求:**
```bash
curl -X GET "http://localhost:8212/api/v1/organizations/org_abc123def456/stats" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "organization_id": "org_abc123def456",
  "name": "Acme Corporation",
  "plan": "professional",
  "status": "active",
  "member_count": 3,
  "active_members": 3,
  "credits_pool": 1000,
  "credits_used_this_month": 150,
  "storage_used_gb": 2.5,
  "api_calls_this_month": 1250,
  "created_at": "2025-01-20T10:00:00Z"
}
```

### 获取组织使用量

**请求:**
```bash
curl -X GET "http://localhost:8212/api/v1/organizations/org_abc123def456/usage?start_date=2025-01-01&end_date=2025-01-31" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "organization_id": "org_abc123def456",
  "period_start": "2025-01-01T00:00:00Z",
  "period_end": "2025-01-31T23:59:59Z",
  "credits_consumed": 150,
  "api_calls": 1250,
  "storage_gb_hours": 75.0,
  "active_users": 3,
  "top_users": [
    {
      "user_id": "test_user_2",
      "credits_used": 100,
      "api_calls": 800
    }
  ],
  "usage_by_service": {
    "task_service": 50,
    "storage_service": 30,
    "payment_service": 70
  }
}
```

## 角色和权限

### 角色层级
1. **owner** - 组织所有者（完全控制）
2. **admin** - 管理员（成员管理、设置管理）
3. **member** - 普通成员（基本功能）
4. **viewer** - 只读访问
5. **guest** - 临时访问

### 权限规则
- **所有者**：可以管理所有内容，包括删除组织
- **管理员**：可以管理成员和组织设置，但不能管理其他管理员或所有者
- **成员**：可以使用组织功能，但不能管理其他成员
- **访客**：只能查看被授权的内容

## 错误处理

### 常见错误响应

#### 401 未认证
```json
{
  "detail": "User authentication required"
}
```

#### 403 访问被拒绝
```json
{
  "detail": "User test_user_3 does not have admin access to organization org_abc123def456"
}
```

#### 404 组织不存在
```json
{
  "detail": "Organization org_abc123def456 not found"
}
```

#### 400 验证错误
```json
{
  "detail": "Organization name and billing email are required"
}
```

## 集成示例

### 与其他微服务集成

```python
import httpx

class OrganizationClient:
    def __init__(self, base_url="http://localhost:8212"):
        self.base_url = base_url
    
    async def get_user_organizations(self, user_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/organizations",
                headers={"X-User-Id": user_id}
            )
            return response.json()
    
    async def switch_context(self, user_id: str, org_id: str = None):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/organizations/context",
                headers={"X-User-Id": user_id},
                json={"organization_id": org_id}
            )
            return response.json()

# 使用示例
client = OrganizationClient()
orgs = await client.get_user_organizations("test_user_2")
context = await client.switch_context("test_user_2", "org_abc123def456")
```

## 数据库表结构

### organizations 表
```sql
CREATE TABLE dev.organizations (
    organization_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    billing_email VARCHAR(255) NOT NULL,
    plan VARCHAR(20) DEFAULT 'free',
    status VARCHAR(20) DEFAULT 'active',
    credits_pool DECIMAL(20, 8) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### organization_members 表
```sql
CREATE TABLE dev.organization_members (
    organization_id VARCHAR(255),
    user_id VARCHAR(255),
    role VARCHAR(20) DEFAULT 'member',
    status VARCHAR(20) DEFAULT 'active',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (organization_id, user_id)
);
```

## 部署和配置

### 环境变量
```bash
DATABASE_URL=postgresql://...
CONSUL_HOST=localhost
CONSUL_PORT=8500
SERVICE_PORT=8212
```

### 启动命令
```bash
# 开发环境
source .venv/bin/activate
python -m microservices.organization_service.main

# 生产环境
uvicorn microservices.organization_service.main:app --host 0.0.0.0 --port 8212
```

### 数据库迁移
```bash
# 执行数据库迁移
source .env && PGPASSWORD=$SUPABASE_PWD psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -f microservices/organization_service/migrations/001_create_organization_tables.sql
```

## 监控和日志

### 健康检查
服务在 `/health` 端点提供健康检查，可配合监控系统使用。

### 日志记录
服务记录以下类型的日志：
- 组织创建/更新/删除
- 成员添加/移除/角色变更
- 权限验证失败
- 系统错误

### Consul 集成
服务自动注册到 Consul，支持服务发现和健康检查。

## 最佳实践

1. **权限验证**: 每个操作都进行适当的权限检查
2. **数据验证**: 使用 Pydantic 模型进行输入验证
3. **错误处理**: 提供清晰的错误信息
4. **日志记录**: 记录重要操作便于审计
5. **性能优化**: 使用数据库索引和连接池

---

**文档版本**: 1.0.0  
**最后更新**: 2025-01-20  
**维护者**: Organization Service Team