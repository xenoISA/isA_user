"""
Campaign Service Protocols

Defines interfaces for dependency injection and testing.
Following the protocol-based architecture pattern.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .models import (
    Campaign,
    CampaignAudience,
    CampaignChannel,
    CampaignVariant,
    CampaignTrigger,
    CampaignExecution,
    CampaignMessage,
    CampaignMetricsSummary,
    CampaignConversion,
    CampaignUnsubscribe,
    TriggerHistoryRecord,
    CampaignStatus,
    CampaignType,
    ExecutionStatus,
    MessageStatus,
    ChannelType,
)


# ====================
# Repository Protocol
# ====================


class CampaignRepositoryProtocol(Protocol):
    """Protocol for campaign data repository"""

    async def initialize(self) -> None:
        """Initialize repository connection"""
        ...

    async def close(self) -> None:
        """Close repository connection"""
        ...

    async def health_check(self) -> bool:
        """Check repository health"""
        ...

    # Campaign CRUD
    async def save_campaign(self, campaign: Campaign) -> Campaign:
        """Save a campaign"""
        ...

    async def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        ...

    async def get_campaign_by_org(
        self, organization_id: str, campaign_id: str
    ) -> Optional[Campaign]:
        """Get campaign by organization and ID"""
        ...

    async def list_campaigns(
        self,
        organization_id: Optional[str] = None,
        status: Optional[List[CampaignStatus]] = None,
        campaign_type: Optional[CampaignType] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Campaign], int]:
        """List campaigns with filters"""
        ...

    async def update_campaign(
        self, campaign_id: str, updates: dict
    ) -> Optional[Campaign]:
        """Update campaign fields"""
        ...

    async def update_campaign_status(
        self, campaign_id: str, status: CampaignStatus, **kwargs
    ) -> Optional[Campaign]:
        """Update campaign status"""
        ...

    async def delete_campaign(self, campaign_id: str) -> bool:
        """Soft delete campaign"""
        ...

    # Audience operations
    async def save_audiences(
        self, campaign_id: str, audiences: List[CampaignAudience]
    ) -> List[CampaignAudience]:
        """Save campaign audiences"""
        ...

    async def get_audiences(self, campaign_id: str) -> List[CampaignAudience]:
        """Get campaign audiences"""
        ...

    # Variant operations
    async def save_variant(
        self, campaign_id: str, variant: CampaignVariant
    ) -> CampaignVariant:
        """Save campaign variant"""
        ...

    async def get_variants(self, campaign_id: str) -> List[CampaignVariant]:
        """Get campaign variants"""
        ...

    async def update_variant(
        self, campaign_id: str, variant_id: str, updates: dict
    ) -> Optional[CampaignVariant]:
        """Update variant"""
        ...

    async def delete_variant(self, campaign_id: str, variant_id: str) -> bool:
        """Delete variant"""
        ...

    # Channel operations
    async def save_channels(
        self, campaign_id: str, channels: List[CampaignChannel]
    ) -> List[CampaignChannel]:
        """Save campaign channels"""
        ...

    async def get_channels(self, campaign_id: str) -> List[CampaignChannel]:
        """Get campaign channels"""
        ...

    # Trigger operations
    async def save_triggers(
        self, campaign_id: str, triggers: List[CampaignTrigger]
    ) -> List[CampaignTrigger]:
        """Save campaign triggers"""
        ...

    async def get_triggers(self, campaign_id: str) -> List[CampaignTrigger]:
        """Get campaign triggers"""
        ...

    # Execution operations
    async def save_execution(self, execution: CampaignExecution) -> CampaignExecution:
        """Save execution"""
        ...

    async def get_execution(self, execution_id: str) -> Optional[CampaignExecution]:
        """Get execution by ID"""
        ...

    async def list_executions(
        self, campaign_id: str, limit: int = 20, offset: int = 0
    ) -> Tuple[List[CampaignExecution], int]:
        """List executions for campaign"""
        ...

    async def update_execution_status(
        self, execution_id: str, status: ExecutionStatus, **kwargs
    ) -> Optional[CampaignExecution]:
        """Update execution status"""
        ...

    # Message operations
    async def save_message(self, message: CampaignMessage) -> CampaignMessage:
        """Save message"""
        ...

    async def get_message(self, message_id: str) -> Optional[CampaignMessage]:
        """Get message by ID"""
        ...

    async def list_messages(
        self,
        campaign_id: str,
        execution_id: Optional[str] = None,
        status: Optional[MessageStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[CampaignMessage], int]:
        """List messages for campaign"""
        ...

    async def update_message_status(
        self, message_id: str, status: MessageStatus, **kwargs
    ) -> Optional[CampaignMessage]:
        """Update message status"""
        ...

    # Metrics operations
    async def get_metrics_summary(
        self, campaign_id: str
    ) -> Optional[CampaignMetricsSummary]:
        """Get metrics summary for campaign"""
        ...

    async def save_metrics_summary(
        self, metrics: CampaignMetricsSummary
    ) -> CampaignMetricsSummary:
        """Save metrics summary"""
        ...

    # Conversion operations
    async def save_conversion(
        self, conversion: CampaignConversion
    ) -> CampaignConversion:
        """Save conversion record"""
        ...

    async def list_conversions(
        self, campaign_id: str, limit: int = 100, offset: int = 0
    ) -> Tuple[List[CampaignConversion], int]:
        """List conversions for campaign"""
        ...

    # Unsubscribe operations
    async def save_unsubscribe(
        self, unsubscribe: CampaignUnsubscribe
    ) -> CampaignUnsubscribe:
        """Save unsubscribe record"""
        ...

    # Trigger history operations
    async def save_trigger_history(
        self, history: TriggerHistoryRecord
    ) -> TriggerHistoryRecord:
        """Save trigger history record"""
        ...

    async def get_recent_trigger_history(
        self,
        campaign_id: str,
        trigger_id: str,
        user_id: str,
        hours: int = 24,
    ) -> List[TriggerHistoryRecord]:
        """Get recent trigger history for frequency limiting"""
        ...


# ====================
# Event Bus Protocol
# ====================


class EventBusProtocol(Protocol):
    """Protocol for event bus operations"""

    async def publish_event(self, event: Any) -> bool:
        """Publish an event to the event bus"""
        ...

    async def subscribe(
        self, subject: str, handler: Any, durable: Optional[str] = None
    ) -> None:
        """Subscribe to events matching a subject"""
        ...

    async def close(self) -> None:
        """Close event bus connection"""
        ...


# ====================
# Service Client Protocols
# ====================


class TaskClientProtocol(Protocol):
    """Protocol for task service client"""

    async def create_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        scheduled_at: datetime,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a scheduled task"""
        ...

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        ...


class NotificationClientProtocol(Protocol):
    """Protocol for notification service client"""

    async def send_notification(
        self,
        user_id: str,
        channel_type: ChannelType,
        content: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a notification"""
        ...


class IsADataClientProtocol(Protocol):
    """Protocol for isA_Data client (segment resolution)"""

    async def get_segment_users(self, segment_id: str) -> List[str]:
        """Get user IDs in a segment"""
        ...

    async def get_user_360(self, user_id: str) -> Dict[str, Any]:
        """Get user 360 profile"""
        ...

    async def estimate_segment_size(self, segment_id: str) -> int:
        """Estimate segment size"""
        ...


class AccountClientProtocol(Protocol):
    """Protocol for account service client"""

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user communication preferences"""
        ...

    async def check_channel_eligibility(
        self, user_id: str, channel_type: ChannelType
    ) -> bool:
        """Check if user is eligible for channel"""
        ...


# ====================
# Custom Exceptions
# ====================


class CampaignServiceError(Exception):
    """Base exception for campaign service errors"""
    pass


class CampaignNotFoundError(CampaignServiceError):
    """Raised when campaign is not found"""
    pass


class InvalidCampaignStateError(CampaignServiceError):
    """Raised when campaign is in invalid state for operation"""

    def __init__(self, message: str, current_status: Optional[CampaignStatus] = None):
        super().__init__(message)
        self.current_status = current_status


class InvalidCampaignTypeError(CampaignServiceError):
    """Raised when operation is invalid for campaign type"""

    def __init__(self, message: str, campaign_type: Optional[CampaignType] = None):
        super().__init__(message)
        self.campaign_type = campaign_type


class CampaignValidationError(CampaignServiceError):
    """Raised when campaign validation fails"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


class AudienceResolutionError(CampaignServiceError):
    """Raised when audience resolution fails"""
    pass


class VariantAllocationError(CampaignServiceError):
    """Raised when variant allocation is invalid"""
    pass


class TriggerEvaluationError(CampaignServiceError):
    """Raised when trigger evaluation fails"""
    pass


class MessageDeliveryError(CampaignServiceError):
    """Raised when message delivery fails"""
    pass


__all__ = [
    "CampaignRepositoryProtocol",
    "EventBusProtocol",
    "TaskClientProtocol",
    "NotificationClientProtocol",
    "IsADataClientProtocol",
    "AccountClientProtocol",
    "CampaignServiceError",
    "CampaignNotFoundError",
    "InvalidCampaignStateError",
    "InvalidCampaignTypeError",
    "CampaignValidationError",
    "AudienceResolutionError",
    "VariantAllocationError",
    "TriggerEvaluationError",
    "MessageDeliveryError",
]
