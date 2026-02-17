"""
Telemetry Service - Data Models

遥测服务数据模型，包含设备数据采集、监控、警报等
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


class DataType(str, Enum):
    """数据类型"""
    NUMERIC = "numeric"
    STRING = "string"
    BOOLEAN = "boolean"
    JSON = "json"
    BINARY = "binary"
    GEOLOCATION = "geolocation"
    TIMESTAMP = "timestamp"


class MetricType(str, Enum):
    """指标类型"""
    GAUGE = "gauge"  # 瞬时值
    COUNTER = "counter"  # 计数器
    HISTOGRAM = "histogram"  # 直方图
    SUMMARY = "summary"  # 摘要


class AlertLevel(str, Enum):
    """警报级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    """警报状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AggregationType(str, Enum):
    """聚合类型"""
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    MEDIAN = "median"
    P95 = "p95"
    P99 = "p99"


class TimeRange(str, Enum):
    """时间范围"""
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"


# ==================
# Request Models
# ==================

class TelemetryDataPoint(BaseModel):
    """遥测数据点"""
    timestamp: datetime
    metric_name: str = Field(..., min_length=1, max_length=100)
    value: Union[int, float, str, bool, Dict[str, Any]]
    unit: Optional[str] = Field(None, max_length=20)
    tags: Optional[Dict[str, str]] = {}
    metadata: Optional[Dict[str, Any]] = {}


class TelemetryBatchRequest(BaseModel):
    """批量遥测数据请求"""
    data_points: List[TelemetryDataPoint] = Field(..., min_items=1, max_items=1000)
    compression: Optional[str] = None  # gzip, lz4, etc.
    batch_id: Optional[str] = None  # 批次ID，用于去重


class MetricDefinitionRequest(BaseModel):
    """指标定义请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    data_type: DataType
    metric_type: MetricType = MetricType.GAUGE
    unit: Optional[str] = Field(None, max_length=20)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    retention_days: int = Field(90, ge=1, le=3650)  # 数据保留天数
    aggregation_interval: int = Field(60, ge=1, le=86400)  # 聚合间隔（秒）
    tags: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}


class AlertRuleRequest(BaseModel):
    """警报规则请求"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    metric_name: str = Field(..., min_length=1, max_length=100)
    condition: str = Field(..., min_length=1)  # e.g., "> 80", "< 10", "== 'error'"
    threshold_value: Union[int, float, str]
    evaluation_window: int = Field(300, ge=60, le=3600)  # 评估窗口（秒）
    trigger_count: int = Field(1, ge=1, le=100)  # 连续触发次数
    level: AlertLevel = AlertLevel.WARNING
    
    # 目标设备
    device_ids: Optional[List[str]] = []
    device_groups: Optional[List[str]] = []
    device_filters: Optional[Dict[str, Any]] = {}
    
    # 通知配置
    notification_channels: Optional[List[str]] = []
    cooldown_minutes: int = Field(15, ge=1, le=1440)  # 冷却时间
    auto_resolve: bool = True
    auto_resolve_timeout: int = Field(3600, ge=300, le=86400)  # 自动解除时间
    
    enabled: bool = True
    tags: Optional[List[str]] = []


class QueryRequest(BaseModel):
    """查询请求"""
    devices: Optional[List[str]] = []  # Changed from device_ids to match test
    metrics: List[str] = Field(..., min_items=1)  # Changed from metric_names to match test
    start_time: datetime
    end_time: datetime
    aggregation: Optional[AggregationType] = None
    interval: Optional[int] = Field(None, ge=60, le=86400)  # 聚合间隔
    filters: Optional[Dict[str, str]] = {}  # Changed from tags to match test
    limit: int = Field(1000, ge=1, le=10000)
    offset: int = Field(0, ge=0)


class RealTimeSubscriptionRequest(BaseModel):
    """实时订阅请求"""
    device_ids: Optional[List[str]] = []
    metric_names: Optional[List[str]] = []
    tags: Optional[Dict[str, str]] = {}
    filter_condition: Optional[str] = None  # 过滤条件
    max_frequency: int = Field(1000, ge=100, le=10000)  # 最大频率（毫秒）


# ==================
# Response Models
# ==================

class MetricDefinitionResponse(BaseModel):
    """指标定义响应"""
    metric_id: str
    name: str
    description: Optional[str]
    data_type: DataType
    metric_type: MetricType
    unit: Optional[str]
    min_value: Optional[float]
    max_value: Optional[float]
    retention_days: int
    aggregation_interval: int
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: str


class TelemetryDataResponse(BaseModel):
    """遥测数据响应"""
    device_id: str
    metric_name: str
    data_points: List[TelemetryDataPoint]
    count: int
    aggregation: Optional[AggregationType]
    interval: Optional[int]
    start_time: datetime
    end_time: datetime


class AlertRuleResponse(BaseModel):
    """警报规则响应"""
    rule_id: str
    name: str
    description: Optional[str]
    metric_name: str
    condition: str
    threshold_value: Union[int, float, str]
    evaluation_window: int
    trigger_count: int
    level: AlertLevel
    device_ids: List[str]
    device_groups: List[str]
    device_filters: Dict[str, Any]
    notification_channels: List[str]
    cooldown_minutes: int
    auto_resolve: bool
    auto_resolve_timeout: int
    enabled: bool
    tags: List[str]
    
    # 统计信息
    total_triggers: int = 0
    last_triggered: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    created_by: str


class AlertResponse(BaseModel):
    """警报响应"""
    alert_id: str
    rule_id: str
    rule_name: str
    device_id: str
    metric_name: str
    level: AlertLevel
    status: AlertStatus
    message: str
    current_value: Union[int, float, str]
    threshold_value: Union[int, float, str]
    
    # 时间信息
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    auto_resolve_at: Optional[datetime] = None
    
    # 操作信息
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None
    
    # 上下文信息
    affected_devices_count: int = 1
    tags: List[str]
    metadata: Dict[str, Any]


class DeviceTelemetryStatsResponse(BaseModel):
    """设备遥测统计响应"""
    device_id: str
    total_metrics: int
    active_metrics: int
    data_points_count: int
    last_update: Optional[datetime]
    storage_size: int  # bytes
    avg_frequency: float  # points per minute
    
    # 最近24小时统计
    last_24h_points: int
    last_24h_alerts: int
    
    # 指标分布
    metrics_by_type: Dict[str, int]
    top_metrics: List[Dict[str, Any]]  # 最活跃的指标


class TelemetryStatsResponse(BaseModel):
    """遥测统计响应"""
    total_devices: int
    active_devices: int
    total_metrics: int
    total_data_points: int
    storage_size: int  # bytes
    
    # 数据摄取统计
    points_per_second: float
    avg_latency: float  # milliseconds
    error_rate: float
    
    # 最近24小时统计
    last_24h_points: int
    last_24h_devices: int
    last_24h_alerts: int
    
    # 分布统计
    devices_by_type: Dict[str, int]
    metrics_by_type: Dict[str, int]
    data_by_hour: List[Dict[str, Any]]  # 每小时数据量


class RealTimeDataResponse(BaseModel):
    """实时数据响应"""
    subscription_id: str
    device_id: str
    data_points: List[TelemetryDataPoint]
    timestamp: datetime
    sequence_number: int


class AggregatedDataResponse(BaseModel):
    """聚合数据响应"""
    device_id: Optional[str]  # None表示多设备聚合
    metric_name: str
    aggregation_type: AggregationType
    interval: int  # 秒
    data_points: List[Dict[str, Any]]  # {"timestamp": datetime, "value": float}
    start_time: datetime
    end_time: datetime
    count: int


class AlertListResponse(BaseModel):
    """警报列表响应"""
    alerts: List[AlertResponse]
    count: int
    active_count: int
    critical_count: int
    filters: Dict[str, Any]
    limit: int
    offset: int