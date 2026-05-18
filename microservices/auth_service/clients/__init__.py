"""
Auth Service Clients Module

HTTP clients for synchronous communication with other services.
"""

from .organization_client import OrganizationServiceClient
from .project_client import ProjectAccessClient

__all__ = [
    "OrganizationServiceClient",
    "ProjectAccessClient",
]
