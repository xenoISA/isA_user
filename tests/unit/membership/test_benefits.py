"""
Unit Tests for Benefits Management

Tests for benefit availability and usage.
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
    TierBenefit,
)


class TestGetBenefits:
    """Tests for get_benefits method"""

    @pytest.mark.asyncio
    async def test_get_benefits_success(self, membership_service, gold_membership):
        """Test getting benefits for gold membership"""
        result = await membership_service.get_benefits(
            gold_membership.membership_id
        )

        assert result.success is True
        assert len(result.benefits) > 0
        assert result.tier_code == MembershipTier.GOLD

    @pytest.mark.asyncio
    async def test_get_benefits_not_found(self, membership_service):
        """Test getting benefits for non-existent membership"""
        result = await membership_service.get_benefits("nonexistent_id")

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_get_benefits_bronze_tier(self, membership_service, sample_membership):
        """Test getting benefits for bronze tier"""
        result = await membership_service.get_benefits(
            sample_membership.membership_id
        )

        assert result.success is True
        assert result.tier_code == MembershipTier.BRONZE

    @pytest.mark.asyncio
    async def test_benefits_include_usage_info(self, membership_service, gold_membership):
        """Test benefits include usage information"""
        result = await membership_service.get_benefits(
            gold_membership.membership_id
        )

        assert result.success is True
        for benefit in result.benefits:
            assert hasattr(benefit, 'used_count')
            assert hasattr(benefit, 'is_available')


class TestUseBenefit:
    """Tests for use_benefit method"""

    @pytest.mark.asyncio
    async def test_use_benefit_success(self, membership_service, gold_membership):
        """Test using a benefit successfully"""
        result = await membership_service.use_benefit(
            membership_id=gold_membership.membership_id,
            benefit_code="FREE_SHIPPING"
        )

        assert result.success is True
        assert result.benefit_code == "FREE_SHIPPING"

    @pytest.mark.asyncio
    async def test_use_benefit_membership_not_found(self, membership_service):
        """Test using benefit with non-existent membership"""
        result = await membership_service.use_benefit(
            membership_id="nonexistent",
            benefit_code="FREE_SHIPPING"
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_use_benefit_not_available_at_tier(self, membership_service, sample_membership):
        """Test using benefit not available at tier"""
        # Bronze tier doesn't have EARLY_ACCESS benefit
        result = await membership_service.use_benefit(
            membership_id=sample_membership.membership_id,
            benefit_code="EARLY_ACCESS"
        )

        assert result.success is False
        assert "not available" in result.message.lower()

    @pytest.mark.asyncio
    async def test_use_benefit_suspended_membership(self, membership_service, mock_repository, gold_membership):
        """Test using benefit with suspended membership"""
        await mock_repository.update_status(
            gold_membership.membership_id,
            MembershipStatus.SUSPENDED
        )

        result = await membership_service.use_benefit(
            membership_id=gold_membership.membership_id,
            benefit_code="FREE_SHIPPING"
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_use_benefit_with_limit(self, membership_service, mock_repository):
        """Test using benefit with usage limit"""
        # Create silver membership with LIMITED shipping benefit
        membership = await mock_repository.create_membership(
            user_id="limited_user",
            tier_code="silver"
        )

        # Use benefit 3 times (limit is 3)
        for i in range(3):
            result = await membership_service.use_benefit(
                membership_id=membership.membership_id,
                benefit_code="FREE_SHIPPING"
            )
            assert result.success is True

        # 4th use should fail
        result = await membership_service.use_benefit(
            membership_id=membership.membership_id,
            benefit_code="FREE_SHIPPING"
        )
        assert result.success is False
        assert "limit exceeded" in result.message.lower()

    @pytest.mark.asyncio
    async def test_use_unlimited_benefit_many_times(self, membership_service, gold_membership):
        """Test using unlimited benefit many times"""
        # FREE_SHIPPING is unlimited for gold tier
        for i in range(10):
            result = await membership_service.use_benefit(
                membership_id=gold_membership.membership_id,
                benefit_code="FREE_SHIPPING"
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_use_benefit_records_history(self, membership_service, gold_membership, mock_repository):
        """Test benefit usage creates history entry"""
        result = await membership_service.use_benefit(
            membership_id=gold_membership.membership_id,
            benefit_code="FREE_SHIPPING"
        )

        assert result.success is True
        history = await mock_repository.get_history(gold_membership.membership_id)
        benefit_used = [h for h in history if h.action == PointAction.BENEFIT_USED]
        assert len(benefit_used) >= 1
        assert benefit_used[0].benefit_code == "FREE_SHIPPING"

    @pytest.mark.asyncio
    async def test_use_benefit_publishes_event(self, membership_service, gold_membership, mock_event_bus):
        """Test benefit usage publishes event"""
        result = await membership_service.use_benefit(
            membership_id=gold_membership.membership_id,
            benefit_code="FREE_SHIPPING"
        )

        assert result.success is True
        events = [e for e in mock_event_bus.published_events if "benefit.used" in e["subject"]]
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_use_benefit_returns_remaining(self, membership_service, mock_repository):
        """Test benefit usage returns remaining uses"""
        membership = await mock_repository.create_membership(
            user_id="remaining_user",
            tier_code="silver"
        )

        result = await membership_service.use_benefit(
            membership_id=membership.membership_id,
            benefit_code="FREE_SHIPPING"  # Limit of 3 for silver
        )

        assert result.success is True
        assert result.remaining_uses == 2


class TestGetMembershipBenefits:
    """Tests for _get_membership_benefits helper"""

    @pytest.mark.asyncio
    async def test_benefits_marked_available(self, membership_service, gold_membership):
        """Test benefits correctly marked as available"""
        benefits = await membership_service._get_membership_benefits(gold_membership)

        assert len(benefits) > 0
        for benefit in benefits:
            if benefit.is_unlimited:
                assert benefit.is_available is True
            elif benefit.remaining is not None and benefit.remaining > 0:
                assert benefit.is_available is True

    @pytest.mark.asyncio
    async def test_benefits_usage_counted(self, membership_service, gold_membership, mock_repository):
        """Test benefits usage is correctly counted"""
        # Use a benefit
        await mock_repository.record_benefit_usage(
            gold_membership.membership_id,
            "FREE_SHIPPING"
        )

        benefits = await membership_service._get_membership_benefits(gold_membership)

        shipping = next((b for b in benefits if b.benefit_code == "FREE_SHIPPING"), None)
        assert shipping is not None
        assert shipping.used_count == 1


class TestBenefitTypes:
    """Tests for different benefit types"""

    @pytest.mark.asyncio
    async def test_service_benefit(self, membership_service, gold_membership):
        """Test service type benefit"""
        result = await membership_service.get_benefits(
            gold_membership.membership_id
        )

        service_benefits = [b for b in result.benefits if b.benefit_type == "service"]
        assert len(service_benefits) > 0

    @pytest.mark.asyncio
    async def test_discount_benefit(self, membership_service, gold_membership):
        """Test discount type benefit"""
        result = await membership_service.get_benefits(
            gold_membership.membership_id
        )

        discount_benefits = [b for b in result.benefits if b.benefit_type == "discount"]
        assert len(discount_benefits) > 0

    @pytest.mark.asyncio
    async def test_access_benefit(self, membership_service, gold_membership):
        """Test access type benefit"""
        result = await membership_service.get_benefits(
            gold_membership.membership_id
        )

        access_benefits = [b for b in result.benefits if b.benefit_type == "access"]
        assert len(access_benefits) > 0
