"""
Membership Service Integration Tests - CRUD Operations

Tests the MembershipService CRUD operations with mocked dependencies.
These tests verify membership management operations.

Usage:
    pytest tests/integration/tdd/membership/test_membership_crud_integration.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

# Import from centralized data contracts
from tests.contracts.membership.data_contract import (
    MembershipTestDataFactory,
    MembershipStatusContract,
)

# Import service and models
from microservices.membership_service.membership_service import MembershipService
from microservices.membership_service.models import (
    Membership,
    MembershipStatus,
    MembershipTier,
    CancelMembershipRequest,
    SuspendMembershipRequest,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Get Membership Tests (4 tests)
# ============================================================================

class TestGetMembershipIntegration:
    """Integration tests for getting membership."""

    async def test_get_membership_by_id_success(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Gets membership by ID successfully."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )

        result = await membership_service.get_membership(
            membership_id=sample_membership.membership_id
        )

        assert result.success is True
        assert result.membership.membership_id == sample_membership.membership_id

    async def test_get_membership_by_user_id_success(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Gets membership by user ID successfully."""
        mock_membership_repository.get_membership_by_user = AsyncMock(
            return_value=sample_membership
        )

        result = await membership_service.get_membership_by_user(
            user_id=sample_membership.user_id
        )

        assert result.success is True
        assert result.membership.user_id == sample_membership.user_id

    async def test_get_membership_not_found(
        self, membership_service, mock_membership_repository
    ):
        """Returns failure when membership not found."""
        mock_membership_repository.get_membership = AsyncMock(return_value=None)

        result = await membership_service.get_membership(
            membership_id="nonexistent"
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_get_membership_includes_all_fields(
        self, membership_service, mock_membership_repository, gold_membership
    ):
        """Returns membership with all required fields."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=gold_membership
        )

        result = await membership_service.get_membership(
            membership_id=gold_membership.membership_id
        )

        assert result.success is True
        assert result.membership.tier_code is not None
        assert result.membership.status is not None
        assert result.membership.points_balance >= 0


# ============================================================================
# List Memberships Tests (4 tests)
# ============================================================================

class TestListMembershipsIntegration:
    """Integration tests for listing memberships."""

    async def test_list_memberships_success(
        self, membership_service, mock_membership_repository, sample_membership, gold_membership
    ):
        """Lists memberships successfully."""
        mock_membership_repository.list_memberships = AsyncMock(
            return_value=[sample_membership, gold_membership]
        )
        mock_membership_repository.count_memberships = AsyncMock(return_value=2)

        result = await membership_service.list_memberships()

        assert result.success is True
        assert len(result.memberships) == 2

    async def test_list_memberships_by_status(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Lists memberships filtered by status."""
        mock_membership_repository.list_memberships = AsyncMock(
            return_value=[sample_membership]
        )
        mock_membership_repository.count_memberships = AsyncMock(return_value=1)

        result = await membership_service.list_memberships(
            status=MembershipStatus.ACTIVE
        )

        assert result.success is True
        assert all(m.status == MembershipStatus.ACTIVE for m in result.memberships)

    async def test_list_memberships_empty(
        self, membership_service, mock_membership_repository
    ):
        """Returns empty list when no memberships found."""
        mock_membership_repository.list_memberships = AsyncMock(return_value=[])
        mock_membership_repository.count_memberships = AsyncMock(return_value=0)

        result = await membership_service.list_memberships()

        assert result.success is True
        assert len(result.memberships) == 0

    async def test_list_memberships_pagination(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Lists memberships with pagination."""
        mock_membership_repository.list_memberships = AsyncMock(
            return_value=[sample_membership]
        )
        mock_membership_repository.count_memberships = AsyncMock(return_value=10)  # 10 total

        result = await membership_service.list_memberships(page=1, page_size=1)

        assert result.success is True
        assert result.total == 10


# ============================================================================
# Cancel Membership Tests (5 tests)
# ============================================================================

class TestCancelMembershipIntegration:
    """Integration tests for canceling membership."""

    async def test_cancel_membership_success(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Cancels membership successfully."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )

        canceled_membership = Membership(
            **{**sample_membership.__dict__,
               "status": MembershipStatus.CANCELED}
        )
        mock_membership_repository.update_status = AsyncMock(
            return_value=canceled_membership
        )
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Not using anymore"
        )

        assert result.success is True
        assert result.membership.status == MembershipStatus.CANCELED

    async def test_cancel_membership_not_found(
        self, membership_service, mock_membership_repository
    ):
        """Fails to cancel when membership not found."""
        mock_membership_repository.get_membership = AsyncMock(return_value=None)

        result = await membership_service.cancel_membership(
            membership_id="nonexistent",
            reason="Test"
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_cancel_already_canceled(
        self, membership_service, mock_membership_repository
    ):
        """Fails to cancel already canceled membership."""
        canceled_membership = Membership(
            membership_id=MembershipTestDataFactory.make_membership_id(),
            user_id=MembershipTestDataFactory.make_user_id(),
            tier_code=MembershipTier.BRONZE,
            status=MembershipStatus.CANCELED,
            points_balance=0,
            tier_points=0,
            lifetime_points=1000,
            enrolled_at=datetime.now(timezone.utc),
        )

        mock_membership_repository.get_membership = AsyncMock(
            return_value=canceled_membership
        )

        result = await membership_service.cancel_membership(
            membership_id=canceled_membership.membership_id,
            reason="Test"
        )

        assert result.success is False

    async def test_cancel_with_forfeit_points(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Cancels membership and forfeits points."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )

        canceled_membership = Membership(
            **{**sample_membership.__dict__,
               "status": MembershipStatus.CANCELED,
               "points_balance": 0}  # Points forfeited
        )
        mock_membership_repository.update_status = AsyncMock(
            return_value=canceled_membership
        )
        mock_membership_repository.deduct_points = AsyncMock(
            return_value=canceled_membership
        )
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Leaving",
            forfeit_points=True
        )

        assert result.success is True

    async def test_cancel_publishes_event(
        self, membership_service, mock_membership_repository, mock_event_bus, sample_membership
    ):
        """Cancellation publishes event."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )

        canceled_membership = Membership(
            **{**sample_membership.__dict__,
               "status": MembershipStatus.CANCELED}
        )
        mock_membership_repository.update_status = AsyncMock(
            return_value=canceled_membership
        )
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.cancel_membership(
            membership_id=sample_membership.membership_id,
            reason="Test"
        )

        assert len(mock_event_bus.published_events) > 0


# ============================================================================
# Suspend/Reactivate Membership Tests (6 tests)
# ============================================================================

class TestSuspendReactivateIntegration:
    """Integration tests for suspending and reactivating membership."""

    async def test_suspend_membership_success(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Suspends membership successfully."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )

        suspended_membership = Membership(
            **{**sample_membership.__dict__,
               "status": MembershipStatus.SUSPENDED}
        )
        mock_membership_repository.update_status = AsyncMock(
            return_value=suspended_membership
        )
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.suspend_membership(
            membership_id=sample_membership.membership_id,
            reason="Policy violation"
        )

        assert result.success is True
        assert result.membership.status == MembershipStatus.SUSPENDED

    async def test_suspend_membership_not_found(
        self, membership_service, mock_membership_repository
    ):
        """Fails to suspend when membership not found."""
        mock_membership_repository.get_membership = AsyncMock(return_value=None)

        result = await membership_service.suspend_membership(
            membership_id="nonexistent",
            reason="Test"
        )

        assert result.success is False

    async def test_suspend_already_suspended(
        self, membership_service, mock_membership_repository, suspended_membership
    ):
        """Fails to suspend already suspended membership."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=suspended_membership
        )

        result = await membership_service.suspend_membership(
            membership_id=suspended_membership.membership_id,
            reason="Test"
        )

        assert result.success is False

    async def test_reactivate_membership_success(
        self, membership_service, mock_membership_repository, suspended_membership
    ):
        """Reactivates suspended membership successfully."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=suspended_membership
        )

        reactivated_membership = Membership(
            **{**suspended_membership.__dict__,
               "status": MembershipStatus.ACTIVE}
        )
        mock_membership_repository.update_status = AsyncMock(
            return_value=reactivated_membership
        )
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.reactivate_membership(
            membership_id=suspended_membership.membership_id
        )

        assert result.success is True
        assert result.membership.status == MembershipStatus.ACTIVE

    async def test_reactivate_not_suspended_fails(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Fails to reactivate non-suspended membership."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership  # Already active
        )

        result = await membership_service.reactivate_membership(
            membership_id=sample_membership.membership_id
        )

        assert result.success is False

    async def test_suspend_publishes_event(
        self, membership_service, mock_membership_repository, mock_event_bus, sample_membership
    ):
        """Suspension publishes event."""
        mock_membership_repository.get_membership = AsyncMock(
            return_value=sample_membership
        )

        suspended_membership = Membership(
            **{**sample_membership.__dict__,
               "status": MembershipStatus.SUSPENDED}
        )
        mock_membership_repository.update_status = AsyncMock(
            return_value=suspended_membership
        )
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.suspend_membership(
            membership_id=sample_membership.membership_id,
            reason="Test"
        )

        assert len(mock_event_bus.published_events) > 0
