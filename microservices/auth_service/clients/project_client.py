"""Project access checks for project-scoped API key creation."""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class ProjectAccessClient:
    """Validate that a caller can bind an API key to a project."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        self.base_url = (
            base_url
            or os.getenv("PROJECT_SERVICE_URL")
            or (
                f"http://{os.getenv('PROJECT_SERVICE_HOST', '127.0.0.1')}:"
                f"{os.getenv('PROJECT_SERVICE_PORT', '8260')}"
            )
        ).rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

    async def validate_project_access(
        self,
        *,
        organization_id: str,
        project_id: str,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> bool:
        if not project_id:
            return True

        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token
        else:
            internal_secret = os.getenv("INTERNAL_SERVICE_SECRET")
            if internal_secret:
                headers["X-Internal-Service"] = "true"
                headers["X-Internal-Service-Secret"] = internal_secret

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}",
                headers=headers,
            )
            if response.status_code in {401, 403, 404}:
                return False
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "Project access validation failed for user=%s org=%s project=%s: %s",
                user_id,
                organization_id,
                project_id,
                exc,
            )
            return False

        project_org_id = payload.get("organization_id") or payload.get("org_id")
        if project_org_id and project_org_id != organization_id:
            return False

        return True

    async def close(self):
        await self.client.aclose()
