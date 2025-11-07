# isA User Microservices - 测试套件

## 📋 概述

统一测试运行器脚本，可以自动发现并运行所有27个微服务的测试。

## 🚀 快速开始

### 运行所有测试

```bash
cd /Users/xenodennis/Documents/Fun/isA_user
./tests/run_all_microservices_tests.sh
```

### 只测试特定服务

```bash
./tests/run_all_microservices_tests.sh --service auth_service
```

### 遇到失败立即停止

```bash
./tests/run_all_microservices_tests.sh --stop-on-fail
```

### 显示详细输出

```bash
./tests/run_all_microservices_tests.sh --verbose
```

## 📊 服务测试覆盖

| 服务 | 测试脚本数 | 说明 |
|------|-----------|------|
| auth_service | 4 | JWT, API Key, Device Auth, Registration |
| account_service | 1 | Account management |
| audit_service | 1 | Audit logging |
| authorization_service | 1 | Permission control |
| billing_service | 1 | Billing operations |
| calendar_service | 1 | Calendar events |
| compliance_service | 3 | GDPR, PCI-DSS checks |
| device_service | 3 | Device management & commands |
| event_service | 1 | Event management |
| invitation_service | 1 | Invitation flow |
| location_service | 1 | Location tracking |
| media_service | 2 | Photo versions & galleries |
| memory_service | 7 | All memory types |
| notification_service | 1 | Notifications |
| order_service | 1 | Order processing |
| organization_service | 1 | Organization management |
| ota_service | 1 | Firmware updates |
| payment_service | 1 | Payment processing |
| product_service | 1 | Product catalog |
| session_service | 1 | Session management |
| storage_service | 4 | File operations & intelligence |
| task_service | 1 | Task management |
| telemetry_service | 1 | Telemetry data |
| vault_service | 1 | Secret management |
| wallet_service | 1 | Wallet operations |
| weather_service | 1 | Weather data |
| album_service | 1 | Album management |

**总计**: ~51个测试脚本

## 🎯 功能特性

### 1. 自动发现测试
- 自动扫描所有微服务的 `tests/` 目录
- 排除辅助脚本 (debug_*, run_all_tests.sh)
- 按字母顺序执行

### 2. 详细的测试报告
- 实时显示测试进度
- 彩色输出，易于识别
- 生成摘要日志文件

### 3. 日志管理
- 每次运行生成时间戳标记的日志
- 日志保存在 `tests/logs/` 目录
- 失败时显示最后5行日志

### 4. 灵活的选项
```bash
--service <name>    # 只运行指定服务
--stop-on-fail      # 遇到失败立即停止
--parallel          # 并行运行(实验性)
--verbose, -v       # 显示详细输出
--help, -h          # 显示帮助
```

## 📁 输出结构

```
tests/
├── run_all_microservices_tests.sh    # 主测试运行器
├── README.md                          # 本文档
└── logs/                              # 测试日志目录
    ├── test_summary_20251107_120000.log
    ├── auth_service_jwt_auth_test_20251107_120000.log
    └── ...
```

## 🔍 示例输出

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  isA User Microservices - 测试运行器
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

开始时间: 2025-11-07 12:00:00
项目路径: /Users/xenodennis/Documents/Fun/isA_user
日志目录: /Users/xenodennis/Documents/Fun/isA_user/tests/logs

ℹ️  发现 27 个微服务

╔════════════════════════════════════════════════════════════╗
║  📦 Service: auth_service
║  📝 Tests: 4
╚════════════════════════════════════════════════════════════╝

▶ Running: jwt_auth_test
✅ PASSED: jwt_auth_test
▶ Running: api_key_test
✅ PASSED: api_key_test
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  测试报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

统计信息:
  测试的服务数: 27
  测试脚本总数: 51
  通过的测试:   48
  失败的测试:   3
  跳过的测试:   0
  成功率:       94.12%

结束时间: 2025-11-07 12:05:00
摘要日志: tests/logs/test_summary_20251107_120000.log

✅ 所有测试通过! 🎉
```

## 🛠️ 故障排查

### 测试失败时
1. 查看详细日志: `tests/logs/<service>_<test>_<timestamp>.log`
2. 使用 `--verbose` 模式查看实时输出
3. 单独运行失败的测试进行调试

### 服务未启动
确保 Docker 容器正在运行:
```bash
docker ps | grep user-staging
```

### 端口冲突
检查测试脚本中的端口配置是否与实际部署匹配。

## 📝 添加新测试

1. 在服务的 `tests/` 目录创建新的 `.sh` 文件
2. 添加可执行权限: `chmod +x your_test.sh`
3. 运行器会自动发现新测试

## 🎨 最佳实践

### 测试脚本结构
```bash
#!/bin/bash

# 配置
BASE_URL="http://localhost:8201"
API_BASE="${BASE_URL}/api/v1/your-service"

# 测试计数
TESTS_PASSED=0
TESTS_FAILED=0

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# 测试函数
test_something() {
    # 测试逻辑
    if [ condition ]; then
        echo -e "${GREEN}✅ Test passed${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ Test failed${NC}"
        ((TESTS_FAILED++))
    fi
}

# 运行测试
test_something

# 退出码
[ $TESTS_FAILED -eq 0 ] && exit 0 || exit 1
```

## 🔗 相关文档

- [服务迁移指南](../docs/service_migration.md)
- [Consul 注册检查报告](../docs/consul_registration_check_report.md)
- [架构文档](../docs/)

---

**版本**: 1.0.0
**更新时间**: 2025-11-07
**维护者**: isA Platform Team
