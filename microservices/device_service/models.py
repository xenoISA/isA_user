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
    SMART_FRAME = "smart_frame"  # Smart photo frame (like a tablet/pad with display)


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


class BulkCommandRequest(BaseModel):
    """批量命令请求"""
    device_ids: List[str]
    command_name: str = Field(..., alias="command", min_length=1, max_length=100)
    parameters: Optional[Dict[str, Any]] = Field(default={})
    timeout: int = Field(default=30, ge=1, le=300)
    priority: int = Field(default=5, ge=1, le=10)
    require_ack: bool = Field(default=True)
    
    model_config = {"populate_by_name": True}


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
    user_id: str  # Owner of the device group (for authorization & multi-tenancy)
    organization_id: Optional[str]  # Organization ownership (for multi-tenancy)
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


# ==================== Smart Frame Models ====================

class FrameDisplayMode(str, Enum):
    """智能相框显示模式"""
    PHOTO_SLIDESHOW = "photo_slideshow"
    VIDEO_PLAYBACK = "video_playback"
    CLOCK_DISPLAY = "clock_display"
    WEATHER_INFO = "weather_info"
    CALENDAR_VIEW = "calendar_view"
    OFF = "off"


class FrameOrientation(str, Enum):
    """相框方向"""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    AUTO = "auto"


class FrameConfig(BaseModel):
    """智能相框配置"""
    device_id: str = Field(..., description="设备ID")
    
    # Display settings
    brightness: int = Field(80, ge=0, le=100, description="亮度 (0-100)")
    contrast: int = Field(100, ge=0, le=200, description="对比度 (0-200)")
    auto_brightness: bool = Field(True, description="自动亮度")
    orientation: FrameOrientation = Field(FrameOrientation.AUTO, description="显示方向")
    
    # Slideshow settings
    slideshow_interval: int = Field(30, ge=5, le=3600, description="幻灯片间隔(秒)")
    slideshow_transition: str = Field("fade", description="过渡效果")
    shuffle_photos: bool = Field(True, description="随机播放")
    show_metadata: bool = Field(False, description="显示照片信息")
    
    # Power management
    sleep_schedule: Dict[str, str] = Field(
        default_factory=lambda: {"start": "23:00", "end": "07:00"},
        description="休眠时间表"
    )
    auto_sleep: bool = Field(True, description="自动休眠")
    motion_detection: bool = Field(True, description="动作检测唤醒")
    
    # Sync settings
    auto_sync_albums: List[str] = Field(default_factory=list, description="自动同步的相册ID列表")
    sync_frequency: str = Field("hourly", description="同步频率")
    wifi_only_sync: bool = Field(True, description="仅Wi-Fi同步")
    
    # Display mode
    display_mode: FrameDisplayMode = Field(FrameDisplayMode.PHOTO_SLIDESHOW, description="显示模式")
    
    # Location and environment
    location: Optional[Dict[str, float]] = Field(None, description="位置信息")
    timezone: str = Field("UTC", description="时区")


class DisplayCommand(BaseModel):
    """显示控制命令"""
    command_type: str = Field(..., description="命令类型")
    command_id: str = Field(..., description="命令ID")
    device_id: str = Field(..., description="目标设备ID")
    
    # Command parameters
    parameters: Dict[str, Any] = Field(default_factory=dict, description="命令参数")
    
    # Execution settings
    priority: str = Field("normal", description="优先级: low, normal, high, urgent")
    timeout_seconds: int = Field(30, description="超时时间(秒)")
    retry_count: int = Field(3, description="重试次数")
    
    # Scheduling
    execute_at: Optional[datetime] = Field(None, description="定时执行时间")
    expires_at: Optional[datetime] = Field(None, description="命令过期时间")


class FrameStatus(BaseModel):
    """智能相框状态"""
    device_id: str
    
    # Basic status
    is_online: bool
    current_mode: FrameDisplayMode
    brightness_level: int
    
    # Display info
    current_photo: Optional[str] = Field(None, description="当前显示的照片ID")
    slideshow_active: bool = False
    total_photos: int = 0
    
    # Hardware status
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    storage_used: Optional[float] = None
    storage_total: Optional[float] = None
    temperature: Optional[float] = None
    
    # Network and sync
    wifi_signal: Optional[int] = None
    last_sync_time: Optional[datetime] = None
    sync_status: str = "idle"  # idle, syncing, error
    pending_sync_items: int = 0
    
    # Sensors
    ambient_light: Optional[float] = None
    motion_detected: bool = False
    
    # Timestamps
    last_seen: datetime
    uptime_seconds: int = 0


# ==================== Smart Frame Request/Response Models ====================

class FrameRegistrationRequest(BaseModel):
    """智能相框注册请求"""
    device_name: str = Field(..., description="设备名称")
    manufacturer: str = Field("Generic", description="制造商")
    model: str = Field("SmartFrame", description="型号")
    serial_number: str = Field(..., description="序列号")
    mac_address: str = Field(..., description="MAC地址")
    
    # Frame specific info
    screen_size: str = Field(..., description="屏幕尺寸")
    resolution: str = Field(..., description="分辨率")
    supported_formats: List[str] = Field(default_factory=lambda: ["jpg", "png", "mp4"], description="支持的文件格式")
    
    # Network info
    connectivity_type: ConnectivityType = Field(ConnectivityType.WIFI, description="连接类型")
    
    # Location and organization
    location: Optional[Dict[str, float]] = Field(None, description="位置信息")
    organization_id: Optional[str] = Field(None, description="组织ID")
    
    # Initial config
    initial_config: Optional[FrameConfig] = Field(None, description="初始配置")


class UpdateFrameConfigRequest(BaseModel):
    """更新相框配置请求"""
    brightness: Optional[int] = Field(None, ge=0, le=100)
    auto_brightness: Optional[bool] = None
    slideshow_interval: Optional[int] = Field(None, ge=5, le=3600)
    display_mode: Optional[FrameDisplayMode] = None
    auto_sync_albums: Optional[List[str]] = None
    sleep_schedule: Optional[Dict[str, str]] = None
    orientation: Optional[FrameOrientation] = None


class FrameCommandRequest(BaseModel):
    """相框命令请求"""
    command_type: str = Field(..., description="命令类型: display_photo, start_slideshow, stop_slideshow, sync_album, reboot")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="命令参数")
    priority: str = Field("normal", description="优先级")
    timeout_seconds: int = Field(30, description="超时时间")


class FrameResponse(BaseModel):
    """智能相框响应"""
    device_id: str
    device_name: str
    status: DeviceStatus
    frame_status: FrameStatus
    config: FrameConfig
    
    # Family sharing info (from organization_service)
    is_family_shared: bool = False
    sharing_info: Optional[Dict[str, Any]] = None
    
    # Registration info
    registered_at: datetime
    last_seen: datetime


class FrameListResponse(BaseModel):
    """智能相框列表响应"""
    frames: List[FrameResponse]
    count: int
    limit: int
    offset: int
# ============================================================================
# Device Pairing Models
# ============================================================================

class DevicePairingRequest(BaseModel):
    """Request to pair a device with a user"""
    pairing_token: str = Field(..., description="Pairing token from QR code")
    user_id: str = Field(..., description="User ID attempting to pair")


class DevicePairingResponse(BaseModel):
    """Response for device pairing"""
    success: bool
    device: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None
