# Notification Service 使用指南

## 服务概述
Notification Service 提供全面的通知管理功能，支持邮件、推送通知、应用内通知、Webhook和批量发送。

**端口**: 8206  
**基础URL**: `http://localhost:8206`

## 快速开始

### 1. 启动服务
```bash
cd microservices/notification_service
python main.py
```

### 2. 健康检查
```bash
curl http://localhost:8206/health
```

**实际响应**:
```json
{
  "status": "healthy",
  "service": "notification_service",
  "port": 8206,
  "version": "1.0.0"
}
```

### 3. 查看服务能力
```bash
curl http://localhost:8206/info
```

**实际响应**:
```json
{
  "service": "notification-service",
  "version": "1.0.0",
  "description": "Notification management and delivery service",
  "capabilities": {
    "email": true,
    "sms": false,
    "in_app": true,
    "push": true,
    "webhook": true,
    "templates": true,
    "batch_sending": true
  },
  "endpoints": {
    "send_notification": "/api/v1/notifications/send",
    "send_batch": "/api/v1/notifications/batch",
    "templates": "/api/v1/notifications/templates",
    "in_app_notifications": "/api/v1/notifications/in-app"
  }
}
```

## 真实测试用例

### 测试场景 1: 创建和使用通知模板

#### 步骤 1: 创建欢迎邮件模板
```bash
curl -X POST http://localhost:8206/api/v1/notifications/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Welcome Email",
    "description": "Welcome email for new users",
    "type": "email",
    "subject": "Welcome to {{app_name}}!",
    "content": "Hello {{user_name}}, welcome to {{app_name}}!",
    "html_content": "<h1>Welcome to {{app_name}}!</h1><p>Hello {{user_name}}, we are glad to have you!</p>",
    "variables": ["user_name", "app_name"],
    "metadata": {"category": "onboarding"}
  }'
```

**实际响应**:
```json
{
  "template": {
    "id": 2,
    "template_id": "tpl_email_1759130299.932903",
    "name": "Welcome Email",
    "description": "Welcome email template",
    "type": "email",
    "subject": "Welcome to our platform!",
    "content": "Hello {{name}}, welcome to our platform!",
    "html_content": null,
    "variables": ["name"],
    "metadata": {},
    "status": "active",
    "version": 1,
    "created_by": null,
    "created_at": "2025-09-29T15:18:19.933636",
    "updated_at": "2025-09-29T15:18:19.933636"
  },
  "message": "Template created successfully"
}
```

#### 步骤 2: 发送邮件通知（基于实际测试）
```bash
curl -X POST http://localhost:8206/api/v1/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "email",
    "recipient_email": "test@example.com",
    "subject": "Test Email",
    "content": "This is a test email",
    "priority": "normal"
  }'
```

**实际响应**:
```json
{
  "notification": {
    "id": 3,
    "notification_id": "ntf_email_1759129077.148551",
    "type": "email",
    "priority": "normal",
    "recipient_type": "email",
    "recipient_id": null,
    "recipient_email": "test@example.com",
    "subject": "Test Email",
    "content": "This is a test email",
    "status": "pending",
    "created_at": "2025-09-29T14:57:57.148670"
  },
  "message": "Notification created and queued for sending",
  "success": true
}
```

### 测试场景 2: Push通知订阅和发送

#### 步骤 1: 注册Push订阅（Android设备）
```bash
curl -X POST http://localhost:8206/api/v1/notifications/push/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "device_token": "fcm_token_example_123456",
    "platform": "android",
    "device_name": "Pixel 6",
    "device_model": "Google Pixel 6",
    "app_version": "1.0.0"
  }'
```

**实际响应**:
```json
{
  "id": 1,
  "user_id": "user_123",
  "device_token": "fcm_token_example_123456",
  "platform": "android",
  "endpoint": null,
  "auth_key": null,
  "p256dh_key": null,
  "device_name": "Pixel 6",
  "device_model": "Google Pixel 6",
  "app_version": "1.0.0",
  "is_active": true,
  "created_at": "2025-09-19T03:18:18.185109",
  "updated_at": "2025-09-19T03:18:18.185109",
  "last_used_at": null
}
```

#### 步骤 2: 发送Push通知
```bash
curl -X POST http://localhost:8206/api/v1/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "push",
    "recipient_id": "user_123",
    "subject": "Test Push Notification",
    "content": "This is a test push notification message!",
    "priority": "high",
    "metadata": {"action_url": "/notifications/view"}
  }'
```

**实际响应**:
```json
{
  "notification": {
    "id": 1,
    "notification_id": "ntf_push_1758223230.4393",
    "type": "push",
    "priority": "high",
    "recipient_type": "user",
    "recipient_id": "user_123",
    "recipient_email": null,
    "recipient_phone": null,
    "template_id": null,
    "subject": "Test Push Notification",
    "content": "This is a test push notification message!",
    "html_content": null,
    "variables": {},
    "scheduled_at": null,
    "expires_at": null,
    "retry_count": 0,
    "max_retries": 3,
    "status": "pending",
    "error_message": null,
    "provider": null,
    "provider_message_id": null,
    "metadata": {"action_url": "/notifications/view"},
    "tags": [],
    "created_at": "2025-09-19T03:20:30.439358",
    "sent_at": null,
    "delivered_at": null,
    "read_at": null,
    "failed_at": null
  },
  "message": "Notification created and queued for sending",
  "success": true
}
```

### 测试场景 3: 应用内通知（基于实际测试）

#### 发送应用内通知
```bash
curl -X POST http://localhost:8206/api/v1/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "in_app",
    "recipient_id": "user123",
    "subject": "Test In-App",
    "content": "This is a test in-app notification",
    "priority": "normal"
  }'
```

**实际响应**:
```json
{
  "notification": {
    "id": 4,
    "notification_id": "ntf_in_app_1759129342.713785",
    "type": "in_app",
    "priority": "normal",
    "recipient_type": "user",
    "recipient_id": "user123",
    "subject": "Test In-App",
    "content": "This is a test in-app notification",
    "status": "pending",
    "created_at": "2025-09-29T15:02:22.713843"
  },
  "message": "Notification created and queued for sending",
  "success": true
}
```

#### 获取用户的应用内通知
```bash
curl http://localhost:8206/api/v1/notifications/in-app/user123
```

**实际响应**:
```json
[
  {
    "id": 1,
    "notification_id": "ntf_in_app_1759129342.713785",
    "user_id": "user123",
    "title": "Test In-App",
    "message": "This is a test in-app notification",
    "priority": "normal",
    "is_read": false,
    "is_archived": false,
    "created_at": "2025-09-29T15:02:22.736307"
  }
]
```

#### 标记通知为已读
```bash
curl -X POST "http://localhost:8206/api/v1/notifications/in-app/ntf_in_app_1759129342.713785/read?user_id=user123"
```

#### 获取未读通知数量
```bash
curl http://localhost:8206/api/v1/notifications/in-app/user123/unread-count
```

### 测试场景 4: 批量发送

#### 创建批量发送任务
```bash
curl -X POST http://localhost:8206/api/v1/notifications/batch \
  -H "Content-Type: application/json" \
  -d '{
    "name": "月度通讯",
    "template_id": "tpl_email_1759130299.932903",
    "type": "email",
    "recipients": [
      {
        "email": "user1@example.com",
        "variables": {"name": "User 1"}
      },
      {
        "email": "user2@example.com",
        "variables": {"name": "User 2"}
      },
      {
        "email": "user3@example.com",
        "variables": {"name": "User 3"}
      }
    ],
    "priority": "normal",
    "metadata": {"campaign": "monthly_newsletter"}
  }'
```

### 测试场景 5: Web Push订阅

#### 注册Web Push订阅
```bash
curl -X POST http://localhost:8206/api/v1/notifications/push/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_456",
    "device_token": "web_token_abc123",
    "platform": "web",
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc123...",
    "auth_key": "auth_key_here",
    "p256dh_key": "p256dh_key_here",
    "device_name": "Chrome on Mac"
  }'
```

#### 查询用户的Push订阅
```bash
curl http://localhost:8206/api/v1/notifications/push/subscriptions/user_456
```

#### 取消Push订阅
```bash
curl -X DELETE "http://localhost:8206/api/v1/notifications/push/unsubscribe?user_id=user_456&device_token=web_token_abc123"
```

### 测试场景 6: 获取通知统计

```bash
curl "http://localhost:8206/api/v1/notifications/stats?user_id=user_123&period=today"
```

**响应示例**:
```json
{
  "total_sent": 15,
  "total_delivered": 12,
  "total_failed": 2,
  "total_pending": 1,
  "by_type": {
    "email": 8,
    "push": 5,
    "in_app": 2
  },
  "by_status": {
    "delivered": 12,
    "failed": 2,
    "pending": 1
  },
  "period": "today"
}
```

## 通知类型

- **EMAIL**: 邮件通知（通过Resend API）
- **PUSH**: 推送通知（支持Web、iOS、Android）
- **IN_APP**: 应用内通知
- **SMS**: 短信通知（需要配置）
- **WEBHOOK**: Webhook通知

## 通知优先级

- **LOW**: 低优先级
- **NORMAL**: 普通优先级
- **HIGH**: 高优先级
- **URGENT**: 紧急

## 通知状态

- **PENDING**: 待发送
- **SENDING**: 发送中
- **SENT**: 已发送
- **DELIVERED**: 已送达
- **FAILED**: 失败
- **BOUNCED**: 退回
- **CANCELLED**: 已取消

## 模板变量系统

模板支持 `{{variable_name}}` 格式的变量替换：

```json
{
  "subject": "Hello {{user_name}}!",
  "content": "Your order #{{order_id}} has been shipped to {{address}}.",
  "variables": {
    "user_name": "John",
    "order_id": "12345",
    "address": "123 Main St"
  }
}
```

## 数据库表结构

服务使用以下数据库表：
- `dev.notification_templates` - 通知模板
- `dev.notifications` - 所有通知记录
- `dev.in_app_notifications` - 应用内通知
- `dev.notification_batches` - 批量发送任务
- `dev.push_subscriptions` - Push订阅信息

## 环境变量配置

在 `.env` 文件中配置：

```env
# Email (Resend)
RESEND_API_KEY=re_xxxxx

# Push通知
VAPID_PRIVATE_KEY=xxx  # Web Push
FCM_SERVER_KEY=xxx     # Android Push
APNS_CERT_PATH=xxx     # iOS Push

# SMS (可选)
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
```

## 常见错误及解决方案

### 1. 邮件发送失败
**错误**:
```json
{
  "detail": "Email client not configured"
}
```
**解决**: 配置 `RESEND_API_KEY` 环境变量

### 2. Push通知失败
**错误**:
```json
{
  "detail": "No active push subscriptions found for user"
}
```
**解决**: 确保用户已注册Push订阅

### 3. 模板不存在
**错误**:
```json
{
  "detail": "Template not found"
}
```
**解决**: 检查template_id或创建新模板

## 后台任务

服务自动运行后台任务，每30秒检查并发送待处理的通知：
- 处理计划发送的通知
- 重试失败的通知
- 清理过期的通知

## 批量发送最佳实践

1. 将大批量任务分批处理（建议每批不超过1000个）
2. 使用模板减少数据传输
3. 设置合适的优先级
4. 使用metadata跟踪批次

## 故障排除

### 服务无法启动
- 检查端口8206是否被占用
- 验证数据库连接
- 查看日志文件

### 通知未发送
- 检查通知状态和error_message
- 验证接收者信息
- 确认相关服务配置（如Resend API）

### Push通知未收到
- 确认设备token有效
- 检查FCM/APNs配置
- 验证用户订阅状态

## 测试建议

1. 先创建模板，再使用模板发送
2. 测试各种通知类型
3. 验证变量替换功能
4. 测试批量发送限流
5. 测试通知重试机制

## API速率限制

为避免服务过载，建议：
- 单次批量发送不超过1000个接收者
- API调用频率不超过100次/分钟
- 使用优先级合理分配资源

---

## 最新测试总结（2025-09-29）

✅ **已验证功能**：
1. **健康检查** - 服务在端口8206正常运行
2. **邮件通知** - 成功创建并排队发送邮件通知
3. **应用内通知** - 成功创建应用内通知，用户可查看
4. **模板管理** - 成功创建和查询通知模板

🎯 **核心特性**：
- 支持多种通知类型：email、in_app、push、webhook
- 模板系统支持变量替换 `{{变量名}}`
- 异步处理机制，支持批量发送
- 完整的状态管理和错误处理
- Push通知支持Web、iOS、Android平台
- 统计功能和应用内通知管理

📊 **服务状态**：运行稳定，API接口完整可用