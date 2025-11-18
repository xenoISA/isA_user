"""
Wallet Service Clients

HTTP clients for synchronous communication with other services.
Each client encapsulates the logic for calling external microservices.
"""

from .account_client import AccountClient

__all__ = [
    "AccountClient",
]
