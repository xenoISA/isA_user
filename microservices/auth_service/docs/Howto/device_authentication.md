# Device Authentication Service - HOWTO Guide

## 概述

设备认证服务提供 IoT 设备的注册、认证和管理功能，集成在 auth_service 中，确保统一的认证架构。

## 架构设计

```
┌──────────────┐
│  IoT Device  │───MQTT──▶│ MQTT Gateway │
└──────────────┘          └──────────────┘
                                 │
                          HTTP POST /api/v1/devices/auth
                                 ▼
                    ┌────────────────────────┐
                    │    device_service      │
                    └────────────────────────┘
                                 │
                          调用 auth_service
                                 ▼
                    ┌────────────────────────┐
                    │     auth_service       │
                    │  (设备认证中心)         │
                    └────────────────────────┘
```

## 快速开始

### 1. 数据库设置

运行迁移脚本创建设备认证表：

```bash
# 使用 psql 执行迁移
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres \
  -c "SET search_path TO dev;" \
  -f microservices/auth_service/migrations/002_create_device_credentials_table.sql
```

### 2. 启动服务

```bash
# 启动 auth_service (端口 8202)
python -m uvicorn microservices.auth_service.main:app --host 127.0.0.1 --port 8202

# 启动 device_service (端口 8220)  
python -m uvicorn microservices.device_service.main:app --host 127.0.0.1 --port 8220
```

## API 使用指南

### 设备注册

注册新设备并获取认证凭证：

```bash
curl -X POST http://localhost:8202/api/v1/auth/device/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "sensor_001",
    "organization_id": "org_123",
    "device_name": "Temperature Sensor",
    "device_type": "sensor",
    "metadata": {
      "location": "Building A",
      "firmware": "v1.0.0"
    }
  }'
```

**响应示例：**
```json
{
  "success": true,
  "device_id": "sensor_001",
  "device_secret": "7a06IctTO6kNKhGgaNjYchb6uFmV2d0a3Hjqfxz1aZs",
  "organization_id": "org_123",
  "device_name": "Temperature Sensor",
  "device_type": "sensor",
  "status": "active",
  "created_at": "2025-09-26T16:11:19.430658"
}
```

⚠️ **重要**: `device_secret` 仅在注册时返回一次，请妥善保存！

### 设备认证

#### 方式1: 直接通过 auth_service

```bash
curl -X POST http://localhost:8202/api/v1/auth/device/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "sensor_001",
    "device_secret": "7a06IctTO6kNKhGgaNjYchb6uFmV2d0a3Hjqfxz1aZs"
  }'
```

#### 方式2: 通过 device_service (推荐)

```bash
curl -X POST http://localhost:8220/api/v1/devices/auth \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "sensor_001",
    "device_secret": "7a06IctTO6kNKhGgaNjYchb6uFmV2d0a3Hjqfxz1aZs"
  }'
```

**响应示例：**
```json
{
  "device_id": "sensor_001",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

### Token 验证

验证设备 JWT token 是否有效：

```bash
curl -X POST http://localhost:8202/api/v1/auth/device/verify-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**响应示例：**
```json
{
  "valid": true,
  "device_id": "sensor_001",
  "organization_id": "org_123",
  "device_type": "sensor",
  "expires_at": "2025-09-27T16:11:55+00:00"
}
```

### 其他管理功能

#### 刷新设备密钥

```bash
curl -X POST http://localhost:8202/api/v1/auth/device/sensor_001/refresh-secret \
  -H "Content-Type: application/json" \
  -d '{"organization_id": "org_123"}'
```

#### 撤销设备

```bash
curl -X DELETE http://localhost:8202/api/v1/auth/device/sensor_001?organization_id=org_123
```

#### 列出组织设备

```bash
curl -X GET "http://localhost:8202/api/v1/auth/device/list?organization_id=org_123"
```

## 数据库架构

### device_credentials 表

| 字段 | 类型 | 说明 |
|-----|------|------|
| device_id | VARCHAR(255) | 设备唯一标识 (主键) |
| device_secret | VARCHAR(255) | 设备密钥 (哈希存储) |
| organization_id | VARCHAR(255) | 所属组织 |
| device_name | VARCHAR(255) | 设备名称 |
| device_type | VARCHAR(50) | 设备类型 |
| status | VARCHAR(20) | 状态: active/inactive/revoked |
| last_authenticated_at | TIMESTAMP | 最后认证时间 |
| authentication_count | INTEGER | 认证次数 |
| metadata | JSONB | 设备元数据 |
| expires_at | TIMESTAMP | 过期时间 |

### device_auth_logs 表

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | SERIAL | 日志ID |
| device_id | VARCHAR(255) | 设备ID |
| auth_status | VARCHAR(20) | 认证状态: success/failed/blocked |
| ip_address | VARCHAR(45) | IP地址 |
| user_agent | TEXT | User Agent |
| error_message | TEXT | 错误信息 |
| created_at | TIMESTAMP | 创建时间 |

## 安全最佳实践

1. **密钥管理**
   - 设备密钥使用 SHA256 哈希存储
   - 密钥仅在注册时明文返回
   - 支持密钥刷新和撤销

2. **Token 安全**
   - JWT token 有效期默认 24 小时
   - Token 包含设备类型和组织信息
   - 支持 token 验证和过期检查

3. **访问控制**
   - 设备操作需要组织ID验证
   - 认证失败记录在日志表中
   - 支持设备状态管理 (active/revoked)

## 集成示例

### Python 设备客户端

```python
import requests
import json

class DeviceClient:
    def __init__(self, auth_url="http://localhost:8202"):
        self.auth_url = auth_url
        self.device_id = None
        self.device_secret = None
        self.access_token = None
    
    def register(self, device_id, org_id, device_name, device_type="sensor"):
        """注册设备"""
        response = requests.post(
            f"{self.auth_url}/api/v1/auth/device/register",
            json={
                "device_id": device_id,
                "organization_id": org_id,
                "device_name": device_name,
                "device_type": device_type
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.device_id = data["device_id"]
            self.device_secret = data["device_secret"]
            print(f"Device registered: {self.device_id}")
            print(f"Secret: {self.device_secret}")
            return data
        else:
            print(f"Registration failed: {response.text}")
            return None
    
    def authenticate(self):
        """设备认证"""
        if not self.device_id or not self.device_secret:
            print("Device not registered")
            return None
        
        response = requests.post(
            f"{self.auth_url}/api/v1/auth/device/authenticate",
            json={
                "device_id": self.device_id,
                "device_secret": self.device_secret
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["token"]
            print(f"Authenticated! Token expires in {data['expires_in']} seconds")
            return data
        else:
            print(f"Authentication failed: {response.text}")
            return None
    
    def send_telemetry(self, data):
        """发送遥测数据 (需要认证)"""
        if not self.access_token:
            print("Not authenticated")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # 发送到遥测服务
        response = requests.post(
            "http://localhost:8230/api/v1/telemetry",
            headers=headers,
            json={
                "device_id": self.device_id,
                "data": data
            }
        )
        
        return response.json() if response.status_code == 200 else None

# 使用示例
if __name__ == "__main__":
    client = DeviceClient()
    
    # 注册设备 (首次)
    client.register(
        device_id="temp_sensor_001",
        org_id="org_123",
        device_name="Temperature Sensor #1",
        device_type="sensor"
    )
    
    # 认证
    client.authenticate()
    
    # 发送数据
    client.send_telemetry({
        "temperature": 25.5,
        "humidity": 60
    })
```

### MQTT 集成

设备通过 MQTT 认证时，MQTT Gateway 应该：

1. 接收设备凭证
2. 调用 device_service 的 `/api/v1/devices/auth` 端点
3. 缓存认证结果
4. 使用 token 进行后续操作

## 故障排查

### 常见问题

1. **"duplicate key value violates unique constraint"**
   - 原因：设备ID已存在
   - 解决：使用新的设备ID或删除旧设备

2. **"Invalid credentials"**
   - 原因：设备密钥错误或设备已被撤销
   - 解决：检查密钥或重新注册设备

3. **"Token has expired"**
   - 原因：JWT token 已过期
   - 解决：重新认证获取新 token

### 日志查询

```sql
-- 查看设备认证日志
SELECT * FROM dev.device_auth_logs 
WHERE device_id = 'sensor_001' 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看设备状态
SELECT device_id, status, last_authenticated_at, authentication_count 
FROM dev.device_credentials 
WHERE organization_id = 'org_123';
```

## 性能优化

1. **Token 缓存**
   - 客户端应缓存 token 直到过期
   - 避免频繁认证请求

2. **连接池**
   - 使用 Supabase 客户端内置连接池
   - 避免频繁创建数据库连接

3. **批量操作**
   - 使用批量注册 API (待实现)
   - 减少网络往返

## 未来扩展

- [ ] X.509 证书认证支持
- [ ] OAuth 2.0 设备流程
- [ ] 设备分组管理
- [ ] 认证速率限制
- [ ] 设备固件版本管理
- [ ] 双因素认证 (2FA)

## 相关文档

- [Auth Service API](../main.py)
- [Device Service API](../../device_service/main.py)
- [数据库迁移](../migrations/002_create_device_credentials_table.sql)
- [测试脚本](../../../test_device_auth.py)