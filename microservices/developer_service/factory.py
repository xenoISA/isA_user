"""Factory helpers for developer_service."""

from .clients import (
    BillingOverviewClient,
    CredentialOverviewClient,
    ModelFirstCallClient,
    OrganizationOverviewClient,
    ProjectOverviewClient,
)
from .developer_service import DeveloperOverviewService


def create_developer_service() -> DeveloperOverviewService:
    return DeveloperOverviewService(
        organization_client=OrganizationOverviewClient(),
        project_client=ProjectOverviewClient(),
        credential_client=CredentialOverviewClient(),
        billing_client=BillingOverviewClient(),
        model_client=ModelFirstCallClient(),
    )
