"""
Project Sharing Service Client (Story 9 — paired with xenoISA/isA_#429)

Thin internal client used by authorization_service to look up the role a
given user has on a given project. Used by the viewer-role write rejection
flow added in Story 9.

Design notes mirror project_service/clients/project_sharing_client.py
(shipped in #444):
- Short timeout — auth checks are hot-path.
- Service discovery first, fall back to env var
  (PROJECT_SHARING_SERVICE_URL), then to a localhost dev default.
- Uses internal service auth headers — same shape as the project_service
  variant.
- Never raises; returns ``None`` if the role can't be determined so the
  authorization layer can fail-closed on the caller's side.
"""

import logging
import os
from typing import Optional

import httpx

from core.auth_dependencies import INTERNAL_SERVICE_SECRET
from core.service_discovery import get_service_discovery

logger = logging.getLogger(__name__)


# Default port reserved for project_sharing_service (see config/ports.yaml).
_DEFAULT_BASE_URL = "http://localhost:8270"


class ProjectSharingClient:
    """Best-effort HTTP client for project_sharing_service role lookup."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 3.0,
    ) -> None:
        configured = base_url or os.getenv("PROJECT_SHARING_SERVICE_URL")
        if configured:
            self.base_url = configured.rstrip("/")
        else:
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("project_sharing_service")
            except Exception as exc:
                logger.debug(
                    "service discovery for project_sharing_service failed (%s); falling back to %s",
                    exc,
                    _DEFAULT_BASE_URL,
                )
                self.base_url = _DEFAULT_BASE_URL

        self._timeout = timeout
        self._internal_headers = {
            "X-Internal-Service": "true",
            "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
            "Content-Type": "application/json",
        }

    async def get_user_role_on_project(self, user_id: str, project_id: str) -> Optional[str]:
        """
        Resolve the role a user has on a project via the accepted shares list.

        Calls ``GET /api/v1/projects/{project_id}/shares?status=accepted`` and
        scans the response for a row whose ``invitee_user_id`` matches
        ``user_id``.

        Returns:
            One of ``"viewer" | "editor" | "owner"`` if the user has an
            accepted share on the project; ``None`` otherwise (including
            all transport/parse failures). Owners of the project itself
            do NOT appear in project_shares — callers handle ownership
            separately.
        """
        url = f"{self.base_url}/api/v1/projects/{project_id}/shares"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    params={"status": "accepted"},
                    headers=self._internal_headers,
                )
            if resp.status_code != 200:
                logger.debug(
                    "project_sharing_service returned %s for project %s",
                    resp.status_code,
                    project_id,
                )
                return None
            body = resp.json()
            shares = body.get("shares", []) if isinstance(body, dict) else []
            for share in shares:
                if share.get("invitee_user_id") == user_id:
                    role = share.get("role")
                    if isinstance(role, str):
                        return role
            return None
        except httpx.TimeoutException:
            logger.warning(
                "project_sharing_service timed out resolving role for user=%s project=%s",
                user_id,
                project_id,
            )
            return None
        except Exception as exc:  # noqa: BLE001 — best-effort by design
            logger.warning(
                "project_sharing_service unreachable for user=%s project=%s: %s",
                user_id,
                project_id,
                exc,
            )
            return None


__all__ = ["ProjectSharingClient"]
