"""
Organization Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_organization_service, create_family_sharing_service
    org_service = create_organization_service(config, event_bus)
    sharing_service = create_family_sharing_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .organization_service import OrganizationService
from .family_sharing_service import FamilySharingService


def create_organization_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    account_client=None,
) -> OrganizationService:
    """
    Create OrganizationService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        account_client: Account service client

    Returns:
        Configured OrganizationService instance
    """
    # Import real repository here (not at module level)
    from .organization_repository import OrganizationRepository

    repository = OrganizationRepository(config=config)

    return OrganizationService(
        repository=repository,
        event_bus=event_bus,
        account_client=account_client,
    )


def create_family_sharing_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> FamilySharingService:
    """
    Create FamilySharingService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events

    Returns:
        Configured FamilySharingService instance
    """
    # Import real repository here (not at module level)
    from .family_sharing_repository import FamilySharingRepository

    repository = FamilySharingRepository(config=config)

    return FamilySharingService(
        repository=repository,
        event_bus=event_bus,
    )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "create_organization_service",
    "create_family_sharing_service",
]
