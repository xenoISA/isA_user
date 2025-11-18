"""
Billing Service - Service Clients

Centralized client management for inter-service communication
"""

from .product_client import ProductClient
from .wallet_client import WalletClient

__all__ = [
    "WalletClient",
    "ProductClient",
]
