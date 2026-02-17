"""
Unit Test Fixtures for Membership Service

Provides mock fixtures for unit testing.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from typing import List, Optional, Dict, Any

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from microservices.membership_service.models import (
    Membership,
    MembershipHistory,
    MembershipStatus,
    MembershipTier,
    PointAction,
    InitiatedBy,
    Tier,
    TierBenefit,
)
from microservices.membership_service.membership_service import MembershipService


# ====================
# Mock Repository
# ====================


class MockMembershipRepository:
    """Mock repository for unit testing"""

    def __init__(self):
        self.memberships: Dict[str, Membership] = {}
        self.history: List[MembershipHistory] = []
        self.tiers: Dict[str, Tier] = {}
        self.tier_benefits: Dict[str, List[TierBenefit]] = {}
        self.benefit_usage: Dict[str, Dict[str, int]] = {}
        self._counter = 0
        self._initialize_tiers()

    def _initialize_tiers(self):
        """Initialize default tiers"""
        self.tiers = {
            "bronze": Tier(tier_code=MembershipTier.BRONZE, tier_name="Bronze", qualification_threshold=0, point_multiplier=Decimal("1.0")),
            "silver": Tier(tier_code=MembershipTier.SILVER, tier_name="Silver", qualification_threshold=5000, point_multiplier=Decimal("1.25")),
            "gold": Tier(tier_code=MembershipTier.GOLD, tier_name="Gold", qualification_threshold=20000, point_multiplier=Decimal("1.5")),
            "platinum": Tier(tier_code=MembershipTier.PLATINUM, tier_name="Platinum", qualification_threshold=50000, point_multiplier=Decimal("2.0")),
            "diamond": Tier(tier_code=MembershipTier.DIAMOND, tier_name="Diamond", qualification_threshold=100000, point_multiplier=Decimal("3.0")),
        }

        # Default benefits
        self.tier_benefits = {
            "bronze": [
                TierBenefit(benefit_id="b1", tier_code=MembershipTier.BRONZE, benefit_code="BASIC_SUPPORT", benefit_name="Basic Support", benefit_type="service", is_unlimited=True)
            ],
            "silver": [
                TierBenefit(benefit_id="b2", tier_code=MembershipTier.SILVER, benefit_code="PRIORITY_SUPPORT", benefit_name="Priority Support", benefit_type="service", is_unlimited=True),
                TierBenefit(benefit_id="b3", tier_code=MembershipTier.SILVER, benefit_code="FREE_SHIPPING", benefit_name="Free Shipping", benefit_type="discount", usage_limit=3)
            ],
            "gold": [
                TierBenefit(benefit_id="b4", tier_code=MembershipTier.GOLD, benefit_code="PRIORITY_SUPPORT", benefit_name="Priority Support", benefit_type="service", is_unlimited=True),
                TierBenefit(benefit_id="b5", tier_code=MembershipTier.GOLD, benefit_code="FREE_SHIPPING", benefit_name="Free Shipping", benefit_type="discount", is_unlimited=True),
                TierBenefit(benefit_id="b6", tier_code=MembershipTier.GOLD, benefit_code="EARLY_ACCESS", benefit_name="Early Access", benefit_type="access", is_unlimited=True)
            ],
        }

    async def initialize(self):
        pass

    async def close(self):
        pass

    async def create_membership(self, user_id: str, tier_code: str, points_balance: int = 0, **kwargs) -> Membership:
        self._counter += 1
        now = datetime.now(timezone.utc)
        membership = Membership(
            id=self._counter,
            membership_id=f"mem_{self._counter:016d}",
            user_id=user_id,
            organization_id=kwargs.get("organization_id"),
            tier_code=MembershipTier(tier_code),
            status=MembershipStatus.ACTIVE,
            points_balance=points_balance,
            tier_points=kwargs.get("tier_points", 0),
            lifetime_points=points_balance,
            pending_points=0,
            enrolled_at=now,
            expiration_date=now + timedelta(days=365),
            last_activity_at=now,
            enrollment_source=kwargs.get("enrollment_source", "api"),
            promo_code=kwargs.get("promo_code"),
            metadata=kwargs.get("metadata", {}),
            created_at=now,
            updated_at=now
        )
        self.memberships[membership.membership_id] = membership
        return membership

    async def get_membership(self, membership_id: str) -> Optional[Membership]:
        return self.memberships.get(membership_id)

    async def get_membership_by_user(self, user_id: str, organization_id: Optional[str] = None, active_only: bool = True) -> Optional[Membership]:
        for m in self.memberships.values():
            if m.user_id == user_id:
                if organization_id is None and m.organization_id is None:
                    if not active_only or m.status in (MembershipStatus.ACTIVE, MembershipStatus.PENDING):
                        return m
                elif organization_id == m.organization_id:
                    if not active_only or m.status in (MembershipStatus.ACTIVE, MembershipStatus.PENDING):
                        return m
        return None

    async def list_memberships(self, user_id=None, organization_id=None, status=None, tier_code=None, limit=50, offset=0) -> List[Membership]:
        results = list(self.memberships.values())
        if user_id:
            results = [m for m in results if m.user_id == user_id]
        if organization_id:
            results = [m for m in results if m.organization_id == organization_id]
        if status:
            results = [m for m in results if m.status == status]
        if tier_code:
            results = [m for m in results if m.tier_code == tier_code]
        return results[offset:offset+limit]

    async def count_memberships(self, user_id=None, organization_id=None, status=None, tier_code=None) -> int:
        return len(await self.list_memberships(user_id, organization_id, status, tier_code))

    async def add_points(self, membership_id: str, points: int, tier_points: int, source: str, reference_id: Optional[str] = None) -> Membership:
        m = self.memberships.get(membership_id)
        if not m:
            raise Exception(f"Membership not found: {membership_id}")
        m.points_balance += points
        m.tier_points += tier_points
        m.lifetime_points += points
        m.last_activity_at = datetime.now(timezone.utc)
        m.updated_at = datetime.now(timezone.utc)
        return m

    async def deduct_points(self, membership_id: str, points: int, reward_code: str, description: Optional[str] = None) -> Membership:
        m = self.memberships.get(membership_id)
        if not m:
            raise Exception(f"Membership not found: {membership_id}")
        if m.points_balance < points:
            raise Exception(f"Insufficient points")
        m.points_balance -= points
        m.last_activity_at = datetime.now(timezone.utc)
        m.updated_at = datetime.now(timezone.utc)
        return m

    async def update_tier(self, membership_id: str, new_tier: str) -> Membership:
        m = self.memberships.get(membership_id)
        if not m:
            raise Exception(f"Membership not found: {membership_id}")
        m.tier_code = MembershipTier(new_tier)
        m.updated_at = datetime.now(timezone.utc)
        return m

    async def get_tier(self, tier_code: str) -> Optional[Tier]:
        return self.tiers.get(tier_code)

    async def get_all_tiers(self) -> List[Tier]:
        return list(self.tiers.values())

    async def update_status(self, membership_id: str, status: MembershipStatus, reason: Optional[str] = None) -> Membership:
        m = self.memberships.get(membership_id)
        if not m:
            raise Exception(f"Membership not found: {membership_id}")
        m.status = status
        m.updated_at = datetime.now(timezone.utc)
        return m

    async def get_history(self, membership_id: str, limit: int = 50, offset: int = 0, action: Optional[PointAction] = None) -> List[MembershipHistory]:
        results = [h for h in self.history if h.membership_id == membership_id]
        if action:
            results = [h for h in results if h.action == action]
        return results[offset:offset+limit]

    async def count_history(self, membership_id: str, action: Optional[PointAction] = None) -> int:
        return len(await self.get_history(membership_id, action=action))

    async def add_history(self, membership_id: str, action: PointAction, points_change: int = 0, **kwargs) -> MembershipHistory:
        self._counter += 1
        h = MembershipHistory(
            id=self._counter,
            history_id=f"hist_{self._counter:016d}",
            membership_id=membership_id,
            action=action,
            points_change=points_change,
            balance_after=kwargs.get("balance_after"),
            previous_tier=kwargs.get("previous_tier"),
            new_tier=kwargs.get("new_tier"),
            source=kwargs.get("source"),
            reference_id=kwargs.get("reference_id"),
            reward_code=kwargs.get("reward_code"),
            benefit_code=kwargs.get("benefit_code"),
            description=kwargs.get("description"),
            initiated_by=InitiatedBy(kwargs.get("initiated_by", "system")),
            metadata=kwargs.get("metadata", {}),
            created_at=datetime.now(timezone.utc)
        )
        self.history.append(h)
        return h

    async def get_tier_benefits(self, tier_code: str) -> List[TierBenefit]:
        return self.tier_benefits.get(tier_code, [])

    async def get_benefit_usage(self, membership_id: str, benefit_code: str) -> int:
        return self.benefit_usage.get(membership_id, {}).get(benefit_code, 0)

    async def record_benefit_usage(self, membership_id: str, benefit_code: str) -> None:
        if membership_id not in self.benefit_usage:
            self.benefit_usage[membership_id] = {}
        self.benefit_usage[membership_id][benefit_code] = self.benefit_usage[membership_id].get(benefit_code, 0) + 1
        await self.add_history(membership_id, PointAction.BENEFIT_USED, benefit_code=benefit_code)

    async def delete_user_data(self, user_id: str) -> int:
        to_delete = [m_id for m_id, m in self.memberships.items() if m.user_id == user_id]
        for m_id in to_delete:
            del self.memberships[m_id]
        self.history = [h for h in self.history if h.membership_id not in to_delete]
        return len(to_delete)

    async def get_stats(self) -> Dict[str, Any]:
        total = len(self.memberships)
        active = len([m for m in self.memberships.values() if m.status == MembershipStatus.ACTIVE])
        return {
            "total_memberships": total,
            "active_memberships": active,
            "suspended_memberships": 0,
            "expired_memberships": 0,
            "canceled_memberships": 0,
            "total_points_issued": sum(m.lifetime_points for m in self.memberships.values()),
            "total_points_redeemed": 0,
            "tier_distribution": {}
        }


# ====================
# Mock Event Bus
# ====================


class MockEventBus:
    """Mock event bus for unit testing"""

    def __init__(self):
        self.published_events: List[Dict[str, Any]] = []

    async def publish(self, subject: str, data: Dict[str, Any]) -> None:
        self.published_events.append({"subject": subject, "data": data})

    async def subscribe(self, pattern: str, handler) -> None:
        pass

    async def close(self) -> None:
        pass


# ====================
# Fixtures
# ====================


@pytest.fixture
def mock_repository():
    """Create mock repository"""
    return MockMembershipRepository()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest.fixture
def membership_service(mock_repository, mock_event_bus):
    """Create membership service with mocks"""
    return MembershipService(
        repository=mock_repository,
        event_bus=mock_event_bus
    )


@pytest.fixture
async def sample_membership(mock_repository):
    """Create sample membership"""
    return await mock_repository.create_membership(
        user_id="user_123",
        tier_code="bronze",
        points_balance=1000
    )


@pytest.fixture
async def gold_membership(mock_repository):
    """Create gold tier membership"""
    m = await mock_repository.create_membership(
        user_id="user_gold",
        tier_code="gold",
        points_balance=5000,
        tier_points=25000
    )
    return m
