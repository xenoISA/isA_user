"""
Order Service Clients Module

HTTP clients for synchronous communication with other services
"""

from .payment_client import PaymentClient
from .wallet_client import WalletClient
from .account_client import AccountClient
from .storage_client import StorageClient
from .billing_client import BillingClient
from .order_client import OrderServiceClient

__all__ = [
    "PaymentClient",
    "WalletClient",
    "AccountClient",
    "StorageClient",
    "BillingClient",
    "OrderServiceClient"
]
