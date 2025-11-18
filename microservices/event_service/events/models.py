"""
Event Service - Event Models

Defines event payloads published by the event service.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class EventModel(BaseModel):
    """Base event model for all event service events"""
    event_id: str = Field(..., description="Event ID")
    event_type: str = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User ID associated with the event")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class EventCreatedEvent(BaseModel):
    """Event published when a new event is created"""
    event_id: str = Field(..., description="Event ID")
    event_type: str = Field(..., description="Type of event created")
    event_source: str = Field(..., description="Source of the event")
    event_category: str = Field(..., description="Category of the event")
    user_id: Optional[str] = Field(None, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")


class EventProcessedEvent(BaseModel):
    """Event published when an event is successfully processed"""
    event_id: str = Field(..., description="Event ID")
    processor_name: str = Field(..., description="Name of processor that handled the event")
    status: str = Field(..., description="Processing status")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    duration_ms: Optional[int] = Field(None, description="Processing duration in milliseconds")
    result: Optional[Dict[str, Any]] = Field(None, description="Processing result data")


class EventFailedEvent(BaseModel):
    """Event published when event processing fails"""
    event_id: str = Field(..., description="Event ID")
    processor_name: str = Field(..., description="Name of processor that failed")
    error_message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    retry_count: int = Field(0, description="Number of retry attempts")
    failed_at: datetime = Field(default_factory=datetime.utcnow, description="Failure timestamp")
    will_retry: bool = Field(False, description="Whether the event will be retried")


class EventReplayStartedEvent(BaseModel):
    """Event published when event replay is started"""
    replay_id: str = Field(..., description="Replay job ID")
    start_time: datetime = Field(..., description="Start time for replay")
    end_time: datetime = Field(..., description="End time for replay")
    event_types: Optional[list] = Field(None, description="Event types to replay")
    target_service: Optional[str] = Field(None, description="Target service for replay")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Replay start timestamp")


class EventReplayCompletedEvent(BaseModel):
    """Event published when event replay is completed"""
    replay_id: str = Field(..., description="Replay job ID")
    events_replayed: int = Field(..., description="Number of events replayed")
    completed_at: datetime = Field(default_factory=datetime.utcnow, description="Completion timestamp")
    duration_ms: int = Field(..., description="Total replay duration in milliseconds")
    success: bool = Field(True, description="Whether replay was successful")


__all__ = [
    "EventModel",
    "EventCreatedEvent",
    "EventProcessedEvent",
    "EventFailedEvent",
    "EventReplayStartedEvent",
    "EventReplayCompletedEvent",
]
