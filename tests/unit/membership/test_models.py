"""
Unit Tests for Membership Models

Tests for Pydantic model validation and enums.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ValidationError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from microservices.membership_service.models import (
    # Enums
    MembershipStatus,
    MembershipTier,
    PointAction,
    InitiatedBy,
    # Core Models
    Membership,
    MembershipHistory,
    Tier,
    TierBenefit,
    BenefitUsage,
    # Request Models
    EnrollMembershipRequest,
    EarnPointsRequest,
    RedeemPointsRequest,
    CancelMembershipRequest,
    SuspendMembershipRequest,
    UseBenefitRequest,
    # Response Models
    TierInfo,
    TierProgress,
    PointsBalance,
    EnrollMembershipResponse,
    EarnPointsResponse,
    RedeemPointsResponse,
    PointsBalanceResponse,
    MembershipStats,
)


# ====================
# Enum Tests
# ====================

class TestMembershipStatusEnum:
    """Tests for MembershipStatus enum"""

    def test_active_status(self):
        assert MembershipStatus.ACTIVE.value == "active"

    def test_pending_status(self):
        assert MembershipStatus.PENDING.value == "pending"

    def test_suspended_status(self):
        assert MembershipStatus.SUSPENDED.value == "suspended"

    def test_expired_status(self):
        assert MembershipStatus.EXPIRED.value == "expired"

    def test_canceled_status(self):
        assert MembershipStatus.CANCELED.value == "canceled"

    def test_status_from_string(self):
        assert MembershipStatus("active") == MembershipStatus.ACTIVE

    def test_invalid_status_raises_error(self):
        with pytest.raises(ValueError):
            MembershipStatus("invalid_status")


class TestMembershipTierEnum:
    """Tests for MembershipTier enum"""

    def test_bronze_tier(self):
        assert MembershipTier.BRONZE.value == "bronze"

    def test_silver_tier(self):
        assert MembershipTier.SILVER.value == "silver"

    def test_gold_tier(self):
        assert MembershipTier.GOLD.value == "gold"

    def test_platinum_tier(self):
        assert MembershipTier.PLATINUM.value == "platinum"

    def test_diamond_tier(self):
        assert MembershipTier.DIAMOND.value == "diamond"

    def test_tier_from_string(self):
        assert MembershipTier("gold") == MembershipTier.GOLD


class TestPointActionEnum:
    """Tests for PointAction enum"""

    def test_enrolled_action(self):
        assert PointAction.ENROLLED.value == "enrolled"

    def test_points_earned_action(self):
        assert PointAction.POINTS_EARNED.value == "points_earned"

    def test_points_redeemed_action(self):
        assert PointAction.POINTS_REDEEMED.value == "points_redeemed"

    def test_tier_upgraded_action(self):
        assert PointAction.TIER_UPGRADED.value == "tier_upgraded"

    def test_benefit_used_action(self):
        assert PointAction.BENEFIT_USED.value == "benefit_used"


class TestInitiatedByEnum:
    """Tests for InitiatedBy enum"""

    def test_user_initiated(self):
        assert InitiatedBy.USER.value == "user"

    def test_system_initiated(self):
        assert InitiatedBy.SYSTEM.value == "system"

    def test_admin_initiated(self):
        assert InitiatedBy.ADMIN.value == "admin"


# ====================
# Core Model Tests
# ====================

class TestMembershipModel:
    """Tests for Membership model"""

    def test_create_membership_minimal(self):
        membership = Membership(
            membership_id="mem_123",
            user_id="user_456"
        )
        assert membership.membership_id == "mem_123"
        assert membership.user_id == "user_456"
        assert membership.tier_code == MembershipTier.BRONZE
        assert membership.status == MembershipStatus.ACTIVE
        assert membership.points_balance == 0

    def test_create_membership_full(self):
        now = datetime.now(timezone.utc)
        membership = Membership(
            membership_id="mem_123",
            user_id="user_456",
            organization_id="org_789",
            tier_code=MembershipTier.GOLD,
            status=MembershipStatus.ACTIVE,
            points_balance=5000,
            tier_points=25000,
            lifetime_points=30000,
            enrolled_at=now
        )
        assert membership.tier_code == MembershipTier.GOLD
        assert membership.points_balance == 5000
        assert membership.tier_points == 25000

    def test_membership_default_values(self):
        membership = Membership(
            membership_id="mem_123",
            user_id="user_456"
        )
        assert membership.pending_points == 0
        assert membership.auto_renew is True
        assert membership.metadata == {}

    def test_membership_invalid_points_balance(self):
        with pytest.raises(ValidationError):
            Membership(
                membership_id="mem_123",
                user_id="user_456",
                points_balance=-100
            )


class TestMembershipHistoryModel:
    """Tests for MembershipHistory model"""

    def test_create_history_entry(self):
        history = MembershipHistory(
            history_id="hist_123",
            membership_id="mem_456",
            action=PointAction.POINTS_EARNED,
            points_change=100
        )
        assert history.action == PointAction.POINTS_EARNED
        assert history.points_change == 100

    def test_history_with_tier_change(self):
        history = MembershipHistory(
            history_id="hist_123",
            membership_id="mem_456",
            action=PointAction.TIER_UPGRADED,
            previous_tier="silver",
            new_tier="gold"
        )
        assert history.previous_tier == "silver"
        assert history.new_tier == "gold"


class TestTierModel:
    """Tests for Tier model"""

    def test_create_tier(self):
        tier = Tier(
            tier_code=MembershipTier.GOLD,
            tier_name="Gold",
            qualification_threshold=20000,
            point_multiplier=Decimal("1.5")
        )
        assert tier.tier_code == MembershipTier.GOLD
        assert tier.qualification_threshold == 20000
        assert tier.point_multiplier == Decimal("1.5")

    def test_tier_default_values(self):
        tier = Tier(
            tier_code=MembershipTier.BRONZE,
            tier_name="Bronze"
        )
        assert tier.display_order == 0
        assert tier.is_active is True


class TestTierBenefitModel:
    """Tests for TierBenefit model"""

    def test_create_benefit(self):
        benefit = TierBenefit(
            benefit_id="bnft_123",
            tier_code=MembershipTier.GOLD,
            benefit_code="FREE_SHIPPING",
            benefit_name="Free Shipping",
            benefit_type="discount"
        )
        assert benefit.benefit_code == "FREE_SHIPPING"
        assert benefit.is_unlimited is False

    def test_benefit_with_limit(self):
        benefit = TierBenefit(
            benefit_id="bnft_123",
            tier_code=MembershipTier.SILVER,
            benefit_code="FREE_SHIPPING",
            benefit_name="Free Shipping",
            benefit_type="discount",
            usage_limit=3
        )
        assert benefit.usage_limit == 3


# ====================
# Request Model Tests
# ====================

class TestEnrollMembershipRequest:
    """Tests for EnrollMembershipRequest"""

    def test_valid_request(self):
        request = EnrollMembershipRequest(
            user_id="user_123"
        )
        assert request.user_id == "user_123"
        assert request.enrollment_source == "api"

    def test_request_with_promo(self):
        request = EnrollMembershipRequest(
            user_id="user_123",
            promo_code="WELCOME100"
        )
        assert request.promo_code == "WELCOME100"

    def test_empty_user_id_fails(self):
        with pytest.raises(ValidationError):
            EnrollMembershipRequest(user_id="")


class TestEarnPointsRequest:
    """Tests for EarnPointsRequest"""

    def test_valid_request(self):
        request = EarnPointsRequest(
            user_id="user_123",
            points_amount=500,
            source="order_completed"
        )
        assert request.points_amount == 500

    def test_zero_points_fails(self):
        with pytest.raises(ValidationError):
            EarnPointsRequest(
                user_id="user_123",
                points_amount=0,
                source="order"
            )

    def test_negative_points_fails(self):
        with pytest.raises(ValidationError):
            EarnPointsRequest(
                user_id="user_123",
                points_amount=-100,
                source="order"
            )

    def test_max_points_limit(self):
        with pytest.raises(ValidationError):
            EarnPointsRequest(
                user_id="user_123",
                points_amount=20_000_000,
                source="order"
            )


class TestRedeemPointsRequest:
    """Tests for RedeemPointsRequest"""

    def test_valid_request(self):
        request = RedeemPointsRequest(
            user_id="user_123",
            points_amount=500,
            reward_code="DISCOUNT_10"
        )
        assert request.reward_code == "DISCOUNT_10"

    def test_zero_points_fails(self):
        with pytest.raises(ValidationError):
            RedeemPointsRequest(
                user_id="user_123",
                points_amount=0,
                reward_code="REWARD"
            )


class TestCancelMembershipRequest:
    """Tests for CancelMembershipRequest"""

    def test_valid_request(self):
        request = CancelMembershipRequest(
            reason="Not using the service"
        )
        assert request.forfeit_points is False

    def test_forfeit_points(self):
        request = CancelMembershipRequest(
            reason="Moving",
            forfeit_points=True
        )
        assert request.forfeit_points is True


class TestSuspendMembershipRequest:
    """Tests for SuspendMembershipRequest"""

    def test_valid_request(self):
        request = SuspendMembershipRequest(
            reason="Fraud investigation"
        )
        assert request.duration_days is None

    def test_with_duration(self):
        request = SuspendMembershipRequest(
            reason="Temporary suspension",
            duration_days=30
        )
        assert request.duration_days == 30


# ====================
# Response Model Tests
# ====================

class TestTierInfo:
    """Tests for TierInfo response model"""

    def test_tier_info(self):
        info = TierInfo(
            tier_code=MembershipTier.GOLD,
            tier_name="Gold",
            point_multiplier=Decimal("1.5"),
            qualification_threshold=20000
        )
        assert info.tier_code == MembershipTier.GOLD


class TestTierProgress:
    """Tests for TierProgress response model"""

    def test_tier_progress(self):
        progress = TierProgress(
            current_tier_points=15000,
            next_tier_threshold=20000,
            points_to_next_tier=5000,
            progress_percentage=Decimal("75.00")
        )
        assert progress.points_to_next_tier == 5000

    def test_progress_at_max(self):
        progress = TierProgress(
            current_tier_points=100000,
            next_tier_threshold=100000,
            points_to_next_tier=0,
            progress_percentage=Decimal("100.00")
        )
        assert progress.progress_percentage == Decimal("100.00")


class TestPointsBalance:
    """Tests for PointsBalance response model"""

    def test_points_balance(self):
        balance = PointsBalance(
            user_id="user_123",
            points_balance=5000,
            tier_points=7500,
            lifetime_points=10000
        )
        assert balance.points_balance == 5000


class TestEnrollMembershipResponse:
    """Tests for EnrollMembershipResponse"""

    def test_success_response(self):
        response = EnrollMembershipResponse(
            success=True,
            message="Enrolled successfully",
            enrollment_bonus=100
        )
        assert response.success is True
        assert response.enrollment_bonus == 100


class TestEarnPointsResponse:
    """Tests for EarnPointsResponse"""

    def test_earn_response(self):
        response = EarnPointsResponse(
            success=True,
            message="Points earned",
            points_earned=150,
            multiplier=Decimal("1.5"),
            points_balance=5150
        )
        assert response.points_earned == 150


class TestRedeemPointsResponse:
    """Tests for RedeemPointsResponse"""

    def test_redeem_response(self):
        response = RedeemPointsResponse(
            success=True,
            message="Points redeemed",
            points_redeemed=500,
            points_balance=4500
        )
        assert response.points_redeemed == 500


class TestMembershipStats:
    """Tests for MembershipStats response model"""

    def test_stats_defaults(self):
        stats = MembershipStats()
        assert stats.total_memberships == 0
        assert stats.active_memberships == 0

    def test_stats_with_data(self):
        stats = MembershipStats(
            total_memberships=1000,
            active_memberships=850,
            tier_distribution={"bronze": 500, "silver": 250, "gold": 100}
        )
        assert stats.tier_distribution["bronze"] == 500
