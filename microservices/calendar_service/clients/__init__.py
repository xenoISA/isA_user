"""
Calendar Service - Service Clients

Clients for inter-service communication
"""

from .google_calendar_client import GoogleCalendarClient
from .notification_client import NotificationClient
from .outlook_calendar_client import OutlookCalendarClient
from .account_client import AccountClient

__all__ = [
    "GoogleCalendarClient",
    "NotificationClient",
    "OutlookCalendarClient",
    "AccountClient",
]
