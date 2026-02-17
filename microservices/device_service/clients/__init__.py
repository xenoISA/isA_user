"""
Device Service Clients Module

HTTP clients for async communication with other services.
Following wallet_service pattern.
"""

from .auth_client import AuthServiceClient, get_auth_client, close_auth_client
from .account_client import AccountClient

__all__ = [
    'AuthServiceClient',
    'get_auth_client',
    'close_auth_client',
    'AccountClient',
]
