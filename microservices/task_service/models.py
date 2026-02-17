"""
Task Service Data Models

任务服务数据模型定义
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# 枚举定义
class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(str, Enum):
    """任务类型"""
    DAILY_WEATHER = "daily_weather"
    DAILY_NEWS = "daily_news"
    NEWS_MONITOR = "news_monitor"
    WEATHER_ALERT = "weather_alert"
    PRICE_TRACKER = "price_tracker"
    DATA_BACKUP = "data_backup"
    TODO = "todo"
    REMINDER = "reminder"
    CALENDAR_EVENT = "calendar_event"
    CUSTOM = "custom"


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# 请求模型
class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: TaskType
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    config: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[Dict[str, Any]] = None
    credits_per_run: Optional[float] = Field(default=0.0)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    config: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    credits_per_run: Optional[float] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None


class TaskExecutionRequest(BaseModel):
    """执行任务请求"""
    trigger_type: str = Field(default="manual")
    trigger_data: Dict[str, Any] = Field(default_factory=dict)


# 响应模型
class TaskResponse(BaseModel):
    """任务响应"""
    id: int
    task_id: str
    user_id: str
    name: str
    description: Optional[str]
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    schedule: Optional[Dict[str, Any]] = None
    credits_per_run: float = 0.0
    tags: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # 执行相关
    next_run_time: Optional[datetime]
    last_run_time: Optional[datetime]
    last_success_time: Optional[datetime]
    last_error: Optional[str]
    last_result: Optional[Dict[str, Any]]

    # 统计
    run_count: int
    success_count: int
    failure_count: int
    total_credits_consumed: float
    
    # 时间相关
    due_date: Optional[datetime]
    reminder_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class TaskExecutionResponse(BaseModel):
    """任务执行响应"""
    id: int
    execution_id: str
    task_id: str
    user_id: str
    status: TaskStatus
    trigger_type: str
    trigger_data: Optional[Dict[str, Any]]
    
    # 执行结果
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]

    # 资源消耗
    credits_consumed: float
    tokens_used: Optional[int]
    api_calls_made: int
    duration_ms: Optional[int]
    
    # 时间
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime


class TaskTemplateResponse(BaseModel):
    """任务模板响应"""
    id: int
    template_id: str
    name: str
    description: str
    category: str
    task_type: TaskType
    default_config: Dict[str, Any]
    required_fields: Optional[List[str]] = []
    optional_fields: Optional[List[str]] = []
    config_schema: Optional[Dict[str, Any]] = {}
    required_subscription_level: str
    credits_per_run: float
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = {}
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TaskAnalyticsResponse(BaseModel):
    """任务分析响应"""
    user_id: str
    time_period: str
    
    # 任务统计
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    paused_tasks: int
    
    # 执行统计
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_execution_time: float  # 秒

    # 资源消耗
    total_credits_consumed: float
    total_tokens_used: int
    total_api_calls: int
    
    # 任务类型分布
    task_types_distribution: Dict[str, int]
    
    # 时间分析
    busiest_hours: List[int]
    busiest_days: List[str]
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    count: int
    limit: int
    offset: int
    filters: Dict[str, Any]