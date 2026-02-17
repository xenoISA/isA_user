"""
Campaign Service Data Models

Re-exports all models from the data contract for microservice use.
This module provides the canonical data structures for the campaign service.
"""

# Import all models from data_contract.py which is the single source of truth
from tests.contracts.campaign.data_contract import (
    # Enums
    CampaignType,
    CampaignStatus,
    ScheduleType,
    ChannelType,
    SegmentType,
    TriggerOperator,
    MessageStatus,
    BounceType,
    ExecutionType,
    ExecutionStatus,
    MetricType,
    AttributionModel,
    AutoWinnerMetric,
    FrequencyWindow,
    # Core Models
    Campaign,
    CampaignAudience,
    CampaignChannel,
    CampaignVariant,
    CampaignTrigger,
    TriggerCondition,
    ThrottleConfig,
    ABTestConfig,
    ConversionConfig,
    # Channel Content Models
    EmailChannelContent,
    SMSChannelContent,
    WhatsAppChannelContent,
    InAppChannelContent,
    WebhookChannelContent,
    # Execution Models
    CampaignExecution,
    CampaignMessage,
    # Metrics Models
    CampaignMetricRecord,
    CampaignMetricsSummary,
    VariantStatistics,
    # Conversion/Tracking Models
    CampaignConversion,
    CampaignUnsubscribe,
    TriggerHistoryRecord,
    # Request/Response Models
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignResponse,
    CampaignListResponse,
    CampaignQueryRequest,
    CampaignMetricsResponse,
    AudienceEstimateResponse,
    ContentPreviewRequest,
    ContentPreviewResponse,
    # Test Data Factory
    CampaignTestDataFactory,
    CampaignCreateRequestBuilder,
)

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ====================
# Additional Service Models
# ====================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    port: int
    version: str
    dependencies: Dict[str, str] = Field(default_factory=dict)


class ReadinessResponse(BaseModel):
    """Readiness check response"""
    ready: bool
    checks: Dict[str, bool] = Field(default_factory=dict)
    details: Dict[str, str] = Field(default_factory=dict)


class LivenessResponse(BaseModel):
    """Liveness check response"""
    alive: bool
    uptime_seconds: float


class ScheduleRequest(BaseModel):
    """Request to schedule a campaign"""
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"


class CancelRequest(BaseModel):
    """Request to cancel a campaign"""
    reason: Optional[str] = Field(None, max_length=500)


class CloneRequest(BaseModel):
    """Request to clone a campaign"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class VariantCreateRequest(BaseModel):
    """Request to create a variant"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    allocation_percentage: float = Field(..., ge=0, le=100)
    is_control: bool = False
    channels: List[CampaignChannel] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
    # Core Models
    "Campaign",
    "CampaignAudience",
    "CampaignChannel",
    "CampaignVariant",
    "CampaignTrigger",
    "TriggerCondition",
    "ThrottleConfig",
    "ABTestConfig",
    "ConversionConfig",
    # Channel Content
    "EmailChannelContent",
    "SMSChannelContent",
    "WhatsAppChannelContent",
    "InAppChannelContent",
    "WebhookChannelContent",
    # Execution
    "CampaignExecution",
    "CampaignMessage",
    # Metrics
    "CampaignMetricRecord",
    "CampaignMetricsSummary",
    "VariantStatistics",
    # Conversion/Tracking
    "CampaignConversion",
    "CampaignUnsubscribe",
    "TriggerHistoryRecord",
    # Request/Response
    "CampaignCreateRequest",
    "CampaignUpdateRequest",
    "CampaignResponse",
    "CampaignListResponse",
    "CampaignQueryRequest",
    "CampaignMetricsResponse",
    "AudienceEstimateResponse",
    "ContentPreviewRequest",
    "ContentPreviewResponse",
    # Service Models
    "HealthResponse",
    "ReadinessResponse",
    "LivenessResponse",
    "ScheduleRequest",
    "CancelRequest",
    "CloneRequest",
    "VariantCreateRequest",
    "ErrorResponse",
    # Test Data
    "CampaignTestDataFactory",
    "CampaignCreateRequestBuilder",
]
