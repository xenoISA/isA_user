"""
Event Service Models

定义事件相关的数据模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid


# ==================== 事件类型枚举 ====================

class EventSource(str, Enum):
    """事件来源"""
    FRONTEND = "frontend"           # 前端用户行为
    BACKEND = "backend"             # 后端业务逻辑
    SYSTEM = "system"               # 系统内部
    IOT_DEVICE = "iot_device"       # IoT设备
    EXTERNAL_API = "external_api"   # 外部API
    SCHEDULED = "scheduled"         # 定时任务


class EventCategory(str, Enum):
    """事件分类"""
    # 用户行为
    USER_ACTION = "user_action"
    PAGE_VIEW = "page_view"
    FORM_SUBMIT = "form_submit"
    CLICK = "click"

    # 业务事件
    USER_LIFECYCLE = "user_lifecycle"
    PAYMENT = "payment"
    ORDER = "order"
    TASK = "task"

    # 系统事件
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"

    # IoT事件
    DEVICE = "device"  # 兼容旧数据
    DEVICE_STATUS = "device_status"
    TELEMETRY = "telemetry"
    COMMAND = "command"
    ALERT = "alert"


class EventStatus(str, Enum):
    """事件处理状态"""
    PENDING = "pending"         # 待处理
    PROCESSING = "processing"   # 处理中
    PROCESSED = "processed"     # 已处理
    FAILED = "failed"          # 处理失败
    ARCHIVED = "archived"      # 已归档


class ProcessingStatus(str, Enum):
    """处理器状态"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


# ==================== 事件模型 ====================

class Event(BaseModel):
    """统一事件模型"""
    model_config = ConfigDict(from_attributes=True)
    
    # 基础字段
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="事件唯一ID")
    event_type: str = Field(..., description="事件类型")
    event_source: EventSource = Field(..., description="事件来源")
    event_category: EventCategory = Field(..., description="事件分类")
    
    # 关联信息
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    organization_id: Optional[str] = Field(None, description="组织ID")
    device_id: Optional[str] = Field(None, description="设备ID")
    correlation_id: Optional[str] = Field(None, description="关联ID（用于追踪）")
    
    # 事件数据
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    # 上下文信息
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    properties: Optional[Dict[str, Any]] = Field(None, description="属性")
    
    # 处理信息
    status: EventStatus = Field(EventStatus.PENDING, description="事件状态")
    processed_at: Optional[datetime] = Field(None, description="处理时间")
    processors: List[str] = Field(default_factory=list, description="已处理的处理器")
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(0, description="重试次数")
    
    # 时间信息
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间戳")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    
    # 版本控制
    version: str = Field("1.0.0", description="事件版本")
    schema_version: str = Field("1.0.0", description="模式版本")


class EventStream(BaseModel):
    """事件流模型"""
    model_config = ConfigDict(from_attributes=True)
    
    stream_id: str = Field(..., description="流ID")
    stream_type: str = Field(..., description="流类型")
    entity_id: str = Field(..., description="实体ID")
    entity_type: str = Field(..., description="实体类型")
    
    events: List[Event] = Field(default_factory=list, description="事件列表")
    version: int = Field(0, description="流版本")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== RudderStack 事件模型 ====================

class RudderStackEvent(BaseModel):
    """RudderStack 事件模型"""
    model_config = ConfigDict(from_attributes=True)
    
    anonymousId: Optional[str] = Field(None, description="匿名ID")
    userId: Optional[str] = Field(None, description="用户ID")
    event: str = Field(..., description="事件名称")
    type: str = Field(..., description="事件类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="事件属性")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文")
    timestamp: str = Field(..., description="时间戳")
    sentAt: Optional[str] = Field(None, description="发送时间")
    receivedAt: Optional[str] = Field(None, description="接收时间")
    originalTimestamp: Optional[str] = Field(None, description="原始时间戳")


# ==================== API 请求/响应模型 ====================

class EventCreateRequest(BaseModel):
    """创建事件请求"""
    event_type: str = Field(..., description="事件类型")
    event_source: Optional[EventSource] = Field(EventSource.BACKEND, description="事件来源")
    event_category: Optional[EventCategory] = Field(EventCategory.USER_ACTION, description="事件分类")
    user_id: Optional[str] = Field(None, description="用户ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文")


class EventQueryRequest(BaseModel):
    """查询事件请求"""
    user_id: Optional[str] = Field(None, description="用户ID")
    event_type: Optional[str] = Field(None, description="事件类型")
    event_source: Optional[EventSource] = Field(None, description="事件来源")
    event_category: Optional[EventCategory] = Field(None, description="事件分类")
    status: Optional[EventStatus] = Field(None, description="事件状态")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    limit: int = Field(100, ge=1, le=1000, description="返回数量")
    offset: int = Field(0, ge=0, description="偏移量")


class EventResponse(BaseModel):
    """事件响应"""
    event_id: str
    event_type: str
    event_source: EventSource
    event_category: EventCategory
    user_id: Optional[str]
    data: Dict[str, Any]
    status: EventStatus
    timestamp: datetime
    created_at: datetime


class EventListResponse(BaseModel):
    """事件列表响应"""
    events: List[EventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class EventStatistics(BaseModel):
    """事件统计"""
    total_events: int = Field(..., description="事件总数")
    pending_events: int = Field(..., description="待处理事件数")
    processed_events: int = Field(..., description="已处理事件数")
    failed_events: int = Field(..., description="失败事件数")
    
    events_by_source: Dict[str, int] = Field(default_factory=dict, description="按来源统计")
    events_by_category: Dict[str, int] = Field(default_factory=dict, description="按分类统计")
    events_by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    
    events_today: int = Field(0, description="今日事件数")
    events_this_week: int = Field(0, description="本周事件数")
    events_this_month: int = Field(0, description="本月事件数")
    
    average_processing_time: float = Field(0.0, description="平均处理时间(秒)")
    processing_rate: float = Field(0.0, description="处理率(%)")
    error_rate: float = Field(0.0, description="错误率(%)")
    
    top_users: List[Dict[str, Any]] = Field(default_factory=list, description="活跃用户")
    top_event_types: List[Dict[str, Any]] = Field(default_factory=list, description="热门事件类型")
    
    calculated_at: datetime = Field(default_factory=datetime.utcnow, description="统计时间")


class EventProcessingResult(BaseModel):
    """事件处理结果"""
    event_id: str
    processor_name: str
    status: ProcessingStatus
    message: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = None


class EventReplayRequest(BaseModel):
    """事件重放请求"""
    stream_id: Optional[str] = Field(None, description="流ID")
    event_ids: Optional[List[str]] = Field(None, description="事件ID列表")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    target_service: Optional[str] = Field(None, description="目标服务")
    dry_run: bool = Field(False, description="模拟运行")


class EventProjection(BaseModel):
    """事件投影"""
    projection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    projection_name: str = Field(..., description="投影名称")
    entity_id: str = Field(..., description="实体ID")
    entity_type: str = Field(..., description="实体类型")
    
    state: Dict[str, Any] = Field(default_factory=dict, description="当前状态")
    version: int = Field(0, description="版本号")
    last_event_id: Optional[str] = Field(None, description="最后处理的事件ID")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== 处理器配置 ====================

class EventProcessor(BaseModel):
    """事件处理器配置"""
    processor_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    processor_name: str = Field(..., description="处理器名称")
    processor_type: str = Field(..., description="处理器类型")
    
    enabled: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")
    
    filters: Dict[str, Any] = Field(default_factory=dict, description="过滤条件")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")
    
    error_count: int = Field(0, description="错误次数")
    last_error: Optional[str] = Field(None, description="最后错误")
    last_processed_at: Optional[datetime] = Field(None, description="最后处理时间")


class EventSubscription(BaseModel):
    """事件订阅"""
    subscription_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subscriber_name: str = Field(default="default_subscriber", description="订阅者名称")
    subscriber_type: str = Field(default="service", description="订阅者类型")
    
    event_types: List[str] = Field(..., description="订阅的事件类型")
    event_sources: Optional[List[EventSource]] = Field(None, description="订阅的事件源")
    event_categories: Optional[List[EventCategory]] = Field(None, description="订阅的事件分类")
    
    callback_url: Optional[str] = Field(None, description="回调URL")
    webhook_secret: Optional[str] = Field(None, description="Webhook密钥")
    
    enabled: bool = Field(True, description="是否启用")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="重试策略")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)