# 微服务内部认证架构指南

## 📋 概述

本文档说明如何在isA User Platform的26个微服务中使用统一的内部服务认证机制。

## 🎯 设计目标

- **统一认证**：所有服务使用相同的认证逻辑
- **服务间通信**：服务可以互相调用而无需用户凭证
- **权限控制**：内部服务调用自动绕过用户权限检查
- **易于维护**：认证逻辑集中在 `core/` 目录

## 🏗️ 架构组件

### 1. 核心认证模块 (`core/`)

#### `core/internal_service_auth.py`
提供内部服务认证的基础功能：

```python
from core.internal_service_auth import InternalServiceAuth

# 获取内部服务认证 headers
headers = InternalServiceAuth.get_internal_service_headers()
# 返回: {
#     "X-Internal-Service": "true",
#     "X-Internal-Service-Secret": "<secret>"
# }
```

#### `core/auth_dependencies.py`
提供 FastAPI 认证依赖：

```python
from fastapi import Depends
from core.auth_dependencies import (
    require_auth_or_internal_service,
    optional_auth_or_internal_service,
    is_internal_service_request
)

@app.get("/api/resource")
async def get_resource(
    user_id: str = Depends(require_auth_or_internal_service)
):
    if is_internal_service_request(user_id):
        # 内部服务调用，绕过权限检查
        return await get_all_data()
    else:
        # 普通用户调用，检查权限
        return await get_user_data(user_id)
```

#### `core/service_client_base.py`
所有服务客户端的基类：

```python
from core.service_client_base import BaseServiceClient

class AccountServiceClient(BaseServiceClient):
    service_name = "account_service"
    default_port = 8202

    async def get_user(self, user_id: str):
        response = await self.get(f"/api/v1/users/{user_id}")
        return response.json()
```

## 📚 使用指南

### 服务端（API 端点）

#### 方式 1：使用统一认证依赖（推荐）

```python
from fastapi import FastAPI, Depends
from core.auth_dependencies import require_auth_or_internal_service, is_internal_service_request

app = FastAPI()

@app.get("/api/v1/organizations/{organization_id}")
async def get_organization(
    organization_id: str,
    user_id: str = Depends(require_auth_or_internal_service)  # 自动处理认证
):
    # 检查是否是内部服务调用
    if is_internal_service_request(user_id):
        # 跳过权限检查，直接返回数据
        return await service.get_organization(organization_id, user_id=None)
    else:
        # 用户调用，需要检查权限
        return await service.get_organization(organization_id, user_id)
```

#### 方式 2：在 Service 层处理

```python
class OrganizationService:
    async def get_organization(
        self,
        organization_id: str,
        user_id: Optional[str] = None
    ):
        # 内部服务调用跳过权限检查
        if user_id and user_id != "internal-service":
            has_access = await self.check_user_access(organization_id, user_id)
            if not has_access:
                raise PermissionDenied()

        return await self.repository.get_organization(organization_id)
```

### 客户端（服务间调用）

#### 方式 1：使用 BaseServiceClient（推荐）

```python
from core.service_client_base import BaseServiceClient

class OrganizationServiceClient(BaseServiceClient):
    service_name = "organization_service"
    default_port = 8212

    async def get_organization(self, organization_id: str):
        """获取组织信息"""
        response = await self.get(f"/api/v1/organizations/{organization_id}")
        response.raise_for_status()
        return response.json()

# 使用
async with OrganizationServiceClient() as client:
    org = await client.get_organization("org_123")
    print(org)
```

**BaseServiceClient 自动处理：**
- ✅ 服务发现
- ✅ 内部服务认证 headers
- ✅ HTTP 客户端管理
- ✅ 超时控制

#### 方式 2：手动添加认证 headers

```python
import httpx
from core.internal_service_auth import InternalServiceAuth

headers = InternalServiceAuth.get_internal_service_headers()

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8212/api/v1/organizations/org_123",
        headers=headers
    )
    org = response.json()
```

## 🔒 安全配置

### 环境变量

```bash
# .env 或环境变量
INTERNAL_SERVICE_SECRET=your-secure-secret-min-32-chars-replace-in-production
```

**重要提示：**
- ⚠️ 生产环境必须使用强密钥（至少32个字符）
- ⚠️ 不要将密钥提交到Git仓库
- ⚠️ 所有服务必须使用相同的密钥

### 推荐：使用密钥管理服务

```python
import os
from hashlib import sha256

# 从 Kubernetes Secrets / AWS Secrets Manager 等读取
INTERNAL_SERVICE_SECRET = os.getenv(
    "INTERNAL_SERVICE_SECRET",
    sha256(b"default-dev-secret").hexdigest()  # 开发环境
)
```

## 📊 认证流程

```
┌─────────────┐                    ┌──────────────────┐
│ Auth Service│                    │Organization Svc  │
│             │                    │                  │
│  需要验证   │  1. HTTP Request   │                  │
│  组织是否   │ ───────────────>  │                  │
│  存在       │  Headers:          │                  │
│             │  X-Internal-Service│                  │
│             │  X-Internal-Service│                  │
│             │        -Secret     │                  │
│             │                    │                  │
│             │  2. 检查认证       │                  │
│             │     headers        │                  │
│             │     ✓ 密钥正确     │                  │
│             │                    │                  │
│             │  3. user_id =      │                  │
│             │     "internal-     │                  │
│             │      service"      │                  │
│             │                    │                  │
│             │  4. 跳过权限检查   │                  │
│             │                    │                  │
│             │  5. 返回组织数据   │                  │
│             │ <─────────────── │                  │
│             │  200 OK            │                  │
└─────────────┘                    └──────────────────┘
```

## 📝 完整示例

### 示例：Auth Service 调用 Organization Service

```python
# auth_service/main.py
from microservices.organization_service.client import OrganizationServiceClient

class AuthMicroservice:
    async def initialize(self):
        # 初始化organization客户端（自动使用内部认证）
        self.organization_client = OrganizationServiceClient()

    async def create_api_key(self, organization_id: str):
        # 验证组织是否存在
        org = await self.organization_client.get_organization(organization_id)
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        # 创建 API key
        ...
```

### 示例：Organization Service 接收内部调用

```python
# organization_service/main.py
from fastapi import Depends
from core.auth_dependencies import require_auth_or_internal_service

@app.get("/api/v1/organizations/{organization_id}")
async def get_organization(
    organization_id: str,
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    # user_id 可能是:
    # - "internal-service" (来自其他微服务)
    # - "user_123" (来自用户请求)

    return await service.get_organization(organization_id, user_id)
```

## 🧪 测试

### 单元测试

```python
import pytest
from core.auth_dependencies import is_internal_service_request

def test_internal_service_detection():
    assert is_internal_service_request("internal-service") == True
    assert is_internal_service_request("user_123") == False
```

### 集成测试

```python
from microservices.organization_service.client import OrganizationServiceClient

@pytest.mark.asyncio
async def test_internal_service_call():
    async with OrganizationServiceClient() as client:
        # 应该成功调用（即使没有用户认证）
        org = await client.get_organization("org_test_001")
        assert org is not None
```

## 📋 迁移检查清单

将现有服务迁移到统一认证架构：

### 服务端（API）

- [ ] 导入 `from core.auth_dependencies import require_auth_or_internal_service`
- [ ] 更新端点使用 `user_id: str = Depends(require_auth_or_internal_service)`
- [ ] 在 Service 层添加内部服务检查：`if user_id != "internal-service":`
- [ ] 测试用户调用和内部服务调用都能正常工作

### 客户端

- [ ] 继承 `BaseServiceClient`
- [ ] 定义 `service_name` 和 `default_port`
- [ ] 移除手动添加认证 headers 的代码
- [ ] 测试服务间调用

## 🔍 故障排查

### 问题：401 Unauthorized

**原因**：内部服务认证失败

**解决方案**：
1. 检查环境变量 `INTERNAL_SERVICE_SECRET` 是否一致
2. 确认客户端使用了 `BaseServiceClient` 或手动添加了认证headers
3. 检查服务端是否使用了 `require_auth_or_internal_service`

### 问题：403 Forbidden

**原因**：内部服务调用但仍然检查权限

**解决方案**：
1. 在 Service 层添加内部服务检查：
   ```python
   if user_id != "internal-service":
       # 检查权限
   ```
2. 确认 `require_auth_or_internal_service` 正确返回 `"internal-service"`

## 📊 测试结果

### JWT 测试
```
✅ Passed: 14/14
❌ Failed: 0/14
```

### API Key 测试
```
✅ Passed: 8/8
❌ Failed: 0/8
```

## 🎯 最佳实践

1. **始终使用 BaseServiceClient**：自动处理认证、服务发现、错误处理
2. **环境变量分离**：开发/测试/生产使用不同的密钥
3. **最小权限原则**：内部服务调用只绕过必要的权限检查
4. **日志记录**：记录所有内部服务调用以便审计
5. **超时设置**：为服务间调用设置合理的超时时间

## 📚 相关文档

- [服务发现配置](./service_discovery.md)
- [微服务架构设计](./microservices_architecture.md)
- [安全最佳实践](./security_best_practices.md)

---

**更新时间**: 2025-10-31
**作者**: isA User Platform Team
**版本**: 1.0.0
