"""
Location Service - Data Models

位置服务数据模型，包含位置追踪、地理围栏、常用地点、路线等
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum


class LocationMethod(str, Enum):
    """位置获取方法"""
    GPS = "gps"
    WIFI = "wifi"
    CELLULAR = "cellular"
    BLUETOOTH = "bluetooth"
    MANUAL = "manual"
    HYBRID = "hybrid"


class GeofenceShapeType(str, Enum):
    """地理围栏形状类型"""
    CIRCLE = "circle"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"


class GeofenceTriggerType(str, Enum):
    """地理围栏触发类型"""
    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"


class PlaceCategory(str, Enum):
    """常用地点分类"""
    HOME = "home"
    WORK = "work"
    SCHOOL = "school"
    FAVORITE = "favorite"
    CUSTOM = "custom"


class LocationEventType(str, Enum):
    """位置事件类型"""
    LOCATION_UPDATE = "location_update"
    GEOFENCE_ENTER = "geofence_enter"
    GEOFENCE_EXIT = "geofence_exit"
    GEOFENCE_DWELL = "geofence_dwell"
    SIGNIFICANT_MOVEMENT = "significant_movement"
    LOW_BATTERY_AT_LOCATION = "low_battery_at_location"
    DEVICE_STOPPED = "device_stopped"
    DEVICE_MOVING = "device_moving"


class RouteStatus(str, Enum):
    """路线状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ==================== Request Models ====================

class LocationReportRequest(BaseModel):
    """位置报告请求"""
    device_id: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    accuracy: float = Field(..., gt=0)  # 精度（米）
    heading: Optional[float] = Field(None, ge=0, lt=360)  # 方向（度）
    speed: Optional[float] = Field(None, ge=0)  # 速度（m/s）

    # 地址信息（可选，可以通过反向地理编码获得）
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)

    # 元数据
    location_method: LocationMethod = LocationMethod.GPS
    battery_level: Optional[float] = Field(None, ge=0, le=100)
    timestamp: Optional[datetime] = None  # 如果不提供，使用服务器时间
    source: str = Field("device", max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class LocationBatchRequest(BaseModel):
    """批量位置报告请求"""
    locations: List[LocationReportRequest] = Field(..., min_length=1, max_length=1000)
    compression: Optional[str] = None  # gzip, lz4
    batch_id: Optional[str] = None


class GeofenceCreateRequest(BaseModel):
    """地理围栏创建请求"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

    # 几何形状
    shape_type: GeofenceShapeType
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    radius: Optional[float] = Field(None, gt=0)  # 圆形半径（米）
    polygon_coordinates: Optional[List[Tuple[float, float]]] = None  # 多边形坐标

    # 配置
    trigger_on_enter: bool = True
    trigger_on_exit: bool = True
    trigger_on_dwell: bool = False
    dwell_time_seconds: Optional[int] = Field(None, ge=60)

    # 目标设备
    target_devices: List[str] = Field(default_factory=list)
    target_groups: List[str] = Field(default_factory=list)

    # 时间限制
    active_days: Optional[List[str]] = None  # ["monday", "tuesday", ...]
    active_hours: Optional[Dict[str, str]] = None  # {"start": "09:00", "end": "18:00"}

    # 通知配置
    notification_channels: List[str] = Field(default_factory=list)
    notification_template: Optional[str] = None

    tags: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('polygon_coordinates')
    def validate_polygon(cls, v, info):
        if info.data.get('shape_type') == GeofenceShapeType.POLYGON:
            if not v or len(v) < 3:
                raise ValueError('Polygon must have at least 3 coordinates')
        return v


class GeofenceUpdateRequest(BaseModel):
    """地理围栏更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

    trigger_on_enter: Optional[bool] = None
    trigger_on_exit: Optional[bool] = None
    trigger_on_dwell: Optional[bool] = None
    dwell_time_seconds: Optional[int] = Field(None, ge=60)

    target_devices: Optional[List[str]] = None
    target_groups: Optional[List[str]] = None

    active_days: Optional[List[str]] = None
    active_hours: Optional[Dict[str, str]] = None

    notification_channels: Optional[List[str]] = None
    notification_template: Optional[str] = None

    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PlaceCreateRequest(BaseModel):
    """常用地点创建请求"""
    name: str = Field(..., min_length=1, max_length=200)
    category: PlaceCategory

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)
    radius: float = Field(100.0, gt=0, le=1000)  # 识别半径（米）

    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    tags: List[str] = Field(default_factory=list)


class PlaceUpdateRequest(BaseModel):
    """常用地点更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[PlaceCategory] = None

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)
    radius: Optional[float] = Field(None, gt=0, le=1000)

    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    tags: Optional[List[str]] = None


class RouteStartRequest(BaseModel):
    """开始路线记录请求"""
    device_id: str = Field(..., min_length=1, max_length=100)
    name: Optional[str] = Field(None, max_length=200)
    start_location: LocationReportRequest


class NearbySearchRequest(BaseModel):
    """附近设备搜索请求"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(..., gt=0, le=50000)  # 最大50km
    device_types: Optional[List[str]] = None
    time_window_minutes: int = Field(30, ge=1, le=1440)  # 默认30分钟内
    limit: int = Field(50, ge=1, le=500)


class RadiusSearchRequest(BaseModel):
    """圆形区域搜索请求"""
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(..., gt=0, le=100000)  # 最大100km
    start_time: datetime
    end_time: datetime
    device_ids: Optional[List[str]] = None
    limit: int = Field(100, ge=1, le=1000)


class PolygonSearchRequest(BaseModel):
    """多边形区域搜索请求"""
    polygon_coordinates: List[Tuple[float, float]] = Field(..., min_length=3)
    start_time: datetime
    end_time: datetime
    device_ids: Optional[List[str]] = None
    limit: int = Field(100, ge=1, le=1000)


# ==================== Response Models ====================

class LocationResponse(BaseModel):
    """位置响应"""
    location_id: str
    device_id: str
    user_id: str

    latitude: float
    longitude: float
    altitude: Optional[float]
    accuracy: float
    heading: Optional[float]
    speed: Optional[float]

    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]

    location_method: LocationMethod
    battery_level: Optional[float]
    source: str
    metadata: Dict[str, Any]

    timestamp: datetime
    created_at: datetime


class GeofenceResponse(BaseModel):
    """地理围栏响应"""
    geofence_id: str
    name: str
    description: Optional[str]
    user_id: str
    organization_id: Optional[str]

    shape_type: GeofenceShapeType
    center_lat: float
    center_lon: float
    radius: Optional[float]
    polygon_coordinates: Optional[List[Tuple[float, float]]]

    active: bool
    trigger_on_enter: bool
    trigger_on_exit: bool
    trigger_on_dwell: bool
    dwell_time_seconds: Optional[int]

    target_devices: List[str]
    target_groups: List[str]

    active_days: Optional[List[str]]
    active_hours: Optional[Dict[str, str]]

    notification_channels: List[str]
    notification_template: Optional[str]

    total_triggers: int
    last_triggered: Optional[datetime]

    created_at: datetime
    updated_at: datetime
    tags: List[str]
    metadata: Dict[str, Any]


class LocationEventResponse(BaseModel):
    """位置事件响应"""
    event_id: str
    event_type: LocationEventType
    device_id: str
    user_id: str

    location: LocationResponse

    geofence_id: Optional[str]
    geofence_name: Optional[str]

    distance_from_last: Optional[float]
    time_from_last: Optional[float]
    estimated_speed: Optional[float]

    trigger_reason: Optional[str]
    metadata: Dict[str, Any]

    timestamp: datetime
    processed: bool
    created_at: datetime


class PlaceResponse(BaseModel):
    """常用地点响应"""
    place_id: str
    user_id: str
    name: str
    category: PlaceCategory

    latitude: float
    longitude: float
    address: Optional[str]
    radius: float

    icon: Optional[str]
    color: Optional[str]

    visit_count: int
    total_time_spent: int
    last_visit: Optional[datetime]

    created_at: datetime
    updated_at: datetime
    tags: List[str]


class RouteResponse(BaseModel):
    """路线响应"""
    route_id: str
    device_id: str
    user_id: str
    name: Optional[str]
    status: RouteStatus

    start_location: LocationResponse
    end_location: Optional[LocationResponse]
    waypoint_count: int

    total_distance: Optional[float]
    total_duration: Optional[float]
    avg_speed: Optional[float]
    max_speed: Optional[float]

    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime


class DeviceLocationResponse(BaseModel):
    """设备位置响应（用于附近搜索）"""
    device_id: str
    device_name: str
    device_type: str
    user_id: str

    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: float
    distance: float  # 距离搜索点的距离（米）

    status: str  # 设备状态


class LocationListResponse(BaseModel):
    """位置列表响应"""
    locations: List[LocationResponse]
    count: int
    limit: int
    offset: int


class GeofenceListResponse(BaseModel):
    """地理围栏列表响应"""
    geofences: List[GeofenceResponse]
    count: int
    limit: int
    offset: int


class PlaceListResponse(BaseModel):
    """常用地点列表响应"""
    places: List[PlaceResponse]
    count: int


class RouteListResponse(BaseModel):
    """路线列表响应"""
    routes: List[RouteResponse]
    count: int
    limit: int
    offset: int


class LocationEventListResponse(BaseModel):
    """位置事件列表响应"""
    events: List[LocationEventResponse]
    count: int
    limit: int
    offset: int


class LocationStatsResponse(BaseModel):
    """位置统计响应"""
    total_locations: int
    active_devices: int
    total_geofences: int
    active_geofences: int
    total_places: int
    total_routes: int

    # 最近24小时统计
    last_24h_locations: int
    last_24h_events: int
    last_24h_geofence_triggers: int

    # 设备分布
    devices_by_type: Dict[str, int]

    # 最活跃的地理围栏
    top_geofences: List[Dict[str, Any]]


class GeofenceStatsResponse(BaseModel):
    """地理围栏统计响应"""
    geofence_id: str
    geofence_name: str

    total_triggers: int
    enter_count: int
    exit_count: int
    dwell_count: int

    unique_devices: int
    avg_dwell_time: Optional[float]

    last_triggered: Optional[datetime]

    # 最近触发的设备
    recent_devices: List[Dict[str, Any]]


class DistanceResponse(BaseModel):
    """距离计算响应"""
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_meters: float
    distance_km: float


class HeatmapDataResponse(BaseModel):
    """热力图数据响应"""
    points: List[Dict[str, Any]]  # [{"lat": float, "lon": float, "weight": float}]
    bounds: Dict[str, float]  # {"min_lat", "max_lat", "min_lon", "max_lon"}
    total_points: int


# ==================== Service Status ====================

class LocationServiceStatus(BaseModel):
    """位置服务状态"""
    service: str
    status: str
    version: str
    database_connected: bool
    cache_connected: bool
    geofencing_enabled: bool
    route_tracking_enabled: bool
    timestamp: datetime


# ==================== Operation Result ====================

class LocationOperationResult(BaseModel):
    """位置操作结果"""
    success: bool
    location_id: Optional[str] = None
    geofence_id: Optional[str] = None
    place_id: Optional[str] = None
    route_id: Optional[str] = None
    operation: str
    message: str
    data: Optional[Dict[str, Any]] = None
    affected_count: int = 0
