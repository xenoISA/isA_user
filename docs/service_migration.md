# 微服务迁移指南 - Consul 服务注册与发现

本文档说明如何将微服务从硬编码连接迁移到使用 Consul 服务注册与发现的架构。

---

## 📋 迁移概览

### 完成的工作（以 auth_service 为例）

✅ **依赖更新**
- 升级 `isa-common` 到 0.1.8（支持 Consul meta 元数据）
- 更新 `config_manager` 支持服务发现

✅ **服务注册**
- 创建 `routes_registry.py` 集中管理路由定义
- 在服务启动时注册到 Consul
- 在服务关闭时从 Consul 注销

✅ **服务发现**
- Repositories 使用 `config_manager.discover_service()` 发现依赖服务
- 配置优先级：环境变量 → Consul → localhost fallback

---

## 🚀 迁移步骤

### 步骤 1: 创建路由注册表

为每个微服务创建 `routes_registry.py`，集中定义所有路由和元数据。

**文件位置**: `microservices/{service_name}/routes_registry.py`

```python
"""
{Service Name} Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# 定义所有路由
SERVICE_ROUTES = [
    {
        "path": "/",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Root health check"
    },
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check"
    },
    {
        "path": "/api/v1/{service}/endpoint",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "Main endpoint description"
    },
    # ... 添加所有路由
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    api_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]
        # 使用紧凑表示：只保留路径的关键部分
        compact_path = path.replace("/api/v1/{service}/", "")

        if path in ["/", "/health"]:
            health_routes.append(compact_path)
        else:
            api_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/{service}",
        "health": ",".join(health_routes),
        "api": ",".join(api_routes),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "{service_name}",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "{category}"],
    "capabilities": [
        "capability1",
        "capability2",
    ]
}
```

---

### 步骤 2: 更新 main.py - 添加 Consul 注册

在 `main.py` 中添加服务注册逻辑。

#### 2.1 导入依赖

```python
from isa_common.consul_client import ConsulRegistry
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
```

#### 2.2 在服务类中添加 consul_registry

```python
class {Service}Microservice:
    def __init__(self):
        # ... 其他初始化
        self.consul_registry: Optional[ConsulRegistry] = None
```

#### 2.3 在 initialize() 中注册服务

```python
async def initialize(self):
    try:
        logger.info("Initializing {service} microservice...")

        # Consul 服务注册
        if config.consul_enabled:
            try:
                # 获取路由元数据
                route_meta = get_routes_for_consul()

                # 合并服务元数据
                consul_meta = {
                    'version': SERVICE_METADATA['version'],
                    'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                    **route_meta
                }

                self.consul_registry = ConsulRegistry(
                    service_name=SERVICE_METADATA['service_name'],
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port,
                    tags=SERVICE_METADATA['tags'],
                    meta=consul_meta,
                    health_check_type='http'
                )
                self.consul_registry.register()
                logger.info(f"Service registered with Consul: {len(route_meta.get('all_routes', '').split('|'))} routes")
            except Exception as e:
                logger.warning(f"Failed to register with Consul: {e}")
                self.consul_registry = None

        # ... 其他初始化逻辑
```

#### 2.4 在 shutdown() 中注销服务

```python
async def shutdown(self):
    # Consul 注销
    if self.consul_registry:
        try:
            self.consul_registry.deregister()
            logger.info("Service deregistered from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister from Consul: {e}")

    # ... 其他清理逻辑
```

---

### 步骤 3: 更新 Repositories - 使用服务发现

将硬编码的连接信息改为使用 `config_manager.discover_service()`。

#### 3.1 导入 ConfigManager

```python
from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager
```

#### 3.2 更新 Repository 构造函数

**迁移前（硬编码）：**
```python
class MyRepository:
    def __init__(self):
        self.db = PostgresClient(
            host='isa-postgres-grpc',
            port=50061,
            user_id='my-service'
        )
```

**迁移后（服务发现）：**
```python
class MyRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("my_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(host=host, port=port, user_id='my-service')
```

#### 3.3 更新 main.py 中的 Repository 初始化

```python
# 在 initialize() 方法中
self.my_repository = MyRepository(config=config_manager)
```

---

### 步骤 4: 常见服务的服务发现配置

#### PostgreSQL (gRPC)
```python
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061,
    env_host_key='POSTGRES_HOST',
    env_port_key='POSTGRES_PORT'
)
```

#### Redis (gRPC)
```python
host, port = config.discover_service(
    service_name='redis_grpc_service',
    default_host='isa-redis-grpc',
    default_port=50052,
    env_host_key='REDIS_HOST',
    env_port_key='REDIS_PORT'
)
```

#### NATS
```python
host, port = config.discover_service(
    service_name='nats_grpc_service',
    default_host='isa-nats-grpc',
    default_port=50053,
    env_host_key='NATS_HOST',
    env_port_key='NATS_PORT'
)
```

#### MinIO (gRPC)
```python
host, port = config.discover_service(
    service_name='minio_grpc_service',
    default_host='isa-minio-grpc',
    default_port=50051,
    env_host_key='MINIO_HOST',
    env_port_key='MINIO_PORT'
)
```

#### 其他微服务（如 account_service）
```python
host, port = config.discover_service(
    service_name='account_service',
    default_host='localhost',
    default_port=8202,
    env_host_key='ACCOUNT_SERVICE_HOST',
    env_port_key='ACCOUNT_SERVICE_PORT'
)
```

---

## 🎯 配置优先级

服务发现使用以下优先级（从高到低）：

### 1️⃣ 环境变量（最高优先级）
```bash
# .env.staging
POSTGRES_HOST=custom-postgres-host
POSTGRES_PORT=5432
```

### 2️⃣ Consul 服务发现
```python
# 从 Consul 自动发现服务
# 返回已注册的健康服务实例
```

### 3️⃣ Localhost Fallback（默认值）
```python
# 如果环境变量和 Consul 都没有，使用默认值
default_host='localhost'
default_port=8080
```

---

## ✅ 验证清单

迁移完成后，检查以下项目：

- [ ] 服务在 Consul 中成功注册
  ```bash
  python3 -c "
  from isa_common.consul_client import ConsulRegistry
  consul = ConsulRegistry(consul_host='localhost', consul_port=8500)
  instances = consul.discover_service('your_service_name')
  print(f'Found {len(instances)} instances')
  for inst in instances:
      print(f'  - {inst[\"address\"]}:{inst[\"port\"]}')
      print(f'  - Routes: {inst[\"meta\"].get(\"route_count\")}')
  "
  ```

- [ ] 服务能够发现依赖的基础设施服务
  ```bash
  # 查看服务日志，确认显示：
  # "Service postgres_grpc_service discovered via Consul: xxx:xxx"
  # 或
  # "Service postgres_grpc_service from env: xxx:xxx"
  ```

- [ ] 所有现有测试通过
  ```bash
  cd /Users/xenodennis/Documents/Fun/isA_user
  python3 tests/test_nats_events.py
  python3 tests/test_minio_client.py
  ```

- [ ] 服务健康检查正常
  ```bash
  curl http://localhost:8201/health
  ```

- [ ] 路由元数据正确注册到 Consul
  ```python
  # 验证 meta 字段包含：
  # - route_count
  # - base_path
  # - health, api, device 等路由分类
  # - version, capabilities
  ```

---

## 📝 注意事项

### Consul Meta 字段限制
- 每个 meta 字段值限制为 **512 字符**
- 如果路由过多，需要分类压缩（参考 auth_service 的实现）
- 使用紧凑表示法（移除重复的路径前缀）

### 服务命名规范
- 基础设施服务：`{service}_grpc_service`（如 `postgres_grpc_service`）
- 用户微服务：`{service}_service`（如 `auth_service`, `account_service`）

### 环境变量命名
- 主机：`{SERVICE}_HOST`（如 `POSTGRES_HOST`）
- 端口：`{SERVICE}_PORT`（如 `POSTGRES_PORT`）

### 健康检查
- 默认使用 HTTP 健康检查
- 确保服务提供 `/health` 端点
- Consul 会定期检查服务健康状态

---

## 🔧 故障排查

### 问题 1: 服务未在 Consul 中注册
**检查**:
```python
# 1. 检查 Consul 连接
consul_host = os.getenv('CONSUL_HOST', 'localhost')
consul_port = int(os.getenv('CONSUL_PORT', 8500))

# 2. 检查 consul_enabled 配置
config.consul_enabled  # 应该为 True

# 3. 查看服务启动日志
# 应该看到: "Service registered with Consul: ..."
```

### 问题 2: Meta 字段过长错误
**错误信息**: `Value is too long (limit: 512 characters)`

**解决方案**:
- 使用紧凑路径表示（去除 `/api/v1/service/` 前缀）
- 将路由分类到不同的 meta 字段（health, api, device 等）
- 参考 `auth_service/routes_registry.py` 的实现

### 问题 3: 服务发现返回 localhost
**原因**: Consul 中未找到服务，使用了 fallback

**检查**:
```python
# 1. 确认服务名称正确
service_name='postgres_grpc_service'  # 不是 'postgres' 或 'postgres_service'

# 2. 确认服务已注册到 Consul
consul.discover_service('postgres_grpc_service')

# 3. 检查日志
# 应该看到: "Service xxx discovered via Consul: ..."
# 而不是: "Service xxx using fallback: ..."
```

---

## ⚠️ 常见问题和陷阱

### 问题 1: Service 类未传入 config_manager

**症状**:
- API 返回 `503 Service discovery not available`
- 数据库连接失败，显示使用了错误的 host/port

**原因**:
Service 类在 `__init__` 中直接创建 Repository，没有传入 `config_manager`

```python
# ❌ 错误示例
class MyService:
    def __init__(self, event_bus=None):
        self.repository = MyRepository()  # 没有传入 config_manager
```

**解决方案**:
```python
# ✅ 正确示例
class MyService:
    def __init__(self, event_bus=None, config_manager: Optional[ConfigManager] = None):
        self.repository = MyRepository(config=config_manager)
        self.config_manager = config_manager if config_manager else ConfigManager("my_service")

# main.py 中传入 config_manager
service = MyService(event_bus=event_bus, config_manager=config_manager)
```

---

### 问题 2: 使用了旧的服务发现方式

**症状**:
- 代码检查 `app.state.consul_registry` 或 `hasattr(app.state, 'consul_registry')`
- 使用 `consul_registry.get_service_endpoint()`
- 依赖函数返回 `503 Service discovery not available`

**原因**:
使用了旧的 Consul 客户端 API，而不是统一的 `config_manager.discover_service()`

```python
# ❌ 错误示例
async def get_user_context():
    if not hasattr(app.state, 'consul_registry'):
        raise HTTPException(status_code=503, detail="Service discovery not available")

    auth_url = app.state.consul_registry.get_service_endpoint("auth_service")
```

**解决方案**:
```python
# ✅ 正确示例
async def get_user_context():
    # 使用 config_manager 进行服务发现
    auth_host, auth_port = config_manager.discover_service(
        service_name='auth_service',
        default_host='localhost',
        default_port=8201,
        env_host_key='AUTH_SERVICE_HOST',
        env_port_key='AUTH_SERVICE_PORT'
    )
    auth_url = f"http://{auth_host}:{auth_port}"
```

---

### 问题 3: 导入了不需要的旧模块

**症状**:
```python
from core.service_discovery import get_service_discovery
```

**解决方案**:
删除旧的服务发现导入，只保留必要的：
```python
# ✅ 只需要这些
from isa_common.consul_client import ConsulRegistry
from core.config_manager import ConfigManager
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
```

---

### 问题 4: FastAPI 依赖函数中的服务发现

**场景**: 在 FastAPI 的 `Depends` 依赖函数中调用其他微服务

**错误模式**:
```python
# ❌ 错误：检查 app.state
async def get_user_context(authorization: str = Header(None)):
    if not hasattr(app.state, 'consul_registry'):
        raise HTTPException(status_code=503, detail="Service discovery not available")
```

**正确模式**:
```python
# ✅ 正确：使用 config_manager
async def get_user_context(authorization: str = Header(None)):
    # 直接使用全局 config_manager 进行服务发现
    auth_host, auth_port = config_manager.discover_service(
        service_name='auth_service',
        default_host='localhost',
        default_port=8201,
        env_host_key='AUTH_SERVICE_HOST',
        env_port_key='AUTH_SERVICE_PORT'
    )

    # 调用服务
    response = requests.post(f"http://{auth_host}:{auth_port}/api/v1/auth/verify-token", ...)
```

---

### 问题 5: Client 调用其他微服务时未使用服务发现

**场景**: Service 类中需要调用其他微服务（如 account_service, notification_service）

**错误模式**:
```python
# ❌ 错误：硬编码 URL
class MyService:
    def __init__(self):
        self.account_url = "http://localhost:8202"
```

**正确模式**:
```python
# ✅ 正确：使用 config_manager 发现服务
class MyService:
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager if config_manager else ConfigManager("my_service")

    async def call_account_service(self, user_id: str):
        # 每次调用时使用服务发现（或缓存）
        account_host, account_port = self.config_manager.discover_service(
            service_name='account_service',
            default_host='localhost',
            default_port=8202,
            env_host_key='ACCOUNT_SERVICE_HOST',
            env_port_key='ACCOUNT_SERVICE_PORT'
        )

        response = await self.http_client.get(
            f"http://{account_host}:{account_port}/api/v1/accounts/{user_id}"
        )
        return response.json()
```

---

### 验证迁移是否正确

迁移完成后，检查以下几点：

1. **代码搜索检查**:
   ```bash
   # 搜索旧的服务发现模式
   grep -r "app.state.consul_registry" microservices/your_service/
   grep -r "get_service_discovery" microservices/your_service/
   grep -r "service_discovery.get" microservices/your_service/

   # 应该返回空结果
   ```

2. **日志检查**:
   ```bash
   docker logs user-staging 2>&1 | grep "your_service" | grep -i "consul\|postgresql"

   # 应该看到:
   # ✅ Connecting to PostgreSQL at isa-postgres-grpc:50061
   # ✅ Service registered with Consul: XX routes
   ```

3. **运行测试**:
   ```bash
   bash microservices/your_service/tests/your_test.sh

   # 所有测试应该通过，不应该看到 "Service discovery not available"
   ```

4. **API 测试**:
   ```bash
   # 测试需要认证的端点
   curl -X POST http://localhost:YOUR_PORT/api/v1/your-endpoint \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{...}'

   # 应该返回正常响应，不是 503 错误
   ```

---

## 📚 相关文档

- [isa-common Consul 客户端使用指南](../../../isA_Cloud/how_to_consul.md)
- [ConfigManager 文档](../core/config_manager.py)
- [Routes Registry 示例](../microservices/auth_service/routes_registry.py)

---

## 🎉 完成示例

参考已完成迁移的服务：
- ✅ **auth_service** - 完整实现了服务注册与发现
  - 路由注册：22 个端点
  - 服务发现：PostgreSQL
  - 微服务调用：organization_service

- ✅ **task_service** - 修复了所有常见陷阱
  - 15 个路由全部通过测试
  - 正确使用 config_manager 进行服务发现
  - 依赖函数中正确调用 auth_service

---

*Last Updated: 2025-11-07*
*Author: isA Platform Team*
