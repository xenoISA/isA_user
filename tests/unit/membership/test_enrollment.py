"""
Unit Tests for Membership Enrollment

Tests for enrollment business logic.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from microservices.membership_service.models import (
    MembershipStatus,
    MembershipTier,
    PointAction,
)


class TestEnrollMembership:
    """Tests for enroll_membership method"""

    @pytest.mark.asyncio
    async def test_enroll_new_membership_success(self, membership_service, mock_repository):
        """Test successful enrollment"""
        result = await membership_service.enroll_membership(
            user_id="new_user_123"
        )

        assert result.success is True
        assert result.membership is not None
        assert result.membership.user_id == "new_user_123"
        assert result.membership.tier_code == MembershipTier.BRONZE
        assert result.membership.status == MembershipStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_enroll_with_promo_code_welcome100(self, membership_service):
        """Test enrollment with WELCOME100 promo code"""
        result = await membership_service.enroll_membership(
            user_id="new_user_456",
            promo_code="WELCOME100"
        )

        assert result.success is True
        assert result.enrollment_bonus == 100
        assert result.membership.points_balance == 100

    @pytest.mark.asyncio
    async def test_enroll_with_promo_code_welcome500(self, membership_service):
        """Test enrollment with WELCOME500 promo code"""
        result = await membership_service.enroll_membership(
            user_id="new_user_789",
            promo_code="WELCOME500"
        )

        assert result.success is True
        assert result.enrollment_bonus == 500

    @pytest.mark.asyncio
    async def test_enroll_with_promo_code_vip1000(self, membership_service):
        """Test enrollment with VIP1000 promo code"""
        result = await membership_service.enroll_membership(
            user_id="vip_user",
            promo_code="VIP1000"
        )

        assert result.success is True
        assert result.enrollment_bonus == 1000

    @pytest.mark.asyncio
    async def test_enroll_with_invalid_promo_code(self, membership_service):
        """Test enrollment with invalid promo code gives 0 bonus"""
        result = await membership_service.enroll_membership(
            user_id="new_user_abc",
            promo_code="INVALID_CODE"
        )

        assert result.success is True
        assert result.enrollment_bonus == 0

    @pytest.mark.asyncio
    async def test_enroll_duplicate_fails(self, membership_service, sample_membership):
        """Test enrolling duplicate user fails"""
        result = await membership_service.enroll_membership(
            user_id="user_123"  # Already has membership from sample_membership
        )

        assert result.success is False
        assert "already has active" in result.message.lower()

    @pytest.mark.asyncio
    async def test_enroll_with_organization(self, membership_service):
        """Test enrollment with organization"""
        result = await membership_service.enroll_membership(
            user_id="org_user_123",
            organization_id="org_456"
        )

        assert result.success is True
        assert result.membership.organization_id == "org_456"

    @pytest.mark.asyncio
    async def test_enroll_same_user_different_org(self, membership_service, sample_membership):
        """Test same user can enroll in different org"""
        result = await membership_service.enroll_membership(
            user_id="user_123",
            organization_id="org_different"
        )

        assert result.success is True
        assert result.membership.organization_id == "org_different"

    @pytest.mark.asyncio
    async def test_enroll_with_metadata(self, membership_service):
        """Test enrollment with metadata"""
        result = await membership_service.enroll_membership(
            user_id="meta_user",
            metadata={"source": "mobile_app", "campaign": "summer2025"}
        )

        assert result.success is True
        assert result.membership.metadata.get("source") == "mobile_app"

    @pytest.mark.asyncio
    async def test_enroll_with_enrollment_source(self, membership_service):
        """Test enrollment source tracking"""
        result = await membership_service.enroll_membership(
            user_id="source_user",
            enrollment_source="mobile_app"
        )

        assert result.success is True
        assert result.membership.enrollment_source == "mobile_app"

    @pytest.mark.asyncio
    async def test_enroll_creates_history_entry(self, membership_service, mock_repository):
        """Test enrollment creates history entry"""
        result = await membership_service.enroll_membership(
            user_id="history_user"
        )

        assert result.success is True
        history = await mock_repository.get_history(result.membership.membership_id)
        assert len(history) == 1
        assert history[0].action == PointAction.ENROLLED

    @pytest.mark.asyncio
    async def test_enroll_sets_expiration_date(self, membership_service):
        """Test enrollment sets expiration date"""
        result = await membership_service.enroll_membership(
            user_id="expiry_user"
        )

        assert result.success is True
        assert result.membership.expiration_date is not None
        # Should be about 1 year in future
        now = datetime.now(timezone.utc)
        diff = result.membership.expiration_date - now
        assert 360 < diff.days < 370

    @pytest.mark.asyncio
    async def test_enroll_publishes_event(self, membership_service, mock_event_bus):
        """Test enrollment publishes event"""
        result = await membership_service.enroll_membership(
            user_id="event_user"
        )

        assert result.success is True
        assert len(mock_event_bus.published_events) == 1
        event = mock_event_bus.published_events[0]
        assert event["subject"] == "membership.enrolled"
        assert event["data"]["data"]["user_id"] == "event_user"

    @pytest.mark.asyncio
    async def test_enroll_lowercase_promo_code(self, membership_service):
        """Test promo code is case insensitive"""
        result = await membership_service.enroll_membership(
            user_id="lower_user",
            promo_code="welcome100"
        )

        assert result.success is True
        assert result.enrollment_bonus == 100


class TestEnrollmentBonusCalculation:
    """Tests for enrollment bonus calculation"""

    @pytest.mark.asyncio
    async def test_bonus_none_promo(self, membership_service):
        """Test no bonus with None promo code"""
        bonus = membership_service._calculate_enrollment_bonus(None)
        assert bonus == 0

    @pytest.mark.asyncio
    async def test_bonus_empty_promo(self, membership_service):
        """Test no bonus with empty promo code"""
        bonus = membership_service._calculate_enrollment_bonus("")
        assert bonus == 0

    @pytest.mark.asyncio
    async def test_bonus_welcome100(self, membership_service):
        """Test WELCOME100 bonus"""
        bonus = membership_service._calculate_enrollment_bonus("WELCOME100")
        assert bonus == 100

    @pytest.mark.asyncio
    async def test_bonus_welcome500(self, membership_service):
        """Test WELCOME500 bonus"""
        bonus = membership_service._calculate_enrollment_bonus("WELCOME500")
        assert bonus == 500

    @pytest.mark.asyncio
    async def test_bonus_vip1000(self, membership_service):
        """Test VIP1000 bonus"""
        bonus = membership_service._calculate_enrollment_bonus("VIP1000")
        assert bonus == 1000

    @pytest.mark.asyncio
    async def test_bonus_invalid_code(self, membership_service):
        """Test invalid code returns 0"""
        bonus = membership_service._calculate_enrollment_bonus("NOTACODE")
        assert bonus == 0

    @pytest.mark.asyncio
    async def test_bonus_case_insensitive(self, membership_service):
        """Test promo codes are case insensitive"""
        bonus1 = membership_service._calculate_enrollment_bonus("welcome100")
        bonus2 = membership_service._calculate_enrollment_bonus("Welcome100")
        bonus3 = membership_service._calculate_enrollment_bonus("WELCOME100")
        assert bonus1 == bonus2 == bonus3 == 100
