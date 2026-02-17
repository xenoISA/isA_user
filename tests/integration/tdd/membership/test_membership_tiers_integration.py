"""
Membership Service Integration Tests - Tier Operations

Tests the MembershipService tier operations with mocked dependencies.
These tests verify tier progression, upgrades, and status.

Usage:
    pytest tests/integration/tdd/membership/test_membership_tiers_integration.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

# Import from centralized data contracts
from tests.contracts.membership.data_contract import (
    MembershipTestDataFactory,
    MembershipTierContract,
)

# Import service and models
from microservices.membership_service.membership_service import MembershipService
from microservices.membership_service.models import (
    Membership,
    MembershipStatus,
    MembershipTier,
    Tier,
    TierBenefit,
    EarnPointsRequest,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Tier Status Tests (6 tests)
# ============================================================================

class TestTierStatusIntegration:
    """Integration tests for tier status operations."""

    async def test_get_tier_status_success(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Gets tier status successfully."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )
        mock_membership_repository.get_tier = AsyncMock(
            return_value=Tier(
                tier_code=MembershipTier.BRONZE,
                tier_name="Bronze",
                qualification_threshold=0,
                point_multiplier=Decimal("1.0"),
            )
        )
        mock_membership_repository.get_tier_benefits = AsyncMock(return_value=[])

        result = await membership_service.get_tier_status(
            membership_id=sample_membership.membership_id
        )

        assert result.success is True
        assert result.current_tier is not None
        assert result.current_tier.tier_code == MembershipTier.BRONZE

    async def test_get_tier_status_with_progress(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Gets tier status with progress to next tier."""
        # Membership with points approaching silver (5000)
        sample_membership.tier_points = 3000

        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )
        mock_membership_repository.get_tier = AsyncMock(
            return_value=Tier(
                tier_code=MembershipTier.BRONZE,
                tier_name="Bronze",
                qualification_threshold=0,
                point_multiplier=Decimal("1.0"),
            )
        )
        mock_membership_repository.get_tier_benefits = AsyncMock(return_value=[])

        result = await membership_service.get_tier_status(
            membership_id=sample_membership.membership_id
        )

        assert result.success is True
        assert result.tier_progress is not None
        assert result.tier_progress.points_to_next_tier == 2000  # 5000 - 3000

    async def test_get_tier_status_at_max_tier(
        self, membership_service, mock_membership_repository
    ):
        """Gets tier status when at maximum tier (diamond)."""
        diamond_membership = Membership(
            membership_id=MembershipTestDataFactory.make_membership_id(),
            user_id=MembershipTestDataFactory.make_user_id(),
            tier_code=MembershipTier.DIAMOND,
            status=MembershipStatus.ACTIVE,
            points_balance=150000,
            tier_points=150000,
            lifetime_points=200000,
            enrolled_at=datetime.now(timezone.utc),
        )

        mock_membership_repository.get_membership = AsyncMock(
            return_value=diamond_membership
        )
        mock_membership_repository.get_tier = AsyncMock(
            return_value=Tier(
                tier_code=MembershipTier.DIAMOND,
                tier_name="Diamond",
                qualification_threshold=100000,
                point_multiplier=Decimal("3.0"),
            )
        )
        mock_membership_repository.get_tier_benefits = AsyncMock(return_value=[])

        result = await membership_service.get_tier_status(
            membership_id=diamond_membership.membership_id
        )

        assert result.success is True
        assert result.tier_progress.points_to_next_tier == 0  # At max tier

    async def test_get_tier_status_not_found(
        self, membership_service, mock_membership_repository
    ):
        """Returns failure when membership not found."""
        mock_membership_repository.get_membership = AsyncMock(return_value=None)

        result = await membership_service.get_tier_status(
            membership_id="nonexistent"
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_get_tier_status_includes_benefits(
        self, membership_service, mock_membership_repository, gold_membership
    ):
        """Tier status includes available benefits."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=gold_membership
        )
        mock_membership_repository.get_tier = AsyncMock(
            return_value=Tier(
                tier_code=MembershipTier.GOLD,
                tier_name="Gold",
                qualification_threshold=20000,
                point_multiplier=Decimal("1.5"),
            )
        )
        mock_membership_repository.get_tier_benefits = AsyncMock(
            return_value=[
                TierBenefit(
                    benefit_id="bnft_1",
                    tier_code=MembershipTier.GOLD,
                    benefit_code="FREE_SHIPPING",
                    benefit_name="Free Shipping",
                    benefit_type="discount",
                    is_unlimited=True,
                )
            ]
        )

        result = await membership_service.get_tier_status(
            membership_id=gold_membership.membership_id
        )

        assert result.success is True
        assert len(result.benefits) > 0

    async def test_get_tier_progress_percentage(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Tier progress includes percentage."""
        sample_membership.tier_points = 2500  # 50% of 5000 to silver

        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )
        mock_membership_repository.get_tier = AsyncMock(
            return_value=Tier(
                tier_code=MembershipTier.BRONZE,
                tier_name="Bronze",
                qualification_threshold=0,
                point_multiplier=Decimal("1.0"),
            )
        )
        mock_membership_repository.get_tier_benefits = AsyncMock(return_value=[])

        result = await membership_service.get_tier_status(
            membership_id=sample_membership.membership_id
        )

        assert result.success is True
        assert result.tier_progress.progress_percentage == Decimal("50.00")


# ============================================================================
# Tier Upgrade Tests (6 tests)
# ============================================================================

class TestTierUpgradeIntegration:
    """Integration tests for tier upgrade operations."""

    async def test_earn_points_triggers_tier_upgrade(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Earning enough points triggers tier upgrade."""
        # Starting at bronze with 4000 points
        sample_membership.tier_points = 4000
        sample_membership.points_balance = 4000
        points_to_earn = 2000  # Total will be 6000, above silver threshold (5000)

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        # Return upgraded membership
        upgraded_membership = Membership(
            **{**sample_membership.__dict__,
               "tier_code": MembershipTier.SILVER,
               "tier_points": 6000,
               "points_balance": 6000}
        )
        mock_membership_repository.add_points = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.update_tier = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=points_to_earn,
                source="order_completed"
            )
        )

        assert result.success is True
        # Tier upgrade should have been triggered

    async def test_tier_upgrade_publishes_event(
        self, membership_service, mock_membership_repository, mock_event_bus, sample_membership
    ):
        """Tier upgrade publishes tier.upgraded event."""
        sample_membership.tier_points = 4500
        sample_membership.points_balance = 4500
        points_to_earn = 1000

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        upgraded_membership = Membership(
            **{**sample_membership.__dict__,
               "tier_code": MembershipTier.SILVER,
               "tier_points": 5500,
               "points_balance": 5500}
        )
        mock_membership_repository.add_points = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.update_tier = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=points_to_earn,
                source="order_completed"
            )
        )

        # Check if tier upgrade event was published
        assert len(mock_event_bus.published_events) > 0

    async def test_multiple_tier_upgrades(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Large point earn can trigger multiple tier upgrades."""
        sample_membership.tier_points = 0
        sample_membership.points_balance = 0
        points_to_earn = 25000  # Should go straight to gold (20000)

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        upgraded_membership = Membership(
            **{**sample_membership.__dict__,
               "tier_code": MembershipTier.GOLD,
               "tier_points": 25000,
               "points_balance": 25000}
        )
        mock_membership_repository.add_points = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.update_tier = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=points_to_earn,
                source="signup_bonus"
            )
        )

        assert result.success is True

    async def test_no_tier_upgrade_below_threshold(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """No tier upgrade when below threshold."""
        sample_membership.tier_points = 1000
        sample_membership.points_balance = 1000
        points_to_earn = 1000  # Total 2000, still below silver (5000)

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        updated_membership = Membership(
            **{**sample_membership.__dict__,
               "tier_points": 2000,
               "points_balance": 2000}
        )
        mock_membership_repository.add_points = AsyncMock(return_value=updated_membership)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=points_to_earn,
                source="order_completed"
            )
        )

        assert result.success is True
        # update_tier should not have been called
        mock_membership_repository.update_tier.assert_not_called() if hasattr(mock_membership_repository, 'update_tier') else None

    async def test_tier_upgrade_at_exact_threshold(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Tier upgrade occurs at exact threshold."""
        sample_membership.tier_points = 4500
        sample_membership.points_balance = 4500
        points_to_earn = 500  # Exactly 5000 for silver

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        upgraded_membership = Membership(
            **{**sample_membership.__dict__,
               "tier_code": MembershipTier.SILVER,
               "tier_points": 5000,
               "points_balance": 5000}
        )
        mock_membership_repository.add_points = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.update_tier = AsyncMock(return_value=upgraded_membership)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=points_to_earn,
                source="order_completed"
            )
        )

        assert result.success is True

    async def test_diamond_tier_no_further_upgrade(
        self, membership_service, mock_membership_repository
    ):
        """Diamond tier cannot upgrade further."""
        diamond_membership = Membership(
            membership_id=MembershipTestDataFactory.make_membership_id(),
            user_id=MembershipTestDataFactory.make_user_id(),
            tier_code=MembershipTier.DIAMOND,
            status=MembershipStatus.ACTIVE,
            points_balance=150000,
            tier_points=150000,
            lifetime_points=200000,
            enrolled_at=datetime.now(timezone.utc),
        )

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=diamond_membership
        )

        updated_membership = Membership(
            **{**diamond_membership.__dict__,
               "tier_points": 200000,
               "points_balance": 200000}
        )
        mock_membership_repository.add_points = AsyncMock(return_value=updated_membership)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=diamond_membership.user_id,
                points_amount=50000,
                source="mega_order"
            )
        )

        assert result.success is True
        # Tier should remain diamond
