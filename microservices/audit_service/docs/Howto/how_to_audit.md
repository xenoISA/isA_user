# Audit Service 使用指南

## 服务概述
Audit Service 是一个综合审计日志微服务，运行在端口 **8204**。负责记录、查询、分析系统中的所有审计事件、安全告警和合规报告。

## 端口配置
- **服务端口**: 8204
- **API基础路径**: `http://localhost:8204/api/v1/audit`

## 数据库配置
- **数据库**: PostgreSQL (通过 Supabase)
- **连接字符串**: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Schema**: `dev`
- **核心表**: `audit_events` (统一审计事件表)

## 核心功能与测试用例

### 1. 健康检查

#### 基础健康检查
```bash
curl http://localhost:8204/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "service": "audit_service",
  "port": 8204,
  "version": "1.0.0"
}
```

#### 详细健康检查
```bash
curl http://localhost:8204/health/detailed
```

**响应示例**:
```json
{
  "service": "audit_service",
  "status": "operational",
  "port": 8204,
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2025-09-18T15:30:00.000Z"
}
```

### 2. 记录审计事件

#### 单个事件记录
```bash
curl -X POST "http://localhost:8204/api/v1/audit/events" \
-H "Content-Type: application/json" \
-d '{
  "event_type": "user_login",
  "category": "authentication",
  "severity": "low",
  "action": "User login via API",
  "description": "Test user logged in through API",
  "user_id": "test_user_2",
  "resource_type": "auth_system",
  "resource_name": "login_api",
  "ip_address": "192.168.1.50",
  "success": true,
  "metadata": {"method": "password", "device": "api_client"}
}'
```

**成功响应示例**:
```json
{
  "id": "5",
  "event_type": "user_login",
  "category": "authentication",
  "severity": "low",
  "status": "success",
  "action": "User login via API",
  "description": "Test user logged in through API",
  "user_id": "test_user_2",
  "organization_id": null,
  "resource_type": "auth_system",
  "resource_name": "login_api",
  "success": true,
  "timestamp": "2025-09-18T15:40:20.549524Z",
  "metadata": {
    "method": "password",
    "device": "api_client"
  }
}
```

#### 批量事件记录
```bash
curl -X POST "http://localhost:8204/api/v1/audit/events/batch" \
-H "Content-Type: application/json" \
-d '[
  {
    "event_type": "resource_access",
    "category": "data_access",
    "severity": "low",
    "action": "Read API data",
    "user_id": "test_user_1",
    "resource_type": "api",
    "resource_name": "weather_api",
    "success": true
  },
  {
    "event_type": "permission_grant",
    "category": "authorization",
    "severity": "medium",
    "action": "Grant permission",
    "user_id": "admin_user",
    "resource_type": "api",
    "resource_name": "data_api",
    "success": true
  }
]'
```

**批量响应示例**:
```json
{
  "message": "批量事件记录完成",
  "successful_count": 2,
  "failed_count": 0,
  "total_count": 2,
  "results": [...]
}
```

### 3. 查询审计事件

#### 基础查询 (GET方式)
```bash
curl "http://localhost:8204/api/v1/audit/events?user_id=test_user_2&limit=5"
```

#### 高级查询 (POST方式)
```bash
curl -X POST "http://localhost:8204/api/v1/audit/events/query" \
-H "Content-Type: application/json" \
-d '{
  "event_types": ["user_login", "resource_access"],
  "categories": ["authentication", "data_access"],
  "user_id": "test_user_2",
  "start_time": "2025-09-18T00:00:00Z",
  "end_time": "2025-09-19T00:00:00Z",
  "success_only": true,
  "limit": 10,
  "offset": 0,
  "sort_by": "timestamp",
  "sort_order": "desc"
}'
```

### 4. 用户活动跟踪

#### 获取用户活动记录
```bash
curl "http://localhost:8204/api/v1/audit/users/test_user_2/activities?days=30&limit=100"
```

#### 获取用户活动摘要
```bash
curl "http://localhost:8204/api/v1/audit/users/test_user_2/summary?days=30"
```

**摘要响应示例**:
```json
{
  "user_id": "test_user_2",
  "total_activities": 3,
  "success_count": 2,
  "failure_count": 1,
  "last_activity": "2025-09-18T15:40:20.549524Z",
  "most_common_activities": [
    {"activity_type": "security_alert", "count": 1},
    {"activity_type": "resource_access", "count": 1},
    {"activity_type": "user_login", "count": 1}
  ],
  "risk_score": 26.67,
  "metadata": {
    "period_days": 30,
    "analysis_timestamp": "2025-09-18T15:41:00.586515"
  }
}
```

### 5. 安全事件管理

#### 创建安全告警
```bash
curl -X POST "http://localhost:8204/api/v1/audit/security/alerts" \
-H "Content-Type: application/json" \
-d '{
  "threat_type": "brute_force_attempt",
  "severity": "high",
  "source_ip": "192.168.1.100",
  "target_resource": "/api/login",
  "description": "Multiple failed login attempts detected from same IP"
}'
```

**告警响应示例**:
```json
{
  "message": "安全告警已创建",
  "alert_id": "6",
  "threat_level": "high",
  "created_at": "2025-09-18T15:41:13.893902"
}
```

#### 获取安全事件列表
```bash
curl "http://localhost:8204/api/v1/audit/security/events?days=7&severity=high"
```

### 6. 合规报告

#### 生成合规报告
```bash
curl -X POST "http://localhost:8204/api/v1/audit/compliance/reports" \
-H "Content-Type: application/json" \
-d '{
  "report_type": "monthly",
  "compliance_standard": "GDPR",
  "period_start": "2025-09-01T00:00:00Z",
  "period_end": "2025-09-30T23:59:59Z",
  "include_details": true
}'
```

#### 获取支持的合规标准
```bash
curl http://localhost:8204/api/v1/audit/compliance/standards
```

**响应示例**:
```json
{
  "supported_standards": [
    {
      "name": "GDPR",
      "description": "通用数据保护条例",
      "retention_days": 2555,
      "regions": ["EU"]
    },
    {
      "name": "SOX",
      "description": "萨班斯-奥克斯利法案",
      "retention_days": 2555,
      "regions": ["US"]
    },
    {
      "name": "HIPAA",
      "description": "健康保险便携性和问责法案",
      "retention_days": 2190,
      "regions": ["US"]
    }
  ]
}
```

### 7. 服务统计

#### 获取服务统计信息
```bash
curl http://localhost:8204/api/v1/audit/stats
```

**统计响应示例**:
```json
{
  "total_events": 1,
  "events_today": 0,
  "active_users": 3,
  "security_alerts": 1,
  "compliance_score": 70.0
}
```

### 8. 服务信息

#### 获取服务信息
```bash
curl http://localhost:8204/api/v1/audit/info
```

**响应示例**:
```json
{
  "service": "audit_service",
  "version": "1.0.0",
  "description": "综合审计事件记录、查询、分析和合规报告服务",
  "capabilities": {
    "event_logging": true,
    "event_querying": true,
    "user_activity_tracking": true,
    "security_alerting": true,
    "compliance_reporting": true,
    "real_time_analysis": true,
    "data_retention": true
  },
  "endpoints": {
    "log_event": "/api/v1/audit/events",
    "query_events": "/api/v1/audit/events/query",
    "user_activities": "/api/v1/audit/users/{user_id}/activities",
    "security_alerts": "/api/v1/audit/security/alerts",
    "compliance_reports": "/api/v1/audit/compliance/reports"
  }
}
```

### 9. 数据维护

#### 清理过期数据
```bash
curl -X POST "http://localhost:8204/api/v1/audit/maintenance/cleanup?retention_days=365"
```

## 事件类型说明

### 事件类型 (Event Types)
- `user_login` - 用户登录
- `user_logout` - 用户登出
- `user_register` - 用户注册
- `user_update` - 用户更新
- `permission_grant` - 权限授予
- `permission_revoke` - 权限撤销
- `resource_access` - 资源访问
- `security_alert` - 安全告警
- `compliance_check` - 合规检查

### 事件分类 (Categories)
- `authentication` - 认证相关
- `authorization` - 授权相关
- `data_access` - 数据访问
- `security` - 安全相关
- `compliance` - 合规相关
- `system` - 系统相关

### 严重程度 (Severities)
- `low` - 低
- `medium` - 中
- `high` - 高
- `critical` - 严重

## 风险评分计算

用户风险评分基于以下因素计算：
- 失败率 (失败事件 / 总事件)
- 安全事件数量
- 异常行为模式

评分范围：0-100
- 0-30: 低风险
- 31-60: 中风险
- 61-80: 高风险
- 81-100: 极高风险

## 数据库操作

### 查看审计事件
```sql
-- 连接数据库
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

-- 查看所有审计事件
SET search_path TO dev;
SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 10;

-- 查看特定用户的事件
SELECT * FROM audit_events 
WHERE user_id = 'test_user_2' 
ORDER BY timestamp DESC;

-- 查看安全事件
SELECT * FROM audit_events 
WHERE category = 'security' 
AND severity IN ('high', 'critical')
ORDER BY timestamp DESC;

-- 统计事件类型
SELECT event_type, COUNT(*) as count 
FROM audit_events 
GROUP BY event_type 
ORDER BY count DESC;
```

### 插入测试数据
```sql
INSERT INTO dev.audit_events (
    event_type, category, severity, action, description,
    user_id, resource_type, resource_name,
    ip_address, success, metadata, tags
) VALUES (
    'user_login', 'authentication', 'low', 
    'Manual test login', 'Testing audit functionality',
    'test_user_3', 'auth_system', 'web_portal',
    '10.0.0.1', true,
    '{"browser": "Chrome", "os": "macOS"}',
    ARRAY['test', 'manual']
);
```

## 故障排查

### 常见问题

1. **数据库连接失败**
   ```
   ERROR: 数据库连接检查失败: [Errno 61] Connection refused
   ```
   - 解决方案：启动Supabase
   ```bash
   cd /path/to/supabase && supabase start
   ```

2. **JSON解析错误**
   ```
   ERROR: the JSON object must be str, bytes or bytearray, not dict
   ```
   - 这是已知问题，不影响事件记录功能
   - 查询功能可能需要修复JSON序列化

3. **事件查询返回空**
   - 检查时间范围参数
   - 验证用户ID是否正确
   - 确认事件确实存在于数据库

## 性能优化

### 索引优化
数据库已创建以下索引：
- `idx_audit_events_event_type`
- `idx_audit_events_user_id`
- `idx_audit_events_timestamp`
- `idx_audit_events_category_timestamp` (复合索引)
- `idx_audit_events_metadata` (GIN索引)

### 查询优化建议
1. 使用时间范围限制查询
2. 避免过大的limit值 (最大1000)
3. 使用批量操作减少API调用
4. 定期清理过期数据

## 集成示例

### Python集成
```python
import requests
import json

# 记录审计事件
def log_audit_event(event_data):
    url = "http://localhost:8204/api/v1/audit/events"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=event_data, headers=headers)
    return response.json()

# 使用示例
event = {
    "event_type": "resource_access",
    "category": "data_access",
    "severity": "low",
    "action": "Read user data",
    "user_id": "app_user_1",
    "resource_type": "database",
    "resource_name": "user_profiles",
    "success": True
}

result = log_audit_event(event)
print(f"Event logged with ID: {result['id']}")
```

### JavaScript集成
```javascript
// 记录审计事件
async function logAuditEvent(eventData) {
    const response = await fetch('http://localhost:8204/api/v1/audit/events', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(eventData)
    });
    return await response.json();
}

// 使用示例
const event = {
    event_type: 'user_login',
    category: 'authentication',
    severity: 'low',
    action: 'Web login',
    user_id: 'web_user_1',
    success: true
};

logAuditEvent(event).then(result => {
    console.log(`Event logged with ID: ${result.id}`);
});
```

## 相关服务

- **Account Service** (端口 8201) - 用户账户管理
- **Auth Service** (端口 8202) - 身份认证
- **Authorization Service** (端口 8203) - 权限管理

## 监控建议

1. **关键指标监控**
   - 每分钟事件数
   - 失败事件比例
   - 安全告警数量
   - API响应时间

2. **告警设置**
   - 高严重度安全事件
   - 异常高的失败率
   - 数据库连接失败
   - 合规评分下降

3. **日志保留策略**
   - 标准事件：1年
   - 安全事件：7年
   - 合规相关：按标准要求