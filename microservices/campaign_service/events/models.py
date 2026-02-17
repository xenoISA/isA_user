"""
Campaign Event Data Models

Event type definitions and data structures for campaign service events.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Event Type Definitions
# =============================================================================


class CampaignEventType(str, Enum):
    """
    Events published by campaign_service.

    These are the authoritative event types for this service.
    Other services should reference these when subscribing.
    """
    # Campaign lifecycle events
    CREATED = "campaign.created"
    UPDATED = "campaign.updated"
    SCHEDULED = "campaign.scheduled"
    ACTIVATED = "campaign.activated"
    STARTED = "campaign.started"
    PAUSED = "campaign.paused"
    RESUMED = "campaign.resumed"
    COMPLETED = "campaign.completed"
    CANCELLED = "campaign.cancelled"

    # Message events
    MESSAGE_QUEUED = "campaign.message.queued"
    MESSAGE_SENT = "campaign.message.sent"
    MESSAGE_DELIVERED = "campaign.message.delivered"
    MESSAGE_OPENED = "campaign.message.opened"
    MESSAGE_CLICKED = "campaign.message.clicked"
    MESSAGE_CONVERTED = "campaign.message.converted"
    MESSAGE_BOUNCED = "campaign.message.bounced"
    MESSAGE_FAILED = "campaign.message.failed"
    MESSAGE_UNSUBSCRIBED = "campaign.message.unsubscribed"

    # Metric events
    METRIC_UPDATED = "campaign.metric.updated"

    # Error events
    ERROR = "campaign.error"


class CampaignSubscribedEventType(str, Enum):
    """
    Events that campaign_service subscribes to from other services.
    """
    # Task events (from task_service)
    TASK_EXECUTED = "task.executed"

    # Event events (from event_service)
    EVENT_STORED = "event.stored"

    # Notification events (from notification_service)
    NOTIFICATION_DELIVERED = "notification.delivered"
    NOTIFICATION_FAILED = "notification.failed"
    NOTIFICATION_OPENED = "notification.opened"
    NOTIFICATION_CLICKED = "notification.clicked"

    # User events (from account_service)
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    USER_PREFERENCES_UPDATED = "user.preferences.updated"

    # Subscription events (from subscription_service)
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPGRADED = "subscription.upgraded"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"

    # Order events (from order_service)
    ORDER_COMPLETED = "order.completed"


class CampaignStreamConfig:
    """Stream configuration for campaign_service"""
    STREAM_NAME = "campaign-stream"
    SUBJECTS = ["campaign.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "campaign"


# =============================================================================
# Event Data Models - Published Events
# =============================================================================


class CampaignCreatedEventData(BaseModel):
    """campaign.created event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    organization_id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Campaign name")
    campaign_type: str = Field(..., description="scheduled or triggered")
    status: str = Field(..., description="Campaign status (draft)")
    created_by: str = Field(..., description="User who created the campaign")
    cloned_from_id: Optional[str] = Field(None, description="Source campaign if cloned")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignUpdatedEventData(BaseModel):
    """campaign.updated event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    changed_fields: List[str] = Field(..., description="List of changed field names")
    updated_by: str = Field(..., description="User who updated the campaign")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignScheduledEventData(BaseModel):
    """campaign.scheduled event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    scheduled_at: str = Field(..., description="Scheduled execution time (ISO format)")
    task_id: Optional[str] = Field(None, description="Task ID from task_service")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignActivatedEventData(BaseModel):
    """campaign.activated event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    activated_at: str = Field(..., description="Activation time (ISO format)")
    trigger_count: int = Field(..., description="Number of triggers registered")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignStartedEventData(BaseModel):
    """campaign.started event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    execution_id: str = Field(..., description="Execution ID")
    audience_size: int = Field(..., description="Total audience size")
    holdout_size: int = Field(..., description="Holdout group size")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignPausedEventData(BaseModel):
    """campaign.paused event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    execution_id: Optional[str] = Field(None, description="Execution ID")
    paused_by: Optional[str] = Field(None, description="User who paused")
    messages_sent: int = Field(..., description="Messages sent before pause")
    messages_remaining: int = Field(..., description="Messages remaining")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignResumedEventData(BaseModel):
    """campaign.resumed event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    execution_id: Optional[str] = Field(None, description="Execution ID")
    resumed_by: Optional[str] = Field(None, description="User who resumed")
    messages_remaining: int = Field(..., description="Messages remaining")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignCompletedEventData(BaseModel):
    """campaign.completed event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    execution_id: str = Field(..., description="Execution ID")
    total_sent: int = Field(..., description="Total messages sent")
    total_delivered: int = Field(..., description="Total messages delivered")
    total_failed: int = Field(..., description="Total messages failed")
    duration_minutes: int = Field(..., description="Execution duration in minutes")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignCancelledEventData(BaseModel):
    """campaign.cancelled event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    cancelled_by: Optional[str] = Field(None, description="User who cancelled")
    reason: Optional[str] = Field(None, description="Cancellation reason")
    messages_sent_before_cancel: int = Field(..., description="Messages sent before cancel")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CampaignMessageEventData(BaseModel):
    """Base class for campaign message events"""
    campaign_id: str = Field(..., description="Campaign ID")
    message_id: str = Field(..., description="Message ID")
    execution_id: Optional[str] = Field(None, description="Execution ID")
    user_id: Optional[str] = Field(None, description="Recipient user ID")
    variant_id: Optional[str] = Field(None, description="Variant ID")
    channel_type: Optional[str] = Field(None, description="Channel type")

    # Additional fields for specific message events
    notification_id: Optional[str] = Field(None, description="Notification service ID")
    provider_message_id: Optional[str] = Field(None, description="Provider message ID")
    link_id: Optional[str] = Field(None, description="Link ID (for clicks)")
    link_url: Optional[str] = Field(None, description="Link URL (for clicks)")
    conversion_event: Optional[str] = Field(None, description="Conversion event type")
    conversion_value: Optional[float] = Field(None, description="Conversion value")
    attribution_model: Optional[str] = Field(None, description="Attribution model used")
    bounce_type: Optional[str] = Field(None, description="Bounce type (hard/soft)")
    error_reason: Optional[str] = Field(None, description="Error/bounce reason")
    user_agent: Optional[str] = Field(None, description="User agent (for opens)")

    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), Decimal: lambda v: float(v)}


class CampaignMetricUpdatedEventData(BaseModel):
    """campaign.metric.updated event data"""
    campaign_id: str = Field(..., description="Campaign ID")
    metric_type: str = Field(..., description="Metric type (sent, delivered, opened, etc)")
    count: int = Field(..., description="Current count")
    rate: Optional[float] = Field(None, description="Current rate")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# =============================================================================
# Event Data Models - Subscribed Events
# =============================================================================


class TaskExecutedEventData(BaseModel):
    """Data from task.executed event"""
    task_id: str = Field(..., description="Task ID")
    task_type: str = Field(..., description="Task type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload")
    executed_at: Optional[datetime] = Field(None, description="Execution time")


class EventStoredEventData(BaseModel):
    """Data from event.stored event"""
    event_id: str = Field(..., description="Event ID")
    event_type: str = Field(..., description="Event type")
    user_id: Optional[str] = Field(None, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    stored_at: Optional[datetime] = Field(None, description="Storage time")


class NotificationStatusEventData(BaseModel):
    """Data from notification.* status events"""
    notification_id: str = Field(..., description="Notification ID")
    message_id: Optional[str] = Field(None, description="Original message ID")
    status: str = Field(..., description="Notification status")
    provider_message_id: Optional[str] = Field(None, description="Provider message ID")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    bounce_type: Optional[str] = Field(None, description="Bounce type if bounced")
    timestamp: Optional[datetime] = Field(None, description="Status update time")


class UserDeletedEventData(BaseModel):
    """Data from user.deleted event (GDPR cleanup)"""
    user_id: str = Field(..., description="Deleted user ID")
    organization_id: Optional[str] = Field(None, description="User's organization")
    deleted_at: Optional[datetime] = Field(None, description="Deletion time")


class SubscriptionEventData(BaseModel):
    """Data from subscription.* events"""
    subscription_id: str = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    plan_id: Optional[str] = Field(None, description="Plan ID")
    previous_plan_id: Optional[str] = Field(None, description="Previous plan (for upgrades)")
    event_type: str = Field(..., description="created, upgraded, cancelled")
    timestamp: Optional[datetime] = Field(None, description="Event time")


class OrderCompletedEventData(BaseModel):
    """Data from order.completed event"""
    order_id: str = Field(..., description="Order ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    total_amount: Optional[float] = Field(None, description="Order total")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Order items")
    completed_at: Optional[datetime] = Field(None, description="Completion time")


__all__ = [
    # Event Types
    "CampaignEventType",
    "CampaignSubscribedEventType",
    "CampaignStreamConfig",
    # Published Event Data
    "CampaignCreatedEventData",
    "CampaignUpdatedEventData",
    "CampaignScheduledEventData",
    "CampaignActivatedEventData",
    "CampaignStartedEventData",
    "CampaignPausedEventData",
    "CampaignResumedEventData",
    "CampaignCompletedEventData",
    "CampaignCancelledEventData",
    "CampaignMessageEventData",
    "CampaignMetricUpdatedEventData",
    # Subscribed Event Data
    "TaskExecutedEventData",
    "EventStoredEventData",
    "NotificationStatusEventData",
    "UserDeletedEventData",
    "SubscriptionEventData",
    "OrderCompletedEventData",
]
