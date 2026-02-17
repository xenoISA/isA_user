"""
Task Service Clients

HTTP clients for async communication with other services.
Each client encapsulates the logic for calling external microservices.
"""

from .notification_client import NotificationClient
from .account_client import AccountClient
from .calendar_client import CalendarClient

__all__ = [
    "NotificationClient",
    "AccountClient",
    "CalendarClient",
]
