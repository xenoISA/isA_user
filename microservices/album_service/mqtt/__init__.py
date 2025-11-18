"""
MQTT module for album_service

MQTT messaging for smart frame communication
"""

from .publisher import AlbumMQTTPublisher

__all__ = [
    "AlbumMQTTPublisher",
]
