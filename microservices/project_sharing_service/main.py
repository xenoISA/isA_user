"""
Project Sharing Microservice

Responsibilities:
- Invite collaborators to a project by email + role
- Accept invitations via token
- Revoke / role-update invitations
- Idempotent re-invite for pending invites

Paired with isA_/#429. Owns the project_sharing.project_shares table.
"""

from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status

from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.health import HealthCheck
from core.logger import setup_service_logger
from core.metrics import setup_metrics
from core.nats_client import get_event_bus
from isa_common.consul_client import ConsulRegistry

from .factory import create_project_sharing_service
from .models import (
    AcceptShareRequest,
    CreateShareRequest,
    RevokeResponse,
    ShareListResponse,
    ShareResponse,
    UpdateShareRequest,
)
from .project_sharing_service import ProjectSharingService
from .protocols import (
    ProjectShareNotFoundError,
    ProjectSharePermissionError,
    ProjectShareServiceError,
    ProjectShareValidationError,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Initialize configuration
config_manager = ConfigManager("project_sharing_service")
config = config_manager.get_service_config()

# Setup loggers
logger = setup_service_logger("project_sharing_service")


class ProjectSharingMicroservice:
    """Project sharing microservice core class."""

    def __init__(self):
        self.sharing_service: Optional[ProjectSharingService] = None
        self.event_bus = None
        self.consul_registry: Optional[ConsulRegistry] = None

    async def initialize(self, event_bus=None):
        try:
            self.event_bus = event_bus
            self.sharing_service = create_project_sharing_service(
                config=config_manager,
                event_bus=event_bus,
            )
            logger.info("Project sharing microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize project sharing microservice: {e}")
            raise

    async def shutdown(self):
        try:
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("Project sharing service deregistered from Consul")
                except Exception as e:
                    logger.error(f"Failed to deregister from Consul: {e}")

            if self.event_bus:
                await self.event_bus.close()
                logger.info("Event bus closed")
            logger.info("Project sharing microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
project_sharing_microservice = ProjectSharingMicroservice()
shutdown_manager = GracefulShutdown("project_sharing_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    shutdown_manager.install_signal_handlers()

    event_bus = None
    try:
        event_bus = await get_event_bus("project_sharing_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    await project_sharing_microservice.initialize(event_bus=event_bus)

    if config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }
            project_sharing_microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",
            )
            project_sharing_microservice.consul_registry.register()
            project_sharing_microservice.consul_registry.start_maintenance()
            logger.info(f"Service registered with Consul: {route_meta.get('route_count')} routes")
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            project_sharing_microservice.consul_registry = None

    yield

    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    await project_sharing_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Project Sharing Service",
    description="Project-level invite/accept/revoke for collaboration (#442)",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "project_sharing_service")


# Dependency injection
def get_sharing_service() -> ProjectSharingService:
    if not project_sharing_microservice.sharing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project sharing service not initialized",
        )
    return project_sharing_microservice.sharing_service


# Health check
health = HealthCheck(
    "project_sharing_service",
    version="1.0.0",
    shutdown_manager=shutdown_manager,
)
health.add_postgres(
    lambda: (
        project_sharing_microservice.sharing_service.share_repo.db
        if project_sharing_microservice.sharing_service
        and hasattr(project_sharing_microservice.sharing_service, "_share_repo")
        and project_sharing_microservice.sharing_service._share_repo
        else None
    )
)


@app.get("/api/v1/project-sharing/health")
@app.get("/health")
async def health_check():
    """Service health check."""
    return await health.check()


# ============================================================================
# Project share management endpoints (owner-scoped)
# ============================================================================


@app.post(
    "/api/v1/projects/{project_id}/shares",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_to_project(
    project_id: str,
    request: CreateShareRequest,
    sharing_service: ProjectSharingService = Depends(get_sharing_service),
):
    """Invite a user to a project. Idempotent on (project_id, lower(email)) while pending."""
    try:
        return await sharing_service.invite(project_id, request)
    except ProjectShareValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProjectSharePermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ProjectShareServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/projects/{project_id}/shares", response_model=ShareListResponse)
async def list_project_shares(
    project_id: str,
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Optional filter: pending | accepted | revoked",
    ),
    sharing_service: ProjectSharingService = Depends(get_sharing_service),
):
    """List project shares, optionally filtered by status."""
    try:
        return await sharing_service.list_shares(project_id, status=status_filter)
    except ProjectShareValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProjectShareServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.patch(
    "/api/v1/projects/{project_id}/shares/{share_id}",
    response_model=ShareResponse,
)
async def update_share_role(
    project_id: str,
    share_id: str,
    request: UpdateShareRequest,
    sharing_service: ProjectSharingService = Depends(get_sharing_service),
):
    """Update the role on a project share."""
    try:
        return await sharing_service.update_role(project_id, share_id, request)
    except ProjectShareNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ProjectShareValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProjectShareServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete(
    "/api/v1/projects/{project_id}/shares/{share_id}",
    response_model=RevokeResponse,
)
async def revoke_project_share(
    project_id: str,
    share_id: str,
    sharing_service: ProjectSharingService = Depends(get_sharing_service),
):
    """Revoke a project share. Nulls the invite_token so it can't be reused."""
    try:
        return await sharing_service.revoke(project_id, share_id)
    except ProjectShareNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ProjectShareServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Public accept endpoint — token IS the auth
# ============================================================================


@app.post(
    "/api/v1/shares/accept/{token}",
    response_model=ShareResponse,
)
async def accept_share(
    token: str,
    request: AcceptShareRequest,
    sharing_service: ProjectSharingService = Depends(get_sharing_service),
):
    """Accept a project share invite via token. Idempotent on already-accepted invites."""
    try:
        return await sharing_service.accept(token, request)
    except ProjectShareNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ProjectShareValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProjectShareServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


if __name__ == "__main__":
    config_manager.print_config_summary()
    uvicorn.run(
        "microservices.project_sharing_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
