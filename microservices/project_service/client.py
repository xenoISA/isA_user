"""
Project Service Client (#300)

Client library for other microservices to interact with project_service.

Usage:
    async with ProjectServiceClient() as client:
        project = await client.create_project(
            user_id="user123", name="My Project",
            auth_token="Bearer ..."
        )
        projects = await client.list_projects(user_id="user123", auth_token="Bearer ...")
"""

from io import BytesIO

import httpx
import logging
from typing import Optional, List, Dict, Any

from core.auth_dependencies import INTERNAL_SERVICE_SECRET
from core.service_discovery import get_service_discovery

logger = logging.getLogger(__name__)


class ProjectServiceClient:
    """Project Service HTTP client"""

    def __init__(self, base_url: str = None, timeout: float = 30.0, retries: int = 0):
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("project_service")
            except Exception as e:
                logger.warning("Service discovery failed, using default: %s", e)
                self.base_url = "http://localhost:8260"

        transport = httpx.AsyncHTTPTransport(retries=retries) if retries else None
        self.client = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _headers(self, auth_token: str) -> Dict[str, str]:
        return {"Authorization": auth_token}

    def _internal_headers(self) -> Dict[str, str]:
        return {
            "X-Internal-Service": "true",
            "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
        }

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def create_project(
        self,
        auth_token: str,
        name: str,
        description: str = None,
        custom_instructions: str = None,
        organization_id: str = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            payload: Dict[str, Any] = {"name": name}
            if description is not None:
                payload["description"] = description
            if custom_instructions is not None:
                payload["custom_instructions"] = custom_instructions
            if organization_id is not None:
                payload["organization_id"] = organization_id
            resp = await self.client.post(
                f"{self.base_url}/api/v1/projects",
                json=payload,
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("create_project failed: %s", e.response.status_code)
            return None
        except Exception as e:
            logger.error("create_project error: %s", e)
            return None

    async def get_project(
        self,
        auth_token: str,
        project_id: str,
        organization_id: str = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            params = {}
            if organization_id:
                params["organization_id"] = organization_id
            resp = await self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}",
                params=params,
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("get_project failed: %s", e.response.status_code)
            return None
        except Exception as e:
            logger.error("get_project error: %s", e)
            return None

    async def list_projects(
        self,
        auth_token: str,
        limit: int = 50,
        offset: int = 0,
        organization_id: str = None,
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            params = {"limit": limit, "offset": offset}
            if organization_id:
                params["organization_id"] = organization_id
            resp = await self.client.get(
                f"{self.base_url}/api/v1/projects",
                params=params,
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("list_projects failed: %s", e.response.status_code)
            return None
        except Exception as e:
            logger.error("list_projects error: %s", e)
            return None

    async def export_user_data(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Export project-owned user data for GDPR subject access workflows."""
        try:
            params = {"user_id": user_id}
            if organization_id is not None:
                params["organization_id"] = organization_id
            if request_id is not None:
                params["request_id"] = request_id

            resp = await self.client.get(
                f"{self.base_url}/api/v1/projects/export",
                params=params,
                headers=self._internal_headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("export_user_data failed: %s", e.response.status_code)
            return None
        except Exception as e:
            logger.error("export_user_data error: %s", e)
            return None

    async def update_project(
        self,
        auth_token: str,
        project_id: str,
        organization_id: str = None,
        **updates,
    ) -> Optional[Dict[str, Any]]:
        try:
            params = {}
            if organization_id:
                params["organization_id"] = organization_id
            resp = await self.client.put(
                f"{self.base_url}/api/v1/projects/{project_id}",
                params=params,
                json=updates,
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("update_project failed: %s", e.response.status_code)
            return None
        except Exception as e:
            logger.error("update_project error: %s", e)
            return None

    async def delete_project(
        self, auth_token: str, project_id: str, organization_id: str = None
    ) -> bool:
        try:
            params = {}
            if organization_id:
                params["organization_id"] = organization_id
            resp = await self.client.delete(
                f"{self.base_url}/api/v1/projects/{project_id}",
                params=params,
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error("delete_project failed: %s", e.response.status_code)
            return False
        except Exception as e:
            logger.error("delete_project error: %s", e)
            return False

    async def set_instructions(
        self,
        auth_token: str,
        project_id: str,
        instructions: str,
    ) -> bool:
        try:
            resp = await self.client.put(
                f"{self.base_url}/api/v1/projects/{project_id}/instructions",
                json={"instructions": instructions},
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error("set_instructions failed: %s", e.response.status_code)
            return False
        except Exception as e:
            logger.error("set_instructions error: %s", e)
            return False

    async def list_project_files(
        self,
        auth_token: str,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        try:
            resp = await self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}/files",
                params={"limit": limit, "offset": offset},
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("list_project_files failed: %s", e.response.status_code)
            return None
        except Exception as e:
            logger.error("list_project_files error: %s", e)
            return None

    async def upload_project_file(
        self,
        auth_token: str,
        project_id: str,
        filename: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Optional[Dict[str, Any]]:
        try:
            resp = await self.client.post(
                f"{self.base_url}/api/v1/projects/{project_id}/files",
                files={"file": (filename, BytesIO(file_content), content_type)},
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("upload_project_file failed: %s", e.response.status_code)
            return None
        except Exception as e:
            logger.error("upload_project_file error: %s", e)
            return None

    async def delete_project_file(
        self,
        auth_token: str,
        project_id: str,
        file_id: str,
    ) -> bool:
        try:
            resp = await self.client.delete(
                f"{self.base_url}/api/v1/projects/{project_id}/files/{file_id}",
                headers=self._headers(auth_token),
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error("delete_project_file failed: %s", e.response.status_code)
            return False
        except Exception as e:
            logger.error("delete_project_file error: %s", e)
            return False

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(f"{self.base_url}/health")
            return resp.status_code == 200
        except Exception:
            return False


__all__ = ["ProjectServiceClient"]
