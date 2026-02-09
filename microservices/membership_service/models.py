"""
Membership Service Data Models

Pydantic models for membership, points, tiers, and benefits.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# ====================
# Enum Types
# ====================

class MembershipStatus(str, Enum):
    """Membership status"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELED = "canceled"


class MembershipTier(str, Enum):
    """Membership tier codes"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class PointAction(str, Enum):
    """Point/membership action types"""
    ENROLLED = "enrolled"
    POINTS_EARNED = "points_earned"
    POINTS_REDEEMED = "points_redeemed"
    POINTS_EXPIRED = "points_expired"
    POINTS_ADJUSTED = "points_adjusted"
    TIER_UPGRADED = "tier_upgraded"
    TIER_DOWNGRADED = "tier_downgraded"
    BENEFIT_USED = "benefit_used"
    SUSPENDED = "suspended"
    REACTIVATED = "reactivated"
    RENEWED = "renewed"
    EXPIRED = "expired"
    CANCELED = "canceled"


class InitiatedBy(str, Enum):
    """Who initiated the action"""
    USER = "user"
    SYSTEM = "system"
    ADMIN = "admin"
    SERVICE = "service"


# ====================
# Core Data Models
# ====================

class Membership(BaseModel):
    """Membership entity model"""
    id: Optional[int] = None
    membership_id: str = Field(..., description="Unique membership ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = None

    # Tier
    tier_code: MembershipTier = MembershipTier.BRONZE
    status: MembershipStatus = MembershipStatus.ACTIVE

    # Points
    points_balance: int = Field(default=0, ge=0)
    tier_points: int = Field(default=0, ge=0)
    lifetime_points: int = Field(default=0, ge=0)
    pending_points: int = Field(default=0, ge=0)

    # Dates
    enrolled_at: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    # Settings
    auto_renew: bool = True

    # Metadata
    enrollment_source: Optional[str] = None
    promo_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MembershipHistory(BaseModel):
    """Membership history entry model"""
    id: Optional[int] = None
    history_id: str = Field(..., description="History entry ID")
    membership_id: str = Field(..., description="Membership ID")

    # Action
    action: PointAction
    points_change: int = 0
    balance_after: Optional[int] = None
    previous_tier: Optional[str] = None
    new_tier: Optional[str] = None

    # Context
    source: Optional[str] = None
    reference_id: Optional[str] = None
    reward_code: Optional[str] = None
    benefit_code: Optional[str] = None
    description: Optional[str] = None
    initiated_by: InitiatedBy = InitiatedBy.SYSTEM
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: Optional[datetime] = None


class Tier(BaseModel):
    """Tier definition model"""
    id: Optional[int] = None
    tier_code: MembershipTier
    tier_name: str
    display_order: int = 0
    qualification_threshold: int = Field(default=0, ge=0)
    point_multiplier: Decimal = Field(default=Decimal("1.0"))
    is_active: bool = True
    created_at: Optional[datetime] = None


class TierBenefit(BaseModel):
    """Tier benefit model"""
    id: Optional[int] = None
    benefit_id: str
    tier_code: MembershipTier
    benefit_code: str
    benefit_name: str
    benefit_type: str
    usage_limit: Optional[int] = None
    is_unlimited: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None


class BenefitUsage(BaseModel):
    """Benefit usage tracking"""
    benefit_code: str
    benefit_name: str
    benefit_type: str
    usage_limit: Optional[int] = None
    used_count: int = Field(default=0, ge=0)
    remaining: Optional[int] = None
    is_unlimited: bool = False
    is_available: bool = True


# ====================
# Request Models
# ====================

class EnrollMembershipRequest(BaseModel):
    """Enrollment request"""
    user_id: str = Field(..., min_length=1, description="User ID")
    organization_id: Optional[str] = None
    enrollment_source: Optional[str] = Field(default="api", max_length=50)
    promo_code: Optional[str] = Field(default=None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None


class EarnPointsRequest(BaseModel):
    """Earn points request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = None
    points_amount: int = Field(..., gt=0, le=10_000_000)
    source: str = Field(..., min_length=1, max_length=50)
    reference_id: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None


class RedeemPointsRequest(BaseModel):
    """Redeem points request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = None
    points_amount: int = Field(..., gt=0, le=10_000_000)
    reward_code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None


class CancelMembershipRequest(BaseModel):
    """Cancel membership request"""
    reason: Optional[str] = Field(default=None, max_length=500)
    forfeit_points: bool = False
    feedback: Optional[str] = Field(default=None, max_length=1000)


class SuspendMembershipRequest(BaseModel):
    """Suspend membership request"""
    reason: str = Field(..., min_length=1, max_length=500)
    duration_days: Optional[int] = Field(default=None, ge=1, le=365)


class UseBenefitRequest(BaseModel):
    """Use benefit request"""
    benefit_code: str = Field(..., min_length=1, max_length=50)
    metadata: Optional[Dict[str, Any]] = None


class GetHistoryRequest(BaseModel):
    """Get history request"""
    membership_id: str = Field(..., min_length=1)
    action: Optional[PointAction] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class GetPointsBalanceRequest(BaseModel):
    """Get points balance request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = None


class ListMembershipsRequest(BaseModel):
    """List memberships request"""
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    status: Optional[MembershipStatus] = None
    tier_code: Optional[MembershipTier] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


# ====================
# Response Models
# ====================

class TierInfo(BaseModel):
    """Tier information response"""
    tier_code: MembershipTier
    tier_name: str
    point_multiplier: Decimal = Field(default=Decimal("1.0"))
    qualification_threshold: int = Field(default=0, ge=0)


class TierProgress(BaseModel):
    """Tier progress information"""
    current_tier_points: int = Field(ge=0)
    next_tier_threshold: int = Field(ge=0)
    points_to_next_tier: int = Field(ge=0)
    progress_percentage: Decimal = Field(ge=0, le=100)


class PointsBalance(BaseModel):
    """Points balance response"""
    user_id: str
    organization_id: Optional[str] = None
    points_balance: int = Field(ge=0)
    tier_points: int = Field(default=0, ge=0)
    lifetime_points: int = Field(default=0, ge=0)
    pending_points: int = Field(default=0, ge=0)
    points_expiring_soon: int = Field(default=0, ge=0)
    expiration_date: Optional[datetime] = None
    membership_id: Optional[str] = None
    tier_code: Optional[MembershipTier] = None


class MembershipResponse(BaseModel):
    """Single membership response"""
    success: bool
    message: str
    membership: Optional[Membership] = None


class EnrollMembershipResponse(BaseModel):
    """Enrollment response"""
    success: bool
    message: str
    membership: Optional[Membership] = None
    enrollment_bonus: Optional[int] = None


class EarnPointsResponse(BaseModel):
    """Earn points response"""
    success: bool
    message: str
    points_earned: int = 0
    multiplier: Decimal = Field(default=Decimal("1.0"))
    points_balance: int = 0
    tier_points: int = 0
    tier_upgraded: bool = False
    new_tier: Optional[MembershipTier] = None


class RedeemPointsResponse(BaseModel):
    """Redeem points response"""
    success: bool
    message: str
    points_redeemed: int = 0
    points_balance: int = 0
    reward_code: Optional[str] = None


class PointsBalanceResponse(BaseModel):
    """Points balance response"""
    success: bool
    message: str
    balance: Optional[PointsBalance] = None


class TierStatusResponse(BaseModel):
    """Tier status response"""
    success: bool
    message: str
    membership_id: str
    current_tier: Optional[TierInfo] = None
    tier_progress: Optional[TierProgress] = None
    benefits: List[BenefitUsage] = Field(default_factory=list)


class BenefitListResponse(BaseModel):
    """Benefits list response"""
    success: bool
    message: str
    membership_id: str
    tier_code: MembershipTier
    benefits: List[BenefitUsage] = Field(default_factory=list)


class HistoryResponse(BaseModel):
    """History response"""
    success: bool
    message: str
    membership_id: str
    history: List[MembershipHistory] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class ListMembershipsResponse(BaseModel):
    """List memberships response"""
    success: bool
    message: str
    memberships: List[Membership] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class UseBenefitResponse(BaseModel):
    """Use benefit response"""
    success: bool
    message: str
    benefit_code: str
    remaining_uses: Optional[int] = None


class MembershipStats(BaseModel):
    """Membership statistics"""
    total_memberships: int = 0
    active_memberships: int = 0
    suspended_memberships: int = 0
    expired_memberships: int = 0
    canceled_memberships: int = 0
    total_points_issued: int = 0
    total_points_redeemed: int = 0
    tier_distribution: Dict[str, int] = Field(default_factory=dict)


# ====================
# System Models
# ====================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    port: int
    version: str
    dependencies: Dict[str, str]


class ServiceInfo(BaseModel):
    """Service information"""
    service: str
    version: str
    description: str
    capabilities: List[str]


__all__ = [
    # Enums
    "MembershipStatus",
    "MembershipTier",
    "PointAction",
    "InitiatedBy",
    # Core Models
    "Membership",
    "MembershipHistory",
    "Tier",
    "TierBenefit",
    "BenefitUsage",
    # Request Models
    "EnrollMembershipRequest",
    "EarnPointsRequest",
    "RedeemPointsRequest",
    "CancelMembershipRequest",
    "SuspendMembershipRequest",
    "UseBenefitRequest",
    "GetHistoryRequest",
    "GetPointsBalanceRequest",
    "ListMembershipsRequest",
    # Response Models
    "TierInfo",
    "TierProgress",
    "PointsBalance",
    "MembershipResponse",
    "EnrollMembershipResponse",
    "EarnPointsResponse",
    "RedeemPointsResponse",
    "PointsBalanceResponse",
    "TierStatusResponse",
    "BenefitListResponse",
    "HistoryResponse",
    "ListMembershipsResponse",
    "UseBenefitResponse",
    "MembershipStats",
    # System Models
    "HealthResponse",
    "ServiceInfo",
]
