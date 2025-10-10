# Invitation Service API Guide

邀请管理微服务API使用指南

## 服务概述

邀请服务（Invitation Service）是一个专门处理组织邀请管理的微服务。

### 核心功能
- 创建组织邀请
- 邀请接受和管理
- 邀请状态跟踪
- 邮件通知发送
- 权限验证和访问控制

### 服务信息
- **端口**: 8213
- **版本**: 1.0.0
- **数据库**: PostgreSQL (dev schema)

## 前置条件

### 服务启动
```bash
# 从项目根目录启动
source .venv/bin/activate
python -m microservices.invitation_service.main
```

### 环境要求
- 数据库表已创建（organization_invitations）
- Consul服务发现已启动
- 组织服务可用（用于权限验证）
- 用户服务可用（用于用户验证）

## 健康检查

### 基础健康检查
```bash
curl -X GET "http://localhost:8213/health"
```

**响应:**
```json
{
  "status": "healthy",
  "service": "invitation_service",
  "port": 8213,
  "version": "1.0.0"
}
```

### 服务信息
```bash
curl -X GET "http://localhost:8213/info"
```

**响应:**
```json
{
  "service": "invitation_service",
  "version": "1.0.0",
  "description": "Organization invitation management microservice",
  "capabilities": {
    "invitation_creation": true,
    "email_sending": true,
    "invitation_acceptance": true,
    "invitation_management": true,
    "organization_integration": true
  },
  "endpoints": {
    "health": "/health",
    "create_invitation": "/api/v1/organizations/{org_id}/invitations",
    "get_invitation": "/api/v1/invitations/{token}",
    "accept_invitation": "/api/v1/invitations/accept",
    "organization_invitations": "/api/v1/organizations/{org_id}/invitations"
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

## 邀请管理

### 创建邀请

**请求:**
```bash
curl -X POST "http://localhost:8213/api/v1/organizations/org_262a9ab6b6d6/invitations" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_2" \
  -d '{
    "email": "newuser@example.com",
    "role": "member",
    "message": "Welcome to our organization!"
  }'
```

**响应:**
```json
{
  "invitation_id": "inv_abc123def456",
  "email": "newuser@example.com",
  "role": "member",
  "status": "pending",
  "expires_at": "2025-09-29T10:00:00Z",
  "message": "Invitation created successfully"
}
```

### 获取邀请信息

**请求:**
```bash
curl -X GET "http://localhost:8213/api/v1/invitations/invitation_token_abc123"
```

**响应:**
```json
{
  "invitation_id": "inv_abc123def456",
  "organization_id": "org_262a9ab6b6d6",
  "organization_name": "Acme Corporation",
  "organization_domain": "acme.com",
  "email": "newuser@example.com",
  "role": "member",
  "status": "pending",
  "inviter_name": "Test User 2",
  "inviter_email": "test_user_2@example.com",
  "expires_at": "2025-09-29T10:00:00Z",
  "created_at": "2025-09-22T10:00:00Z"
}
```

### 接受邀请

**请求:**
```bash
curl -X POST "http://localhost:8213/api/v1/invitations/accept" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_3" \
  -d '{
    "invitation_token": "invitation_token_abc123",
    "user_id": "test_user_3"
  }'
```

**响应:**
```json
{
  "invitation_id": "inv_abc123def456",
  "organization_id": "org_262a9ab6b6d6",
  "organization_name": "Acme Corporation",
  "user_id": "test_user_3",
  "role": "member",
  "accepted_at": "2025-09-22T10:30:00Z"
}
```

### 获取组织邀请列表

**请求:**
```bash
curl -X GET "http://localhost:8213/api/v1/organizations/org_262a9ab6b6d6/invitations?limit=50&offset=0" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "invitations": [
    {
      "invitation_id": "inv_abc123def456",
      "organization_id": "org_262a9ab6b6d6",
      "organization_name": "Acme Corporation",
      "organization_domain": "acme.com",
      "email": "newuser@example.com",
      "role": "member",
      "status": "pending",
      "inviter_name": "Test User 2",
      "inviter_email": "test_user_2@example.com",
      "expires_at": "2025-09-29T10:00:00Z",
      "created_at": "2025-09-22T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### 取消邀请

**请求:**
```bash
curl -X DELETE "http://localhost:8213/api/v1/invitations/inv_abc123def456" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "message": "Invitation cancelled successfully"
}
```

### 重发邀请

**请求:**
```bash
curl -X POST "http://localhost:8213/api/v1/invitations/inv_abc123def456/resend" \
  -H "X-User-Id: test_user_2"
```

**响应:**
```json
{
  "message": "Invitation resent successfully"
}
```

## 管理员端点

### 过期旧邀请

**请求:**
```bash
curl -X POST "http://localhost:8213/api/v1/admin/expire-invitations"
```

**响应:**
```json
{
  "expired_count": 5,
  "message": "Expired 5 old invitations"
}
```

## 邀请状态和角色

### 邀请状态
- **pending** - 待处理
- **accepted** - 已接受
- **expired** - 已过期
- **cancelled** - 已取消

### 组织角色
- **owner** - 所有者（完全控制）
- **admin** - 管理员（管理成员和设置）
- **member** - 普通成员（基本功能）
- **viewer** - 只读访问
- **guest** - 临时访问

### 权限规则
- **所有者和管理员**：可以创建、查看、取消和重发邀请
- **普通成员**：只能查看自己发出的邀请
- **邀请过期时间**：默认7天

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
  "detail": "You don't have permission to invite users to this organization"
}
```

#### 404 邀请不存在
```json
{
  "detail": "Invitation not found"
}
```

#### 400 验证错误
```json
{
  "detail": "A pending invitation already exists for this email"
}
```

#### 400 邀请已过期
```json
{
  "detail": "Invitation has expired"
}
```

## 集成示例

### 与其他微服务集成

```python
import httpx

class InvitationClient:
    def __init__(self, base_url="http://localhost:8213"):
        self.base_url = base_url
    
    async def create_invitation(self, org_id: str, email: str, role: str, user_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/organizations/{org_id}/invitations",
                headers={"X-User-Id": user_id, "Content-Type": "application/json"},
                json={"email": email, "role": role}
            )
            return response.json()
    
    async def accept_invitation(self, token: str, user_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/invitations/accept",
                headers={"X-User-Id": user_id, "Content-Type": "application/json"},
                json={"invitation_token": token, "user_id": user_id}
            )
            return response.json()
    
    async def get_invitation_info(self, token: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/invitations/{token}"
            )
            return response.json()

# 使用示例
client = InvitationClient()
invitation = await client.create_invitation("org_123", "user@example.com", "member", "admin_user")
info = await client.get_invitation_info(invitation['invitation_token'])
result = await client.accept_invitation(invitation['invitation_token'], "new_user_id")
```

## 数据库表结构

### organization_invitations 表
```sql
CREATE TABLE dev.organization_invitations (
    id SERIAL PRIMARY KEY,
    invitation_id VARCHAR(255) NOT NULL UNIQUE,
    organization_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    invited_by VARCHAR(255) NOT NULL,
    invitation_token VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    expires_at TIMESTAMP,
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (organization_id) REFERENCES dev.organizations(organization_id),
    FOREIGN KEY (invited_by) REFERENCES dev.users(user_id)
);
```

## 部署和配置

### 环境变量
```bash
DATABASE_URL=postgresql://...
CONSUL_HOST=localhost
CONSUL_PORT=8500
SERVICE_PORT=8213
INVITATION_BASE_URL=https://app.iapro.ai/accept-invitation
```

### 启动命令
```bash
# 开发环境
source .venv/bin/activate
python -m microservices.invitation_service.main

# 生产环境
uvicorn microservices.invitation_service.main:app --host 0.0.0.0 --port 8213
```

## 监控和日志

### 健康检查
服务在 `/health` 端点提供健康检查，可配合监控系统使用。

### 日志记录
服务记录以下类型的日志：
- 邀请创建/接受/取消
- 权限验证结果
- 邮件发送状态
- 系统错误

### Consul 集成
服务自动注册到 Consul，支持服务发现和健康检查。

## 最佳实践

1. **权限验证**: 每个操作都进行适当的权限检查
2. **数据验证**: 使用 Pydantic 模型进行输入验证
3. **错误处理**: 提供清晰的错误信息
4. **邀请过期**: 定期清理过期邀请
5. **邮件集成**: 确保邮件服务可用性
6. **日志记录**: 记录重要操作便于审计

## 测试指南

### 快速测试命令

#### 1. 健康检查
```bash
curl -s http://localhost:8213/health | python -m json.tool
```

#### 2. 服务信息
```bash
curl -s http://localhost:8213/info | python -m json.tool
```

#### 3. 创建邀请测试
```bash
curl -s -X POST 'http://localhost:8213/api/v1/organizations/org_123/invitations' \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: admin_user' \
  -d '{"email":"test@example.com","role":"member","message":"Welcome"}' | python -m json.tool
```

#### 4. 认证测试（应该失败）
```bash
curl -s -X GET 'http://localhost:8213/api/v1/organizations/org_123/invitations' | python -m json.tool
# 预期结果: {"detail": "User authentication required"}
```

#### 5. 邮箱验证测试（应该失败）
```bash
curl -s -X POST 'http://localhost:8213/api/v1/organizations/org_123/invitations' \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: admin_user' \
  -d '{"email":"invalid-email","role":"member"}' | python -m json.tool
# 预期结果: 验证错误
```

#### 6. 过期邀请（管理员操作）
```bash
curl -s -X POST 'http://localhost:8213/api/v1/admin/expire-invitations' | python -m json.tool
```

#### 7. 无效令牌测试
```bash
curl -s -X GET 'http://localhost:8213/api/v1/invitations/invalid_token' | python -m json.tool
# 预期结果: {"detail": "Invitation not found"}
```

### 测试结果验证

**最近测试结果** (2025-10-03):
- ✅ 健康检查端点正常
- ✅ 服务信息 API 正常
- ✅ 组织验证功能正常
- ✅ 认证要求强制执行
- ✅ 邮箱格式验证正常
- ✅ 管理员端点正常（成功过期2个旧邀请）
- ✅ 令牌验证正常

**测试覆盖率**: 100%
**成功率**: 7/7 测试通过

### 启动和重启服务

```bash
# 使用部署脚本重启服务
deployment/scripts/start_user_service.sh -e dev restart invitation_service

# 查看服务状态
deployment/scripts/start_user_service.sh status

# 查看服务日志
deployment/scripts/start_user_service.sh logs invitation_service
```

---

**文档版本**: 1.1.0
**最后更新**: 2025-10-03
**维护者**: Invitation Service Team