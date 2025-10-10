"""
Device Management Service - Business Logic

设备管理服务业务逻辑
"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import asyncio
from .models import (
    DeviceStatus, DeviceType, SecurityLevel,
    DeviceResponse, DeviceAuthResponse, DeviceStatsResponse,
    DeviceHealthResponse, DeviceGroupResponse
)

logger = logging.getLogger("device_service")

# Import MQTT client from core
try:
    from core.mqtt_client import create_command_client
except ImportError:
    create_command_client = None
    logger.warning("MQTT client not available - commands will be simulated")


class DeviceService:
    """设备管理服务"""
    
    def __init__(self):
        self.secret_key = "device_service_secret_key_2024"  # 实际应从环境变量读取
        self.token_expiry = 86400  # 24小时
        
        # Initialize MQTT command client
        self.mqtt_command_client = None
        self._init_mqtt_command_client()
        
    async def register_device(self, user_id: str, device_data: Dict[str, Any]) -> Optional[DeviceResponse]:
        """注册新设备"""
        try:
            # 生成设备ID
            device_id = self._generate_device_id(
                device_data["serial_number"],
                device_data["mac_address"] if "mac_address" in device_data else ""
            )
            
            # 创建设备记录
            device = DeviceResponse(
                device_id=device_id,
                device_name=device_data["device_name"],
                device_type=device_data["device_type"],
                manufacturer=device_data["manufacturer"],
                model=device_data["model"],
                serial_number=device_data["serial_number"],
                firmware_version=device_data["firmware_version"],
                hardware_version=device_data.get("hardware_version"),
                mac_address=device_data.get("mac_address"),
                connectivity_type=device_data["connectivity_type"],
                security_level=device_data.get("security_level", SecurityLevel.STANDARD),
                status=DeviceStatus.PENDING,
                location=device_data.get("location"),
                metadata=device_data.get("metadata", {}),
                group_id=device_data.get("group_id"),
                tags=device_data.get("tags", []),
                last_seen=None,
                registered_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                user_id=user_id,
                organization_id=None,
                total_commands=0,
                total_telemetry_points=0,
                uptime_percentage=0.0
            )
            
            logger.info(f"Device registered: {device_id}")
            return device
            
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return None
    
    async def authenticate_device(self, device_id: str, auth_data: Dict[str, Any]) -> Optional[DeviceAuthResponse]:
        """设备认证"""
        try:
            # 验证设备凭证（简化版本）
            # 实际应该验证密钥、证书等
            
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
            await self.update_device_status(device_id, DeviceStatus.ACTIVE)
            
            logger.info(f"Device authenticated: {device_id}")
            return auth_response
            
        except Exception as e:
            logger.error(f"Error authenticating device: {e}")
            return None
    
    async def update_device_status(self, device_id: str, status: DeviceStatus) -> bool:
        """更新设备状态"""
        try:
            # 更新设备状态和最后上线时间
            logger.info(f"Device {device_id} status updated to {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return False
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """向设备发送命令"""
        try:
            if self.mqtt_command_client and self.mqtt_command_client.is_connected():
                # 使用 MQTT client 发送命令
                command_id = self.mqtt_command_client.send_device_command(
                    device_id=device_id,
                    command=command["command"],
                    parameters=command.get("parameters", {}),
                    timeout=command.get("timeout", 30),
                    priority=command.get("priority", 1),
                    require_ack=command.get("require_ack", True)
                )
                
                if command_id:
                    logger.info(f"Command sent via MQTT to device {device_id}: {command['command']}")
                    return {
                        "success": True,
                        "command_id": command_id,
                        "status": "published",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                else:
                    logger.error(f"Failed to send command via MQTT to device {device_id}")
                    return {
                        "success": False,
                        "error": "Failed to publish command via MQTT"
                    }
            else:
                # 回退到模拟模式
                logger.warning("MQTT client not connected, simulating command send")
                command_id = secrets.token_hex(16)
                await asyncio.sleep(0.1)  # 模拟网络延迟
                
                logger.info(f"Command simulated for device {device_id}: {command['command']}")
                return {
                    "success": True,
                    "command_id": command_id,
                    "status": "simulated",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            
        except Exception as e:
            logger.error(f"Error sending command to device: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_device_health(self, device_id: str) -> Optional[DeviceHealthResponse]:
        """获取设备健康状态"""
        try:
            # 模拟健康检查数据
            health = DeviceHealthResponse(
                device_id=device_id,
                status=DeviceStatus.ACTIVE,
                health_score=95.5,
                cpu_usage=23.4,
                memory_usage=45.6,
                disk_usage=67.8,
                temperature=35.2,
                battery_level=87.0,
                signal_strength=-65.0,  # dBm
                error_count=0,
                warning_count=2,
                last_error=None,
                last_check=datetime.utcnow(),
                diagnostics={
                    "network_latency": 12.5,
                    "packet_loss": 0.1,
                    "uptime_hours": 168.5
                }
            )
            
            return health
            
        except Exception as e:
            logger.error(f"Error getting device health: {e}")
            return None
    
    async def get_device_stats(self, user_id: str) -> Optional[DeviceStatsResponse]:
        """获取设备统计信息"""
        try:
            # 模拟统计数据
            stats = DeviceStatsResponse(
                total_devices=156,
                active_devices=142,
                inactive_devices=10,
                error_devices=4,
                devices_by_type={
                    DeviceType.SENSOR: 68,
                    DeviceType.ACTUATOR: 32,
                    DeviceType.GATEWAY: 12,
                    DeviceType.SMART_HOME: 28,
                    DeviceType.CAMERA: 16
                },
                devices_by_status={
                    DeviceStatus.ACTIVE: 142,
                    DeviceStatus.INACTIVE: 10,
                    DeviceStatus.ERROR: 4
                },
                devices_by_connectivity={
                    "wifi": 98,
                    "ethernet": 24,
                    "4g": 18,
                    "zigbee": 16
                },
                avg_uptime=98.5,
                total_data_points=1567890,
                last_24h_activity={
                    "commands_sent": 342,
                    "telemetry_received": 89456,
                    "alerts_triggered": 12,
                    "firmware_updates": 3
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
            
            group = DeviceGroupResponse(
                group_id=group_id,
                group_name=group_data["group_name"],
                description=group_data.get("description"),
                parent_group_id=group_data.get("parent_group_id"),
                device_count=0,
                tags=group_data.get("tags", []),
                metadata=group_data.get("metadata", {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            logger.info(f"Device group created: {group_id}")
            return group
            
        except Exception as e:
            logger.error(f"Error creating device group: {e}")
            return None
    
    async def decommission_device(self, device_id: str) -> bool:
        """停用设备"""
        try:
            # 更新设备状态为已停用
            await self.update_device_status(device_id, DeviceStatus.DECOMMISSIONED)
            
            # 撤销设备的所有令牌
            # 清理设备相关的资源
            
            logger.info(f"Device decommissioned: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error decommissioning device: {e}")
            return False
    
    def _generate_device_id(self, serial_number: str, mac_address: str = "") -> str:
        """生成设备ID"""
        unique_string = f"{serial_number}:{mac_address}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32]
    
    def _generate_access_token(self, device_id: str) -> str:
        """生成访问令牌"""
        payload = {
            "device_id": device_id,
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiry),
            "iat": datetime.utcnow(),
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