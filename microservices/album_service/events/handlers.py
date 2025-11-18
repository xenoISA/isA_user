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
    - file.uploaded.with_ai: Add photo to user's default album or specified album
    - file.deleted: Remove deleted photos from all albums
    - device.deleted: Clean up sync status for deleted devices
    """

    def __init__(self, album_repository, album_service=None, mqtt_publisher=None):
        """
        Initialize event handler

        Args:
            album_repository: AlbumRepository instance for data access
            album_service: AlbumService instance for business logic
            mqtt_publisher: AlbumMQTTPublisher instance for MQTT notifications
        """
        self.album_repo = album_repository
        self.album_service = album_service
        self.mqtt_publisher = mqtt_publisher

    async def handle_file_uploaded_with_ai(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle file.uploaded.with_ai event

        When a photo is uploaded with AI metadata, automatically add it to:
        1. Album specified in upload metadata (if provided)
        2. User's default album (if no album specified)

        Then publish MQTT notification to subscribed smart frames

        Args:
            event_data: Event data containing file_id, user_id, metadata

        Returns:
            bool: True if handled successfully
        """
        try:
            file_id = event_data.get('file_id')
            user_id = event_data.get('user_id')
            metadata = event_data.get('metadata', {})
            ai_metadata = event_data.get('ai_metadata', {})

            if not file_id or not user_id:
                logger.warning("file.uploaded.with_ai event missing file_id or user_id")
                return False

            logger.info(f"Handling file.uploaded.with_ai event for file {file_id}")

            # Check if album_id is specified in upload metadata
            album_id = metadata.get('album_id')

            if album_id:
                # Add photo to specified album
                await self.album_repo.add_photo_to_album(album_id, file_id, user_id)
                logger.info(f"Added photo {file_id} to specified album {album_id}")

                # Publish MQTT notification
                if self.mqtt_publisher:
                    photo_metadata = {
                        'file_name': event_data.get('file_name'),
                        'content_type': event_data.get('content_type'),
                        'file_size': event_data.get('file_size'),
                        'ai_metadata': ai_metadata,
                        'created_at': event_data.get('timestamp')
                    }
                    await self.mqtt_publisher.publish_photo_added(
                        album_id=album_id,
                        file_id=file_id,
                        photo_metadata=photo_metadata
                    )

                # Publish NATS event if album_service is available
                if self.album_service and hasattr(self.album_service, 'event_publishers'):
                    await self.album_service.event_publishers.publish_album_photo_added(
                        album_id=album_id,
                        file_id=file_id,
                        added_by=user_id,
                        photo_metadata=photo_metadata
                    )

            else:
                # Get or create user's default album
                # This requires album_service to have a get_or_create_default_album method
                if self.album_service:
                    default_album = await self.album_service.get_or_create_default_album(user_id)
                    if default_album:
                        album_id = default_album.get('album_id')
                        await self.album_repo.add_photo_to_album(album_id, file_id, user_id)
                        logger.info(f"Added photo {file_id} to default album {album_id}")

                        # Publish MQTT notification
                        if self.mqtt_publisher:
                            photo_metadata = {
                                'file_name': event_data.get('file_name'),
                                'content_type': event_data.get('content_type'),
                                'file_size': event_data.get('file_size'),
                                'ai_metadata': ai_metadata,
                                'created_at': event_data.get('timestamp')
                            }
                            await self.mqtt_publisher.publish_photo_added(
                                album_id=album_id,
                                file_id=file_id,
                                photo_metadata=photo_metadata
                            )

            return True

        except Exception as e:
            logger.error(f"Failed to handle file.uploaded.with_ai event: {e}", exc_info=True)
            return False

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

            if event_type == EventType.FILE_UPLOADED_WITH_AI.value:
                return await self.handle_file_uploaded_with_ai(event.data)
            elif event_type == EventType.FILE_DELETED.value:
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
