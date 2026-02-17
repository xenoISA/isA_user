"""
Unit Tests for Membership Management

Tests for get, list, cancel, suspend, reactivate operations.
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


class TestGetMembership:
    """Tests for get_membership method"""

    @pytest.mark.asyncio
    async def test_get_membership_success(self, membership_service, sample_membership):
        """Test getting membership by ID"""
        result = await membership_service.get_membership(
            sample_membership.membership_id
        )

        assert result.success is True
        assert result.membership is not None
        assert result.membership.membership_id == sample_membership.membership_id

    @pytest.mark.asyncio
    async def test_get_membership_not_found(self, membership_service):
        """Test getting non-existent membership"""
        result = await membership_service.get_membership("nonexistent_id")

        assert result.success is False
        assert "not found" in result.message.lower()


class TestGetMembershipByUser:
    """Tests for get_membership_by_user method"""

    @pytest.mark.asyncio
    async def test_get_by_user_success(self, membership_service, sample_membership):
        """Test getting membership by user ID"""
        result = await membership_service.get_membership_by_user(
            user_id="user_123"
        )

        assert result.success is True
        assert result.membership.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_get_by_user_not_found(self, membership_service):
        """Test getting membership for user without membership"""
        result = await membership_service.get_membership_by_user(
            user_id="nonexistent_user"
        )

        assert result.success is False
        assert "not found" in result.message.lower()


class TestListMemberships:
    """Tests for list_memberships method"""

    @pytest.mark.asyncio
    async def test_list_all_memberships(self, membership_service, sample_membership, gold_membership):
        """Test listing all memberships"""
        result = await membership_service.list_memberships()

        assert result.success is True
        assert len(result.memberships) >= 2

    @pytest.mark.asyncio
    async def test_list_by_user(self, membership_service, sample_membership):
        """Test listing memberships by user"""
        result = await membership_service.list_memberships(
            user_id="user_123"
        )

        assert result.success is True
        assert all(m.user_id == "user_123" for m in result.memberships)

    @pytest.mark.asyncio
    async def test_list_by_status(self, membership_service, mock_repository, sample_membership):
        """Test listing memberships by status"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.list_memberships(
            status=MembershipStatus.SUSPENDED
        )

        assert result.success is True
        assert all(m.status == MembershipStatus.SUSPENDED for m in result.memberships)

    @pytest.mark.asyncio
    async def test_list_by_tier(self, membership_service, gold_membership):
        """Test listing memberships by tier"""
        result = await membership_service.list_memberships(
            tier_code=MembershipTier.GOLD
        )

        assert result.success is True
        assert all(m.tier_code == MembershipTier.GOLD for m in result.memberships)

    @pytest.mark.asyncio
    async def test_list_pagination(self, membership_service, mock_repository):
        """Test listing with pagination"""
        # Create multiple memberships
        for i in range(10):
            await mock_repository.create_membership(
                user_id=f"page_user_{i}",
                tier_code="bronze"
            )

        result = await membership_service.list_memberships(
            page=1,
            page_size=5
        )

        assert result.success is True
        assert len(result.memberships) == 5
        assert result.page == 1
        assert result.page_size == 5


class TestCancelMembership:
    """Tests for cancel_membership method"""

    @pytest.mark.asyncio
    async def test_cancel_membership_success(self, membership_service, sample_membership):
        """Test canceling membership"""
        result = await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Moving to another service"
        )

        assert result.success is True
        assert result.membership.status == MembershipStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_membership(self, membership_service):
        """Test canceling non-existent membership"""
        result = await membership_service.cancel_membership(
            membership_id="nonexistent",
            reason="Test"
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_already_canceled(self, membership_service, mock_repository, sample_membership):
        """Test canceling already canceled membership"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.CANCELED
        )

        result = await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Again"
        )

        assert result.success is False
        assert "already canceled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_creates_history(self, membership_service, sample_membership, mock_repository):
        """Test cancellation creates history entry"""
        result = await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Moving"
        )

        assert result.success is True
        history = await mock_repository.get_history(sample_membership.membership_id)
        canceled = [h for h in history if h.action == PointAction.CANCELED]
        assert len(canceled) >= 1

    @pytest.mark.asyncio
    async def test_cancel_publishes_event(self, membership_service, sample_membership, mock_event_bus):
        """Test cancellation publishes event"""
        result = await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Test"
        )

        assert result.success is True
        events = [e for e in mock_event_bus.published_events if "canceled" in e["subject"]]
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_cancel_with_feedback(self, membership_service, sample_membership):
        """Test cancellation with feedback"""
        result = await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Moving",
            feedback="Great service, just don't need it anymore"
        )

        assert result.success is True


class TestSuspendMembership:
    """Tests for suspend_membership method"""

    @pytest.mark.asyncio
    async def test_suspend_membership_success(self, membership_service, sample_membership):
        """Test suspending membership"""
        result = await membership_service.suspend_membership(
            membership_id=sample_membership.membership_id,
            reason="Policy violation"
        )

        assert result.success is True
        assert result.membership.status == MembershipStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_suspend_nonexistent_membership(self, membership_service):
        """Test suspending non-existent membership"""
        result = await membership_service.suspend_membership(
            membership_id="nonexistent",
            reason="Test"
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_suspend_already_suspended(self, membership_service, mock_repository, sample_membership):
        """Test suspending already suspended membership"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.suspend_membership(
            membership_id=sample_membership.membership_id,
            reason="Again"
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_suspend_with_duration(self, membership_service, sample_membership, mock_repository):
        """Test suspension with duration"""
        result = await membership_service.suspend_membership(
            membership_id=sample_membership.membership_id,
            reason="Temporary",
            duration_days=30
        )

        assert result.success is True
        history = await mock_repository.get_history(sample_membership.membership_id)
        suspended = [h for h in history if h.action == PointAction.SUSPENDED]
        assert len(suspended) >= 1

    @pytest.mark.asyncio
    async def test_suspend_publishes_event(self, membership_service, sample_membership, mock_event_bus):
        """Test suspension publishes event"""
        result = await membership_service.suspend_membership(
            membership_id=sample_membership.membership_id,
            reason="Test"
        )

        assert result.success is True
        events = [e for e in mock_event_bus.published_events if "suspended" in e["subject"]]
        assert len(events) >= 1


class TestReactivateMembership:
    """Tests for reactivate_membership method"""

    @pytest.mark.asyncio
    async def test_reactivate_membership_success(self, membership_service, mock_repository, sample_membership):
        """Test reactivating suspended membership"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.reactivate_membership(
            sample_membership.membership_id
        )

        assert result.success is True
        assert result.membership.status == MembershipStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_reactivate_nonexistent_membership(self, membership_service):
        """Test reactivating non-existent membership"""
        result = await membership_service.reactivate_membership("nonexistent")

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reactivate_active_membership(self, membership_service, sample_membership):
        """Test reactivating already active membership fails"""
        result = await membership_service.reactivate_membership(
            sample_membership.membership_id
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_reactivate_creates_history(self, membership_service, mock_repository, sample_membership):
        """Test reactivation creates history entry"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.reactivate_membership(
            sample_membership.membership_id
        )

        assert result.success is True
        history = await mock_repository.get_history(sample_membership.membership_id)
        reactivated = [h for h in history if h.action == PointAction.REACTIVATED]
        assert len(reactivated) >= 1

    @pytest.mark.asyncio
    async def test_reactivate_publishes_event(self, membership_service, mock_repository, sample_membership, mock_event_bus):
        """Test reactivation publishes event"""
        await mock_repository.update_status(
            sample_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.reactivate_membership(
            sample_membership.membership_id
        )

        assert result.success is True
        events = [e for e in mock_event_bus.published_events if "reactivated" in e["subject"]]
        assert len(events) >= 1
