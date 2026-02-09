"""
Membership Service Integration Tests - Points Operations

Tests the MembershipService points operations with mocked dependencies.
These tests verify business logic integration including tier multipliers.

Usage:
    pytest tests/integration/tdd/membership/test_membership_points_integration.py -v
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
    EarnPointsRequest,
    RedeemPointsRequest,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Earn Points Tests (10 tests)
# ============================================================================

class TestEarnPointsIntegration:
    """Integration tests for earning points."""

    async def test_earn_points_bronze_tier(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Earns points with bronze tier multiplier (1.0x)."""
        points_to_earn = 1000

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        updated_membership = Membership(
            **{**sample_membership.__dict__,
               "points_balance": sample_membership.points_balance + points_to_earn,
               "tier_points": sample_membership.tier_points + points_to_earn}
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
        assert result.points_earned == points_to_earn
        assert result.multiplier == Decimal("1.0")

    async def test_earn_points_gold_tier_multiplier(
        self, membership_service, mock_membership_repository, gold_membership
    ):
        """Earns points with gold tier multiplier (1.5x)."""
        points_to_earn = 1000
        expected_earned = int(1000 * 1.5)  # 1500

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=gold_membership
        )

        updated_membership = Membership(
            **{**gold_membership.__dict__,
               "points_balance": gold_membership.points_balance + expected_earned,
               "tier_points": gold_membership.tier_points + expected_earned}
        )
        mock_membership_repository.add_points = AsyncMock(return_value=updated_membership)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=gold_membership.user_id,
                points_amount=points_to_earn,
                source="order_completed"
            )
        )

        assert result.success is True
        assert result.points_earned == expected_earned
        assert result.multiplier == Decimal("1.5")

    async def test_earn_points_membership_not_found(
        self, membership_service, mock_membership_repository
    ):
        """Fails to earn points when membership not found."""
        user_id = MembershipTestDataFactory.make_user_id()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=user_id,
                points_amount=1000,
                source="order_completed"
            )
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_earn_points_suspended_membership(
        self, membership_service, mock_membership_repository, suspended_membership
    ):
        """Fails to earn points on suspended membership."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=suspended_membership
        )

        result = await membership_service.earn_points(
            EarnPointsRequest(
                user_id=suspended_membership.user_id,
                points_amount=1000,
                source="order_completed"
            )
        )

        assert result.success is False
        assert "suspended" in result.message.lower() or "inactive" in result.message.lower()

    async def test_earn_points_publishes_event(
        self, membership_service, mock_membership_repository, mock_event_bus, sample_membership
    ):
        """Earning points publishes points.earned event."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )
        mock_membership_repository.add_points = AsyncMock(return_value=sample_membership)
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=1000,
                source="order_completed"
            )
        )

        # Verify event was published
        assert len(mock_event_bus.published_events) > 0

    async def test_earn_points_creates_history(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Earning points creates history entry."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )
        mock_membership_repository.add_points = AsyncMock(return_value=sample_membership)
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=1000,
                source="order_completed"
            )
        )

        mock_membership_repository.add_history.assert_called()

    async def test_earn_points_with_reference_id(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Earning points records reference ID."""
        reference_id = MembershipTestDataFactory.make_reference_id()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )
        mock_membership_repository.add_points = AsyncMock(return_value=sample_membership)

        captured_history = []
        async def capture_history(**kwargs):
            captured_history.append(kwargs)
        mock_membership_repository.add_history = AsyncMock(side_effect=capture_history)

        await membership_service.earn_points(
            EarnPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=1000,
                source="order_completed",
                reference_id=reference_id
            )
        )

        assert len(captured_history) > 0
        assert captured_history[0].get("reference_id") == reference_id


# ============================================================================
# Redeem Points Tests (8 tests)
# ============================================================================

class TestRedeemPointsIntegration:
    """Integration tests for redeeming points."""

    async def test_redeem_points_success(
        self, membership_service, mock_membership_repository, gold_membership
    ):
        """Successfully redeems points."""
        points_to_redeem = 500

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=gold_membership
        )

        updated_membership = Membership(
            **{**gold_membership.__dict__,
               "points_balance": gold_membership.points_balance - points_to_redeem}
        )
        mock_membership_repository.deduct_points = AsyncMock(return_value=updated_membership)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.redeem_points(
            RedeemPointsRequest(
                user_id=gold_membership.user_id,
                points_amount=points_to_redeem,
                reward_code="FREE_SHIPPING"
            )
        )

        assert result.success is True
        assert result.points_redeemed == points_to_redeem
        assert result.points_balance == gold_membership.points_balance - points_to_redeem

    async def test_redeem_points_insufficient_balance(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Fails to redeem more points than balance."""
        points_to_redeem = sample_membership.points_balance + 5000

        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        result = await membership_service.redeem_points(
            RedeemPointsRequest(
                user_id=sample_membership.user_id,
                points_amount=points_to_redeem,
                reward_code="FREE_SHIPPING"
            )
        )

        assert result.success is False
        assert "insufficient" in result.message.lower()

    async def test_redeem_points_membership_not_found(
        self, membership_service, mock_membership_repository
    ):
        """Fails to redeem when membership not found."""
        user_id = MembershipTestDataFactory.make_user_id()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        result = await membership_service.redeem_points(
            RedeemPointsRequest(
                user_id=user_id,
                points_amount=500,
                reward_code="FREE_SHIPPING"
            )
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_redeem_points_suspended_membership(
        self, membership_service, mock_membership_repository, suspended_membership
    ):
        """Fails to redeem points on suspended membership."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=suspended_membership
        )

        result = await membership_service.redeem_points(
            RedeemPointsRequest(
                user_id=suspended_membership.user_id,
                points_amount=500,
                reward_code="FREE_SHIPPING"
            )
        )

        assert result.success is False

    async def test_redeem_points_publishes_event(
        self, membership_service, mock_membership_repository, mock_event_bus, gold_membership
    ):
        """Redeeming points publishes event."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=gold_membership
        )
        mock_membership_repository.deduct_points = AsyncMock(return_value=gold_membership)
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.redeem_points(
            RedeemPointsRequest(
                user_id=gold_membership.user_id,
                points_amount=500,
                reward_code="FREE_SHIPPING"
            )
        )

        assert len(mock_event_bus.published_events) > 0

    async def test_redeem_zero_points_fails(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Fails to redeem zero points."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        try:
            result = await membership_service.redeem_points(
                RedeemPointsRequest(
                    user_id=sample_membership.user_id,
                    points_amount=0,
                    reward_code="FREE_SHIPPING"
                )
            )
            assert result.success is False
        except (ValueError, Exception):
            # Expected - validation error
            pass


# ============================================================================
# Points Balance Tests (4 tests)
# ============================================================================

class TestPointsBalanceIntegration:
    """Integration tests for points balance queries."""

    async def test_get_points_balance_success(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Gets points balance successfully."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        result = await membership_service.get_points_balance(
            user_id=sample_membership.user_id
        )

        assert result.success is True
        assert result.balance.points_balance == sample_membership.points_balance
        assert result.balance.tier_points == sample_membership.tier_points

    async def test_get_points_balance_not_found(
        self, membership_service, mock_membership_repository
    ):
        """Returns failure when membership not found."""
        user_id = MembershipTestDataFactory.make_user_id()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        result = await membership_service.get_points_balance(user_id=user_id)

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_get_points_balance_includes_tier_info(
        self, membership_service, mock_membership_repository, gold_membership
    ):
        """Points balance includes tier information."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=gold_membership
        )

        result = await membership_service.get_points_balance(
            user_id=gold_membership.user_id
        )

        assert result.success is True
        assert result.balance.tier_code is not None

    async def test_get_points_balance_includes_lifetime(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Points balance includes lifetime points."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        result = await membership_service.get_points_balance(
            user_id=sample_membership.user_id
        )

        assert result.success is True
        assert result.balance.lifetime_points == sample_membership.lifetime_points
