"""
Product Service Clients Module

HTTP clients for synchronous communication with other services
"""

from .account_client import AccountClient
from .organization_client import OrganizationClient

# Import ProductServiceClient from parent directory
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from client import ProductServiceClient

__all__ = [
    "AccountClient",
    "OrganizationClient",
    "ProductServiceClient"
]
