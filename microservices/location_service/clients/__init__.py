"""
Location Service Clients

HTTP clients for synchronous communication with other services.
Each client encapsulates the logic for calling external microservices.
"""

from .device_client import DeviceClient
from .notification_client import NotificationClient

__all__ = [
    "DeviceClient",
    "NotificationClient",
]
