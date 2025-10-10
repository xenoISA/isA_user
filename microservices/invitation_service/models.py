"""
Invitation Service Models

邀请服务数据模型定义
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class InvitationStatus(str, Enum):
    """邀请状态"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class OrganizationRole(str, Enum):
    """组织角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


# Request Models
class InvitationCreateRequest(BaseModel):
    """创建邀请请求"""
    email: str = Field(..., description="被邀请人邮箱")
    role: OrganizationRole = Field(default=OrganizationRole.MEMBER, description="角色")
    message: Optional[str] = Field(None, max_length=500, description="个人消息")

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()


class AcceptInvitationRequest(BaseModel):
    """接受邀请请求"""
    invitation_token: str = Field(..., description="邀请令牌")
    user_id: Optional[str] = Field(None, description="用户ID（如果已注册）")


class ResendInvitationRequest(BaseModel):
    """重发邀请请求"""
    invitation_id: str = Field(..., description="邀请ID")


# Response Models
class InvitationResponse(BaseModel):
    """邀请响应"""
    invitation_id: str
    organization_id: str
    email: str
    role: OrganizationRole
    status: InvitationStatus
    invited_by: str
    invitation_token: str
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class InvitationDetailResponse(BaseModel):
    """邀请详情响应"""
    invitation_id: str
    organization_id: str
    organization_name: str
    organization_domain: Optional[str] = None
    email: str
    role: OrganizationRole
    status: InvitationStatus
    inviter_name: Optional[str] = None
    inviter_email: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class InvitationListResponse(BaseModel):
    """邀请列表响应"""
    invitations: List[InvitationDetailResponse]
    total: int
    limit: int
    offset: int


class AcceptInvitationResponse(BaseModel):
    """接受邀请响应"""
    invitation_id: str
    organization_id: str
    organization_name: str
    user_id: str
    role: OrganizationRole
    accepted_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Service Status Models
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    service: str = "invitation_service"
    port: int = 8213
    version: str = "1.0.0"


class ServiceInfo(BaseModel):
    """服务信息"""
    service: str = "invitation_service"
    version: str = "1.0.0"
    description: str = "Organization invitation management microservice"
    capabilities: Dict[str, bool] = Field(default_factory=lambda: {
        "invitation_creation": True,
        "email_sending": True,
        "invitation_acceptance": True,
        "invitation_management": True,
        "organization_integration": True
    })
    endpoints: Dict[str, str] = Field(default_factory=lambda: {
        "health": "/health",
        "create_invitation": "/api/v1/organizations/{org_id}/invitations",
        "get_invitation": "/api/v1/invitations/{token}",
        "accept_invitation": "/api/v1/invitations/accept",
        "organization_invitations": "/api/v1/organizations/{org_id}/invitations"
    })


class ServiceStats(BaseModel):
    """服务统计"""
    total_invitations: int = 0
    pending_invitations: int = 0
    accepted_invitations: int = 0
    expired_invitations: int = 0
    requests_today: int = 0
    average_response_time_ms: float = 0.0