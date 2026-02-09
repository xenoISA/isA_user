"""
Storage Service - Clients Module

Centralized HTTP clients for inter-service communication
"""

from .organization_client import StorageOrganizationClient
from .account_client import AccountClient

__all__ = [
    "StorageOrganizationClient",
    "AccountClient",
]
