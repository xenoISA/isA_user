"""
Task Service - Data Contract

Pydantic schemas, test data factory, and request builders for task_service.
Zero hardcoded data - all test data generated through factory methods.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from enum import Enum
import secrets
import uuid


# ============================================================================
# Enums
# ============================================================================


class TaskStatusContract(str, Enum):
    """Task status enum contract"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskTypeContract(str, Enum):
    """Task type enum contract"""
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


class TaskPriorityContract(str, Enum):
    """Task priority enum contract"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TriggerTypeContract(str, Enum):
    """Execution trigger type contract"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    EVENT = "event"


class SubscriptionLevelContract(str, Enum):
    """Subscription level contract"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ============================================================================
# Request Contracts (12 schemas)
# ============================================================================


class TaskCreateRequestContract(BaseModel):
    """Contract for task creation requests"""
    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    task_type: TaskTypeContract = Field(..., description="Type of task")
    priority: TaskPriorityContract = Field(
        default=TaskPriorityContract.MEDIUM, description="Task priority"
    )
    config: Dict[str, Any] = Field(default_factory=dict, description="Task config")
    schedule: Optional[Dict[str, Any]] = Field(None, description="Schedule config")
    credits_per_run: float = Field(default=0.0, ge=0, description="Credits per run")
    tags: List[str] = Field(default_factory=list, description="Task tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")
    due_date: Optional[datetime] = Field(None, description="Due date for todos")
    reminder_time: Optional[datetime] = Field(None, description="Reminder time")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v:
            return [tag.strip() for tag in v if tag and tag.strip()]
        return []


class TaskUpdateRequestContract(BaseModel):
    """Contract for task update requests"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriorityContract] = None
    status: Optional[TaskStatusContract] = None
    config: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    credits_per_run: Optional[float] = Field(None, ge=0)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None


class TaskExecutionRequestContract(BaseModel):
    """Contract for task execution requests"""
    trigger_type: TriggerTypeContract = Field(
        default=TriggerTypeContract.MANUAL, description="Execution trigger type"
    )
    trigger_data: Dict[str, Any] = Field(
        default_factory=dict, description="Trigger context data"
    )


class TaskFromTemplateRequestContract(BaseModel):
    """Contract for creating task from template"""
    template_id: str = Field(..., description="Template ID to use")
    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Override config"
    )
    schedule: Optional[Dict[str, Any]] = Field(None, description="Schedule config")
    tags: List[str] = Field(default_factory=list, description="Task tags")

    @field_validator('template_id')
    @classmethod
    def validate_template_id(cls, v):
        if not v or not v.strip():
            raise ValueError("template_id cannot be empty")
        return v.strip()


class TaskListQueryContract(BaseModel):
    """Contract for task list query parameters"""
    status: Optional[TaskStatusContract] = None
    task_type: Optional[TaskTypeContract] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AnalyticsQueryContract(BaseModel):
    """Contract for analytics query parameters"""
    days: int = Field(default=30, ge=1, le=365)


class ScheduleConfigContract(BaseModel):
    """Contract for schedule configuration"""
    type: str = Field(..., description="Schedule type: cron or interval")
    expression: Optional[str] = Field(None, description="Cron expression")
    interval_minutes: Optional[int] = Field(None, ge=1, description="Interval in minutes")
    timezone: str = Field(default="UTC", description="Timezone")


class TaskConfigContract(BaseModel):
    """Contract for task-specific configuration"""
    location: Optional[str] = None
    units: Optional[str] = None
    categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    target_price: Optional[float] = None
    webhook_url: Optional[str] = None
    notification_type: Optional[str] = None


# ============================================================================
# Response Contracts (10 schemas)
# ============================================================================


class TaskResponseContract(BaseModel):
    """Contract for task response"""
    id: int
    task_id: str
    user_id: str
    name: str
    description: Optional[str] = None
    task_type: TaskTypeContract
    status: TaskStatusContract
    priority: TaskPriorityContract
    config: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[Dict[str, Any]] = None
    credits_per_run: float = 0.0
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_credits_consumed: float = 0.0
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class TaskExecutionResponseContract(BaseModel):
    """Contract for task execution response"""
    id: int
    execution_id: str
    task_id: str
    user_id: str
    status: TaskStatusContract
    trigger_type: TriggerTypeContract
    trigger_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    credits_consumed: float = 0.0
    tokens_used: Optional[int] = None
    api_calls_made: int = 0
    duration_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime


class TaskTemplateResponseContract(BaseModel):
    """Contract for task template response"""
    id: int
    template_id: str
    name: str
    description: str
    category: str
    task_type: TaskTypeContract
    default_config: Dict[str, Any]
    required_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    required_subscription_level: SubscriptionLevelContract
    credits_per_run: float
    tags: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TaskAnalyticsResponseContract(BaseModel):
    """Contract for task analytics response"""
    user_id: str
    time_period: str
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    paused_tasks: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_execution_time: float
    total_credits_consumed: float
    total_tokens_used: int
    total_api_calls: int
    task_types_distribution: Dict[str, int]
    busiest_hours: List[int]
    busiest_days: List[str]
    created_at: datetime


class TaskListResponseContract(BaseModel):
    """Contract for task list response"""
    tasks: List[TaskResponseContract]
    count: int
    limit: int
    offset: int
    filters: Dict[str, Any]


class HealthResponseContract(BaseModel):
    """Contract for health check response"""
    status: str
    service: str = "task_service"
    version: str
    timestamp: datetime


class ErrorResponseContract(BaseModel):
    """Contract for error response"""
    detail: str
    error_code: Optional[str] = None
    task_id: Optional[str] = None


class SuccessResponseContract(BaseModel):
    """Contract for simple success response"""
    success: bool = True
    message: Optional[str] = None


# ============================================================================
# TaskTestDataFactory - 40+ methods (25 valid + 15 invalid)
# ============================================================================


class TaskTestDataFactory:
    """Test data factory for task_service - zero hardcoded data"""

    # === ID Generators ===

    @staticmethod
    def make_task_id() -> str:
        """Generate valid task ID"""
        return f"tsk_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_execution_id() -> str:
        """Generate valid execution ID"""
        return f"exe_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_template_id() -> str:
        """Generate valid template ID"""
        return f"tpl_{secrets.token_hex(8)}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"usr_{uuid.uuid4().hex[:16]}"

    # === String Generators ===

    @staticmethod
    def make_task_name() -> str:
        """Generate valid task name"""
        prefixes = ["Daily", "Weekly", "Monitor", "Track", "Alert", "Sync"]
        prefix = secrets.choice(prefixes)
        return f"{prefix} Task {secrets.token_hex(4)}"

    @staticmethod
    def make_description() -> str:
        """Generate valid description"""
        return f"Task description generated at {datetime.now(timezone.utc).isoformat()}"

    @staticmethod
    def make_tag() -> str:
        """Generate valid tag"""
        return f"tag_{secrets.token_hex(4)}"

    @staticmethod
    def make_tags(count: int = 3) -> List[str]:
        """Generate list of valid tags"""
        return [TaskTestDataFactory.make_tag() for _ in range(count)]

    @staticmethod
    def make_location() -> str:
        """Generate valid location string"""
        cities = ["San Francisco", "New York", "London", "Tokyo", "Sydney"]
        return f"{secrets.choice(cities)}, {secrets.token_hex(2).upper()}"

    @staticmethod
    def make_email() -> str:
        """Generate valid email"""
        return f"user_{secrets.token_hex(4)}@example.com"

    # === Timestamp Generators ===

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_future_timestamp(hours: int = 24) -> datetime:
        """Generate future timestamp"""
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    @staticmethod
    def make_past_timestamp(hours: int = 24) -> datetime:
        """Generate past timestamp"""
        return datetime.now(timezone.utc) - timedelta(hours=hours)

    @staticmethod
    def make_due_date() -> datetime:
        """Generate valid due date (in the future)"""
        return TaskTestDataFactory.make_future_timestamp(hours=48)

    @staticmethod
    def make_reminder_time() -> datetime:
        """Generate valid reminder time (in the future)"""
        return TaskTestDataFactory.make_future_timestamp(hours=12)

    # === Numeric Generators ===

    @staticmethod
    def make_credits_per_run() -> float:
        """Generate valid credits per run"""
        return round(secrets.randbelow(500) / 100 + 0.1, 2)

    @staticmethod
    def make_duration_ms() -> int:
        """Generate valid execution duration in milliseconds"""
        return secrets.randbelow(10000) + 100

    @staticmethod
    def make_run_count() -> int:
        """Generate valid run count"""
        return secrets.randbelow(1000)

    @staticmethod
    def make_success_count(run_count: int) -> int:
        """Generate valid success count based on run count"""
        return secrets.randbelow(run_count + 1)

    # === Config Generators ===

    @staticmethod
    def make_task_config(task_type: TaskTypeContract = None) -> Dict[str, Any]:
        """Generate valid task config based on type"""
        if task_type == TaskTypeContract.DAILY_WEATHER:
            return {
                "location": TaskTestDataFactory.make_location(),
                "units": secrets.choice(["imperial", "metric"]),
            }
        elif task_type == TaskTypeContract.DAILY_NEWS:
            return {
                "categories": ["tech", "business"],
                "sources": ["cnn", "bbc"],
            }
        elif task_type == TaskTypeContract.TODO:
            return {
                "priority": "medium",
                "reminder_enabled": True,
            }
        return {"custom_key": f"value_{secrets.token_hex(4)}"}

    @staticmethod
    def make_schedule_config() -> Dict[str, Any]:
        """Generate valid schedule config"""
        schedule_type = secrets.choice(["cron", "interval"])
        if schedule_type == "cron":
            hour = secrets.randbelow(24)
            return {
                "type": "cron",
                "expression": f"0 {hour} * * *",
                "timezone": "UTC",
            }
        return {
            "type": "interval",
            "interval_minutes": secrets.randbelow(1440) + 60,
            "timezone": "UTC",
        }

    @staticmethod
    def make_trigger_data() -> Dict[str, Any]:
        """Generate valid trigger data"""
        return {
            "initiated_by": secrets.choice(["user_action", "system_schedule", "webhook"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def make_execution_result() -> Dict[str, Any]:
        """Generate valid execution result"""
        return {
            "status": "success",
            "data": {"value": secrets.token_hex(8)},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate valid metadata"""
        return {
            "source": f"source_{secrets.token_hex(4)}",
            "version": f"1.{secrets.randbelow(10)}",
        }

    # === Request Generators ===

    @staticmethod
    def make_create_request(
        task_type: TaskTypeContract = None,
        **overrides
    ) -> TaskCreateRequestContract:
        """Generate valid task creation request"""
        task_type = task_type or secrets.choice(list(TaskTypeContract))
        defaults = {
            "name": TaskTestDataFactory.make_task_name(),
            "description": TaskTestDataFactory.make_description(),
            "task_type": task_type,
            "priority": TaskPriorityContract.MEDIUM,
            "config": TaskTestDataFactory.make_task_config(task_type),
            "schedule": None,
            "credits_per_run": TaskTestDataFactory.make_credits_per_run(),
            "tags": TaskTestDataFactory.make_tags(2),
            "metadata": TaskTestDataFactory.make_metadata(),
        }
        defaults.update(overrides)
        return TaskCreateRequestContract(**defaults)

    @staticmethod
    def make_update_request(**overrides) -> TaskUpdateRequestContract:
        """Generate valid task update request"""
        defaults = {
            "name": TaskTestDataFactory.make_task_name(),
            "priority": secrets.choice(list(TaskPriorityContract)),
        }
        defaults.update(overrides)
        return TaskUpdateRequestContract(**defaults)

    @staticmethod
    def make_execution_request(**overrides) -> TaskExecutionRequestContract:
        """Generate valid execution request"""
        defaults = {
            "trigger_type": TriggerTypeContract.MANUAL,
            "trigger_data": TaskTestDataFactory.make_trigger_data(),
        }
        defaults.update(overrides)
        return TaskExecutionRequestContract(**defaults)

    @staticmethod
    def make_from_template_request(**overrides) -> TaskFromTemplateRequestContract:
        """Generate valid from-template request"""
        defaults = {
            "template_id": TaskTestDataFactory.make_template_id(),
            "name": TaskTestDataFactory.make_task_name(),
            "config": {"location": TaskTestDataFactory.make_location()},
            "tags": TaskTestDataFactory.make_tags(2),
        }
        defaults.update(overrides)
        return TaskFromTemplateRequestContract(**defaults)

    # === Response Generators ===

    @staticmethod
    def make_task_response(**overrides) -> TaskResponseContract:
        """Generate valid task response"""
        now = TaskTestDataFactory.make_timestamp()
        run_count = TaskTestDataFactory.make_run_count()
        success_count = TaskTestDataFactory.make_success_count(run_count)
        defaults = {
            "id": secrets.randbelow(10000) + 1,
            "task_id": TaskTestDataFactory.make_task_id(),
            "user_id": TaskTestDataFactory.make_user_id(),
            "name": TaskTestDataFactory.make_task_name(),
            "description": TaskTestDataFactory.make_description(),
            "task_type": secrets.choice(list(TaskTypeContract)),
            "status": TaskStatusContract.PENDING,
            "priority": TaskPriorityContract.MEDIUM,
            "config": TaskTestDataFactory.make_task_config(),
            "schedule": None,
            "credits_per_run": TaskTestDataFactory.make_credits_per_run(),
            "tags": TaskTestDataFactory.make_tags(2),
            "metadata": TaskTestDataFactory.make_metadata(),
            "run_count": run_count,
            "success_count": success_count,
            "failure_count": run_count - success_count,
            "total_credits_consumed": run_count * 0.5,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return TaskResponseContract(**defaults)

    @staticmethod
    def make_execution_response(**overrides) -> TaskExecutionResponseContract:
        """Generate valid execution response"""
        now = TaskTestDataFactory.make_timestamp()
        defaults = {
            "id": secrets.randbelow(10000) + 1,
            "execution_id": TaskTestDataFactory.make_execution_id(),
            "task_id": TaskTestDataFactory.make_task_id(),
            "user_id": TaskTestDataFactory.make_user_id(),
            "status": TaskStatusContract.COMPLETED,
            "trigger_type": TriggerTypeContract.MANUAL,
            "trigger_data": TaskTestDataFactory.make_trigger_data(),
            "result": TaskTestDataFactory.make_execution_result(),
            "credits_consumed": TaskTestDataFactory.make_credits_per_run(),
            "api_calls_made": secrets.randbelow(10) + 1,
            "duration_ms": TaskTestDataFactory.make_duration_ms(),
            "started_at": now,
            "completed_at": now,
            "created_at": now,
        }
        defaults.update(overrides)
        return TaskExecutionResponseContract(**defaults)

    @staticmethod
    def make_template_response(**overrides) -> TaskTemplateResponseContract:
        """Generate valid template response"""
        now = TaskTestDataFactory.make_timestamp()
        defaults = {
            "id": secrets.randbelow(100) + 1,
            "template_id": TaskTestDataFactory.make_template_id(),
            "name": f"Template {secrets.token_hex(4)}",
            "description": TaskTestDataFactory.make_description(),
            "category": secrets.choice(["productivity", "monitoring", "alerts"]),
            "task_type": TaskTypeContract.DAILY_WEATHER,
            "default_config": {"units": "metric"},
            "required_fields": ["location"],
            "optional_fields": ["units", "time"],
            "config_schema": {},
            "required_subscription_level": SubscriptionLevelContract.FREE,
            "credits_per_run": TaskTestDataFactory.make_credits_per_run(),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return TaskTemplateResponseContract(**defaults)

    @staticmethod
    def make_analytics_response(**overrides) -> TaskAnalyticsResponseContract:
        """Generate valid analytics response"""
        total_execs = secrets.randbelow(1000) + 100
        successful = int(total_execs * 0.95)
        defaults = {
            "user_id": TaskTestDataFactory.make_user_id(),
            "time_period": "Last 30 days",
            "total_tasks": secrets.randbelow(50) + 10,
            "active_tasks": secrets.randbelow(30) + 5,
            "completed_tasks": secrets.randbelow(20),
            "failed_tasks": secrets.randbelow(5),
            "paused_tasks": secrets.randbelow(3),
            "total_executions": total_execs,
            "successful_executions": successful,
            "failed_executions": total_execs - successful,
            "success_rate": round(successful / total_execs * 100, 2),
            "average_execution_time": round(secrets.randbelow(1000) / 100 + 0.5, 2),
            "total_credits_consumed": round(total_execs * 0.5, 2),
            "total_tokens_used": secrets.randbelow(50000),
            "total_api_calls": secrets.randbelow(5000),
            "task_types_distribution": {
                "daily_weather": secrets.randbelow(10),
                "todo": secrets.randbelow(20),
                "reminder": secrets.randbelow(15),
            },
            "busiest_hours": [7, 8, 12, 18, 21],
            "busiest_days": ["Monday", "Tuesday", "Wednesday"],
            "created_at": TaskTestDataFactory.make_timestamp(),
        }
        defaults.update(overrides)
        return TaskAnalyticsResponseContract(**defaults)

    # === Invalid Data Generators ===

    @staticmethod
    def make_invalid_task_id() -> str:
        """Generate invalid task ID (wrong format)"""
        return "invalid_task_id"

    @staticmethod
    def make_invalid_user_id() -> str:
        """Generate invalid user ID"""
        return ""

    @staticmethod
    def make_invalid_name_empty() -> str:
        """Generate invalid name (empty)"""
        return ""

    @staticmethod
    def make_invalid_name_whitespace() -> str:
        """Generate invalid name (whitespace only)"""
        return "   "

    @staticmethod
    def make_invalid_name_too_long() -> str:
        """Generate invalid name (too long)"""
        return "x" * 300

    @staticmethod
    def make_invalid_task_type() -> str:
        """Generate invalid task type"""
        return "invalid_type"

    @staticmethod
    def make_invalid_status() -> str:
        """Generate invalid status"""
        return "invalid_status"

    @staticmethod
    def make_invalid_priority() -> str:
        """Generate invalid priority"""
        return "invalid_priority"

    @staticmethod
    def make_invalid_credits_per_run() -> float:
        """Generate invalid credits per run (negative)"""
        return -1.0

    @staticmethod
    def make_invalid_schedule_config() -> Dict[str, Any]:
        """Generate invalid schedule config"""
        return {"type": "invalid", "expression": "not_valid"}

    @staticmethod
    def make_invalid_cron_expression() -> str:
        """Generate invalid cron expression"""
        return "* * * * * * * *"

    @staticmethod
    def make_invalid_template_id() -> str:
        """Generate invalid template ID (empty)"""
        return ""

    @staticmethod
    def make_invalid_limit() -> int:
        """Generate invalid limit (negative)"""
        return -1

    @staticmethod
    def make_invalid_offset() -> int:
        """Generate invalid offset (negative)"""
        return -10

    @staticmethod
    def make_past_due_date() -> datetime:
        """Generate invalid due date (in the past)"""
        return datetime.now(timezone.utc) - timedelta(days=30)


# ============================================================================
# Request Builders (4 builders)
# ============================================================================


class TaskCreateRequestBuilder:
    """Builder for task creation requests"""

    def __init__(self):
        self._name = TaskTestDataFactory.make_task_name()
        self._description = None
        self._task_type = TaskTypeContract.TODO
        self._priority = TaskPriorityContract.MEDIUM
        self._config = {}
        self._schedule = None
        self._credits_per_run = 0.0
        self._tags = []
        self._metadata = {}
        self._due_date = None
        self._reminder_time = None

    def with_name(self, value: str) -> 'TaskCreateRequestBuilder':
        self._name = value
        return self

    def with_description(self, value: str) -> 'TaskCreateRequestBuilder':
        self._description = value
        return self

    def with_task_type(self, value: TaskTypeContract) -> 'TaskCreateRequestBuilder':
        self._task_type = value
        return self

    def with_priority(self, value: TaskPriorityContract) -> 'TaskCreateRequestBuilder':
        self._priority = value
        return self

    def with_config(self, value: Dict[str, Any]) -> 'TaskCreateRequestBuilder':
        self._config = value
        return self

    def with_schedule(self, value: Dict[str, Any]) -> 'TaskCreateRequestBuilder':
        self._schedule = value
        return self

    def with_credits_per_run(self, value: float) -> 'TaskCreateRequestBuilder':
        self._credits_per_run = value
        return self

    def with_tags(self, value: List[str]) -> 'TaskCreateRequestBuilder':
        self._tags = value
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'TaskCreateRequestBuilder':
        self._metadata = value
        return self

    def with_due_date(self, value: datetime) -> 'TaskCreateRequestBuilder':
        self._due_date = value
        return self

    def with_reminder_time(self, value: datetime) -> 'TaskCreateRequestBuilder':
        self._reminder_time = value
        return self

    def build(self) -> TaskCreateRequestContract:
        return TaskCreateRequestContract(
            name=self._name,
            description=self._description,
            task_type=self._task_type,
            priority=self._priority,
            config=self._config,
            schedule=self._schedule,
            credits_per_run=self._credits_per_run,
            tags=self._tags,
            metadata=self._metadata,
            due_date=self._due_date,
            reminder_time=self._reminder_time,
        )


class TaskUpdateRequestBuilder:
    """Builder for task update requests"""

    def __init__(self):
        self._name = None
        self._description = None
        self._priority = None
        self._status = None
        self._config = None
        self._schedule = None
        self._tags = None

    def with_name(self, value: str) -> 'TaskUpdateRequestBuilder':
        self._name = value
        return self

    def with_priority(self, value: TaskPriorityContract) -> 'TaskUpdateRequestBuilder':
        self._priority = value
        return self

    def with_status(self, value: TaskStatusContract) -> 'TaskUpdateRequestBuilder':
        self._status = value
        return self

    def with_config(self, value: Dict[str, Any]) -> 'TaskUpdateRequestBuilder':
        self._config = value
        return self

    def build(self) -> TaskUpdateRequestContract:
        return TaskUpdateRequestContract(
            name=self._name,
            description=self._description,
            priority=self._priority,
            status=self._status,
            config=self._config,
            schedule=self._schedule,
            tags=self._tags,
        )


class TaskExecutionRequestBuilder:
    """Builder for task execution requests"""

    def __init__(self):
        self._trigger_type = TriggerTypeContract.MANUAL
        self._trigger_data = {}

    def with_trigger_type(self, value: TriggerTypeContract) -> 'TaskExecutionRequestBuilder':
        self._trigger_type = value
        return self

    def with_trigger_data(self, value: Dict[str, Any]) -> 'TaskExecutionRequestBuilder':
        self._trigger_data = value
        return self

    def build(self) -> TaskExecutionRequestContract:
        return TaskExecutionRequestContract(
            trigger_type=self._trigger_type,
            trigger_data=self._trigger_data,
        )


class TaskFromTemplateRequestBuilder:
    """Builder for from-template requests"""

    def __init__(self):
        self._template_id = TaskTestDataFactory.make_template_id()
        self._name = TaskTestDataFactory.make_task_name()
        self._config = {}
        self._schedule = None
        self._tags = []

    def with_template_id(self, value: str) -> 'TaskFromTemplateRequestBuilder':
        self._template_id = value
        return self

    def with_name(self, value: str) -> 'TaskFromTemplateRequestBuilder':
        self._name = value
        return self

    def with_config(self, value: Dict[str, Any]) -> 'TaskFromTemplateRequestBuilder':
        self._config = value
        return self

    def with_schedule(self, value: Dict[str, Any]) -> 'TaskFromTemplateRequestBuilder':
        self._schedule = value
        return self

    def with_tags(self, value: List[str]) -> 'TaskFromTemplateRequestBuilder':
        self._tags = value
        return self

    def build(self) -> TaskFromTemplateRequestContract:
        return TaskFromTemplateRequestContract(
            template_id=self._template_id,
            name=self._name,
            config=self._config,
            schedule=self._schedule,
            tags=self._tags,
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "TaskStatusContract",
    "TaskTypeContract",
    "TaskPriorityContract",
    "TriggerTypeContract",
    "SubscriptionLevelContract",
    # Request Contracts
    "TaskCreateRequestContract",
    "TaskUpdateRequestContract",
    "TaskExecutionRequestContract",
    "TaskFromTemplateRequestContract",
    "TaskListQueryContract",
    "AnalyticsQueryContract",
    "ScheduleConfigContract",
    "TaskConfigContract",
    # Response Contracts
    "TaskResponseContract",
    "TaskExecutionResponseContract",
    "TaskTemplateResponseContract",
    "TaskAnalyticsResponseContract",
    "TaskListResponseContract",
    "HealthResponseContract",
    "ErrorResponseContract",
    "SuccessResponseContract",
    # Factory
    "TaskTestDataFactory",
    # Builders
    "TaskCreateRequestBuilder",
    "TaskUpdateRequestBuilder",
    "TaskExecutionRequestBuilder",
    "TaskFromTemplateRequestBuilder",
]
