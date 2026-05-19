"""
Installed connectors route — GET /api/v1/connectors/installed.

Merges two data sources into one response:

  1. ``connector.connector`` — built-in catalog install state per user.
     Initially empty for every user; only populated once a user clicks
     "Connect" (OAuth handoff is out of scope for this PR — see
     ``docs/design/connector_marketplace_service.md`` §"Install Or
     Connect").
  2. ``connector.custom_mcp_connector`` — user-added remote MCP rows.

The frontend renders these in two distinct sections of the "My
connectors" view, so we return them as two arrays plus a combined
``count`` for convenience.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, status

from .auth import resolve_user_id
from .models import InstalledConnectorsResponse

if TYPE_CHECKING:
    from .connector_repository import ConnectorRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/connectors", tags=["connector-installed"])


def build_router(get_repo) -> APIRouter:
    """Bind the router to a repository factory.

    Pattern matches main.py's ``get_repo`` dependency closure — same
    shape used in project_sharing_service.
    """

    @router.get("/installed", response_model=InstalledConnectorsResponse)
    async def list_installed(request: Request) -> InstalledConnectorsResponse:
        user_id = await resolve_user_id(request)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "unauthenticated",
                        "message": "Missing or invalid auth",
                    }
                },
            )

        repo: "ConnectorRepository" = get_repo()

        installed = await repo.list_installed_for_user(user_id)
        custom = await repo.list_custom_for_user(user_id)

        return InstalledConnectorsResponse(
            installed=installed,
            custom=custom,
            count=len(installed) + len(custom),
        )

    return router
