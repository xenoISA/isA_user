"""
Project Service Protocols (Interfaces)

Contracts for dependency injection.
NO import-time I/O dependencies — safe to import anywhere.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# =============================================================================
# Exceptions — defined here to avoid importing repository
# =============================================================================


class ProjectServiceException(Exception):
    """Base project service exception"""

    pass


class ProjectNotFoundError(ProjectServiceException):
    """Project does not exist"""

    pass


class ProjectPermissionError(ProjectServiceException):
    """Caller lacks access to the project"""

    pass


class ProjectLimitExceeded(ProjectServiceException):
    """User has reached the maximum number of projects"""

    pass


class InvalidProjectUpdate(ProjectServiceException):
    """Update payload is invalid"""

    def __init__(self, detail: str = "Invalid update"):
        self.detail = detail
        super().__init__(detail)


class RepositoryError(ProjectServiceException):
    """Database / persistence layer failure"""

    def __init__(self, detail: str = "Repository error", cause: Exception = None):
        self.detail = detail
        self.cause = cause
        super().__init__(detail)


class ProjectStorageError(ProjectServiceException):
    """Project file storage operation failed"""

    pass


# =============================================================================
# Repository Protocol
# =============================================================================


@runtime_checkable
class ProjectRepositoryProtocol(Protocol):
    """Interface for Project Repository — implementations provide data access."""

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str = None,
        custom_instructions: str = None,
    ) -> Dict[str, Any]: ...

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]: ...

    async def list_projects(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]: ...

    async def update_project(
        self, project_id: str, **updates
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_project(self, project_id: str) -> bool: ...

    async def set_instructions(self, project_id: str, instructions: str) -> bool: ...

    async def count_projects(self, user_id: str) -> int: ...

    async def create_project_file(
        self,
        project_id: str,
        file_id: str,
        filename: str,
        storage_path: str,
        file_type: str = None,
        file_size: int = None,
    ) -> Dict[str, Any]: ...

    async def list_project_files(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]: ...

    async def get_project_file(
        self,
        project_id: str,
        file_id: str,
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_project_file(self, project_id: str, file_id: str) -> bool: ...

    async def cleanup(self) -> None: ...


# =============================================================================
# Event Bus Protocol
# =============================================================================


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus — no I/O imports."""

    async def publish_event(self, event: Any) -> None: ...


@runtime_checkable
class StorageServiceProtocol(Protocol):
    """Interface for storage service operations used by project_service."""

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        organization_id: Optional[str] = None,
        access_level: str = "private",
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        auto_delete_after_days: Optional[int] = None,
        enable_indexing: bool = True,
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_file(
        self,
        file_id: str,
        user_id: str,
        permanent: bool = False,
    ) -> bool: ...
