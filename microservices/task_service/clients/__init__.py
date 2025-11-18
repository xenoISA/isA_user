"""
Task Service Clients

HTTP clients for synchronous communication with other services.
Each client encapsulates the logic for calling external microservices.
"""

from .notification_client import NotificationClient

__all__ = [
    "NotificationClient",
]
