"""
Organization Service Models

组织服务数据模型定义
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# Enums
class OrganizationPlan(str, Enum):
    """组织订阅计划"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class OrganizationStatus(str, Enum):
    """组织状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class OrganizationRole(str, Enum):
    """组织成员角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class MemberStatus(str, Enum):
    """成员状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


# Request Models
class OrganizationCreateRequest(BaseModel):
    """创建组织请求"""
    name: str = Field(..., min_length=1, max_length=100, description="组织名称")
    domain: Optional[str] = Field(None, max_length=255, description="组织域名")
    billing_email: str = Field(..., description="账单邮箱")
    plan: OrganizationPlan = Field(default=OrganizationPlan.FREE, description="订阅计划")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="组织设置")

    @validator('billing_email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()


class OrganizationUpdateRequest(BaseModel):
    """更新组织请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    domain: Optional[str] = Field(None, max_length=255)
    billing_email: Optional[str] = None
    plan: Optional[OrganizationPlan] = None
    settings: Optional[Dict[str, Any]] = None

    @validator('billing_email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower() if v else v


class OrganizationMemberAddRequest(BaseModel):
    """添加组织成员请求"""
    user_id: str = Field(..., description="用户ID")
    role: OrganizationRole = Field(default=OrganizationRole.MEMBER, description="成员角色")
    permissions: Optional[List[str]] = Field(default_factory=list, description="自定义权限")

    @validator('role')
    def validate_role(cls, v):
        # 不能直接添加 owner
        if v == OrganizationRole.OWNER:
            raise ValueError('Cannot directly add owner role')
        return v


class OrganizationMemberUpdateRequest(BaseModel):
    """更新组织成员请求"""
    role: Optional[OrganizationRole] = None
    status: Optional[MemberStatus] = None
    permissions: Optional[List[str]] = None


class OrganizationSwitchRequest(BaseModel):
    """切换组织上下文请求"""
    organization_id: Optional[str] = Field(None, description="组织ID（None表示切回个人）")


# Response Models
class OrganizationResponse(BaseModel):
    """组织响应"""
    organization_id: str
    name: str
    domain: Optional[str] = None
    billing_email: str
    plan: OrganizationPlan
    status: OrganizationStatus
    member_count: int = 0
    credits_pool: Decimal = Decimal(0)
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class OrganizationMemberResponse(BaseModel):
    """组织成员响应"""
    user_id: str
    organization_id: str
    role: OrganizationRole
    status: MemberStatus
    permissions: List[str] = Field(default_factory=list)
    joined_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OrganizationListResponse(BaseModel):
    """组织列表响应"""
    organizations: List[OrganizationResponse]
    total: int
    limit: int
    offset: int


class OrganizationMemberListResponse(BaseModel):
    """组织成员列表响应"""
    members: List[OrganizationMemberResponse]
    total: int
    limit: int
    offset: int


class OrganizationContextResponse(BaseModel):
    """组织上下文响应"""
    context_type: str  # "individual" or "organization"
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    user_role: Optional[OrganizationRole] = None
    permissions: List[str] = Field(default_factory=list)
    credits_available: Optional[Decimal] = None

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class OrganizationStatsResponse(BaseModel):
    """组织统计响应"""
    organization_id: str
    name: str
    plan: OrganizationPlan
    status: OrganizationStatus
    member_count: int
    active_members: int
    credits_pool: Decimal
    credits_used_this_month: Decimal = Decimal(0)
    storage_used_gb: float = 0.0
    api_calls_this_month: int = 0
    created_at: datetime
    subscription_expires_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class OrganizationUsageResponse(BaseModel):
    """组织使用量响应"""
    organization_id: str
    period_start: datetime
    period_end: datetime
    credits_consumed: Decimal
    api_calls: int
    storage_gb_hours: float
    active_users: int
    top_users: List[Dict[str, Any]] = Field(default_factory=list)
    usage_by_service: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


# Service Status Models (for health checks)
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    service: str = "organization_service"
    port: int = 8212
    version: str = "1.0.0"


class ServiceInfo(BaseModel):
    """服务信息"""
    service: str = "organization_service"
    version: str = "1.0.0"
    description: str = "Organization management microservice"
    capabilities: Dict[str, bool] = Field(default_factory=lambda: {
        "organization_management": True,
        "member_management": True,
        "role_management": True,
        "context_switching": True,
        "usage_tracking": True,
        "multi_tenant": True
    })
    endpoints: Dict[str, str] = Field(default_factory=lambda: {
        "health": "/health",
        "organizations": "/api/v1/organizations",
        "members": "/api/v1/organizations/{org_id}/members",
        "context": "/api/v1/organizations/context",
        "stats": "/api/v1/organizations/{org_id}/stats"
    })


class ServiceStats(BaseModel):
    """服务统计"""
    total_organizations: int = 0
    active_organizations: int = 0
    total_members: int = 0
    requests_today: int = 0
    average_response_time_ms: float = 0.0