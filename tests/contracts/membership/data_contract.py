"""
Membership Service - Data Contract

Pydantic schemas, test data factory, and request builders for membership_service.
Zero hardcoded data - all test data generated through factory methods.

Reference: docs/CDD_GUIDE.md
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import secrets
import uuid


# ============================================================================
# Enum Contracts
# ============================================================================

class MembershipStatusContract(str, Enum):
    """Valid membership statuses"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELED = "canceled"


class MembershipTierContract(str, Enum):
    """Valid membership tiers"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class PointActionContract(str, Enum):
    """Valid point/membership actions"""
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


class InitiatedByContract(str, Enum):
    """Who initiated the action"""
    USER = "user"
    SYSTEM = "system"
    ADMIN = "admin"
    SERVICE = "service"


# ============================================================================
# Request Contracts (10 schemas)
# ============================================================================

class EnrollMembershipRequestContract(BaseModel):
    """Contract for membership enrollment request"""
    user_id: str = Field(..., min_length=1, description="User ID")
    organization_id: Optional[str] = Field(default=None, description="Organization ID")
    enrollment_source: Optional[str] = Field(default="api", max_length=50)
    promo_code: Optional[str] = Field(default=None, max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class EarnPointsRequestContract(BaseModel):
    """Contract for point earning request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = Field(default=None)
    points_amount: int = Field(..., gt=0, le=10_000_000)
    source: str = Field(..., min_length=1, max_length=50)
    reference_id: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        if not v or not v.strip():
            raise ValueError("source cannot be empty")
        return v.strip()


class RedeemPointsRequestContract(BaseModel):
    """Contract for point redemption request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = Field(default=None)
    points_amount: int = Field(..., gt=0, le=10_000_000)
    reward_code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class GetMembershipRequestContract(BaseModel):
    """Contract for get membership request"""
    membership_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    organization_id: Optional[str] = Field(default=None)


class CancelMembershipRequestContract(BaseModel):
    """Contract for membership cancellation request"""
    reason: Optional[str] = Field(default=None, max_length=500)
    forfeit_points: bool = Field(default=False)
    feedback: Optional[str] = Field(default=None, max_length=1000)


class SuspendMembershipRequestContract(BaseModel):
    """Contract for membership suspension request"""
    reason: str = Field(..., min_length=1, max_length=500)
    duration_days: Optional[int] = Field(default=None, ge=1, le=365)


class UseBenefitRequestContract(BaseModel):
    """Contract for benefit usage request"""
    benefit_code: str = Field(..., min_length=1, max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class GetHistoryRequestContract(BaseModel):
    """Contract for history request"""
    membership_id: str = Field(..., min_length=1)
    action: Optional[PointActionContract] = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class GetPointsBalanceRequestContract(BaseModel):
    """Contract for points balance request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = Field(default=None)


class ListMembershipsRequestContract(BaseModel):
    """Contract for list memberships request"""
    user_id: Optional[str] = Field(default=None)
    organization_id: Optional[str] = Field(default=None)
    status: Optional[MembershipStatusContract] = Field(default=None)
    tier_code: Optional[MembershipTierContract] = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


# ============================================================================
# Response Contracts (15 schemas)
# ============================================================================

class MembershipTierInfoContract(BaseModel):
    """Contract for tier information"""
    tier_code: MembershipTierContract
    tier_name: str
    point_multiplier: Decimal = Field(default=Decimal("1.0"))
    qualification_threshold: int = Field(default=0, ge=0)


class TierProgressContract(BaseModel):
    """Contract for tier progress information"""
    current_tier_points: int = Field(ge=0)
    next_tier_threshold: int = Field(ge=0)
    points_to_next_tier: int = Field(ge=0)
    progress_percentage: Decimal = Field(ge=0, le=100)


class MembershipContract(BaseModel):
    """Contract for membership data"""
    membership_id: str
    user_id: str
    organization_id: Optional[str] = None
    tier_code: MembershipTierContract
    status: MembershipStatusContract
    points_balance: int = Field(ge=0)
    tier_points: int = Field(default=0, ge=0)
    lifetime_points: int = Field(default=0, ge=0)
    pending_points: int = Field(default=0, ge=0)
    enrolled_at: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    auto_renew: bool = True
    enrollment_source: Optional[str] = None
    promo_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MembershipHistoryContract(BaseModel):
    """Contract for membership history entry"""
    history_id: str
    membership_id: str
    action: PointActionContract
    points_change: int = 0
    balance_after: Optional[int] = None
    previous_tier: Optional[str] = None
    new_tier: Optional[str] = None
    source: Optional[str] = None
    reference_id: Optional[str] = None
    reward_code: Optional[str] = None
    benefit_code: Optional[str] = None
    description: Optional[str] = None
    initiated_by: InitiatedByContract = InitiatedByContract.SYSTEM
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class PointsBalanceContract(BaseModel):
    """Contract for points balance"""
    user_id: str
    organization_id: Optional[str] = None
    points_balance: int = Field(ge=0)
    tier_points: int = Field(default=0, ge=0)
    lifetime_points: int = Field(default=0, ge=0)
    pending_points: int = Field(default=0, ge=0)
    points_expiring_soon: int = Field(default=0, ge=0)
    expiration_date: Optional[datetime] = None
    membership_id: Optional[str] = None
    tier_code: Optional[MembershipTierContract] = None


class BenefitContract(BaseModel):
    """Contract for tier benefit"""
    benefit_code: str
    benefit_name: str
    benefit_type: str
    usage_limit: Optional[int] = None
    used_count: int = Field(default=0, ge=0)
    remaining: Optional[int] = None
    is_unlimited: bool = False
    is_available: bool = True


class MembershipResponseContract(BaseModel):
    """Contract for single membership response"""
    success: bool
    message: str
    membership: Optional[MembershipContract] = None


class EnrollMembershipResponseContract(BaseModel):
    """Contract for enrollment response"""
    success: bool
    message: str
    membership: Optional[MembershipContract] = None
    enrollment_bonus: Optional[int] = None


class EarnPointsResponseContract(BaseModel):
    """Contract for earn points response"""
    success: bool
    message: str
    points_earned: int = 0
    multiplier: Decimal = Field(default=Decimal("1.0"))
    points_balance: int = 0
    tier_points: int = 0


class RedeemPointsResponseContract(BaseModel):
    """Contract for redeem points response"""
    success: bool
    message: str
    points_redeemed: int = 0
    points_balance: int = 0
    reward_code: Optional[str] = None


class PointsBalanceResponseContract(BaseModel):
    """Contract for points balance response"""
    success: bool
    message: str
    balance: Optional[PointsBalanceContract] = None


class TierStatusResponseContract(BaseModel):
    """Contract for tier status response"""
    success: bool
    message: str
    membership_id: str
    current_tier: Optional[MembershipTierInfoContract] = None
    tier_progress: Optional[TierProgressContract] = None
    benefits: List[BenefitContract] = Field(default_factory=list)


class BenefitListResponseContract(BaseModel):
    """Contract for benefits list response"""
    success: bool
    message: str
    membership_id: str
    tier_code: MembershipTierContract
    benefits: List[BenefitContract] = Field(default_factory=list)


class HistoryResponseContract(BaseModel):
    """Contract for history response"""
    success: bool
    message: str
    membership_id: str
    history: List[MembershipHistoryContract] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class ErrorResponseContract(BaseModel):
    """Contract for error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# MembershipTestDataFactory - 40+ methods (25 valid + 15 invalid)
# ============================================================================

class MembershipTestDataFactory:
    """Test data factory for membership_service - zero hardcoded data"""

    # ========================================
    # Valid ID Generators
    # ========================================

    @staticmethod
    def make_membership_id() -> str:
        """Generate valid membership ID"""
        return f"mem_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_history_id() -> str:
        """Generate valid history ID"""
        return f"hist_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_benefit_id() -> str:
        """Generate valid benefit ID"""
        return f"bnft_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_reference_id() -> str:
        """Generate valid reference ID"""
        return f"ref_{uuid.uuid4().hex[:16]}"

    # ========================================
    # Valid Value Generators
    # ========================================

    @staticmethod
    def make_tier_code() -> MembershipTierContract:
        """Generate random valid tier code"""
        tiers = list(MembershipTierContract)
        return secrets.choice(tiers)

    @staticmethod
    def make_elevated_tier_code() -> MembershipTierContract:
        """Generate elevated tier code (silver+)"""
        tiers = [MembershipTierContract.SILVER, MembershipTierContract.GOLD,
                 MembershipTierContract.PLATINUM, MembershipTierContract.DIAMOND]
        return secrets.choice(tiers)

    @staticmethod
    def make_status() -> MembershipStatusContract:
        """Generate random membership status"""
        statuses = list(MembershipStatusContract)
        return secrets.choice(statuses)

    @staticmethod
    def make_active_status() -> MembershipStatusContract:
        """Generate active or pending status"""
        return secrets.choice([MembershipStatusContract.ACTIVE, MembershipStatusContract.PENDING])

    @staticmethod
    def make_points_amount() -> int:
        """Generate random points amount (100 to 10000)"""
        return secrets.randbelow(10000) + 100

    @staticmethod
    def make_small_points_amount() -> int:
        """Generate small points amount (10 to 500)"""
        return secrets.randbelow(500) + 10

    @staticmethod
    def make_large_points_balance() -> int:
        """Generate large points balance (10000 to 100000)"""
        return secrets.randbelow(90000) + 10000

    @staticmethod
    def make_tier_points() -> int:
        """Generate tier points (0 to 50000)"""
        return secrets.randbelow(50000)

    @staticmethod
    def make_point_multiplier() -> Decimal:
        """Generate point multiplier based on tier"""
        multipliers = [Decimal("1.0"), Decimal("1.25"), Decimal("1.5"), Decimal("2.0"), Decimal("3.0")]
        return secrets.choice(multipliers)

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_enrolled_at() -> datetime:
        """Generate enrollment date (past 1-365 days)"""
        days_ago = secrets.randbelow(365) + 1
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    @staticmethod
    def make_expiration_date() -> datetime:
        """Generate expiration date (future 1-365 days)"""
        days_future = secrets.randbelow(365) + 1
        return datetime.now(timezone.utc) + timedelta(days=days_future)

    @staticmethod
    def make_point_source() -> str:
        """Generate random point source"""
        sources = ['order_completed', 'signup_bonus', 'referral', 'promotion', 'activity_bonus', 'manual_adjustment']
        return secrets.choice(sources)

    @staticmethod
    def make_reward_code() -> str:
        """Generate reward code"""
        codes = ['FREE_SHIPPING', 'DISCOUNT_10', 'EXCLUSIVE_ACCESS', 'PRIORITY_SUPPORT', 'EARLY_BIRD']
        return secrets.choice(codes)

    @staticmethod
    def make_benefit_code() -> str:
        """Generate benefit code"""
        codes = ['PRIORITY_SUPPORT', 'FREE_SHIPPING', 'EARLY_ACCESS', 'EXCLUSIVE_CONTENT', 'VIP_CONCIERGE']
        return secrets.choice(codes)

    @staticmethod
    def make_enrollment_source() -> str:
        """Generate enrollment source"""
        sources = ['web_signup', 'mobile_app', 'referral', 'promotion', 'customer_service']
        return secrets.choice(sources)

    @staticmethod
    def make_promo_code() -> str:
        """Generate promo code"""
        return f"PROMO{secrets.token_hex(4).upper()}"

    @staticmethod
    def make_cancellation_reason() -> str:
        """Generate cancellation reason"""
        reasons = ['Not using enough', 'Too expensive', 'Found alternative', 'Other']
        return secrets.choice(reasons)

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate sample metadata"""
        return {
            "source": "api",
            "campaign": f"camp_{secrets.token_hex(4)}",
            "ref_code": secrets.token_hex(8)
        }

    # ========================================
    # Valid Request Generators
    # ========================================

    @staticmethod
    def make_enroll_membership_request() -> EnrollMembershipRequestContract:
        """Generate valid enrollment request"""
        return EnrollMembershipRequestContract(
            user_id=MembershipTestDataFactory.make_user_id(),
            enrollment_source=MembershipTestDataFactory.make_enrollment_source()
        )

    @staticmethod
    def make_enroll_with_promo_request() -> EnrollMembershipRequestContract:
        """Generate enrollment request with promo code"""
        return EnrollMembershipRequestContract(
            user_id=MembershipTestDataFactory.make_user_id(),
            enrollment_source='promotion',
            promo_code=MembershipTestDataFactory.make_promo_code()
        )

    @staticmethod
    def make_earn_points_request() -> EarnPointsRequestContract:
        """Generate valid earn points request"""
        return EarnPointsRequestContract(
            user_id=MembershipTestDataFactory.make_user_id(),
            points_amount=MembershipTestDataFactory.make_points_amount(),
            source=MembershipTestDataFactory.make_point_source(),
            reference_id=MembershipTestDataFactory.make_reference_id()
        )

    @staticmethod
    def make_redeem_points_request() -> RedeemPointsRequestContract:
        """Generate valid redeem points request"""
        return RedeemPointsRequestContract(
            user_id=MembershipTestDataFactory.make_user_id(),
            points_amount=MembershipTestDataFactory.make_small_points_amount(),
            reward_code=MembershipTestDataFactory.make_reward_code()
        )

    @staticmethod
    def make_cancel_membership_request() -> CancelMembershipRequestContract:
        """Generate valid cancel membership request"""
        return CancelMembershipRequestContract(
            reason=MembershipTestDataFactory.make_cancellation_reason(),
            forfeit_points=False
        )

    @staticmethod
    def make_use_benefit_request() -> UseBenefitRequestContract:
        """Generate valid use benefit request"""
        return UseBenefitRequestContract(
            benefit_code=MembershipTestDataFactory.make_benefit_code()
        )

    # ========================================
    # Valid Response/Entity Generators
    # ========================================

    @staticmethod
    def make_membership() -> MembershipContract:
        """Generate valid membership entity"""
        now = MembershipTestDataFactory.make_timestamp()
        points = MembershipTestDataFactory.make_large_points_balance()
        tier_points = MembershipTestDataFactory.make_tier_points()
        return MembershipContract(
            membership_id=MembershipTestDataFactory.make_membership_id(),
            user_id=MembershipTestDataFactory.make_user_id(),
            tier_code=MembershipTierContract.BRONZE,
            status=MembershipStatusContract.ACTIVE,
            points_balance=points,
            tier_points=tier_points,
            lifetime_points=points + secrets.randbelow(10000),
            enrolled_at=MembershipTestDataFactory.make_enrolled_at(),
            expiration_date=MembershipTestDataFactory.make_expiration_date(),
            created_at=now,
            updated_at=now
        )

    @staticmethod
    def make_elevated_membership() -> MembershipContract:
        """Generate membership with elevated tier"""
        membership = MembershipTestDataFactory.make_membership()
        membership.tier_code = MembershipTestDataFactory.make_elevated_tier_code()
        membership.tier_points = 25000 + secrets.randbelow(50000)
        return membership

    @staticmethod
    def make_membership_history() -> MembershipHistoryContract:
        """Generate membership history entry"""
        return MembershipHistoryContract(
            history_id=MembershipTestDataFactory.make_history_id(),
            membership_id=MembershipTestDataFactory.make_membership_id(),
            action=PointActionContract.POINTS_EARNED,
            points_change=MembershipTestDataFactory.make_points_amount(),
            balance_after=MembershipTestDataFactory.make_large_points_balance(),
            source=MembershipTestDataFactory.make_point_source(),
            initiated_by=InitiatedByContract.SYSTEM,
            created_at=MembershipTestDataFactory.make_timestamp()
        )

    @staticmethod
    def make_tier_info() -> MembershipTierInfoContract:
        """Generate tier info"""
        tier = MembershipTestDataFactory.make_tier_code()
        multipliers = {
            MembershipTierContract.BRONZE: Decimal("1.0"),
            MembershipTierContract.SILVER: Decimal("1.25"),
            MembershipTierContract.GOLD: Decimal("1.5"),
            MembershipTierContract.PLATINUM: Decimal("2.0"),
            MembershipTierContract.DIAMOND: Decimal("3.0"),
        }
        thresholds = {
            MembershipTierContract.BRONZE: 0,
            MembershipTierContract.SILVER: 5000,
            MembershipTierContract.GOLD: 20000,
            MembershipTierContract.PLATINUM: 50000,
            MembershipTierContract.DIAMOND: 100000,
        }
        return MembershipTierInfoContract(
            tier_code=tier,
            tier_name=tier.value.title(),
            point_multiplier=multipliers[tier],
            qualification_threshold=thresholds[tier]
        )

    @staticmethod
    def make_benefit() -> BenefitContract:
        """Generate benefit"""
        return BenefitContract(
            benefit_code=MembershipTestDataFactory.make_benefit_code(),
            benefit_name="Priority Support",
            benefit_type="service",
            usage_limit=None,
            is_unlimited=True,
            is_available=True
        )

    @staticmethod
    def make_points_balance() -> PointsBalanceContract:
        """Generate points balance"""
        points = MembershipTestDataFactory.make_large_points_balance()
        return PointsBalanceContract(
            user_id=MembershipTestDataFactory.make_user_id(),
            points_balance=points,
            tier_points=MembershipTestDataFactory.make_tier_points(),
            lifetime_points=points + secrets.randbelow(20000),
            membership_id=MembershipTestDataFactory.make_membership_id(),
            tier_code=MembershipTierContract.SILVER
        )

    @staticmethod
    def make_success_response() -> MembershipResponseContract:
        """Generate success response"""
        return MembershipResponseContract(
            success=True,
            message="Operation successful",
            membership=MembershipTestDataFactory.make_membership()
        )

    @staticmethod
    def make_earn_points_response() -> EarnPointsResponseContract:
        """Generate earn points response"""
        points = MembershipTestDataFactory.make_points_amount()
        multiplier = Decimal("1.25")
        return EarnPointsResponseContract(
            success=True,
            message="Points earned successfully",
            points_earned=int(points * multiplier),
            multiplier=multiplier,
            points_balance=MembershipTestDataFactory.make_large_points_balance(),
            tier_points=MembershipTestDataFactory.make_tier_points()
        )

    # ========================================
    # Invalid Data Generators (15+ methods)
    # ========================================

    @staticmethod
    def make_empty_user_id() -> str:
        """Generate empty user ID (invalid)"""
        return ""

    @staticmethod
    def make_whitespace_user_id() -> str:
        """Generate whitespace user ID (invalid)"""
        return "   "

    @staticmethod
    def make_invalid_tier_code() -> str:
        """Generate invalid tier code"""
        return f"invalid_tier_{secrets.token_hex(4)}"

    @staticmethod
    def make_negative_points() -> int:
        """Generate negative points amount (invalid)"""
        return -1000

    @staticmethod
    def make_zero_points() -> int:
        """Generate zero points (invalid for earning)"""
        return 0

    @staticmethod
    def make_excessive_points() -> int:
        """Generate excessive points amount (invalid)"""
        return 100_000_000  # 100 million

    @staticmethod
    def make_invalid_status() -> str:
        """Generate invalid membership status"""
        return "invalid_status"

    @staticmethod
    def make_empty_source() -> str:
        """Generate empty source (invalid)"""
        return ""

    @staticmethod
    def make_empty_reward_code() -> str:
        """Generate empty reward code (invalid)"""
        return ""

    @staticmethod
    def make_nonexistent_membership_id() -> str:
        """Generate membership ID that doesn't exist"""
        return f"mem_nonexistent_{secrets.token_hex(8)}"

    @staticmethod
    def make_malformed_membership_id() -> str:
        """Generate malformed membership ID"""
        return "not_a_valid_id"

    @staticmethod
    def make_invalid_page() -> int:
        """Generate invalid page number"""
        return 0

    @staticmethod
    def make_invalid_page_size() -> int:
        """Generate invalid page size"""
        return 1000

    @staticmethod
    def make_past_expiration_date() -> datetime:
        """Generate past expiration date (expired)"""
        return datetime.now(timezone.utc) - timedelta(days=30)

    @staticmethod
    def make_empty_benefit_code() -> str:
        """Generate empty benefit code (invalid)"""
        return ""


# ============================================================================
# Request Builders (3 builders)
# ============================================================================

class EnrollMembershipRequestBuilder:
    """Builder for enrollment requests"""

    def __init__(self):
        self._user_id = MembershipTestDataFactory.make_user_id()
        self._organization_id: Optional[str] = None
        self._enrollment_source = 'api'
        self._promo_code: Optional[str] = None
        self._metadata: Optional[Dict[str, Any]] = None

    def with_user_id(self, user_id: str) -> 'EnrollMembershipRequestBuilder':
        self._user_id = user_id
        return self

    def with_organization_id(self, org_id: str) -> 'EnrollMembershipRequestBuilder':
        self._organization_id = org_id
        return self

    def with_enrollment_source(self, source: str) -> 'EnrollMembershipRequestBuilder':
        self._enrollment_source = source
        return self

    def with_promo_code(self, code: str) -> 'EnrollMembershipRequestBuilder':
        self._promo_code = code
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'EnrollMembershipRequestBuilder':
        self._metadata = metadata
        return self

    def build(self) -> EnrollMembershipRequestContract:
        return EnrollMembershipRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            enrollment_source=self._enrollment_source,
            promo_code=self._promo_code,
            metadata=self._metadata
        )


class EarnPointsRequestBuilder:
    """Builder for earn points requests"""

    def __init__(self):
        self._user_id = MembershipTestDataFactory.make_user_id()
        self._organization_id: Optional[str] = None
        self._points_amount = MembershipTestDataFactory.make_points_amount()
        self._source = 'order_completed'
        self._reference_id: Optional[str] = None
        self._description: Optional[str] = None
        self._metadata: Optional[Dict[str, Any]] = None

    def with_user_id(self, user_id: str) -> 'EarnPointsRequestBuilder':
        self._user_id = user_id
        return self

    def with_organization_id(self, org_id: str) -> 'EarnPointsRequestBuilder':
        self._organization_id = org_id
        return self

    def with_points(self, points: int) -> 'EarnPointsRequestBuilder':
        self._points_amount = points
        return self

    def with_source(self, source: str) -> 'EarnPointsRequestBuilder':
        self._source = source
        return self

    def with_reference_id(self, ref_id: str) -> 'EarnPointsRequestBuilder':
        self._reference_id = ref_id
        return self

    def with_description(self, desc: str) -> 'EarnPointsRequestBuilder':
        self._description = desc
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'EarnPointsRequestBuilder':
        self._metadata = metadata
        return self

    def build(self) -> EarnPointsRequestContract:
        return EarnPointsRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            points_amount=self._points_amount,
            source=self._source,
            reference_id=self._reference_id,
            description=self._description,
            metadata=self._metadata
        )


class RedeemPointsRequestBuilder:
    """Builder for redeem points requests"""

    def __init__(self):
        self._user_id = MembershipTestDataFactory.make_user_id()
        self._organization_id: Optional[str] = None
        self._points_amount = MembershipTestDataFactory.make_small_points_amount()
        self._reward_code = 'FREE_SHIPPING'
        self._description: Optional[str] = None
        self._metadata: Optional[Dict[str, Any]] = None

    def with_user_id(self, user_id: str) -> 'RedeemPointsRequestBuilder':
        self._user_id = user_id
        return self

    def with_organization_id(self, org_id: str) -> 'RedeemPointsRequestBuilder':
        self._organization_id = org_id
        return self

    def with_points(self, points: int) -> 'RedeemPointsRequestBuilder':
        self._points_amount = points
        return self

    def with_reward_code(self, code: str) -> 'RedeemPointsRequestBuilder':
        self._reward_code = code
        return self

    def with_description(self, desc: str) -> 'RedeemPointsRequestBuilder':
        self._description = desc
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'RedeemPointsRequestBuilder':
        self._metadata = metadata
        return self

    def build(self) -> RedeemPointsRequestContract:
        return RedeemPointsRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            points_amount=self._points_amount,
            reward_code=self._reward_code,
            description=self._description,
            metadata=self._metadata
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "MembershipStatusContract",
    "MembershipTierContract",
    "PointActionContract",
    "InitiatedByContract",
    # Request Contracts
    "EnrollMembershipRequestContract",
    "EarnPointsRequestContract",
    "RedeemPointsRequestContract",
    "GetMembershipRequestContract",
    "CancelMembershipRequestContract",
    "SuspendMembershipRequestContract",
    "UseBenefitRequestContract",
    "GetHistoryRequestContract",
    "GetPointsBalanceRequestContract",
    "ListMembershipsRequestContract",
    # Response/Entity Contracts
    "MembershipContract",
    "MembershipTierInfoContract",
    "MembershipHistoryContract",
    "TierProgressContract",
    "PointsBalanceContract",
    "BenefitContract",
    "MembershipResponseContract",
    "EnrollMembershipResponseContract",
    "EarnPointsResponseContract",
    "RedeemPointsResponseContract",
    "PointsBalanceResponseContract",
    "TierStatusResponseContract",
    "BenefitListResponseContract",
    "HistoryResponseContract",
    "ErrorResponseContract",
    # Factory
    "MembershipTestDataFactory",
    # Builders
    "EnrollMembershipRequestBuilder",
    "EarnPointsRequestBuilder",
    "RedeemPointsRequestBuilder",
]
