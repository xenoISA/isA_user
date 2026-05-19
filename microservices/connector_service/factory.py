"""
Connector Service Factory.

Factory functions for creating service dependencies — the ONLY place
that imports IO-dependent modules. Mirrors project_sharing_service.factory.
"""

from typing import Optional

from core.config_manager import ConfigManager


def create_connector_repository(config: Optional[ConfigManager] = None):
    """Create the ConnectorRepository with real Postgres dependencies."""
    from .connector_repository import ConnectorRepository

    return ConnectorRepository(config=config)
