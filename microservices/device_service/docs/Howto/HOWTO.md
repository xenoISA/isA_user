# Device Service - HOWTO

## 概述
Device Service 是一个专门用于 IoT 设备管理的微服务，提供设备注册、认证、生命周期管理、命令控制和设备分组功能。

## 快速开始

### 1. 启动服务
```bash
# 默认端口 8220
PYTHONPATH=. python -m microservices.device_service.main

# 或使用脚本启动所有服务
./scripts/start_all_services.sh
```

### 2. 健康检查
```bash
curl http://localhost:8220/health
```

## API 使用指南

### 认证
所有端点（除设备认证外）都需要认证。支持两种方式：
- JWT Token: `Authorization: Bearer <token>`
- API Key: `X-API-Key: <key>`

获取开发 token：
```bash
curl -X POST http://localhost:8202/api/v1/auth/dev-token \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "iot_test",
    "email": "iot@example.com",
    "expires_in": 7200
  }'
```

### 核心功能

#### 1. 设备注册

```bash
curl -X POST http://localhost:8220/api/v1/devices \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "Smart Sensor 001",
    "device_type": "sensor",
    "manufacturer": "IoT Corp",
    "model": "SS-2024",
    "serial_number": "SN123456789",
    "firmware_version": "1.2.3",
    "hardware_version": "1.0",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "connectivity_type": "wifi",
    "security_level": "standard",
    "location": {
      "latitude": 39.9042,
      "longitude": 116.4074,
      "address": "Beijing, China"
    },
    "metadata": {
      "installation_date": "2025-09-26",
      "warranty_expires": "2027-09-26"
    },
    "tags": ["production", "beijing", "temperature"]
  }'
```

#### 2. 设备认证

设备使用其 ID 和密钥进行认证：
```bash
curl -X POST http://localhost:8220/api/v1/devices/auth \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device_123456",
    "device_secret": "secret_key_here"
  }'
```

返回设备专用的访问令牌：
```json
{
  "device_id": "device_123456",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### 3. 获取设备详情

```bash
curl -X GET http://localhost:8220/api/v1/devices/{device_id} \
  -H "Authorization: Bearer <token>"
```

#### 4. 更新设备信息

```bash
curl -X PUT http://localhost:8220/api/v1/devices/{device_id} \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "firmware_version": "1.2.4",
    "status": "active",
    "location": {
      "latitude": 31.2304,
      "longitude": 121.4737,
      "address": "Shanghai, China"
    }
  }'
```

#### 5. 获取设备列表

支持多种过滤条件：
```bash
curl -X GET "http://localhost:8220/api/v1/devices?status=active&device_type=sensor&limit=50" \
  -H "Authorization: Bearer <token>"
```

参数说明：
- `status`: active, inactive, maintenance, decommissioned
- `device_type`: sensor, actuator, gateway, controller, display
- `connectivity`: wifi, ethernet, cellular, bluetooth, zigbee, lora
- `group_id`: 设备组 ID
- `limit`: 最大返回数量 (1-500)
- `offset`: 偏移量

#### 6. 发送设备命令

```bash
curl -X POST http://localhost:8220/api/v1/devices/{device_id}/commands \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "command_type": "reboot",
    "parameters": {
      "delay_seconds": 30,
      "force": false
    },
    "priority": "high",
    "timeout_seconds": 60
  }'
```

常用命令类型：
- `reboot`: 重启设备
- `reset`: 恢复出厂设置
- `update_config`: 更新配置
- `collect_logs`: 收集日志
- `run_diagnostic`: 运行诊断

#### 7. 设备健康监控

获取设备健康状态：
```bash
curl -X GET http://localhost:8220/api/v1/devices/{device_id}/health \
  -H "Authorization: Bearer <token>"
```

返回示例：
```json
{
  "device_id": "device_123456",
  "health_status": "healthy",
  "connectivity": {
    "status": "connected",
    "signal_strength": -65,
    "last_seen": "2025-09-26T16:00:00Z"
  },
  "resource_usage": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "storage_percent": 35.0,
    "battery_level": 85
  },
  "error_count": 0,
  "warning_count": 2,
  "last_diagnostic": "2025-09-26T15:30:00Z"
}
```

#### 8. 设备组管理

**创建设备组**
```bash
curl -X POST http://localhost:8220/api/v1/groups \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "Temperature Sensors",
    "description": "All temperature monitoring sensors",
    "group_type": "functional",
    "metadata": {
      "location": "Building A",
      "floor": "3rd"
    },
    "tags": ["monitoring", "environmental"]
  }'
```

**添加设备到组**
```bash
curl -X PUT http://localhost:8220/api/v1/groups/{group_id}/devices/{device_id} \
  -H "Authorization: Bearer <token>"
```

**获取组内设备**
```bash
curl -X GET http://localhost:8220/api/v1/groups/{group_id} \
  -H "Authorization: Bearer <token>"
```

#### 9. 批量操作

**批量注册设备**
```bash
curl -X POST http://localhost:8220/api/v1/devices/bulk/register \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "device_name": "Sensor 001",
      "device_type": "sensor",
      "serial_number": "SN001"
    },
    {
      "device_name": "Sensor 002",
      "device_type": "sensor",
      "serial_number": "SN002"
    }
  ]'
```

**批量发送命令**
```bash
curl -X POST http://localhost:8220/api/v1/devices/bulk/commands \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device1", "device2", "device3"],
    "command": {
      "command_type": "update_config",
      "parameters": {
        "report_interval": 60
      }
    }
  }'
```

#### 10. 设备停用

```bash
curl -X DELETE http://localhost:8220/api/v1/devices/{device_id} \
  -H "Authorization: Bearer <token>"
```

## 数据模型

### Device
```json
{
  "device_id": "string",
  "device_name": "string",
  "device_type": "sensor|actuator|gateway|controller|display",
  "manufacturer": "string",
  "model": "string",
  "serial_number": "string",
  "firmware_version": "string",
  "hardware_version": "string",
  "mac_address": "string",
  "connectivity_type": "wifi|ethernet|cellular|bluetooth|zigbee|lora",
  "security_level": "basic|standard|enhanced",
  "status": "active|inactive|maintenance|decommissioned",
  "location": {
    "latitude": 0.0,
    "longitude": 0.0,
    "address": "string"
  },
  "metadata": {},
  "group_id": "string",
  "tags": ["string"],
  "last_seen": "datetime",
  "registered_at": "datetime",
  "updated_at": "datetime"
}
```

### DeviceCommand
```json
{
  "command_type": "string",
  "parameters": {},
  "priority": "low|normal|high|critical",
  "timeout_seconds": 60
}
```

### DeviceGroup
```json
{
  "group_id": "string",
  "group_name": "string",
  "description": "string",
  "group_type": "functional|geographical|custom",
  "device_count": 0,
  "metadata": {},
  "tags": ["string"],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 最佳实践

### 1. 设备注册流程
1. 预注册设备（生成 device_id 和 secret）
2. 物理设备首次连接时使用预分配的凭据
3. 设备认证获取访问令牌
4. 使用令牌进行后续 API 调用

### 2. 设备分组策略
- **功能分组**: 相同功能的设备（如所有温度传感器）
- **地理分组**: 同一位置的设备（如某栋楼的所有设备）
- **自定义分组**: 基于业务逻辑的分组

### 3. 命令执行
- 使用优先级控制命令执行顺序
- 设置合理的超时时间
- 实现命令确认机制
- 记录命令执行历史

### 4. 安全建议
- 定期轮换设备密钥
- 使用 TLS 加密通信
- 实施设备证书管理
- 监控异常认证行为

### 5. 性能优化
- 批量操作减少 API 调用
- 合理设置心跳间隔
- 使用缓存减少数据库查询
- 实施速率限制

## 监控和调试

### 查看服务日志
```bash
tail -f logs/device_service.log
```

### 获取服务统计
```bash
curl http://localhost:8220/api/v1/service/stats
```

### 获取设备统计
```bash
curl http://localhost:8220/api/v1/devices/stats \
  -H "Authorization: Bearer <token>"
```

## 故障排除

### 常见问题

1. **设备无法认证**
   - 检查 device_id 和 secret 是否正确
   - 确认设备状态为 active
   - 验证 auth_service 是否运行

2. **命令执行失败**
   - 检查设备是否在线
   - 验证命令参数格式
   - 查看设备日志

3. **设备状态不更新**
   - 检查设备心跳配置
   - 验证网络连接
   - 查看 last_seen 时间戳

## 集成示例

### Python SDK
```python
import httpx
from typing import Dict, Any

class DeviceClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def register_device(self, device_data: Dict[str, Any]):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/devices",
                headers=self.headers,
                json=device_data
            )
            return response.json()
    
    async def get_device(self, device_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/devices/{device_id}",
                headers=self.headers
            )
            return response.json()
    
    async def send_command(self, device_id: str, command: Dict[str, Any]):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/commands",
                headers=self.headers,
                json=command
            )
            return response.json()

# 使用示例
client = DeviceClient("http://localhost:8220", "your_token")
device = await client.register_device({
    "device_name": "New Sensor",
    "device_type": "sensor",
    "serial_number": "SN999"
})
```

### MQTT 集成
```python
import paho.mqtt.client as mqtt
import json
import requests

def on_connect(client, userdata, flags, rc):
    # 订阅设备状态主题
    client.subscribe("devices/+/status")
    client.subscribe("devices/+/telemetry")

def on_message(client, userdata, msg):
    topic_parts = msg.topic.split('/')
    device_id = topic_parts[1]
    message_type = topic_parts[2]
    
    if message_type == "status":
        # 更新设备状态
        data = json.loads(msg.payload)
        requests.put(
            f"http://localhost:8220/api/v1/devices/{device_id}",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"status": data["status"]}
        )

# MQTT 客户端设置
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("mqtt_broker_host", 1883, 60)
mqtt_client.loop_forever()
```

## 相关服务

- **OTA Service**: 固件更新管理
- **Telemetry Service**: 遥测数据收集
- **Auth Service**: 认证和授权
- **Notification Service**: 设备告警通知
- **Gateway Service**: API 网关

## 扩展功能

### 计划中的功能
- 设备配置模板
- 自动设备发现
- 设备孪生（Digital Twin）
- 边缘计算支持
- 设备市场集成