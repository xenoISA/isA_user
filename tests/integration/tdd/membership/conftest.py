"""
Membership Service Integration Test Fixtures

Provides fixtures for testing MembershipService with mocked dependencies.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Import from centralized data contracts
from tests.contracts.membership.data_contract import (
    MembershipTestDataFactory,
    MembershipTierContract,
    MembershipStatusContract,
    PointActionContract,
)

# Import service layer to test
from microservices.membership_service.membership_service import MembershipService

# Import protocols
from microservices.membership_service.protocols import (
    MembershipRepositoryProtocol,
    EventBusProtocol,
)

# Import models
from microservices.membership_service.models import (
    Membership,
    MembershipHistory,
    Tier,
    TierBenefit,
    BenefitUsage,
    MembershipStatus,
    MembershipTier,
    PointAction,
)


@pytest.fixture
def mock_membership_repository():
    """Mock membership repository for testing service layer."""
    repo = AsyncMock(spec=MembershipRepositoryProtocol)
    repo._memberships = {}
    repo._history = {}
    repo._benefit_usage = {}
    repo._tiers = {
        "bronze": Tier(
            tier_code=MembershipTier.BRONZE,
            tier_name="Bronze",
            display_order=1,
            qualification_threshold=0,
            point_multiplier=Decimal("1.0"),
        ),
        "silver": Tier(
            tier_code=MembershipTier.SILVER,
            tier_name="Silver",
            display_order=2,
            qualification_threshold=5000,
            point_multiplier=Decimal("1.25"),
        ),
        "gold": Tier(
            tier_code=MembershipTier.GOLD,
            tier_name="Gold",
            display_order=3,
            qualification_threshold=20000,
            point_multiplier=Decimal("1.5"),
        ),
        "platinum": Tier(
            tier_code=MembershipTier.PLATINUM,
            tier_name="Platinum",
            display_order=4,
            qualification_threshold=50000,
            point_multiplier=Decimal("2.0"),
        ),
        "diamond": Tier(
            tier_code=MembershipTier.DIAMOND,
            tier_name="Diamond",
            display_order=5,
            qualification_threshold=100000,
            point_multiplier=Decimal("3.0"),
        ),
    }
    repo._benefits = {
        "bronze": [
            TierBenefit(
                benefit_id="bnft_bronze_1",
                tier_code=MembershipTier.BRONZE,
                benefit_code="BASIC_SUPPORT",
                benefit_name="Basic Support",
                benefit_type="service",
                is_unlimited=True,
            )
        ],
        "silver": [
            TierBenefit(
                benefit_id="bnft_silver_1",
                tier_code=MembershipTier.SILVER,
                benefit_code="PRIORITY_SUPPORT",
                benefit_name="Priority Support",
                benefit_type="service",
                is_unlimited=True,
            ),
            TierBenefit(
                benefit_id="bnft_silver_2",
                tier_code=MembershipTier.SILVER,
                benefit_code="FREE_SHIPPING",
                benefit_name="Free Shipping",
                benefit_type="discount",
                usage_limit=3,
                is_unlimited=False,
            ),
        ],
        "gold": [
            TierBenefit(
                benefit_id="bnft_gold_1",
                tier_code=MembershipTier.GOLD,
                benefit_code="PRIORITY_SUPPORT",
                benefit_name="Priority Support",
                benefit_type="service",
                is_unlimited=True,
            ),
            TierBenefit(
                benefit_id="bnft_gold_2",
                tier_code=MembershipTier.GOLD,
                benefit_code="FREE_SHIPPING",
                benefit_name="Free Shipping",
                benefit_type="discount",
                is_unlimited=True,
            ),
            TierBenefit(
                benefit_id="bnft_gold_3",
                tier_code=MembershipTier.GOLD,
                benefit_code="EARLY_ACCESS",
                benefit_name="Early Access",
                benefit_type="access",
                is_unlimited=True,
            ),
        ],
    }
    return repo


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing."""
    bus = AsyncMock(spec=EventBusProtocol)
    bus.published_events = []

    async def capture_event(event_type: str, data: Dict[str, Any]):
        bus.published_events.append({"event_type": event_type, "data": data})

    bus.publish = AsyncMock(side_effect=capture_event)
    return bus


@pytest.fixture
def membership_service(mock_membership_repository, mock_event_bus):
    """Create MembershipService with mocked dependencies."""
    return MembershipService(
        repository=mock_membership_repository,
        event_bus=mock_event_bus,
    )


@pytest.fixture
def sample_membership():
    """Create a sample membership for testing."""
    return Membership(
        membership_id=MembershipTestDataFactory.make_membership_id(),
        user_id=MembershipTestDataFactory.make_user_id(),
        tier_code=MembershipTier.BRONZE,
        status=MembershipStatus.ACTIVE,
        points_balance=1000,
        tier_points=1000,
        lifetime_points=1000,
        enrolled_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def gold_membership():
    """Create a gold tier membership for testing."""
    return Membership(
        membership_id=MembershipTestDataFactory.make_membership_id(),
        user_id=MembershipTestDataFactory.make_user_id(),
        tier_code=MembershipTier.GOLD,
        status=MembershipStatus.ACTIVE,
        points_balance=25000,
        tier_points=25000,
        lifetime_points=30000,
        enrolled_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def suspended_membership():
    """Create a suspended membership for testing."""
    return Membership(
        membership_id=MembershipTestDataFactory.make_membership_id(),
        user_id=MembershipTestDataFactory.make_user_id(),
        tier_code=MembershipTier.SILVER,
        status=MembershipStatus.SUSPENDED,
        points_balance=8000,
        tier_points=8000,
        lifetime_points=10000,
        enrolled_at=datetime.now(timezone.utc),
    )
