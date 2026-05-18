"""
Artifact Service Protocols (Interfaces)

These interfaces enable dependency injection for tests without dragging in
I/O-heavy imports (Postgres client, NATS, Consul). The service layer depends
on these — only ``factory.py`` knows about the concrete implementations.
"""

from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable

from .models import (
    Artifact,
    ArtifactScope,
    ArtifactVersion,
)


# ==================== Custom Exceptions ====================


class ArtifactNotFoundError(Exception):
    """Raised when an artifact id cannot be resolved (or is soft-deleted)."""


class ArtifactValidationError(Exception):
    """Raised for request-level validation failures."""


class ArtifactPermissionError(Exception):
    """Raised when the caller is not the owner / lacks visibility access."""


class ArtifactServiceError(Exception):
    """General service-level failure."""


# ==================== Repository Protocol ====================


@runtime_checkable
class ArtifactRepositoryProtocol(Protocol):
    """Interface the artifact service expects of any backing store."""

    async def create_artifact(self, artifact: Artifact) -> Artifact: ...

    async def get_artifact(self, artifact_id: str, include_deleted: bool = False) -> Optional[Artifact]: ...

    async def list_artifacts(
        self,
        *,
        user_id: str,
        scope: ArtifactScope,
        q: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> tuple[List[Artifact], Optional[str], int]: ...

    async def update_artifact(self, artifact_id: str, fields: dict) -> Optional[Artifact]: ...

    async def set_current_version(self, artifact_id: str, version_id: str) -> bool: ...

    async def soft_delete_artifact(self, artifact_id: str, user_id: str) -> bool: ...

    async def add_version(self, artifact_id: str, version: ArtifactVersion) -> ArtifactVersion: ...

    async def list_versions(self, artifact_id: str) -> List[ArtifactVersion]: ...

    async def next_version_number(self, artifact_id: str) -> int: ...

    async def check_connection(self) -> bool: ...


# ==================== Event Bus Protocol ====================


@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...
