"""
Invitation Service Event Models

邀请服务事件数据模型定义
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class InvitationEventType(str, Enum):
    """
    Events published by invitation_service.

    Stream: invitation-stream
    Subjects: invitation.>
    """
    INVITATION_SENT = "invitation.sent"
    INVITATION_ACCEPTED = "invitation.accepted"
    INVITATION_DECLINED = "invitation.declined"
    INVITATION_EXPIRED = "invitation.expired"
    INVITATION_CANCELLED = "invitation.cancelled"


class InvitationSubscribedEventType(str, Enum):
    """Events that invitation_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class InvitationStreamConfig:
    """Stream configuration for invitation_service"""
    STREAM_NAME = "invitation-stream"
    SUBJECTS = ["invitation.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "invitation"

from typing import Optional, Dict, Any
from datetime import datetime


class InvitationSentEvent(BaseModel):
    """邀请已发送事件"""

    invitation_id: str = Field(..., description="邀请ID")
    organization_id: str = Field(..., description="组织ID")
    email: str = Field(..., description="受邀邮箱")
    role: str = Field(..., description="角色")
    invited_by: str = Field(..., description="邀请人用户ID")
    email_sent: bool = Field(default=False, description="邮件是否发送成功")
    timestamp: str = Field(..., description="事件时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class InvitationExpiredEvent(BaseModel):
    """邀请已过期事件"""

    invitation_id: str = Field(..., description="邀请ID")
    organization_id: str = Field(..., description="组织ID")
    email: str = Field(..., description="受邀邮箱")
    expired_at: str = Field(..., description="过期时间")
    timestamp: str = Field(..., description="事件时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class InvitationAcceptedEvent(BaseModel):
    """邀请已接受事件"""

    invitation_id: str = Field(..., description="邀请ID")
    organization_id: str = Field(..., description="组织ID")
    user_id: str = Field(..., description="接受邀请的用户ID")
    email: str = Field(..., description="用户邮箱")
    role: str = Field(..., description="分配的角色")
    accepted_at: str = Field(..., description="接受时间")
    timestamp: str = Field(..., description="事件时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class InvitationCancelledEvent(BaseModel):
    """邀请已取消事件"""

    invitation_id: str = Field(..., description="邀请ID")
    organization_id: str = Field(..., description="组织ID")
    email: str = Field(..., description="受邀邮箱")
    cancelled_by: str = Field(..., description="取消人用户ID")
    timestamp: str = Field(..., description="事件时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")
