"""
Project Sharing Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.
"""

from typing import Optional

from core.config_manager import ConfigManager

from .project_sharing_service import ProjectSharingService


def create_project_sharing_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> ProjectSharingService:
    """Create ProjectSharingService with real dependencies."""
    from .project_share_repository import ProjectShareRepository

    repo = ProjectShareRepository(config=config)

    return ProjectSharingService(
        share_repo=repo,
        event_bus=event_bus,
        config=config,
    )


def create_project_sharing_service_for_testing(
    share_repo=None,
    event_bus=None,
) -> ProjectSharingService:
    """Create ProjectSharingService with injected dependencies for testing."""
    return ProjectSharingService(
        share_repo=share_repo,
        event_bus=event_bus,
    )
