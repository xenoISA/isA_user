"""
Task Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_task_service
    service = create_task_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .task_service import TaskService


def create_task_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    notification_client=None,
    calendar_client=None,
    account_client=None,
) -> TaskService:
    """
    Create TaskService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager for service discovery
        event_bus: Event bus for publishing events
        notification_client: Notification service client (reserved for future use)
        calendar_client: Calendar service client (reserved for future use)
        account_client: Account service client (reserved for future use)

    Returns:
        Configured TaskService instance
    """
    # Create config if not provided
    if config is None:
        config = ConfigManager("task_service")

    # TaskService creates its own repository internally
    return TaskService(
        event_bus=event_bus,
        config_manager=config,
    )


def create_task_repository(config: Optional[ConfigManager] = None):
    """
    Create TaskRepository with real dependencies.

    Args:
        config: Configuration manager for service discovery

    Returns:
        Configured TaskRepository instance
    """
    from .task_repository import TaskRepository

    if config is None:
        config = ConfigManager("task_service")

    return TaskRepository(config=config)


__all__ = [
    "create_task_service",
    "create_task_repository",
]
