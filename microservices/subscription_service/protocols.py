"""
Subscription Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import (
    UserSubscription,
    SubscriptionHistory,
    SubscriptionStatus,
)


# Custom exceptions - defined here to avoid importing repository
class SubscriptionServiceError(Exception):
    """Base exception for subscription service errors"""
    pass


class SubscriptionNotFoundError(SubscriptionServiceError):
    """Subscription not found"""
    pass


class SubscriptionValidationError(SubscriptionServiceError):
    """Validation error"""
    pass


class InsufficientCreditsError(SubscriptionServiceError):
    """Not enough credits"""
    pass


class TierNotFoundError(SubscriptionServiceError):
    """Subscription tier not found"""
    pass


@runtime_checkable
class SubscriptionRepositoryProtocol(Protocol):
    """
    Interface for Subscription Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def initialize(self) -> None:
        """Initialize repository"""
        ...

    async def close(self) -> None:
        """Close repository connections"""
        ...

    async def create_subscription(
        self, subscription: UserSubscription
    ) -> Optional[UserSubscription]:
        """Create a new subscription"""
        ...

    async def get_subscription(
        self, subscription_id: str
    ) -> Optional[UserSubscription]:
        """Get subscription by ID"""
        ...

    async def get_user_subscription(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        active_only: bool = True,
    ) -> Optional[UserSubscription]:
        """Get user's subscription"""
        ...

    async def get_subscriptions(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[SubscriptionStatus] = None,
        tier_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserSubscription]:
        """Get subscriptions with filters"""
        ...

    async def update_subscription(
        self,
        subscription_id: str,
        update_data: Dict[str, Any],
    ) -> Optional[UserSubscription]:
        """Update subscription"""
        ...

    async def consume_credits(
        self,
        subscription_id: str,
        credits: int,
    ) -> bool:
        """Consume credits from subscription"""
        ...

    async def allocate_credits(
        self,
        subscription_id: str,
        credits: int,
        rollover: int = 0,
    ) -> bool:
        """Allocate credits to subscription"""
        ...

    async def add_history(
        self, history: SubscriptionHistory
    ) -> Optional[SubscriptionHistory]:
        """Add subscription history entry"""
        ...

    async def get_subscription_history(
        self,
        subscription_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SubscriptionHistory]:
        """Get subscription history"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...
