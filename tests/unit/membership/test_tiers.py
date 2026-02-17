"""
Unit Tests for Tier Management

Tests for tier progression, calculation, and status.
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


class TestCalculateTier:
    """Tests for _calculate_tier method"""

    def test_zero_points_is_bronze(self, membership_service):
        """Test 0 points gives bronze tier"""
        tier = membership_service._calculate_tier(0)
        assert tier == MembershipTier.BRONZE

    def test_4999_points_is_bronze(self, membership_service):
        """Test 4999 points is still bronze"""
        tier = membership_service._calculate_tier(4999)
        assert tier == MembershipTier.BRONZE

    def test_5000_points_is_silver(self, membership_service):
        """Test 5000 points gives silver tier"""
        tier = membership_service._calculate_tier(5000)
        assert tier == MembershipTier.SILVER

    def test_19999_points_is_silver(self, membership_service):
        """Test 19999 points is still silver"""
        tier = membership_service._calculate_tier(19999)
        assert tier == MembershipTier.SILVER

    def test_20000_points_is_gold(self, membership_service):
        """Test 20000 points gives gold tier"""
        tier = membership_service._calculate_tier(20000)
        assert tier == MembershipTier.GOLD

    def test_49999_points_is_gold(self, membership_service):
        """Test 49999 points is still gold"""
        tier = membership_service._calculate_tier(49999)
        assert tier == MembershipTier.GOLD

    def test_50000_points_is_platinum(self, membership_service):
        """Test 50000 points gives platinum tier"""
        tier = membership_service._calculate_tier(50000)
        assert tier == MembershipTier.PLATINUM

    def test_99999_points_is_platinum(self, membership_service):
        """Test 99999 points is still platinum"""
        tier = membership_service._calculate_tier(99999)
        assert tier == MembershipTier.PLATINUM

    def test_100000_points_is_diamond(self, membership_service):
        """Test 100000 points gives diamond tier"""
        tier = membership_service._calculate_tier(100000)
        assert tier == MembershipTier.DIAMOND

    def test_1000000_points_is_diamond(self, membership_service):
        """Test 1000000 points is still diamond"""
        tier = membership_service._calculate_tier(1000000)
        assert tier == MembershipTier.DIAMOND


class TestTierProgress:
    """Tests for _calculate_tier_progress method"""

    @pytest.mark.asyncio
    async def test_bronze_progress_to_silver(self, membership_service, sample_membership):
        """Test progress from bronze towards silver"""
        sample_membership.tier_code = MembershipTier.BRONZE
        sample_membership.tier_points = 2500

        progress = membership_service._calculate_tier_progress(sample_membership)

        assert progress.current_tier_points == 2500
        assert progress.next_tier_threshold == 5000
        assert progress.points_to_next_tier == 2500
        assert progress.progress_percentage == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_silver_progress_to_gold(self, membership_service, mock_repository):
        """Test progress from silver towards gold"""
        membership = await mock_repository.create_membership(
            user_id="silver_user",
            tier_code="silver",
            tier_points=12500
        )

        progress = membership_service._calculate_tier_progress(membership)

        assert progress.next_tier_threshold == 20000
        assert progress.points_to_next_tier == 7500
        # Progress: (12500 - 5000) / (20000 - 5000) = 7500/15000 = 50%
        assert progress.progress_percentage == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_diamond_at_max(self, membership_service, mock_repository):
        """Test diamond tier at max progress"""
        membership = await mock_repository.create_membership(
            user_id="diamond_user",
            tier_code="diamond",
            tier_points=150000
        )

        progress = membership_service._calculate_tier_progress(membership)

        assert progress.points_to_next_tier == 0
        assert progress.progress_percentage == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_just_reached_tier(self, membership_service, mock_repository):
        """Test progress at tier boundary"""
        membership = await mock_repository.create_membership(
            user_id="boundary_user",
            tier_code="silver",
            tier_points=5000
        )

        progress = membership_service._calculate_tier_progress(membership)

        assert progress.progress_percentage == Decimal("0.00")


class TestGetTierStatus:
    """Tests for get_tier_status method"""

    @pytest.mark.asyncio
    async def test_get_tier_status_success(self, membership_service, sample_membership):
        """Test getting tier status"""
        result = await membership_service.get_tier_status(
            sample_membership.membership_id
        )

        assert result.success is True
        assert result.current_tier is not None
        assert result.current_tier.tier_code == MembershipTier.BRONZE
        assert result.tier_progress is not None

    @pytest.mark.asyncio
    async def test_get_tier_status_not_found(self, membership_service):
        """Test getting tier status for non-existent membership"""
        result = await membership_service.get_tier_status("nonexistent_id")

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_get_tier_status_includes_multiplier(self, membership_service, gold_membership):
        """Test tier status includes multiplier"""
        result = await membership_service.get_tier_status(
            gold_membership.membership_id
        )

        assert result.success is True
        assert result.current_tier.point_multiplier == Decimal("1.5")

    @pytest.mark.asyncio
    async def test_get_tier_status_includes_threshold(self, membership_service, gold_membership):
        """Test tier status includes qualification threshold"""
        result = await membership_service.get_tier_status(
            gold_membership.membership_id
        )

        assert result.success is True
        assert result.current_tier.qualification_threshold == 20000

    @pytest.mark.asyncio
    async def test_get_tier_status_includes_benefits(self, membership_service, gold_membership):
        """Test tier status includes benefits"""
        result = await membership_service.get_tier_status(
            gold_membership.membership_id
        )

        assert result.success is True
        assert len(result.benefits) > 0


class TestTierUpgrade:
    """Tests for tier upgrade logic"""

    @pytest.mark.asyncio
    async def test_upgrade_bronze_to_silver(self, membership_service, mock_repository):
        """Test upgrading from bronze to silver"""
        membership = await mock_repository.create_membership(
            user_id="upgrade_user",
            tier_code="bronze",
            tier_points=4900
        )

        result = await membership_service.earn_points(
            user_id="upgrade_user",
            points_amount=200,
            source="order"
        )

        assert result.success is True
        assert result.tier_upgraded is True
        assert result.new_tier == MembershipTier.SILVER

    @pytest.mark.asyncio
    async def test_upgrade_silver_to_gold(self, membership_service, mock_repository):
        """Test upgrading from silver to gold"""
        membership = await mock_repository.create_membership(
            user_id="upgrade_user2",
            tier_code="silver",
            tier_points=19500
        )

        result = await membership_service.earn_points(
            user_id="upgrade_user2",
            points_amount=600,  # 600 * 1.25 = 750, but tier_points get base 600
            source="order"
        )

        # tier_points = 19500 + 600 = 20100 > 20000
        assert result.success is True
        assert result.tier_upgraded is True
        assert result.new_tier == MembershipTier.GOLD

    @pytest.mark.asyncio
    async def test_no_upgrade_insufficient_points(self, membership_service, sample_membership):
        """Test no upgrade when insufficient points"""
        result = await membership_service.earn_points(
            user_id="user_123",
            points_amount=100,  # Not enough to reach silver
            source="order"
        )

        assert result.success is True
        assert result.tier_upgraded is False
        assert result.new_tier is None

    @pytest.mark.asyncio
    async def test_upgrade_creates_history(self, membership_service, mock_repository):
        """Test tier upgrade creates history entry"""
        membership = await mock_repository.create_membership(
            user_id="upgrade_hist_user",
            tier_code="bronze",
            tier_points=4900
        )

        result = await membership_service.earn_points(
            user_id="upgrade_hist_user",
            points_amount=200,
            source="order"
        )

        assert result.tier_upgraded is True
        history = await mock_repository.get_history(membership.membership_id)
        upgrades = [h for h in history if h.action == PointAction.TIER_UPGRADED]
        assert len(upgrades) == 1
        assert upgrades[0].previous_tier == "bronze"
        assert upgrades[0].new_tier == "silver"

    @pytest.mark.asyncio
    async def test_upgrade_publishes_event(self, membership_service, mock_repository, mock_event_bus):
        """Test tier upgrade publishes event"""
        membership = await mock_repository.create_membership(
            user_id="upgrade_event_user",
            tier_code="bronze",
            tier_points=4900
        )

        result = await membership_service.earn_points(
            user_id="upgrade_event_user",
            points_amount=200,
            source="order"
        )

        assert result.tier_upgraded is True
        events = [e for e in mock_event_bus.published_events if "tier_upgraded" in e["subject"]]
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_skip_tier_upgrade(self, membership_service, mock_repository):
        """Test skipping directly from bronze to gold"""
        membership = await mock_repository.create_membership(
            user_id="skip_user",
            tier_code="bronze",
            tier_points=0
        )

        # Earn enough points to skip silver and go to gold
        result = await membership_service.earn_points(
            user_id="skip_user",
            points_amount=25000,  # Well over 20000 threshold
            source="bonus"
        )

        assert result.success is True
        assert result.tier_upgraded is True
        assert result.new_tier == MembershipTier.GOLD
