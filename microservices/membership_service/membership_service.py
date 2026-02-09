"""
Membership Service Business Logic

Core business logic for membership enrollment, points, tiers, and benefits.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from .protocols import (
    MembershipRepositoryProtocol,
    EventBusProtocol,
    MembershipNotFoundError,
    DuplicateMembershipError,
    InsufficientPointsError,
    InvalidStatusTransitionError,
    MembershipSuspendedError,
    MembershipExpiredError,
    BenefitNotAvailableError,
    BenefitUsageLimitExceededError,
)
from .models import (
    Membership,
    MembershipHistory,
    MembershipStatus,
    MembershipTier,
    PointAction,
    InitiatedBy,
    Tier,
    TierInfo,
    TierProgress,
    BenefitUsage,
    PointsBalance,
    EnrollMembershipRequest,
    EnrollMembershipResponse,
    EarnPointsRequest,
    EarnPointsResponse,
    RedeemPointsRequest,
    RedeemPointsResponse,
    CancelMembershipRequest,
    SuspendMembershipRequest,
    UseBenefitRequest,
    UseBenefitResponse,
    PointsBalanceResponse,
    TierStatusResponse,
    BenefitListResponse,
    HistoryResponse,
    ListMembershipsResponse,
    MembershipResponse,
    MembershipStats,
)

logger = logging.getLogger(__name__)


# Tier thresholds and multipliers
TIER_CONFIG = {
    MembershipTier.BRONZE: {"threshold": 0, "multiplier": Decimal("1.0")},
    MembershipTier.SILVER: {"threshold": 5000, "multiplier": Decimal("1.25")},
    MembershipTier.GOLD: {"threshold": 20000, "multiplier": Decimal("1.5")},
    MembershipTier.PLATINUM: {"threshold": 50000, "multiplier": Decimal("2.0")},
    MembershipTier.DIAMOND: {"threshold": 100000, "multiplier": Decimal("3.0")},
}

TIER_ORDER = [
    MembershipTier.BRONZE,
    MembershipTier.SILVER,
    MembershipTier.GOLD,
    MembershipTier.PLATINUM,
    MembershipTier.DIAMOND,
]


class MembershipService:
    """Membership service core business logic"""

    def __init__(
        self,
        repository: MembershipRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ):
        """
        Initialize membership service with injected dependencies

        Args:
            repository: Repository for data access
            event_bus: Optional event bus for publishing events
        """
        self.repository = repository
        self.event_bus = event_bus

        logger.info("MembershipService initialized with dependency injection")

    async def initialize(self):
        """Initialize service (load caches, etc.)"""
        await self.repository.initialize()
        logger.info("MembershipService initialized")

    # ====================
    # Enrollment
    # ====================

    async def enroll_membership(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        enrollment_source: Optional[str] = None,
        promo_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EnrollMembershipResponse:
        """Enroll a new membership"""
        try:
            # Check for existing active membership
            existing = await self.repository.get_membership_by_user(
                user_id=user_id,
                organization_id=organization_id,
                active_only=True
            )

            if existing:
                return EnrollMembershipResponse(
                    success=False,
                    message="User already has active membership"
                )

            # Calculate enrollment bonus
            enrollment_bonus = self._calculate_enrollment_bonus(promo_code)

            # Create membership
            membership = await self.repository.create_membership(
                user_id=user_id,
                tier_code=MembershipTier.BRONZE.value,
                points_balance=enrollment_bonus,
                organization_id=organization_id,
                enrollment_source=enrollment_source or "api",
                promo_code=promo_code,
                metadata=metadata or {}
            )

            # Record enrollment history
            await self.repository.add_history(
                membership_id=membership.membership_id,
                action=PointAction.ENROLLED,
                points_change=enrollment_bonus,
                balance_after=enrollment_bonus,
                source=enrollment_source or "api",
                initiated_by=InitiatedBy.USER.value,
                metadata={"promo_code": promo_code} if promo_code else {}
            )

            # Publish enrollment event
            await self._publish_event(
                "membership.enrolled",
                {
                    "membership_id": membership.membership_id,
                    "user_id": user_id,
                    "tier_code": membership.tier_code.value,
                    "enrollment_bonus": enrollment_bonus,
                    "enrolled_at": membership.enrolled_at.isoformat() if membership.enrolled_at else None
                }
            )

            return EnrollMembershipResponse(
                success=True,
                message="Membership enrolled successfully",
                membership=membership,
                enrollment_bonus=enrollment_bonus
            )

        except Exception as e:
            logger.error(f"Error enrolling membership: {e}")
            return EnrollMembershipResponse(
                success=False,
                message=f"Error enrolling membership: {str(e)}"
            )

    # ====================
    # Points Management
    # ====================

    async def earn_points(
        self,
        user_id: str,
        points_amount: int,
        source: str,
        organization_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EarnPointsResponse:
        """Earn points"""
        try:
            # Get membership (include all statuses to provide specific error messages)
            membership = await self.repository.get_membership_by_user(
                user_id=user_id,
                organization_id=organization_id,
                active_only=False
            )

            if not membership:
                return EarnPointsResponse(
                    success=False,
                    message="No membership found"
                )

            # Check membership status
            if membership.status == MembershipStatus.SUSPENDED:
                return EarnPointsResponse(
                    success=False,
                    message="Membership is suspended"
                )

            if membership.status == MembershipStatus.EXPIRED:
                return EarnPointsResponse(
                    success=False,
                    message="Membership is expired"
                )

            # Get tier multiplier
            multiplier = TIER_CONFIG.get(membership.tier_code, {}).get("multiplier", Decimal("1.0"))

            # Calculate final points with multiplier
            final_points = int(Decimal(str(points_amount)) * multiplier)

            # Base points go to tier_points (before multiplier)
            base_points = points_amount

            # Add points
            old_tier = membership.tier_code
            updated_membership = await self.repository.add_points(
                membership_id=membership.membership_id,
                points=final_points,
                tier_points=base_points,
                source=source,
                reference_id=reference_id
            )

            # Record history
            await self.repository.add_history(
                membership_id=membership.membership_id,
                action=PointAction.POINTS_EARNED,
                points_change=final_points,
                balance_after=updated_membership.points_balance,
                source=source,
                reference_id=reference_id,
                description=description,
                initiated_by=InitiatedBy.SYSTEM.value,
                metadata={"base_points": base_points, "multiplier": str(multiplier), **(metadata or {})}
            )

            # Check for tier upgrade
            tier_upgraded = False
            new_tier = None
            new_tier_code = self._calculate_tier(updated_membership.tier_points)

            if new_tier_code != old_tier:
                tier_upgraded = True
                new_tier = new_tier_code
                await self._upgrade_tier(updated_membership, old_tier, new_tier_code)

            # Publish points earned event
            await self._publish_event(
                "points.earned",
                {
                    "membership_id": membership.membership_id,
                    "user_id": user_id,
                    "points_earned": final_points,
                    "multiplier": float(multiplier),
                    "source": source,
                    "balance_after": updated_membership.points_balance,
                    "tier_upgraded": tier_upgraded,
                    "new_tier": new_tier.value if new_tier else None
                }
            )

            return EarnPointsResponse(
                success=True,
                message="Points earned successfully",
                points_earned=final_points,
                multiplier=multiplier,
                points_balance=updated_membership.points_balance,
                tier_points=updated_membership.tier_points,
                tier_upgraded=tier_upgraded,
                new_tier=new_tier
            )

        except Exception as e:
            logger.error(f"Error earning points: {e}")
            return EarnPointsResponse(
                success=False,
                message=f"Error earning points: {str(e)}"
            )

    async def redeem_points(
        self,
        user_id: str,
        points_amount: int,
        reward_code: str,
        organization_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RedeemPointsResponse:
        """Redeem points"""
        try:
            # Get membership (include all statuses to provide specific error messages)
            membership = await self.repository.get_membership_by_user(
                user_id=user_id,
                organization_id=organization_id,
                active_only=False
            )

            if not membership:
                return RedeemPointsResponse(
                    success=False,
                    message="No membership found"
                )

            # Check membership status
            if membership.status == MembershipStatus.SUSPENDED:
                return RedeemPointsResponse(
                    success=False,
                    message="Membership is suspended"
                )

            if membership.status == MembershipStatus.EXPIRED:
                return RedeemPointsResponse(
                    success=False,
                    message="Membership is expired"
                )

            # Check sufficient points
            if membership.points_balance < points_amount:
                return RedeemPointsResponse(
                    success=False,
                    message=f"Insufficient points. Available: {membership.points_balance}, Requested: {points_amount}"
                )

            # Deduct points
            updated_membership = await self.repository.deduct_points(
                membership_id=membership.membership_id,
                points=points_amount,
                reward_code=reward_code,
                description=description
            )

            # Record history
            await self.repository.add_history(
                membership_id=membership.membership_id,
                action=PointAction.POINTS_REDEEMED,
                points_change=-points_amount,
                balance_after=updated_membership.points_balance,
                reward_code=reward_code,
                description=description,
                initiated_by=InitiatedBy.USER.value,
                metadata=metadata or {}
            )

            # Publish points redeemed event
            await self._publish_event(
                "points.redeemed",
                {
                    "membership_id": membership.membership_id,
                    "user_id": user_id,
                    "points_redeemed": points_amount,
                    "reward_code": reward_code,
                    "balance_after": updated_membership.points_balance
                }
            )

            return RedeemPointsResponse(
                success=True,
                message="Points redeemed successfully",
                points_redeemed=points_amount,
                points_balance=updated_membership.points_balance,
                reward_code=reward_code
            )

        except Exception as e:
            logger.error(f"Error redeeming points: {e}")
            return RedeemPointsResponse(
                success=False,
                message=f"Error redeeming points: {str(e)}"
            )

    async def get_points_balance(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> PointsBalanceResponse:
        """Get points balance"""
        try:
            membership = await self.repository.get_membership_by_user(
                user_id=user_id,
                organization_id=organization_id,
                active_only=True
            )

            if not membership:
                return PointsBalanceResponse(
                    success=False,
                    message="No active membership found",
                    balance=None
                )

            balance = PointsBalance(
                user_id=user_id,
                organization_id=organization_id,
                points_balance=membership.points_balance,
                tier_points=membership.tier_points,
                lifetime_points=membership.lifetime_points,
                pending_points=membership.pending_points,
                points_expiring_soon=0,  # TODO: Calculate expiring points
                expiration_date=membership.expiration_date,
                membership_id=membership.membership_id,
                tier_code=membership.tier_code
            )

            return PointsBalanceResponse(
                success=True,
                message="Points balance retrieved",
                balance=balance
            )

        except Exception as e:
            logger.error(f"Error getting points balance: {e}")
            return PointsBalanceResponse(
                success=False,
                message=f"Error getting points balance: {str(e)}",
                balance=None
            )

    # ====================
    # Membership Management
    # ====================

    async def get_membership(self, membership_id: str) -> MembershipResponse:
        """Get membership by ID"""
        try:
            membership = await self.repository.get_membership(membership_id)

            if not membership:
                return MembershipResponse(
                    success=False,
                    message="Membership not found"
                )

            return MembershipResponse(
                success=True,
                message="Membership retrieved",
                membership=membership
            )

        except Exception as e:
            logger.error(f"Error getting membership: {e}")
            return MembershipResponse(
                success=False,
                message=f"Error getting membership: {str(e)}"
            )

    async def get_membership_by_user(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> MembershipResponse:
        """Get membership by user ID"""
        try:
            membership = await self.repository.get_membership_by_user(
                user_id=user_id,
                organization_id=organization_id,
                active_only=False
            )

            if not membership:
                return MembershipResponse(
                    success=False,
                    message="Membership not found"
                )

            return MembershipResponse(
                success=True,
                message="Membership retrieved",
                membership=membership
            )

        except Exception as e:
            logger.error(f"Error getting membership by user: {e}")
            return MembershipResponse(
                success=False,
                message=f"Error getting membership: {str(e)}"
            )

    async def list_memberships(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[MembershipStatus] = None,
        tier_code: Optional[MembershipTier] = None,
        page: int = 1,
        page_size: int = 50
    ) -> ListMembershipsResponse:
        """List memberships"""
        try:
            offset = (page - 1) * page_size

            memberships = await self.repository.list_memberships(
                user_id=user_id,
                organization_id=organization_id,
                status=status,
                tier_code=tier_code,
                limit=page_size,
                offset=offset
            )

            total = await self.repository.count_memberships(
                user_id=user_id,
                organization_id=organization_id,
                status=status,
                tier_code=tier_code
            )

            return ListMembershipsResponse(
                success=True,
                message="Memberships retrieved",
                memberships=memberships,
                total=total,
                page=page,
                page_size=page_size
            )

        except Exception as e:
            logger.error(f"Error listing memberships: {e}")
            return ListMembershipsResponse(
                success=False,
                message=f"Error listing memberships: {str(e)}"
            )

    async def cancel_membership(
        self,
        membership_id: str,
        reason: Optional[str] = None,
        forfeit_points: bool = False,
        feedback: Optional[str] = None
    ) -> MembershipResponse:
        """Cancel membership"""
        try:
            membership = await self.repository.get_membership(membership_id)

            if not membership:
                return MembershipResponse(
                    success=False,
                    message="Membership not found"
                )

            if membership.status == MembershipStatus.CANCELED:
                return MembershipResponse(
                    success=False,
                    message="Membership already canceled"
                )

            # Update status
            updated_membership = await self.repository.update_status(
                membership_id=membership_id,
                status=MembershipStatus.CANCELED,
                reason=reason
            )

            # Record history
            await self.repository.add_history(
                membership_id=membership_id,
                action=PointAction.CANCELED,
                points_change=-membership.points_balance if forfeit_points else 0,
                balance_after=0 if forfeit_points else membership.points_balance,
                description=reason,
                initiated_by=InitiatedBy.USER.value,
                metadata={"feedback": feedback} if feedback else {}
            )

            # Publish cancellation event
            await self._publish_event(
                "membership.canceled",
                {
                    "membership_id": membership_id,
                    "user_id": membership.user_id,
                    "reason": reason,
                    "points_forfeited": membership.points_balance if forfeit_points else 0
                }
            )

            return MembershipResponse(
                success=True,
                message="Membership canceled successfully",
                membership=updated_membership
            )

        except Exception as e:
            logger.error(f"Error canceling membership: {e}")
            return MembershipResponse(
                success=False,
                message=f"Error canceling membership: {str(e)}"
            )

    async def suspend_membership(
        self,
        membership_id: str,
        reason: str,
        duration_days: Optional[int] = None
    ) -> MembershipResponse:
        """Suspend membership"""
        try:
            membership = await self.repository.get_membership(membership_id)

            if not membership:
                return MembershipResponse(
                    success=False,
                    message="Membership not found"
                )

            if membership.status != MembershipStatus.ACTIVE:
                return MembershipResponse(
                    success=False,
                    message=f"Cannot suspend membership with status: {membership.status.value}"
                )

            # Update status
            updated_membership = await self.repository.update_status(
                membership_id=membership_id,
                status=MembershipStatus.SUSPENDED,
                reason=reason
            )

            # Record history
            await self.repository.add_history(
                membership_id=membership_id,
                action=PointAction.SUSPENDED,
                description=reason,
                initiated_by=InitiatedBy.ADMIN.value,
                metadata={"duration_days": duration_days} if duration_days else {}
            )

            # Publish suspension event
            await self._publish_event(
                "membership.suspended",
                {
                    "membership_id": membership_id,
                    "user_id": membership.user_id,
                    "reason": reason,
                    "duration_days": duration_days
                }
            )

            return MembershipResponse(
                success=True,
                message="Membership suspended successfully",
                membership=updated_membership
            )

        except Exception as e:
            logger.error(f"Error suspending membership: {e}")
            return MembershipResponse(
                success=False,
                message=f"Error suspending membership: {str(e)}"
            )

    async def reactivate_membership(self, membership_id: str) -> MembershipResponse:
        """Reactivate suspended membership"""
        try:
            membership = await self.repository.get_membership(membership_id)

            if not membership:
                return MembershipResponse(
                    success=False,
                    message="Membership not found"
                )

            if membership.status != MembershipStatus.SUSPENDED:
                return MembershipResponse(
                    success=False,
                    message=f"Cannot reactivate membership with status: {membership.status.value}"
                )

            # Update status
            updated_membership = await self.repository.update_status(
                membership_id=membership_id,
                status=MembershipStatus.ACTIVE,
                reason="Reactivated"
            )

            # Record history
            await self.repository.add_history(
                membership_id=membership_id,
                action=PointAction.REACTIVATED,
                initiated_by=InitiatedBy.ADMIN.value
            )

            # Publish reactivation event
            await self._publish_event(
                "membership.reactivated",
                {
                    "membership_id": membership_id,
                    "user_id": membership.user_id
                }
            )

            return MembershipResponse(
                success=True,
                message="Membership reactivated successfully",
                membership=updated_membership
            )

        except Exception as e:
            logger.error(f"Error reactivating membership: {e}")
            return MembershipResponse(
                success=False,
                message=f"Error reactivating membership: {str(e)}"
            )

    # ====================
    # Tier Management
    # ====================

    async def get_tier_status(self, membership_id: str) -> TierStatusResponse:
        """Get tier status and progress"""
        try:
            membership = await self.repository.get_membership(membership_id)

            if not membership:
                return TierStatusResponse(
                    success=False,
                    message="Membership not found",
                    membership_id=membership_id
                )

            # Get current tier info
            tier_config = TIER_CONFIG.get(membership.tier_code, {})
            current_tier = TierInfo(
                tier_code=membership.tier_code,
                tier_name=membership.tier_code.value.title(),
                point_multiplier=tier_config.get("multiplier", Decimal("1.0")),
                qualification_threshold=tier_config.get("threshold", 0)
            )

            # Calculate tier progress
            tier_progress = self._calculate_tier_progress(membership)

            # Get benefits
            benefits = await self._get_membership_benefits(membership)

            return TierStatusResponse(
                success=True,
                message="Tier status retrieved",
                membership_id=membership_id,
                current_tier=current_tier,
                tier_progress=tier_progress,
                benefits=benefits
            )

        except Exception as e:
            logger.error(f"Error getting tier status: {e}")
            return TierStatusResponse(
                success=False,
                message=f"Error getting tier status: {str(e)}",
                membership_id=membership_id
            )

    # ====================
    # Benefits Management
    # ====================

    async def get_benefits(self, membership_id: str) -> BenefitListResponse:
        """Get available benefits"""
        try:
            membership = await self.repository.get_membership(membership_id)

            if not membership:
                return BenefitListResponse(
                    success=False,
                    message="Membership not found",
                    membership_id=membership_id,
                    tier_code=MembershipTier.BRONZE
                )

            benefits = await self._get_membership_benefits(membership)

            return BenefitListResponse(
                success=True,
                message="Benefits retrieved",
                membership_id=membership_id,
                tier_code=membership.tier_code,
                benefits=benefits
            )

        except Exception as e:
            logger.error(f"Error getting benefits: {e}")
            return BenefitListResponse(
                success=False,
                message=f"Error getting benefits: {str(e)}",
                membership_id=membership_id,
                tier_code=MembershipTier.BRONZE
            )

    async def use_benefit(
        self,
        membership_id: str,
        benefit_code: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UseBenefitResponse:
        """Use a benefit"""
        try:
            membership = await self.repository.get_membership(membership_id)

            if not membership:
                return UseBenefitResponse(
                    success=False,
                    message="Membership not found",
                    benefit_code=benefit_code
                )

            if membership.status != MembershipStatus.ACTIVE:
                return UseBenefitResponse(
                    success=False,
                    message=f"Cannot use benefit with membership status: {membership.status.value}",
                    benefit_code=benefit_code
                )

            # Get tier benefits
            tier_benefits = await self.repository.get_tier_benefits(membership.tier_code.value)
            benefit = next((b for b in tier_benefits if b.benefit_code == benefit_code), None)

            if not benefit:
                return UseBenefitResponse(
                    success=False,
                    message="Benefit not available at your tier",
                    benefit_code=benefit_code
                )

            # Check usage limit
            if not benefit.is_unlimited and benefit.usage_limit:
                usage_count = await self.repository.get_benefit_usage(
                    membership_id=membership_id,
                    benefit_code=benefit_code
                )
                if usage_count >= benefit.usage_limit:
                    return UseBenefitResponse(
                        success=False,
                        message="Benefit usage limit exceeded",
                        benefit_code=benefit_code,
                        remaining_uses=0
                    )

            # Record benefit usage
            await self.repository.record_benefit_usage(
                membership_id=membership_id,
                benefit_code=benefit_code
            )

            # Calculate remaining uses
            remaining_uses = None
            if not benefit.is_unlimited and benefit.usage_limit:
                usage_count = await self.repository.get_benefit_usage(
                    membership_id=membership_id,
                    benefit_code=benefit_code
                )
                remaining_uses = max(0, benefit.usage_limit - usage_count)

            # Publish benefit used event
            await self._publish_event(
                "benefit.used",
                {
                    "membership_id": membership_id,
                    "user_id": membership.user_id,
                    "benefit_code": benefit_code
                }
            )

            return UseBenefitResponse(
                success=True,
                message="Benefit used successfully",
                benefit_code=benefit_code,
                remaining_uses=remaining_uses
            )

        except Exception as e:
            logger.error(f"Error using benefit: {e}")
            return UseBenefitResponse(
                success=False,
                message=f"Error using benefit: {str(e)}",
                benefit_code=benefit_code
            )

    # ====================
    # History
    # ====================

    async def get_history(
        self,
        membership_id: str,
        action: Optional[PointAction] = None,
        page: int = 1,
        page_size: int = 50
    ) -> HistoryResponse:
        """Get membership history"""
        try:
            offset = (page - 1) * page_size

            history = await self.repository.get_history(
                membership_id=membership_id,
                limit=page_size,
                offset=offset,
                action=action
            )

            total = await self.repository.count_history(
                membership_id=membership_id,
                action=action
            )

            return HistoryResponse(
                success=True,
                message="History retrieved",
                membership_id=membership_id,
                history=history,
                total=total,
                page=page,
                page_size=page_size
            )

        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return HistoryResponse(
                success=False,
                message=f"Error getting history: {str(e)}",
                membership_id=membership_id
            )

    # ====================
    # Statistics
    # ====================

    async def get_stats(self) -> MembershipStats:
        """Get membership statistics"""
        try:
            stats = await self.repository.get_stats()
            return MembershipStats(**stats)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return MembershipStats()

    # ====================
    # Private Helper Methods
    # ====================

    def _calculate_enrollment_bonus(self, promo_code: Optional[str]) -> int:
        """Calculate enrollment bonus based on promo code"""
        if not promo_code:
            return 0

        # Example promo code bonuses
        promo_bonuses = {
            "WELCOME100": 100,
            "WELCOME500": 500,
            "VIP1000": 1000,
        }

        return promo_bonuses.get(promo_code.upper(), 0)

    def _calculate_tier(self, tier_points: int) -> MembershipTier:
        """Calculate tier based on tier points"""
        for tier in reversed(TIER_ORDER):
            threshold = TIER_CONFIG[tier]["threshold"]
            if tier_points >= threshold:
                return tier
        return MembershipTier.BRONZE

    def _calculate_tier_progress(self, membership: Membership) -> TierProgress:
        """Calculate tier progress"""
        current_index = TIER_ORDER.index(membership.tier_code)
        current_threshold = TIER_CONFIG[membership.tier_code]["threshold"]

        # If at highest tier
        if current_index == len(TIER_ORDER) - 1:
            return TierProgress(
                current_tier_points=membership.tier_points,
                next_tier_threshold=current_threshold,
                points_to_next_tier=0,
                progress_percentage=Decimal("100.0")
            )

        next_tier = TIER_ORDER[current_index + 1]
        next_threshold = TIER_CONFIG[next_tier]["threshold"]
        points_to_next = max(0, next_threshold - membership.tier_points)

        # Calculate progress percentage
        tier_range = next_threshold - current_threshold
        points_in_range = membership.tier_points - current_threshold
        progress = Decimal(str(min(100, (points_in_range / tier_range) * 100))) if tier_range > 0 else Decimal("100.0")

        return TierProgress(
            current_tier_points=membership.tier_points,
            next_tier_threshold=next_threshold,
            points_to_next_tier=points_to_next,
            progress_percentage=progress.quantize(Decimal("0.01"))
        )

    async def _upgrade_tier(
        self,
        membership: Membership,
        old_tier: MembershipTier,
        new_tier: MembershipTier
    ) -> None:
        """Handle tier upgrade"""
        # Update tier in database
        await self.repository.update_tier(
            membership_id=membership.membership_id,
            new_tier=new_tier.value
        )

        # Record history
        await self.repository.add_history(
            membership_id=membership.membership_id,
            action=PointAction.TIER_UPGRADED,
            previous_tier=old_tier.value,
            new_tier=new_tier.value,
            initiated_by=InitiatedBy.SYSTEM.value
        )

        # Publish tier upgrade event
        await self._publish_event(
            "membership.tier_upgraded",
            {
                "membership_id": membership.membership_id,
                "user_id": membership.user_id,
                "previous_tier": old_tier.value,
                "new_tier": new_tier.value,
                "tier_points": membership.tier_points
            }
        )

        logger.info(f"Membership {membership.membership_id} upgraded from {old_tier.value} to {new_tier.value}")

    async def _get_membership_benefits(self, membership: Membership) -> List[BenefitUsage]:
        """Get benefits with usage for membership"""
        tier_benefits = await self.repository.get_tier_benefits(membership.tier_code.value)
        benefits = []

        for benefit in tier_benefits:
            usage_count = await self.repository.get_benefit_usage(
                membership_id=membership.membership_id,
                benefit_code=benefit.benefit_code
            )

            remaining = None
            if not benefit.is_unlimited and benefit.usage_limit:
                remaining = max(0, benefit.usage_limit - usage_count)

            benefits.append(BenefitUsage(
                benefit_code=benefit.benefit_code,
                benefit_name=benefit.benefit_name,
                benefit_type=benefit.benefit_type,
                usage_limit=benefit.usage_limit,
                used_count=usage_count,
                remaining=remaining,
                is_unlimited=benefit.is_unlimited,
                is_available=benefit.is_unlimited or (remaining is not None and remaining > 0)
            ))

        return benefits

    async def _publish_event(self, subject: str, data: Dict[str, Any]) -> None:
        """Publish event to event bus"""
        if not self.event_bus:
            return

        try:
            event_data = {
                "event_type": subject.upper().replace(".", "_"),
                "source": "membership_service",
                "data": {
                    **data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            await self.event_bus.publish(subject, event_data)
        except Exception as e:
            logger.warning(f"Failed to publish event {subject}: {e}")


__all__ = ["MembershipService"]
