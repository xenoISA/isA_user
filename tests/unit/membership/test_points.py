"""
Unit Tests for Points Management

Tests for earning, redeeming, and balance logic.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from microservices.membership_service.models import (
    MembershipStatus,
    MembershipTier,
    PointAction,
)


class TestEarnPoints:
    """Tests for earn_points method"""

    @pytest.mark.asyncio
    async def test_earn_points_success(self, membership_service, sample_membership):
        """Test earning points successfully"""
        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order_completed"
        )

        assert result.success is True
        assert result.points_earned == 500  # Bronze tier, 1.0 multiplier
        assert result.points_balance == 1500  # 1000 initial + 500

    @pytest.mark.asyncio
    async def test_earn_points_gold_tier_multiplier(self, membership_service, gold_membership):
        """Test gold tier gets 1.5x multiplier"""
        result = await membership_service.earn_points(
            user_id="user_gold",
            points_amount=1000,
            source="order_completed"
        )

        assert result.success is True
        assert result.multiplier == Decimal("1.5")
        assert result.points_earned == 1500  # 1000 * 1.5

    @pytest.mark.asyncio
    async def test_earn_points_no_membership(self, membership_service):
        """Test earning points with no membership fails"""
        result = await membership_service.earn_points(
            user_id="nonexistent_user",
            points_amount=500,
            source="order"
        )

        assert result.success is False
        assert "no active membership" in result.message.lower()

    @pytest.mark.asyncio
    async def test_earn_points_suspended_membership(self, membership_service, mock_repository, sample_membership):
        """Test earning points with suspended membership fails"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order"
        )

        assert result.success is False
        assert "suspended" in result.message.lower()

    @pytest.mark.asyncio
    async def test_earn_points_expired_membership(self, membership_service, mock_repository, sample_membership):
        """Test earning points with expired membership fails"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.EXPIRED
        )

        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order"
        )

        assert result.success is False
        assert "expired" in result.message.lower()

    @pytest.mark.asyncio
    async def test_earn_points_with_reference_id(self, membership_service, sample_membership, mock_repository):
        """Test earning points with reference ID"""
        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order_completed",
            reference_id="order_12345"
        )

        assert result.success is True
        history = await mock_repository.get_history(sample_membership.membership_id)
        # Find the POINTS_EARNED entry
        earned_entry = [h for h in history if h.action == PointAction.POINTS_EARNED]
        assert len(earned_entry) > 0
        assert earned_entry[0].reference_id == "order_12345"

    @pytest.mark.asyncio
    async def test_earn_points_with_description(self, membership_service, sample_membership, mock_repository):
        """Test earning points with description"""
        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order_completed",
            description="Purchase of $50.00"
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_earn_points_updates_tier_points(self, membership_service, sample_membership, mock_repository):
        """Test tier points are updated with base amount"""
        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order"
        )

        assert result.success is True
        assert result.tier_points == 500  # Base points go to tier_points

    @pytest.mark.asyncio
    async def test_earn_points_triggers_tier_upgrade(self, membership_service, mock_repository):
        """Test tier upgrade triggered by earning points"""
        # Create membership close to silver threshold
        membership = await mock_repository.create_membership(
            user_id="upgrade_user",
            tier_code="bronze",
            points_balance=0,
            tier_points=4900
        )

        result = await membership_service.earn_points(
            user_id="upgrade_user",
            points_amount=200,  # Should push over 5000 threshold
            source="order"
        )

        assert result.success is True
        assert result.tier_upgraded is True
        assert result.new_tier == MembershipTier.SILVER

    @pytest.mark.asyncio
    async def test_earn_points_publishes_event(self, membership_service, sample_membership, mock_event_bus):
        """Test earning points publishes event"""
        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order"
        )

        assert result.success is True
        events = [e for e in mock_event_bus.published_events if e["subject"] == "points.earned"]
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_earn_small_points(self, membership_service, sample_membership):
        """Test earning small amount of points"""
        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=1,
            source="daily_login"
        )

        assert result.success is True
        assert result.points_earned == 1


class TestRedeemPoints:
    """Tests for redeem_points method"""

    @pytest.mark.asyncio
    async def test_redeem_points_success(self, membership_service, sample_membership):
        """Test redeeming points successfully"""
        result = await membership_service.redeem_points(
            user_id="user_123",
            points_amount=500,
            reward_code="DISCOUNT_10"
        )

        assert result.success is True
        assert result.points_redeemed == 500
        assert result.points_balance == 500  # 1000 - 500
        assert result.reward_code == "DISCOUNT_10"

    @pytest.mark.asyncio
    async def test_redeem_all_points(self, membership_service, sample_membership):
        """Test redeeming all points"""
        result = await membership_service.redeem_points(
            user_id="user_123",
            points_amount=1000,
            reward_code="FULL_REDEEM"
        )

        assert result.success is True
        assert result.points_balance == 0

    @pytest.mark.asyncio
    async def test_redeem_insufficient_points(self, membership_service, sample_membership):
        """Test redeeming more points than available fails"""
        result = await membership_service.redeem_points(
            user_id="user_123",
            points_amount=2000,  # Only has 1000
            reward_code="BIG_DISCOUNT"
        )

        assert result.success is False
        assert "insufficient" in result.message.lower()

    @pytest.mark.asyncio
    async def test_redeem_no_membership(self, membership_service):
        """Test redeeming with no membership fails"""
        result = await membership_service.redeem_points(
            user_id="no_member",
            points_amount=100,
            reward_code="DISCOUNT"
        )

        assert result.success is False
        assert "no active membership" in result.message.lower()

    @pytest.mark.asyncio
    async def test_redeem_suspended_membership(self, membership_service, mock_repository, sample_membership):
        """Test redeeming with suspended membership fails"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.redeem_points(
            user_id="user_123",
            points_amount=100,
            reward_code="DISCOUNT"
        )

        assert result.success is False
        assert "suspended" in result.message.lower()

    @pytest.mark.asyncio
    async def test_redeem_creates_history(self, membership_service, sample_membership, mock_repository):
        """Test redemption creates history entry"""
        result = await membership_service.redeem_points(
            user_id="user_123",
            points_amount=100,
            reward_code="DISCOUNT"
        )

        assert result.success is True
        history = await mock_repository.get_history(sample_membership.membership_id)
        redeemed = [h for h in history if h.action == PointAction.POINTS_REDEEMED]
        assert len(redeemed) >= 1
        assert redeemed[0].points_change == -100

    @pytest.mark.asyncio
    async def test_redeem_publishes_event(self, membership_service, sample_membership, mock_event_bus):
        """Test redemption publishes event"""
        result = await membership_service.redeem_points(
            user_id="user_123",
            points_amount=100,
            reward_code="DISCOUNT"
        )

        assert result.success is True
        events = [e for e in mock_event_bus.published_events if e["subject"] == "points.redeemed"]
        assert len(events) >= 1


class TestGetPointsBalance:
    """Tests for get_points_balance method"""

    @pytest.mark.asyncio
    async def test_get_balance_success(self, membership_service, sample_membership):
        """Test getting points balance"""
        result = await membership_service.get_points_balance(
            user_id="user_123"
        )

        assert result.success is True
        assert result.balance is not None
        assert result.balance.points_balance == 1000
        assert result.balance.membership_id == sample_membership.membership_id

    @pytest.mark.asyncio
    async def test_get_balance_no_membership(self, membership_service):
        """Test getting balance with no membership"""
        result = await membership_service.get_points_balance(
            user_id="no_member"
        )

        assert result.success is False
        assert result.balance is None

    @pytest.mark.asyncio
    async def test_get_balance_includes_tier_info(self, membership_service, sample_membership):
        """Test balance includes tier information"""
        result = await membership_service.get_points_balance(
            user_id="user_123"
        )

        assert result.success is True
        assert result.balance.tier_code == MembershipTier.BRONZE

    @pytest.mark.asyncio
    async def test_get_balance_with_organization(self, membership_service, mock_repository):
        """Test getting balance for organization membership"""
        await mock_repository.create_membership(
            user_id="org_user",
            tier_code="bronze",
            organization_id="org_123",
            points_balance=2000
        )

        result = await membership_service.get_points_balance(
            user_id="org_user",
            organization_id="org_123"
        )

        assert result.success is True
        assert result.balance.points_balance == 2000


class TestTierMultipliers:
    """Tests for tier point multipliers"""

    @pytest.mark.asyncio
    async def test_bronze_multiplier_is_1x(self, membership_service, mock_repository):
        """Test bronze tier has 1x multiplier"""
        await mock_repository.create_membership(
            user_id="bronze_user",
            tier_code="bronze",
            points_balance=0
        )

        result = await membership_service.earn_points(
            user_id="bronze_user",
            points_amount=100,
            source="test"
        )

        assert result.success is True
        assert result.multiplier == Decimal("1.0")
        assert result.points_earned == 100

    @pytest.mark.asyncio
    async def test_silver_multiplier_is_1_25x(self, membership_service, mock_repository):
        """Test silver tier has 1.25x multiplier"""
        await mock_repository.create_membership(
            user_id="silver_user",
            tier_code="silver",
            points_balance=0
        )

        result = await membership_service.earn_points(
            user_id="silver_user",
            points_amount=100,
            source="test"
        )

        assert result.success is True
        assert result.multiplier == Decimal("1.25")
        assert result.points_earned == 125

    @pytest.mark.asyncio
    async def test_gold_multiplier_is_1_5x(self, membership_service, mock_repository):
        """Test gold tier has 1.5x multiplier"""
        await mock_repository.create_membership(
            user_id="gold_user",
            tier_code="gold",
            points_balance=0
        )

        result = await membership_service.earn_points(
            user_id="gold_user",
            points_amount=100,
            source="test"
        )

        assert result.success is True
        assert result.multiplier == Decimal("1.5")
        assert result.points_earned == 150

    @pytest.mark.asyncio
    async def test_platinum_multiplier_is_2x(self, membership_service, mock_repository):
        """Test platinum tier has 2x multiplier"""
        await mock_repository.create_membership(
            user_id="plat_user",
            tier_code="platinum",
            points_balance=0
        )

        result = await membership_service.earn_points(
            user_id="plat_user",
            points_amount=100,
            source="test"
        )

        assert result.success is True
        assert result.multiplier == Decimal("2.0")
        assert result.points_earned == 200

    @pytest.mark.asyncio
    async def test_diamond_multiplier_is_3x(self, membership_service, mock_repository):
        """Test diamond tier has 3x multiplier"""
        await mock_repository.create_membership(
            user_id="diamond_user",
            tier_code="diamond",
            points_balance=0
        )

        result = await membership_service.earn_points(
            user_id="diamond_user",
            points_amount=100,
            source="test"
        )

        assert result.success is True
        assert result.multiplier == Decimal("3.0")
        assert result.points_earned == 300
