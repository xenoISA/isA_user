"""
Task Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

# Import only models (no I/O dependencies)
from .models import (
    TaskResponse,
    TaskExecutionResponse,
    TaskTemplateResponse,
    TaskAnalyticsResponse,
)


# ============================================================================
# Custom Exceptions - defined here to avoid importing repository
# ============================================================================


class TaskNotFoundError(Exception):
    """Task not found error"""
    def __init__(self, message: str = "Task not found", task_id: str = None):
        super().__init__(message)
        self.task_id = task_id


class TaskExecutionError(Exception):
    """Task execution error"""
    def __init__(self, message: str, task_id: str = None, error_code: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.error_code = error_code


class TaskLimitExceededError(Exception):
    """Task limit exceeded error"""
    def __init__(self, message: str, user_id: str = None, limit_type: str = None):
        super().__init__(message)
        self.user_id = user_id
        self.limit_type = limit_type


class TaskPermissionDeniedError(Exception):
    """Permission denied for task operation"""
    def __init__(self, message: str, task_id: str = None, action: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.action = action


class TaskValidationError(Exception):
    """Task configuration validation error"""
    def __init__(self, message: str, field: str = None):
        super().__init__(message)
        self.field = field


class DuplicateTaskError(Exception):
    """Duplicate task error"""
    pass


# ============================================================================
# Protocol Interfaces
# ============================================================================


@runtime_checkable
class TaskRepositoryProtocol(Protocol):
    """
    Interface for Task Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_task(
        self, user_id: str, task_data: Dict[str, Any]
    ) -> Optional[TaskResponse]:
        """Create a new task"""
        ...

    async def get_task_by_id(
        self, task_id: str, user_id: str = None
    ) -> Optional[TaskResponse]:
        """Get task by ID"""
        ...

    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TaskResponse]:
        """Get all tasks for a user with optional filtering"""
        ...

    async def update_task(
        self, task_id: str, updates: Dict[str, Any], user_id: str = None
    ) -> bool:
        """Update task data"""
        ...

    async def delete_task(self, task_id: str, user_id: str = None) -> bool:
        """Soft delete a task"""
        ...

    async def get_pending_tasks(self, limit: int = 100) -> List[TaskResponse]:
        """Get pending tasks for scheduler"""
        ...

    async def update_task_execution_info(
        self, task_id: str, success: bool, credits_consumed: float = 0
    ) -> bool:
        """Update task execution statistics"""
        ...

    async def create_execution_record(
        self, task_id: str, user_id: str, execution_data: Dict[str, Any]
    ) -> Optional[TaskExecutionResponse]:
        """Create execution record"""
        ...

    async def update_execution_record(
        self, execution_id: str, updates: Dict[str, Any]
    ) -> bool:
        """Update execution record"""
        ...

    async def get_task_executions(
        self, task_id: str, limit: int = 50, offset: int = 0
    ) -> List[TaskExecutionResponse]:
        """Get task execution history"""
        ...

    async def get_task_templates(
        self,
        subscription_level: Optional[str] = None,
        category: Optional[str] = None,
        task_type: Optional[str] = None,
        is_active: bool = True,
    ) -> List[TaskTemplateResponse]:
        """Get available task templates"""
        ...

    async def get_template(self, template_id: str) -> Optional[TaskTemplateResponse]:
        """Get task template by ID"""
        ...

    async def get_task_analytics(
        self, user_id: str, days: int = 30
    ) -> Optional[TaskAnalyticsResponse]:
        """Get task analytics for user"""
        ...

    async def cancel_user_tasks(self, user_id: str) -> int:
        """Cancel all tasks for a user (used when user is deleted)"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class NotificationClientProtocol(Protocol):
    """Interface for Notification Service Client"""

    async def send_notification(
        self,
        recipient_id: str,
        notification_type: str,
        subject: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a notification to user"""
        ...


@runtime_checkable
class CalendarClientProtocol(Protocol):
    """Interface for Calendar Service Client"""

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
        ...

    async def update_calendar_event(
        self,
        event_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a calendar event"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client"""

    async def get_user_subscription_level(self, user_id: str) -> str:
        """Get user's subscription level"""
        ...

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        ...


__all__ = [
    # Exceptions
    "TaskNotFoundError",
    "TaskExecutionError",
    "TaskLimitExceededError",
    "TaskPermissionDeniedError",
    "TaskValidationError",
    "DuplicateTaskError",
    # Protocols
    "TaskRepositoryProtocol",
    "EventBusProtocol",
    "NotificationClientProtocol",
    "CalendarClientProtocol",
    "AccountClientProtocol",
]
