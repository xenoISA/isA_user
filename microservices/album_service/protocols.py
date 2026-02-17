"""
Album Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import Album, AlbumPhoto, AlbumSyncStatus


# Custom exceptions - defined here to avoid importing repository
class AlbumNotFoundError(Exception):
    """Album not found error"""
    pass


class AlbumValidationError(Exception):
    """Album validation error"""
    pass


class AlbumPermissionError(Exception):
    """Album permission denied error"""
    pass


class AlbumServiceError(Exception):
    """Base exception for album service errors"""
    pass


@runtime_checkable
class AlbumRepositoryProtocol(Protocol):
    """
    Interface for Album Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    # ==================== Album Operations ====================

    async def create_album(self, album_data: Album) -> Optional[Album]:
        """Create a new album"""
        ...

    async def get_album_by_id(
        self, album_id: str, user_id: Optional[str] = None
    ) -> Optional[Album]:
        """Get album by album_id"""
        ...

    async def list_user_albums(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        is_family_shared: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Album]:
        """List albums for a user with optional filters"""
        ...

    async def update_album(
        self, album_id: str, user_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """Update album"""
        ...

    async def delete_album(self, album_id: str, user_id: str) -> bool:
        """Delete an album"""
        ...

    async def update_album_photo_count(self, album_id: str) -> bool:
        """Update photo count for an album"""
        ...

    # ==================== Album Photos Operations ====================

    async def add_photos_to_album(
        self, album_id: str, photo_ids: List[str], added_by: str
    ) -> int:
        """Add photos to album (returns number of photos added)"""
        ...

    async def remove_photos_from_album(
        self, album_id: str, photo_ids: List[str]
    ) -> int:
        """Remove photos from album (returns number of photos removed)"""
        ...

    async def get_album_photos(
        self, album_id: str, limit: int = 50, offset: int = 0
    ) -> List[AlbumPhoto]:
        """Get photos in an album"""
        ...

    async def remove_all_photos_from_album(self, album_id: str) -> bool:
        """Remove all photos from an album"""
        ...

    # ==================== Album Sync Status Operations ====================

    async def get_album_sync_status(
        self, album_id: str, frame_id: str
    ) -> Optional[AlbumSyncStatus]:
        """Get sync status for album and frame"""
        ...

    async def update_album_sync_status(
        self, album_id: str, frame_id: str, user_id: str, status_data: Dict[str, Any]
    ) -> bool:
        """Update or create album sync status"""
        ...

    async def list_album_sync_statuses(
        self,
        album_id: Optional[str] = None,
        frame_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[AlbumSyncStatus]:
        """List album sync statuses with optional filters"""
        ...

    # ==================== Event Handler Methods ====================

    async def remove_photo_from_all_albums(self, photo_id: str) -> int:
        """Remove a photo from all albums"""
        ...

    async def delete_sync_status_by_frame(self, frame_id: str) -> int:
        """Delete all sync status records for a frame"""
        ...

    # ==================== Utility Methods ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...
