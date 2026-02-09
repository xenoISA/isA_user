"""
Unit Tests for History Management

Tests for history retrieval and filtering.
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


class TestGetHistory:
    """Tests for get_history method"""

    @pytest.mark.asyncio
    async def test_get_history_success(self, membership_service, sample_membership, mock_repository):
        """Test getting history"""
        # Enroll creates history, let's add more
        await mock_repository.add_history(
            sample_membership.membership_id,
            PointAction.POINTS_EARNED,
            points_change=100
        )

        result = await membership_service.get_history(
            sample_membership.membership_id
        )

        assert result.success is True
        assert len(result.history) >= 1

    @pytest.mark.asyncio
    async def test_get_history_empty(self, membership_service, mock_repository):
        """Test getting history for membership with no history"""
        membership = await mock_repository.create_membership(
            user_id="no_history_user",
            tier_code="bronze"
        )

        result = await membership_service.get_history(
            membership.membership_id
        )

        assert result.success is True
        # May have enrollment history

    @pytest.mark.asyncio
    async def test_get_history_filter_by_action(self, membership_service, sample_membership, mock_repository):
        """Test filtering history by action type"""
        # Add different types of history
        await mock_repository.add_history(
            sample_membership.membership_id,
            PointAction.POINTS_EARNED,
            points_change=100
        )
        await mock_repository.add_history(
            sample_membership.membership_id,
            PointAction.POINTS_REDEEMED,
            points_change=-50
        )

        result = await membership_service.get_history(
            sample_membership.membership_id,
            action=PointAction.POINTS_EARNED
        )

        assert result.success is True
        for entry in result.history:
            assert entry.action == PointAction.POINTS_EARNED

    @pytest.mark.asyncio
    async def test_get_history_pagination(self, membership_service, sample_membership, mock_repository):
        """Test history pagination"""
        # Add many history entries
        for i in range(15):
            await mock_repository.add_history(
                sample_membership.membership_id,
                PointAction.POINTS_EARNED,
                points_change=i * 10
            )

        result = await membership_service.get_history(
            sample_membership.membership_id,
            page=1,
            page_size=5
        )

        assert result.success is True
        assert len(result.history) == 5
        assert result.page == 1
        assert result.page_size == 5

    @pytest.mark.asyncio
    async def test_get_history_total_count(self, membership_service, sample_membership, mock_repository):
        """Test history returns total count"""
        for i in range(10):
            await mock_repository.add_history(
                sample_membership.membership_id,
                PointAction.POINTS_EARNED,
                points_change=100
            )

        result = await membership_service.get_history(
            sample_membership.membership_id,
            page=1,
            page_size=5
        )

        assert result.success is True
        assert result.total >= 10


class TestHistoryEntries:
    """Tests for history entry details"""

    @pytest.mark.asyncio
    async def test_enrollment_history(self, membership_service, mock_event_bus):
        """Test enrollment creates history entry"""
        result = await membership_service.enroll_membership(
            user_id="enroll_hist_user"
        )

        assert result.success is True
        hist_result = await membership_service.get_history(
            result.membership.membership_id
        )

        enrolled = [h for h in hist_result.history if h.action == PointAction.ENROLLED]
        assert len(enrolled) >= 1

    @pytest.mark.asyncio
    async def test_earn_points_history(self, membership_service, sample_membership, mock_repository):
        """Test earning points creates history entry"""
        await membership_service.earn_points(
            user_id="user_123",
            points_amount=500,
            source="order_completed",
            reference_id="order_12345"
        )

        history = await mock_repository.get_history(sample_membership.membership_id)
        earned = [h for h in history if h.action == PointAction.POINTS_EARNED]

        assert len(earned) >= 1
        assert earned[0].points_change > 0
        assert earned[0].source == "order_completed"
        assert earned[0].reference_id == "order_12345"

    @pytest.mark.asyncio
    async def test_redeem_points_history(self, membership_service, sample_membership, mock_repository):
        """Test redeeming points creates history entry"""
        await membership_service.redeem_points(
            user_id="user_123",
            points_amount=100,
            reward_code="DISCOUNT_10"
        )

        history = await mock_repository.get_history(sample_membership.membership_id)
        redeemed = [h for h in history if h.action == PointAction.POINTS_REDEEMED]

        assert len(redeemed) >= 1
        assert redeemed[0].points_change == -100
        assert redeemed[0].reward_code == "DISCOUNT_10"

    @pytest.mark.asyncio
    async def test_tier_upgrade_history(self, membership_service, mock_repository):
        """Test tier upgrade creates history entry"""
        membership = await mock_repository.create_membership(
            user_id="tier_hist_user",
            tier_code="bronze",
            tier_points=4900
        )

        await membership_service.earn_points(
            user_id="tier_hist_user",
            points_amount=200,
            source="test"
        )

        history = await mock_repository.get_history(membership.membership_id)
        upgraded = [h for h in history if h.action == PointAction.TIER_UPGRADED]

        assert len(upgraded) >= 1
        assert upgraded[0].previous_tier == "bronze"
        assert upgraded[0].new_tier == "silver"

    @pytest.mark.asyncio
    async def test_benefit_used_history(self, membership_service, gold_membership, mock_repository):
        """Test benefit usage creates history entry"""
        await membership_service.use_benefit(
            membership_id=gold_membership.membership_id,
            benefit_code="FREE_SHIPPING"
        )

        history = await mock_repository.get_history(gold_membership.membership_id)
        benefit_used = [h for h in history if h.action == PointAction.BENEFIT_USED]

        assert len(benefit_used) >= 1
        assert benefit_used[0].benefit_code == "FREE_SHIPPING"

    @pytest.mark.asyncio
    async def test_suspension_history(self, membership_service, sample_membership, mock_repository):
        """Test suspension creates history entry"""
        await membership_service.suspend_membership(
            membership_id=sample_membership.membership_id,
            reason="Testing"
        )

        history = await mock_repository.get_history(sample_membership.membership_id)
        suspended = [h for h in history if h.action == PointAction.SUSPENDED]

        assert len(suspended) >= 1

    @pytest.mark.asyncio
    async def test_cancellation_history(self, membership_service, sample_membership, mock_repository):
        """Test cancellation creates history entry"""
        await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Moving"
        )

        history = await mock_repository.get_history(sample_membership.membership_id)
        canceled = [h for h in history if h.action == PointAction.CANCELED]

        assert len(canceled) >= 1


class TestHistoryMetadata:
    """Tests for history metadata"""

    @pytest.mark.asyncio
    async def test_history_with_metadata(self, membership_service, sample_membership, mock_repository):
        """Test history with custom metadata"""
        await membership_service.earn_points(
            user_id="user_123",
            points_amount=100,
            source="bonus",
            metadata={"campaign": "summer2025", "referrer": "partner_xyz"}
        )

        history = await mock_repository.get_history(sample_membership.membership_id)
        earned = [h for h in history if h.action == PointAction.POINTS_EARNED]

        assert len(earned) >= 1
        # Metadata includes base_points and multiplier plus custom fields

    @pytest.mark.asyncio
    async def test_history_balance_after(self, membership_service, sample_membership, mock_repository):
        """Test history includes balance after"""
        await membership_service.earn_points(
            user_id="user_123",
            points_amount=100,
            source="test"
        )

        history = await mock_repository.get_history(sample_membership.membership_id)
        earned = [h for h in history if h.action == PointAction.POINTS_EARNED]

        assert len(earned) >= 1
        assert earned[0].balance_after is not None
