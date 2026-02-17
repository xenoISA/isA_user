"""
Unit Golden Tests: Task Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.task_service.models import (
    TaskStatus,
    TaskType,
    TaskPriority,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskExecutionRequest,
    TaskResponse,
    TaskExecutionResponse,
    TaskTemplateResponse,
    TaskAnalyticsResponse,
    TaskListResponse,
)


class TestEnumTypes:
    """Test enum type definitions"""

    def test_task_status_values(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.SCHEDULED == "scheduled"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.PAUSED == "paused"

    def test_task_priority_values(self):
        """Test TaskPriority enum values"""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.MEDIUM == "medium"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.URGENT == "urgent"

    def test_task_type_values(self):
        """Test TaskType enum values"""
        assert TaskType.DAILY_WEATHER == "daily_weather"
        assert TaskType.DAILY_NEWS == "daily_news"
        assert TaskType.NEWS_MONITOR == "news_monitor"
        assert TaskType.WEATHER_ALERT == "weather_alert"
        assert TaskType.PRICE_TRACKER == "price_tracker"
        assert TaskType.DATA_BACKUP == "data_backup"
        assert TaskType.TODO == "todo"
        assert TaskType.REMINDER == "reminder"
        assert TaskType.CALENDAR_EVENT == "calendar_event"
        assert TaskType.CUSTOM == "custom"

    def test_task_status_comparison(self):
        """Test task status comparison"""
        assert TaskStatus.PENDING != TaskStatus.COMPLETED
        assert TaskStatus.RUNNING.value == "running"

    def test_task_priority_comparison(self):
        """Test task priority comparison"""
        assert TaskPriority.LOW != TaskPriority.URGENT
        assert TaskPriority.MEDIUM.value == "medium"


class TestTaskCreateRequest:
    """Test TaskCreateRequest model validation"""

    def test_task_create_request_minimal(self):
        """Test creating task with minimal required fields"""
        request = TaskCreateRequest(
            name="Test Task",
            task_type=TaskType.TODO,
        )

        assert request.name == "Test Task"
        assert request.task_type == TaskType.TODO
        assert request.priority == TaskPriority.MEDIUM
        assert request.config == {}
        assert request.schedule is None
        assert request.credits_per_run == 0.0
        assert request.tags == []
        assert request.metadata == {}

    def test_task_create_request_with_all_fields(self):
        """Test creating task with all fields"""
        now = datetime.now(timezone.utc)
        due = now + timedelta(days=7)
        reminder = now + timedelta(days=6)

        request = TaskCreateRequest(
            name="Complete Project",
            description="Finish the quarterly report",
            task_type=TaskType.TODO,
            priority=TaskPriority.HIGH,
            config={"notify_on_complete": True},
            schedule={"cron": "0 9 * * MON"},
            credits_per_run=5.0,
            tags=["work", "quarterly"],
            metadata={"project_id": "proj_123"},
            due_date=due,
            reminder_time=reminder,
        )

        assert request.name == "Complete Project"
        assert request.description == "Finish the quarterly report"
        assert request.task_type == TaskType.TODO
        assert request.priority == TaskPriority.HIGH
        assert request.config == {"notify_on_complete": True}
        assert request.schedule == {"cron": "0 9 * * MON"}
        assert request.credits_per_run == 5.0
        assert request.tags == ["work", "quarterly"]
        assert request.metadata == {"project_id": "proj_123"}
        assert request.due_date == due
        assert request.reminder_time == reminder

    def test_task_create_request_with_weather_alert(self):
        """Test creating weather alert task"""
        request = TaskCreateRequest(
            name="Daily Weather Alert",
            description="Send weather notifications",
            task_type=TaskType.WEATHER_ALERT,
            priority=TaskPriority.MEDIUM,
            config={"location": "San Francisco", "alert_types": ["rain", "storm"]},
            schedule={"cron": "0 7 * * *"},
        )

        assert request.task_type == TaskType.WEATHER_ALERT
        assert request.config["location"] == "San Francisco"
        assert len(request.config["alert_types"]) == 2

    def test_task_create_request_name_validation(self):
        """Test name field validation"""
        # Test minimum length validation
        with pytest.raises(ValidationError) as exc_info:
            TaskCreateRequest(
                name="",
                task_type=TaskType.TODO,
            )
        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "name" for err in errors)

    def test_task_create_request_missing_required_fields(self):
        """Test missing required fields raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreateRequest(name="Test Task")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "task_type" in missing_fields

    def test_task_create_request_priority_default(self):
        """Test default priority is MEDIUM"""
        request = TaskCreateRequest(
            name="Test Task",
            task_type=TaskType.REMINDER,
        )

        assert request.priority == TaskPriority.MEDIUM


class TestTaskUpdateRequest:
    """Test TaskUpdateRequest model validation"""

    def test_task_update_request_partial(self):
        """Test partial update request"""
        request = TaskUpdateRequest(
            name="Updated Name",
            description="Updated description",
        )

        assert request.name == "Updated Name"
        assert request.description == "Updated description"
        assert request.priority is None
        assert request.status is None

    def test_task_update_request_status_change(self):
        """Test updating task status"""
        request = TaskUpdateRequest(
            status=TaskStatus.COMPLETED,
        )

        assert request.status == TaskStatus.COMPLETED

    def test_task_update_request_priority_change(self):
        """Test updating task priority"""
        request = TaskUpdateRequest(
            priority=TaskPriority.URGENT,
        )

        assert request.priority == TaskPriority.URGENT

    def test_task_update_request_schedule_update(self):
        """Test updating task schedule"""
        request = TaskUpdateRequest(
            schedule={"cron": "0 10 * * *"},
            next_run_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        assert request.schedule == {"cron": "0 10 * * *"}
        assert request.next_run_time is not None

    def test_task_update_request_all_fields(self):
        """Test update request with all fields"""
        now = datetime.now(timezone.utc)
        due = now + timedelta(days=5)
        reminder = now + timedelta(days=4)
        next_run = now + timedelta(hours=2)

        request = TaskUpdateRequest(
            name="Updated Task",
            description="New description",
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            config={"updated": True},
            schedule={"interval": "daily"},
            credits_per_run=10.0,
            tags=["updated", "important"],
            metadata={"version": 2},
            due_date=due,
            reminder_time=reminder,
            next_run_time=next_run,
        )

        assert request.name == "Updated Task"
        assert request.priority == TaskPriority.HIGH
        assert request.status == TaskStatus.RUNNING
        assert request.credits_per_run == 10.0
        assert len(request.tags) == 2

    def test_task_update_request_name_validation(self):
        """Test name field validation on update"""
        # Empty string should fail min_length validation
        with pytest.raises(ValidationError) as exc_info:
            TaskUpdateRequest(name="")

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "name" for err in errors)


class TestTaskExecutionRequest:
    """Test TaskExecutionRequest model validation"""

    def test_task_execution_request_defaults(self):
        """Test default execution request"""
        request = TaskExecutionRequest()

        assert request.trigger_type == "manual"
        assert request.trigger_data == {}

    def test_task_execution_request_scheduled(self):
        """Test scheduled execution request"""
        request = TaskExecutionRequest(
            trigger_type="scheduled",
            trigger_data={"scheduled_time": "2024-01-01T00:00:00Z"},
        )

        assert request.trigger_type == "scheduled"
        assert request.trigger_data["scheduled_time"] == "2024-01-01T00:00:00Z"

    def test_task_execution_request_event_triggered(self):
        """Test event-triggered execution request"""
        request = TaskExecutionRequest(
            trigger_type="event",
            trigger_data={"event_type": "user_action", "user_id": "user_123"},
        )

        assert request.trigger_type == "event"
        assert request.trigger_data["event_type"] == "user_action"


class TestTaskResponse:
    """Test TaskResponse model"""

    def test_task_response_minimal(self):
        """Test creating task response with minimal fields"""
        now = datetime.now(timezone.utc)

        response = TaskResponse(
            id=1,
            task_id="task_123",
            user_id="user_456",
            name="Test Task",
            description=None,
            task_type=TaskType.TODO,
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            next_run_time=None,
            last_run_time=None,
            last_success_time=None,
            last_error=None,
            last_result=None,
            run_count=0,
            success_count=0,
            failure_count=0,
            total_credits_consumed=0.0,
            due_date=None,
            reminder_time=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        assert response.id == 1
        assert response.task_id == "task_123"
        assert response.user_id == "user_456"
        assert response.name == "Test Task"
        assert response.task_type == TaskType.TODO
        assert response.status == TaskStatus.PENDING
        assert response.run_count == 0
        assert response.total_credits_consumed == 0.0

    def test_task_response_with_all_fields(self):
        """Test creating task response with all fields"""
        now = datetime.now(timezone.utc)
        next_run = now + timedelta(hours=1)
        last_run = now - timedelta(hours=1)
        due = now + timedelta(days=7)

        response = TaskResponse(
            id=42,
            task_id="task_complete_123",
            user_id="user_789",
            name="Completed Task",
            description="A fully executed task",
            task_type=TaskType.DATA_BACKUP,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
            config={"backup_location": "/data/backup"},
            schedule={"cron": "0 2 * * *"},
            credits_per_run=2.5,
            tags=["backup", "nightly"],
            metadata={"backup_id": "bkp_001"},
            next_run_time=next_run,
            last_run_time=last_run,
            last_success_time=last_run,
            last_error=None,
            last_result={"status": "success", "bytes_backed_up": 1024000},
            run_count=100,
            success_count=98,
            failure_count=2,
            total_credits_consumed=250.0,
            due_date=due,
            reminder_time=None,
            created_at=now - timedelta(days=100),
            updated_at=now,
            deleted_at=None,
        )

        assert response.id == 42
        assert response.name == "Completed Task"
        assert response.status == TaskStatus.COMPLETED
        assert response.run_count == 100
        assert response.success_count == 98
        assert response.failure_count == 2
        assert response.total_credits_consumed == 250.0
        assert response.last_result["status"] == "success"

    def test_task_response_with_error(self):
        """Test task response with error information"""
        now = datetime.now(timezone.utc)

        response = TaskResponse(
            id=5,
            task_id="task_failed_123",
            user_id="user_123",
            name="Failed Task",
            description="Task that encountered an error",
            task_type=TaskType.PRICE_TRACKER,
            status=TaskStatus.FAILED,
            priority=TaskPriority.MEDIUM,
            next_run_time=None,
            last_run_time=now - timedelta(minutes=30),
            last_success_time=None,
            last_error="Connection timeout",
            last_result=None,
            run_count=3,
            success_count=0,
            failure_count=3,
            total_credits_consumed=0.0,
            due_date=None,
            reminder_time=None,
            created_at=now - timedelta(hours=2),
            updated_at=now,
            deleted_at=None,
        )

        assert response.status == TaskStatus.FAILED
        assert response.last_error == "Connection timeout"
        assert response.failure_count == 3
        assert response.success_count == 0


class TestTaskExecutionResponse:
    """Test TaskExecutionResponse model"""

    def test_task_execution_response_success(self):
        """Test successful task execution response"""
        now = datetime.now(timezone.utc)
        started = now - timedelta(minutes=5)
        completed = now

        response = TaskExecutionResponse(
            id=1,
            execution_id="exec_123",
            task_id="task_456",
            user_id="user_789",
            status=TaskStatus.COMPLETED,
            trigger_type="manual",
            trigger_data={"user_action": "execute_now"},
            result={"status": "success", "items_processed": 42},
            error_message=None,
            error_details=None,
            credits_consumed=2.5,
            tokens_used=1500,
            api_calls_made=3,
            duration_ms=5000,
            started_at=started,
            completed_at=completed,
            created_at=started,
        )

        assert response.execution_id == "exec_123"
        assert response.status == TaskStatus.COMPLETED
        assert response.result["items_processed"] == 42
        assert response.credits_consumed == 2.5
        assert response.tokens_used == 1500
        assert response.api_calls_made == 3
        assert response.duration_ms == 5000

    def test_task_execution_response_failed(self):
        """Test failed task execution response"""
        now = datetime.now(timezone.utc)
        started = now - timedelta(minutes=2)

        response = TaskExecutionResponse(
            id=2,
            execution_id="exec_failed_456",
            task_id="task_789",
            user_id="user_123",
            status=TaskStatus.FAILED,
            trigger_type="scheduled",
            trigger_data=None,
            result=None,
            error_message="API rate limit exceeded",
            error_details={"code": "RATE_LIMIT", "retry_after": 60},
            credits_consumed=0.0,
            tokens_used=None,
            api_calls_made=1,
            duration_ms=500,
            started_at=started,
            completed_at=None,
            created_at=started,
        )

        assert response.status == TaskStatus.FAILED
        assert response.error_message == "API rate limit exceeded"
        assert response.error_details["code"] == "RATE_LIMIT"
        assert response.credits_consumed == 0.0
        assert response.completed_at is None

    def test_task_execution_response_running(self):
        """Test running task execution response"""
        now = datetime.now(timezone.utc)
        started = now - timedelta(seconds=30)

        response = TaskExecutionResponse(
            id=3,
            execution_id="exec_running_789",
            task_id="task_abc",
            user_id="user_xyz",
            status=TaskStatus.RUNNING,
            trigger_type="event",
            trigger_data={"event_id": "evt_123"},
            result=None,
            error_message=None,
            error_details=None,
            credits_consumed=0.0,
            tokens_used=None,
            api_calls_made=0,
            duration_ms=None,
            started_at=started,
            completed_at=None,
            created_at=started,
        )

        assert response.status == TaskStatus.RUNNING
        assert response.completed_at is None
        assert response.duration_ms is None


class TestTaskTemplateResponse:
    """Test TaskTemplateResponse model"""

    def test_task_template_response(self):
        """Test task template response"""
        now = datetime.now(timezone.utc)

        response = TaskTemplateResponse(
            id=1,
            template_id="tpl_daily_weather",
            name="Daily Weather Report",
            description="Get daily weather forecast for your location",
            category="weather",
            task_type=TaskType.DAILY_WEATHER,
            default_config={"location": "auto", "units": "metric"},
            required_fields=["location"],
            optional_fields=["units", "language"],
            config_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "units": {"type": "string", "enum": ["metric", "imperial"]},
                },
            },
            required_subscription_level="basic",
            credits_per_run=1.0,
            tags=["weather", "daily"],
            metadata={"version": "1.0"},
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        assert response.template_id == "tpl_daily_weather"
        assert response.name == "Daily Weather Report"
        assert response.task_type == TaskType.DAILY_WEATHER
        assert response.credits_per_run == 1.0
        assert response.is_active is True
        assert response.required_subscription_level == "basic"

    def test_task_template_response_inactive(self):
        """Test inactive task template"""
        now = datetime.now(timezone.utc)

        response = TaskTemplateResponse(
            id=2,
            template_id="tpl_deprecated",
            name="Deprecated Template",
            description="This template is no longer active",
            category="deprecated",
            task_type=TaskType.CUSTOM,
            default_config={},
            required_subscription_level="premium",
            credits_per_run=0.0,
            is_active=False,
            created_at=now - timedelta(days=365),
            updated_at=now,
        )

        assert response.is_active is False
        assert response.template_id == "tpl_deprecated"


class TestTaskAnalyticsResponse:
    """Test TaskAnalyticsResponse model"""

    def test_task_analytics_response(self):
        """Test task analytics response"""
        now = datetime.now(timezone.utc)

        response = TaskAnalyticsResponse(
            user_id="user_123",
            time_period="last_30_days",
            total_tasks=50,
            active_tasks=20,
            completed_tasks=25,
            failed_tasks=3,
            paused_tasks=2,
            total_executions=500,
            successful_executions=475,
            failed_executions=25,
            success_rate=0.95,
            average_execution_time=2.5,
            total_credits_consumed=250.0,
            total_tokens_used=150000,
            total_api_calls=1500,
            task_types_distribution={
                "todo": 20,
                "reminder": 15,
                "daily_weather": 10,
                "data_backup": 5,
            },
            busiest_hours=[9, 10, 14, 18],
            busiest_days=["Monday", "Wednesday", "Friday"],
            created_at=now,
        )

        assert response.user_id == "user_123"
        assert response.time_period == "last_30_days"
        assert response.total_tasks == 50
        assert response.active_tasks == 20
        assert response.completed_tasks == 25
        assert response.success_rate == 0.95
        assert response.total_credits_consumed == 250.0
        assert len(response.task_types_distribution) == 4
        assert len(response.busiest_hours) == 4
        assert len(response.busiest_days) == 3

    def test_task_analytics_response_low_activity(self):
        """Test task analytics with low activity"""
        now = datetime.now(timezone.utc)

        response = TaskAnalyticsResponse(
            user_id="user_new_456",
            time_period="last_7_days",
            total_tasks=2,
            active_tasks=2,
            completed_tasks=0,
            failed_tasks=0,
            paused_tasks=0,
            total_executions=5,
            successful_executions=5,
            failed_executions=0,
            success_rate=1.0,
            average_execution_time=1.2,
            total_credits_consumed=5.0,
            total_tokens_used=3000,
            total_api_calls=10,
            task_types_distribution={"todo": 1, "reminder": 1},
            busiest_hours=[9],
            busiest_days=["Monday"],
            created_at=now,
        )

        assert response.total_tasks == 2
        assert response.success_rate == 1.0
        assert response.failed_executions == 0


class TestTaskListResponse:
    """Test TaskListResponse model"""

    def test_task_list_response(self):
        """Test task list response"""
        now = datetime.now(timezone.utc)

        tasks = [
            TaskResponse(
                id=i,
                task_id=f"task_{i}",
                user_id="user_123",
                name=f"Task {i}",
                description=None,
                task_type=TaskType.TODO,
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                next_run_time=None,
                last_run_time=None,
                last_success_time=None,
                last_error=None,
                last_result=None,
                run_count=0,
                success_count=0,
                failure_count=0,
                total_credits_consumed=0.0,
                due_date=None,
                reminder_time=None,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            for i in range(10)
        ]

        response = TaskListResponse(
            tasks=tasks,
            count=10,
            limit=20,
            offset=0,
            filters={"status": "pending"},
        )

        assert len(response.tasks) == 10
        assert response.count == 10
        assert response.limit == 20
        assert response.offset == 0
        assert response.filters["status"] == "pending"

    def test_task_list_response_empty(self):
        """Test empty task list response"""
        response = TaskListResponse(
            tasks=[],
            count=0,
            limit=20,
            offset=0,
            filters={},
        )

        assert len(response.tasks) == 0
        assert response.count == 0

    def test_task_list_response_with_pagination(self):
        """Test task list response with pagination"""
        now = datetime.now(timezone.utc)

        tasks = [
            TaskResponse(
                id=i,
                task_id=f"task_{i}",
                user_id="user_123",
                name=f"Task {i}",
                description=None,
                task_type=TaskType.REMINDER,
                status=TaskStatus.SCHEDULED,
                priority=TaskPriority.HIGH,
                next_run_time=now + timedelta(hours=i),
                last_run_time=None,
                last_success_time=None,
                last_error=None,
                last_result=None,
                run_count=0,
                success_count=0,
                failure_count=0,
                total_credits_consumed=0.0,
                due_date=None,
                reminder_time=None,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            for i in range(20, 30)
        ]

        response = TaskListResponse(
            tasks=tasks,
            count=10,
            limit=10,
            offset=20,
            filters={"priority": "high", "status": "scheduled"},
        )

        assert len(response.tasks) == 10
        assert response.offset == 20
        assert response.filters["priority"] == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
