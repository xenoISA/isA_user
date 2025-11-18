# Telemetry Service - HOWTO

## 概述
Telemetry Service 是一个专门用于 IoT 设备数据采集、存储和监控的微服务。它提供时序数据管理、实时数据流、指标聚合和警报功能。

## 快速开始

### 1. 启动服务
```bash
# 默认端口 8225
PORT=8225 PYTHONPATH=. python -m microservices.telemetry_service.main

# 或使用脚本启动所有服务
./scripts/start_all_services.sh
```

### 2. 健康检查
```bash
curl http://localhost:8225/health
```

## API 使用指南

### 认证
所有端点都需要认证。支持两种方式：
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

#### 1. 发送遥测数据

**单个数据点**
```bash
curl -X POST http://localhost:8225/api/v1/devices/{device_id}/telemetry \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_name": "temperature",
    "value": 25.5,
    "unit": "celsius",
    "timestamp": "2025-09-26T16:00:00Z",
    "tags": {
      "location": "room1",
      "sensor_type": "dht22"
    }
  }'
```

**批量数据点**
```bash
curl -X POST http://localhost:8225/api/v1/devices/{device_id}/telemetry/batch \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_points": [
      {
        "metric_name": "temperature",
        "value": 25.5,
        "unit": "celsius",
        "timestamp": "2025-09-26T16:00:00Z"
      },
      {
        "metric_name": "humidity",
        "value": 65.2,
        "unit": "percent",
        "timestamp": "2025-09-26T16:00:00Z"
      }
    ]
  }'
```

#### 2. 定义指标

```bash
curl -X POST http://localhost:8225/api/v1/metrics \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "temperature",
    "description": "Room temperature sensor",
    "data_type": "numeric",
    "unit": "celsius",
    "min_value": -40,
    "max_value": 85,
    "retention_days": 90,
    "aggregation_interval": 60
  }'
```

#### 3. 查询数据

**获取最新值**
```bash
curl -X GET "http://localhost:8225/api/v1/devices/{device_id}/metrics/{metric_name}/latest" \
  -H "Authorization: Bearer <token>"
```

**获取时间范围数据**
```bash
curl -X GET "http://localhost:8225/api/v1/devices/{device_id}/metrics/{metric_name}/range?start=2025-09-26T00:00:00Z&end=2025-09-26T23:59:59Z" \
  -H "Authorization: Bearer <token>"
```

**高级查询**
```bash
curl -X POST http://localhost:8225/api/v1/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "devices": ["device1", "device2"],
    "metrics": ["temperature", "humidity"],
    "start_time": "2025-09-26T00:00:00Z",
    "end_time": "2025-09-26T23:59:59Z",
    "aggregation": "avg",
    "interval": "1h",
    "filters": {
      "location": "room1"
    }
  }'
```

#### 4. 数据聚合

```bash
curl -X GET "http://localhost:8225/api/v1/aggregated?device_id={device_id}&metric_name=temperature&aggregation_type=avg&interval=3600" \
  -H "Authorization: Bearer <token>"
```

#### 5. 警报管理

**创建警报规则**
```bash
curl -X POST http://localhost:8225/api/v1/alerts/rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Temperature Alert",
    "description": "Alert when temperature exceeds threshold",
    "metric_name": "temperature",
    "condition": "greater_than",
    "threshold_value": "30",
    "evaluation_window": 300,
    "trigger_count": 2,
    "level": "warning",
    "device_ids": ["device1"],
    "notification_channels": ["email", "webhook"],
    "cooldown_minutes": 15
  }'
```

**获取活跃警报**
```bash
curl -X GET "http://localhost:8225/api/v1/alerts?status=active" \
  -H "Authorization: Bearer <token>"
```

**确认警报**
```bash
curl -X POST http://localhost:8225/api/v1/alerts/{alert_id}/acknowledge \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "acknowledgement_note": "Investigating the issue"
  }'
```

#### 6. 实时订阅

**创建WebSocket订阅**
```bash
curl -X POST http://localhost:8225/api/v1/subscribe \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device1", "device2"],
    "metric_names": ["temperature", "humidity"],
    "filter_condition": "value > 25",
    "max_frequency": 1000
  }'
```

#### 7. 数据导出

```bash
curl -X POST http://localhost:8225/api/v1/export/csv \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device1"],
    "metric_names": ["temperature"],
    "start_time": "2025-09-26T00:00:00Z",
    "end_time": "2025-09-26T23:59:59Z",
    "include_metadata": true
  }' \
  -o telemetry_export.csv
```

#### 8. 统计信息

**获取设备统计**
```bash
curl -X GET http://localhost:8225/api/v1/devices/{device_id}/stats \
  -H "Authorization: Bearer <token>"
```

**获取服务统计**
```bash
curl -X GET http://localhost:8225/api/v1/stats \
  -H "Authorization: Bearer <token>"
```

## 数据模型

### TelemetryDataPoint
```json
{
  "metric_name": "string",      // 指标名称
  "value": "number",            // 数值
  "unit": "string",             // 单位
  "timestamp": "datetime",      // 时间戳
  "tags": {                     // 可选标签
    "key": "value"
  },
  "quality": 100               // 数据质量 (0-100)
}
```

### MetricDefinition
```json
{
  "name": "string",
  "description": "string",
  "data_type": "numeric|string|boolean|json",
  "unit": "string",
  "min_value": "number",
  "max_value": "number",
  "retention_days": 90,
  "aggregation_interval": 60
}
```

### AlertRule
```json
{
  "name": "string",
  "metric_name": "string",
  "condition": "greater_than|less_than|equals|not_equals",
  "threshold_value": "string",
  "evaluation_window": 300,
  "level": "info|warning|error|critical",
  "device_ids": ["string"],
  "notification_channels": ["email", "webhook"]
}
```

## 最佳实践

### 1. 批量发送数据
- 使用批量端点提高效率
- 建议批次大小：100-500 个数据点
- 实现本地缓冲和重试机制

### 2. 数据采样策略
```python
# 示例：智能采样
def should_send_data(current_value, last_value, threshold=0.5):
    """只在值变化超过阈值时发送"""
    if abs(current_value - last_value) > threshold:
        return True
    return False
```

### 3. 时间戳管理
- 始终使用 UTC 时间
- 包含设备本地时间戳
- 实现时钟同步机制

### 4. 标签使用
- 使用标签进行数据分类
- 常用标签：location, device_type, firmware_version
- 避免高基数标签（如 UUID）

### 5. 数据保留策略
- 原始数据：7-30 天
- 小时聚合：90 天
- 日聚合：1 年
- 月聚合：永久

## 监控和调试

### 查看服务日志
```bash
tail -f logs/telemetry_service.log
```

### 检查数据接收率
```bash
curl http://localhost:8225/api/v1/stats | jq '.ingestion_rate'
```

### 验证数据完整性
```bash
# 检查特定设备的数据质量
curl "http://localhost:8225/api/v1/devices/{device_id}/stats" \
  -H "Authorization: Bearer <token>" | jq '.data_quality'
```

## 故障排除

### 常见问题

1. **数据未显示**
   - 检查时间戳格式
   - 验证设备 ID 正确
   - 确认认证有效

2. **高延迟**
   - 检查批次大小
   - 优化查询时间范围
   - 使用聚合数据而非原始数据

3. **数据丢失**
   - 实现客户端缓冲
   - 配置重试机制
   - 检查网络连接

## 集成示例

### Python SDK
```python
import httpx
from datetime import datetime

class TelemetryClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def send_telemetry(self, device_id, metric_name, value, unit):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/telemetry",
                headers=self.headers,
                json={
                    "metric_name": metric_name,
                    "value": value,
                    "unit": unit,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
            return response.json()
```

### MQTT Bridge
```python
# 将 MQTT 数据转发到 Telemetry Service
import paho.mqtt.client as mqtt
import requests

def on_message(client, userdata, msg):
    # 解析 MQTT 消息
    data = json.loads(msg.payload)
    
    # 转发到 Telemetry Service
    requests.post(
        f"http://localhost:8225/api/v1/devices/{data['device_id']}/telemetry",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "metric_name": data['metric'],
            "value": data['value'],
            "unit": data['unit'],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )
```

## 性能优化

### 配置建议
- 连接池大小：100-200
- 批量大小：100-500
- 聚合间隔：60 秒
- 缓存 TTL：5 分钟

### 扩展方案
1. 水平扩展服务实例
2. 使用 TimescaleDB 进行时序优化
3. 实现数据分片
4. 配置读写分离

## 相关服务

- **Device Service**: 设备注册和管理
- **OTA Service**: 固件更新
- **Gateway Service**: API 网关
- **Auth Service**: 认证服务