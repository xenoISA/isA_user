"""
Audit Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules (repository).

Usage:
    from .factory import create_audit_service
    service = create_audit_service(config)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .audit_service import AuditService


def create_audit_service(
    config: Optional[ConfigManager] = None,
) -> AuditService:
    """
    Create AuditService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Optional ConfigManager instance

    Returns:
        AuditService: Configured service instance with real repository
    """
    # Import real repository here (not at module level)
    from .audit_repository import AuditRepository

    repository = AuditRepository(config=config)

    return AuditService(
        repository=repository,
    )
