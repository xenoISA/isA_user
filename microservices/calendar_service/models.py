"""
Calendar Service Models

日历事件管理数据模型
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class RecurrenceType(str, Enum):
    """事件重复类型"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class EventCategory(str, Enum):
    """事件分类"""
    WORK = "work"
    PERSONAL = "personal"
    MEETING = "meeting"
    REMINDER = "reminder"
    HOLIDAY = "holiday"
    BIRTHDAY = "birthday"
    OTHER = "other"


class SyncProvider(str, Enum):
    """外部日历提供商"""
    GOOGLE = "google_calendar"
    APPLE = "apple_calendar"
    OUTLOOK = "outlook"
    LOCAL = "local"


class CalendarEvent(BaseModel):
    """日历事件模型"""
    id: Optional[int] = None
    event_id: str = Field(..., description="事件唯一标识")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = None
    
    # 事件基本信息
    title: str = Field(..., description="事件标题")
    description: Optional[str] = None
    location: Optional[str] = None
    
    # 时间信息
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    all_day: bool = Field(False, description="是否全天事件")
    timezone: str = Field("UTC", description="时区")
    
    # 分类和样式
    category: EventCategory = EventCategory.OTHER
    color: Optional[str] = Field(None, description="事件颜色 (#RRGGBB)")
    
    # 重复设置
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    recurrence_end_date: Optional[datetime] = None
    recurrence_rule: Optional[str] = None  # iCalendar RRULE format
    
    # 提醒设置
    reminders: List[int] = Field(default_factory=list, description="提醒时间（分钟）")
    
    # 同步信息
    sync_provider: SyncProvider = SyncProvider.LOCAL
    external_event_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    
    # 共享设置
    is_shared: bool = False
    shared_with: List[str] = Field(default_factory=list)
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = None
    
    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Request Models

class EventCreateRequest(BaseModel):
    """创建事件请求"""
    user_id: str
    organization_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    timezone: str = "UTC"
    category: EventCategory = EventCategory.OTHER
    color: Optional[str] = None
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    recurrence_end_date: Optional[datetime] = None
    recurrence_rule: Optional[str] = None
    reminders: List[int] = Field(default_factory=list)
    is_shared: bool = False
    shared_with: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class EventUpdateRequest(BaseModel):
    """更新事件请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    category: Optional[EventCategory] = None
    color: Optional[str] = None
    recurrence_type: Optional[RecurrenceType] = None
    recurrence_end_date: Optional[datetime] = None
    reminders: Optional[List[int]] = None
    is_shared: Optional[bool] = None
    shared_with: Optional[List[str]] = None


class EventQueryRequest(BaseModel):
    """查询事件请求"""
    user_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category: Optional[EventCategory] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# Response Models

class EventResponse(BaseModel):
    """事件响应"""
    event_id: str
    user_id: str
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: datetime
    all_day: bool
    category: EventCategory
    color: Optional[str]
    recurrence_type: RecurrenceType
    recurrence_end_date: Optional[datetime] = None
    recurrence_rule: Optional[str] = None
    reminders: List[int]
    is_shared: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """事件列表响应"""
    events: List[EventResponse]
    total: int
    page: int
    page_size: int


class SyncStatusResponse(BaseModel):
    """同步状态响应"""
    provider: str  # Can be SyncProvider value or other string
    last_synced: Optional[datetime]
    synced_events: int
    status: str
    message: Optional[str] = None


__all__ = [
    "CalendarEvent",
    "RecurrenceType",
    "EventCategory",
    "SyncProvider",
    "EventCreateRequest",
    "EventUpdateRequest",
    "EventQueryRequest",
    "EventResponse",
    "EventListResponse",
    "SyncStatusResponse"
]

