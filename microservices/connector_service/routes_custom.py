"""
Custom remote MCP connector routes.

  POST   /api/v1/connectors/custom              -> create + validate + persist
  DELETE /api/v1/connectors/custom/{id}         -> revoke + delete
  POST   /api/v1/connectors/custom/{id}/revalidate -> re-run handshake

Behavior:
  * All three routes return 404 (route_disabled) when
    ALLOW_CUSTOM_MCP_CONNECTORS=false. The catalog + installed routes
    remain available — we only gate the BYO MCP slice.
  * POST is rate limited at 10 requests / hour per caller (JWT key,
    IP fallback) via core.rate_limiter.SlidingWindowCounter. 429 with
    Retry-After on overflow.
  * On handshake failure we DO NOT persist the row. A 422 is returned
    with a stable ``error.code`` so the UI can switch on it.
  * Vault interaction goes through dev_vault for now — see dev_vault.py
    for the migration note.
  * Every successful mutation emits a ``connector_service.connector.*``
    NATS audit event.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, HTTPException, Request, status

from core.nats_client import Event
from core.rate_limiter import (
    InMemoryBackend,
    RateLimitConfig,
    SlidingWindowCounter,
)

from . import dev_vault
from .auth import resolve_user_id
from .feature_flags import custom_mcp_enabled
from .handshake import HandshakeResult, validate_mcp_url
from .models import (
    ConnectorErrorBody,
    CreateCustomMcpRequest,
    CustomMcpAuthKind,
    CustomMcpConnector,
    CustomMcpStatus,
)

if TYPE_CHECKING:
    from .connector_repository import ConnectorRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/connectors", tags=["connector-custom"])


# ----------------------------------------------------------------------------
# Rate limiter — 10 req / hour per caller on POST /custom.
#
# Different cadence from the per-minute caps in project_sharing_service /
# artifact_service: registering a remote MCP server is a much rarer
# action than inviting collaborators, and the handshake itself takes
# up to 10s. 10/hour is enough headroom for a user iterating on the URL
# while keeping a runaway script bounded.
# ----------------------------------------------------------------------------
_CUSTOM_POST_RATE = RateLimitConfig(requests=10, window_seconds=3600)
_custom_post_counter = SlidingWindowCounter(InMemoryBackend())


def _rate_limit_key(request: Request) -> str:
    """Stable per-caller key — prefer JWT (hash prefix), fall back to IP."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth:
        return "jwt:" + hashlib.sha1(auth.strip().encode("utf-8")).hexdigest()[:12]
    if request.client and request.client.host:
        return "ip:" + request.client.host
    return "anon"


async def _enforce_post_rate_limit(request: Request) -> None:
    key = f"custom_mcp:{_rate_limit_key(request)}"
    allowed, info = await _custom_post_counter.check(key, _CUSTOM_POST_RATE)
    if not allowed:
        retry_after = info.get("retry_after") or _CUSTOM_POST_RATE.window_seconds
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Custom MCP create is limited to 10 requests / hour per caller",
                },
                "limit_type": "per_hour",
            },
            headers={"Retry-After": str(retry_after)},
        )


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _feature_disabled_404() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": {
                "code": "route_disabled",
                "message": "Custom MCP connectors are not enabled in this environment",
            }
        },
    )


def _unauth_401() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {"code": "unauthenticated", "message": "Missing or invalid auth"}
        },
    )


def _not_found_404() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": {
                "code": "connector_not_found",
                "message": "Custom MCP connector not found",
            }
        },
    )


def _handshake_422(result: HandshakeResult) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": ConnectorErrorBody(
                code=result.error_code or "handshake_failed",
                message=result.error_message or "MCP handshake failed",
            ).model_dump()
        },
    )


async def _publish_audit(event_bus, event_type: str, data: dict) -> None:
    """Best-effort NATS audit publish — never fail a request because NATS is down."""
    if not event_bus:
        return
    try:
        event = Event(
            event_type=event_type,
            source="connector_service",
            data=data,
        )
        await event_bus.publish_event(event)
    except Exception as e:
        logger.error("Failed to publish %s: %s", event_type, e)


def _validate_auth_payload(req: CreateCustomMcpRequest) -> Optional[HTTPException]:
    """Return a 422 if auth_kind requires a secret and none was provided."""
    needs_secret = req.auth_kind in (CustomMcpAuthKind.PAT, CustomMcpAuthKind.OAUTH_OOB)
    if needs_secret and not req.auth_secret:
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "missing_auth_secret",
                    "message": f"auth_kind={req.auth_kind.value} requires an auth_secret",
                }
            },
        )
    return None


# ----------------------------------------------------------------------------
# Route builder
# ----------------------------------------------------------------------------


def build_router(get_repo, get_event_bus) -> APIRouter:
    """Bind the routes to repository + event_bus closures."""

    @router.post(
        "/custom",
        response_model=CustomMcpConnector,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_custom_mcp(
        request: Request,
        body: CreateCustomMcpRequest,
    ) -> CustomMcpConnector:
        if not custom_mcp_enabled():
            raise _feature_disabled_404()

        await _enforce_post_rate_limit(request)

        user_id = await resolve_user_id(request)
        if not user_id:
            raise _unauth_401()

        repo: "ConnectorRepository" = get_repo()

        # Idempotency: same (user, url) -> return the existing row rather
        # than 409. Cheaper for the UI and matches project_sharing's
        # pending-invite re-invite shape.
        url_str = str(body.url)
        existing = await repo.get_custom_by_user_and_url(user_id, url_str)
        if existing is not None and existing.status != CustomMcpStatus.REVOKED:
            return existing

        # Run the MCP handshake BEFORE persisting. If it fails the row
        # never lands — the user has to fix the URL/secret and retry.
        handshake = await validate_mcp_url(
            url=url_str,
            auth_kind=body.auth_kind.value,
            auth_secret=body.auth_secret,
        )
        if not handshake.ok:
            raise _handshake_422(handshake)

        # Auth secret -> vault. Only writes when there's actually a
        # secret; ``auth_kind=none`` leaves the ref column NULL.
        secret_ref: Optional[str] = None
        if body.auth_secret and body.auth_kind != CustomMcpAuthKind.NONE:
            secret_ref = dev_vault.store_secret(user_id, body.label, body.auth_secret)

        try:
            persisted = await repo.insert_custom(
                user_id=user_id,
                label=body.label,
                url=url_str,
                auth_kind=body.auth_kind.value,
                auth_secret_ref=secret_ref,
                status=CustomMcpStatus.ACTIVE.value,
                tools_count=handshake.tools_count,
                last_error=None,
            )
        except Exception as e:
            # Roll back the dev-vault write so we don't leak orphaned
            # secrets when the insert fails.
            if secret_ref:
                dev_vault.revoke_secret(secret_ref)
            logger.error(
                "Persist failed after successful handshake: %s", e, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": {
                        "code": "internal_error",
                        "message": "Failed to persist connector",
                    }
                },
            )

        if persisted is None:
            # Same rollback path as above.
            if secret_ref:
                dev_vault.revoke_secret(secret_ref)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": {
                        "code": "internal_error",
                        "message": "Persist returned no row",
                    }
                },
            )

        await _publish_audit(
            get_event_bus(),
            "connector_service.connector.custom_mcp.created",
            {
                "user_id": user_id,
                "connector_id": persisted.id,
                "label": persisted.label,
                "url": persisted.url,
                "tools_count": persisted.tools_count,
            },
        )
        return persisted

    @router.delete("/custom/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_custom_mcp(connector_id: str, request: Request):
        if not custom_mcp_enabled():
            raise _feature_disabled_404()

        user_id = await resolve_user_id(request)
        if not user_id:
            raise _unauth_401()

        repo: "ConnectorRepository" = get_repo()
        existing = await repo.get_custom_by_id(user_id, connector_id)
        if existing is None:
            raise _not_found_404()

        # Revoke vault ref first; if it's a no-op for ``none`` rows
        # dev_vault returns True regardless.
        # We don't have the ref on the API model — for dev_vault we can
        # call revoke with the empty string and it's a no-op. For the
        # real vault we'll need the ref column exposed on a repo helper;
        # follow-up issue tracked in the PR body.
        dev_vault.revoke_secret("")

        ok = await repo.delete_custom(user_id, connector_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": {
                        "code": "internal_error",
                        "message": "Failed to delete connector",
                    }
                },
            )

        await _publish_audit(
            get_event_bus(),
            "connector_service.connector.custom_mcp.revoked",
            {
                "user_id": user_id,
                "connector_id": connector_id,
                "url": existing.url,
            },
        )
        # 204 -> no body
        return None

    @router.post(
        "/custom/{connector_id}/revalidate",
        response_model=CustomMcpConnector,
    )
    async def revalidate_custom_mcp(
        connector_id: str, request: Request
    ) -> CustomMcpConnector:
        if not custom_mcp_enabled():
            raise _feature_disabled_404()

        user_id = await resolve_user_id(request)
        if not user_id:
            raise _unauth_401()

        repo: "ConnectorRepository" = get_repo()
        existing = await repo.get_custom_by_id(user_id, connector_id)
        if existing is None:
            raise _not_found_404()

        # We don't have the auth_secret in memory — for the dev_vault
        # stub, ``none`` rows just retry with no auth. PAT/oauth_oob
        # re-validation in this slice will need the user to re-submit
        # the secret; tracked as a follow-up. For now we run the
        # handshake without the secret if we don't have it.
        handshake = await validate_mcp_url(
            url=existing.url,
            auth_kind=existing.auth_kind.value,
            auth_secret=None,
        )

        new_status = (
            CustomMcpStatus.ACTIVE.value
            if handshake.ok
            else CustomMcpStatus.ERROR.value
        )
        last_error = None if handshake.ok else handshake.error_message
        updated = await repo.update_custom_after_handshake(
            user_id=user_id,
            connector_id=connector_id,
            status=new_status,
            tools_count=handshake.tools_count if handshake.ok else existing.tools_count,
            last_error=last_error,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": {
                        "code": "internal_error",
                        "message": "Failed to update connector",
                    }
                },
            )

        await _publish_audit(
            get_event_bus(),
            (
                "connector_service.connector.custom_mcp.revalidated"
                if handshake.ok
                else "connector_service.connector.custom_mcp.revalidate_failed"
            ),
            {
                "user_id": user_id,
                "connector_id": connector_id,
                "status": new_status,
                "tools_count": handshake.tools_count,
                "error_code": handshake.error_code,
            },
        )

        if not handshake.ok:
            # Even though the row updated, surface the handshake failure
            # to the caller so the UI can show the same error path as on
            # create.
            raise _handshake_422(handshake)
        return updated

    return router
