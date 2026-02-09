"""
Notification Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_notification_service
    service = create_notification_service(event_bus=event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager
from .notification_service import NotificationService


def create_notification_service(
    event_bus=None,
    config_manager: Optional[ConfigManager] = None,
) -> NotificationService:
    """
    Create NotificationService with real dependencies.

    This function imports the real repository and clients (which have I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        event_bus: Event bus for publishing events
        config_manager: ConfigManager instance for service discovery

    Returns:
        Configured NotificationService instance
    """
    # Import real repository and clients here (not at module level)
    from .notification_repository import NotificationRepository
    from .clients import AccountServiceClient, OrganizationServiceClient

    repository = NotificationRepository(config=config_manager)
    account_client = AccountServiceClient(config_manager)
    organization_client = OrganizationServiceClient(config_manager)

    return NotificationService(
        event_bus=event_bus,
        config_manager=config_manager,
        repository=repository,
        account_client=account_client,
        organization_client=organization_client,
    )
