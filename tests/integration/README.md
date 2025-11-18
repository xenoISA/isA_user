# 集成测试套件

完整的用户注册、设备注册和登录流程集成测试。

## 📋 测试覆盖范围

### 1. 用户注册流程测试
- ✅ 用户注册 (auth_service → account_service)
- ✅ 验证码发送 (notification_service)
- ✅ 注册验证
- ✅ JWT token 生成
- ✅ 事件发布验证 (`user.created`, `user.logged_in`)
- ✅ 数据库记录验证

### 2. 用户登录测试
- ✅ Token pair 生成 (access + refresh tokens)
- ✅ Token 验证
- ✅ 事件发布验证 (`user.logged_in`)

### 3. 设备注册流程测试
- ✅ 设备注册 (device_service)
- ✅ 设备凭证生成 (auth_service)
- ✅ 设备密钥管理
- ✅ 事件发布验证 (`device.registered`)
- ✅ 数据库记录验证

### 4. 设备认证测试
- ✅ 设备认证 (使用 device_id + device_secret)
- ✅ 设备 JWT token 生成
- ✅ Token 验证
- ✅ 事件发布验证 (`device.authenticated`)

### 5. 服务健康检查
- ✅ 所有微服务健康状态
- ✅ 基础设施服务 (PostgreSQL, NATS, Consul)
- ✅ 详细健康检查 (数据库连接、事件总线连接等)

### 6. 事件总线测试
- ✅ NATS JetStream 连接性
- ✅ 事件发布
- ✅ 事件订阅
- ✅ 事件传递验证

### 7. 数据库测试
- ✅ PostgreSQL 连接性
- ✅ 数据写入验证
- ✅ 数据查询验证
- ✅ 多数据库事务一致性

## 🚀 快速开始

### 前置条件

1. **基础设施服务运行中**:
   ```bash
   # PostgreSQL
   docker ps | grep postgres
   
   # NATS
   docker ps | grep nats
   
   # Consul
   docker ps | grep consul
   ```

2. **微服务运行中**:
   ```bash
   # auth_service (端口 8201)
   # account_service (端口 8202)
   # device_service (端口 8203)
   # notification_service (端口 8206) - 可选,用于验证码发送
   ```

3. **Python 依赖**:
   ```bash
   pip install httpx asyncpg
   ```

4. **系统工具**:
   ```bash
   # macOS
   brew install jq
   
   # 验证工具
   which python3 curl jq nc psql
   ```

### 运行所有集成测试

```bash
cd tests/integration
./run_integration_tests.sh
```

### 只运行 Python 集成测试

```bash
python3 test_user_device_registration_flow.py
```

### 只检查服务健康

```bash
./check_services_health.sh
```

详细健康检查:
```bash
CHECK_DETAILED=true ./check_services_health.sh
```

## 🔧 配置

### 环境变量

#### 服务地址配置
```bash
export AUTH_BASE_URL="http://localhost:8201"
export ACCOUNT_BASE_URL="http://localhost:8202"
export DEVICE_BASE_URL="http://localhost:8203"
export ORG_BASE_URL="http://localhost:8204"
```

#### 数据库配置
```bash
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="postgres"
```

#### NATS 配置
```bash
export NATS_URL="nats://localhost:4222"
```

#### 测试配置
```bash
# 跳过健康检查
export SKIP_HEALTH_CHECK=true

# 运行详细测试
export RUN_DETAILED_TESTS=true

# 验证码 (可选,用于自动化测试)
export VERIFICATION_CODE="123456"
```

## 📊 测试输出示例

### 成功输出
```
================================================================================
🚀 INTEGRATION TEST SUITE: User & Device Registration Flow
================================================================================
Timestamp: 2025-01-09T12:00:00.000000

Test Configuration:
  Auth Service: http://localhost:8201
  Account Service: http://localhost:8202
  Device Service: http://localhost:8203
  NATS URL: nats://localhost:4222
  PostgreSQL: localhost:5432

Test Email: test_a1b2c3d4@example.com

================================================================================
🔧 Setting up integration test environment...
================================================================================
✅ HTTP client created
✅ Connected to NATS event bus
✅ Subscribed to all events
✅ Connected to auth_db
✅ Connected to account_db
✅ Connected to device_db

================================================================================
TEST [1/8]: User Registration Flow
================================================================================

📝 Step 1: Starting registration...
  ✅ Registration returned pending_registration_id
  📋 Pending ID: abc123...

📝 Step 2: Getting verification code...
  ✅ Got verification code from dev endpoint
  🔑 Verification code: 123456

📝 Step 3: Verifying registration...
  ✅ Verification successful
  ✅ Verification returned user_id
  ✅ Verification returned access_token
  👤 User ID: usr_xyz789...
  🔐 Access Token: eyJhbGciOi...

📝 Step 4: Verifying events...
  📨 Event received: user.created from auth_service
  📨 Event received: user.logged_in from auth_service
  ✅ user.created event was published (1 events)
  ✅ user.logged_in event was published (1 events)

📝 Step 5: Verifying database records...
  ✅ User record exists in database
  ✅ User email matches: test_a1b2c3d4@example.com
  ✅ User name matches: Integration Test User

✅ TEST PASSED: User Registration Flow

... (更多测试) ...

================================================================================
📊 FINAL TEST SUMMARY
================================================================================

Total Tests: 8
Passed: 8 ✅
Failed: 0 ❌
Pass Rate: 100.0%

🎉 ALL TESTS PASSED!
✅ User registration, device registration, and login flows are working correctly

================================================================================
```

## 🐛 故障排查

### 问题 1: 服务健康检查失败

```bash
# 检查哪些服务未运行
./check_services_health.sh

# 检查服务日志
docker logs <service_container>

# 或者直接访问健康端点
curl http://localhost:8201/health
```

### 问题 2: 无法连接到 NATS

```bash
# 检查 NATS 是否运行
docker ps | grep nats
nc -z localhost 4222

# 查看 NATS 日志
docker logs nats
```

### 问题 3: 数据库连接失败

```bash
# 测试 PostgreSQL 连接
psql -h localhost -p 5432 -U postgres -d auth_db -c "SELECT 1"

# 检查数据库是否存在
psql -h localhost -p 5432 -U postgres -l
```

### 问题 4: 验证码无法获取

有两种方式获取验证码:

1. **使用 dev 端点** (推荐,仅在开发模式可用):
   ```bash
   # 测试会自动从 dev 端点获取
   ```

2. **手动输入**:
   ```bash
   # 查看 auth_service 日志中的验证码
   docker logs auth_service | grep "verification code"
   
   # 或设置环境变量
   export VERIFICATION_CODE="123456"
   ```

### 问题 5: 测试失败,需要重新运行

```bash
# 清理测试数据 (可选)
# 警告: 这会删除测试用户数据
psql -h localhost -U postgres -d account_db -c "DELETE FROM users WHERE email LIKE 'test_%@example.com'"
psql -h localhost -U postgres -d device_db -c "DELETE FROM devices WHERE device_name LIKE 'Integration Test%'"

# 重新运行测试
./run_integration_tests.sh
```

## 📁 文件结构

```
tests/integration/
├── README.md                                # 本文档
├── run_integration_tests.sh                 # 主测试运行脚本
├── check_services_health.sh                 # 服务健康检查脚本
├── test_user_device_registration_flow.py    # Python 集成测试
└── test_event_flows.py                      # 事件流测试

tests/logs/
└── integration_test_YYYYMMDD_HHMMSS.log    # 测试日志
```

## 🔍 测试详情

### Python 集成测试内容

**test_user_device_registration_flow.py** 包含 8 个测试:

1. **test_1_user_registration** - 用户注册完��流程
2. **test_2_user_login** - 用户登录和 token 生成
3. **test_3_device_registration** - 设备注册流程
4. **test_4_device_authentication** - 设备认证流程
5. **test_5_service_health_checks** - 所有服务健康检查
6. **test_6_event_bus_connectivity** - 事件总线连接性
7. **test_7_database_connectivity** - 数据库连接性
8. **test_8_end_to_end_cleanup** - 端到端清理验证

### 事件验证

测试会验证以下事件是否正确发布和订阅:

- `user.created` - 用户创建
- `user.logged_in` - 用户登录
- `user.profile_updated` - 用户资料更新
- `device.registered` - 设备注册
- `device.authenticated` - 设备认证
- `device.online` - 设备上线
- `device.offline` - 设备离线

### 数据库验证

测试会验证以下数据库中的记录:

- **auth_db**: 设备凭证表
- **account_db**: 用户表
- **device_db**: 设备表
- **organization_db**: 组织表 (如果使用组织)

## 📈 持续集成

### GitHub Actions 示例

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
          
      nats:
        image: nats:latest
        ports:
          - 4222:4222
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install httpx asyncpg
      
      - name: Start microservices
        run: |
          # 启动所有微服务
          docker-compose up -d
      
      - name: Run integration tests
        run: |
          cd tests/integration
          ./run_integration_tests.sh
```

## 🤝 贡献

如需添加新的测试用例:

1. 在 `test_user_device_registration_flow.py` 中添加新的测试方法
2. 遵循命名规范: `async def test_N_description(self):`
3. 使用 `self.assert_true()` 和 `self.assert_equal()` 进行断言
4. 更新测试计数器
5. 更新本 README 文档

## 📚 相关文档

- [用户注册流程文档](../../docs/user_registration_flow.md)
- [设备注册流程文档](../../docs/device_registration_flow.md)
- [事件驱动架构文档](../../docs/event_driven_architecture.md)
- [微服务架构概览](../../docs/microservices_architecture.md)

## 📞 支持

如遇到问题:

1. 查看测试日志: `tests/logs/integration_test_*.log`
2. 检查服务日志: `docker logs <service_name>`
3. 运行详细健康检查: `CHECK_DETAILED=true ./check_services_health.sh`
4. 查看本 README 的故障排查部分

---

最后更新: 2025-01-09
