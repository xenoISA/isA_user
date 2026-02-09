"""
Media Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import (
    PhotoVersion,
    PhotoMetadata,
    Playlist,
    RotationSchedule,
    PhotoCache,
    CacheStatus,
)


class MediaServiceError(Exception):
    """Base exception for media service errors"""
    pass


class MediaNotFoundError(MediaServiceError):
    """Media resource not found"""
    pass


class MediaValidationError(MediaServiceError):
    """Media data validation error"""
    pass


class MediaPermissionError(MediaServiceError):
    """Media permission error"""
    pass


@runtime_checkable
class MediaRepositoryProtocol(Protocol):
    """
    Interface for Media Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    # Photo Version operations
    async def create_photo_version(self, version_data: PhotoVersion) -> Optional[PhotoVersion]:
        """Create a new photo version"""
        ...

    async def get_photo_version(self, version_id: str) -> Optional[PhotoVersion]:
        """Get photo version by ID"""
        ...

    async def list_photo_versions(self, photo_id: str, user_id: str) -> List[PhotoVersion]:
        """List all versions of a photo"""
        ...

    async def delete_photo_version(self, version_id: str, user_id: str) -> bool:
        """Delete a photo version"""
        ...

    # Photo Metadata operations
    async def create_or_update_metadata(self, metadata: PhotoMetadata) -> Optional[PhotoMetadata]:
        """Create or update photo metadata"""
        ...

    async def get_photo_metadata(self, file_id: str) -> Optional[PhotoMetadata]:
        """Get photo metadata by file ID"""
        ...

    # Playlist operations
    async def create_playlist(self, playlist_data: Playlist) -> Optional[Playlist]:
        """Create a new playlist"""
        ...

    async def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """Get playlist by ID"""
        ...

    async def list_user_playlists(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Playlist]:
        """List user's playlists"""
        ...

    async def update_playlist(self, playlist_id: str, updates: Dict[str, Any]) -> Optional[Playlist]:
        """Update a playlist"""
        ...

    async def delete_playlist(self, playlist_id: str, user_id: str) -> bool:
        """Delete a playlist"""
        ...

    # Rotation Schedule operations
    async def create_rotation_schedule(self, schedule_data: RotationSchedule) -> Optional[RotationSchedule]:
        """Create a rotation schedule"""
        ...

    async def get_rotation_schedule(self, schedule_id: str) -> Optional[RotationSchedule]:
        """Get rotation schedule by ID"""
        ...

    async def list_frame_schedules(self, frame_id: str) -> List[RotationSchedule]:
        """List schedules for a frame"""
        ...

    async def update_schedule_status(self, schedule_id: str, is_active: bool) -> Optional[RotationSchedule]:
        """Update schedule status"""
        ...

    async def delete_rotation_schedule(self, schedule_id: str, user_id: str) -> bool:
        """Delete a rotation schedule"""
        ...

    # Photo Cache operations
    async def create_photo_cache(self, cache_data: PhotoCache) -> Optional[PhotoCache]:
        """Create a photo cache entry"""
        ...

    async def get_photo_cache(self, cache_id: str) -> Optional[PhotoCache]:
        """Get photo cache by ID"""
        ...

    async def get_frame_cache(self, frame_id: str, file_id: str) -> Optional[PhotoCache]:
        """Get cache for specific frame and file"""
        ...

    async def list_frame_cache(self, frame_id: str) -> List[PhotoCache]:
        """List all cached photos for a frame"""
        ...

    async def update_cache_status(self, cache_id: str, status: CacheStatus) -> Optional[PhotoCache]:
        """Update cache status"""
        ...

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class StorageClientProtocol(Protocol):
    """Interface for Storage Service Client"""

    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information"""
        ...

    async def file_exists(self, file_id: str) -> bool:
        """Check if file exists"""
        ...


@runtime_checkable
class DeviceClientProtocol(Protocol):
    """Interface for Device Service Client"""

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device information"""
        ...

    async def device_exists(self, device_id: str) -> bool:
        """Check if device exists"""
        ...
