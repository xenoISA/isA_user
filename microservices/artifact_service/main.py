"""
Artifact Microservice

Backend persistence for AI-generated artifacts (code, html, svg, charts, etc.)
that users save out of chat sessions and reopen from the library. Phase 1 of
xenoISA/isA_user#441 (paired with frontend xenoISA/isA_#427 / #444).

Architecture:
- PostgreSQL: artifact + artifact_versions + artifact_shares tables
  (schema 'artifact'); migration 001 boots the three tables.
- NATS: artifact.created / .updated / .deleted / .version_added events
  for downstream consumers (audit, analytics).
- Consul: registers SERVICE_METADATA + API_ROUTES from routes_registry.

Port: 8291
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel

from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.health import HealthCheck
from core.logger import setup_service_logger
from core.metrics import setup_metrics
from core.nats_client import get_event_bus
from isa_common.consul_client import ConsulRegistry

from .factory import create_artifact_service
from .models import (
    Artifact,
    ArtifactCreateRequest,
    ArtifactListResponse,
    ArtifactScope,
    ArtifactSharesListResponse,
    ArtifactUpdateRequest,
    ArtifactVersion,
    ArtifactVersionCreateRequest,
    PublicArtifactResponse,
    PublishArtifactRequest,
    PublishArtifactResponse,
    RemixArtifactRequest,
    RevokeArtifactRequest,
    RevokeArtifactResponse,
)
from .protocols import (
    ArtifactNotFoundError,
    ArtifactPermissionError,
    ArtifactValidationError,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

config_manager = ConfigManager("artifact_service")
service_config = config_manager.get_service_config()

logger = setup_service_logger("artifact_service")

artifact_service = None
consul_registry: Optional[ConsulRegistry] = None
shutdown_manager = GracefulShutdown("artifact_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global artifact_service, consul_registry
    shutdown_manager.install_signal_handlers()

    logger.info("Starting Artifact Service...")

    # #461: initialise Sentry first so anything that crashes during startup
    # also lands in the dashboard.  No-op when SENTRY_DSN is absent (dev path).
    from .observability import init_sentry

    init_sentry("artifact_service")

    event_bus = None
    try:
        event_bus = await get_event_bus("artifact_service")
        logger.info("Event bus initialized")
    except Exception as e:
        logger.warning(f"Event bus init failed: {e}. Continuing without event publishing.")

    artifact_service = create_artifact_service(event_bus=event_bus)

    # Consul registration — matches the memory_service pattern so the gateway
    # can discover and route /api/v1/artifacts/* to this service.
    if service_config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }
            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=service_config.service_port,
                consul_host=service_config.consul_host,
                consul_port=service_config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",
            )
            consul_registry.register()
            consul_registry.start_maintenance()
            shutdown_manager.set_consul_registry(consul_registry)
            logger.info(f"Registered with Consul: {route_meta.get('route_count')} routes")
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            consul_registry = None

    logger.info("Artifact Service initialized successfully")
    yield

    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    if event_bus:
        await event_bus.close()
    logger.info("Artifact Service shut down cleanly")


app = FastAPI(
    title="Artifact Service",
    description="Backend persistence + lifecycle for AI-generated artifacts",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, service_name="artifact_service")

health = HealthCheck("artifact_service", version="1.0.0", shutdown_manager=shutdown_manager)


@app.get("/api/v1/artifacts/health")
@app.get("/health")
async def health_check():
    return await health.check()


# ============================================================================
# Library CRUD (xenoISA/isA_user#441 — paired with xenoISA/isA_#427 frontend
# library in src/stores/useArtifactLibrary.ts).
#
# All routes accept user_id either via query/body parameter for now. When the
# gateway-issued JWT path lands, swap for a Depends(get_auth_user) shim that
# resolves the same user_id from the request scope.
# ============================================================================


def _raise_for_artifact_error(e: Exception) -> None:
    if isinstance(e, ArtifactNotFoundError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, ArtifactPermissionError):
        raise HTTPException(status_code=403, detail=str(e))
    if isinstance(e, ArtifactValidationError):
        raise HTTPException(status_code=400, detail=str(e))


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Return the bearer token from the ``Authorization`` header (if any).

    Phase 3 polish (xenoISA/isA_user#441 follow-up): the artifact service
    forwards the caller's JWT to upstream services (isA_Model, isA_MCP) so
    user-level rate limits + audit apply to the proxied call. If no header
    is present (e.g. dev/no-auth path) we return ``None`` and the upstream
    keeps using its existing default auth.
    """
    authorization = request.headers.get("authorization") or request.headers.get("Authorization")
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
        return parts[1].strip()
    return None


class CreateArtifactBody(BaseModel):
    user_id: str
    artifact: ArtifactCreateRequest


@app.post("/api/v1/artifacts", response_model=Artifact)
async def create_artifact(body: CreateArtifactBody):
    """Create a new artifact with its first version."""
    try:
        return await artifact_service.create_artifact(body.artifact, body.user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"create_artifact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(
    user_id: str = Query(..., description="User id"),
    scope: ArtifactScope = Query(ArtifactScope.ALL),
    q: Optional[str] = Query(None, description="Free-text filter"),
    cursor: Optional[str] = Query(None, description="Opaque next-page cursor"),
    limit: int = Query(50, ge=1, le=200),
):
    """Compact list for the library grid — does NOT include version content."""
    try:
        return await artifact_service.list_artifacts(
            user_id=user_id,
            scope=scope,
            q=q,
            cursor=cursor,
            limit=limit,
        )
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"list_artifacts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/artifacts/{artifact_id}", response_model=Artifact)
async def get_artifact(
    artifact_id: str,
    user_id: str = Query(..., description="User id"),
):
    """Get full artifact with all versions."""
    try:
        return await artifact_service.get_artifact(artifact_id, user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"get_artifact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateArtifactBody(BaseModel):
    user_id: str
    update: ArtifactUpdateRequest


@app.patch("/api/v1/artifacts/{artifact_id}", response_model=Artifact)
async def update_artifact(artifact_id: str, body: UpdateArtifactBody):
    """Patch artifact: title, visibility, ai_runtime_enabled, storage_scope, metadata."""
    try:
        return await artifact_service.update_artifact(artifact_id, body.update, body.user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"update_artifact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/artifacts/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    user_id: str = Query(..., description="User id"),
):
    """Soft-delete — sets deleted_at, leaves rows in place for audit."""
    try:
        ok = await artifact_service.delete_artifact(artifact_id, user_id)
        return {"success": ok}
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"delete_artifact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AddVersionBody(BaseModel):
    user_id: str
    version: ArtifactVersionCreateRequest


@app.post("/api/v1/artifacts/{artifact_id}/versions", response_model=ArtifactVersion)
async def add_version(artifact_id: str, body: AddVersionBody):
    """Append a new immutable version. Auto-increments number when omitted."""
    try:
        return await artifact_service.add_version(artifact_id, body.version, body.user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"add_version failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 2 (#441) — publish / revoke / public reader / remix
# ============================================================================
# Wires to ArtifactService.publish_artifact / revoke_artifact / list_shares /
# read_public_share / remix_artifact. See isA_/docs/design/427-artifact-flows.md
# §7-8 for the publish + remix flows, and the share + visibility rules.

# Phase 2 Pydantic schemas are imported up top so ruff doesn't strip them
# as unused once the routes below land:
#   PublishArtifactRequest, PublishArtifactResponse,
#   RevokeArtifactRequest, RevokeArtifactResponse,
#   ArtifactSharesListResponse, PublicArtifactResponse, RemixArtifactRequest


@app.post(
    "/api/v1/artifacts/{artifact_id}/publish",
    response_model=PublishArtifactResponse,
)
async def publish_artifact(artifact_id: str, body: PublishArtifactRequest):
    """Owner mints a public/org share token for an artifact (Phase 2 §7)."""
    try:
        return await artifact_service.publish_artifact(artifact_id, body)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"publish_artifact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/artifacts/{artifact_id}/revoke",
    response_model=RevokeArtifactResponse,
)
async def revoke_artifact(artifact_id: str, body: RevokeArtifactRequest):
    """Owner revokes one share (by token) or all active shares for the artifact."""
    try:
        return await artifact_service.revoke_artifact(artifact_id, body)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"revoke_artifact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/artifacts/{artifact_id}/shares",
    response_model=ArtifactSharesListResponse,
)
async def list_artifact_shares(
    artifact_id: str,
    user_id: str = Query(..., description="User id"),
):
    """Owner lists all share rows (active + revoked) for an artifact."""
    try:
        return await artifact_service.list_shares(artifact_id, user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"list_artifact_shares failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/shares/artifacts/{token}",
    response_model=PublicArtifactResponse,
)
async def read_public_artifact_share(
    token: str,
    v: Optional[int] = Query(None, description="Pin to a specific version number"),
    org_id: Optional[str] = Query(None, description="Caller org id for org-scoped shares"),
):
    """Public reader — resolves token → artifact + version. 410 if revoked/expired."""
    try:
        return await artifact_service.read_public_share(token, version=v, org_id=org_id)
    except ArtifactValidationError as e:
        # Revoked/expired/bad-version → 410 Gone is the design-doc behaviour.
        raise HTTPException(status_code=410, detail=str(e))
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"read_public_artifact_share failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/artifacts/remix", response_model=Artifact)
async def remix_artifact(body: RemixArtifactRequest):
    """Clone a published artifact into a new artifact owned by body.user_id (§8)."""
    try:
        return await artifact_service.remix_artifact(body)
    except ArtifactValidationError as e:
        raise HTTPException(status_code=410, detail=str(e))
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"remix_artifact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 3 (#441) — AI Runtime + per-user daily quota,
#                  MCP grants (approve/call/list),
#                  KV storage (get/put/delete).
#
# See isA_/docs/design/427-artifact-flows.md §9-11 for the spec.
# Imports for Phase 3 schemas live in a deferred block below so the format
# step doesn't strip them as "unused" before the route handlers reference
# them. They MUST appear before the @app.<method> decorators below.
# ============================================================================

from .artifact_service import ArtifactQuotaExceededError  # noqa: E402
from .models import (  # noqa: E402
    ArtifactKVResponse,
    ArtifactKVScope,
    ArtifactKVValueRequest,
    ArtifactMCPGrant,
    ArtifactMCPGrantsListResponse,
    ArtifactRuntimeInvokeRequest,
    ArtifactRuntimeInvokeResponse,
    ArtifactRuntimeUsageResponse,
    MCPApproveRequest,
    MCPCallRequest,
    MCPCallResponse,
)


# ----- AI Runtime -----


@app.post(
    "/api/v1/artifacts/{artifact_id}/runtime/invoke",
    response_model=ArtifactRuntimeInvokeResponse,
)
async def runtime_invoke(
    artifact_id: str,
    body: ArtifactRuntimeInvokeRequest,
    response: Response,
    request: Request,
):
    """Invoke the artifact's AI runtime + book usage against quota.

    Proxies to isA_Model with a stub fallback when the upstream is
    unreachable, so the endpoint never 500s on a transient outage. Returns
    429 + Retry-After when the per-user daily call cap is hit. The quota
    check + usage upsert run inside the service layer so we never book a
    call we refused.

    The caller's bearer token (when present) is forwarded to isA_Model so
    user-level rate limits + audit apply to the upstream call.
    """
    try:
        auth_token = _extract_bearer_token(request)
        return await artifact_service.runtime_invoke(artifact_id, body, auth_token=auth_token)
    except ArtifactQuotaExceededError as e:
        response.headers["Retry-After"] = str(e.retry_after)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_quota_exceeded",
                "calls_today": e.calls_today,
                "quota": e.quota,
                "retry_after": e.retry_after,
            },
            headers={"Retry-After": str(e.retry_after)},
        )
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"runtime_invoke failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/artifacts/{artifact_id}/runtime/usage",
    response_model=ArtifactRuntimeUsageResponse,
)
async def runtime_usage(
    artifact_id: str,
    user_id: str = Query(..., description="User id"),
):
    """Return today's (UTC) usage row + the daily quota for the caller."""
    try:
        return await artifact_service.runtime_usage(artifact_id, user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"runtime_usage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----- MCP grants -----


@app.post(
    "/api/v1/artifacts/{artifact_id}/mcp/approve",
    response_model=ArtifactMCPGrant,
)
async def mcp_approve(artifact_id: str, body: MCPApproveRequest):
    """Upsert an MCP grant — ``allow``+``always`` is the one that unlocks the
    silent /mcp/call path. Other (decision, scope) combos are persisted for
    audit but do NOT short-circuit the approval prompt on subsequent calls.
    """
    try:
        return await artifact_service.mcp_approve(artifact_id, body)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"mcp_approve failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/artifacts/{artifact_id}/mcp/call",
    response_model=MCPCallResponse,
)
async def mcp_call(artifact_id: str, body: MCPCallRequest, request: Request):
    """MCP tool call — gated by an active ``allow``+``always`` grant.

    First call (no grant) returns ``{requires_approval: true, prompt}``. After
    POSTing /mcp/approve with scope=always, the same body proxies to isA_MCP
    over the session-aware streamable-HTTP transport and returns the tool's
    result. If isA_MCP is unreachable the response falls back to a stub body
    so the endpoint never 500s.

    The caller's bearer token (when present) is forwarded to isA_MCP so
    user-level rate limits + audit apply to the upstream call.
    """
    try:
        auth_token = _extract_bearer_token(request)
        return await artifact_service.mcp_call(artifact_id, body, auth_token=auth_token)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"mcp_call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/artifacts/{artifact_id}/mcp/grants",
    response_model=ArtifactMCPGrantsListResponse,
)
async def list_mcp_grants(
    artifact_id: str,
    user_id: str = Query(..., description="User id"),
):
    """List every (active or expired) grant the user holds on this artifact."""
    try:
        return await artifact_service.list_mcp_grants(artifact_id, user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"list_mcp_grants failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----- KV storage -----
#
# scope=personal requires user_id (the row is keyed per-user); scope=shared
# only writes if the artifact's storage_scope='shared'. The service layer
# raises ArtifactPermissionError (-> 403) when a shared write isn't allowed
# and ArtifactNotFoundError (-> 404) for missing keys.


@app.get(
    "/api/v1/artifacts/{artifact_id}/kv/{key}",
    response_model=ArtifactKVResponse,
)
async def kv_get(
    artifact_id: str,
    key: str,
    scope: ArtifactKVScope = Query(ArtifactKVScope.PERSONAL, description="KV scope: personal or shared"),
    user_id: Optional[str] = Query(None, description="Required when scope=personal"),
):
    try:
        return await artifact_service.kv_get(artifact_id, key, scope=scope, user_id=user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"kv_get failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/api/v1/artifacts/{artifact_id}/kv/{key}",
    response_model=ArtifactKVResponse,
)
async def kv_put(
    artifact_id: str,
    key: str,
    body: ArtifactKVValueRequest,
    scope: ArtifactKVScope = Query(ArtifactKVScope.PERSONAL, description="KV scope: personal or shared"),
    user_id: Optional[str] = Query(None, description="Required when scope=personal"),
):
    try:
        return await artifact_service.kv_put(artifact_id, key, value=body.value, scope=scope, user_id=user_id)
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"kv_put failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/artifacts/{artifact_id}/kv/{key}")
async def kv_delete(
    artifact_id: str,
    key: str,
    scope: ArtifactKVScope = Query(ArtifactKVScope.PERSONAL, description="KV scope: personal or shared"),
    user_id: Optional[str] = Query(None, description="Required when scope=personal"),
):
    try:
        ok = await artifact_service.kv_delete(artifact_id, key, scope=scope, user_id=user_id)
        return {"success": ok}
    except Exception as e:
        _raise_for_artifact_error(e)
        logger.error(f"kv_delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
