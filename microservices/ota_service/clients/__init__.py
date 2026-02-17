"""
OTA Service Clients

HTTP clients for synchronous communication with other services
"""

from .device_client import DeviceClient
from .storage_client import StorageClient
from .notification_client import NotificationClient

__all__ = [
    'DeviceClient',
    'StorageClient',
    'NotificationClient',
]
