"""
Calendar Service - Service Clients

Clients for inter-service communication
"""

from .google_calendar_client import GoogleCalendarClient
from .notification_client import NotificationClient
from .outlook_calendar_client import OutlookCalendarClient

__all__ = [
    "GoogleCalendarClient",
    "NotificationClient",
    "OutlookCalendarClient",
]
