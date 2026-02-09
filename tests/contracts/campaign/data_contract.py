"""
Campaign Service Data Contract

Defines all Pydantic models, validation rules, and test data factories
for the Campaign Service.

This is the SINGLE SOURCE OF TRUTH for campaign data structures.
All tests MUST use these models and factories.

Reference:
- Domain: docs/domain/campaign_service.md
- PRD: docs/prd/campaign_service.md
- Design: docs/design/campaign_service.md
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
import hashlib
import random
import string

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# ENUMS
# =============================================================================

class CampaignType(str, Enum):
    """Campaign execution type"""
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"


class CampaignStatus(str, Enum):
    """Campaign lifecycle status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"  # For triggered campaigns that are listening
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ScheduleType(str, Enum):
    """Schedule type for scheduled campaigns"""
    ONE_TIME = "one_time"
    RECURRING = "recurring"


class ChannelType(str, Enum):
    """Delivery channel type"""
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class SegmentType(str, Enum):
    """Audience segment type"""
    INCLUDE = "include"
    EXCLUDE = "exclude"


class TriggerOperator(str, Enum):
    """Trigger condition operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class MessageStatus(str, Enum):
    """Message delivery status"""
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"


class BounceType(str, Enum):
    """Email bounce type"""
    HARD = "hard"  # Permanent failure (invalid address)
    SOFT = "soft"  # Temporary failure (mailbox full, etc.)


class ExecutionType(str, Enum):
    """Campaign execution trigger type"""
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    MANUAL = "manual"


class ExecutionStatus(str, Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    """Campaign metric types"""
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    CONVERTED = "converted"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"


class AttributionModel(str, Enum):
    """Conversion attribution models"""
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"


class AutoWinnerMetric(str, Enum):
    """Metrics for automatic winner selection"""
    OPEN_RATE = "open_rate"
    CLICK_RATE = "click_rate"
    CONVERSION_RATE = "conversion_rate"


class FrequencyWindow(str, Enum):
    """Trigger frequency window"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# =============================================================================
# BASE MODELS
# =============================================================================

class BaseContract(BaseModel):
    """Base model for all contracts"""

    model_config = {
        "from_attributes": True,
        # Note: NOT using use_enum_values here so enum attributes remain as enum objects
        # for proper attribute access (e.g., campaign.status.value works correctly).
        # Serialization to string happens automatically when converting to dict/JSON.
    }


# =============================================================================
# CAMPAIGN MODELS
# =============================================================================

class TriggerCondition(BaseContract):
    """Single trigger condition"""
    field: str = Field(..., description="Event property field")
    operator: TriggerOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")


class CampaignTrigger(BaseContract):
    """Campaign trigger configuration"""
    trigger_id: str = Field(default_factory=lambda: f"trg_{uuid4().hex[:16]}")
    event_type: str = Field(..., description="Event type to trigger on")
    conditions: List[TriggerCondition] = Field(default_factory=list, description="AND conditions")
    delay_minutes: int = Field(default=0, ge=0, description="Delay before sending")
    delay_days: int = Field(default=0, ge=0, le=30, description="Delay in days")
    frequency_limit: int = Field(default=1, ge=1, description="Max triggers per window")
    frequency_window_hours: int = Field(default=24, ge=1, description="Frequency window in hours")
    quiet_hours_start: Optional[int] = Field(None, ge=0, le=23, description="Quiet hours start (0-23)")
    quiet_hours_end: Optional[int] = Field(None, ge=0, le=23, description="Quiet hours end (0-23)")
    quiet_hours_timezone: str = Field(default="user_local", description="Timezone for quiet hours")
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignAudience(BaseContract):
    """Campaign audience segment configuration"""
    audience_id: str = Field(default_factory=lambda: f"aud_{uuid4().hex[:16]}")
    segment_type: SegmentType = Field(..., description="Include or exclude")
    segment_id: Optional[str] = Field(None, description="Reference to isA_Data segment")
    segment_query: Optional[Dict[str, Any]] = Field(None, description="Inline segment query")
    name: Optional[str] = Field(None, max_length=255)
    estimated_size: Optional[int] = Field(None, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_segment_source(self):
        """Either segment_id or segment_query must be provided"""
        if not self.segment_id and not self.segment_query:
            raise ValueError("Either segment_id or segment_query must be provided")
        return self


class EmailChannelContent(BaseContract):
    """Email channel content configuration"""
    subject: str = Field(..., min_length=1, max_length=255)
    body_html: Optional[str] = Field(None, description="HTML email body")
    body_text: Optional[str] = Field(None, description="Plain text email body")
    sender_name: Optional[str] = Field(None, max_length=100)
    sender_email: Optional[str] = Field(None, max_length=255)
    reply_to: Optional[str] = Field(None, max_length=255)


class SMSChannelContent(BaseContract):
    """SMS channel content configuration"""
    body: str = Field(..., min_length=1, max_length=160)


class WhatsAppChannelContent(BaseContract):
    """WhatsApp channel content configuration"""
    body: str = Field(..., min_length=1, max_length=1600)
    template_id: Optional[str] = Field(None, description="WhatsApp template ID")


class InAppChannelContent(BaseContract):
    """In-app notification content configuration"""
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=2000)
    action_url: Optional[str] = Field(None, description="Deep link URL")
    icon: Optional[str] = Field(None, description="Icon URL")


class WebhookChannelContent(BaseContract):
    """Webhook channel content configuration"""
    url: str = Field(..., description="Webhook URL")
    method: str = Field(default="POST", pattern="^(GET|POST|PUT|PATCH)$")
    headers: Dict[str, str] = Field(default_factory=dict)
    payload_template: Optional[str] = Field(None, description="JSON payload template")


class CampaignChannel(BaseContract):
    """Campaign channel configuration"""
    channel_id: str = Field(default_factory=lambda: f"chn_{uuid4().hex[:16]}")
    channel_type: ChannelType
    enabled: bool = Field(default=True)
    priority: int = Field(default=0, description="Fallback order (lower = higher priority)")
    template_id: Optional[str] = Field(None, description="Reference to isA_Creative template")

    # Channel-specific content (only one should be populated based on channel_type)
    email_content: Optional[EmailChannelContent] = None
    sms_content: Optional[SMSChannelContent] = None
    whatsapp_content: Optional[WhatsAppChannelContent] = None
    in_app_content: Optional[InAppChannelContent] = None
    webhook_content: Optional[WebhookChannelContent] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_content(self):
        """Validate that content matches channel type"""
        content_mapping = {
            ChannelType.EMAIL: self.email_content,
            ChannelType.SMS: self.sms_content,
            ChannelType.WHATSAPP: self.whatsapp_content,
            ChannelType.IN_APP: self.in_app_content,
            ChannelType.WEBHOOK: self.webhook_content,
        }
        expected_content = content_mapping.get(self.channel_type)
        if not expected_content and not self.template_id:
            raise ValueError(f"Content required for channel type {self.channel_type} if no template_id")
        return self


class CampaignVariant(BaseContract):
    """A/B test variant configuration"""
    variant_id: str = Field(default_factory=lambda: f"var_{uuid4().hex[:16]}")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    allocation_percentage: Decimal = Field(..., ge=0, le=100, description="Traffic allocation")
    is_control: bool = Field(default=False, description="Control variant (no message sent)")
    channels: List[CampaignChannel] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThrottleConfig(BaseContract):
    """Campaign throttle configuration"""
    per_minute: Optional[int] = Field(None, ge=1, description="Max messages per minute")
    per_hour: Optional[int] = Field(None, ge=1, description="Max messages per hour")
    send_window_start: Optional[int] = Field(None, ge=0, le=23, description="Start hour (0-23)")
    send_window_end: Optional[int] = Field(None, ge=0, le=23, description="End hour (0-23)")
    exclude_weekends: bool = Field(default=False)


class ABTestConfig(BaseContract):
    """A/B testing configuration"""
    enabled: bool = Field(default=False)
    auto_winner_enabled: bool = Field(default=False)
    auto_winner_metric: Optional[AutoWinnerMetric] = None
    auto_winner_confidence: Decimal = Field(default=Decimal("0.95"), ge=0.90, le=0.99)
    auto_winner_min_sample: int = Field(default=1000, ge=100)
    winner_variant_id: Optional[str] = None


class ConversionConfig(BaseContract):
    """Conversion tracking configuration"""
    conversion_event_type: Optional[str] = Field(None, description="Event type to track as conversion")
    attribution_window_days: int = Field(default=7, ge=1, le=30)
    attribution_model: AttributionModel = Field(default=AttributionModel.LAST_TOUCH)


class Campaign(BaseContract):
    """Core Campaign model"""
    campaign_id: str = Field(default_factory=lambda: f"cmp_{uuid4().hex[:16]}")
    organization_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)

    # Type and Status
    campaign_type: CampaignType
    status: CampaignStatus = Field(default=CampaignStatus.DRAFT)

    # Scheduling
    schedule_type: Optional[ScheduleType] = None
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = Field(None, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)

    # Throttling
    throttle: Optional[ThrottleConfig] = None

    # A/B Testing
    ab_test: ABTestConfig = Field(default_factory=ABTestConfig)

    # Conversion Tracking
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)

    # Holdout
    holdout_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=20)

    # Audiences
    audiences: List[CampaignAudience] = Field(default_factory=list)

    # Variants (if not A/B testing, single implicit variant)
    variants: List[CampaignVariant] = Field(default_factory=list)

    # Triggers (for triggered campaigns)
    triggers: List[CampaignTrigger] = Field(default_factory=list)

    # Task Service Integration
    task_id: Optional[str] = None

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Audit
    created_by: str
    updated_by: Optional[str] = None
    paused_by: Optional[str] = None
    paused_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    cloned_from_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v):
        if v and v < datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Scheduled time must be at least 5 minutes in the future")
        return v

    @model_validator(mode="after")
    def validate_campaign_type_requirements(self):
        """Validate requirements based on campaign type"""
        if self.campaign_type == CampaignType.SCHEDULED:
            if self.status in [CampaignStatus.SCHEDULED, CampaignStatus.RUNNING]:
                if not self.schedule_type:
                    raise ValueError("Scheduled campaigns require schedule_type")
                if self.schedule_type == ScheduleType.ONE_TIME and not self.scheduled_at:
                    raise ValueError("One-time campaigns require scheduled_at")
                if self.schedule_type == ScheduleType.RECURRING and not self.cron_expression:
                    raise ValueError("Recurring campaigns require cron_expression")

        if self.campaign_type == CampaignType.TRIGGERED:
            if self.status == CampaignStatus.ACTIVE and not self.triggers:
                raise ValueError("Triggered campaigns require at least one trigger")

        return self

    @model_validator(mode="after")
    def validate_variant_allocation(self):
        """Validate variant allocations sum to 100%"""
        if self.ab_test.enabled and self.variants:
            total = sum(v.allocation_percentage for v in self.variants)
            if total != Decimal("100"):
                raise ValueError(f"Variant allocations must sum to 100%, got {total}%")
        return self


# =============================================================================
# EXECUTION MODELS
# =============================================================================

class CampaignExecution(BaseContract):
    """Campaign execution instance"""
    execution_id: str = Field(default_factory=lambda: f"exe_{uuid4().hex[:16]}")
    campaign_id: str
    execution_type: ExecutionType
    trigger_event_id: Optional[str] = None

    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)

    # Audience
    total_audience_size: int = Field(default=0, ge=0)
    holdout_size: int = Field(default=0, ge=0)

    # Progress
    messages_queued: int = Field(default=0, ge=0)
    messages_sent: int = Field(default=0, ge=0)
    messages_delivered: int = Field(default=0, ge=0)
    messages_failed: int = Field(default=0, ge=0)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignMessage(BaseContract):
    """Individual campaign message"""
    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex[:16]}")
    campaign_id: str
    execution_id: str
    variant_id: Optional[str] = None

    # Recipient
    user_id: str
    channel_type: ChannelType
    recipient_address: Optional[str] = Field(None, description="Email, phone number, etc.")

    # Status
    status: MessageStatus = Field(default=MessageStatus.QUEUED)

    # Tracking
    notification_id: Optional[str] = None
    provider_message_id: Optional[str] = None

    # Timestamps
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    unsubscribed_at: Optional[datetime] = None

    # Error Tracking
    error_message: Optional[str] = None
    bounce_type: Optional[BounceType] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# METRICS MODELS
# =============================================================================

class CampaignMetricRecord(BaseContract):
    """Single metric record"""
    metric_id: str = Field(default_factory=lambda: f"met_{uuid4().hex[:16]}")
    campaign_id: str
    execution_id: Optional[str] = None
    variant_id: Optional[str] = None
    channel_type: Optional[ChannelType] = None
    segment_id: Optional[str] = None

    metric_type: MetricType
    count: int = Field(default=0, ge=0)
    rate: Optional[Decimal] = Field(None, ge=0, le=1)
    value: Optional[Decimal] = None  # For conversion value

    bucket_start: Optional[datetime] = None
    bucket_end: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignMetricsSummary(BaseContract):
    """Aggregated campaign metrics"""
    campaign_id: str
    execution_id: Optional[str] = None

    # Counts
    sent: int = Field(default=0, ge=0)
    delivered: int = Field(default=0, ge=0)
    opened: int = Field(default=0, ge=0)
    clicked: int = Field(default=0, ge=0)
    converted: int = Field(default=0, ge=0)
    bounced: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    unsubscribed: int = Field(default=0, ge=0)

    # Rates
    delivery_rate: Optional[Decimal] = None
    open_rate: Optional[Decimal] = None
    click_rate: Optional[Decimal] = None
    conversion_rate: Optional[Decimal] = None
    bounce_rate: Optional[Decimal] = None
    unsubscribe_rate: Optional[Decimal] = None

    # Conversion Value
    total_conversion_value: Decimal = Field(default=Decimal("0"))

    # Timing
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VariantStatistics(BaseContract):
    """A/B test variant statistics"""
    variant_id: str
    variant_name: str

    # Metrics
    sent: int = Field(default=0)
    delivered: int = Field(default=0)
    opened: int = Field(default=0)
    clicked: int = Field(default=0)
    converted: int = Field(default=0)

    # Rates
    open_rate: Optional[Decimal] = None
    click_rate: Optional[Decimal] = None
    conversion_rate: Optional[Decimal] = None

    # Statistical Analysis
    chi_square_statistic: Optional[Decimal] = None
    p_value: Optional[Decimal] = None
    is_significant: bool = False
    confidence_interval_lower: Optional[Decimal] = None
    confidence_interval_upper: Optional[Decimal] = None


# =============================================================================
# CONVERSION MODELS
# =============================================================================

class CampaignConversion(BaseContract):
    """Conversion attribution record"""
    conversion_id: str = Field(default_factory=lambda: f"cnv_{uuid4().hex[:16]}")
    campaign_id: str
    execution_id: Optional[str] = None
    message_id: Optional[str] = None
    user_id: str

    conversion_event_type: str
    conversion_event_id: Optional[str] = None
    conversion_value: Optional[Decimal] = None

    attribution_model: AttributionModel
    attribution_weight: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)

    converted_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# UNSUBSCRIBE MODELS
# =============================================================================

class CampaignUnsubscribe(BaseContract):
    """Unsubscribe record"""
    unsubscribe_id: str = Field(default_factory=lambda: f"uns_{uuid4().hex[:16]}")
    campaign_id: str
    message_id: Optional[str] = None
    user_id: str
    channel_type: ChannelType

    reason: Optional[str] = Field(None, max_length=255)
    source: str = Field(default="link")  # link, reply, complaint

    unsubscribed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synced_to_account_at: Optional[datetime] = None


# =============================================================================
# TRIGGER HISTORY MODELS
# =============================================================================

class TriggerHistoryRecord(BaseContract):
    """Trigger evaluation history"""
    history_id: str = Field(default_factory=lambda: f"trh_{uuid4().hex[:16]}")
    campaign_id: str
    trigger_id: str

    event_id: str
    event_type: str
    user_id: str

    triggered: bool
    skip_reason: Optional[str] = None  # frequency_limit, quiet_hours, not_in_segment

    execution_id: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_send_at: Optional[datetime] = None


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CampaignCreateRequest(BaseContract):
    """Campaign creation request"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    campaign_type: CampaignType

    # Scheduling (for scheduled campaigns)
    schedule_type: Optional[ScheduleType] = None
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    timezone: str = Field(default="UTC")

    # Throttling
    throttle: Optional[ThrottleConfig] = None

    # Audiences
    audiences: List[CampaignAudience] = Field(default_factory=list)

    # Channels (for non-A/B testing campaigns)
    channels: List[CampaignChannel] = Field(default_factory=list)

    # A/B Testing
    enable_ab_testing: bool = Field(default=False)
    variants: List[CampaignVariant] = Field(default_factory=list)

    # Triggers (for triggered campaigns)
    triggers: List[CampaignTrigger] = Field(default_factory=list)

    # Conversion Tracking
    conversion_event_type: Optional[str] = None
    attribution_window_days: int = Field(default=7)

    # Holdout
    holdout_percentage: Decimal = Field(default=Decimal("0"))

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CampaignUpdateRequest(BaseContract):
    """Campaign update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)

    # Scheduling
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None

    # Throttling
    throttle: Optional[ThrottleConfig] = None

    # Audiences
    audiences: Optional[List[CampaignAudience]] = None

    # Channels
    channels: Optional[List[CampaignChannel]] = None

    # Triggers
    triggers: Optional[List[CampaignTrigger]] = None

    # Metadata
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CampaignResponse(BaseContract):
    """Campaign response"""
    campaign: Campaign
    message: str = "Success"


class CampaignListResponse(BaseContract):
    """Campaign list response"""
    campaigns: List[Campaign]
    total: int
    limit: int
    offset: int
    has_more: bool


class CampaignQueryRequest(BaseContract):
    """Campaign query/filter request"""
    status: Optional[List[CampaignStatus]] = None
    campaign_type: Optional[CampaignType] = None
    channel: Optional[ChannelType] = None
    search: Optional[str] = Field(None, description="Search by name")
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    scheduled_after: Optional[datetime] = None
    scheduled_before: Optional[datetime] = None
    tags: Optional[List[str]] = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CampaignMetricsResponse(BaseContract):
    """Campaign metrics response"""
    campaign_id: str
    metrics: CampaignMetricsSummary
    by_variant: Optional[Dict[str, CampaignMetricsSummary]] = None
    by_channel: Optional[Dict[str, CampaignMetricsSummary]] = None
    by_segment: Optional[Dict[str, CampaignMetricsSummary]] = None
    updated_at: datetime


class AudienceEstimateResponse(BaseContract):
    """Audience estimation response"""
    campaign_id: str
    estimated_size: int
    by_segment: List[Dict[str, Any]]
    after_exclusions: int
    after_holdout: int
    estimated_at: datetime


class ContentPreviewRequest(BaseContract):
    """Content preview request"""
    variant_id: Optional[str] = None
    channel_type: ChannelType
    sample_user_id: Optional[str] = None


class ContentPreviewResponse(BaseContract):
    """Content preview response"""
    campaign_id: str
    variant_id: Optional[str]
    channel_type: ChannelType
    rendered_content: Dict[str, Any]
    sample_user: Dict[str, Any]


# =============================================================================
# TEST DATA FACTORY
# =============================================================================

class CampaignTestDataFactory:
    """Factory for generating test data for campaign service tests

    Usage:
        factory = CampaignTestDataFactory()
        campaign = factory.make_campaign()
        audience = factory.make_audience()
        message = factory.make_message(campaign_id=campaign.campaign_id)
    """

    @staticmethod
    def make_id(prefix: str = "cmp") -> str:
        """Generate a unique ID with prefix"""
        return f"{prefix}_{uuid4().hex[:16]}"

    @staticmethod
    def make_campaign_id() -> str:
        """Generate campaign ID"""
        return f"cmp_{uuid4().hex[:16]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate organization ID"""
        return f"org_{uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate user ID"""
        return f"usr_{uuid4().hex[:16]}"

    @staticmethod
    def make_execution_id() -> str:
        """Generate execution ID"""
        return f"exe_{uuid4().hex[:16]}"

    @staticmethod
    def make_message_id() -> str:
        """Generate message ID"""
        return f"msg_{uuid4().hex[:16]}"

    @staticmethod
    def make_variant_id() -> str:
        """Generate variant ID"""
        return f"var_{uuid4().hex[:16]}"

    @staticmethod
    def make_segment_id() -> str:
        """Generate segment ID"""
        return f"seg_{uuid4().hex[:16]}"

    @staticmethod
    def make_email() -> str:
        """Generate random email"""
        local = "".join(random.choices(string.ascii_lowercase, k=8))
        return f"{local}@example.com"

    @staticmethod
    def make_phone() -> str:
        """Generate random phone number"""
        return f"+1{''.join(random.choices(string.digits, k=10))}"

    @staticmethod
    def make_name() -> str:
        """Generate random campaign name"""
        adjectives = ["New", "Premium", "Special", "Holiday", "Welcome", "Summer", "Winter"]
        nouns = ["Promotion", "Campaign", "Offer", "Sale", "Launch", "Update", "Newsletter"]
        return f"{random.choice(adjectives)} {random.choice(nouns)} {random.randint(1, 100)}"

    @classmethod
    def make_email_content(cls) -> EmailChannelContent:
        """Generate email content"""
        return EmailChannelContent(
            subject="{{first_name}}, check out our special offer!",
            body_html="<html><body><h1>Hello {{first_name}}!</h1><p>Special offer for you.</p></body></html>",
            body_text="Hello {{first_name}}! Special offer for you.",
            sender_name="Marketing Team",
            sender_email="marketing@example.com",
            reply_to="support@example.com"
        )

    @classmethod
    def make_sms_content(cls) -> SMSChannelContent:
        """Generate SMS content"""
        return SMSChannelContent(
            body="Hi {{first_name}}! Check our special offer: example.com/offer"
        )

    @classmethod
    def make_in_app_content(cls) -> InAppChannelContent:
        """Generate in-app content"""
        return InAppChannelContent(
            title="Special Offer!",
            body="{{first_name}}, we have a special offer just for you.",
            action_url="/offers/special"
        )

    @classmethod
    def make_channel(
        cls,
        channel_type: ChannelType = ChannelType.EMAIL,
        enabled: bool = True
    ) -> CampaignChannel:
        """Generate channel configuration"""
        content_map = {
            ChannelType.EMAIL: ("email_content", cls.make_email_content()),
            ChannelType.SMS: ("sms_content", cls.make_sms_content()),
            ChannelType.IN_APP: ("in_app_content", cls.make_in_app_content()),
        }

        content_field, content = content_map.get(channel_type, ("email_content", cls.make_email_content()))

        return CampaignChannel(
            channel_id=cls.make_id("chn"),
            channel_type=channel_type,
            enabled=enabled,
            **{content_field: content}
        )

    @classmethod
    def make_audience(
        cls,
        segment_type: SegmentType = SegmentType.INCLUDE,
        segment_id: Optional[str] = None
    ) -> CampaignAudience:
        """Generate audience configuration"""
        return CampaignAudience(
            audience_id=cls.make_id("aud"),
            segment_type=segment_type,
            segment_id=segment_id or cls.make_segment_id(),
            name=f"Audience {random.randint(1, 100)}",
            estimated_size=random.randint(1000, 100000)
        )

    @classmethod
    def make_trigger(
        cls,
        event_type: str = "user.action"
    ) -> CampaignTrigger:
        """Generate trigger configuration"""
        return CampaignTrigger(
            trigger_id=cls.make_id("trg"),
            event_type=event_type,
            conditions=[
                TriggerCondition(
                    field="action_type",
                    operator=TriggerOperator.EQUALS,
                    value="purchase"
                )
            ],
            delay_minutes=0,
            frequency_limit=1,
            frequency_window_hours=24
        )

    @classmethod
    def make_variant(
        cls,
        name: str = "Variant A",
        allocation: Decimal = Decimal("50")
    ) -> CampaignVariant:
        """Generate variant configuration"""
        return CampaignVariant(
            variant_id=cls.make_variant_id(),
            name=name,
            allocation_percentage=allocation,
            channels=[cls.make_channel()]
        )

    @classmethod
    def make_campaign(
        cls,
        campaign_type: CampaignType = CampaignType.SCHEDULED,
        status: CampaignStatus = CampaignStatus.DRAFT,
        organization_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Campaign:
        """Generate complete campaign"""
        org_id = organization_id or cls.make_organization_id()
        user_id = created_by or cls.make_user_id()

        # Create default variant with channels
        default_variant = CampaignVariant(
            variant_id=cls.make_variant_id(),
            name="Default",
            allocation_percentage=Decimal("100"),
            channels=[cls.make_channel()]
        )

        # Build campaign kwargs - set schedule_type and scheduled_at BEFORE creating
        # the Campaign object to pass model validation
        campaign_kwargs = {
            "campaign_id": cls.make_campaign_id(),
            "organization_id": org_id,
            "name": cls.make_name(),
            "description": "Test campaign description",
            "campaign_type": campaign_type,
            "status": status,
            "audiences": [cls.make_audience()],
            "variants": [default_variant],
            "created_by": user_id,
            "throttle": ThrottleConfig(),  # Initialize throttle to avoid None access
        }

        # For scheduled campaigns, set schedule_type and scheduled_at before creation
        # to satisfy model validator requirements
        if campaign_type == CampaignType.SCHEDULED:
            campaign_kwargs["schedule_type"] = ScheduleType.ONE_TIME
            campaign_kwargs["scheduled_at"] = datetime.now(timezone.utc) + timedelta(hours=1)

        # For SCHEDULED status, ensure schedule fields are set
        if status in [CampaignStatus.SCHEDULED, CampaignStatus.RUNNING]:
            if campaign_type == CampaignType.SCHEDULED:
                campaign_kwargs["schedule_type"] = ScheduleType.ONE_TIME
                campaign_kwargs["scheduled_at"] = datetime.now(timezone.utc) + timedelta(hours=1)

        # For triggered campaigns, add triggers
        if campaign_type == CampaignType.TRIGGERED:
            campaign_kwargs["triggers"] = [cls.make_trigger()]

        campaign = Campaign(**campaign_kwargs)

        return campaign

    @classmethod
    def make_scheduled_campaign(
        cls,
        scheduled_at: Optional[datetime] = None,
        **kwargs
    ) -> Campaign:
        """Generate scheduled campaign"""
        campaign = cls.make_campaign(campaign_type=CampaignType.SCHEDULED, **kwargs)
        campaign.schedule_type = ScheduleType.ONE_TIME
        campaign.scheduled_at = scheduled_at or datetime.now(timezone.utc) + timedelta(hours=1)
        return campaign

    @classmethod
    def make_triggered_campaign(cls, **kwargs) -> Campaign:
        """Generate triggered campaign"""
        campaign = cls.make_campaign(campaign_type=CampaignType.TRIGGERED, **kwargs)
        campaign.triggers = [cls.make_trigger()]
        return campaign

    @classmethod
    def make_ab_test_campaign(
        cls,
        num_variants: int = 2,
        **kwargs
    ) -> Campaign:
        """Generate A/B test campaign"""
        campaign = cls.make_campaign(**kwargs)

        # Create variants with equal allocation
        allocation = Decimal("100") / num_variants
        campaign.variants = [
            cls.make_variant(name=f"Variant {chr(65+i)}", allocation=allocation)
            for i in range(num_variants)
        ]

        campaign.ab_test = ABTestConfig(
            enabled=True,
            auto_winner_enabled=False
        )

        return campaign

    @classmethod
    def make_execution(
        cls,
        campaign_id: str,
        status: ExecutionStatus = ExecutionStatus.PENDING
    ) -> CampaignExecution:
        """Generate campaign execution"""
        return CampaignExecution(
            execution_id=cls.make_execution_id(),
            campaign_id=campaign_id,
            execution_type=ExecutionType.SCHEDULED,
            status=status,
            total_audience_size=random.randint(1000, 100000)
        )

    @classmethod
    def make_message(
        cls,
        campaign_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        user_id: Optional[str] = None,
        channel_type: ChannelType = ChannelType.EMAIL,
        status: MessageStatus = MessageStatus.QUEUED
    ) -> CampaignMessage:
        """Generate campaign message.

        Args:
            campaign_id: Campaign ID (auto-generated if not provided)
            execution_id: Execution ID (auto-generated if not provided)
            user_id: User ID (auto-generated if not provided)
            channel_type: Channel type (default: EMAIL)
            status: Message status (default: QUEUED)
        """
        return CampaignMessage(
            message_id=cls.make_message_id(),
            campaign_id=campaign_id or cls.make_campaign_id(),
            execution_id=execution_id or cls.make_execution_id(),
            user_id=user_id or cls.make_user_id(),
            channel_type=channel_type,
            recipient_address=cls.make_email() if channel_type == ChannelType.EMAIL else cls.make_phone(),
            status=status
        )

    @classmethod
    def make_metrics_summary(
        cls,
        campaign_id: str,
        sent: int = 10000,
        execution_id: Optional[str] = None
    ) -> CampaignMetricsSummary:
        """Generate metrics summary"""
        delivered = int(sent * 0.98)
        opened = int(delivered * 0.25)
        clicked = int(opened * 0.15)
        converted = int(clicked * 0.05)
        bounced = sent - delivered
        unsubscribed = int(delivered * 0.002)

        return CampaignMetricsSummary(
            campaign_id=campaign_id,
            execution_id=execution_id,
            sent=sent,
            delivered=delivered,
            opened=opened,
            clicked=clicked,
            converted=converted,
            bounced=bounced,
            failed=0,
            unsubscribed=unsubscribed,
            delivery_rate=Decimal(str(round(delivered / sent, 4))) if sent > 0 else None,
            open_rate=Decimal(str(round(opened / delivered, 4))) if delivered > 0 else None,
            click_rate=Decimal(str(round(clicked / delivered, 4))) if delivered > 0 else None,
            conversion_rate=Decimal(str(round(converted / sent, 4))) if sent > 0 else None,
            bounce_rate=Decimal(str(round(bounced / sent, 4))) if sent > 0 else None,
            unsubscribe_rate=Decimal(str(round(unsubscribed / delivered, 4))) if delivered > 0 else None
        )

    @classmethod
    def make_conversion(
        cls,
        campaign_id: str,
        user_id: Optional[str] = None,
        conversion_value: Optional[Decimal] = None
    ) -> CampaignConversion:
        """Generate conversion record"""
        return CampaignConversion(
            conversion_id=cls.make_id("cnv"),
            campaign_id=campaign_id,
            user_id=user_id or cls.make_user_id(),
            conversion_event_type="purchase.completed",
            conversion_value=conversion_value or Decimal(str(random.randint(10, 500))),
            attribution_model=AttributionModel.LAST_TOUCH,
            converted_at=datetime.now(timezone.utc)
        )

    @classmethod
    def make_unsubscribe(
        cls,
        campaign_id: str,
        user_id: Optional[str] = None,
        channel_type: ChannelType = ChannelType.EMAIL
    ) -> CampaignUnsubscribe:
        """Generate unsubscribe record"""
        return CampaignUnsubscribe(
            unsubscribe_id=cls.make_id("uns"),
            campaign_id=campaign_id,
            user_id=user_id or cls.make_user_id(),
            channel_type=channel_type,
            reason="No longer interested"
        )

    @staticmethod
    def get_variant_hash(user_id: str, campaign_id: str) -> str:
        """Generate deterministic hash for variant assignment"""
        combined = f"{user_id}:{campaign_id}"
        return hashlib.md5(combined.encode()).hexdigest()

    @classmethod
    def assign_variant(
        cls,
        user_id: str,
        campaign_id: str,
        variants: List[CampaignVariant]
    ) -> CampaignVariant:
        """Deterministically assign user to variant"""
        hash_value = cls.get_variant_hash(user_id, campaign_id)
        hash_int = int(hash_value, 16)
        bucket = hash_int % 100

        cumulative = Decimal("0")
        for variant in variants:
            cumulative += variant.allocation_percentage
            if bucket < cumulative:
                return variant

        return variants[-1]  # Fallback to last variant


# =============================================================================
# BUILDER CLASSES
# =============================================================================

class CampaignCreateRequestBuilder:
    """Builder for CampaignCreateRequest"""

    def __init__(self):
        self._data = {
            "name": CampaignTestDataFactory.make_name(),
            "campaign_type": CampaignType.SCHEDULED,
            "audiences": [],
            "channels": [],
            "tags": [],
            "metadata": {}
        }

    def with_name(self, name: str) -> "CampaignCreateRequestBuilder":
        self._data["name"] = name
        return self

    def with_description(self, description: str) -> "CampaignCreateRequestBuilder":
        self._data["description"] = description
        return self

    def with_type(self, campaign_type: CampaignType) -> "CampaignCreateRequestBuilder":
        self._data["campaign_type"] = campaign_type
        return self

    def with_schedule(
        self,
        schedule_type: ScheduleType = ScheduleType.ONE_TIME,
        scheduled_at: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        timezone: str = "UTC"
    ) -> "CampaignCreateRequestBuilder":
        self._data["schedule_type"] = schedule_type
        self._data["scheduled_at"] = scheduled_at or datetime.now(timezone.utc) + timedelta(hours=1)
        self._data["cron_expression"] = cron_expression
        self._data["timezone"] = timezone
        return self

    def with_audience(
        self,
        segment_id_or_audience: Union[str, CampaignAudience],
        segment_type: Optional[SegmentType] = None
    ) -> "CampaignCreateRequestBuilder":
        """Add audience to request.

        Can be called with:
        - A CampaignAudience object directly
        - A segment_id string and SegmentType to create an audience
        """
        if isinstance(segment_id_or_audience, CampaignAudience):
            self._data["audiences"].append(segment_id_or_audience)
        else:
            # segment_id_or_audience is a string segment_id
            audience = CampaignAudience(
                audience_id=f"aud_{uuid4().hex[:16]}",
                segment_type=segment_type or SegmentType.INCLUDE,
                segment_id=segment_id_or_audience,
            )
            self._data["audiences"].append(audience)
        return self

    def with_channel(self, channel: CampaignChannel) -> "CampaignCreateRequestBuilder":
        self._data["channels"].append(channel)
        return self

    def with_trigger(self, trigger: CampaignTrigger) -> "CampaignCreateRequestBuilder":
        if "triggers" not in self._data:
            self._data["triggers"] = []
        self._data["triggers"].append(trigger)
        return self

    def with_ab_testing(
        self,
        variants: Optional[List[CampaignVariant]] = None,
        enabled: bool = True
    ) -> "CampaignCreateRequestBuilder":
        """Enable A/B testing with optional variants.

        Can be called with:
        - A list of CampaignVariant objects
        - enabled=True to just enable A/B testing (will use default variants)
        """
        self._data["enable_ab_testing"] = enabled
        if variants:
            self._data["variants"] = variants
        return self

    def with_holdout(self, percentage: Decimal) -> "CampaignCreateRequestBuilder":
        self._data["holdout_percentage"] = percentage
        return self

    def with_conversion_tracking(
        self,
        event_type: str,
        window_days: int = 7
    ) -> "CampaignCreateRequestBuilder":
        self._data["conversion_event_type"] = event_type
        self._data["attribution_window_days"] = window_days
        return self

    def build(self) -> CampaignCreateRequest:
        return CampaignCreateRequest(**self._data)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "CampaignType",
    "CampaignStatus",
    "ScheduleType",
    "ChannelType",
    "SegmentType",
    "TriggerOperator",
    "MessageStatus",
    "BounceType",
    "ExecutionType",
    "ExecutionStatus",
    "MetricType",
    "AttributionModel",
    "AutoWinnerMetric",
    "FrequencyWindow",

    # Models
    "Campaign",
    "CampaignAudience",
    "CampaignChannel",
    "CampaignVariant",
    "CampaignTrigger",
    "TriggerCondition",
    "ThrottleConfig",
    "ABTestConfig",
    "ConversionConfig",
    "EmailChannelContent",
    "SMSChannelContent",
    "WhatsAppChannelContent",
    "InAppChannelContent",
    "WebhookChannelContent",

    # Execution Models
    "CampaignExecution",
    "CampaignMessage",

    # Metrics Models
    "CampaignMetricRecord",
    "CampaignMetricsSummary",
    "VariantStatistics",

    # Conversion/Unsubscribe Models
    "CampaignConversion",
    "CampaignUnsubscribe",
    "TriggerHistoryRecord",

    # Request/Response Models
    "CampaignCreateRequest",
    "CampaignUpdateRequest",
    "CampaignResponse",
    "CampaignListResponse",
    "CampaignQueryRequest",
    "CampaignMetricsResponse",
    "AudienceEstimateResponse",
    "ContentPreviewRequest",
    "ContentPreviewResponse",

    # Test Data
    "CampaignTestDataFactory",
    "CampaignCreateRequestBuilder",
]
