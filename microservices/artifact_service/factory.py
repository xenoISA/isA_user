"""
Artifact Service Factory

Lazy wiring of the real ArtifactRepository (which imports postgres / gRPC
clients) — keeps the rest of the package import-safe.
"""

from __future__ import annotations

from typing import Optional

from core.config_manager import ConfigManager

from .artifact_service import ArtifactService


def create_artifact_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> ArtifactService:
    from .artifact_repository import ArtifactRepository

    repository = ArtifactRepository(config=config)
    return ArtifactService(repository=repository, event_bus=event_bus)
