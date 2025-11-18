# Test Data Standardization

## 目的
统一所有微服务的测试数据 ID 格式，确保跨服务引用的一致性。

## 标准 ID 格式

### 用户 (Users)
```
test_user_001  - Alice (alice@example.com) - 个人用户，免费计划
test_user_002  - Bob (bob@example.com) - 个人用户，基础计划
test_user_003  - Charlie (charlie@example.com) - 企业用户，专业计划
test_user_004  - Diana (diana@example.com) - 非活跃用户
```

### 组织 (Organizations)
```
test_org_001   - Test Organization Alpha - 小型团队 (owner: test_user_001)
test_org_002   - Test Organization Beta - 中型团队 (owner: test_user_002)
test_org_003   - Test Organization Gamma - 企业团队 (owner: test_user_003)
```

### 设备 (Devices)
```
test_device_001 - Smart Frame Living Room (org: test_org_001, user: test_user_001)
test_device_002 - Smart Frame Bedroom (org: test_org_001, user: test_user_001)
test_device_003 - Mobile Device iPhone (org: test_org_002, user: test_user_002)
test_device_004 - IoT Sensor Kitchen (user: test_user_001)
test_device_005 - Security Camera (org: test_org_002, user: test_user_002)
```

### 钱包 (Wallets)
```
test_wallet_001 - test_user_001 个人钱包 (余额: $1000)
test_wallet_002 - test_user_002 个人钱包 (余额: $500)
test_wallet_003 - test_org_001 组织钱包 (余额: $5000)
```

### 订阅计划 (Subscription Plans)
```
plan_free       - 免费计划
plan_basic      - 基础计划 ($9.99/月)
plan_pro        - 专业计划 ($29.99/月)
plan_enterprise - 企业计划 ($99.99/月)
```

### 产品 (Products)
```
product_test_001 - AI Model Credits
product_test_002 - Storage Expansion
product_test_003 - Premium Features
```

### 其他资源
```
test_album_001    - 家庭相册
test_file_001     - vacation_photo.jpg
test_task_001     - 日常任务
test_session_001  - AI 会话
```

## 跨服务依赖关系

### 核心依赖
```
account_service (用户) 
  ↓
auth_service (认证)
  ↓
organization_service (组织) → device_service (设备)
  ↓
wallet_service (钱包) → payment_service (支付)
  ↓
billing_service (计费)
```

### Seed 执行顺序
1. **account_service** - 创建用户
2. **auth_service** - 用户认证数据
3. **authorization_service** - 权限配置
4. **organization_service** - 组织和成员
5. **device_service** - 设备
6. **wallet_service** - 钱包
7. **payment_service** - 支付和订阅
8. **product_service** - 产品目录
9. **其他服务** - 按需

## 命名规则

### DO ✅
- 使用下划线分隔: `test_user_001`
- 使用三位数字: `001`, `002`, `003`
- 保持一致的前缀: `test_`, `plan_`, `product_`
- 使用描述性名称: `alice@example.com`

### DON'T ❌
- 不使用连字符: ~~`test-user-1`~~
- 不使用不规则数字: ~~`user_test_01`~~
- 不混用格式: ~~`test_user_1`, `test-user-002`~~
- 不使用真实邮箱: ~~`@testorg.com`~~

## 邮箱域名
统一使用: `@example.com`

## 测试数据特点
- 所有测试数据 ID 以 `test_` 开头
- 便于识别和清理
- 不影响生产数据
- ON CONFLICT DO NOTHING 保证幂等性
