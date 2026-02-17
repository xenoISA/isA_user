"""
Event Service Data Contract

Defines canonical data structures for event service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for event service test data.
Zero hardcoded data - all values generated through factory methods.
"""

import uuid
import random
import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import from production models for type consistency
from microservices.event_service.models import (
    Event,
    EventStream,
    EventProcessor,
    EventSubscription,
    EventProjection,
    EventProcessingResult,
    EventCreateRequest,
    EventQueryRequest,
    EventResponse,
    EventListResponse,
    EventStatistics,
    EventReplayRequest,
    RudderStackEvent,
    EventSource,
    EventCategory,
    EventStatus,
    ProcessingStatus,
)


# ============================================================================
# Re-export Enums from production models
# ============================================================================

# EventSource enum values:
# - FRONTEND: Frontend user behavior
# - BACKEND: Backend business logic
# - SYSTEM: System internal
# - IOT_DEVICE: IoT device
# - EXTERNAL_API: External API
# - SCHEDULED: Scheduled task

# EventCategory enum values:
# - USER_ACTION, PAGE_VIEW, FORM_SUBMIT, CLICK (user behavior)
# - USER_LIFECYCLE, PAYMENT, ORDER, TASK (business events)
# - SYSTEM, SECURITY, PERFORMANCE, ERROR (system events)
# - DEVICE, DEVICE_STATUS, TELEMETRY, COMMAND, ALERT (IoT events)

# EventStatus enum values:
# - PENDING: Awaiting processing
# - PROCESSING: Currently being processed
# - PROCESSED: Successfully processed
# - FAILED: Processing failed
# - ARCHIVED: Archived

# ProcessingStatus enum values:
# - SUCCESS: Processing succeeded
# - FAILED: Processing failed
# - SKIPPED: Processing skipped
# - RETRY: Needs retry


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class EventCreateRequestContract(BaseModel):
    """
    Contract: Event creation request schema

    Used for creating new events via API.
    Maps to EventCreateRequest from production models.
    """
    model_config = ConfigDict(from_attributes=True)

    event_type: str = Field(..., min_length=1, max_length=255, description="Event type identifier")
    event_source: EventSource = Field(default=EventSource.BACKEND, description="Event source")
    event_category: EventCategory = Field(default=EventCategory.USER_ACTION, description="Event category")
    user_id: Optional[str] = Field(None, max_length=255, description="User ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event metadata")
    context: Optional[Dict[str, Any]] = Field(None, description="Event context")

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Event type must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "user.logged_in",
                "event_source": "backend",
                "event_category": "user_lifecycle",
                "user_id": "user_001",
                "data": {"login_method": "oauth"},
                "metadata": {"source": "api"},
            }
        }


class EventQueryRequestContract(BaseModel):
    """
    Contract: Event query request schema

    Used for querying events with filters.
    Maps to EventQueryRequest from production models.
    """
    model_config = ConfigDict(from_attributes=True)

    user_id: Optional[str] = Field(None, description="Filter by user ID")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    event_source: Optional[EventSource] = Field(None, description="Filter by event source")
    event_category: Optional[EventCategory] = Field(None, description="Filter by event category")
    status: Optional[EventStatus] = Field(None, description="Filter by event status")
    start_time: Optional[datetime] = Field(None, description="Start of time range")
    end_time: Optional[datetime] = Field(None, description="End of time range")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results (1-1000)")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")

    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Limit cannot exceed 1000"""
        if v > 1000:
            raise ValueError("Query limit cannot exceed 1000")
        return v

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate time range is valid"""
        if v is not None and info.data.get('start_time') is not None:
            start = info.data['start_time']
            if v < start:
                raise ValueError("end_time must be after start_time")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_001",
                "event_type": "user.logged_in",
                "event_source": "backend",
                "start_time": "2025-12-01T00:00:00Z",
                "end_time": "2025-12-30T23:59:59Z",
                "limit": 100,
                "offset": 0,
            }
        }


class EventBatchCreateRequestContract(BaseModel):
    """
    Contract: Batch event creation request schema

    Used for creating multiple events at once.
    """
    events: List[EventCreateRequestContract] = Field(
        ..., min_length=1, max_length=100,
        description="List of events to create (max 100)"
    )

    @field_validator('events')
    @classmethod
    def validate_events(cls, v: List) -> List:
        """Validate batch size"""
        if len(v) > 100:
            raise ValueError("Maximum 100 events per batch")
        if len(v) == 0:
            raise ValueError("At least one event required")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_type": "user.logged_in",
                        "event_source": "backend",
                        "event_category": "user_lifecycle",
                        "user_id": "user_001",
                    }
                ]
            }
        }


class EventReplayRequestContract(BaseModel):
    """
    Contract: Event replay request schema

    Used for replaying events.
    """
    model_config = ConfigDict(from_attributes=True)

    stream_id: Optional[str] = Field(None, description="Stream ID to replay")
    event_ids: Optional[List[str]] = Field(None, description="Specific event IDs to replay")
    start_time: Optional[datetime] = Field(None, description="Start of time range")
    end_time: Optional[datetime] = Field(None, description="End of time range")
    target_service: Optional[str] = Field(None, max_length=100, description="Target service for replay")
    dry_run: bool = Field(default=False, description="Simulate replay without executing")

    class Config:
        json_schema_extra = {
            "example": {
                "stream_id": "stream_abc123",
                "start_time": "2025-12-01T00:00:00Z",
                "end_time": "2025-12-30T23:59:59Z",
                "target_service": "notification_service",
                "dry_run": True,
            }
        }


class EventProcessorCreateRequestContract(BaseModel):
    """
    Contract: Event processor creation request schema

    Used for creating event processors.
    """
    processor_name: str = Field(..., min_length=1, max_length=255, description="Processor name")
    processor_type: str = Field(..., min_length=1, max_length=100, description="Processor type")
    enabled: bool = Field(default=True, description="Whether processor is enabled")
    priority: int = Field(default=0, ge=0, le=100, description="Processor priority (0-100)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Event filters")
    config: Dict[str, Any] = Field(default_factory=dict, description="Processor configuration")

    @field_validator('processor_name')
    @classmethod
    def validate_processor_name(cls, v: str) -> str:
        """Processor name must not be empty"""
        if not v or not v.strip():
            raise ValueError("processor_name cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "processor_name": "notification_processor",
                "processor_type": "webhook",
                "enabled": True,
                "priority": 10,
                "filters": {"event_types": ["user.created"]},
                "config": {"webhook_url": "https://example.com/webhook"},
            }
        }


class EventSubscriptionCreateRequestContract(BaseModel):
    """
    Contract: Event subscription creation request schema

    Used for creating event subscriptions.
    """
    subscriber_name: str = Field(..., min_length=1, max_length=255, description="Subscriber name")
    subscriber_type: str = Field(default="service", max_length=100, description="Subscriber type")
    event_types: List[str] = Field(..., min_length=1, description="Event types to subscribe to")
    event_sources: Optional[List[EventSource]] = Field(None, description="Filter by event sources")
    event_categories: Optional[List[EventCategory]] = Field(None, description="Filter by categories")
    callback_url: Optional[str] = Field(None, max_length=500, description="Webhook callback URL")
    webhook_secret: Optional[str] = Field(None, max_length=255, description="Webhook secret")
    enabled: bool = Field(default=True, description="Whether subscription is enabled")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="Retry configuration")

    @field_validator('subscriber_name')
    @classmethod
    def validate_subscriber_name(cls, v: str) -> str:
        """Subscriber name must not be empty"""
        if not v or not v.strip():
            raise ValueError("subscriber_name cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "subscriber_name": "notification_service",
                "subscriber_type": "service",
                "event_types": ["user.created", "user.updated"],
                "callback_url": "https://notification.example.com/events",
                "enabled": True,
            }
        }


class EventProjectionQueryRequestContract(BaseModel):
    """
    Contract: Event projection query request schema

    Used for querying event projections.
    """
    entity_type: str = Field(..., min_length=1, max_length=100, description="Entity type")
    entity_id: str = Field(..., min_length=1, max_length=255, description="Entity ID")
    projection_name: str = Field(default="default", max_length=255, description="Projection name")

    class Config:
        json_schema_extra = {
            "example": {
                "entity_type": "user",
                "entity_id": "user_001",
                "projection_name": "user_state",
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class EventResponseContract(BaseModel):
    """
    Contract: Event response schema

    Validates API response structure for events.
    Maps to EventResponse from production models.
    """
    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(..., description="Unique event ID")
    event_type: str = Field(..., description="Event type")
    event_source: EventSource = Field(..., description="Event source")
    event_category: EventCategory = Field(..., description="Event category")
    user_id: Optional[str] = Field(None, description="User ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    status: EventStatus = Field(..., description="Event status")
    timestamp: datetime = Field(..., description="Event timestamp")
    created_at: datetime = Field(..., description="Record creation time")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123def456",
                "event_type": "user.logged_in",
                "event_source": "backend",
                "event_category": "user_lifecycle",
                "user_id": "user_001",
                "data": {"login_method": "oauth"},
                "status": "processed",
                "timestamp": "2025-12-22T10:00:00Z",
                "created_at": "2025-12-22T10:00:00Z",
            }
        }


class EventDetailResponseContract(BaseModel):
    """
    Contract: Detailed event response schema

    Full event details including all fields.
    """
    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(..., description="Unique event ID")
    event_type: str = Field(..., description="Event type")
    event_source: EventSource = Field(..., description="Event source")
    event_category: EventCategory = Field(..., description="Event category")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    device_id: Optional[str] = Field(None, description="Device ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    context: Optional[Dict[str, Any]] = Field(None, description="Event context")
    properties: Optional[Dict[str, Any]] = Field(None, description="Event properties")
    status: EventStatus = Field(..., description="Event status")
    processed_at: Optional[datetime] = Field(None, description="Processing time")
    processors: List[str] = Field(default_factory=list, description="Processors that handled event")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Retry count")
    timestamp: datetime = Field(..., description="Event timestamp")
    created_at: datetime = Field(..., description="Record creation time")
    updated_at: datetime = Field(..., description="Last update time")
    version: str = Field(default="1.0.0", description="Event version")
    schema_version: str = Field(default="1.0.0", description="Schema version")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123def456",
                "event_type": "user.logged_in",
                "event_source": "backend",
                "event_category": "user_lifecycle",
                "user_id": "user_001",
                "data": {"login_method": "oauth"},
                "metadata": {"source": "api"},
                "status": "processed",
                "processors": ["notification_processor"],
                "timestamp": "2025-12-22T10:00:00Z",
                "created_at": "2025-12-22T10:00:00Z",
                "updated_at": "2025-12-22T10:00:01Z",
            }
        }


class EventListResponseContract(BaseModel):
    """
    Contract: Event list response schema

    Validates API response for event list queries.
    Maps to EventListResponse from production models.
    """
    events: List[EventResponseContract] = Field(..., description="List of events")
    total: int = Field(..., ge=0, description="Total matching events")
    limit: int = Field(..., ge=1, le=1000, description="Query limit")
    offset: int = Field(..., ge=0, description="Query offset")
    has_more: bool = Field(..., description="Whether more results exist")

    class Config:
        json_schema_extra = {
            "example": {
                "events": [],
                "total": 0,
                "limit": 100,
                "offset": 0,
                "has_more": False,
            }
        }


class EventStatisticsResponseContract(BaseModel):
    """
    Contract: Event statistics response schema

    Validates API response for event statistics.
    Maps to EventStatistics from production models.
    """
    total_events: int = Field(..., ge=0, description="Total event count")
    pending_events: int = Field(..., ge=0, description="Pending events")
    processed_events: int = Field(..., ge=0, description="Processed events")
    failed_events: int = Field(..., ge=0, description="Failed events")
    events_by_source: Dict[str, int] = Field(default_factory=dict, description="By source")
    events_by_category: Dict[str, int] = Field(default_factory=dict, description="By category")
    events_by_type: Dict[str, int] = Field(default_factory=dict, description="By type")
    events_today: int = Field(default=0, ge=0, description="Events today")
    events_this_week: int = Field(default=0, ge=0, description="Events this week")
    events_this_month: int = Field(default=0, ge=0, description="Events this month")
    average_processing_time: float = Field(default=0.0, ge=0, description="Avg processing time (s)")
    processing_rate: float = Field(default=0.0, ge=0, le=100, description="Processing rate (%)")
    error_rate: float = Field(default=0.0, ge=0, le=100, description="Error rate (%)")
    top_users: List[Dict[str, Any]] = Field(default_factory=list, description="Top active users")
    top_event_types: List[Dict[str, Any]] = Field(default_factory=list, description="Top event types")
    calculated_at: datetime = Field(..., description="Calculation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 125000,
                "pending_events": 500,
                "processed_events": 124000,
                "failed_events": 500,
                "events_by_source": {"backend": 100000, "frontend": 25000},
                "events_today": 1500,
                "events_this_week": 10500,
                "events_this_month": 45000,
                "average_processing_time": 0.05,
                "processing_rate": 99.6,
                "error_rate": 0.4,
                "calculated_at": "2025-12-22T12:00:00Z",
            }
        }


class EventProcessingResultResponseContract(BaseModel):
    """
    Contract: Event processing result response schema

    Validates processing result data.
    """
    event_id: str = Field(..., description="Event ID")
    processor_name: str = Field(..., description="Processor name")
    status: ProcessingStatus = Field(..., description="Processing status")
    message: Optional[str] = Field(None, description="Result message")
    processed_at: datetime = Field(..., description="Processing time")
    duration_ms: Optional[int] = Field(None, ge=0, description="Processing duration (ms)")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123",
                "processor_name": "notification_processor",
                "status": "success",
                "message": "Notification sent",
                "processed_at": "2025-12-22T10:00:01Z",
                "duration_ms": 45,
            }
        }


class EventStreamResponseContract(BaseModel):
    """
    Contract: Event stream response schema

    Validates event stream data.
    """
    stream_id: str = Field(..., description="Stream ID")
    stream_type: str = Field(..., description="Stream type")
    entity_id: str = Field(..., description="Entity ID")
    entity_type: str = Field(..., description="Entity type")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Events in stream")
    version: int = Field(default=0, ge=0, description="Stream version")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        json_schema_extra = {
            "example": {
                "stream_id": "stream_abc123",
                "stream_type": "user_activity",
                "entity_id": "user_001",
                "entity_type": "user",
                "events": [],
                "version": 5,
                "created_at": "2025-12-01T00:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
            }
        }


class EventProjectionResponseContract(BaseModel):
    """
    Contract: Event projection response schema

    Validates event projection data.
    """
    projection_id: str = Field(..., description="Projection ID")
    projection_name: str = Field(..., description="Projection name")
    entity_id: str = Field(..., description="Entity ID")
    entity_type: str = Field(..., description="Entity type")
    state: Dict[str, Any] = Field(default_factory=dict, description="Current state")
    version: int = Field(default=0, ge=0, description="Projection version")
    last_event_id: Optional[str] = Field(None, description="Last processed event ID")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        json_schema_extra = {
            "example": {
                "projection_id": "proj_abc123",
                "projection_name": "user_state",
                "entity_id": "user_001",
                "entity_type": "user",
                "state": {"login_count": 42, "last_login": "2025-12-22T10:00:00Z"},
                "version": 42,
                "last_event_id": "evt_xyz789",
                "created_at": "2025-12-01T00:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
            }
        }


class EventProcessorResponseContract(BaseModel):
    """
    Contract: Event processor response schema

    Validates event processor data.
    """
    processor_id: str = Field(..., description="Processor ID")
    processor_name: str = Field(..., description="Processor name")
    processor_type: str = Field(..., description="Processor type")
    enabled: bool = Field(..., description="Whether enabled")
    priority: int = Field(..., ge=0, description="Processor priority")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Event filters")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration")
    error_count: int = Field(default=0, ge=0, description="Error count")
    last_error: Optional[str] = Field(None, description="Last error message")
    last_processed_at: Optional[datetime] = Field(None, description="Last processing time")

    class Config:
        json_schema_extra = {
            "example": {
                "processor_id": "proc_abc123",
                "processor_name": "notification_processor",
                "processor_type": "webhook",
                "enabled": True,
                "priority": 10,
                "filters": {"event_types": ["user.created"]},
                "config": {"webhook_url": "https://example.com/webhook"},
                "error_count": 0,
                "last_processed_at": "2025-12-22T10:00:00Z",
            }
        }


class EventSubscriptionResponseContract(BaseModel):
    """
    Contract: Event subscription response schema

    Validates event subscription data.
    """
    subscription_id: str = Field(..., description="Subscription ID")
    subscriber_name: str = Field(..., description="Subscriber name")
    subscriber_type: str = Field(..., description="Subscriber type")
    event_types: List[str] = Field(..., description="Subscribed event types")
    event_sources: Optional[List[str]] = Field(None, description="Event source filters")
    event_categories: Optional[List[str]] = Field(None, description="Category filters")
    callback_url: Optional[str] = Field(None, description="Callback URL")
    enabled: bool = Field(..., description="Whether enabled")
    retry_policy: Dict[str, Any] = Field(default_factory=dict, description="Retry policy")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub_abc123",
                "subscriber_name": "notification_service",
                "subscriber_type": "service",
                "event_types": ["user.created", "user.updated"],
                "callback_url": "https://notification.example.com/events",
                "enabled": True,
                "retry_policy": {"max_retries": 3},
                "created_at": "2025-12-01T00:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
            }
        }


class EventServiceHealthResponseContract(BaseModel):
    """
    Contract: Event service health response schema

    Validates service health check response.
    """
    service: str = Field(default="event_service", description="Service name")
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$", description="Health status")
    port: int = Field(..., ge=1024, le=65535, description="Service port")
    version: str = Field(..., description="Service version")
    database_connected: bool = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Check timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "event_service",
                "status": "healthy",
                "port": 8211,
                "version": "1.0.0",
                "database_connected": True,
                "timestamp": "2025-12-22T12:00:00Z",
            }
        }


class EventBatchCreateResponseContract(BaseModel):
    """
    Contract: Batch event creation response schema

    Validates batch event creation response.
    """
    successful_count: int = Field(..., ge=0, description="Successfully created events")
    failed_count: int = Field(..., ge=0, description="Failed events")
    results: List[Dict[str, Any]] = Field(..., description="Individual results")

    class Config:
        json_schema_extra = {
            "example": {
                "successful_count": 5,
                "failed_count": 0,
                "results": [{"event_id": "evt_001", "success": True}],
            }
        }


class EventReplayResponseContract(BaseModel):
    """
    Contract: Event replay response schema

    Validates event replay response.
    """
    replayed_count: int = Field(..., ge=0, description="Events replayed")
    failed_count: int = Field(..., ge=0, description="Events failed")
    dry_run: bool = Field(..., description="Whether dry run")
    target_service: Optional[str] = Field(None, description="Target service")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Replay results")

    class Config:
        json_schema_extra = {
            "example": {
                "replayed_count": 10,
                "failed_count": 0,
                "dry_run": False,
                "target_service": "notification_service",
                "results": [],
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class EventTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Zero hardcoded data - all values generated dynamically.
    Methods prefixed with 'make_' generate valid data.
    Methods prefixed with 'make_invalid_' generate invalid data.
    """

    # ========================================================================
    # ID Generators
    # ========================================================================

    @staticmethod
    def make_event_id() -> str:
        """Generate unique event ID"""
        return f"evt_{uuid.uuid4().hex}"

    @staticmethod
    def make_stream_id() -> str:
        """Generate unique stream ID"""
        return f"stream_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_processor_id() -> str:
        """Generate unique processor ID"""
        return f"proc_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_subscription_id() -> str:
        """Generate unique subscription ID"""
        return f"sub_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_projection_id() -> str:
        """Generate unique projection ID"""
        return f"proj_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique user ID"""
        return f"user_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate unique organization ID"""
        return f"org_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_session_id() -> str:
        """Generate unique session ID"""
        return f"sess_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_device_id() -> str:
        """Generate unique device ID"""
        return f"dev_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_uuid() -> str:
        """Generate standard UUID"""
        return str(uuid.uuid4())

    # ========================================================================
    # Event Type Generators
    # ========================================================================

    @staticmethod
    def make_event_type() -> str:
        """Generate random event type"""
        domains = ["user", "device", "order", "payment", "session", "album", "media"]
        actions = ["created", "updated", "deleted", "viewed", "logged_in", "logged_out"]
        return f"{random.choice(domains)}.{random.choice(actions)}"

    @staticmethod
    def make_event_type_user() -> str:
        """Generate user-related event type"""
        actions = ["created", "updated", "deleted", "logged_in", "logged_out", "password_reset"]
        return f"user.{random.choice(actions)}"

    @staticmethod
    def make_event_type_device() -> str:
        """Generate device-related event type"""
        actions = ["registered", "connected", "disconnected", "updated", "command_sent"]
        return f"device.{random.choice(actions)}"

    @staticmethod
    def make_event_type_order() -> str:
        """Generate order-related event type"""
        actions = ["created", "confirmed", "shipped", "delivered", "cancelled"]
        return f"order.{random.choice(actions)}"

    # ========================================================================
    # Enum Generators
    # ========================================================================

    @staticmethod
    def make_event_source() -> EventSource:
        """Generate random event source"""
        return random.choice(list(EventSource))

    @staticmethod
    def make_event_category() -> EventCategory:
        """Generate random event category"""
        return random.choice(list(EventCategory))

    @staticmethod
    def make_event_status() -> EventStatus:
        """Generate random event status"""
        return random.choice(list(EventStatus))

    @staticmethod
    def make_processing_status() -> ProcessingStatus:
        """Generate random processing status"""
        return random.choice(list(ProcessingStatus))

    # ========================================================================
    # String Generators
    # ========================================================================

    @staticmethod
    def make_processor_name() -> str:
        """Generate random processor name"""
        prefixes = ["notification", "analytics", "audit", "webhook", "sync"]
        return f"{random.choice(prefixes)}_processor_{secrets.token_hex(4)}"

    @staticmethod
    def make_processor_type() -> str:
        """Generate random processor type"""
        types = ["webhook", "queue", "stream", "database", "analytics"]
        return random.choice(types)

    @staticmethod
    def make_subscriber_name() -> str:
        """Generate random subscriber name"""
        services = ["notification_service", "analytics_service", "audit_service", "sync_service"]
        return f"{random.choice(services)}_{secrets.token_hex(4)}"

    @staticmethod
    def make_subscriber_type() -> str:
        """Generate random subscriber type"""
        types = ["service", "webhook", "queue", "stream"]
        return random.choice(types)

    @staticmethod
    def make_entity_type() -> str:
        """Generate random entity type"""
        types = ["user", "device", "order", "album", "media", "organization"]
        return random.choice(types)

    @staticmethod
    def make_projection_name() -> str:
        """Generate random projection name"""
        names = ["default", "summary", "detailed", "aggregate", "timeline"]
        return random.choice(names)

    @staticmethod
    def make_stream_type() -> str:
        """Generate random stream type"""
        types = ["user_activity", "device_events", "order_history", "audit_trail"]
        return random.choice(types)

    @staticmethod
    def make_callback_url() -> str:
        """Generate random callback URL"""
        services = ["notification", "analytics", "audit", "webhook"]
        return f"https://{random.choice(services)}.example.com/events/{secrets.token_hex(4)}"

    @staticmethod
    def make_webhook_secret() -> str:
        """Generate webhook secret"""
        return f"whsec_{secrets.token_hex(16)}"

    @staticmethod
    def make_error_message() -> str:
        """Generate random error message"""
        errors = [
            "Connection timeout",
            "Invalid payload format",
            "Rate limit exceeded",
            "Service unavailable",
            "Authentication failed",
        ]
        return random.choice(errors)

    # ========================================================================
    # Timestamp Generators
    # ========================================================================

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current UTC timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days))

    @staticmethod
    def make_future_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(days=random.randint(1, days))

    @staticmethod
    def make_timestamp_iso() -> str:
        """Generate ISO format timestamp string"""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def make_time_range(days: int = 30) -> Tuple[datetime, datetime]:
        """Generate start and end time range"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        return (start, end)

    # ========================================================================
    # Numeric Generators
    # ========================================================================

    @staticmethod
    def make_positive_int(max_val: int = 1000) -> int:
        """Generate positive integer"""
        return random.randint(1, max_val)

    @staticmethod
    def make_percentage() -> float:
        """Generate percentage (0-100)"""
        return round(random.uniform(0, 100), 2)

    @staticmethod
    def make_priority() -> int:
        """Generate priority (0-100)"""
        return random.randint(0, 100)

    @staticmethod
    def make_retry_count() -> int:
        """Generate retry count"""
        return random.randint(0, 5)

    @staticmethod
    def make_duration_ms() -> int:
        """Generate duration in milliseconds"""
        return random.randint(1, 5000)

    @staticmethod
    def make_version_number() -> int:
        """Generate version number"""
        return random.randint(0, 100)

    # ========================================================================
    # Data/Metadata Generators
    # ========================================================================

    @staticmethod
    def make_event_data() -> Dict[str, Any]:
        """Generate random event data dictionary"""
        return {
            "action": random.choice(["create", "update", "delete", "view"]),
            "source": random.choice(["api", "ui", "internal"]),
            "trace_id": EventTestDataFactory.make_correlation_id(),
            "timestamp": EventTestDataFactory.make_timestamp_iso(),
        }

    @staticmethod
    def make_event_metadata() -> Dict[str, Any]:
        """Generate random event metadata"""
        return {
            "version": f"1.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "source": random.choice(["api", "nats", "grpc"]),
            "client_ip": EventTestDataFactory.make_ip_address(),
            "user_agent": EventTestDataFactory.make_user_agent(),
        }

    @staticmethod
    def make_event_context() -> Dict[str, Any]:
        """Generate random event context"""
        return {
            "request_id": EventTestDataFactory.make_correlation_id(),
            "session_id": EventTestDataFactory.make_session_id(),
            "client_version": f"2.{random.randint(0, 9)}.{random.randint(0, 9)}",
        }

    @staticmethod
    def make_event_properties() -> Dict[str, Any]:
        """Generate random event properties"""
        return {
            "priority": random.choice(["low", "normal", "high"]),
            "tags": EventTestDataFactory.make_tags(),
            "category": EventTestDataFactory.make_event_category().value,
        }

    @staticmethod
    def make_processor_filters() -> Dict[str, Any]:
        """Generate processor filters"""
        return {
            "event_types": [EventTestDataFactory.make_event_type() for _ in range(2)],
            "event_sources": [EventTestDataFactory.make_event_source().value],
        }

    @staticmethod
    def make_processor_config() -> Dict[str, Any]:
        """Generate processor configuration"""
        return {
            "webhook_url": EventTestDataFactory.make_callback_url(),
            "timeout_ms": random.randint(1000, 30000),
            "retry_count": random.randint(1, 5),
        }

    @staticmethod
    def make_retry_policy() -> Dict[str, Any]:
        """Generate retry policy"""
        return {
            "max_retries": random.randint(1, 5),
            "initial_delay_ms": random.randint(100, 1000),
            "max_delay_ms": random.randint(5000, 30000),
            "backoff_multiplier": round(random.uniform(1.5, 3.0), 1),
        }

    @staticmethod
    def make_projection_state() -> Dict[str, Any]:
        """Generate projection state"""
        return {
            "count": random.randint(1, 1000),
            "last_update": EventTestDataFactory.make_timestamp_iso(),
            "status": random.choice(["active", "inactive", "pending"]),
        }

    @staticmethod
    def make_tags(count: int = 3) -> List[str]:
        """Generate random tags"""
        all_tags = ["critical", "urgent", "normal", "internal", "external", "automated", "manual"]
        return random.sample(all_tags, min(count, len(all_tags)))

    @staticmethod
    def make_ip_address() -> str:
        """Generate random IPv4 address"""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    @staticmethod
    def make_user_agent() -> str:
        """Generate random user agent string"""
        browsers = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile/15E148",
        ]
        return random.choice(browsers)

    @staticmethod
    def make_version() -> str:
        """Generate version string"""
        return f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"

    # ========================================================================
    # Model Instance Generators
    # ========================================================================

    @staticmethod
    def create_event(**overrides) -> Event:
        """
        Create Event instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            Event instance with valid data
        """
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "event_id": EventTestDataFactory.make_event_id(),
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": EventTestDataFactory.make_event_source(),
            "event_category": EventTestDataFactory.make_event_category(),
            "user_id": EventTestDataFactory.make_user_id(),
            "session_id": EventTestDataFactory.make_session_id(),
            "organization_id": EventTestDataFactory.make_organization_id(),
            "device_id": EventTestDataFactory.make_device_id(),
            "correlation_id": EventTestDataFactory.make_correlation_id(),
            "data": EventTestDataFactory.make_event_data(),
            "metadata": EventTestDataFactory.make_event_metadata(),
            "context": EventTestDataFactory.make_event_context(),
            "properties": EventTestDataFactory.make_event_properties(),
            "status": EventStatus.PENDING,
            "processed_at": None,
            "processors": [],
            "error_message": None,
            "retry_count": 0,
            "timestamp": now,
            "created_at": now,
            "updated_at": now,
            "version": "1.0.0",
            "schema_version": "1.0.0",
        }
        defaults.update(overrides)
        return Event(**defaults)

    @staticmethod
    def create_event_stream(**overrides) -> EventStream:
        """
        Create EventStream instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            EventStream instance with valid data
        """
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "stream_id": EventTestDataFactory.make_stream_id(),
            "stream_type": EventTestDataFactory.make_stream_type(),
            "entity_id": EventTestDataFactory.make_user_id(),
            "entity_type": EventTestDataFactory.make_entity_type(),
            "events": [],
            "version": 0,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return EventStream(**defaults)

    @staticmethod
    def create_event_processor(**overrides) -> EventProcessor:
        """
        Create EventProcessor instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            EventProcessor instance with valid data
        """
        defaults = {
            "processor_id": EventTestDataFactory.make_processor_id(),
            "processor_name": EventTestDataFactory.make_processor_name(),
            "processor_type": EventTestDataFactory.make_processor_type(),
            "enabled": True,
            "priority": EventTestDataFactory.make_priority(),
            "filters": EventTestDataFactory.make_processor_filters(),
            "config": EventTestDataFactory.make_processor_config(),
            "error_count": 0,
            "last_error": None,
            "last_processed_at": None,
        }
        defaults.update(overrides)
        return EventProcessor(**defaults)

    @staticmethod
    def create_event_subscription(**overrides) -> EventSubscription:
        """
        Create EventSubscription instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            EventSubscription instance with valid data
        """
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "subscription_id": EventTestDataFactory.make_subscription_id(),
            "subscriber_name": EventTestDataFactory.make_subscriber_name(),
            "subscriber_type": EventTestDataFactory.make_subscriber_type(),
            "event_types": [EventTestDataFactory.make_event_type() for _ in range(3)],
            "event_sources": [EventTestDataFactory.make_event_source()],
            "event_categories": [EventTestDataFactory.make_event_category()],
            "callback_url": EventTestDataFactory.make_callback_url(),
            "webhook_secret": EventTestDataFactory.make_webhook_secret(),
            "enabled": True,
            "retry_policy": EventTestDataFactory.make_retry_policy(),
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return EventSubscription(**defaults)

    @staticmethod
    def create_event_projection(**overrides) -> EventProjection:
        """
        Create EventProjection instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            EventProjection instance with valid data
        """
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "projection_id": EventTestDataFactory.make_projection_id(),
            "projection_name": EventTestDataFactory.make_projection_name(),
            "entity_id": EventTestDataFactory.make_user_id(),
            "entity_type": EventTestDataFactory.make_entity_type(),
            "state": EventTestDataFactory.make_projection_state(),
            "version": EventTestDataFactory.make_version_number(),
            "last_event_id": EventTestDataFactory.make_event_id(),
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return EventProjection(**defaults)

    @staticmethod
    def create_processing_result(**overrides) -> EventProcessingResult:
        """
        Create EventProcessingResult instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            EventProcessingResult instance with valid data
        """
        defaults = {
            "event_id": EventTestDataFactory.make_event_id(),
            "processor_name": EventTestDataFactory.make_processor_name(),
            "status": ProcessingStatus.SUCCESS,
            "message": "Processing completed successfully",
            "processed_at": EventTestDataFactory.make_timestamp(),
            "duration_ms": EventTestDataFactory.make_duration_ms(),
        }
        defaults.update(overrides)
        return EventProcessingResult(**defaults)

    @staticmethod
    def create_event_create_request(**overrides) -> EventCreateRequest:
        """
        Create EventCreateRequest instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            EventCreateRequest instance with valid data
        """
        defaults = {
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": EventTestDataFactory.make_event_source(),
            "event_category": EventTestDataFactory.make_event_category(),
            "user_id": EventTestDataFactory.make_user_id(),
            "data": EventTestDataFactory.make_event_data(),
            "metadata": EventTestDataFactory.make_event_metadata(),
            "context": EventTestDataFactory.make_event_context(),
        }
        defaults.update(overrides)
        return EventCreateRequest(**defaults)

    @staticmethod
    def create_event_query_request(**overrides) -> EventQueryRequest:
        """
        Create EventQueryRequest instance with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            EventQueryRequest instance with valid data
        """
        start, end = EventTestDataFactory.make_time_range(30)
        defaults = {
            "user_id": EventTestDataFactory.make_user_id(),
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": EventTestDataFactory.make_event_source(),
            "event_category": EventTestDataFactory.make_event_category(),
            "status": EventStatus.PROCESSED,
            "start_time": start,
            "end_time": end,
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return EventQueryRequest(**defaults)

    # ========================================================================
    # Request Contract Generators
    # ========================================================================

    @staticmethod
    def make_event_create_request_contract(**overrides) -> EventCreateRequestContract:
        """Generate valid event creation request contract"""
        defaults = {
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": EventTestDataFactory.make_event_source(),
            "event_category": EventTestDataFactory.make_event_category(),
            "user_id": EventTestDataFactory.make_user_id(),
            "data": EventTestDataFactory.make_event_data(),
            "metadata": EventTestDataFactory.make_event_metadata(),
            "context": EventTestDataFactory.make_event_context(),
        }
        defaults.update(overrides)
        return EventCreateRequestContract(**defaults)

    @staticmethod
    def make_event_query_request_contract(**overrides) -> EventQueryRequestContract:
        """Generate valid event query request contract"""
        start, end = EventTestDataFactory.make_time_range(30)
        defaults = {
            "user_id": EventTestDataFactory.make_user_id(),
            "event_type": EventTestDataFactory.make_event_type(),
            "start_time": start,
            "end_time": end,
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return EventQueryRequestContract(**defaults)

    @staticmethod
    def make_event_batch_create_request_contract(count: int = 5) -> EventBatchCreateRequestContract:
        """Generate valid batch event creation request contract"""
        events = [
            EventTestDataFactory.make_event_create_request_contract()
            for _ in range(count)
        ]
        return EventBatchCreateRequestContract(events=events)

    @staticmethod
    def make_event_replay_request_contract(**overrides) -> EventReplayRequestContract:
        """Generate valid event replay request contract"""
        start, end = EventTestDataFactory.make_time_range(7)
        defaults = {
            "stream_id": EventTestDataFactory.make_stream_id(),
            "start_time": start,
            "end_time": end,
            "target_service": "notification_service",
            "dry_run": False,
        }
        defaults.update(overrides)
        return EventReplayRequestContract(**defaults)

    @staticmethod
    def make_processor_create_request_contract(**overrides) -> EventProcessorCreateRequestContract:
        """Generate valid processor creation request contract"""
        defaults = {
            "processor_name": EventTestDataFactory.make_processor_name(),
            "processor_type": EventTestDataFactory.make_processor_type(),
            "enabled": True,
            "priority": EventTestDataFactory.make_priority(),
            "filters": EventTestDataFactory.make_processor_filters(),
            "config": EventTestDataFactory.make_processor_config(),
        }
        defaults.update(overrides)
        return EventProcessorCreateRequestContract(**defaults)

    @staticmethod
    def make_subscription_create_request_contract(**overrides) -> EventSubscriptionCreateRequestContract:
        """Generate valid subscription creation request contract"""
        defaults = {
            "subscriber_name": EventTestDataFactory.make_subscriber_name(),
            "subscriber_type": EventTestDataFactory.make_subscriber_type(),
            "event_types": [EventTestDataFactory.make_event_type() for _ in range(3)],
            "event_sources": [EventTestDataFactory.make_event_source()],
            "event_categories": [EventTestDataFactory.make_event_category()],
            "callback_url": EventTestDataFactory.make_callback_url(),
            "webhook_secret": EventTestDataFactory.make_webhook_secret(),
            "enabled": True,
            "retry_policy": EventTestDataFactory.make_retry_policy(),
        }
        defaults.update(overrides)
        return EventSubscriptionCreateRequestContract(**defaults)

    @staticmethod
    def make_projection_query_request_contract(**overrides) -> EventProjectionQueryRequestContract:
        """Generate valid projection query request contract"""
        defaults = {
            "entity_type": EventTestDataFactory.make_entity_type(),
            "entity_id": EventTestDataFactory.make_user_id(),
            "projection_name": EventTestDataFactory.make_projection_name(),
        }
        defaults.update(overrides)
        return EventProjectionQueryRequestContract(**defaults)

    # ========================================================================
    # Response Generators
    # ========================================================================

    @staticmethod
    def make_event_response(**overrides) -> Dict[str, Any]:
        """Generate event response data"""
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "event_id": EventTestDataFactory.make_event_id(),
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": EventTestDataFactory.make_event_source().value,
            "event_category": EventTestDataFactory.make_event_category().value,
            "user_id": EventTestDataFactory.make_user_id(),
            "data": EventTestDataFactory.make_event_data(),
            "status": EventStatus.PROCESSED.value,
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_event_list_response(count: int = 5) -> Dict[str, Any]:
        """Generate event list response data"""
        events = [
            EventTestDataFactory.make_event_response()
            for _ in range(count)
        ]
        return {
            "events": events,
            "total": count,
            "limit": 100,
            "offset": 0,
            "has_more": False,
        }

    @staticmethod
    def make_event_statistics_response(**overrides) -> Dict[str, Any]:
        """Generate event statistics response data"""
        total = random.randint(10000, 500000)
        pending = random.randint(100, 1000)
        failed = random.randint(10, 100)
        processed = total - pending - failed
        defaults = {
            "total_events": total,
            "pending_events": pending,
            "processed_events": processed,
            "failed_events": failed,
            "events_by_source": {
                "backend": int(total * 0.6),
                "frontend": int(total * 0.3),
                "system": int(total * 0.1),
            },
            "events_by_category": {
                "user_lifecycle": int(total * 0.4),
                "user_action": int(total * 0.3),
                "system": int(total * 0.3),
            },
            "events_by_type": {
                "user.logged_in": random.randint(1000, 10000),
                "user.created": random.randint(500, 5000),
            },
            "events_today": random.randint(1000, 10000),
            "events_this_week": random.randint(10000, 50000),
            "events_this_month": random.randint(50000, 200000),
            "average_processing_time": round(random.uniform(0.01, 0.5), 3),
            "processing_rate": round((processed / total) * 100, 2),
            "error_rate": round((failed / total) * 100, 2),
            "top_users": [
                {"user_id": EventTestDataFactory.make_user_id(), "count": random.randint(100, 1000)}
                for _ in range(5)
            ],
            "top_event_types": [
                {"event_type": EventTestDataFactory.make_event_type(), "count": random.randint(1000, 10000)}
                for _ in range(5)
            ],
            "calculated_at": EventTestDataFactory.make_timestamp().isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_processing_result_response(**overrides) -> Dict[str, Any]:
        """Generate processing result response data"""
        defaults = {
            "event_id": EventTestDataFactory.make_event_id(),
            "processor_name": EventTestDataFactory.make_processor_name(),
            "status": ProcessingStatus.SUCCESS.value,
            "message": "Processing completed successfully",
            "processed_at": EventTestDataFactory.make_timestamp().isoformat(),
            "duration_ms": EventTestDataFactory.make_duration_ms(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_event_stream_response(**overrides) -> Dict[str, Any]:
        """Generate event stream response data"""
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "stream_id": EventTestDataFactory.make_stream_id(),
            "stream_type": EventTestDataFactory.make_stream_type(),
            "entity_id": EventTestDataFactory.make_user_id(),
            "entity_type": EventTestDataFactory.make_entity_type(),
            "events": [],
            "version": EventTestDataFactory.make_version_number(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_event_projection_response(**overrides) -> Dict[str, Any]:
        """Generate event projection response data"""
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "projection_id": EventTestDataFactory.make_projection_id(),
            "projection_name": EventTestDataFactory.make_projection_name(),
            "entity_id": EventTestDataFactory.make_user_id(),
            "entity_type": EventTestDataFactory.make_entity_type(),
            "state": EventTestDataFactory.make_projection_state(),
            "version": EventTestDataFactory.make_version_number(),
            "last_event_id": EventTestDataFactory.make_event_id(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_processor_response(**overrides) -> Dict[str, Any]:
        """Generate processor response data"""
        defaults = {
            "processor_id": EventTestDataFactory.make_processor_id(),
            "processor_name": EventTestDataFactory.make_processor_name(),
            "processor_type": EventTestDataFactory.make_processor_type(),
            "enabled": True,
            "priority": EventTestDataFactory.make_priority(),
            "filters": EventTestDataFactory.make_processor_filters(),
            "config": EventTestDataFactory.make_processor_config(),
            "error_count": 0,
            "last_error": None,
            "last_processed_at": EventTestDataFactory.make_timestamp().isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_subscription_response(**overrides) -> Dict[str, Any]:
        """Generate subscription response data"""
        now = EventTestDataFactory.make_timestamp()
        defaults = {
            "subscription_id": EventTestDataFactory.make_subscription_id(),
            "subscriber_name": EventTestDataFactory.make_subscriber_name(),
            "subscriber_type": EventTestDataFactory.make_subscriber_type(),
            "event_types": [EventTestDataFactory.make_event_type() for _ in range(3)],
            "event_sources": [EventTestDataFactory.make_event_source().value],
            "event_categories": [EventTestDataFactory.make_event_category().value],
            "callback_url": EventTestDataFactory.make_callback_url(),
            "enabled": True,
            "retry_policy": EventTestDataFactory.make_retry_policy(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_service_health_response(**overrides) -> Dict[str, Any]:
        """Generate service health response data"""
        defaults = {
            "service": "event_service",
            "status": "healthy",
            "port": 8211,
            "version": "1.0.0",
            "database_connected": True,
            "timestamp": EventTestDataFactory.make_timestamp().isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_batch_create_response(total: int = 5, failed: int = 0) -> Dict[str, Any]:
        """Generate batch event creation response data"""
        return {
            "successful_count": total - failed,
            "failed_count": failed,
            "results": [
                {"event_id": EventTestDataFactory.make_event_id(), "success": True}
                for _ in range(total - failed)
            ],
        }

    @staticmethod
    def make_replay_response(**overrides) -> Dict[str, Any]:
        """Generate event replay response data"""
        defaults = {
            "replayed_count": random.randint(5, 20),
            "failed_count": 0,
            "dry_run": False,
            "target_service": "notification_service",
            "results": [],
        }
        defaults.update(overrides)
        return defaults

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_event_create_missing_type() -> dict:
        """Generate event create request missing event_type"""
        return {
            "event_source": EventSource.BACKEND.value,
            "event_category": EventCategory.USER_ACTION.value,
            # Missing event_type
        }

    @staticmethod
    def make_invalid_event_create_empty_type() -> dict:
        """Generate event create request with empty event_type"""
        return {
            "event_type": "",
            "event_source": EventSource.BACKEND.value,
            "event_category": EventCategory.USER_ACTION.value,
        }

    @staticmethod
    def make_invalid_event_create_whitespace_type() -> dict:
        """Generate event create request with whitespace-only event_type"""
        return {
            "event_type": "   ",
            "event_source": EventSource.BACKEND.value,
            "event_category": EventCategory.USER_ACTION.value,
        }

    @staticmethod
    def make_invalid_event_create_invalid_source() -> dict:
        """Generate event create request with invalid event_source"""
        return {
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": "invalid_source",
            "event_category": EventCategory.USER_ACTION.value,
        }

    @staticmethod
    def make_invalid_event_create_invalid_category() -> dict:
        """Generate event create request with invalid event_category"""
        return {
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": EventSource.BACKEND.value,
            "event_category": "invalid_category",
        }

    @staticmethod
    def make_invalid_query_limit_zero() -> dict:
        """Generate query with zero limit"""
        return {"limit": 0, "offset": 0}

    @staticmethod
    def make_invalid_query_limit_negative() -> dict:
        """Generate query with negative limit"""
        return {"limit": -1, "offset": 0}

    @staticmethod
    def make_invalid_query_limit_too_large() -> dict:
        """Generate query with limit exceeding max"""
        return {"limit": 1001, "offset": 0}

    @staticmethod
    def make_invalid_query_offset_negative() -> dict:
        """Generate query with negative offset"""
        return {"limit": 100, "offset": -1}

    @staticmethod
    def make_invalid_query_time_range_reversed() -> dict:
        """Generate query with reversed time range"""
        now = datetime.now(timezone.utc)
        return {
            "start_time": now.isoformat(),
            "end_time": (now - timedelta(days=30)).isoformat(),
        }

    @staticmethod
    def make_invalid_batch_empty() -> dict:
        """Generate empty batch request"""
        return {"events": []}

    @staticmethod
    def make_invalid_batch_too_large() -> dict:
        """Generate batch request exceeding limit"""
        return {
            "events": [
                {
                    "event_type": f"event.type_{i}",
                    "event_source": EventSource.BACKEND.value,
                    "event_category": EventCategory.USER_ACTION.value,
                }
                for i in range(101)  # Exceeds 100 limit
            ]
        }

    @staticmethod
    def make_invalid_processor_create_empty_name() -> dict:
        """Generate processor create request with empty name"""
        return {
            "processor_name": "",
            "processor_type": EventTestDataFactory.make_processor_type(),
        }

    @staticmethod
    def make_invalid_processor_create_invalid_priority() -> dict:
        """Generate processor create request with invalid priority"""
        return {
            "processor_name": EventTestDataFactory.make_processor_name(),
            "processor_type": EventTestDataFactory.make_processor_type(),
            "priority": 150,  # Max is 100
        }

    @staticmethod
    def make_invalid_subscription_create_empty_name() -> dict:
        """Generate subscription create request with empty name"""
        return {
            "subscriber_name": "",
            "event_types": [EventTestDataFactory.make_event_type()],
        }

    @staticmethod
    def make_invalid_subscription_create_empty_event_types() -> dict:
        """Generate subscription create request with empty event_types"""
        return {
            "subscriber_name": EventTestDataFactory.make_subscriber_name(),
            "event_types": [],
        }

    # ========================================================================
    # Edge Case Generators
    # ========================================================================

    @staticmethod
    def make_unicode_event_type() -> str:
        """Generate event type with unicode characters"""
        return f"user.action_\u4e2d\u6587_{secrets.token_hex(4)}"

    @staticmethod
    def make_special_chars_event_type() -> str:
        """Generate event type with special characters (but valid)"""
        return f"user.action-{secrets.token_hex(4)}"

    @staticmethod
    def make_max_length_event_type() -> str:
        """Generate event type at max length (255 chars)"""
        return "x" * 255

    @staticmethod
    def make_min_length_event_type() -> str:
        """Generate event type at min length (1 char)"""
        return "x"

    @staticmethod
    def make_large_event_data() -> Dict[str, Any]:
        """Generate large event data payload"""
        return {
            f"field_{i}": secrets.token_hex(100)
            for i in range(100)
        }

    @staticmethod
    def make_deeply_nested_event_data(depth: int = 10) -> Dict[str, Any]:
        """Generate deeply nested event data"""
        result: Dict[str, Any] = {"value": "leaf"}
        for i in range(depth):
            result = {f"level_{i}": result}
        return result

    # ========================================================================
    # Batch Generators
    # ========================================================================

    @staticmethod
    def make_batch_event_ids(count: int = 5) -> List[str]:
        """Generate multiple event IDs"""
        return [EventTestDataFactory.make_event_id() for _ in range(count)]

    @staticmethod
    def make_batch_user_ids(count: int = 5) -> List[str]:
        """Generate multiple user IDs"""
        return [EventTestDataFactory.make_user_id() for _ in range(count)]

    @staticmethod
    def make_batch_events(count: int = 5, **overrides) -> List[Event]:
        """Generate multiple Event instances"""
        return [EventTestDataFactory.create_event(**overrides) for _ in range(count)]

    @staticmethod
    def make_batch_create_requests(count: int = 5) -> List[EventCreateRequestContract]:
        """Generate multiple event create request contracts"""
        return [EventTestDataFactory.make_event_create_request_contract() for _ in range(count)]


# ============================================================================
# Request Builders
# ============================================================================

class EventCreateRequestBuilder:
    """Builder pattern for creating event creation requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._data = {
            "event_type": EventTestDataFactory.make_event_type(),
            "event_source": EventSource.BACKEND,
            "event_category": EventCategory.USER_ACTION,
            "data": {},
            "metadata": {},
        }

    def with_event_type(self, event_type: str) -> "EventCreateRequestBuilder":
        """Set event type"""
        self._data["event_type"] = event_type
        return self

    def with_event_source(self, source: EventSource) -> "EventCreateRequestBuilder":
        """Set event source"""
        self._data["event_source"] = source
        return self

    def with_event_category(self, category: EventCategory) -> "EventCreateRequestBuilder":
        """Set event category"""
        self._data["event_category"] = category
        return self

    def with_user_id(self, user_id: str) -> "EventCreateRequestBuilder":
        """Set user ID"""
        self._data["user_id"] = user_id
        return self

    def with_data(self, data: Dict[str, Any]) -> "EventCreateRequestBuilder":
        """Set event data"""
        self._data["data"] = data
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "EventCreateRequestBuilder":
        """Set event metadata"""
        self._data["metadata"] = metadata
        return self

    def with_context(self, context: Dict[str, Any]) -> "EventCreateRequestBuilder":
        """Set event context"""
        self._data["context"] = context
        return self

    def with_user_event(self, action: str) -> "EventCreateRequestBuilder":
        """Configure as user event"""
        self._data["event_type"] = f"user.{action}"
        self._data["event_source"] = EventSource.BACKEND
        self._data["event_category"] = EventCategory.USER_LIFECYCLE
        return self

    def with_device_event(self, action: str) -> "EventCreateRequestBuilder":
        """Configure as device event"""
        self._data["event_type"] = f"device.{action}"
        self._data["event_source"] = EventSource.IOT_DEVICE
        self._data["event_category"] = EventCategory.DEVICE_STATUS
        return self

    def with_invalid_type(self) -> "EventCreateRequestBuilder":
        """Set invalid empty type for negative testing"""
        self._data["event_type"] = ""
        return self

    def build(self) -> EventCreateRequestContract:
        """Build the request contract"""
        return EventCreateRequestContract(**self._data)

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


class EventQueryRequestBuilder:
    """Builder pattern for creating event query requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._data = {
            "limit": 100,
            "offset": 0,
        }

    def with_user_id(self, user_id: str) -> "EventQueryRequestBuilder":
        """Set user ID filter"""
        self._data["user_id"] = user_id
        return self

    def with_event_type(self, event_type: str) -> "EventQueryRequestBuilder":
        """Set event type filter"""
        self._data["event_type"] = event_type
        return self

    def with_event_source(self, source: EventSource) -> "EventQueryRequestBuilder":
        """Set event source filter"""
        self._data["event_source"] = source
        return self

    def with_event_category(self, category: EventCategory) -> "EventQueryRequestBuilder":
        """Set event category filter"""
        self._data["event_category"] = category
        return self

    def with_status(self, status: EventStatus) -> "EventQueryRequestBuilder":
        """Set status filter"""
        self._data["status"] = status
        return self

    def with_time_range(self, start: datetime, end: datetime) -> "EventQueryRequestBuilder":
        """Set time range filter"""
        self._data["start_time"] = start
        self._data["end_time"] = end
        return self

    def with_time_range_days(self, days: int) -> "EventQueryRequestBuilder":
        """Set time range by days from now"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        self._data["start_time"] = start
        self._data["end_time"] = end
        return self

    def with_pagination(self, limit: int, offset: int) -> "EventQueryRequestBuilder":
        """Set pagination"""
        self._data["limit"] = limit
        self._data["offset"] = offset
        return self

    def with_invalid_limit(self) -> "EventQueryRequestBuilder":
        """Set invalid limit for negative testing"""
        self._data["limit"] = 10000
        return self

    def build(self) -> EventQueryRequestContract:
        """Build the request contract"""
        return EventQueryRequestContract(**self._data)

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


class EventProcessorCreateRequestBuilder:
    """Builder pattern for creating event processor requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._data = {
            "processor_name": EventTestDataFactory.make_processor_name(),
            "processor_type": EventTestDataFactory.make_processor_type(),
            "enabled": True,
            "priority": 0,
            "filters": {},
            "config": {},
        }

    def with_name(self, name: str) -> "EventProcessorCreateRequestBuilder":
        """Set processor name"""
        self._data["processor_name"] = name
        return self

    def with_type(self, processor_type: str) -> "EventProcessorCreateRequestBuilder":
        """Set processor type"""
        self._data["processor_type"] = processor_type
        return self

    def with_enabled(self, enabled: bool) -> "EventProcessorCreateRequestBuilder":
        """Set enabled status"""
        self._data["enabled"] = enabled
        return self

    def with_priority(self, priority: int) -> "EventProcessorCreateRequestBuilder":
        """Set priority"""
        self._data["priority"] = priority
        return self

    def with_filters(self, filters: Dict[str, Any]) -> "EventProcessorCreateRequestBuilder":
        """Set filters"""
        self._data["filters"] = filters
        return self

    def with_config(self, config: Dict[str, Any]) -> "EventProcessorCreateRequestBuilder":
        """Set configuration"""
        self._data["config"] = config
        return self

    def with_webhook(self, url: str) -> "EventProcessorCreateRequestBuilder":
        """Configure as webhook processor"""
        self._data["processor_type"] = "webhook"
        self._data["config"] = {"webhook_url": url}
        return self

    def with_event_type_filter(self, event_types: List[str]) -> "EventProcessorCreateRequestBuilder":
        """Add event type filter"""
        self._data["filters"]["event_types"] = event_types
        return self

    def build(self) -> EventProcessorCreateRequestContract:
        """Build the request contract"""
        return EventProcessorCreateRequestContract(**self._data)

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


class EventSubscriptionCreateRequestBuilder:
    """Builder pattern for creating event subscription requests"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._data = {
            "subscriber_name": EventTestDataFactory.make_subscriber_name(),
            "subscriber_type": "service",
            "event_types": [EventTestDataFactory.make_event_type()],
            "enabled": True,
            "retry_policy": {},
        }

    def with_name(self, name: str) -> "EventSubscriptionCreateRequestBuilder":
        """Set subscriber name"""
        self._data["subscriber_name"] = name
        return self

    def with_type(self, subscriber_type: str) -> "EventSubscriptionCreateRequestBuilder":
        """Set subscriber type"""
        self._data["subscriber_type"] = subscriber_type
        return self

    def with_event_types(self, event_types: List[str]) -> "EventSubscriptionCreateRequestBuilder":
        """Set event types"""
        self._data["event_types"] = event_types
        return self

    def with_event_sources(self, sources: List[EventSource]) -> "EventSubscriptionCreateRequestBuilder":
        """Set event source filters"""
        self._data["event_sources"] = sources
        return self

    def with_event_categories(self, categories: List[EventCategory]) -> "EventSubscriptionCreateRequestBuilder":
        """Set event category filters"""
        self._data["event_categories"] = categories
        return self

    def with_callback_url(self, url: str) -> "EventSubscriptionCreateRequestBuilder":
        """Set callback URL"""
        self._data["callback_url"] = url
        return self

    def with_webhook_secret(self, secret: str) -> "EventSubscriptionCreateRequestBuilder":
        """Set webhook secret"""
        self._data["webhook_secret"] = secret
        return self

    def with_enabled(self, enabled: bool) -> "EventSubscriptionCreateRequestBuilder":
        """Set enabled status"""
        self._data["enabled"] = enabled
        return self

    def with_retry_policy(self, policy: Dict[str, Any]) -> "EventSubscriptionCreateRequestBuilder":
        """Set retry policy"""
        self._data["retry_policy"] = policy
        return self

    def build(self) -> EventSubscriptionCreateRequestContract:
        """Build the request contract"""
        return EventSubscriptionCreateRequestContract(**self._data)

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


# ============================================================================
# JSON Schema Exports
# ============================================================================

def get_event_create_request_json_schema() -> Dict[str, Any]:
    """Get JSON schema for EventCreateRequestContract"""
    return EventCreateRequestContract.model_json_schema()


def get_event_query_request_json_schema() -> Dict[str, Any]:
    """Get JSON schema for EventQueryRequestContract"""
    return EventQueryRequestContract.model_json_schema()


def get_event_response_json_schema() -> Dict[str, Any]:
    """Get JSON schema for EventResponseContract"""
    return EventResponseContract.model_json_schema()


def get_event_list_response_json_schema() -> Dict[str, Any]:
    """Get JSON schema for EventListResponseContract"""
    return EventListResponseContract.model_json_schema()


def get_event_statistics_response_json_schema() -> Dict[str, Any]:
    """Get JSON schema for EventStatisticsResponseContract"""
    return EventStatisticsResponseContract.model_json_schema()


def get_all_json_schemas() -> Dict[str, Dict[str, Any]]:
    """Get all JSON schemas for event service contracts"""
    return {
        "EventCreateRequest": get_event_create_request_json_schema(),
        "EventQueryRequest": get_event_query_request_json_schema(),
        "EventResponse": get_event_response_json_schema(),
        "EventListResponse": get_event_list_response_json_schema(),
        "EventStatisticsResponse": get_event_statistics_response_json_schema(),
        "EventBatchCreateRequest": EventBatchCreateRequestContract.model_json_schema(),
        "EventReplayRequest": EventReplayRequestContract.model_json_schema(),
        "EventProcessorCreateRequest": EventProcessorCreateRequestContract.model_json_schema(),
        "EventSubscriptionCreateRequest": EventSubscriptionCreateRequestContract.model_json_schema(),
        "EventProjectionQueryRequest": EventProjectionQueryRequestContract.model_json_schema(),
        "EventDetailResponse": EventDetailResponseContract.model_json_schema(),
        "EventProcessingResultResponse": EventProcessingResultResponseContract.model_json_schema(),
        "EventStreamResponse": EventStreamResponseContract.model_json_schema(),
        "EventProjectionResponse": EventProjectionResponseContract.model_json_schema(),
        "EventProcessorResponse": EventProcessorResponseContract.model_json_schema(),
        "EventSubscriptionResponse": EventSubscriptionResponseContract.model_json_schema(),
        "EventServiceHealthResponse": EventServiceHealthResponseContract.model_json_schema(),
        "EventBatchCreateResponse": EventBatchCreateResponseContract.model_json_schema(),
        "EventReplayResponse": EventReplayResponseContract.model_json_schema(),
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Re-exported Enums from production models
    "EventSource",
    "EventCategory",
    "EventStatus",
    "ProcessingStatus",

    # Re-exported production models
    "Event",
    "EventStream",
    "EventProcessor",
    "EventSubscription",
    "EventProjection",
    "EventProcessingResult",
    "EventCreateRequest",
    "EventQueryRequest",
    "EventResponse",
    "EventListResponse",
    "EventStatistics",
    "EventReplayRequest",
    "RudderStackEvent",

    # Request Contracts
    "EventCreateRequestContract",
    "EventQueryRequestContract",
    "EventBatchCreateRequestContract",
    "EventReplayRequestContract",
    "EventProcessorCreateRequestContract",
    "EventSubscriptionCreateRequestContract",
    "EventProjectionQueryRequestContract",

    # Response Contracts
    "EventResponseContract",
    "EventDetailResponseContract",
    "EventListResponseContract",
    "EventStatisticsResponseContract",
    "EventProcessingResultResponseContract",
    "EventStreamResponseContract",
    "EventProjectionResponseContract",
    "EventProcessorResponseContract",
    "EventSubscriptionResponseContract",
    "EventServiceHealthResponseContract",
    "EventBatchCreateResponseContract",
    "EventReplayResponseContract",

    # Factory
    "EventTestDataFactory",

    # Builders
    "EventCreateRequestBuilder",
    "EventQueryRequestBuilder",
    "EventProcessorCreateRequestBuilder",
    "EventSubscriptionCreateRequestBuilder",

    # JSON Schema exports
    "get_event_create_request_json_schema",
    "get_event_query_request_json_schema",
    "get_event_response_json_schema",
    "get_event_list_response_json_schema",
    "get_event_statistics_response_json_schema",
    "get_all_json_schemas",
]
