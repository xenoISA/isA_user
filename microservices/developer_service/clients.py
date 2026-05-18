"""HTTP clients used by developer_service aggregation."""

from typing import Any, Dict, Optional

import httpx

from core.internal_service_auth import InternalServiceAuth
from core.service_discovery import get_service_discovery


def _resolve_service_url(service_name: str, default_port: int) -> str:
    try:
        service_discovery = get_service_discovery()
        return service_discovery.get_service_url(service_name).rstrip("/")
    except Exception:
        return f"http://localhost:{default_port}"


class DeveloperHttpClient:
    def __init__(
        self,
        *,
        service_name: str,
        default_port: int,
        timeout: float = 2.0,
    ):
        self.service_name = service_name
        self.base_url = _resolve_service_url(service_name, default_port)
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.client.aclose()

    async def health(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code < 500
        except Exception:
            return False

    def _internal_headers(self) -> Dict[str, str]:
        return InternalServiceAuth.get_internal_service_headers()

    def _auth_headers(self, auth_token: Optional[str]) -> Dict[str, str]:
        if not auth_token:
            return {}
        return {"Authorization": auth_token}


class OrganizationOverviewClient(DeveloperHttpClient):
    def __init__(self, timeout: float = 2.0):
        super().__init__(
            service_name="organization_service",
            default_port=8212,
            timeout=timeout,
        )

    async def get_organization_context(
        self, *, user_id: str, organization_id: str
    ) -> Optional[Dict[str, Any]]:
        headers = self._internal_headers()
        organization_response = await self.client.get(
            f"{self.base_url}/api/v1/organization/organizations/{organization_id}",
            headers=headers,
        )
        if organization_response.status_code == 404:
            return None
        organization_response.raise_for_status()

        members_response = await self.client.get(
            f"{self.base_url}/api/v1/organization/organizations/{organization_id}/members",
            params={"limit": 1000, "offset": 0},
            headers=headers,
        )
        members_response.raise_for_status()
        members = members_response.json().get("members", [])
        member = next(
            (
                item
                for item in members
                if (item.get("user_id") or item.get("member_user_id")) == user_id
            ),
            {},
        )
        return {"organization": organization_response.json(), "member": member}


class ProjectOverviewClient(DeveloperHttpClient):
    def __init__(self, timeout: float = 2.0):
        super().__init__(
            service_name="project_service",
            default_port=8260,
            timeout=timeout,
        )

    async def list_projects(
        self,
        *,
        auth_token: Optional[str],
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
        **_: Any,
    ) -> Dict[str, Any]:
        response = await self.client.get(
            f"{self.base_url}/api/v1/projects",
            params={
                "organization_id": organization_id,
                "limit": limit,
                "offset": offset,
            },
            headers=self._auth_headers(auth_token),
        )
        response.raise_for_status()
        return response.json()


class CredentialOverviewClient(DeveloperHttpClient):
    def __init__(self, timeout: float = 2.0):
        super().__init__(
            service_name="auth_service",
            default_port=8201,
            timeout=timeout,
        )

    async def list_api_keys(
        self,
        *,
        auth_token: Optional[str],
        organization_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {}
        if project_id:
            params["project_id"] = project_id
        response = await self.client.get(
            f"{self.base_url}/api/v1/auth/api-keys/{organization_id}",
            params=params,
            headers=self._auth_headers(auth_token),
        )
        response.raise_for_status()
        return response.json()


class BillingOverviewClient(DeveloperHttpClient):
    def __init__(self, timeout: float = 2.0):
        super().__init__(
            service_name="billing_service",
            default_port=8220,
            timeout=timeout,
        )

    async def get_usage_overview(
        self,
        *,
        user_id: str,
        organization_id: str,
        period_days: int,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "user_id": user_id,
            "organization_id": organization_id,
            "period_days": period_days,
        }
        if project_id:
            params["project_id"] = project_id
        response = await self.client.get(
            f"{self.base_url}/api/v1/billing/usage/overview",
            params=params,
        )
        response.raise_for_status()
        return response.json()
