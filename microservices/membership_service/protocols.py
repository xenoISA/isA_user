"""
Membership Service Protocols

Defines interfaces for dependency injection and testing.
Following the protocol-based architecture pattern.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from .models import (
    Membership,
    MembershipHistory,
    MembershipStatus,
    MembershipTier,
    PointAction,
    Tier,
    TierBenefit,
)


# ====================
# Repository Protocol
# ====================


class MembershipRepositoryProtocol(Protocol):
    """Protocol for membership data repository"""

    async def initialize(self) -> None:
        """Initialize repository connection"""
        ...

    async def close(self) -> None:
        """Close repository connection"""
        ...

    # Membership CRUD
    async def create_membership(
        self,
        user_id: str,
        tier_code: str,
        points_balance: int = 0,
        **kwargs
    ) -> Membership:
        """Create new membership"""
        ...

    async def get_membership(self, membership_id: str) -> Optional[Membership]:
        """Get membership by ID"""
        ...

    async def get_membership_by_user(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[Membership]:
        """Get active membership for user"""
        ...

    async def list_memberships(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[MembershipStatus] = None,
        tier_code: Optional[MembershipTier] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Membership]:
        """List memberships with filters"""
        ...

    async def count_memberships(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[MembershipStatus] = None,
        tier_code: Optional[MembershipTier] = None
    ) -> int:
        """Count memberships with filters"""
        ...

    # Points Operations
    async def add_points(
        self,
        membership_id: str,
        points: int,
        tier_points: int,
        source: str,
        reference_id: Optional[str] = None
    ) -> Membership:
        """Atomically add points"""
        ...

    async def deduct_points(
        self,
        membership_id: str,
        points: int,
        reward_code: str,
        description: Optional[str] = None
    ) -> Membership:
        """Atomically deduct points"""
        ...

    # Tier Operations
    async def update_tier(
        self,
        membership_id: str,
        new_tier: str
    ) -> Membership:
        """Update membership tier"""
        ...

    async def get_tier(self, tier_code: str) -> Optional[Tier]:
        """Get tier definition"""
        ...

    async def get_all_tiers(self) -> List[Tier]:
        """Get all tier definitions"""
        ...

    # Status Operations
    async def update_status(
        self,
        membership_id: str,
        status: MembershipStatus,
        reason: Optional[str] = None
    ) -> Membership:
        """Update membership status"""
        ...

    # History
    async def get_history(
        self,
        membership_id: str,
        limit: int = 50,
        offset: int = 0,
        action: Optional[PointAction] = None
    ) -> List[MembershipHistory]:
        """Get membership history"""
        ...

    async def count_history(
        self,
        membership_id: str,
        action: Optional[PointAction] = None
    ) -> int:
        """Count history entries"""
        ...

    async def add_history(
        self,
        membership_id: str,
        action: PointAction,
        points_change: int = 0,
        **kwargs
    ) -> MembershipHistory:
        """Record history entry"""
        ...

    # Benefits
    async def get_tier_benefits(
        self,
        tier_code: str
    ) -> List[TierBenefit]:
        """Get benefits for tier"""
        ...

    async def get_benefit_usage(
        self,
        membership_id: str,
        benefit_code: str
    ) -> int:
        """Get benefit usage count"""
        ...

    async def record_benefit_usage(
        self,
        membership_id: str,
        benefit_code: str
    ) -> None:
        """Record benefit usage"""
        ...

    # GDPR
    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user data (GDPR)"""
        ...

    # Statistics
    async def get_stats(self) -> Dict[str, Any]:
        """Get membership statistics"""
        ...


# ====================
# Event Bus Protocol
# ====================


class EventBusProtocol(Protocol):
    """Protocol for event bus operations"""

    async def publish(self, subject: str, data: Dict[str, Any]) -> None:
        """Publish event to NATS"""
        ...

    async def subscribe(self, pattern: str, handler: Any) -> None:
        """Subscribe to events"""
        ...

    async def close(self) -> None:
        """Close event bus connection"""
        ...


# ====================
# Service Client Protocols
# ====================


class AccountClientProtocol(Protocol):
    """Protocol for account service client"""

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from account service"""
        ...


# ====================
# Custom Exceptions
# ====================


class MembershipServiceError(Exception):
    """Base exception for membership service errors"""
    pass


class MembershipNotFoundError(MembershipServiceError):
    """Raised when membership is not found"""
    pass


class DuplicateMembershipError(MembershipServiceError):
    """Raised when user already has active membership"""
    pass


class InsufficientPointsError(MembershipServiceError):
    """Raised when user has insufficient points"""

    def __init__(
        self,
        message: str,
        available: int = 0,
        requested: int = 0
    ):
        super().__init__(message)
        self.available = available
        self.requested = requested


class InvalidStatusTransitionError(MembershipServiceError):
    """Raised when status transition is not allowed"""

    def __init__(
        self,
        message: str,
        current_status: str = "",
        target_status: str = ""
    ):
        super().__init__(message)
        self.current_status = current_status
        self.target_status = target_status


class MembershipSuspendedError(MembershipServiceError):
    """Raised when membership is suspended"""
    pass


class MembershipExpiredError(MembershipServiceError):
    """Raised when membership is expired"""
    pass


class BenefitNotAvailableError(MembershipServiceError):
    """Raised when benefit is not available"""
    pass


class BenefitUsageLimitExceededError(MembershipServiceError):
    """Raised when benefit usage limit is exceeded"""
    pass


__all__ = [
    "MembershipRepositoryProtocol",
    "EventBusProtocol",
    "AccountClientProtocol",
    "MembershipServiceError",
    "MembershipNotFoundError",
    "DuplicateMembershipError",
    "InsufficientPointsError",
    "InvalidStatusTransitionError",
    "MembershipSuspendedError",
    "MembershipExpiredError",
    "BenefitNotAvailableError",
    "BenefitUsageLimitExceededError",
]
