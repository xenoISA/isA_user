"""
Album Service Event Handlers

Handles incoming events from other services via NATS
"""

import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType

logger = logging.getLogger(__name__)


class AlbumEventHandler:
    """
    Handles events subscribed by Album Service

    Subscribes to:
    - file.deleted: Remove deleted photos from all albums
    - device.deleted: Clean up sync status for deleted devices
    """

    def __init__(self, album_repository):
        """
        Initialize event handler

        Args:
            album_repository: AlbumRepository instance for data access
        """
        self.album_repo = album_repository

    async def handle_file_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle file.deleted event

        When a photo is deleted from storage, remove it from all albums

        Args:
            event_data: Event data containing file_id

        Returns:
            bool: True if handled successfully
        """
        try:
            file_id = event_data.get('file_id')
            if not file_id:
                logger.warning("file.deleted event missing file_id")
                return False

            logger.info(f"Handling file.deleted event for file {file_id}")

            # Remove photo from all albums
            # We'll need to add a method to the repository for this
            removed_count = await self.album_repo.remove_photo_from_all_albums(file_id)

            logger.info(f"Removed photo {file_id} from {removed_count} albums")
            return True

        except Exception as e:
            logger.error(f"Failed to handle file.deleted event: {e}", exc_info=True)
            return False

    async def handle_device_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle device.deleted event

        When a device/frame is deleted, clean up sync status

        Args:
            event_data: Event data containing device_id

        Returns:
            bool: True if handled successfully
        """
        try:
            device_id = event_data.get('device_id')
            if not device_id:
                logger.warning("device.deleted event missing device_id")
                return False

            logger.info(f"Handling device.deleted event for device {device_id}")

            # Clean up sync status for this device
            # We'll need to add a method to the repository for this
            deleted_count = await self.album_repo.delete_sync_status_by_frame(device_id)

            logger.info(f"Deleted {deleted_count} sync status records for device {device_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle device.deleted event: {e}", exc_info=True)
            return False

    async def handle_event(self, event: Event) -> bool:
        """
        Route event to appropriate handler

        Args:
            event: The event to handle

        Returns:
            bool: True if handled successfully
        """
        try:
            event_type = event.type

            if event_type == EventType.FILE_DELETED.value:
                return await self.handle_file_deleted(event.data)
            elif event_type == EventType.DEVICE_OFFLINE.value:
                # We're treating device.deleted similarly to device.offline
                # You may need to add DEVICE_DELETED to EventType enum
                return await self.handle_device_deleted(event.data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to handle event: {e}", exc_info=True)
            return False

    def get_subscriptions(self) -> list:
        """
        Get list of event types this handler subscribes to

        Returns:
            list: List of event type values to subscribe to
        """
        return [
            EventType.FILE_DELETED.value,
            # Note: You may want to add DEVICE_DELETED to EventType enum
            # For now we're using DEVICE_OFFLINE as a proxy
        ]
