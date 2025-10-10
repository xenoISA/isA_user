# OTA Service - HOWTO

## 概述
OTA (Over-The-Air) Service 是一个专门管理 IoT 设备固件更新的微服务。它提供固件版本管理、更新活动编排、分阶段部署、自动回滚和更新进度跟踪等功能。

## 快速开始

### 1. 启动服务
```bash
# 默认端口 8221
PYTHONPATH=. python -m microservices.ota_service.main

# 或使用脚本启动所有服务
./scripts/start_all_services.sh
```

### 2. 健康检查
```bash
curl http://localhost:8221/health
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
    "user_id": "ota_admin",
    "email": "admin@iotcorp.com",
    "expires_in": 7200
  }'
```

### 核心功能

#### 1. 固件管理

**上传固件（当前为模拟）**
```bash
# 实际实现需要文件上传，当前返回模拟数据
curl -X POST http://localhost:8221/api/v1/firmware \
  -H "Authorization: Bearer <token>" \
  -F "metadata={
    \"name\":\"Device Firmware\",
    \"version\":\"1.2.0\",
    \"description\":\"Security patches and improvements\",
    \"device_model\":\"IOT-2024\",
    \"manufacturer\":\"IoT Corp\"
  }" \
  -F "file=@firmware.bin"
```

**获取固件信息**
```bash
curl -X GET http://localhost:8221/api/v1/firmware/{firmware_id} \
  -H "Authorization: Bearer <token>"
```

**列出所有固件**
```bash
curl -X GET "http://localhost:8221/api/v1/firmware?device_model=IOT-2024&limit=10" \
  -H "Authorization: Bearer <token>"
```

**下载固件**
```bash
curl -X GET http://localhost:8221/api/v1/firmware/{firmware_id}/download \
  -H "Authorization: Bearer <token>" \
  -o firmware.bin
```

#### 2. 更新活动管理

**创建更新活动**
```bash
curl -X POST http://localhost:8221/api/v1/campaigns \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q1 2025 Security Update",
    "description": "Critical security patches for all devices",
    "firmware_id": "fw_v1.2.0",
    "deployment_strategy": "staged",
    "priority": "high",
    "target_devices": ["device1", "device2", "device3"],
    "target_groups": ["production_fleet"],
    "rollout_percentage": 25,
    "max_concurrent_updates": 10,
    "batch_size": 50,
    "auto_rollback": true,
    "failure_threshold_percent": 10,
    "scheduled_start": "2025-10-01T00:00:00Z",
    "timeout_minutes": 120,
    "requires_approval": true
  }'
```

**获取活动详情**
```bash
curl -X GET http://localhost:8221/api/v1/campaigns/{campaign_id} \
  -H "Authorization: Bearer <token>"
```

**批准更新活动**
```bash
curl -X POST http://localhost:8221/api/v1/campaigns/{campaign_id}/approve \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_comment": "Approved after testing in staging environment"
  }'
```

**启动更新活动**
```bash
curl -X POST http://localhost:8221/api/v1/campaigns/{campaign_id}/start \
  -H "Authorization: Bearer <token>"
```

**暂停更新活动**
```bash
curl -X POST http://localhost:8221/api/v1/campaigns/{campaign_id}/pause \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Investigating reported issues"
  }'
```

**取消更新活动**
```bash
curl -X POST http://localhost:8221/api/v1/campaigns/{campaign_id}/cancel \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Critical bug discovered"
  }'
```

**回滚更新活动**
```bash
curl -X POST http://localhost:8221/api/v1/campaigns/{campaign_id}/rollback \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "High failure rate detected",
    "target_devices": ["device1", "device2"]
  }'
```

#### 3. 单设备更新

**触发设备更新**
```bash
curl -X POST http://localhost:8221/api/v1/devices/{device_id}/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "firmware_id": "fw_v1.2.0",
    "priority": "high",
    "force": false,
    "pre_update_commands": ["backup_config"],
    "post_update_commands": ["verify_config"]
  }'
```

**获取设备更新历史**
```bash
curl -X GET "http://localhost:8221/api/v1/devices/{device_id}/updates?limit=10" \
  -H "Authorization: Bearer <token>"
```

**回滚设备固件**
```bash
curl -X POST http://localhost:8221/api/v1/devices/{device_id}/rollback \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "target_version": "1.1.0",
    "reason": "Device experiencing issues with new firmware"
  }'
```

#### 4. 批量操作

**批量更新设备**
```bash
curl -X POST http://localhost:8221/api/v1/devices/bulk/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device1", "device2", "device3"],
    "firmware_id": "fw_v1.2.0",
    "update_config": {
      "priority": "normal",
      "max_retries": 3,
      "timeout_minutes": 60
    }
  }'
```

#### 5. 更新状态管理

**获取更新详情**
```bash
curl -X GET http://localhost:8221/api/v1/updates/{update_id} \
  -H "Authorization: Bearer <token>"
```

**取消更新**
```bash
curl -X POST http://localhost:8221/api/v1/updates/{update_id}/cancel \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "User requested cancellation"
  }'
```

**重试失败的更新**
```bash
curl -X POST http://localhost:8221/api/v1/updates/{update_id}/retry \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "max_retries": 3,
    "retry_delay": 300
  }'
```

#### 6. 统计和监控

**获取更新统计**
```bash
curl -X GET http://localhost:8221/api/v1/stats \
  -H "Authorization: Bearer <token>"
```

**获取活动统计**
```bash
curl -X GET http://localhost:8221/api/v1/stats/campaigns/{campaign_id} \
  -H "Authorization: Bearer <token>"
```

## 数据模型

### Firmware
```json
{
  "firmware_id": "string",
  "name": "string",
  "version": "string",
  "description": "string",
  "device_model": "string",
  "manufacturer": "string",
  "min_hardware_version": "string",
  "max_hardware_version": "string",
  "file_size": 1048576,
  "file_url": "string",
  "checksum_md5": "string",
  "checksum_sha256": "string",
  "tags": ["stable", "production"],
  "metadata": {},
  "is_beta": false,
  "is_security_update": true,
  "changelog": "string"
}
```

### UpdateCampaign
```json
{
  "campaign_id": "string",
  "name": "string",
  "firmware_id": "string",
  "status": "created|scheduled|in_progress|completed|failed|cancelled",
  "deployment_strategy": "immediate|scheduled|staged|canary|blue_green",
  "priority": "low|normal|high|critical|emergency",
  "rollout_percentage": 100,
  "target_devices": ["device1", "device2"],
  "auto_rollback": true,
  "failure_threshold_percent": 10
}
```

### DeviceUpdate
```json
{
  "update_id": "string",
  "device_id": "string",
  "campaign_id": "string",
  "firmware_id": "string",
  "status": "scheduled|downloading|installing|completed|failed",
  "progress_percentage": 75.5,
  "from_version": "1.1.0",
  "to_version": "1.2.0",
  "started_at": "2025-09-26T10:00:00Z",
  "completed_at": "2025-09-26T10:30:00Z"
}
```

## 部署策略

### 1. 立即部署 (Immediate)
所有设备同时开始更新
```json
{
  "deployment_strategy": "immediate",
  "max_concurrent_updates": 100
}
```

### 2. 分阶段部署 (Staged)
按百分比逐步推出
```json
{
  "deployment_strategy": "staged",
  "rollout_percentage": 25,
  "batch_size": 50
}
```

### 3. 金丝雀部署 (Canary)
先更新少量设备进行验证
```json
{
  "deployment_strategy": "canary",
  "canary_percentage": 5,
  "canary_duration_minutes": 1440
}
```

### 4. 蓝绿部署 (Blue-Green)
分组切换更新
```json
{
  "deployment_strategy": "blue_green",
  "blue_group": ["device1", "device2"],
  "green_group": ["device3", "device4"]
}
```

## 回滚机制

### 自动回滚触发条件
- 失败率超过阈值
- 设备健康检查失败
- 更新超时
- 关键指标异常

### 配置示例
```json
{
  "auto_rollback": true,
  "failure_threshold_percent": 10,
  "rollback_triggers": [
    "failure_rate",
    "health_check",
    "timeout",
    "metric_threshold"
  ],
  "health_check_config": {
    "endpoint": "/health",
    "expected_status": 200,
    "timeout": 30
  }
}
```

## 最佳实践

### 1. 更新前验证
```bash
# 检查设备兼容性
curl -X POST http://localhost:8221/api/v1/firmware/{firmware_id}/compatibility-check \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device1", "device2"]
  }'
```

### 2. 测试环境验证
- 先在测试设备组验证
- 收集性能和稳定性数据
- 确认无重大问题后推广

### 3. 监控关键指标
```python
# 示例：监控更新进度
import asyncio
import httpx

async def monitor_campaign(campaign_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8221/api/v1/campaigns/{campaign_id}",
                headers=headers
            )
            data = response.json()
            
            print(f"Progress: {data['completed_devices']}/{data['total_devices']}")
            print(f"Failed: {data['failed_devices']}")
            
            if data['status'] in ['completed', 'failed', 'cancelled']:
                break
            
            await asyncio.sleep(10)
```

### 4. 错误处理
```python
def handle_update_failure(update_id, error_code):
    """处理更新失败"""
    if error_code == "CHECKSUM_MISMATCH":
        # 重新下载
        retry_update(update_id)
    elif error_code == "INSUFFICIENT_SPACE":
        # 清理空间后重试
        cleanup_and_retry(update_id)
    elif error_code == "INCOMPATIBLE_VERSION":
        # 标记设备不兼容
        mark_incompatible(update_id)
```

## 集成示例

### 设备端集成
```python
import httpx
import hashlib
import os

class OTAClient:
    def __init__(self, device_id, base_url, token):
        self.device_id = device_id
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def check_updates(self):
        """检查可用更新"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/devices/{self.device_id}/available-updates",
                headers=self.headers
            )
            return response.json()
    
    async def download_firmware(self, firmware_id, progress_callback=None):
        """下载固件"""
        async with httpx.AsyncClient() as client:
            with open(f"firmware_{firmware_id}.bin", "wb") as f:
                async with client.stream(
                    "GET",
                    f"{self.base_url}/api/v1/firmware/{firmware_id}/download",
                    headers=self.headers
                ) as response:
                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total)
    
    def verify_firmware(self, firmware_path, expected_sha256):
        """验证固件完整性"""
        sha256 = hashlib.sha256()
        with open(firmware_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        
        return sha256.hexdigest() == expected_sha256
    
    async def report_status(self, update_id, status, progress=None):
        """报告更新状态"""
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/api/v1/updates/{update_id}/status",
                headers=self.headers,
                json={
                    "status": status,
                    "progress": progress,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
```

### CI/CD 集成
```yaml
# .github/workflows/firmware-release.yml
name: Firmware Release

on:
  release:
    types: [created]

jobs:
  upload-firmware:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Firmware
        run: make build
      
      - name: Upload to OTA Service
        run: |
          curl -X POST ${{ secrets.OTA_SERVICE_URL }}/api/v1/firmware \
            -H "Authorization: Bearer ${{ secrets.OTA_TOKEN }}" \
            -F "metadata=@firmware-metadata.json" \
            -F "file=@firmware.bin"
      
      - name: Create Update Campaign
        run: |
          curl -X POST ${{ secrets.OTA_SERVICE_URL }}/api/v1/campaigns \
            -H "Authorization: Bearer ${{ secrets.OTA_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d @campaign-config.json
```

## 故障排除

### 常见问题

1. **更新失败：DOWNLOAD_FAILED**
   - 检查网络连接
   - 验证固件 URL 可访问
   - 检查存储空间

2. **更新失败：CHECKSUM_MISMATCH**
   - 重新下载固件
   - 验证上传时的校验和
   - 检查传输过程

3. **更新失败：INCOMPATIBLE_VERSION**
   - 检查硬件版本兼容性
   - 验证依赖版本
   - 确认更新路径

4. **高失败率**
   - 检查目标设备状态
   - 分析失败模式
   - 考虑降低并发数

### 日志分析
```bash
# 查看服务日志
tail -f logs/ota_service.log

# 查看特定活动日志
grep "campaign_id=abc123" logs/ota_service.log

# 查看失败原因统计
grep "update_failed" logs/ota_service.log | \
  awk '{print $NF}' | sort | uniq -c
```

## 性能优化

### 配置建议
- 并发更新数：10-50（根据带宽）
- 批次大小：50-100
- 下载超时：300 秒
- 安装超时：600 秒
- 重试间隔：60 秒

### CDN 集成
```json
{
  "cdn_config": {
    "enabled": true,
    "base_url": "https://cdn.iotcorp.com/firmware",
    "cache_control": "max-age=86400",
    "fallback_url": "https://backup.iotcorp.com/firmware"
  }
}
```

## 安全考虑

### 1. 固件签名
- 使用 RSA/ECDSA 签名
- 设备端验证签名
- 证书链验证

### 2. 传输安全
- 强制 HTTPS/TLS
- 证书固定
- 传输加密

### 3. 访问控制
- 基于角色的权限
- 设备白名单
- API 速率限制

## 相关服务

- **Device Service**: 设备注册和生命周期管理
- **Telemetry Service**: 更新后的性能监控
- **Auth Service**: 设备和用户认证
- **Storage Service**: 固件文件存储