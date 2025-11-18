"""
MQTT Publisher for Album Service

Publishes MQTT messages to notify smart frames about album updates
Uses isa_common.mqtt_client for MQTT operations
"""

import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from isa_common.mqtt_client import MQTTClient

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
        self.mqtt_client = None
        self.session_id = None
        self.connected = False

        logger.info(f"AlbumMQTTPublisher initialized (host: {mqtt_host}, port: {mqtt_port})")

    async def connect(self):
        """Connect to MQTT broker via adapter"""
        if self.connected:
            logger.debug("Already connected to MQTT broker")
            return

        try:
            # Initialize MQTT client
            self.mqtt_client = MQTTClient(
                host=self.mqtt_host,
                port=self.mqtt_port,
                user_id='album_service'
            )

            # Connect to broker
            with self.mqtt_client:
                conn = self.mqtt_client.connect('album-service-connection')
                self.session_id = conn['session_id']
                self.connected = True

            logger.info(f"Connected to MQTT broker (session: {self.session_id})")

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.connected = False

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if not self.connected or not self.mqtt_client:
            return

        try:
            with self.mqtt_client:
                if self.session_id:
                    self.mqtt_client.disconnect(self.session_id)

            self.connected = False
            self.session_id = None
            logger.info("Disconnected from MQTT broker")

        except Exception as e:
            logger.error(f"Failed to disconnect from MQTT broker: {e}")

    async def publish_photo_added(
        self,
        album_id: str,
        file_id: str,
        photo_metadata: Dict[str, Any],
        media_service_url: Optional[str] = None,
        download_url: Optional[str] = None
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
        if not self.connected:
            await self.connect()

        if not self.connected:
            logger.error("Not connected to MQTT broker, cannot publish")
            return False

        try:
            message = {
                'event_type': 'photo_added',
                'album_id': album_id,
                'file_id': file_id,
                'photo_metadata': {
                    'file_name': photo_metadata.get('file_name'),
                    'content_type': photo_metadata.get('content_type'),
                    'file_size': photo_metadata.get('file_size'),
                    'ai_labels': photo_metadata.get('ai_metadata', {}).get('labels', []),
                    'created_at': photo_metadata.get('created_at')
                },
                'media_service_url': media_service_url or f'http://media-service:8222/api/v1/photos/{file_id}',
                'download_url': download_url,
                'timestamp': datetime.utcnow().isoformat()
            }

            # Publish to album-specific topic
            topic = f'albums/{album_id}/photo_added'

            with self.mqtt_client:
                self.mqtt_client.publish_json(
                    self.session_id,
                    topic,
                    message,
                    qos=1,  # At least once delivery
                    retained=False
                )

            logger.info(f"Published MQTT photo_added event to {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish photo_added MQTT event: {e}")
            return False

    async def publish_photo_removed(
        self,
        album_id: str,
        file_id: str
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
        if not self.connected:
            await self.connect()

        if not self.connected:
            logger.error("Not connected to MQTT broker, cannot publish")
            return False

        try:
            message = {
                'event_type': 'photo_removed',
                'album_id': album_id,
                'file_id': file_id,
                'timestamp': datetime.utcnow().isoformat()
            }

            topic = f'albums/{album_id}/photo_removed'

            with self.mqtt_client:
                self.mqtt_client.publish_json(
                    self.session_id,
                    topic,
                    message,
                    qos=1,
                    retained=False
                )

            logger.info(f"Published MQTT photo_removed event to {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish photo_removed MQTT event: {e}")
            return False

    async def publish_album_sync(
        self,
        album_id: str,
        frame_id: str,
        photos: List[Dict[str, Any]]
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
        if not self.connected:
            await self.connect()

        if not self.connected:
            logger.error("Not connected to MQTT broker, cannot publish")
            return False

        try:
            message = {
                'event_type': 'album_sync',
                'album_id': album_id,
                'frame_id': frame_id,
                'photos': photos,
                'total_photos': len(photos),
                'timestamp': datetime.utcnow().isoformat()
            }

            topic = f'frames/{frame_id}/sync'

            with self.mqtt_client:
                self.mqtt_client.publish_json(
                    self.session_id,
                    topic,
                    message,
                    qos=2,  # Exactly once
                    retained=True  # Frame gets last sync on reconnect
                )

            logger.info(f"Published MQTT album_sync event to {topic} ({len(photos)} photos)")
            return True

        except Exception as e:
            logger.error(f"Failed to publish album_sync MQTT event: {e}")
            return False

    async def publish_frame_command(
        self,
        frame_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None
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
        if not self.connected:
            await self.connect()

        if not self.connected:
            logger.error("Not connected to MQTT broker, cannot publish")
            return False

        try:
            message = {
                'event_type': 'frame_command',
                'frame_id': frame_id,
                'command': command,
                'parameters': parameters or {},
                'timestamp': datetime.utcnow().isoformat()
            }

            topic = f'frames/{frame_id}/command'

            with self.mqtt_client:
                self.mqtt_client.publish_json(
                    self.session_id,
                    topic,
                    message,
                    qos=2,  # Exactly once
                    retained=False
                )

            logger.info(f"Published MQTT frame_command '{command}' to {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish frame_command MQTT event: {e}")
            return False

    async def publish_album_config(
        self,
        album_id: str,
        config: Dict[str, Any]
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
        if not self.connected:
            await self.connect()

        if not self.connected:
            logger.error("Not connected to MQTT broker, cannot publish")
            return False

        try:
            message = {
                'event_type': 'album_config',
                'album_id': album_id,
                'config': config,
                'timestamp': datetime.utcnow().isoformat()
            }

            topic = f'albums/{album_id}/config'

            with self.mqtt_client:
                self.mqtt_client.publish_json(
                    self.session_id,
                    topic,
                    message,
                    qos=1,
                    retained=True  # Retained for new subscribers
                )

            logger.info(f"Published MQTT album_config to {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish album_config MQTT event: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        await self.disconnect()
