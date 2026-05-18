"""
Project Sharing Service Client (Story #442, paired with xenoISA/isA_#429)

Thin internal client used by project_service to fan out events (e.g. revoke
all shares when a project is archived) to project_sharing_service.

Design notes:
- Short timeout — share revocation is best-effort during archive. If the
  sharing service is down we still let the archive succeed and rely on a
  reconcile job to clean up later.
- Service discovery first, fall back to env var (PROJECT_SHARING_SERVICE_URL)
  then to a sensible localhost default for dev.
- Uses the internal service auth headers — same pattern as
  StorageServiceClient (microservices/storage_service/client.py).
"""

import logging
import os
from typing import Optional

import httpx

from core.auth_dependencies import INTERNAL_SERVICE_SECRET
from core.service_discovery import get_service_discovery

logger = logging.getLogger(__name__)


# Default port the sister agent has reserved for project_sharing_service.
# Override via PROJECT_SHARING_SERVICE_URL in dev.env once finalized.
_DEFAULT_BASE_URL = "http://localhost:8262"


class ProjectSharingClient:
    """Best-effort HTTP client for project_sharing_service."""

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

    async def revoke_all_shares(self, project_id: str) -> bool:
        """
        Fire-and-forget POST /api/v1/projects/:id/shares/revoke-all.

        Returns True on 2xx, False on any failure. Never raises — archive
        callers should always treat the local archived_at flag as the source
        of truth and log/warn rather than abort if this fails.
        """
        url = f"{self.base_url}/api/v1/projects/{project_id}/shares/revoke-all"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, headers=self._internal_headers)
            if 200 <= resp.status_code < 300:
                logger.info(
                    "project_sharing_service revoked shares for project %s",
                    project_id,
                )
                return True
            logger.warning(
                "project_sharing_service revoke_all_shares returned %s for project %s",
                resp.status_code,
                project_id,
            )
            return False
        except httpx.TimeoutException:
            logger.warning(
                "project_sharing_service timed out revoking shares for project %s; "
                "archive succeeded — background reconcile will catch up",
                project_id,
            )
            return False
        except Exception as exc:  # noqa: BLE001 — best-effort by design
            logger.warning(
                "project_sharing_service unreachable for project %s: %s; "
                "archive succeeded — background reconcile will catch up",
                project_id,
                exc,
            )
            return False


__all__ = ["ProjectSharingClient"]
