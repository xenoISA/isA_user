"""
Credit Service Client Module

Provides HTTP clients for synchronous communication with other microservices.
"""

from .account_client import AccountClient
from .subscription_client import SubscriptionClient

__all__ = [
    "AccountClient",
    "SubscriptionClient",
]
