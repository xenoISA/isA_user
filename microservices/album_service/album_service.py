"""
Album Service Business Logic

Album management business logic layer for the microservice.
Handles validation, business rules, and error handling.

Uses dependency injection for testability:
- Repository is injected, not created at import time
- Event publishers are lazily loaded
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import uuid
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import protocols (no I/O dependencies) - NOT the concrete repository!
from .protocols import (
    AlbumRepositoryProtocol,
    AlbumNotFoundError,
    AlbumValidationError,
    AlbumPermissionError,
    AlbumServiceError,
)
from .models import (
    AlbumCreateRequest, AlbumUpdateRequest, AlbumAddPhotosRequest,
    AlbumRemovePhotosRequest, AlbumSyncRequest, AlbumResponse,
    AlbumSummaryResponse, AlbumPhotoResponse, AlbumSyncStatusResponse,
    AlbumListResponse, Album, AlbumPhoto, SyncStatus
)
from core.nats_client import Event

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


# ==================== Album Service ====================

class AlbumService:
    """
    Album management business logic service

    Handles all album-related business operations while delegating
    data access to the repository layer.

    Uses dependency injection for testability - repository is injected,
    not created internally.
    """

    def __init__(
        self,
        repository: Optional[AlbumRepositoryProtocol] = None,
        event_bus=None,
    ):
        """
        Initialize service with injected dependencies.

        Args:
            repository: Repository (inject mock for testing)
            event_bus: Event bus for publishing events
        """
        self.repo = repository  # Will be set by factory if None
        self.event_bus = event_bus

    # ==================== Album Lifecycle Operations ====================

    async def create_album(
        self,
        request: AlbumCreateRequest,
        user_id: str
    ) -> AlbumResponse:
        """
        Create a new album

        Args:
            request: Album creation request
            user_id: User ID creating the album

        Returns:
            AlbumResponse: Created album

        Raises:
            AlbumValidationError: If request data is invalid
            AlbumServiceError: If operation fails
        """
        try:
            # Validate request
            self._validate_album_create_request(request)

            # Generate album ID
            album_id = f"album_{uuid.uuid4().hex[:16]}"

            # Create album object
            album = Album(
                album_id=album_id,
                name=request.name,
                description=request.description,
                user_id=user_id,
                organization_id=request.organization_id,
                auto_sync=request.auto_sync,
                sync_frames=request.sync_frames,
                is_family_shared=request.is_family_shared,
                tags=request.tags,
                metadata={}
            )

            # Save to database
            created_album = await self.repo.create_album(album)

            if not created_album:
                raise AlbumServiceError("Failed to create album")

            # Publish album.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="album.created",
                        source="album_service",
                        data={
                            "album_id": created_album.album_id,
                            "user_id": created_album.user_id,
                            "name": created_album.name,
                            "organization_id": created_album.organization_id,
                            "is_family_shared": created_album.is_family_shared,
                            "auto_sync": created_album.auto_sync,
                            "sync_frames": created_album.sync_frames,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published album.created event for album {album_id}")
                except Exception as e:
                    logger.error(f"Failed to publish album.created event: {e}")

            logger.info(f"Album created: {album_id} by user {user_id}")
            return AlbumResponse.model_validate(created_album.model_dump())

        except Exception as e:
            logger.error(f"Failed to create album: {e}")
            raise AlbumServiceError(f"Failed to create album: {str(e)}")

    async def get_album(
        self,
        album_id: str,
        user_id: str
    ) -> AlbumResponse:
        """
        Get album by ID

        Args:
            album_id: Album ID
            user_id: User ID requesting the album

        Returns:
            AlbumResponse: Album details

        Raises:
            AlbumNotFoundError: If album not found
            AlbumPermissionError: If user doesn't have access
        """
        try:
            album = await self.repo.get_album_by_id(album_id, user_id)

            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            return AlbumResponse.model_validate(album.model_dump())

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get album: {e}")
            raise AlbumServiceError(f"Failed to get album: {str(e)}")

    async def list_user_albums(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        organization_id: Optional[str] = None,
        is_family_shared: Optional[bool] = None
    ) -> AlbumListResponse:
        """
        List albums for a user with pagination

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            organization_id: Filter by organization
            is_family_shared: Filter by family sharing status

        Returns:
            AlbumListResponse: Paginated album list
        """
        try:
            # Calculate offset
            offset = (page - 1) * page_size

            # Get albums from repository
            albums = await self.repo.list_user_albums(
                user_id=user_id,
                organization_id=organization_id,
                is_family_shared=is_family_shared,
                limit=page_size + 1,  # Get one extra to check if there's a next page
                offset=offset
            )

            # Check if there's a next page
            has_next = len(albums) > page_size
            if has_next:
                albums = albums[:page_size]

            # Convert to summary responses
            album_summaries = [
                AlbumSummaryResponse(
                    album_id=album.album_id,
                    name=album.name,
                    user_id=album.user_id,
                    cover_photo_id=album.cover_photo_id,
                    photo_count=album.photo_count,
                    is_family_shared=album.is_family_shared,
                    created_at=album.created_at
                )
                for album in albums
            ]

            return AlbumListResponse(
                albums=album_summaries,
                total_count=len(album_summaries),  # This is approximate
                page=page,
                page_size=page_size,
                has_next=has_next
            )

        except Exception as e:
            logger.error(f"Failed to list albums: {e}")
            raise AlbumServiceError(f"Failed to list albums: {str(e)}")

    async def update_album(
        self,
        album_id: str,
        user_id: str,
        request: AlbumUpdateRequest
    ) -> AlbumResponse:
        """
        Update album

        Args:
            album_id: Album ID
            user_id: User ID updating the album
            request: Update request

        Returns:
            AlbumResponse: Updated album

        Raises:
            AlbumNotFoundError: If album not found
            AlbumPermissionError: If user doesn't own the album
        """
        try:
            # Verify album exists and user owns it
            album = await self.repo.get_album_by_id(album_id, user_id)
            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            # Build update data (only include non-None values)
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.description is not None:
                update_data["description"] = request.description
            if request.cover_photo_id is not None:
                update_data["cover_photo_id"] = request.cover_photo_id
            if request.auto_sync is not None:
                update_data["auto_sync"] = request.auto_sync
            if request.sync_frames is not None:
                update_data["sync_frames"] = request.sync_frames
            if request.is_family_shared is not None:
                update_data["is_family_shared"] = request.is_family_shared
            if request.tags is not None:
                update_data["tags"] = request.tags

            # Update album
            success = await self.repo.update_album(album_id, user_id, update_data)

            if not success:
                raise AlbumServiceError("Failed to update album")

            # Get updated album
            updated_album = await self.repo.get_album_by_id(album_id, user_id)

            # Publish album.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="album.updated",
                        source="album_service",
                        data={
                            "album_id": album_id,
                            "user_id": user_id,
                            "updates": update_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published album.updated event for album {album_id}")
                except Exception as e:
                    logger.error(f"Failed to publish album.updated event: {e}")

            logger.info(f"Album updated: {album_id} by user {user_id}")
            return AlbumResponse.model_validate(updated_album.model_dump())

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update album: {e}")
            raise AlbumServiceError(f"Failed to update album: {str(e)}")

    async def delete_album(
        self,
        album_id: str,
        user_id: str
    ) -> bool:
        """
        Delete album

        Args:
            album_id: Album ID
            user_id: User ID deleting the album

        Returns:
            bool: True if deleted

        Raises:
            AlbumNotFoundError: If album not found
            AlbumPermissionError: If user doesn't own the album
        """
        try:
            # Verify album exists and user owns it
            album = await self.repo.get_album_by_id(album_id, user_id)
            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            # Delete album (this will cascade delete photos due to repository logic)
            success = await self.repo.delete_album(album_id, user_id)

            if success:
                # Publish album.deleted event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="album.deleted",
                            source="album_service",
                            data={
                                "album_id": album_id,
                                "user_id": user_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published album.deleted event for album {album_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish album.deleted event: {e}")

                logger.info(f"Album deleted: {album_id} by user {user_id}")

            return success

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete album: {e}")
            raise AlbumServiceError(f"Failed to delete album: {str(e)}")

    # ==================== Album Photo Operations ====================

    async def add_photos_to_album(
        self,
        album_id: str,
        user_id: str,
        request: AlbumAddPhotosRequest
    ) -> Dict[str, Any]:
        """
        Add photos to album

        Args:
            album_id: Album ID
            user_id: User ID adding photos
            request: Add photos request

        Returns:
            Dict with added_count

        Raises:
            AlbumNotFoundError: If album not found
            AlbumPermissionError: If user doesn't own the album
        """
        try:
            # Verify album exists and user owns it
            album = await self.repo.get_album_by_id(album_id, user_id)
            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            # TODO: Validate photo_ids exist in storage_service
            # For now, we trust the photo_ids provided

            # Add photos
            added_count = await self.repo.add_photos_to_album(
                album_id=album_id,
                photo_ids=request.photo_ids,
                added_by=user_id
            )

            # Publish album.photo.added event
            if self.event_bus and added_count > 0:
                try:
                    event = Event(
                        event_type="album.photo.added",
                        source="album_service",
                        data={
                            "album_id": album_id,
                            "user_id": user_id,
                            "photo_ids": request.photo_ids,
                            "added_count": added_count,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published album.photo.added event for album {album_id}")
                except Exception as e:
                    logger.error(f"Failed to publish album.photo.added event: {e}")

            logger.info(f"Added {added_count} photos to album {album_id}")

            return {
                "album_id": album_id,
                "added_count": added_count,
                "total_photos": album.photo_count + added_count
            }

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to add photos to album: {e}")
            raise AlbumServiceError(f"Failed to add photos: {str(e)}")

    async def remove_photos_from_album(
        self,
        album_id: str,
        user_id: str,
        request: AlbumRemovePhotosRequest
    ) -> Dict[str, Any]:
        """
        Remove photos from album

        Args:
            album_id: Album ID
            user_id: User ID removing photos
            request: Remove photos request

        Returns:
            Dict with removed_count

        Raises:
            AlbumNotFoundError: If album not found
            AlbumPermissionError: If user doesn't own the album
        """
        try:
            # Verify album exists and user owns it
            album = await self.repo.get_album_by_id(album_id, user_id)
            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            # Remove photos
            removed_count = await self.repo.remove_photos_from_album(
                album_id=album_id,
                photo_ids=request.photo_ids
            )

            # Publish album.photo.removed event
            if self.event_bus and removed_count > 0:
                try:
                    event = Event(
                        event_type="album.photo.removed",
                        source="album_service",
                        data={
                            "album_id": album_id,
                            "user_id": user_id,
                            "photo_ids": request.photo_ids,
                            "removed_count": removed_count,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published album.photo.removed event for album {album_id}")
                except Exception as e:
                    logger.error(f"Failed to publish album.photo.removed event: {e}")

            logger.info(f"Removed {removed_count} photos from album {album_id}")

            return {
                "album_id": album_id,
                "removed_count": removed_count,
                "total_photos": max(0, album.photo_count - removed_count)
            }

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to remove photos from album: {e}")
            raise AlbumServiceError(f"Failed to remove photos: {str(e)}")

    async def get_album_photos(
        self,
        album_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AlbumPhotoResponse]:
        """
        Get photos in an album

        Args:
            album_id: Album ID
            user_id: User ID requesting photos
            limit: Maximum results
            offset: Result offset

        Returns:
            List of AlbumPhotoResponse

        Raises:
            AlbumNotFoundError: If album not found
        """
        try:
            # Verify album exists
            album = await self.repo.get_album_by_id(album_id, user_id)
            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            # Get photos
            photos = await self.repo.get_album_photos(
                album_id=album_id,
                limit=limit,
                offset=offset
            )

            return [AlbumPhotoResponse.model_validate(photo.model_dump()) for photo in photos]

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get album photos: {e}")
            raise AlbumServiceError(f"Failed to get album photos: {str(e)}")

    # ==================== Album Sync Operations ====================

    async def sync_album_to_frame(
        self,
        album_id: str,
        user_id: str,
        request: AlbumSyncRequest
    ) -> AlbumSyncStatusResponse:
        """
        Sync album to smart frame

        Args:
            album_id: Album ID
            user_id: User ID initiating sync
            request: Sync request with frame_id

        Returns:
            AlbumSyncStatusResponse: Sync status

        Raises:
            AlbumNotFoundError: If album not found
        """
        try:
            # Verify album exists
            album = await self.repo.get_album_by_id(album_id, user_id)
            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            # TODO: Validate frame_id exists and user has access via device_service

            # Update sync status
            status_data = {
                "sync_status": SyncStatus.IN_PROGRESS.value,
                "last_sync_timestamp": datetime.now(timezone.utc),
                "sync_version": 1,
                "total_photos": album.photo_count,
                "synced_photos": 0,
                "pending_photos": album.photo_count,
                "failed_photos": 0,
                "error_message": None
            }

            await self.repo.update_album_sync_status(
                album_id=album_id,
                frame_id=request.frame_id,
                user_id=user_id,
                status_data=status_data
            )

            # Get updated sync status
            sync_status = await self.repo.get_album_sync_status(
                album_id=album_id,
                frame_id=request.frame_id
            )

            if not sync_status:
                # If sync status wasn't created properly, return a default response
                return AlbumSyncStatusResponse(
                    album_id=album_id,
                    frame_id=request.frame_id,
                    sync_status=SyncStatus.IN_PROGRESS,
                    total_photos=album.photo_count,
                    synced_photos=0,
                    pending_photos=album.photo_count,
                    failed_photos=0,
                    last_sync_timestamp=datetime.now(timezone.utc),
                    error_message=None
                )

            # Publish album.synced event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="album.synced",
                        source="album_service",
                        data={
                            "album_id": album_id,
                            "user_id": user_id,
                            "frame_id": request.frame_id,
                            "sync_status": SyncStatus.IN_PROGRESS.value,
                            "total_photos": album.photo_count,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published album.synced event for album {album_id}")
                except Exception as e:
                    logger.error(f"Failed to publish album.synced event: {e}")

            logger.info(f"Album sync initiated: {album_id} to frame {request.frame_id}")

            return AlbumSyncStatusResponse.model_validate(sync_status.model_dump())

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to sync album: {e}")
            raise AlbumServiceError(f"Failed to sync album: {str(e)}")

    async def get_album_sync_status(
        self,
        album_id: str,
        frame_id: str,
        user_id: str
    ) -> AlbumSyncStatusResponse:
        """
        Get album sync status for a specific frame

        Args:
            album_id: Album ID
            frame_id: Frame ID
            user_id: User ID

        Returns:
            AlbumSyncStatusResponse: Sync status
        """
        try:
            # Verify album exists
            album = await self.repo.get_album_by_id(album_id, user_id)
            if not album:
                raise AlbumNotFoundError(f"Album not found: {album_id}")

            # Get sync status
            sync_status = await self.repo.get_album_sync_status(
                album_id=album_id,
                frame_id=frame_id
            )

            if not sync_status:
                # Return default pending status if not found
                return AlbumSyncStatusResponse(
                    album_id=album_id,
                    frame_id=frame_id,
                    sync_status=SyncStatus.PENDING,
                    total_photos=album.photo_count,
                    synced_photos=0,
                    pending_photos=album.photo_count,
                    failed_photos=0,
                    last_sync_timestamp=None,
                    error_message=None
                )

            return AlbumSyncStatusResponse.model_validate(sync_status.model_dump())

        except AlbumNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            raise AlbumServiceError(f"Failed to get sync status: {str(e)}")

    # ==================== Validation Methods ====================

    def _validate_album_create_request(self, request: AlbumCreateRequest):
        """Validate album creation request"""
        if not request.name or len(request.name.strip()) == 0:
            raise AlbumValidationError("Album name is required")

        if len(request.name) > 255:
            raise AlbumValidationError("Album name too long (max 255 characters)")

        if request.description and len(request.description) > 1000:
            raise AlbumValidationError("Album description too long (max 1000 characters)")

    # ==================== Utility Methods ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            return await self.repo.check_connection()
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
