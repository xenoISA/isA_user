"""
Media Service - Business logic layer for media operations

Handles photo versions, metadata, playlists, rotation schedules, and photo caching
for smart frame ecosystem.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.nats_client import Event, EventType, ServiceSource

from .media_repository import MediaRepository
from .models import (
    CacheStatus,
    PhotoCache,
    PhotoCacheResponse,
    PhotoMetadata,
    PhotoMetadataResponse,
    PhotoMetadataUpdateRequest,
    PhotoVersion,
    PhotoVersionCreateRequest,
    PhotoVersionResponse,
    PhotoVersionType,
    Playlist,
    PlaylistCreateRequest,
    PlaylistResponse,
    PlaylistType,
    PlaylistUpdateRequest,
    RotationSchedule,
    RotationScheduleCreateRequest,
    RotationScheduleResponse,
    ScheduleType,
)

logger = logging.getLogger(__name__)

# Import service clients for cross-service validation
try:
    from microservices.storage_service.client import StorageServiceClient
except ImportError:
    StorageServiceClient = None
    logger.warning("StorageServiceClient not available - file validation disabled")

try:
    from microservices.device_service.client import DeviceServiceClient
except ImportError:
    DeviceServiceClient = None
    logger.warning("DeviceServiceClient not available - device validation disabled")


# ==================== Custom Exceptions ====================


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


# ==================== Media Service ====================


class MediaService:
    """Media service - business logic layer for media operations"""

    def __init__(self, event_bus=None):
        """Initialize media service"""
        self.repository = MediaRepository()
        self.event_bus = event_bus

        # Initialize service clients for cross-service validation
        self.storage_client = StorageServiceClient() if StorageServiceClient else None
        self.device_client = DeviceServiceClient() if DeviceServiceClient else None

        if self.storage_client:
            logger.info("StorageServiceClient initialized for file validation")
        if self.device_client:
            logger.info("DeviceServiceClient initialized for device validation")

    # ==================== Photo Version Operations ====================

    async def create_photo_version(
        self,
        request: PhotoVersionCreateRequest,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> PhotoVersionResponse:
        """
        Create a new photo version

        Args:
            request: Photo version creation request
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            PhotoVersionResponse

        Raises:
            MediaValidationError: If request validation fails
            MediaServiceError: If creation fails
        """
        try:
            # Validate request
            self._validate_photo_version_request(request)

            # Generate version_id
            version_id = f"ver_{uuid.uuid4().hex[:16]}"

            # Get current version count for this photo
            existing_versions = await self.repository.list_photo_versions(
                request.photo_id, user_id
            )
            version_number = len(existing_versions) + 1

            # Create photo version object
            photo_version = PhotoVersion(
                version_id=version_id,
                photo_id=request.photo_id,
                user_id=user_id,
                organization_id=organization_id,
                version_name=request.version_name,
                version_type=request.version_type,
                processing_mode=request.processing_mode,
                file_id=request.file_id,
                processing_params=request.processing_params or {},
                metadata={},
                is_current=False,
                version_number=version_number,
            )

            # Save to database
            created_version = await self.repository.create_photo_version(photo_version)

            if not created_version:
                raise MediaServiceError("Failed to create photo version")

            # Publish photo_version.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.PHOTO_VERSION_CREATED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "version_id": created_version.version_id,
                            "photo_id": created_version.photo_id,
                            "user_id": user_id,
                            "version_type": created_version.version_type.value,
                            "version_number": created_version.version_number,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish photo_version.created event: {e}")

            return self._version_to_response(created_version)

        except MediaValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating photo version: {e}")
            raise MediaServiceError(f"Failed to create photo version: {str(e)}")

    async def get_photo_version(
        self, version_id: str, user_id: str
    ) -> PhotoVersionResponse:
        """
        Get photo version by ID

        Args:
            version_id: Version ID
            user_id: User ID for permission check

        Returns:
            PhotoVersionResponse

        Raises:
            MediaNotFoundError: If version not found
            MediaPermissionError: If user doesn't have access
        """
        version = await self.repository.get_photo_version(version_id)

        if not version:
            raise MediaNotFoundError(f"Photo version {version_id} not found")

        if version.user_id != user_id:
            raise MediaPermissionError("Access denied to this photo version")

        return self._version_to_response(version)

    async def list_photo_versions(
        self, photo_id: str, user_id: str
    ) -> List[PhotoVersionResponse]:
        """
        List all versions of a photo

        Args:
            photo_id: Photo ID
            user_id: User ID

        Returns:
            List of PhotoVersionResponse
        """
        versions = await self.repository.list_photo_versions(photo_id, user_id)
        return [self._version_to_response(v) for v in versions]

    # ==================== Photo Metadata Operations ====================

    async def update_photo_metadata(
        self,
        file_id: str,
        user_id: str,
        request: PhotoMetadataUpdateRequest,
        organization_id: Optional[str] = None,
    ) -> PhotoMetadataResponse:
        """
        Update or create photo metadata

        Args:
            file_id: File ID
            user_id: User ID
            request: Metadata update request
            organization_id: Optional organization ID

        Returns:
            PhotoMetadataResponse
        """
        try:
            # Get existing metadata or create new
            existing = await self.repository.get_photo_metadata(file_id)

            if existing:
                # Update existing metadata
                metadata_data = existing.model_copy()
                if request.ai_labels is not None:
                    metadata_data.ai_labels = request.ai_labels
                if request.ai_objects is not None:
                    metadata_data.ai_objects = request.ai_objects
                if request.ai_scenes is not None:
                    metadata_data.ai_scenes = request.ai_scenes
                if request.ai_colors is not None:
                    metadata_data.ai_colors = request.ai_colors
                if request.face_detection is not None:
                    metadata_data.face_detection = request.face_detection
                if request.quality_score is not None:
                    metadata_data.quality_score = request.quality_score
            else:
                # Create new metadata
                metadata_data = PhotoMetadata(
                    file_id=file_id,
                    user_id=user_id,
                    organization_id=organization_id,
                    ai_labels=request.ai_labels or [],
                    ai_objects=request.ai_objects or [],
                    ai_scenes=request.ai_scenes or [],
                    ai_colors=request.ai_colors or [],
                    face_detection=request.face_detection or {},
                    quality_score=request.quality_score,
                )

            # Save to database
            updated = await self.repository.create_or_update_metadata(metadata_data)

            if not updated:
                raise MediaServiceError("Failed to update photo metadata")

            # Publish photo_metadata.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.PHOTO_METADATA_UPDATED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "file_id": file_id,
                            "user_id": user_id,
                            "has_ai_labels": bool(updated.ai_labels),
                            "has_face_detection": bool(updated.face_detection),
                            "quality_score": updated.quality_score,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish photo_metadata.updated event: {e}")

            return self._metadata_to_response(updated)

        except Exception as e:
            logger.error(f"Error updating photo metadata: {e}")
            raise MediaServiceError(f"Failed to update metadata: {str(e)}")

    async def get_photo_metadata(
        self, file_id: str, user_id: str
    ) -> Optional[PhotoMetadataResponse]:
        """
        Get photo metadata by file ID

        Args:
            file_id: File ID
            user_id: User ID for permission check

        Returns:
            PhotoMetadataResponse or None
        """
        metadata = await self.repository.get_photo_metadata(file_id)

        if not metadata:
            return None

        if metadata.user_id != user_id:
            raise MediaPermissionError("Access denied to this metadata")

        return self._metadata_to_response(metadata)

    # ==================== Playlist Operations ====================

    async def create_playlist(
        self,
        request: PlaylistCreateRequest,
        user_id: str,
        organization_id: Optional[str] = None,
    ) -> PlaylistResponse:
        """
        Create a new playlist

        Args:
            request: Playlist creation request
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            PlaylistResponse
        """
        try:
            # Validate request
            self._validate_playlist_request(request)

            # Generate playlist_id
            playlist_id = f"pl_{uuid.uuid4().hex[:16]}"

            # Create playlist object
            playlist = Playlist(
                playlist_id=playlist_id,
                name=request.name,
                description=request.description,
                user_id=user_id,
                organization_id=organization_id,
                playlist_type=request.playlist_type,
                smart_criteria=request.smart_criteria or {},
                photo_ids=request.photo_ids or [],
                shuffle=request.shuffle,
                loop=request.loop,
                transition_duration=request.transition_duration,
            )

            # Save to database
            created = await self.repository.create_playlist(playlist)

            if not created:
                raise MediaServiceError("Failed to create playlist")

            # Publish playlist.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.MEDIA_PLAYLIST_CREATED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "playlist_id": created.playlist_id,
                            "name": created.name,
                            "user_id": user_id,
                            "playlist_type": created.playlist_type.value,
                            "photo_count": len(created.photo_ids),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish playlist.created event: {e}")

            return self._playlist_to_response(created)

        except MediaValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            raise MediaServiceError(f"Failed to create playlist: {str(e)}")

    async def get_playlist(self, playlist_id: str, user_id: str) -> PlaylistResponse:
        """
        Get playlist by ID

        Args:
            playlist_id: Playlist ID
            user_id: User ID for permission check

        Returns:
            PlaylistResponse
        """
        playlist = await self.repository.get_playlist(playlist_id)

        if not playlist:
            raise MediaNotFoundError(f"Playlist {playlist_id} not found")

        if playlist.user_id != user_id:
            raise MediaPermissionError("Access denied to this playlist")

        return self._playlist_to_response(playlist)

    async def list_user_playlists(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[PlaylistResponse]:
        """
        List user's playlists

        Args:
            user_id: User ID
            limit: Results limit
            offset: Results offset

        Returns:
            List of PlaylistResponse
        """
        playlists = await self.repository.list_user_playlists(user_id, limit, offset)
        return [self._playlist_to_response(p) for p in playlists]

    async def update_playlist(
        self, playlist_id: str, user_id: str, request: PlaylistUpdateRequest
    ) -> PlaylistResponse:
        """
        Update playlist

        Args:
            playlist_id: Playlist ID
            user_id: User ID for permission check
            request: Update request

        Returns:
            PlaylistResponse
        """
        try:
            # Check playlist exists and user has access
            existing = await self.repository.get_playlist(playlist_id)
            if not existing:
                raise MediaNotFoundError(f"Playlist {playlist_id} not found")

            if existing.user_id != user_id:
                raise MediaPermissionError("Access denied to this playlist")

            # Build update data
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.description is not None:
                update_data["description"] = request.description
            if request.photo_ids is not None:
                update_data["photo_ids"] = request.photo_ids
            if request.smart_criteria is not None:
                update_data["smart_criteria"] = request.smart_criteria
            if request.shuffle is not None:
                update_data["shuffle"] = request.shuffle
            if request.loop is not None:
                update_data["loop"] = request.loop
            if request.transition_duration is not None:
                update_data["transition_duration"] = request.transition_duration

            # Update playlist
            updated = await self.repository.update_playlist(
                playlist_id, user_id, update_data
            )

            if not updated:
                raise MediaServiceError("Failed to update playlist")

            # Publish playlist.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.MEDIA_PLAYLIST_UPDATED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "playlist_id": playlist_id,
                            "user_id": user_id,
                            "updated_fields": list(update_data.keys()),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish playlist.updated event: {e}")

            return self._playlist_to_response(updated)

        except (MediaNotFoundError, MediaPermissionError):
            raise
        except Exception as e:
            logger.error(f"Error updating playlist: {e}")
            raise MediaServiceError(f"Failed to update playlist: {str(e)}")

    async def delete_playlist(self, playlist_id: str, user_id: str) -> bool:
        """
        Delete playlist

        Args:
            playlist_id: Playlist ID
            user_id: User ID for permission check

        Returns:
            True if deleted
        """
        try:
            # Check playlist exists and user has access
            existing = await self.repository.get_playlist(playlist_id)
            if not existing:
                raise MediaNotFoundError(f"Playlist {playlist_id} not found")

            if existing.user_id != user_id:
                raise MediaPermissionError("Access denied to this playlist")

            result = await self.repository.delete_playlist(playlist_id, user_id)

            # Publish playlist.deleted event
            if result and self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.MEDIA_PLAYLIST_DELETED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "playlist_id": playlist_id,
                            "user_id": user_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish playlist.deleted event: {e}")

            return result

        except (MediaNotFoundError, MediaPermissionError):
            raise
        except Exception as e:
            logger.error(f"Error deleting playlist: {e}")
            raise MediaServiceError(f"Failed to delete playlist: {str(e)}")

    # ==================== Rotation Schedule Operations ====================

    async def create_rotation_schedule(
        self, request: RotationScheduleCreateRequest, user_id: str
    ) -> RotationScheduleResponse:
        """
        Create a new rotation schedule for a smart frame

        Args:
            request: Schedule creation request
            user_id: User ID

        Returns:
            RotationScheduleResponse
        """
        try:
            # Validate request
            self._validate_schedule_request(request)

            # Generate schedule_id
            schedule_id = f"sch_{uuid.uuid4().hex[:16]}"

            # Create schedule object
            schedule = RotationSchedule(
                schedule_id=schedule_id,
                user_id=user_id,
                frame_id=request.frame_id,
                playlist_id=request.playlist_id,
                schedule_type=request.schedule_type,
                start_time=request.start_time,
                end_time=request.end_time,
                days_of_week=request.days_of_week or [],
                rotation_interval=request.rotation_interval,
                shuffle=request.shuffle,
                is_active=True,
            )

            # Save to database
            created = await self.repository.create_rotation_schedule(schedule)

            if not created:
                raise MediaServiceError("Failed to create rotation schedule")

            # Publish rotation_schedule.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.ROTATION_SCHEDULE_CREATED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "schedule_id": created.schedule_id,
                            "frame_id": created.frame_id,
                            "playlist_id": created.playlist_id,
                            "user_id": user_id,
                            "schedule_type": created.schedule_type.value,
                            "rotation_interval": created.rotation_interval,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(
                        f"Failed to publish rotation_schedule.created event: {e}"
                    )

            return self._schedule_to_response(created)

        except MediaValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating rotation schedule: {e}")
            raise MediaServiceError(f"Failed to create schedule: {str(e)}")

    async def get_rotation_schedule(
        self, schedule_id: str, user_id: str
    ) -> RotationScheduleResponse:
        """Get rotation schedule by ID"""
        schedule = await self.repository.get_rotation_schedule(schedule_id)

        if not schedule:
            raise MediaNotFoundError(f"Schedule {schedule_id} not found")

        if schedule.user_id != user_id:
            raise MediaPermissionError("Access denied to this schedule")

        return self._schedule_to_response(schedule)

    async def list_frame_schedules(
        self, frame_id: str, user_id: str
    ) -> List[RotationScheduleResponse]:
        """List all schedules for a frame"""
        schedules = await self.repository.list_frame_schedules(frame_id, user_id)
        return [self._schedule_to_response(s) for s in schedules]

    async def update_schedule_status(
        self, schedule_id: str, user_id: str, is_active: bool
    ) -> RotationScheduleResponse:
        """Update schedule active status"""
        try:
            # Check schedule exists and user has access
            existing = await self.repository.get_rotation_schedule(schedule_id)
            if not existing:
                raise MediaNotFoundError(f"Schedule {schedule_id} not found")

            if existing.user_id != user_id:
                raise MediaPermissionError("Access denied to this schedule")

            # Update status
            updated = await self.repository.update_schedule_status(
                schedule_id, user_id, is_active
            )

            if not updated:
                raise MediaServiceError("Failed to update schedule status")

            # Publish rotation_schedule.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.ROTATION_SCHEDULE_UPDATED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "schedule_id": schedule_id,
                            "user_id": user_id,
                            "is_active": is_active,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(
                        f"Failed to publish rotation_schedule.updated event: {e}"
                    )

            return self._schedule_to_response(updated)

        except (MediaNotFoundError, MediaPermissionError):
            raise
        except Exception as e:
            logger.error(f"Error updating schedule status: {e}")
            raise MediaServiceError(f"Failed to update schedule: {str(e)}")

    async def delete_rotation_schedule(self, schedule_id: str, user_id: str) -> bool:
        """Delete rotation schedule"""
        try:
            existing = await self.repository.get_rotation_schedule(schedule_id)
            if not existing:
                raise MediaNotFoundError(f"Schedule {schedule_id} not found")

            if existing.user_id != user_id:
                raise MediaPermissionError("Access denied to this schedule")

            return await self.repository.delete_rotation_schedule(schedule_id, user_id)

        except (MediaNotFoundError, MediaPermissionError):
            raise
        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            raise MediaServiceError(f"Failed to delete schedule: {str(e)}")

    # ==================== Photo Cache Operations ====================

    async def cache_photo_for_frame(
        self,
        frame_id: str,
        photo_id: str,
        user_id: str,
        version_id: Optional[str] = None,
    ) -> PhotoCacheResponse:
        """
        Create cache entry for a photo on a smart frame

        Args:
            frame_id: Smart frame device ID
            photo_id: Photo ID
            user_id: User ID
            version_id: Optional specific version ID

        Returns:
            PhotoCacheResponse
        """
        try:
            # Check if already cached
            existing = await self.repository.get_frame_cache(
                frame_id, photo_id, user_id
            )

            if existing and existing.cache_status == CacheStatus.CACHED:
                # Already cached, increment hit count
                await self.repository.increment_cache_hit(existing.cache_id)
                return self._cache_to_response(existing)

            # Generate cache_id
            cache_id = f"cache_{uuid.uuid4().hex[:16]}"

            # Create cache entry
            cache_entry = PhotoCache(
                cache_id=cache_id,
                user_id=user_id,
                frame_id=frame_id,
                photo_id=photo_id,
                version_id=version_id,
                cache_status=CacheStatus.PENDING,
                hit_count=0,
                retry_count=0,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )

            # Save to database
            created = await self.repository.create_photo_cache(cache_entry)

            if not created:
                raise MediaServiceError("Failed to create cache entry")

            # Publish photo.cached event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.PHOTO_CACHED,
                        source=ServiceSource.MEDIA_SERVICE,
                        data={
                            "cache_id": created.cache_id,
                            "frame_id": frame_id,
                            "photo_id": photo_id,
                            "user_id": user_id,
                            "version_id": version_id,
                            "cache_status": created.cache_status.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish photo.cached event: {e}")

            return self._cache_to_response(created)

        except Exception as e:
            logger.error(f"Error caching photo: {e}")
            raise MediaServiceError(f"Failed to cache photo: {str(e)}")

    async def update_cache_status(
        self, cache_id: str, status: CacheStatus, error_message: Optional[str] = None
    ) -> PhotoCacheResponse:
        """Update photo cache status"""
        try:
            updated = await self.repository.update_cache_status(
                cache_id, status, error_message
            )

            if not updated:
                raise MediaServiceError("Failed to update cache status")

            return self._cache_to_response(updated)

        except Exception as e:
            logger.error(f"Error updating cache status: {e}")
            raise MediaServiceError(f"Failed to update cache: {str(e)}")

    async def list_frame_cache(
        self, frame_id: str, user_id: str, status: Optional[CacheStatus] = None
    ) -> List[PhotoCacheResponse]:
        """List cache entries for a frame"""
        cache_entries = await self.repository.list_frame_cache(
            frame_id, user_id, status
        )
        return [self._cache_to_response(c) for c in cache_entries]

    # ==================== Validation Methods ====================

    def _validate_photo_version_request(self, request: PhotoVersionCreateRequest):
        """Validate photo version creation request"""
        if not request.version_name or len(request.version_name.strip()) == 0:
            raise MediaValidationError("Version name is required")

        if len(request.version_name) > 255:
            raise MediaValidationError("Version name too long (max 255 characters)")

    def _validate_playlist_request(self, request: PlaylistCreateRequest):
        """Validate playlist creation request"""
        if not request.name or len(request.name.strip()) == 0:
            raise MediaValidationError("Playlist name is required")

        if len(request.name) > 255:
            raise MediaValidationError("Playlist name too long (max 255 characters)")

        # Allow empty manual playlists - users can add photos later
        # if request.playlist_type == PlaylistType.MANUAL and not request.photo_ids:
        #     raise MediaValidationError("Manual playlists require at least one photo")

        if request.playlist_type == PlaylistType.SMART and not request.smart_criteria:
            raise MediaValidationError("Smart playlists require smart criteria")

    def _validate_schedule_request(self, request: RotationScheduleCreateRequest):
        """Validate rotation schedule request"""
        if request.rotation_interval < 1:
            raise MediaValidationError("Rotation interval must be at least 1 second")

        if request.schedule_type == ScheduleType.TIME_BASED:
            if not request.start_time or not request.end_time:
                raise MediaValidationError(
                    "Time-based schedules require start_time and end_time"
                )

    # ==================== Response Converters ====================

    def _version_to_response(self, version: PhotoVersion) -> PhotoVersionResponse:
        """Convert PhotoVersion to response"""
        return PhotoVersionResponse(
            version_id=version.version_id,
            photo_id=version.photo_id,
            user_id=version.user_id,
            version_name=version.version_name,
            version_type=version.version_type,
            file_id=version.file_id,
            cloud_url=version.cloud_url,
            file_size=version.file_size,
            is_current=version.is_current,
            version_number=version.version_number,
            created_at=version.created_at,
        )

    def _metadata_to_response(self, metadata: PhotoMetadata) -> PhotoMetadataResponse:
        """Convert PhotoMetadata to response"""
        return PhotoMetadataResponse(
            file_id=metadata.file_id,
            camera_model=metadata.camera_model,
            location_name=metadata.location_name,
            photo_taken_at=metadata.photo_taken_at,
            ai_labels=metadata.ai_labels,
            ai_objects=metadata.ai_objects,
            ai_scenes=metadata.ai_scenes,
            quality_score=metadata.quality_score,
            full_metadata=metadata.full_metadata,
        )

    def _playlist_to_response(self, playlist: Playlist) -> PlaylistResponse:
        """Convert Playlist to response"""
        return PlaylistResponse(
            playlist_id=playlist.playlist_id,
            name=playlist.name,
            description=playlist.description,
            user_id=playlist.user_id,
            playlist_type=playlist.playlist_type,
            photo_ids=playlist.photo_ids,
            shuffle=playlist.shuffle,
            loop=playlist.loop,
            transition_duration=playlist.transition_duration,
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
        )

    def _schedule_to_response(
        self, schedule: RotationSchedule
    ) -> RotationScheduleResponse:
        """Convert RotationSchedule to response"""
        return RotationScheduleResponse(
            schedule_id=schedule.schedule_id,
            frame_id=schedule.frame_id,
            playlist_id=schedule.playlist_id,
            schedule_type=schedule.schedule_type,
            rotation_interval=schedule.rotation_interval,
            is_active=schedule.is_active,
            created_at=schedule.created_at,
        )

    def _cache_to_response(self, cache: PhotoCache) -> PhotoCacheResponse:
        """Convert PhotoCache to response"""
        return PhotoCacheResponse(
            cache_id=cache.cache_id,
            frame_id=cache.frame_id,
            photo_id=cache.photo_id,
            cache_status=cache.cache_status,
            hit_count=cache.hit_count,
            last_accessed_at=cache.last_accessed_at,
        )

    # ==================== Health Check ====================

    async def check_health(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            db_connected = await self.repository.check_connection()
            return {
                "service": "media_service",
                "status": "healthy" if db_connected else "unhealthy",
                "database": "connected" if db_connected else "disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "media_service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
