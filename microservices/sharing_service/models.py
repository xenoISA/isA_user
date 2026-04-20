"""
Sharing Service Models

Independent models for share link management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SharePermission(str, Enum):
    """Share permission levels"""
    VIEW_ONLY = "view_only"
    CAN_COMMENT = "can_comment"
    CAN_EDIT = "can_edit"


# ============================================================================
# Domain Models
# ============================================================================


class Share(BaseModel):
    """Share link domain model"""
    id: str = Field(..., description="Share record UUID")
    session_id: str = Field(..., description="Session being shared")
    owner_id: str = Field(..., description="User who created the share")
    share_token: str = Field(..., description="URL-safe token for access")
    permissions: str = Field(default=SharePermission.VIEW_ONLY, description="Permission level")
    expires_at: Optional[datetime] = Field(None, description="Expiry timestamp (null = never)")
    access_count: int = Field(default=0, description="Number of times accessed")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Request Models
# ============================================================================


class ShareCreateRequest(BaseModel):
    """Create a share link for a session"""
    permissions: SharePermission = Field(
        default=SharePermission.VIEW_ONLY,
        description="Permission level for share recipients",
    )
    expires_in_hours: Optional[int] = Field(
        None,
        ge=1,
        le=8760,  # max 1 year
        description="Hours until link expires (null = never)",
    )


# ============================================================================
# Response Models
# ============================================================================


class ShareResponse(BaseModel):
    """Share link response"""
    id: str
    session_id: str
    owner_id: str
    share_token: str
    share_url: str = Field(..., description="Full shareable URL")
    permissions: str
    expires_at: Optional[datetime] = None
    access_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ShareListResponse(BaseModel):
    """List of share links for a session"""
    shares: List[ShareResponse]
    total: int


class SharedSessionResponse(BaseModel):
    """Session data returned when accessing via share token"""
    session_id: str
    session_summary: str = ""
    permissions: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    message_count: int = 0
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


# ============================================================================
# Error Response
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")


# ============================================================================
# Event Data Models
# ============================================================================


class ShareCreatedEventData(BaseModel):
    """Data for share.created event"""
    share_id: str
    session_id: str
    owner_id: str
    share_token: str
    permissions: str
    expires_at: Optional[str] = None
    timestamp: str


class ShareAccessedEventData(BaseModel):
    """Data for share.accessed event"""
    share_id: str
    session_id: str
    share_token: str
    access_count: int
    timestamp: str


class ShareRevokedEventData(BaseModel):
    """Data for share.revoked event"""
    share_id: str
    session_id: str
    owner_id: str
    share_token: str
    timestamp: str
