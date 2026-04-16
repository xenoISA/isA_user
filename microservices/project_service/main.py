"""
Project Microservice — CRUD for project workspaces (#258)
Port: 8260
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.auth_dependencies import get_authenticated_caller
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware

from .models import CreateProjectRequest, UpdateProjectRequest, SetInstructionsRequest, ProjectResponse, ProjectListResponse
from .project_repository import ProjectNotFoundError
from .factory import create_project_service

config_manager = ConfigManager("project_service")
logger = setup_service_logger("project_service")

project_service = None
shutdown_manager = GracefulShutdown("project_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    shutdown_manager.install_signal_handlers()
    global project_service
    logger.info("Starting Project Service on port 8260...")
    project_service = create_project_service(config_manager=config_manager)
    logger.info("Project Service ready")
    yield
    logger.info("Project Service shutting down")


app = FastAPI(title="Project Service", version="1.0.0", lifespan=lifespan)
app.middleware("http")(shutdown_middleware(shutdown_manager))


def get_service():
    return project_service


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "project_service"}


@app.post("/api/v1/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    result = await svc.create_project(caller_id, request.name, request.description, request.custom_instructions)
    return result


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
    try:
        return await svc.get_project(project_id, caller_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


@app.put("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    try:
        updates = request.dict(exclude_unset=True)
        return await svc.update_project(project_id, caller_id, **updates)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


@app.delete("/api/v1/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    try:
        await svc.delete_project(project_id, caller_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


@app.put("/api/v1/projects/{project_id}/instructions")
async def set_instructions(
    project_id: str,
    request: SetInstructionsRequest,
    svc=Depends(get_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    try:
        await svc.set_instructions(project_id, caller_id, request.instructions)
        return {"message": "Instructions updated"}
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("microservices.project_service.main:app", host="0.0.0.0", port=8260, reload=True)
