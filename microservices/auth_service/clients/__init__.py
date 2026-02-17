"""
Auth Service Clients Module

HTTP clients for synchronous communication with other services.
"""

from .organization_client import OrganizationServiceClient

__all__ = [
    "OrganizationServiceClient",
]
