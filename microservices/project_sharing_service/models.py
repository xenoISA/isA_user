"""
Project Sharing Service Models

Pydantic models for project share invitations.
Schema mirrors the project_shares table (see migrations/001).
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Enums (match Postgres ENUM types in the project_sharing schema)
# ============================================================================


class ProjectShareRole(str, Enum):
    """Permission level granted to an invitee."""

    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"


class ProjectShareStatus(str, Enum):
    """Invite lifecycle state."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


# ============================================================================
# Domain model
# ============================================================================


class ProjectShare(BaseModel):
    """Project share / invitation row."""

    id: str = Field(..., description="Share record UUID")
    project_id: str = Field(..., description="Project being shared")
    invitee_user_id: Optional[str] = Field(None, description="User id once accepted; None for pending invites")
    invitee_email: str = Field(..., description="Invitee email address")
    role: ProjectShareRole = Field(..., description="Permission level")
    invite_token: Optional[str] = Field(
        None,
        description="URL-safe token used to accept the invite; None after revoke",
    )
    status: ProjectShareStatus = Field(..., description="pending | accepted | revoked")
    created_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Request models
# ============================================================================


class CreateShareRequest(BaseModel):
    """POST /api/v1/projects/{project_id}/shares body."""

    invitee_email: EmailStr = Field(..., description="Email address to invite")
    role: ProjectShareRole = Field(default=ProjectShareRole.VIEWER, description="Permission level for the invitee")


class UpdateShareRequest(BaseModel):
    """PATCH /api/v1/projects/{project_id}/shares/{share_id} body."""

    role: ProjectShareRole = Field(..., description="New permission level")


class AcceptShareRequest(BaseModel):
    """POST /api/v1/shares/accept/{token} body."""

    invitee_user_id: str = Field(..., description="User id of the invitee who is accepting")


# ============================================================================
# Response models
# ============================================================================


class ShareResponse(BaseModel):
    """Single share response, returned from invite/list/patch."""

    id: str
    project_id: str
    invitee_user_id: Optional[str] = None
    invitee_email: str
    role: ProjectShareRole
    invite_token: Optional[str] = None
    share_url: Optional[str] = Field(None, description="Full shareable accept URL; None after revoke")
    status: ProjectShareStatus
    created_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ShareListResponse(BaseModel):
    """GET /api/v1/projects/{project_id}/shares response."""

    shares: List[ShareResponse]
    total: int


class RevokeResponse(BaseModel):
    """DELETE /api/v1/projects/{project_id}/shares/{share_id} response."""

    id: str
    project_id: str
    status: ProjectShareStatus
    revoked_at: Optional[datetime] = None


# ============================================================================
# Error response
# ============================================================================


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
