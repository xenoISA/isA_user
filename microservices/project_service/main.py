"""
Project Microservice — CRUD for project workspaces (#258, #294)
Port: 8260
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.auth_dependencies import get_authenticated_caller
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.health import HealthCheck

from isa_common.consul_client import ConsulRegistry

from .models import (
    CreateProjectRequest, UpdateProjectRequest, SetInstructionsRequest,
    ProjectResponse, ProjectListResponse, ProjectFileResponse, ProjectFileListResponse, ErrorResponse,
)
from .protocols import (
    ProjectNotFoundError, ProjectPermissionError,
    ProjectLimitExceeded, InvalidProjectUpdate, RepositoryError,
    ProjectServiceException,
)
from .factory import create_project_service
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

config_manager = ConfigManager("project_service")
config = config_manager.get_service_config()
logger = setup_service_logger("project_service")

project_service = None
consul_registry: Optional[ConsulRegistry] = None
shutdown_manager = GracefulShutdown("project_service")


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    shutdown_manager.install_signal_handlers()
    global project_service, consul_registry
    logger.info("Starting Project Service on port %s...", config.service_port)

    # Wire event bus if NATS is available
    event_bus = None
    try:
        from core.nats_client import get_event_bus
        event_bus = await get_event_bus("project_service")
        logger.info("Event bus connected")
    except Exception as e:
        logger.info("Event bus unavailable, audit events disabled: %s", e)

    project_service = create_project_service(
        config_manager=config_manager,
        event_bus=event_bus,
    )

    if config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }

            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",
            )
            consul_registry.register()
            consul_registry.start_maintenance()
            logger.info("Service registered with Consul: %s routes", route_meta.get("route_count", 0))
        except Exception as e:
            logger.warning("Failed to register with Consul: %s", e)
            consul_registry = None

    logger.info("Project Service ready")
    yield
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("Service deregistered from Consul")
        except Exception as e:
            logger.error("Failed to deregister from Consul: %s", e)
    logger.info("Project Service shutting down")


app = FastAPI(title="Project Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)


# =============================================================================
# Exception handlers — structured {status, error, detail}
# =============================================================================

@app.exception_handler(ProjectNotFoundError)
async def _not_found(request: Request, exc: ProjectNotFoundError):
    logger.warning("Project not found: %s", exc)
    return JSONResponse(status_code=404, content={"status": "error", "error": "not_found", "detail": str(exc)})


@app.exception_handler(ProjectPermissionError)
async def _permission(request: Request, exc: ProjectPermissionError):
    logger.warning("Permission denied: %s", exc)
    return JSONResponse(status_code=403, content={"status": "error", "error": "forbidden", "detail": str(exc)})


@app.exception_handler(ProjectLimitExceeded)
async def _limit(request: Request, exc: ProjectLimitExceeded):
    logger.warning("Project limit exceeded: %s", exc)
    return JSONResponse(status_code=400, content={"status": "error", "error": "limit_exceeded", "detail": str(exc)})


@app.exception_handler(InvalidProjectUpdate)
async def _invalid_update(request: Request, exc: InvalidProjectUpdate):
    logger.warning("Invalid update: %s", exc.detail)
    return JSONResponse(status_code=422, content={"status": "error", "error": "invalid_update", "detail": exc.detail})


@app.exception_handler(RepositoryError)
async def _repository(request: Request, exc: RepositoryError):
    logger.error("Repository error: %s (cause: %s)", exc.detail, exc.cause)
    return JSONResponse(status_code=500, content={"status": "error", "error": "internal_error", "detail": "An internal error occurred"})


# =============================================================================
# Dependencies
# =============================================================================

def get_service():
    return project_service


# =============================================================================
# Health
# =============================================================================

health = HealthCheck("project_service", version="1.0.0", shutdown_manager=shutdown_manager)


@app.get("/api/v1/projects/health")
@app.get("/health")
async def health_check():
    return await health.check()


# =============================================================================
# Project CRUD
# =============================================================================

@app.post("/api/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    return await svc.create_project(caller_id, request.name, request.description, request.custom_instructions)


@app.get("/api/v1/projects", response_model=ProjectListResponse)
async def list_projects(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    projects = await svc.list_projects(caller_id, limit, offset)
    return {"projects": projects, "total": len(projects)}


@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    return await svc.get_project(project_id, caller_id)


@app.put("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    updates = request.model_dump(exclude_unset=True)
    return await svc.update_project(project_id, caller_id, **updates)


@app.delete("/api/v1/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    await svc.delete_project(project_id, caller_id)


@app.put("/api/v1/projects/{project_id}/instructions")
async def set_instructions(
    project_id: str,
    request: SetInstructionsRequest,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    await svc.set_instructions(project_id, caller_id, request.instructions)
    return {"message": "Instructions updated"}


@app.get("/api/v1/projects/{project_id}/files", response_model=ProjectFileListResponse)
async def list_project_files(
    project_id: str,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    files = await svc.list_project_files(project_id, caller_id)
    return {"files": files, "total": len(files)}


@app.post("/api/v1/projects/{project_id}/files", response_model=ProjectFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    content = await file.read()
    return await svc.create_project_file(
        project_id,
        caller_id,
        file.filename or "upload.bin",
        file.content_type,
        len(content),
    )


@app.delete("/api/v1/projects/{project_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_file(
    project_id: str,
    file_id: str,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    await svc.delete_project_file(project_id, caller_id, file_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("microservices.project_service.main:app", host="0.0.0.0", port=8260, reload=True)
