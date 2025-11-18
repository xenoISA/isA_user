# 家庭共享功能开发指南

## 概述

家庭共享功能允许组织内成员共享各种资源，包括订阅、设备、存储、钱包等。

## 系统模块

### 核心组件

1. **数据模型** (`family_sharing_models.py`)
   - 支持共享资源类型：subscription, device, storage, wallet, media_library, calendar, shopping_list, location
   - 权限级别分类：owner, admin, full_access, read_write, read_only, limited, view_only
   - 配额和限制管理
   - 特定资源配置模型：SubscriptionSharingSettings, DeviceSharingSettings 等

2. **数据访问层** (`family_sharing_repository.py`)
   - 共享资源 CRUD 操作
   - 添加成员权限
   - 查询成员共享资源
   - 使用统计查询

3. **业务逻辑层** (`family_sharing_service.py`)
   - 创建共享资源
   - 更新共享配置
   - 删除共享
   - 撤销共享
   - 添加成员权限
   - 查询成员共享资源
   - 使用统计分析

4. **数据库表结构**
   - `family_sharing_resources` - 共享资源表
   - `family_sharing_member_permissions` - 成员权限表
   - `family_sharing_usage_stats` - 使用统计表
   - 核心配置：唯一约束、外键关系等

5. **API Endpoints** (`main.py`)
   ```
   POST   /api/v1/organizations/{organization_id}/sharing
   GET    /api/v1/organizations/{organization_id}/sharing/{sharing_id}
   PUT    /api/v1/organizations/{organization_id}/sharing/{sharing_id}
   DELETE /api/v1/organizations/{organization_id}/sharing/{sharing_id}
   GET    /api/v1/organizations/{organization_id}/sharing
   PUT    /api/v1/organizations/{organization_id}/sharing/{sharing_id}/members
   DELETE /api/v1/organizations/{organization_id}/sharing/{sharing_id}/members/{member_user_id}
   GET    /api/v1/organizations/{organization_id}/members/{member_user_id}/shared-resources
   GET    /api/v1/organizations/{organization_id}/sharing/{sharing_id}/usage
   ```

### 核心测试流程

```bash
# 1. 创建组织
python -c "
import requests
response = requests.post(
    'http://localhost:8212/api/v1/organizations',
    headers={'X-User-Id': 'test-user-001', 'Content-Type': 'application/json'},
    json={'name': 'TestFamily', 'display_name': '测试家庭', 'billing_email': 'family@test.com'}
)
print(response.json())
"

# 2. 添加成员
python -c "
import requests
response = requests.post(
    'http://localhost:8212/api/v1/organizations/org_xxx/members',
    headers={'X-User-Id': 'test-user-001', 'Content-Type': 'application/json'},
    json={'user_id': 'test-user-002', 'role': 'member'}
)
print(response.json())
"

# 3. 创建设备共享
python -c "
import requests
import time
response = requests.post(
    'http://localhost:8212/api/v1/organizations/org_xxx/sharing',
    headers={'X-User-Id': 'test-user-001', 'Content-Type': 'application/json'},
    json={
        'resource_type': 'device',
        'resource_id': 'device_' + str(int(time.time())),
        'resource_name': '智能音箱',
        'share_with_all_members': False,
        'default_permission': 'full_access',
        'restrictions': {'location': 'living_room'},
        'metadata': {'device_type': 'smart_speaker'}
    }
)
print(response.json())
"
```

### 待完成功能清单

#### 1. Service 层待实现

当前 `FamilySharingService` 中待实现的方法：

```python
async def list_organization_sharings(
    self,
    organization_id: str,
    user_id: str,
    resource_type: Optional[SharingResourceType] = None,
    status: Optional[SharingStatus] = None,
    limit: int = 50,
    offset: int = 0
) -> List[SharingResourceResponse]:
    """列出组织的所有共享资源"""
    # TODO: 实现此方法
    pass
```

**位置**: `microservices/organization_service/family_sharing_service.py`

**实现步骤**:
1. 验证用户是否有组织管理员权限
2. 调用 `self.repository.list_organization_sharings()`
3. 转换为响应模型

#### 2. 创建共享时自动授予创建者权限

**问题**: 创建共享资源时，创建者没有被自动授予 owner 权限，导致之后无法访问自己创建的共享

**修改位置**: `family_sharing_service.py` - `create_sharing()` 方法

**修改方案**:
```python
async def create_sharing(...):
    # ... 现有代码 ...

    # 先创建数据库记录
    sharing = await self.repository.create_sharing(sharing_data)

    # 新增: 自动授予创建者 owner 权限
    await self._grant_member_permission(
        sharing_id,
        created_by,
        SharingPermissionLevel.OWNER,
        request.quota_settings
    )

    # 然后处理其他共享成员...
    if request.shared_with_members:
        # ... 现有代码 ...
```

#### 3. 权限检查逻辑优化

**问题**: `_check_sharing_access()` 当前只检查成员权限表，没有考虑创建者自动拥有访问权限

**修改位置**: `family_sharing_service.py` - `_check_sharing_access()` 方法

**修改方案**:
```python
async def _check_sharing_access(self, sharing_id: str, user_id: str) -> bool:
    """验证用户是否有权限访问共享资源"""
    # 检查用户是否是创建者
    sharing = await self.repository.get_sharing(sharing_id)
    if sharing and sharing.get('created_by') == user_id:
        return True

    # 检查是否有成员权限表记录
    permission = await self.repository.get_member_permission(sharing_id, user_id)
    return permission is not None
```

#### 4. Repository 层待实现

当前 `FamilySharingRepository` 中使用到但可能需要完善的方法：

```python
async def get_sharing_member_permissions(self, sharing_id: str) -> List[Dict[str, Any]]:
    """获取共享的所有成员权限（在 _sync_member_permissions 中使用）"""
    # TODO: 在 repository 中实现此方法: list_sharing_members，然后在 service 中调用此方法
    pass
```

#### 5. 使用统计功能

**位置**: `family_sharing_service.py` - `get_sharing_usage_stats()` 方法

说明: TODO 标记，需要集成其他服务的数据：
- Storage Service - 存储使用量
- Wallet Service - 钱包余额和交易
- Device Service - 设备使用量

#### 6. 数据序列化问题修复（已完成）

**已解决**:
- `datetime` 对象需要使用 `.isoformat()` 转换
- `Enum` 对象需要使用 `.value` 提取字符串值

**已修复位置**:
- `create_sharing()` - 核心方法
- `_grant_member_permission()` - 核心方法
- `update_sharing()` - 待确认是否完整
- `update_member_permission()` - 待确认是否完整

## 数据库 Migration

```bash
# 执行 Migration
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres \
  -f microservices/organization_service/migrations/002_create_family_sharing_tables.sql
```

## 架构设计

### 数据流程

```
Client Request
    ↓
API Endpoint (main.py)
    ↓
Service Layer (family_sharing_service.py)
    ↓
Repository Layer (family_sharing_repository.py)
    ↓
Database (Supabase - dev schema)
```

### 权限模型

1. **Owner** (创建者)
   - 完全控制
   - 可以删除共享
   - 可以修改所有配置

2. **Admin**
   - 可以管理成员权限
   - 可以修改部分配置
   - 不能删除共享

3. **Full Access**
   - 可以完全使用资源
   - 不可以管理权限

4. **Read Write**
   - 可以读写资源
   - 有限制条件

5. **Read Only**
   - 只能读取
   - 不可以修改

6. **Limited**
   - 受限的条件
   - 需要审批流程

7. **View Only**
   - 仅查看，无其他权限

### 配额管理

支持的配额周期类型：
- `unlimited` - 无限制
- `daily` - 每日配额
- `weekly` - 每周配额
- `monthly` - 每月配额
- `total` - 总配额

## 常见问题

### 典型错误

1. **重复创建共享**
   ```
   duplicate key value violates unique constraint
   "family_sharing_resources_organization_id_resource_type_reso_key"
   ```
   - 原因：在同一组织中，同一资源类型+资源ID 只能创建一个共享
   - 解决方案：更换 resource_id 或者先删除现有的共享

2. **外键约束违反**
   ```
   violates foreign key constraint "fk_permission_user"
   Key (user_id)=(xxx) is not present in table "users"
   ```
   - 原因：共享给的用户ID不存在于用户表
   - 解决方案：确保用户存在于 users 表中，或者使用 `share_with_all_members=False`

3. **权限不足错误**
   ```
   User xxx does not have access to sharing yyy
   ```
   - 原因：用户没有该共享的访问权限表记录
   - 解决方案：需要先授予创建者权限（参考待修复项）

## 开发优先级

### 优先级 P0（必须修复）

1. 核心 自动授予创建者 owner 权限
2. 核心 实现 `list_organization_sharings()` 方法
3. 核心 优化权限检查逻辑（考虑创建者）

### 优先级 P1（重要功能）

1. 完善使用统计功能
2. 实现配额检查和限制
3. 实现共享过期自动处理
4. 实现成员通知（当被共享资源时）

### 优先级 P2（高级功能）

1. 共享审批流程（require_approval_above）
2. 配额使用限制（time_restrictions）
3. 位置限制检查（location）
4. 批量操作支持
5. 共享模板功能

## 文件结构

```
microservices/organization_service/
├── family_sharing_models.py          # 数据模型
├── family_sharing_repository.py      # 数据访问层
├── family_sharing_service.py         # 业务逻辑层
├── main.py                           # API endpoints
└── migrations/
    └── 002_create_family_sharing_tables.sql  # 数据库表结构
```

## 测试进度

### 基本功能测试

- [x] 创建组织
- [x] 添加成员
- [x] 创建共享（设备）
- [ ] 列出共享
- [ ] 更新共享配置
- [ ] 删除共享
- [ ] 撤销共享
- [ ] 添加成员权限
- [ ] 移除成员权限
- [ ] 查询成员共享资源
- [ ] 查询使用统计

### 权限测试

- [ ] 创建者自动获得创建共享
- [ ] 管理员可以管理共享
- [ ] 普通成员只能使用共享
- [ ] 不同权限级别的配额测试

### 配额测试

- [ ] 每日配额限制
- [ ] 总配额限制
- [ ] 配额用量统计

### 错误处理测试

- [ ] 重复创建共享
- [ ] 共享给不存在的用户
- [ ] 共享给不存在的组织
- [ ] 超出配额使用限制

## 注意事项

1. **数据库 Schema**: 使用 `dev` schema，确保环境变量 `DB_SCHEMA=dev`
2. **用户外键**: 创建成员权限时，确保用户存在于 `dev.users` 表中
3. **Enum 序列化**: 所有 Enum 值需要使用 `.value` 转换为字符串
4. **DateTime 序列化**: 所有 datetime 对象需要使用 `.isoformat()` 转换
5. **唯一约束**: 在组织中，(resource_type, resource_id) 组合唯一

## 参考资料

- [Supabase 本地开发](https://supabase.com/docs/guides/cli/local-development)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 模型](https://docs.pydantic.dev/)

---

**最后更新**: 2025-10-04
**状态**: 开发中 - 基础功能已完成，待优化
**维护者**: Claude Code
