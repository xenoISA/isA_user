"""
Task Service - Mock Dependencies

Mock implementations for component testing.
Returns TaskResponse model objects as expected by the service.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import uuid

# Import the actual models used by the service
from microservices.task_service.models import (
    TaskResponse,
    TaskExecutionResponse,
    TaskTemplateResponse,
    TaskAnalyticsResponse,
    TaskStatus,
    TaskType,
    TaskPriority,
)


class MockTaskRepository:
    """Mock task repository for component testing

    Implements TaskRepositoryProtocol interface.
    Returns TaskResponse model objects.
    """

    def __init__(self):
        self._tasks: Dict[str, TaskResponse] = {}
        self._executions: Dict[str, TaskExecutionResponse] = {}
        self._templates: Dict[str, TaskTemplateResponse] = {}
        self._user_tasks_index: Dict[str, List[str]] = {}  # user_id -> [task_id]
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []
        self._id_counter: int = 1
        self._execution_counter: int = 1

    def set_task(
        self,
        task_id: str,
        user_id: str,
        name: str,
        task_type: TaskType = TaskType.TODO,
        status: TaskStatus = TaskStatus.PENDING,
        priority: TaskPriority = TaskPriority.MEDIUM,
        config: Optional[Dict] = None,
        schedule: Optional[Dict] = None,
        credits_per_run: float = 0.0,
        tags: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
    ):
        """Add a task to the mock repository"""
        now = datetime.now(timezone.utc)
        task = TaskResponse(
            id=self._id_counter,
            task_id=task_id,
            user_id=user_id,
            name=name,
            description=None,
            task_type=task_type,
            status=status,
            priority=priority,
            config=config or {},
            schedule=schedule,
            credits_per_run=credits_per_run,
            tags=tags or [],
            metadata={},
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
            created_at=created_at or now,
            updated_at=now,
            deleted_at=None,
        )
        self._tasks[task_id] = task
        self._id_counter += 1

        # Update user index
        if user_id not in self._user_tasks_index:
            self._user_tasks_index[user_id] = []
        self._user_tasks_index[user_id].append(task_id)

    def set_template(
        self,
        template_id: str,
        name: str,
        task_type: TaskType = TaskType.TODO,
        category: str = "general",
        required_subscription_level: str = "free",
        credits_per_run: float = 0.0,
    ):
        """Add a task template to the mock repository"""
        now = datetime.now(timezone.utc)
        template = TaskTemplateResponse(
            id=self._id_counter,
            template_id=template_id,
            name=name,
            description=f"Template for {name}",
            category=category,
            task_type=task_type,
            default_config={},
            required_fields=[],
            optional_fields=[],
            config_schema={},
            required_subscription_level=required_subscription_level,
            credits_per_run=credits_per_run,
            tags=[],
            metadata={},
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._templates[template_id] = template
        self._id_counter += 1

    def set_error(self, error: Exception):
        """Set an error to be raised on operations"""
        self._error = error

    def clear_error(self):
        """Clear any set error"""
        self._error = None

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, but got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert that a method was called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value, f"Expected {key}={value}, got {call['kwargs'][key]}"
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    def get_call_count(self, method: str) -> int:
        """Get the number of times a method was called"""
        return sum(1 for c in self._call_log if c["method"] == method)

    async def create_task(
        self, user_id: str, task_data: Dict[str, Any]
    ) -> Optional[TaskResponse]:
        """Create a new task"""
        self._log_call("create_task", user_id=user_id, task_data=task_data)
        if self._error:
            raise self._error

        task_id = f"tsk_{uuid.uuid4().hex[:24]}"
        now = datetime.now(timezone.utc)

        # Parse task_type if string
        task_type = task_data.get("task_type")
        if isinstance(task_type, str):
            task_type = TaskType(task_type)
        elif hasattr(task_type, "value"):
            task_type = TaskType(task_type.value)

        # Parse priority if string
        priority = task_data.get("priority", TaskPriority.MEDIUM)
        if isinstance(priority, str):
            priority = TaskPriority(priority)
        elif hasattr(priority, "value"):
            priority = TaskPriority(priority.value)

        # Parse status if string
        status = task_data.get("status", TaskStatus.PENDING)
        if isinstance(status, str):
            status = TaskStatus(status)
        elif hasattr(status, "value"):
            status = TaskStatus(status.value)

        task = TaskResponse(
            id=self._id_counter,
            task_id=task_id,
            user_id=user_id,
            name=task_data.get("name", ""),
            description=task_data.get("description"),
            task_type=task_type,
            status=status,
            priority=priority,
            config=task_data.get("config", {}),
            schedule=task_data.get("schedule"),
            credits_per_run=task_data.get("credits_per_run", 0.0),
            tags=task_data.get("tags", []),
            metadata=task_data.get("metadata", {}),
            next_run_time=task_data.get("next_run_time"),
            last_run_time=None,
            last_success_time=None,
            last_error=None,
            last_result=None,
            run_count=0,
            success_count=0,
            failure_count=0,
            total_credits_consumed=0.0,
            due_date=task_data.get("due_date"),
            reminder_time=task_data.get("reminder_time"),
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        self._tasks[task_id] = task
        self._id_counter += 1

        # Update user index
        if user_id not in self._user_tasks_index:
            self._user_tasks_index[user_id] = []
        self._user_tasks_index[user_id].append(task_id)

        return task

    async def get_task_by_id(
        self, task_id: str, user_id: str = None
    ) -> Optional[TaskResponse]:
        """Get task by ID"""
        self._log_call("get_task_by_id", task_id=task_id, user_id=user_id)
        if self._error:
            raise self._error

        task = self._tasks.get(task_id)
        if task and task.deleted_at is None:
            if user_id is None or task.user_id == user_id:
                return task
        return None

    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TaskResponse]:
        """Get all tasks for a user with optional filtering"""
        self._log_call(
            "get_user_tasks",
            user_id=user_id,
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset,
        )
        if self._error:
            raise self._error

        task_ids = self._user_tasks_index.get(user_id, [])
        results = []

        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task and task.deleted_at is None:
                # Filter by status
                if status and task.status.value != status:
                    continue
                # Filter by task type
                if task_type and task.task_type.value != task_type:
                    continue
                results.append(task)

        # Apply pagination
        return results[offset:offset + limit]

    async def update_task(
        self, task_id: str, updates: Dict[str, Any], user_id: str = None
    ) -> bool:
        """Update task data"""
        self._log_call("update_task", task_id=task_id, updates=updates, user_id=user_id)
        if self._error:
            raise self._error

        task = self._tasks.get(task_id)
        if not task or task.deleted_at is not None:
            return False

        if user_id and task.user_id != user_id:
            return False

        # Create updated task
        now = datetime.now(timezone.utc)
        updated_data = task.dict()
        updated_data.update(updates)
        updated_data["updated_at"] = now

        # Handle enum conversions
        if "status" in updated_data and isinstance(updated_data["status"], str):
            updated_data["status"] = TaskStatus(updated_data["status"])
        if "priority" in updated_data and isinstance(updated_data["priority"], str):
            updated_data["priority"] = TaskPriority(updated_data["priority"])

        self._tasks[task_id] = TaskResponse(**updated_data)
        return True

    async def delete_task(self, task_id: str, user_id: str = None) -> bool:
        """Soft delete a task"""
        self._log_call("delete_task", task_id=task_id, user_id=user_id)
        if self._error:
            raise self._error

        task = self._tasks.get(task_id)
        if not task or task.deleted_at is not None:
            return False

        if user_id and task.user_id != user_id:
            return False

        # Soft delete
        now = datetime.now(timezone.utc)
        updated_data = task.dict()
        updated_data["deleted_at"] = now
        updated_data["status"] = TaskStatus.CANCELLED
        updated_data["updated_at"] = now
        self._tasks[task_id] = TaskResponse(**updated_data)
        return True

    async def get_pending_tasks(self, limit: int = 100) -> List[TaskResponse]:
        """Get pending tasks for scheduler"""
        self._log_call("get_pending_tasks", limit=limit)
        if self._error:
            raise self._error

        results = []
        now = datetime.now(timezone.utc)
        for task in self._tasks.values():
            if task.deleted_at is None and task.status == TaskStatus.SCHEDULED:
                if task.next_run_time and task.next_run_time <= now:
                    results.append(task)
                    if len(results) >= limit:
                        break
        return results

    async def update_task_execution_info(
        self, task_id: str, success: bool, credits_consumed: float = 0
    ) -> bool:
        """Update task execution statistics"""
        self._log_call(
            "update_task_execution_info",
            task_id=task_id,
            success=success,
            credits_consumed=credits_consumed,
        )
        if self._error:
            raise self._error

        task = self._tasks.get(task_id)
        if not task:
            return False

        now = datetime.now(timezone.utc)
        updated_data = task.dict()
        updated_data["run_count"] = task.run_count + 1
        updated_data["last_run_time"] = now
        updated_data["total_credits_consumed"] = task.total_credits_consumed + credits_consumed
        updated_data["updated_at"] = now

        if success:
            updated_data["success_count"] = task.success_count + 1
            updated_data["last_success_time"] = now
        else:
            updated_data["failure_count"] = task.failure_count + 1

        self._tasks[task_id] = TaskResponse(**updated_data)
        return True

    async def create_execution_record(
        self, task_id: str, user_id: str, execution_data: Dict[str, Any]
    ) -> Optional[TaskExecutionResponse]:
        """Create execution record"""
        self._log_call(
            "create_execution_record",
            task_id=task_id,
            user_id=user_id,
            execution_data=execution_data,
        )
        if self._error:
            raise self._error

        execution_id = f"exe_{uuid.uuid4().hex[:24]}"
        now = datetime.now(timezone.utc)

        execution = TaskExecutionResponse(
            id=self._execution_counter,
            execution_id=execution_id,
            task_id=task_id,
            user_id=user_id,
            status=TaskStatus.RUNNING,
            trigger_type=execution_data.get("trigger_type", "manual"),
            trigger_data=execution_data.get("trigger_data", {}),
            result=None,
            error_message=None,
            error_details=None,
            credits_consumed=0.0,
            tokens_used=None,
            api_calls_made=0,
            duration_ms=None,
            started_at=now,
            completed_at=None,
            created_at=now,
        )

        self._executions[execution_id] = execution
        self._execution_counter += 1
        return execution

    async def update_execution_record(
        self, execution_id: str, updates: Dict[str, Any]
    ) -> bool:
        """Update execution record"""
        self._log_call(
            "update_execution_record",
            execution_id=execution_id,
            updates=updates,
        )
        if self._error:
            raise self._error

        execution = self._executions.get(execution_id)
        if not execution:
            return False

        now = datetime.now(timezone.utc)
        updated_data = execution.dict()
        updated_data.update(updates)
        if updates.get("success"):
            updated_data["status"] = TaskStatus.COMPLETED
            updated_data["completed_at"] = now
        elif updates.get("error"):
            updated_data["status"] = TaskStatus.FAILED
            updated_data["error_message"] = updates.get("error")
            updated_data["completed_at"] = now

        self._executions[execution_id] = TaskExecutionResponse(**updated_data)
        return True

    async def get_task_executions(
        self, task_id: str, limit: int = 50, offset: int = 0
    ) -> List[TaskExecutionResponse]:
        """Get task execution history"""
        self._log_call(
            "get_task_executions",
            task_id=task_id,
            limit=limit,
            offset=offset,
        )
        if self._error:
            raise self._error

        results = [e for e in self._executions.values() if e.task_id == task_id]
        return results[offset:offset + limit]

    async def get_task_templates(
        self,
        subscription_level: Optional[str] = None,
        category: Optional[str] = None,
        task_type: Optional[str] = None,
        is_active: bool = True,
    ) -> List[TaskTemplateResponse]:
        """Get available task templates"""
        self._log_call(
            "get_task_templates",
            subscription_level=subscription_level,
            category=category,
            task_type=task_type,
            is_active=is_active,
        )
        if self._error:
            raise self._error

        # Subscription level hierarchy
        level_hierarchy = {"free": 0, "basic": 1, "pro": 2, "enterprise": 3}
        user_level = level_hierarchy.get(subscription_level, 0)

        results = []
        for template in self._templates.values():
            if is_active and not template.is_active:
                continue
            if category and template.category != category:
                continue
            if task_type and template.task_type.value != task_type:
                continue
            # Check subscription level
            template_level = level_hierarchy.get(template.required_subscription_level, 0)
            if template_level <= user_level:
                results.append(template)

        return results

    async def get_template(self, template_id: str) -> Optional[TaskTemplateResponse]:
        """Get task template by ID"""
        self._log_call("get_template", template_id=template_id)
        if self._error:
            raise self._error
        return self._templates.get(template_id)

    async def get_task_analytics(
        self, user_id: str, days: int = 30
    ) -> Optional[TaskAnalyticsResponse]:
        """Get task analytics for user"""
        self._log_call("get_task_analytics", user_id=user_id, days=days)
        if self._error:
            raise self._error

        task_ids = self._user_tasks_index.get(user_id, [])
        tasks = [self._tasks.get(tid) for tid in task_ids if self._tasks.get(tid)]

        total_tasks = len(tasks)
        active_tasks = sum(1 for t in tasks if t.status == TaskStatus.SCHEDULED)
        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        paused_tasks = sum(1 for t in tasks if t.status == TaskStatus.PAUSED)

        total_executions = sum(t.run_count for t in tasks)
        successful_executions = sum(t.success_count for t in tasks)
        failed_executions = sum(t.failure_count for t in tasks)
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0.0

        total_credits = sum(t.total_credits_consumed for t in tasks)

        task_type_dist = {}
        for t in tasks:
            tt = t.task_type.value
            task_type_dist[tt] = task_type_dist.get(tt, 0) + 1

        return TaskAnalyticsResponse(
            user_id=user_id,
            time_period=f"{days}_days",
            total_tasks=total_tasks,
            active_tasks=active_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            paused_tasks=paused_tasks,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            success_rate=success_rate,
            average_execution_time=0.0,
            total_credits_consumed=total_credits,
            total_tokens_used=0,
            total_api_calls=0,
            task_types_distribution=task_type_dist,
            busiest_hours=[9, 10, 11],
            busiest_days=["Monday", "Tuesday"],
        )

    async def cancel_user_tasks(self, user_id: str) -> int:
        """Cancel all tasks for a user"""
        self._log_call("cancel_user_tasks", user_id=user_id)
        if self._error:
            raise self._error

        task_ids = self._user_tasks_index.get(user_id, [])
        cancelled_count = 0
        now = datetime.now(timezone.utc)

        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task and task.deleted_at is None:
                updated_data = task.dict()
                updated_data["status"] = TaskStatus.CANCELLED
                updated_data["updated_at"] = now
                self._tasks[task_id] = TaskResponse(**updated_data)
                cancelled_count += 1

        return cancelled_count


class MockEventBus:
    """Mock NATS event bus"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []

    async def publish(self, event: Any):
        """Publish event"""
        self._call_log.append({"method": "publish", "event": event})
        self.published_events.append(event)

    async def publish_event(self, event: Any):
        """Publish event (alias)"""
        await self.publish(event)

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            event_types = [getattr(e, "event_type", str(e)) for e in self.published_events]
            assert event_type in str(event_types), f"Expected {event_type} event, got {event_types}"

    def assert_not_published(self):
        """Assert that no events were published"""
        assert len(self.published_events) == 0, f"Expected no events, but got {len(self.published_events)}"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def get_events_by_type(self, event_type: str) -> List[Any]:
        """Get events filtered by type"""
        return [
            e for e in self.published_events
            if hasattr(e, "event_type") and str(e.event_type) == event_type
        ]

    def clear(self):
        """Clear all published events"""
        self.published_events.clear()
        self._call_log.clear()


class MockNotificationClient:
    """Mock notification client"""

    def __init__(self):
        self.sent_notifications: List[Dict] = []
        self._error: Optional[Exception] = None

    def set_error(self, error: Exception):
        """Set an error to be raised on send"""
        self._error = error

    async def send_notification(
        self,
        recipient_id: str,
        notification_type: str,
        subject: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a notification"""
        if self._error:
            raise self._error

        self.sent_notifications.append({
            "recipient_id": recipient_id,
            "notification_type": notification_type,
            "subject": subject,
            "content": content,
            "metadata": metadata or {},
        })
        return True

    def assert_notification_sent(self, recipient_id: str = None):
        """Assert that a notification was sent"""
        assert len(self.sent_notifications) > 0, "No notifications were sent"
        if recipient_id:
            recipients = [n["recipient_id"] for n in self.sent_notifications]
            assert recipient_id in recipients, f"Expected notification to {recipient_id}, got {recipients}"


class MockCalendarClient:
    """Mock calendar client"""

    def __init__(self):
        self.created_events: List[Dict] = []
        self._error: Optional[Exception] = None

    def set_error(self, error: Exception):
        """Set an error to be raised"""
        self._error = error

    async def create_calendar_event(
        self,
        user_id: str,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a calendar event"""
        if self._error:
            raise self._error

        event_id = f"evt_{uuid.uuid4().hex[:16]}"
        event = {
            "event_id": event_id,
            "user_id": user_id,
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "description": description,
            "metadata": metadata or {},
        }
        self.created_events.append(event)
        return event

    async def update_calendar_event(
        self,
        event_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a calendar event"""
        if self._error:
            raise self._error
        return True


class MockAccountClient:
    """Mock account client"""

    def __init__(self):
        self._subscription_levels: Dict[str, str] = {}
        self._profiles: Dict[str, Dict] = {}
        self._error: Optional[Exception] = None

    def set_subscription_level(self, user_id: str, level: str):
        """Set subscription level for a user"""
        self._subscription_levels[user_id] = level

    def set_profile(self, user_id: str, profile: Dict):
        """Set profile for a user"""
        self._profiles[user_id] = profile

    def set_error(self, error: Exception):
        """Set an error to be raised"""
        self._error = error

    async def get_user_subscription_level(self, user_id: str) -> str:
        """Get user's subscription level"""
        if self._error:
            raise self._error
        return self._subscription_levels.get(user_id, "free")

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        if self._error:
            raise self._error
        return self._profiles.get(user_id)
