"""
Campaign Service Clients

Clients for calling other microservices.
"""

from .account_client import AccountClient
from .task_client import TaskClient
from .notification_client import NotificationClient

__all__ = [
    "AccountClient",
    "TaskClient",
    "NotificationClient",
]
