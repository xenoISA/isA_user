"""
Subscription Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_subscription_service
    service = create_subscription_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .subscription_service import SubscriptionService


def create_subscription_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> SubscriptionService:
    """
    Create SubscriptionService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events

    Returns:
        Configured SubscriptionService instance
    """
    # Import real repository here (not at module level)
    from .subscription_repository import SubscriptionRepository

    repository = SubscriptionRepository(config=config)

    return SubscriptionService(
        repository=repository,
        event_bus=event_bus,
    )
