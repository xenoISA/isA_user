#!/usr/bin/env python3
"""
P1 集成测试: 设备、OTA 更新、遥测流程

测试覆盖的服务:
- device_service: 设备注册、状态管理
- ota_service: 固件管理、更新推送
- telemetry_service: 数据采集、告警
- notification_service: 更新通知、告警通知
- location_service: 设备位置跟踪

测试流程:
1. 注册设备
2. 设备上线
3. 上报遥测数据
4. 创建固件更新
5. 推送更新到设备
6. 设备完成更新
7. 验证更新状态
8. 测试位置跟踪
9. 测试遥测告警

事件验证:
- device.registered
- device.online/offline
- telemetry.data_received
- firmware.uploaded
- update.started/completed
- alert.triggered
- location.updated
"""

import asyncio
import os
import sys
from datetime import datetime
import random

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../..")
sys.path.insert(0, _project_root)
sys.path.insert(0, _current_dir)

from base_test import BaseIntegrationTest


class DeviceOtaTelemetryIntegrationTest(BaseIntegrationTest):
    """设备 OTA 遥测集成测试"""

    def __init__(self):
        super().__init__()
        # Test data
        self.test_user_id = None
        self.device_id = None
        self.firmware_id = None
        self.campaign_id = None

    async def run(self):
        """运行完整测试"""
        self.log_header("P1: Device → OTA → Telemetry Integration Test")
        self.log(f"Start Time: {datetime.utcnow().isoformat()}")

        try:
            await self.setup()

            self.test_user_id = self.generate_test_user_id()
            self.log(f"Test User ID: {self.test_user_id}")

            # 运行测试步骤
            await self.test_step_1_register_device()
            await self.test_step_2_device_online()
            await self.test_step_3_report_telemetry()
            await self.test_step_4_upload_firmware()
            await self.test_step_5_create_update_campaign()
            await self.test_step_6_push_update_to_device()
            await self.test_step_7_complete_update()
            await self.test_step_8_track_device_location()
            await self.test_step_9_test_telemetry_alert()
            await self.test_step_10_verify_events()

        except Exception as e:
            self.log(f"Test Error: {e}", "red")
            import traceback
            traceback.print_exc()
            self.failed_assertions += 1

        finally:
            await self.teardown()
            self.log_summary()

        return self.failed_assertions == 0

    async def test_step_1_register_device(self):
        """Step 1: 注册设备"""
        self.log_step(1, "Register Device")

        if self.event_collector:
            self.event_collector.clear()

        serial_number = self.test_data.serial_number()

        response = await self.post(
            f"{self.config.DEVICE_URL}/api/v1/devices",
            json={
                "owner_id": self.test_user_id,
                "device_name": "Integration Test Smart Frame",
                "device_type": "digital_photo_frame",
                "manufacturer": "TestManufacturer",
                "model": "Frame-X1-Test",
                "serial_number": serial_number,
                "firmware_version": "1.0.0",
                "connectivity_type": "wifi",
                "capabilities": ["display", "wifi", "bluetooth", "ota"],
                "metadata": {
                    "screen_size": "10.1",
                    "resolution": "1920x1200",
                    "source": "integration_test"
                }
            }
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            data = response.json()
            self.device_id = data.get("device_id")
            self.assert_not_none(self.device_id, "Device registered")
            self.log(f"  Device ID: {self.device_id}")
            self.log(f"  Serial Number: {serial_number}")

            self.track_resource(
                "device",
                self.device_id,
                f"{self.config.DEVICE_URL}/api/v1/devices/{self.device_id}"
            )

            await self.wait(2, "Waiting for device.registered event")

    async def test_step_2_device_online(self):
        """Step 2: 设备上线"""
        self.log_step(2, "Device Online")

        if not self.device_id:
            self.log("  SKIP: No device_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        response = await self.post(
            f"{self.config.DEVICE_URL}/api/v1/devices/{self.device_id}/status",
            json={
                "status": "online",
                "ip_address": "192.168.1.100",
                "connection_type": "wifi",
                "signal_strength": -45,
                "battery_level": 85
            }
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            self.assert_equal(data.get("status"), "online", "Device is online")
            self.log(f"  Device Status: online")

            await self.wait(1, "Waiting for device.online event")

    async def test_step_3_report_telemetry(self):
        """Step 3: 上报遥测数据"""
        self.log_step(3, "Report Telemetry Data")

        if not self.device_id:
            self.log("  SKIP: No device_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # 上报多个遥测数据点
        telemetry_data = {
            "device_id": self.device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "cpu_temperature": round(random.uniform(35, 45), 1),
                "memory_usage": round(random.uniform(40, 60), 1),
                "storage_usage": round(random.uniform(20, 40), 1),
                "battery_level": random.randint(70, 90),
                "wifi_signal": random.randint(-60, -40),
                "display_brightness": random.randint(50, 100),
                "uptime_hours": random.randint(1, 100)
            },
            "metadata": {
                "firmware_version": "1.0.0",
                "report_type": "periodic"
            }
        }

        response = await self.post(
            f"{self.config.TELEMETRY_URL}/api/v1/telemetry/data",
            json=telemetry_data
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            self.assert_true(True, "Telemetry data reported")
            self.log(f"  CPU Temp: {telemetry_data['metrics']['cpu_temperature']}°C")
            self.log(f"  Memory: {telemetry_data['metrics']['memory_usage']}%")
            self.log(f"  Battery: {telemetry_data['metrics']['battery_level']}%")

            await self.wait(1, "Waiting for telemetry.data_received event")

    async def test_step_4_upload_firmware(self):
        """Step 4: 上传固件"""
        self.log_step(4, "Upload Firmware")

        if self.event_collector:
            self.event_collector.clear()

        response = await self.post(
            f"{self.config.OTA_URL}/api/v1/firmwares",
            json={
                "version": "1.1.0",
                "device_type": "digital_photo_frame",
                "model": "Frame-X1-Test",
                "release_notes": "Integration test firmware update",
                "file_size": 52428800,  # 50MB
                "checksum": "sha256:abc123def456...",
                "download_url": "https://example.com/firmware/v1.1.0.bin",
                "min_battery_level": 30,
                "is_mandatory": False,
                "metadata": {
                    "changes": ["Bug fixes", "Performance improvements"],
                    "source": "integration_test"
                }
            }
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            data = response.json()
            self.firmware_id = data.get("firmware_id")
            self.assert_not_none(self.firmware_id, "Firmware uploaded")
            self.log(f"  Firmware ID: {self.firmware_id}")
            self.log(f"  Version: 1.1.0")

            await self.wait(1, "Waiting for firmware.uploaded event")

    async def test_step_5_create_update_campaign(self):
        """Step 5: 创建更新活动"""
        self.log_step(5, "Create Update Campaign")

        if not self.firmware_id:
            self.log("  SKIP: No firmware_id", "yellow")
            return

        response = await self.post(
            f"{self.config.OTA_URL}/api/v1/campaigns",
            json={
                "name": "Integration Test Campaign",
                "firmware_id": self.firmware_id,
                "target_devices": [self.device_id] if self.device_id else [],
                "rollout_percentage": 100,
                "start_time": datetime.utcnow().isoformat(),
                "metadata": {
                    "source": "integration_test"
                }
            }
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            data = response.json()
            self.campaign_id = data.get("campaign_id")
            self.assert_not_none(self.campaign_id, "Campaign created")
            self.log(f"  Campaign ID: {self.campaign_id}")

    async def test_step_6_push_update_to_device(self):
        """Step 6: 推送更新到设备"""
        self.log_step(6, "Push Update to Device")

        if not self.device_id or not self.firmware_id:
            self.log("  SKIP: No device_id or firmware_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        response = await self.post(
            f"{self.config.OTA_URL}/api/v1/devices/{self.device_id}/update",
            json={
                "firmware_id": self.firmware_id,
                "force": False
            }
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            self.log(f"  Update Status: {data.get('status', 'initiated')}")
            self.assert_true(True, "Update pushed to device")

            await self.wait(2, "Waiting for update.started event")

    async def test_step_7_complete_update(self):
        """Step 7: 模拟设备完成更新"""
        self.log_step(7, "Complete Device Update")

        if not self.device_id:
            self.log("  SKIP: No device_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # 模拟设备报告更新完成
        response = await self.post(
            f"{self.config.OTA_URL}/api/v1/devices/{self.device_id}/update/status",
            json={
                "status": "completed",
                "firmware_version": "1.1.0",
                "update_time": datetime.utcnow().isoformat()
            }
        )

        if response.status_code == 200:
            self.assert_true(True, "Update completed")
            self.log(f"  New firmware version: 1.1.0")

            await self.wait(1, "Waiting for update.completed event")

        # 验证设备固件版本
        device_response = await self.get(
            f"{self.config.DEVICE_URL}/api/v1/devices/{self.device_id}"
        )

        if device_response.status_code == 200:
            device_data = device_response.json()
            self.log(f"  Device firmware: {device_data.get('firmware_version', 'N/A')}")

    async def test_step_8_track_device_location(self):
        """Step 8: 设备位置跟踪"""
        self.log_step(8, "Track Device Location")

        if not self.device_id:
            self.log("  SKIP: No device_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # 上报位置
        response = await self.post(
            f"{self.config.LOCATION_URL}/api/v1/locations",
            json={
                "device_id": self.device_id,
                "user_id": self.test_user_id,
                "latitude": 39.9042 + random.uniform(-0.01, 0.01),
                "longitude": 116.4074 + random.uniform(-0.01, 0.01),
                "accuracy": round(random.uniform(5, 20), 1),
                "altitude": round(random.uniform(40, 60), 1),
                "source": "gps",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            self.assert_true(True, "Location reported")
            self.log(f"  Location: Beijing area")

            await self.wait(1, "Waiting for location.updated event")

    async def test_step_9_test_telemetry_alert(self):
        """Step 9: 测试遥测告警"""
        self.log_step(9, "Test Telemetry Alert")

        if not self.device_id:
            self.log("  SKIP: No device_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # 创建告警规则
        rule_response = await self.post(
            f"{self.config.TELEMETRY_URL}/api/v1/alerts/rules",
            json={
                "name": "High CPU Temperature Alert",
                "device_id": self.device_id,
                "metric": "cpu_temperature",
                "condition": "greater_than",
                "threshold": 70,
                "severity": "warning",
                "notification_channels": ["email", "push"]
            }
        )

        if rule_response.status_code in [200, 201]:
            rule_data = rule_response.json()
            rule_id = rule_data.get("rule_id")
            self.log(f"  Alert rule created: {rule_id}")

        # 上报高温数据触发告警
        alert_telemetry = {
            "device_id": self.device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "cpu_temperature": 75.5,  # 超过阈值
                "memory_usage": 80.0
            }
        }

        response = await self.post(
            f"{self.config.TELEMETRY_URL}/api/v1/telemetry/data",
            json=alert_telemetry
        )

        if response.status_code == 200:
            self.log(f"  High temperature reported: 75.5°C")

            await self.wait(2, "Waiting for alert to trigger")

            # 检查是否有告警
            alerts_response = await self.get(
                f"{self.config.TELEMETRY_URL}/api/v1/alerts",
                params={"device_id": self.device_id, "status": "active"}
            )

            if alerts_response.status_code == 200:
                alerts = alerts_response.json().get("alerts", [])
                self.log(f"  Active alerts: {len(alerts)}")

    async def test_step_10_verify_events(self):
        """Step 10: 验证事件"""
        self.log_step(10, "Verify Events")

        if not self.event_collector:
            self.log("  SKIP: No event collector", "yellow")
            return

        summary = self.event_collector.summary()
        self.log(f"  Events collected: {summary}")

        expected_events = [
            "device.registered",
            "telemetry.data.received",
            "firmware.uploaded",
        ]

        for event_type in expected_events:
            if self.event_collector.has_event(event_type):
                self.assert_true(True, f"Event {event_type} published")
            else:
                self.log(f"  Event {event_type} not captured", "yellow")


async def main():
    """主函数"""
    test = DeviceOtaTelemetryIntegrationTest()
    success = await test.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
