"""
Compliance Service Factory

Factory functions for creating service instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .compliance_service import ComplianceService


def create_compliance_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> ComplianceService:
    """
    Create ComplianceService with real dependencies.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events

    Returns:
        ComplianceService: Configured service instance
    """
    service = ComplianceService(event_bus=event_bus, config=config)
    return service
