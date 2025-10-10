# Authorization Service 使用指南

## 服务概述
Authorization Service 是一个统一的权限管理微服务，运行在端口 **8203**。负责处理资源访问控制、多级授权、权限管理等功能。

## 端口配置
- **服务端口**: 8203
- **API基础路径**: `http://localhost:8203/api/v1/auth`

## 数据库配置
- **数据库**: PostgreSQL (通过 Supabase)
- **连接字符串**: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Schema**: `dev`
- **核心表**: `auth_permissions` (统一权限表)

## 核心功能与测试用例

### 1. 健康检查

#### 基础健康检查
```bash
curl http://localhost:8203/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "service": "authorization_service",
  "port": 8203,
  "version": "1.0.0"
}
```

#### 详细健康检查
```bash
curl http://localhost:8203/health/detailed
```

**响应示例**:
```json
{
  "service": "authorization_service",
  "status": "operational",
  "port": 8203,
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2025-09-18T12:50:00.000Z"
}
```

### 2. 权限检查 (核心功能)

#### 检查用户资源访问权限
```bash
curl -X POST "http://localhost:8203/api/v1/auth/check-access" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_2",
  "resource_type": "mcp_tool", 
  "resource_name": "weather_api",
  "required_access_level": "read_only"
}'
```

**成功响应示例** (用户有权限):
```json
{
  "has_access": true,
  "user_access_level": "read_only",
  "permission_source": "subscription",
  "subscription_tier": "free",
  "organization_plan": null,
  "reason": "Subscription access: read_only",
  "expires_at": null,
  "metadata": {
    "subscription_required": "free",
    "resource_category": "utilities"
  }
}
```

**拒绝响应示例** (用户无权限):
```bash
curl -X POST "http://localhost:8203/api/v1/auth/check-access" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_2",
  "resource_type": "ai_model", 
  "resource_name": "advanced_llm",
  "required_access_level": "read_only"
}'
```

```json
{
  "has_access": false,
  "user_access_level": "none",
  "permission_source": "system_default",
  "subscription_tier": "free",
  "organization_plan": null,
  "reason": "Insufficient permissions for ai_model:advanced_llm, required: read_only",
  "expires_at": null,
  "metadata": {
    "required_level": "read_only"
  }
}
```

### 3. 权限授予

#### 授予用户权限
```bash
curl -X POST "http://localhost:8203/api/v1/auth/grant" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_3",
  "resource_type": "api_endpoint",
  "resource_name": "data_export",
  "access_level": "read_write",
  "permission_source": "admin_grant",
  "granted_by": "admin_user",
  "expires_in_days": 30,
  "reason": "Project requirement"
}'
```

### 4. 权限撤销

#### 撤销用户权限
```bash
curl -X POST "http://localhost:8203/api/v1/auth/revoke" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_3",
  "resource_type": "api_endpoint",
  "resource_name": "data_export",
  "revoked_by": "admin_user",
  "reason": "Project completed"
}'
```

### 5. 批量权限检查

#### 检查多个资源的访问权限
```bash
curl -X POST "http://localhost:8203/api/v1/auth/check-access/bulk" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "test_user_2",
  "resources": [
    {
      "resource_type": "mcp_tool",
      "resource_name": "weather_api",
      "required_access_level": "read_only"
    },
    {
      "resource_type": "ai_model",
      "resource_name": "advanced_llm",
      "required_access_level": "read_only"
    }
  ]
}'
```

### 6. 用户权限查询

#### 获取用户所有权限
```bash
curl "http://localhost:8203/api/v1/auth/user-permissions?user_id=test_user_2"
```

### 7. 服务信息与统计

#### 获取服务信息
```bash
curl http://localhost:8203/api/v1/auth/info
```

**响应示例**:
```json
{
  "service": "authorization_service",
  "version": "1.0.0",
  "description": "Comprehensive resource authorization and permission management",
  "capabilities": {
    "resource_access_control": true,
    "multi_level_authorization": ["subscription", "organization", "admin"],
    "permission_management": true,
    "bulk_operations": true
  },
  "endpoints": {
    "check_access": "/api/v1/auth/check-access",
    "grant_permission": "/api/v1/auth/grant",
    "revoke_permission": "/api/v1/auth/revoke",
    "user_permissions": "/api/v1/auth/user-permissions",
    "bulk_operations": "/api/v1/auth/bulk"
  }
}
```

## 权限层级说明

### 订阅层级 (Subscription Tiers)
1. **FREE** - 基础免费层
2. **PRO** - 专业版
3. **ENTERPRISE** - 企业版
4. **CUSTOM** - 定制版

### 访问级别 (Access Levels)
1. **NONE** - 无权限
2. **READ_ONLY** - 只读权限
3. **READ_WRITE** - 读写权限
4. **ADMIN** - 管理员权限
5. **OWNER** - 所有者权限

### 权限来源 (Permission Sources)
1. **SUBSCRIPTION** - 订阅级别授予
2. **ORGANIZATION** - 组织授予
3. **ADMIN_GRANT** - 管理员授予
4. **SYSTEM_DEFAULT** - 系统默认

## 默认资源配置

服务启动时会初始化以下默认资源权限配置：

| 资源类型 | 资源名称 | 所需订阅级别 | 访问级别 |
|---------|---------|------------|---------|
| mcp_tool | weather_api | FREE | READ_ONLY |
| prompt | basic_assistant | FREE | READ_ONLY |
| mcp_tool | image_generator | PRO | READ_WRITE |
| ai_model | advanced_llm | PRO | READ_ONLY |
| database | analytics_db | ENTERPRISE | READ_WRITE |
| api_endpoint | admin_api | ENTERPRISE | ADMIN |

## 权限检查逻辑

权限检查按以下优先级顺序进行：

1. **管理员授予的权限** (最高优先级)
2. **组织权限**
3. **订阅级别权限**
4. **用户特定权限** (非管理员授予)
5. **拒绝访问** (如果以上都不满足)

## 故障排查

### 常见问题

1. **数据库连接失败**
   - 确保 Supabase 正在运行
   - 检查端口 54322 是否可用
   - 验证数据库凭据

2. **权限检查总是返回 false**
   - 验证用户存在于 users 表
   - 检查资源配置是否正确
   - 确认订阅级别设置正确

3. **406 Not Acceptable 错误**
   - 这是 Supabase 查询语法问题
   - 通常不影响核心功能
   - 检查查询参数格式

## 开发调试

### 查看数据库中的权限配置
```sql
-- 连接数据库
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

-- 查看资源配置
SET search_path TO dev;
SELECT * FROM auth_permissions WHERE permission_type = 'resource_config';

-- 查看用户权限
SELECT * FROM auth_permissions WHERE permission_type = 'user_permission' AND target_id = 'test_user_2';
```

### 添加新的资源配置
```sql
INSERT INTO dev.auth_permissions (
    permission_type, target_type, resource_type, resource_name,
    access_level, permission_source, subscription_tier_required,
    is_active, description
) VALUES (
    'resource_config', 'global', 'api_endpoint', 'custom_api',
    'read_only', 'system_default', 'pro',
    true, 'Custom API endpoint'
);
```

## 测试场景

### 场景1: Free用户访问Free资源 ✅
- 用户: test_user_2 (free订阅)
- 资源: weather_api (需要free)
- 结果: 允许访问

### 场景2: Free用户访问Pro资源 ❌
- 用户: test_user_2 (free订阅)  
- 资源: advanced_llm (需要pro)
- 结果: 拒绝访问

### 场景3: 管理员授予特殊权限 ✅
- 即使用户订阅级别不足
- 管理员授予的权限优先级最高
- 可以设置过期时间

## 性能优化建议

1. 使用批量操作减少API调用
2. 缓存频繁访问的权限结果
3. 定期清理过期的权限记录
4. 使用索引优化数据库查询

## 相关服务

- **Account Service** (端口 8201) - 用户账户管理
- **Auth Service** (端口 8202) - 身份认证
- **Audit Service** (端口 8204) - 审计日志