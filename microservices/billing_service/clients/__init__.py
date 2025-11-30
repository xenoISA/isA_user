"""
Billing Service - Service Clients

Centralized client management for inter-service communication
"""

from .product_client import ProductClient
from .wallet_client import WalletClient
from .subscription_client import SubscriptionClient

__all__ = [
    "WalletClient",
    "ProductClient",
    "SubscriptionClient",
]
