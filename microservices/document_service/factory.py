"""
Document Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_document_service
    service = create_document_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .document_service import DocumentService


def create_document_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> DocumentService:
    """
    Create DocumentService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events

    Returns:
        Configured DocumentService instance
    """
    # Import real repository here (not at module level)
    from .document_repository import DocumentRepository

    repository = DocumentRepository(config=config)

    # Import and create clients
    storage_client = None
    auth_client = None
    digital_client = None

    try:
        from .clients import (
            StorageServiceClient,
            AuthorizationServiceClient,
            DigitalAnalyticsClient,
        )
        storage_client = StorageServiceClient()
        auth_client = AuthorizationServiceClient()
        digital_client = DigitalAnalyticsClient()
    except Exception:
        pass  # Clients will be None if import fails

    return DocumentService(
        repository=repository,
        event_bus=event_bus,
        config_manager=config,
        storage_client=storage_client,
        auth_client=auth_client,
        digital_client=digital_client,
    )
