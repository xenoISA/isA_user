"""Developer Journey overview aggregation service."""

from typing import Any, Dict, Optional

from .models import (
    DeveloperHealthResponse,
    DeveloperOverviewResponse,
    build_empty_overview,
    dependency_warning,
)


class DeveloperOverviewService:
    """Thin aggregation boundary for Developer cockpit read models."""

    def __init__(
        self,
        *,
        organization_client: Optional[Any] = None,
        project_client: Optional[Any] = None,
        credential_client: Optional[Any] = None,
        billing_client: Optional[Any] = None,
        trace_client: Optional[Any] = None,
        evaluation_client: Optional[Any] = None,
    ):
        self.organization_client = organization_client
        self.project_client = project_client
        self.credential_client = credential_client
        self.billing_client = billing_client
        self.trace_client = trace_client
        self.evaluation_client = evaluation_client

    async def get_overview(
        self,
        *,
        user_id: str,
        organization_id: str,
        project_id: Optional[str] = None,
        period_days: int = 7,
    ) -> DeveloperOverviewResponse:
        dependency_health = await self.get_dependency_health()
        warnings = [
            dependency_warning(source, status)
            for source, status in dependency_health.items()
            if status != "healthy"
        ]
        return build_empty_overview(
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            period_days=period_days,
            warnings=warnings,
        )

    async def get_dependency_health(self) -> Dict[str, str]:
        clients = {
            "organization_service": self.organization_client,
            "project_service": self.project_client,
            "auth_service": self.credential_client,
            "billing_service": self.billing_client,
            "trace_service": self.trace_client,
            "evaluation_service": self.evaluation_client,
        }
        return {
            source: await self._client_health(client)
            for source, client in clients.items()
        }

    async def health_response(self, *, version: str) -> DeveloperHealthResponse:
        dependencies = await self.get_dependency_health()
        status = (
            "healthy"
            if all(value == "healthy" for value in dependencies.values())
            else "degraded"
        )
        from datetime import datetime, timezone

        return DeveloperHealthResponse(
            status=status,
            service="developer_service",
            version=version,
            dependencies=dependencies,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _client_health(self, client: Optional[Any]) -> str:
        if client is None:
            return "not_configured"

        health = getattr(client, "health", None)
        if health is None:
            return "healthy"

        try:
            result = health()
            if hasattr(result, "__await__"):
                result = await result
            return "healthy" if result else "unhealthy"
        except Exception:
            return "unhealthy"
