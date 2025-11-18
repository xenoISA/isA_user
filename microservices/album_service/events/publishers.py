"""
Event Publishers for Album Service

Centralized event publishing logic for album_service
Publishes events to NATS for other services to consume
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    AlbumCreatedEventData,
    AlbumPhotoAddedEventData,
    AlbumPhotoRemovedEventData,
    AlbumSharedEventData,
    AlbumDeletedEventData,
    AlbumSyncedEventData
)

logger = logging.getLogger(__name__)


class AlbumEventPublishers:
    """Publishers for album service events"""

    def __init__(self, event_bus):
        """
        Initialize event publishers

        Args:
            event_bus: NATS event bus instance
        """
        self.event_bus = event_bus

    async def publish_album_created(
        self,
        album_id: str,
        album_name: str,
        owner_id: str,
        shared_with: List[str],
        album_type: str = "personal"
    ):
        """
        Publish album.created event

        Args:
            album_id: Album ID
            album_name: Album name
            owner_id: Owner user ID
            shared_with: List of user IDs with access
            album_type: Album type (personal, family, shared)
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping album.created event")
            return

        try:
            event_data = AlbumCreatedEventData(
                album_id=album_id,
                album_name=album_name,
                owner_id=owner_id,
                shared_with=shared_with,
                album_type=album_type,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.ALBUM_CREATED,
                source=ServiceSource.ALBUM_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published album.created event for {album_id}")

        except Exception as e:
            logger.error(f"Failed to publish album.created event: {e}")

    async def publish_album_photo_added(
        self,
        album_id: str,
        file_id: str,
        added_by: str,
        photo_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Publish album.photo_added event

        Args:
            album_id: Album ID
            file_id: Photo file ID
            added_by: User ID who added the photo
            photo_metadata: Optional photo metadata
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping album.photo_added event")
            return

        try:
            event_data = AlbumPhotoAddedEventData(
                album_id=album_id,
                file_id=file_id,
                added_by=added_by,
                photo_metadata=photo_metadata,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.ALBUM_PHOTO_ADDED,
                source=ServiceSource.ALBUM_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published album.photo_added event for album {album_id}")

        except Exception as e:
            logger.error(f"Failed to publish album.photo_added event: {e}")

    async def publish_album_photo_removed(
        self,
        album_id: str,
        file_id: str,
        removed_by: str
    ):
        """
        Publish album.photo_removed event

        Args:
            album_id: Album ID
            file_id: Photo file ID
            removed_by: User ID who removed the photo
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping album.photo_removed event")
            return

        try:
            event_data = AlbumPhotoRemovedEventData(
                album_id=album_id,
                file_id=file_id,
                removed_by=removed_by,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.ALBUM_PHOTO_REMOVED,
                source=ServiceSource.ALBUM_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published album.photo_removed event for album {album_id}")

        except Exception as e:
            logger.error(f"Failed to publish album.photo_removed event: {e}")

    async def publish_album_shared(
        self,
        album_id: str,
        album_name: str,
        shared_by: str,
        shared_with: List[str],
        permission: str = "view"
    ):
        """
        Publish album.shared event

        Args:
            album_id: Album ID
            album_name: Album name
            shared_by: User ID who shared
            shared_with: List of user IDs granted access
            permission: Permission level (view, edit, admin)
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping album.shared event")
            return

        try:
            event_data = AlbumSharedEventData(
                album_id=album_id,
                album_name=album_name,
                shared_by=shared_by,
                shared_with=shared_with,
                permission=permission,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.ALBUM_SHARED,
                source=ServiceSource.ALBUM_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published album.shared event for album {album_id}")

        except Exception as e:
            logger.error(f"Failed to publish album.shared event: {e}")

    async def publish_album_deleted(
        self,
        album_id: str,
        deleted_by: str,
        photo_count: int
    ):
        """
        Publish album.deleted event

        Args:
            album_id: Album ID
            deleted_by: User ID who deleted
            photo_count: Number of photos in album
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping album.deleted event")
            return

        try:
            event_data = AlbumDeletedEventData(
                album_id=album_id,
                deleted_by=deleted_by,
                photo_count=photo_count,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.ALBUM_DELETED,
                source=ServiceSource.ALBUM_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published album.deleted event for album {album_id}")

        except Exception as e:
            logger.error(f"Failed to publish album.deleted event: {e}")

    async def publish_album_synced(
        self,
        album_id: str,
        frame_id: str,
        photo_count: int,
        sync_status: str
    ):
        """
        Publish album.synced event

        Args:
            album_id: Album ID
            frame_id: Frame/device ID
            photo_count: Number of photos synced
            sync_status: Sync status (pending, completed, failed)
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping album.synced event")
            return

        try:
            event_data = AlbumSyncedEventData(
                album_id=album_id,
                frame_id=frame_id,
                photo_count=photo_count,
                sync_status=sync_status,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.ALBUM_SYNCED,
                source=ServiceSource.ALBUM_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published album.synced event for album {album_id} to frame {frame_id}")

        except Exception as e:
            logger.error(f"Failed to publish album.synced event: {e}")
