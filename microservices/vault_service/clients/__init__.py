"""
Vault Service Clients

HTTP clients for synchronous communication with other services.
Each client encapsulates the logic for calling external microservices.
"""

from .notification_client import NotificationClient

# Note: account_client.py and organization_client.py are placeholders
# Import them here when they are implemented

__all__ = [
    "NotificationClient",
]
