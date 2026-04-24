"""
Project Microservice — CRUD for project workspaces (#258, #294)
Port: 8260
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.responses import JSONResponse


from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.auth_dependencies import get_authenticated_caller
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.health import HealthCheck

from .models import (
    CreateProjectRequest,
    UpdateProjectRequest,
    SetInstructionsRequest,
    ProjectResponse,
    ProjectListResponse,
)
from .protocols import (
    ProjectNotFoundError,
    ProjectPermissionError,
    ProjectLimitExceeded,
    InvalidProjectUpdate,
    RepositoryError,
)
from .factory import create_project_service

config_manager = ConfigManager("project_service")
logger = setup_service_logger("project_service")

project_service = None
shutdown_manager = GracefulShutdown("project_service")


# =============================================================================
# Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    shutdown_manager.install_signal_handlers()
    global project_service
    logger.info("Starting Project Service on port 8260...")

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
    logger.info("Project Service ready")
    yield
    logger.info("Project Service shutting down")


app = FastAPI(title="Project Service", version="1.0.0", lifespan=lifespan)
app.middleware("http")(shutdown_middleware(shutdown_manager))


# =============================================================================
# Exception handlers — structured {status, error, detail}
# =============================================================================


@app.exception_handler(ProjectNotFoundError)
async def _not_found(request: Request, exc: ProjectNotFoundError):
    logger.warning("Project not found: %s", exc)
    return JSONResponse(
        status_code=404,
        content={"status": "error", "error": "not_found", "detail": str(exc)},
    )


@app.exception_handler(ProjectPermissionError)
async def _permission(request: Request, exc: ProjectPermissionError):
    logger.warning("Permission denied: %s", exc)
    return JSONResponse(
        status_code=403,
        content={"status": "error", "error": "forbidden", "detail": str(exc)},
    )


@app.exception_handler(ProjectLimitExceeded)
async def _limit(request: Request, exc: ProjectLimitExceeded):
    logger.warning("Project limit exceeded: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"status": "error", "error": "limit_exceeded", "detail": str(exc)},
    )


@app.exception_handler(InvalidProjectUpdate)
async def _invalid_update(request: Request, exc: InvalidProjectUpdate):
    logger.warning("Invalid update: %s", exc.detail)
    return JSONResponse(
        status_code=422,
        content={"status": "error", "error": "invalid_update", "detail": exc.detail},
    )


@app.exception_handler(RepositoryError)
async def _repository(request: Request, exc: RepositoryError):
    logger.error("Repository error: %s (cause: %s)", exc.detail, exc.cause)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": "internal_error",
            "detail": "An internal error occurred",
        },
    )


# =============================================================================
# Dependencies
# =============================================================================


def get_service():
    return project_service


# =============================================================================
# Health
# =============================================================================

health = HealthCheck(
    "project_service", version="1.0.0", shutdown_manager=shutdown_manager
)


@app.get("/api/v1/projects/health")
@app.get("/health")
async def health_check():
    return await health.check()


# =============================================================================
# Project CRUD
# =============================================================================


@app.post(
    "/api/v1/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    request: CreateProjectRequest,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    return await svc.create_project(
        caller_id, request.name, request.description, request.custom_instructions
    )


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "microservices.project_service.main:app", host="0.0.0.0", port=8260, reload=True
    )
