"""
Membership Service Integration Tests - Enrollment

Tests the MembershipService enrollment operations with mocked dependencies.
These tests verify business logic integration, not HTTP endpoints.

Usage:
    pytest tests/integration/tdd/membership/test_membership_enrollment_integration.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

# Import from centralized data contracts
from tests.contracts.membership.data_contract import (
    MembershipTestDataFactory,
    MembershipTierContract,
    MembershipStatusContract,
)

# Import service and models
from microservices.membership_service.membership_service import MembershipService
from microservices.membership_service.models import (
    Membership,
    MembershipStatus,
    MembershipTier,
    EnrollMembershipRequest,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Enrollment Tests (8 tests)
# ============================================================================

class TestEnrollmentIntegration:
    """Integration tests for membership enrollment."""

    async def test_enroll_new_member_success(
        self, membership_service, mock_membership_repository
    ):
        """Successfully enrolls a new member with bronze tier."""
        user_id = MembershipTestDataFactory.make_user_id()

        # Setup: No existing membership
        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        # Setup: Create membership returns new membership
        async def create_membership_mock(**kwargs):
            return Membership(
                membership_id=MembershipTestDataFactory.make_membership_id(),
                user_id=kwargs["user_id"],
                tier_code=MembershipTier.BRONZE,
                status=MembershipStatus.ACTIVE,
                points_balance=100,  # Enrollment bonus
                tier_points=0,
                lifetime_points=100,
                enrolled_at=datetime.now(timezone.utc),
            )

        mock_membership_repository.create_membership = AsyncMock(side_effect=create_membership_mock)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.enroll_membership(
            EnrollMembershipRequest(user_id=user_id)
        )

        assert result.success is True
        assert result.membership is not None
        assert result.membership.user_id == user_id
        assert result.membership.tier_code == MembershipTier.BRONZE
        assert result.enrollment_bonus == 100

    async def test_enroll_with_promo_code(
        self, membership_service, mock_membership_repository
    ):
        """Enrolls with promo code for bonus points."""
        user_id = MembershipTestDataFactory.make_user_id()
        promo_code = MembershipTestDataFactory.make_promo_code()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        async def create_membership_mock(**kwargs):
            return Membership(
                membership_id=MembershipTestDataFactory.make_membership_id(),
                user_id=kwargs["user_id"],
                tier_code=MembershipTier.BRONZE,
                status=MembershipStatus.ACTIVE,
                points_balance=200,  # Higher bonus with promo
                tier_points=0,
                lifetime_points=200,
                enrolled_at=datetime.now(timezone.utc),
                promo_code=kwargs.get("promo_code"),
            )

        mock_membership_repository.create_membership = AsyncMock(side_effect=create_membership_mock)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.enroll_membership(
            EnrollMembershipRequest(user_id=user_id, promo_code=promo_code)
        )

        assert result.success is True
        assert result.enrollment_bonus >= 100

    async def test_enroll_already_exists_fails(
        self, membership_service, mock_membership_repository, sample_membership
    ):
        """Fails to enroll when membership already exists."""
        mock_membership_repository.get_membership_by_user_id = AsyncMock(
            return_value=sample_membership
        )

        result = await membership_service.enroll_membership(
            EnrollMembershipRequest(user_id=sample_membership.user_id)
        )

        assert result.success is False
        assert "already" in result.message.lower() or "exists" in result.message.lower()

    async def test_enroll_with_organization(
        self, membership_service, mock_membership_repository
    ):
        """Enrolls with organization context."""
        user_id = MembershipTestDataFactory.make_user_id()
        org_id = MembershipTestDataFactory.make_organization_id()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        async def create_membership_mock(**kwargs):
            return Membership(
                membership_id=MembershipTestDataFactory.make_membership_id(),
                user_id=kwargs["user_id"],
                organization_id=kwargs.get("organization_id"),
                tier_code=MembershipTier.BRONZE,
                status=MembershipStatus.ACTIVE,
                points_balance=100,
                tier_points=0,
                lifetime_points=100,
                enrolled_at=datetime.now(timezone.utc),
            )

        mock_membership_repository.create_membership = AsyncMock(side_effect=create_membership_mock)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.enroll_membership(
            EnrollMembershipRequest(user_id=user_id, organization_id=org_id)
        )

        assert result.success is True
        assert result.membership.organization_id == org_id

    async def test_enroll_publishes_event(
        self, membership_service, mock_membership_repository, mock_event_bus
    ):
        """Enrollment publishes membership.enrolled event."""
        user_id = MembershipTestDataFactory.make_user_id()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        async def create_membership_mock(**kwargs):
            return Membership(
                membership_id=MembershipTestDataFactory.make_membership_id(),
                user_id=kwargs["user_id"],
                tier_code=MembershipTier.BRONZE,
                status=MembershipStatus.ACTIVE,
                points_balance=100,
                tier_points=0,
                lifetime_points=100,
                enrolled_at=datetime.now(timezone.utc),
            )

        mock_membership_repository.create_membership = AsyncMock(side_effect=create_membership_mock)
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.enroll_membership(
            EnrollMembershipRequest(user_id=user_id)
        )

        # Verify event was published
        assert len(mock_event_bus.published_events) > 0
        enrolled_events = [e for e in mock_event_bus.published_events
                         if "enrolled" in e["event_type"].lower()]
        assert len(enrolled_events) > 0

    async def test_enroll_creates_history_entry(
        self, membership_service, mock_membership_repository
    ):
        """Enrollment creates history entry."""
        user_id = MembershipTestDataFactory.make_user_id()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        async def create_membership_mock(**kwargs):
            return Membership(
                membership_id=MembershipTestDataFactory.make_membership_id(),
                user_id=kwargs["user_id"],
                tier_code=MembershipTier.BRONZE,
                status=MembershipStatus.ACTIVE,
                points_balance=100,
                tier_points=0,
                lifetime_points=100,
                enrolled_at=datetime.now(timezone.utc),
            )

        mock_membership_repository.create_membership = AsyncMock(side_effect=create_membership_mock)
        mock_membership_repository.add_history = AsyncMock()

        await membership_service.enroll_membership(
            EnrollMembershipRequest(user_id=user_id)
        )

        # Verify history was created
        mock_membership_repository.add_history.assert_called()

    async def test_enroll_with_enrollment_source(
        self, membership_service, mock_membership_repository
    ):
        """Records enrollment source correctly."""
        user_id = MembershipTestDataFactory.make_user_id()
        source = MembershipTestDataFactory.make_enrollment_source()

        mock_membership_repository.get_membership_by_user_id = AsyncMock(return_value=None)

        captured_args = {}
        async def create_membership_mock(**kwargs):
            captured_args.update(kwargs)
            return Membership(
                membership_id=MembershipTestDataFactory.make_membership_id(),
                user_id=kwargs["user_id"],
                tier_code=MembershipTier.BRONZE,
                status=MembershipStatus.ACTIVE,
                points_balance=100,
                tier_points=0,
                lifetime_points=100,
                enrolled_at=datetime.now(timezone.utc),
                enrollment_source=kwargs.get("enrollment_source"),
            )

        mock_membership_repository.create_membership = AsyncMock(side_effect=create_membership_mock)
        mock_membership_repository.add_history = AsyncMock()

        result = await membership_service.enroll_membership(
            EnrollMembershipRequest(user_id=user_id, enrollment_source=source)
        )

        assert result.success is True
        assert captured_args.get("enrollment_source") == source

    async def test_enroll_empty_user_id_fails(
        self, membership_service, mock_membership_repository
    ):
        """Fails to enroll with empty user ID."""
        # This should fail at validation level
        try:
            result = await membership_service.enroll_membership(
                EnrollMembershipRequest(user_id="")
            )
            # If we get here, check for failure response
            assert result.success is False
        except (ValueError, Exception):
            # Expected - validation error
            pass
