"""
Task Service Event Data Models

task_service ^„‹öpnÓ„šI
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserDeletedEventData(BaseModel):
    """
    (7 d‹öpn (task_service ÆÒ)

    task_service Ñ,d‹övÖˆ(7„@	û¡

    NATS Subject: *.user.deleted
    Publisher: account_service
    """

    user_id: str = Field(..., description="« d„(7ID")
    timestamp: Optional[datetime] = Field(None, description=" döô")
    reason: Optional[str] = Field(None, description=" dŸà")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskCreatedEventData(BaseModel):
    """
    û¡úŸ‹öpn

    task_service úû¡Ñd‹ö

    NATS Subject: task.created
    Subscribers: notification_service, calendar_service
    """

    user_id: str = Field(..., description="(7ID")
    task_id: str = Field(..., description="û¡ID")
    task_type: str = Field(..., description="û¡{‹")
    name: str = Field(..., description="û¡ğ")
    schedule: Optional[str] = Field(None, description="¦h¾")
    timestamp: Optional[datetime] = Field(None, description="úöô")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskCompletedEventData(BaseModel):
    """
    û¡Œ‹öpn

    task_service û¡gLŒÑd‹ö

    NATS Subject: task.completed
    Subscribers: notification_service, analytics_service, billing_service
    """

    user_id: str = Field(..., description="(7ID")
    task_id: str = Field(..., description="û¡ID")
    execution_id: str = Field(..., description="gLID")
    task_type: str = Field(..., description="û¡{‹")
    status: str = Field(..., description="gL¶: success, failed")
    credits_consumed: Optional[float] = Field(None, description="ˆ„ï")
    duration_seconds: Optional[float] = Field(None, description="gLöÒ	")
    timestamp: Optional[datetime] = Field(None, description="Œöô")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskFailedEventData(BaseModel):
    """
    û¡1%‹öpn

    task_service û¡gL1%öÑd‹ö

    NATS Subject: task.failed
    Subscribers: notification_service, monitoring_service
    """

    user_id: str = Field(..., description="(7ID")
    task_id: str = Field(..., description="û¡ID")
    execution_id: str = Field(..., description="gLID")
    task_type: str = Field(..., description="û¡{‹")
    error_message: str = Field(..., description="ïáo")
    retry_count: Optional[int] = Field(None, description="ÍÕ!p")
    timestamp: Optional[datetime] = Field(None, description="1%öô")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Helper functions
def parse_user_deleted_event(event_data: dict) -> UserDeletedEventData:
    """ã user.deleted ‹öpn"""
    return UserDeletedEventData(**event_data)


def create_task_created_event_data(
    user_id: str,
    task_id: str,
    task_type: str,
    name: str,
    schedule: Optional[str] = None,
) -> TaskCreatedEventData:
    """ú task.created ‹öpn"""
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
    """ú task.completed ‹öpn"""
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
    """ú task.failed ‹öpn"""
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
