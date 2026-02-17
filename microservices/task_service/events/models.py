"""
Task Service Event Data Models

task_service ^���pnӄ�I
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class TaskEventType(str, Enum):
    """
    Events published by task_service.

    Stream: task-stream
    Subjects: task.>
    """
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"


class TaskSubscribedEventType(str, Enum):
    """Events that task_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class TaskStreamConfig:
    """Stream configuration for task_service"""
    STREAM_NAME = "task-stream"
    SUBJECTS = ["task.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "task"



class UserDeletedEventData(BaseModel):
    """
    (7 d��pn (task_service ��)

    task_service �,d��vֈ(7�@	��

    NATS Subject: *.user.deleted
    Publisher: account_service
    """

    user_id: str = Field(..., description="User ID")
    timestamp: Optional[datetime] = Field(None, description=" d��")
    reason: Optional[str] = Field(None, description=" d��")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskCreatedEventData(BaseModel):
    """
    ������pn

    task_service ����d��

    NATS Subject: task.created
    Subscribers: notification_service, calendar_service
    """

    user_id: str = Field(..., description="(7ID")
    task_id: str = Field(..., description="Task ID")
    task_type: str = Field(..., description="Task type")
    name: str = Field(..., description="Task name")
    schedule: Optional[str] = Field(None, description="�h�")
    timestamp: Optional[datetime] = Field(None, description="���")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskCompletedEventData(BaseModel):
    """
    �����pn

    task_service ��gL��d��

    NATS Subject: task.completed
    Subscribers: notification_service, analytics_service, billing_service
    """

    user_id: str = Field(..., description="(7ID")
    task_id: str = Field(..., description="Task ID")
    execution_id: str = Field(..., description="gLID")
    task_type: str = Field(..., description="Task type")
    status: str = Field(..., description="gL�: success, failed")
    credits_consumed: Optional[float] = Field(None, description="���")
    duration_seconds: Optional[float] = Field(None, description="gL��	")
    timestamp: Optional[datetime] = Field(None, description="���")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskFailedEventData(BaseModel):
    """
    ��1%��pn

    task_service ��gL1%��d��

    NATS Subject: task.failed
    Subscribers: notification_service, monitoring_service
    """

    user_id: str = Field(..., description="(7ID")
    task_id: str = Field(..., description="Task ID")
    execution_id: str = Field(..., description="gLID")
    task_type: str = Field(..., description="Task type")
    error_message: str = Field(..., description="��o")
    retry_count: Optional[int] = Field(None, description="��!p")
    timestamp: Optional[datetime] = Field(None, description="1%��")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Helper functions
def parse_user_deleted_event(event_data: dict) -> UserDeletedEventData:
    """� user.deleted ��pn"""
    return UserDeletedEventData(**event_data)


def create_task_created_event_data(
    user_id: str,
    task_id: str,
    task_type: str,
    name: str,
    schedule: Optional[str] = None,
) -> TaskCreatedEventData:
    """� task.created ��pn"""
    return TaskCreatedEventData(
        user_id=user_id,
        task_id=task_id,
        task_type=task_type,
        name=name,
        schedule=schedule,
        timestamp=datetime.utcnow(),
    )


def create_task_completed_event_data(
    user_id: str,
    task_id: str,
    execution_id: str,
    task_type: str,
    status: str,
    credits_consumed: Optional[float] = None,
    duration_seconds: Optional[float] = None,
) -> TaskCompletedEventData:
    """� task.completed ��pn"""
    return TaskCompletedEventData(
        user_id=user_id,
        task_id=task_id,
        execution_id=execution_id,
        task_type=task_type,
        status=status,
        credits_consumed=credits_consumed,
        duration_seconds=duration_seconds,
        timestamp=datetime.utcnow(),
    )


def create_task_failed_event_data(
    user_id: str,
    task_id: str,
    execution_id: str,
    task_type: str,
    error_message: str,
    retry_count: Optional[int] = None,
) -> TaskFailedEventData:
    """� task.failed ��pn"""
    return TaskFailedEventData(
        user_id=user_id,
        task_id=task_id,
        execution_id=execution_id,
        task_type=task_type,
        error_message=error_message,
        retry_count=retry_count,
        timestamp=datetime.utcnow(),
    )


__all__ = [
    "UserDeletedEventData",
    "TaskCreatedEventData",
    "TaskCompletedEventData",
    "TaskFailedEventData",
    "parse_user_deleted_event",
    "create_task_created_event_data",
    "create_task_completed_event_data",
    "create_task_failed_event_data",
]
