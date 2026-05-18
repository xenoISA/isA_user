"""HTTP clients used by developer_service aggregation."""

import os
from typing import Any, Dict, Optional

import httpx

from core.internal_service_auth import InternalServiceAuth
from core.service_discovery import get_service_discovery


def _resolve_service_url(service_name: str, default_port: int) -> str:
    if service_name == "model_service":
        env_url = os.getenv("ISA_MODEL_URL") or os.getenv("MODEL_SERVICE_URL")
        if env_url:
            return env_url.rstrip("/")
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

    async def verify_api_key(
        self,
        *,
        api_key: str,
        project_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"api_key": api_key}
        if project_id:
            payload["project_id"] = project_id
        if ip_address:
            payload["ip_address"] = ip_address
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/verify-api-key",
            json=payload,
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


class ModelFirstCallClient(DeveloperHttpClient):
    def __init__(self, timeout: float = 15.0):
        super().__init__(
            service_name="model_service",
            default_port=8082,
            timeout=timeout,
        )

    async def run_first_call(
        self,
        *,
        user_id: str,
        organization_id: str,
        project_id: str,
        model: str,
        prompt: str,
        api_key: Optional[str] = None,
        api_key_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        headers = self._auth_headers(auth_token)
        if api_key:
            headers["X-API-Key"] = api_key
            if not auth_token:
                headers["Authorization"] = f"Bearer {api_key}"

        request_metadata = {
            "user_id": user_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "api_key_id": api_key_id,
            "source": "developer_service_first_call",
            **(metadata or {}),
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "metadata": request_metadata,
            "max_tokens": 64,
            "temperature": 0,
        }
        last_response: Optional[httpx.Response] = None
        for path in (
            "/v1/chat/completions",
            "/api/v1/chat/completions",
            "/chat/completions",
        ):
            response = await self.client.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=headers,
            )
            if response.status_code == 404:
                last_response = response
                continue
            response.raise_for_status()
            return response.json()
        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("Model service did not return a first-call response")
