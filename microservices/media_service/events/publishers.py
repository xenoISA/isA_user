"""
Event Publishers for Media Service

Centralized event publishing logic for media_service
Publishes events to NATS for other services to consume
"""

import logging
from datetime import datetime
from typing import Optional, List

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    MediaVersionCreatedEventData,
    MediaCacheReadyEventData,
    MediaMetadataUpdatedEventData,
    PlaylistCreatedEventData
)

logger = logging.getLogger(__name__)


class MediaEventPublishers:
    """Publishers for media service events"""

    def __init__(self, event_bus):
        """
        Initialize event publishers

        Args:
            event_bus: NATS event bus instance
        """
        self.event_bus = event_bus

    async def publish_media_version_created(
        self,
        file_id: str,
        version_id: str,
        size_variant: str,
        width: int,
        height: int,
        file_size: int,
        storage_path: str
    ):
        """
        Publish media.version_created event

        Args:
            file_id: Original file ID
            version_id: Version ID
            size_variant: Size (thumbnail, hd, original)
            width: Width in pixels
            height: Height in pixels
            file_size: File size in bytes
            storage_path: Storage path
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping media.version_created event")
            return

        try:
            event_data = MediaVersionCreatedEventData(
                file_id=file_id,
                version_id=version_id,
                size_variant=size_variant,
                width=width,
                height=height,
                file_size=file_size,
                storage_path=storage_path,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.MEDIA_VERSION_CREATED,
                source=ServiceSource.MEDIA_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published media.version_created event for {file_id} ({size_variant})")

        except Exception as e:
            logger.error(f"Failed to publish media.version_created event: {e}")

    async def publish_media_cache_ready(
        self,
        file_id: str,
        frame_id: str,
        cached_versions: List[str],
        cache_size: int
    ):
        """
        Publish media.cache_ready event

        Args:
            file_id: File ID
            frame_id: Frame/device ID
            cached_versions: List of cached size variants
            cache_size: Total cache size in bytes
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping media.cache_ready event")
            return

        try:
            event_data = MediaCacheReadyEventData(
                file_id=file_id,
                frame_id=frame_id,
                cached_versions=cached_versions,
                cache_size=cache_size,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.MEDIA_CACHE_READY,
                source=ServiceSource.MEDIA_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published media.cache_ready event for {file_id} on frame {frame_id}")

        except Exception as e:
            logger.error(f"Failed to publish media.cache_ready event: {e}")

    async def publish_media_metadata_updated(
        self,
        file_id: str,
        user_id: str,
        ai_labels: List[str],
        ai_scenes: List[str],
        quality_score: Optional[float] = None
    ):
        """
        Publish media.metadata_updated event

        Args:
            file_id: File ID
            user_id: User ID
            ai_labels: AI detected labels
            ai_scenes: AI detected scenes
            quality_score: Quality score 0-1
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping media.metadata_updated event")
            return

        try:
            event_data = MediaMetadataUpdatedEventData(
                file_id=file_id,
                user_id=user_id,
                ai_labels=ai_labels,
                ai_scenes=ai_scenes,
                quality_score=quality_score,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.MEDIA_METADATA_UPDATED,
                source=ServiceSource.MEDIA_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published media.metadata_updated event for {file_id}")

        except Exception as e:
            logger.error(f"Failed to publish media.metadata_updated event: {e}")

    async def publish_playlist_created(
        self,
        playlist_id: str,
        playlist_name: str,
        user_id: str,
        photo_count: int,
        frame_id: Optional[str] = None
    ):
        """
        Publish media.playlist_created event

        Args:
            playlist_id: Playlist ID
            playlist_name: Playlist name
            user_id: User ID
            photo_count: Number of photos
            frame_id: Optional assigned frame ID
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping media.playlist_created event")
            return

        try:
            event_data = PlaylistCreatedEventData(
                playlist_id=playlist_id,
                playlist_name=playlist_name,
                user_id=user_id,
                photo_count=photo_count,
                frame_id=frame_id,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.MEDIA_PLAYLIST_CREATED,
                source=ServiceSource.MEDIA_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published media.playlist_created event for {playlist_id}")

        except Exception as e:
            logger.error(f"Failed to publish media.playlist_created event: {e}")
