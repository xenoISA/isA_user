"""
Storage Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

from .models import StoredFile, FileShare, FileStatus, StorageQuota


class StorageServiceError(Exception):
    """Base exception for storage service errors"""
    pass


class FileNotFoundError(Exception):
    """File not found"""
    pass


class QuotaExceededError(Exception):
    """Storage quota exceeded"""
    pass


@runtime_checkable
class StorageRepositoryProtocol(Protocol):
    """Interface for Storage Repository"""

    async def check_connection(self) -> bool: ...

    async def create_file_record(self, file_data: StoredFile) -> Optional[StoredFile]: ...

    async def get_file_by_id(
        self, file_id: str, user_id: Optional[str] = None,
    ) -> Optional[StoredFile]: ...

    async def list_user_files(
        self, user_id: str, organization_id: Optional[str] = None,
        status: Optional[FileStatus] = None, content_type: Optional[str] = None,
        prefix: Optional[str] = None, limit: int = 100, offset: int = 0,
    ) -> List[StoredFile]: ...

    async def update_file_status(
        self, file_id: str, user_id: str, status: FileStatus,
        download_url: Optional[str] = None,
        download_url_expires_at: Optional[datetime] = None,
    ) -> bool: ...

    async def delete_file(self, file_id: str, user_id: str) -> bool: ...

    async def create_file_share(self, share_data: FileShare) -> Optional[FileShare]: ...

    async def get_file_share(
        self, share_id: Optional[str] = None, file_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[FileShare]: ...

    async def list_file_shares(
        self, file_id: Optional[str] = None, shared_by: Optional[str] = None,
        shared_with: Optional[str] = None,
    ) -> List[FileShare]: ...

    async def get_storage_quota(
        self, quota_type: str, entity_id: str,
    ) -> Optional[StorageQuota]: ...

    async def create_storage_quota(
        self, quota_type: str, entity_id: str,
        total_quota_bytes: int = 10737418240,
        max_file_size: int = 104857600,
        max_file_count: int = 10000,
    ) -> Optional[StorageQuota]: ...

    async def update_storage_usage(
        self, quota_type: str, entity_id: str,
        bytes_delta: int, file_count_delta: int = 0,
    ) -> bool: ...

    async def get_storage_stats(
        self, user_id: str, organization_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
