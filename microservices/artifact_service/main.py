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

from fastapi import FastAPI, HTTPException, Query
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
    ArtifactUpdateRequest,
    ArtifactVersion,
    ArtifactVersionCreateRequest,
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
