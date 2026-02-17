"""
MQTT Publisher for Album Service

Publishes MQTT messages to notify smart frames about album updates.
Uses centralized MQTTEventBus from core.mqtt_client for async operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.mqtt_client import MQTTEventBus, MQTTTopics, get_mqtt_bus

logger = logging.getLogger(__name__)


class AlbumMQTTPublisher:
    """MQTT publisher for album service to notify smart frames"""

    def __init__(self, mqtt_host: str = "localhost", mqtt_port: int = 50053):
        """
        Initialize MQTT publisher

        Args:
            mqtt_host: MQTT adapter gRPC host
            mqtt_port: MQTT adapter gRPC port
        """
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_bus: Optional[MQTTEventBus] = None
        self._initialized = False

        logger.info(f"AlbumMQTTPublisher initialized (host: {mqtt_host}, port: {mqtt_port})")

    async def _ensure_connected(self):
        """Ensure MQTT bus is connected (lazy initialization)"""
        if self._initialized and self.mqtt_bus and self.mqtt_bus.connected:
            return

        try:
            self.mqtt_bus = MQTTEventBus(
                service_name="album_service",
                host=self.mqtt_host,
                port=self.mqtt_port,
            )
            await self.mqtt_bus.connect()
            self._initialized = True
            logger.info("AlbumMQTTPublisher connected to MQTT bus")

        except Exception as e:
            logger.error(f"Failed to connect to MQTT bus: {e}")
            self._initialized = False
            raise

    async def connect(self):
        """Connect to MQTT broker via adapter (backward compatibility)"""
        await self._ensure_connected()

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.mqtt_bus:
            await self.mqtt_bus.close()
            self._initialized = False
            self.mqtt_bus = None
            logger.info("AlbumMQTTPublisher disconnected")

    async def publish_photo_added(
        self,
        album_id: str,
        file_id: str,
        photo_metadata: Dict[str, Any],
        media_service_url: Optional[str] = None,
        download_url: Optional[str] = None,
    ) -> bool:
        """
        Publish photo_added event to MQTT for smart frames

        Topic: albums/{album_id}/photo_added
        QoS: 1 (at least once delivery)

        Args:
            album_id: Album ID
            file_id: Photo file ID
            photo_metadata: Photo metadata dict
            media_service_url: URL to fetch photo from media service
            download_url: Direct download URL

        Returns:
            True if published successfully
        """
        try:
            await self._ensure_connected()

            message = {
                "event_type": "photo_added",
                "album_id": album_id,
                "file_id": file_id,
                "photo_metadata": {
                    "file_name": photo_metadata.get("file_name"),
                    "content_type": photo_metadata.get("content_type"),
                    "file_size": photo_metadata.get("file_size"),
                    "ai_labels": photo_metadata.get("ai_metadata", {}).get("labels", []),
                    "created_at": photo_metadata.get("created_at"),
                },
                "media_service_url": media_service_url
                or f"http://media-service:8222/api/v1/photos/{file_id}",
                "download_url": download_url,
                "timestamp": datetime.utcnow().isoformat(),
            }

            topic = f"albums/{album_id}/photo_added"
            success = await self.mqtt_bus.publish_json(topic, message, qos=1, retained=False)

            if success:
                logger.info(f"Published MQTT photo_added event to {topic}")
            else:
                logger.error(f"Failed to publish photo_added to {topic}")

            return success

        except Exception as e:
            logger.error(f"Failed to publish photo_added MQTT event: {e}")
            return False

    async def publish_photo_removed(
        self,
        album_id: str,
        file_id: str,
    ) -> bool:
        """
        Publish photo_removed event to MQTT

        Topic: albums/{album_id}/photo_removed
        QoS: 1 (at least once delivery)

        Args:
            album_id: Album ID
            file_id: Photo file ID

        Returns:
            True if published successfully
        """
        try:
            await self._ensure_connected()

            message = {
                "event_type": "photo_removed",
                "album_id": album_id,
                "file_id": file_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

            topic = f"albums/{album_id}/photo_removed"
            success = await self.mqtt_bus.publish_json(topic, message, qos=1, retained=False)

            if success:
                logger.info(f"Published MQTT photo_removed event to {topic}")

            return success

        except Exception as e:
            logger.error(f"Failed to publish photo_removed MQTT event: {e}")
            return False

    async def publish_album_sync(
        self,
        album_id: str,
        frame_id: str,
        photos: List[Dict[str, Any]],
    ) -> bool:
        """
        Publish full album sync to specific frame

        Topic: frames/{frame_id}/sync
        QoS: 2 (exactly once delivery)
        Retained: True (frame gets sync on reconnect)

        Args:
            album_id: Album ID
            frame_id: Frame/device ID
            photos: List of photo metadata dicts

        Returns:
            True if published successfully
        """
        try:
            await self._ensure_connected()

            message = {
                "event_type": "album_sync",
                "album_id": album_id,
                "frame_id": frame_id,
                "photos": photos,
                "total_photos": len(photos),
                "timestamp": datetime.utcnow().isoformat(),
            }

            topic = f"frames/{frame_id}/sync"
            success = await self.mqtt_bus.publish_json(topic, message, qos=2, retained=True)

            if success:
                logger.info(f"Published MQTT album_sync event to {topic} ({len(photos)} photos)")

            return success

        except Exception as e:
            logger.error(f"Failed to publish album_sync MQTT event: {e}")
            return False

    async def publish_frame_command(
        self,
        frame_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publish command to specific frame

        Topic: frames/{frame_id}/command
        QoS: 2 (exactly once delivery)

        Args:
            frame_id: Frame/device ID
            command: Command (refresh, restart, update_config, etc.)
            parameters: Optional command parameters

        Returns:
            True if published successfully
        """
        try:
            await self._ensure_connected()

            message = {
                "event_type": "frame_command",
                "frame_id": frame_id,
                "command": command,
                "parameters": parameters or {},
                "timestamp": datetime.utcnow().isoformat(),
            }

            topic = f"frames/{frame_id}/command"
            success = await self.mqtt_bus.publish_json(topic, message, qos=2, retained=False)

            if success:
                logger.info(f"Published MQTT frame_command '{command}' to {topic}")

            return success

        except Exception as e:
            logger.error(f"Failed to publish frame_command MQTT event: {e}")
            return False

    async def publish_album_config(
        self,
        album_id: str,
        config: Dict[str, Any],
    ) -> bool:
        """
        Publish album configuration update

        Topic: albums/{album_id}/config
        QoS: 1 (at least once)
        Retained: True (new subscribers get config)

        Args:
            album_id: Album ID
            config: Album configuration dict

        Returns:
            True if published successfully
        """
        try:
            await self._ensure_connected()

            message = {
                "event_type": "album_config",
                "album_id": album_id,
                "config": config,
                "timestamp": datetime.utcnow().isoformat(),
            }

            topic = f"albums/{album_id}/config"
            success = await self.mqtt_bus.publish_json(topic, message, qos=1, retained=True)

            if success:
                logger.info(f"Published MQTT album_config to {topic}")

            return success

        except Exception as e:
            logger.error(f"Failed to publish album_config MQTT event: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        await self.disconnect()


# Singleton instance and factory
_album_mqtt_publisher: Optional[AlbumMQTTPublisher] = None


async def get_album_mqtt_publisher(
    mqtt_host: str = "localhost",
    mqtt_port: int = 50053,
) -> AlbumMQTTPublisher:
    """
    Get or create global AlbumMQTTPublisher instance

    Args:
        mqtt_host: MQTT service host
        mqtt_port: MQTT service port

    Returns:
        AlbumMQTTPublisher: Connected publisher instance
    """
    global _album_mqtt_publisher

    if _album_mqtt_publisher is None:
        _album_mqtt_publisher = AlbumMQTTPublisher(mqtt_host=mqtt_host, mqtt_port=mqtt_port)
        await _album_mqtt_publisher.connect()
        logger.info("Created global AlbumMQTTPublisher instance")

    return _album_mqtt_publisher


async def close_album_mqtt_publisher():
    """Close and cleanup global AlbumMQTTPublisher instance"""
    global _album_mqtt_publisher

    if _album_mqtt_publisher is not None:
        await _album_mqtt_publisher.cleanup()
        _album_mqtt_publisher = None
        logger.info("Closed global AlbumMQTTPublisher instance")
