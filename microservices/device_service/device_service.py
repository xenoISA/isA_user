"""
Device Management Service - Business Logic

设备管理服务业务逻辑 - 集成 PostgreSQL Repository
"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import logging
import asyncio

from .device_repository import DeviceRepository
from .models import (
    DeviceStatus, DeviceType, SecurityLevel,
    DeviceResponse, DeviceAuthResponse, DeviceStatsResponse,
    DeviceHealthResponse, DeviceGroupResponse
)
# Import event bus components
from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger("device_service")

# Import MQTT client from core
try:
    from core.mqtt_client import create_command_client
except ImportError:
    create_command_client = None
    logger.warning("MQTT client not available - commands will be simulated")


class DeviceService:
    """设备管理服务 - 带数据库持久化"""

    def __init__(self, event_bus=None):
        self.secret_key = "device_service_secret_key_2024"  # 实际应从环境变量读取
        self.token_expiry = 86400  # 24小时
        self.event_bus = event_bus

        # Initialize repository
        self.device_repo = DeviceRepository()

        # Initialize MQTT command client
        self.mqtt_command_client = None
        self._init_mqtt_command_client()

    async def register_device(self, user_id: str, device_data: Dict[str, Any]) -> Optional[DeviceResponse]:
        """注册新设备"""
        try:
            # 生成设备ID
            device_id = self._generate_device_id(
                device_data["serial_number"],
                device_data.get("mac_address", "")
            )

            # 准备设备数据
            device_dict = {
                "device_id": device_id,
                "user_id": user_id,
                "device_name": device_data["device_name"],
                "device_type": device_data["device_type"],
                "manufacturer": device_data["manufacturer"],
                "model": device_data["model"],
                "serial_number": device_data["serial_number"],
                "firmware_version": device_data["firmware_version"],
                "hardware_version": device_data.get("hardware_version"),
                "mac_address": device_data.get("mac_address"),
                "connectivity_type": device_data["connectivity_type"],
                "security_level": device_data.get("security_level", "standard"),
                "status": "pending",
                "location": device_data.get("location"),
                "metadata": device_data.get("metadata", {}),
                "group_id": device_data.get("group_id"),
                "tags": device_data.get("tags", [])
            }

            # 保存到数据库
            device = await self.device_repo.create_device(device_dict)

            if not device:
                raise Exception("Failed to create device in database")

            logger.info(f"Device registered: {device_id} for user {user_id}")

            # Publish device.registered event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.DEVICE_REGISTERED,
                        source=ServiceSource.DEVICE_SERVICE,
                        data={
                            "device_id": device_id,
                            "device_name": device.device_name,
                            "device_type": device.device_type,
                            "user_id": user_id,
                            "manufacturer": device.manufacturer,
                            "model": device.model,
                            "serial_number": device.serial_number,
                            "connectivity_type": device.connectivity_type,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published device.registered event for device {device_id}")
                except Exception as e:
                    logger.error(f"Failed to publish device.registered event: {e}")

            return device

        except Exception as e:
            logger.error(f"Error registering device: {e}")
            raise

    async def get_device(self, device_id: str) -> Optional[DeviceResponse]:
        """获取设备信息"""
        try:
            device = await self.device_repo.get_device_by_id(device_id)

            if not device:
                logger.warning(f"Device not found: {device_id}")
                return None

            return device

        except Exception as e:
            logger.error(f"Error getting device: {e}")
            return None

    async def list_user_devices(
        self,
        user_id: str,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DeviceResponse]:
        """获取用户设备列表"""
        try:
            devices = await self.device_repo.list_user_devices(
                user_id=user_id,
                device_type=device_type,
                status=status,
                limit=limit,
                offset=offset
            )

            logger.info(f"Listed {len(devices)} devices for user {user_id}")
            return devices

        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []

    async def update_device(
        self,
        device_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[DeviceResponse]:
        """更新设备信息"""
        try:
            # 更新数据库
            success = await self.device_repo.update_device(device_id, update_data)

            if not success:
                logger.warning(f"Failed to update device: {device_id}")
                return None

            # 返回更新后的设备
            device = await self.device_repo.get_device_by_id(device_id)

            logger.info(f"Device updated: {device_id}")
            return device

        except Exception as e:
            logger.error(f"Error updating device: {e}")
            return None

    async def authenticate_device(self, device_id: str, auth_data: Dict[str, Any]) -> Optional[DeviceAuthResponse]:
        """设备认证"""
        try:
            # 验证设备存在
            device = await self.device_repo.get_device_by_id(device_id)

            if not device:
                logger.warning(f"Device not found for authentication: {device_id}")
                return None

            # TODO: 验证设备凭证（device_secret, certificate等）
            # 实际应该从 auth_service 验证

            # 生成访问令牌
            access_token = self._generate_access_token(device_id)
            refresh_token = secrets.token_urlsafe(32)

            auth_response = DeviceAuthResponse(
                device_id=device_id,
                access_token=access_token,
                token_type="Bearer",
                expires_in=self.token_expiry,
                refresh_token=refresh_token,
                scope="device:all",
                mqtt_broker="mqtt://localhost:1883",
                mqtt_topic=f"devices/{device_id}/"
            )

            # 更新设备状态为活跃
            await self.update_device_status(device_id, DeviceStatus.ACTIVE, datetime.now(timezone.utc))

            logger.info(f"Device authenticated: {device_id}")
            return auth_response

        except Exception as e:
            logger.error(f"Error authenticating device: {e}")
            return None

    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus,
        last_seen: Optional[datetime] = None
    ) -> bool:
        """更新设备状态"""
        try:
            success = await self.device_repo.update_device_status(
                device_id,
                status,
                last_seen or datetime.now(timezone.utc)
            )

            if success:
                logger.info(f"Device {device_id} status updated to {status}")

                # Publish device.online or device.offline event based on status
                if self.event_bus and status in [DeviceStatus.ACTIVE, DeviceStatus.INACTIVE]:
                    try:
                        # Get device details for event
                        device = await self.device_repo.get_device_by_id(device_id)

                        if device:
                            event_type = EventType.DEVICE_ONLINE if status == DeviceStatus.ACTIVE else EventType.DEVICE_OFFLINE

                            event = Event(
                                event_type=event_type,
                                source=ServiceSource.DEVICE_SERVICE,
                                data={
                                    "device_id": device_id,
                                    "device_name": device.device_name,
                                    "device_type": device.device_type,
                                    "status": status.value if hasattr(status, 'value') else str(status),
                                    "last_seen": last_seen.isoformat() if last_seen else datetime.now(timezone.utc).isoformat(),
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                            )
                            await self.event_bus.publish_event(event)
                            logger.info(f"Published {event_type.value} event for device {device_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish device status event: {e}")

            return success

        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return False

    async def send_command(self, device_id: str, user_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """向设备发送命令"""
        try:
            command_id = secrets.token_hex(16)

            # 保存命令到数据库
            command_data = {
                "command_id": command_id,
                "device_id": device_id,
                "user_id": user_id,
                "command": command["command"],
                "parameters": command.get("parameters", {}),
                "timeout": command.get("timeout", 30),
                "priority": command.get("priority", 1),
                "require_ack": command.get("require_ack", True)
            }

            await self.device_repo.create_device_command(command_data)

            # 通过 MQTT 发送命令
            if self.mqtt_command_client and self.mqtt_command_client.is_connected():
                # 使用 MQTT client 发送命令
                mqtt_command_id = self.mqtt_command_client.send_device_command(
                    device_id=device_id,
                    command=command["command"],
                    parameters=command.get("parameters", {}),
                    timeout=command.get("timeout", 30),
                    priority=command.get("priority", 1),
                    require_ack=command.get("require_ack", True)
                )

                if mqtt_command_id:
                    await self.device_repo.update_command_status(command_id, "sent")
                    logger.info(f"Command sent via MQTT to device {device_id}: {command['command']}")

                    # Publish device.command_sent event
                    if self.event_bus:
                        try:
                            event = Event(
                                event_type=EventType.DEVICE_COMMAND_SENT,
                                source=ServiceSource.DEVICE_SERVICE,
                                data={
                                    "command_id": command_id,
                                    "device_id": device_id,
                                    "user_id": user_id,
                                    "command": command["command"],
                                    "parameters": command.get("parameters", {}),
                                    "priority": command.get("priority", 1),
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                            )
                            await self.event_bus.publish_event(event)
                            logger.info(f"Published device.command_sent event for command {command_id}")
                        except Exception as e:
                            logger.error(f"Failed to publish device.command_sent event: {e}")

                    return {
                        "success": True,
                        "command_id": command_id,
                        "status": "sent",
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                    }
                else:
                    await self.device_repo.update_command_status(command_id, "failed", error_message="MQTT send failed")
                    return {
                        "success": False,
                        "command_id": command_id,
                        "error": "Failed to publish command via MQTT"
                    }
            else:
                # 模拟发送
                logger.warning("MQTT client not connected, simulating command send")
                await asyncio.sleep(0.1)  # 模拟网络延迟
                await self.device_repo.update_command_status(command_id, "sent")

                logger.info(f"Command simulated for device {device_id}: {command['command']}")

                # Publish device.command_sent event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.DEVICE_COMMAND_SENT,
                            source=ServiceSource.DEVICE_SERVICE,
                            data={
                                "command_id": command_id,
                                "device_id": device_id,
                                "user_id": user_id,
                                "command": command["command"],
                                "parameters": command.get("parameters", {}),
                                "priority": command.get("priority", 1),
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published device.command_sent event for command {command_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish device.command_sent event: {e}")

                return {
                    "success": True,
                    "command_id": command_id,
                    "status": "simulated",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                }

        except Exception as e:
            logger.error(f"Error sending command to device: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_device_health(self, device_id: str) -> Optional[DeviceHealthResponse]:
        """获取设备健康状态 - 从 telemetry_service 获取实际数据"""
        try:
            # 验证设备存在
            device = await self.device_repo.get_device_by_id(device_id)

            if not device:
                return None

            # 从 telemetry_service 获取实际健康数据
            try:
                from microservices.telemetry_service.client import TelemetryServiceClient

                async with TelemetryServiceClient() as telemetry_client:
                    # 获取设备统计数据
                    device_stats = await telemetry_client.get_device_stats(device_id)

                    if device_stats:
                        # 从实际遥测数据构建健康响应
                        metrics = device_stats.get("metrics", {})

                        health = DeviceHealthResponse(
                            device_id=device_id,
                            status=device.status,
                            health_score=metrics.get("health_score", 95.5),
                            cpu_usage=metrics.get("cpu_usage", 0.0),
                            memory_usage=metrics.get("memory_usage", 0.0),
                            disk_usage=metrics.get("disk_usage", 0.0),
                            temperature=metrics.get("temperature", 0.0),
                            battery_level=metrics.get("battery_level", None),
                            signal_strength=metrics.get("signal_strength", None),
                            error_count=device_stats.get("error_count", 0),
                            warning_count=device_stats.get("warning_count", 0),
                            last_error=device_stats.get("last_error"),
                            last_check=datetime.now(timezone.utc),
                            diagnostics=device_stats.get("diagnostics", {})
                        )

                        return health
            except Exception as telemetry_error:
                logger.warning(f"Failed to get telemetry data for device {device_id}: {telemetry_error}")
                # 如果 telemetry service 不可用，返回基于设备状态的简化健康信息

            # 降级返回基于设备状态的简化健康数据
            health = DeviceHealthResponse(
                device_id=device_id,
                status=device.status,
                health_score=90.0 if device.status == "active" else 50.0,
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                temperature=0.0,
                battery_level=None,
                signal_strength=None,
                error_count=0,
                warning_count=0,
                last_error=None,
                last_check=datetime.now(timezone.utc),
                diagnostics={"note": "Telemetry data unavailable"}
            )

            return health

        except Exception as e:
            logger.error(f"Error getting device health: {e}")
            return None

    async def get_device_stats(self, user_id: str) -> Optional[DeviceStatsResponse]:
        """获取设备统计信息"""
        try:
            # 获取用户所有设备
            devices = await self.device_repo.list_user_devices(user_id, limit=1000)

            # 统计数据
            total_devices = len(devices)
            active_devices = len([d for d in devices if d.status == DeviceStatus.ACTIVE])
            inactive_devices = len([d for d in devices if d.status == DeviceStatus.INACTIVE])
            error_devices = len([d for d in devices if d.status == DeviceStatus.ERROR])

            devices_by_type = {}
            for device in devices:
                device_type = device.device_type
                devices_by_type[device_type] = devices_by_type.get(device_type, 0) + 1

            devices_by_status = {}
            for device in devices:
                status = device.status
                devices_by_status[status] = devices_by_status.get(status, 0) + 1

            devices_by_connectivity = {}
            for device in devices:
                connectivity = device.connectivity_type
                devices_by_connectivity[connectivity] = devices_by_connectivity.get(connectivity, 0) + 1

            # 计算平均正常运行时间
            avg_uptime = sum([d.uptime_percentage for d in devices]) / max(total_devices, 1)

            stats = DeviceStatsResponse(
                total_devices=total_devices,
                active_devices=active_devices,
                inactive_devices=inactive_devices,
                error_devices=error_devices,
                devices_by_type=devices_by_type,
                devices_by_status=devices_by_status,
                devices_by_connectivity=devices_by_connectivity,
                avg_uptime=round(avg_uptime, 2),
                total_data_points=sum([d.total_telemetry_points for d in devices]),
                last_24h_activity={
                    "commands_sent": sum([d.total_commands for d in devices]),
                    "telemetry_received": sum([d.total_telemetry_points for d in devices]),
                    "alerts_triggered": 0,  # TODO: 从 alerts 表获取
                    "firmware_updates": 0   # TODO: 从 OTA 服务获取
                }
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting device stats: {e}")
            return None

    async def create_device_group(self, user_id: str, group_data: Dict[str, Any]) -> Optional[DeviceGroupResponse]:
        """创建设备组"""
        try:
            group_id = secrets.token_hex(16)

            group_dict = {
                "group_id": group_id,
                "user_id": user_id,
                "group_name": group_data["group_name"],
                "description": group_data.get("description"),
                "parent_group_id": group_data.get("parent_group_id"),
                "tags": group_data.get("tags", []),
                "metadata": group_data.get("metadata", {})
            }

            group = await self.device_repo.create_device_group(group_dict)

            if not group:
                raise Exception("Failed to create device group")

            logger.info(f"Device group created: {group_id} for user {user_id}")
            return group

        except Exception as e:
            logger.error(f"Error creating device group: {e}")
            raise

    async def decommission_device(self, device_id: str) -> bool:
        """停用设备"""
        try:
            # 软删除 - 设置状态为 decommissioned
            success = await self.device_repo.delete_device(device_id)

            if success:
                # TODO: 撤销设备的所有令牌（调用 auth_service）
                # TODO: 清理设备相关的资源
                logger.info(f"Device decommissioned: {device_id}")

            return success

        except Exception as e:
            logger.error(f"Error decommissioning device: {e}")
            return False

    def _generate_device_id(self, serial_number: str, mac_address: str = "") -> str:
        """生成设备ID"""
        unique_string = f"{serial_number}:{mac_address}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]

    def _generate_access_token(self, device_id: str) -> str:
        """生成访问令牌"""
        payload = {
            "device_id": device_id,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=self.token_expiry),
            "iat": datetime.now(timezone.utc),
            "scope": "device:all"
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def _init_mqtt_command_client(self):
        """初始化MQTT命令客户端"""
        try:
            if create_command_client:
                self.mqtt_command_client = create_command_client()
                self.mqtt_command_client.connect_async()
                logger.info("MQTT command client initialized for device service")
            else:
                logger.warning("MQTT client not available - commands will be simulated")

        except Exception as e:
            logger.error(f"Failed to initialize MQTT command client: {e}")
            self.mqtt_command_client = None

    async def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            return await self.device_repo.check_connection()
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
