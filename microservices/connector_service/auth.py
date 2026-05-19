"""
Auth helpers for connector_service.

Mirrors the get_user_id pattern from vault_service.main: prefer the
internal-service signal, then bearer JWT, then API key. Falls back to a
header-supplied ``X-User-Id`` when running in dev mode so the golden
tests have a single point of injection.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import Request

logger = logging.getLogger(__name__)


async def resolve_user_id(request: Request) -> Optional[str]:
    """Return the authenticated user id, or None if it can't be resolved.

    Order:
      1. Trusted internal-service envelope (X-Internal-Service + secret).
      2. Bearer JWT via core.auth_dependencies.
      3. API key via core.auth_dependencies.
      4. Fallback to ``X-User-Id`` header when CONNECTOR_DEV_AUTH=true.

    Returning None lets the route decide between 401 and a soft "no
    user, list-public-data-only" response. For this slice every mutating
    route requires a user, so they 401 on None.
    """
    try:
        from core.auth_dependencies import (
            INTERNAL_SERVICE_SECRET,
            _extract_user_id_from_api_key,
            _extract_user_id_from_bearer,
        )
    except Exception as e:
        logger.warning(
            "auth_dependencies import failed; falling back to header auth: %s", e
        )
        INTERNAL_SERVICE_SECRET = None
        _extract_user_id_from_bearer = None
        _extract_user_id_from_api_key = None

    # 1) Internal service
    if INTERNAL_SERVICE_SECRET is not None:
        x_internal_service = request.headers.get("X-Internal-Service")
        x_internal_secret = request.headers.get("X-Internal-Service-Secret")
        if (
            x_internal_service == "true"
            and x_internal_secret == INTERNAL_SERVICE_SECRET
        ):
            return "internal-service"

    # 2) Bearer JWT
    authorization = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if authorization and _extract_user_id_from_bearer is not None:
        try:
            user_id = await _extract_user_id_from_bearer(authorization)
            if user_id:
                return user_id
        except Exception as e:
            logger.debug("bearer decode failed: %s", e)

    # 3) API key
    x_api_key = request.headers.get("X-API-Key")
    if x_api_key and _extract_user_id_from_api_key is not None:
        try:
            user_id = await _extract_user_id_from_api_key(x_api_key)
            if user_id:
                return user_id
        except Exception as e:
            logger.debug("api key decode failed: %s", e)

    # 4) Dev fallback
    if os.getenv("CONNECTOR_DEV_AUTH", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return request.headers.get("X-User-Id")

    return None
