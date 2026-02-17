"""
Membership Service Factory

Factory for creating MembershipService with real dependencies.
This is the ONLY module that imports concrete implementations.
"""

import logging
from typing import Optional

from core.config_manager import ConfigManager

from .membership_repository import MembershipRepository
from .membership_service import MembershipService

logger = logging.getLogger(__name__)


def create_membership_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> MembershipService:
    """
    Create MembershipService with all real dependencies

    Args:
        config: Optional config manager (creates default if not provided)
        event_bus: Optional event bus for event publishing

    Returns:
        Fully initialized MembershipService instance
    """
    # Initialize config if not provided
    if config is None:
        config = ConfigManager("membership_service")

    # Create repository
    repository = MembershipRepository(config=config)

    logger.info("MembershipService created with real dependencies")

    # Create and return service
    return MembershipService(
        repository=repository,
        event_bus=event_bus,
    )


__all__ = ["create_membership_service"]
