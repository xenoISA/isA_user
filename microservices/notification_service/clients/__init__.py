"""
Clients module for notification_service

Centralized HTTP clients for synchronous service-to-service communication
"""

from .account_client import AccountServiceClient
from .organization_client import OrganizationServiceClient
from .notification_client import NotificationServiceClient

__all__ = [
    "AccountServiceClient",
    "OrganizationServiceClient",
    "NotificationServiceClient",
]
