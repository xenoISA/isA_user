"""
Device Management Service - Data Models

设备管理服务数据模型，包含设备注册、认证、生命周期管理等
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class DeviceType(str, Enum):
    """设备类型"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    SMART_HOME = "smart_home"
    INDUSTRIAL = "industrial"
    MEDICAL = "medical"
    AUTOMOTIVE = "automotive"
    WEARABLE = "wearable"
    CAMERA = "camera"
    CONTROLLER = "controller"


class DeviceStatus(str, Enum):
    """设备状态"""
    PENDING = "pending"  # 待激活
    ACTIVE = "active"  # 在线活跃
    INACTIVE = "inactive"  # 离线
    MAINTENANCE = "maintenance"  # 维护中
    ERROR = "error"  # 故障
    DECOMMISSIONED = "decommissioned"  # 已停用


class ConnectivityType(str, Enum):
    """连接类型"""
    WIFI = "wifi"
    ETHERNET = "ethernet"
    CELLULAR_4G = "4g"
    CELLULAR_5G = "5g"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    LORA = "lora"
    NB_IOT = "nb-iot"
    MQTT = "mqtt"
    COAP = "coap"


class SecurityLevel(str, Enum):
    """安全级别"""
    NONE = "none"
    BASIC = "basic"  # 基础认证
    STANDARD = "standard"  # 标准加密
    HIGH = "high"  # 高级加密 + 证书
    CRITICAL = "critical"  # 关键设备，多重认证


# ==================
# Request Models
# ==================

class DeviceRegistrationRequest(BaseModel):
    """设备注册请求"""
    device_name: str = Field(..., min_length=1, max_length=200)
    device_type: DeviceType
    manufacturer: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    serial_number: str = Field(..., min_length=1, max_length=100)
    firmware_version: str = Field(..., min_length=1, max_length=50)
    hardware_version: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, pattern="^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
    connectivity_type: ConnectivityType
    security_level: SecurityLevel = SecurityLevel.STANDARD
    location: Optional[Dict[str, Any]] = None  # {latitude, longitude, address, etc.}
    metadata: Optional[Dict[str, Any]] = None
    group_id: Optional[str] = None  # 设备组ID
    tags: Optional[List[str]] = []


class DeviceUpdateRequest(BaseModel):
    """设备更新请求"""
    device_name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[DeviceStatus] = None
    firmware_version: Optional[str] = Field(None, max_length=50)
    location: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    group_id: Optional[str] = None
    tags: Optional[List[str]] = None


class DeviceAuthRequest(BaseModel):
    """设备认证请求"""
    device_id: str
    device_secret: str  # 设备密钥（与 auth_service 保持一致）
    certificate: Optional[str] = None  # X.509证书（可选，未来扩展）
    token: Optional[str] = None  # JWT或其他token（可选，未来扩展）
    auth_type: str = "secret_key"  # secret_key, certificate, token


class DeviceCommandRequest(BaseModel):
    """设备命令请求"""
    command: str = Field(..., min_length=1, max_length=100)
    parameters: Optional[Dict[str, Any]] = {}
    timeout: int = Field(30, ge=1, le=300)  # 超时时间（秒）
    priority: int = Field(1, ge=1, le=10)  # 优先级 1-10
    require_ack: bool = True  # 是否需要确认


class DeviceGroupRequest(BaseModel):
    """设备组请求"""
    group_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_group_id: Optional[str] = None  # 父组ID，支持层级
    tags: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}


# ==================
# Response Models
# ==================

class DeviceResponse(BaseModel):
    """设备响应"""
    device_id: str
    device_name: str
    device_type: DeviceType
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    hardware_version: Optional[str]
    mac_address: Optional[str]
    connectivity_type: ConnectivityType
    security_level: SecurityLevel
    status: DeviceStatus
    location: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    group_id: Optional[str]
    tags: List[str]
    last_seen: Optional[datetime]
    registered_at: datetime
    updated_at: datetime
    user_id: str
    organization_id: Optional[str]
    
    # 统计信息
    total_commands: int = 0
    total_telemetry_points: int = 0
    uptime_percentage: float = 0.0
    

class DeviceAuthResponse(BaseModel):
    """设备认证响应"""
    device_id: str
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # 秒
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    mqtt_broker: Optional[str] = None  # MQTT broker地址
    mqtt_topic: Optional[str] = None  # MQTT主题前缀


class DeviceGroupResponse(BaseModel):
    """设备组响应"""
    group_id: str
    group_name: str
    description: Optional[str]
    parent_group_id: Optional[str]
    device_count: int
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DeviceStatsResponse(BaseModel):
    """设备统计响应"""
    total_devices: int
    active_devices: int
    inactive_devices: int
    error_devices: int
    devices_by_type: Dict[str, int]
    devices_by_status: Dict[str, int]
    devices_by_connectivity: Dict[str, int]
    avg_uptime: float
    total_data_points: int
    last_24h_activity: Dict[str, Any]


class DeviceHealthResponse(BaseModel):
    """设备健康检查响应"""
    device_id: str
    status: DeviceStatus
    health_score: float = Field(..., ge=0, le=100)  # 健康评分 0-100
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    temperature: Optional[float] = None
    battery_level: Optional[float] = None
    signal_strength: Optional[float] = None
    error_count: int = 0
    warning_count: int = 0
    last_error: Optional[str] = None
    last_check: datetime
    diagnostics: Optional[Dict[str, Any]] = {}


class DeviceListResponse(BaseModel):
    """设备列表响应"""
    devices: List[DeviceResponse]
    count: int
    limit: int
    offset: int
    filters: Optional[Dict[str, Any]] = {}