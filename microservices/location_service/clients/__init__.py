"""
Location Service Clients

HTTP clients for async communication with other services.
Each client encapsulates the logic for calling external microservices.
"""

from .device_client import DeviceClient
from .notification_client import NotificationClient
from .account_client import AccountClient

__all__ = [
    "DeviceClient",
    "NotificationClient",
    "AccountClient",
]
