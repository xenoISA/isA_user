"""
Authorization Service Clients Module

HTTP clients for async communication with other microservices.
Used for user and organization validation in permission checks.
"""

from .account_client import AccountClient
from .organization_client import OrganizationClient
from .project_sharing_client import ProjectSharingClient

__all__ = ["AccountClient", "OrganizationClient", "ProjectSharingClient"]
