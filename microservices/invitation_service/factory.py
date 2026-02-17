"""
Invitation Service Factory - Dependency Injection Setup

Creates service instances with real or mock dependencies.
"""
import os
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.config_manager import ConfigManager

from .invitation_service import InvitationService
from .invitation_repository import InvitationRepository
from .protocols import (
    InvitationRepositoryProtocol,
    EventBusProtocol,
    OrganizationClientProtocol,
)


class InvitationServiceFactory:
    """Factory for creating InvitationService with dependencies"""

    @staticmethod
    def create_service(
        repository: Optional[InvitationRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        config: Optional[ConfigManager] = None,
    ) -> InvitationService:
        """
        Create InvitationService instance.

        Args:
            repository: Repository implementation (default: real repository)
            event_bus: Event bus implementation (default: None, set via lifespan)
            config: Config manager (default: creates new one)

        Returns:
            Configured InvitationService instance
        """
        # Use real implementations if not provided
        if repository is None:
            if config is None:
                config = ConfigManager("invitation_service")
            repository = InvitationRepository(config=config)

        # Create service - note: current implementation creates its own repository
        # This factory provides the pattern for future refactoring
        service = InvitationService(event_bus=event_bus)

        # Override repository if provided (for testing)
        if repository is not None:
            service.repository = repository

        return service

    @staticmethod
    def create_for_testing(
        mock_repository: InvitationRepositoryProtocol,
        mock_event_bus: Optional[EventBusProtocol] = None,
    ) -> InvitationService:
        """
        Create service with mock dependencies for testing.

        Args:
            mock_repository: Mock repository implementation
            mock_event_bus: Mock event bus (optional)

        Returns:
            InvitationService with mocked dependencies
        """
        service = InvitationService(event_bus=mock_event_bus)
        service.repository = mock_repository
        return service


def create_invitation_service(
    config: Optional[ConfigManager] = None,
    event_bus: Optional[EventBusProtocol] = None,
) -> InvitationService:
    """
    Convenience function to create InvitationService.

    Used by main.py lifespan context.

    Args:
        config: Configuration manager (optional)
        event_bus: Event bus for publishing (optional)

    Returns:
        Configured InvitationService instance
    """
    return InvitationServiceFactory.create_service(
        config=config,
        event_bus=event_bus,
    )


__all__ = [
    "InvitationServiceFactory",
    "create_invitation_service",
]
