"""
Sharing Microservice

Responsibilities:
- Token-based share link generation for sessions
- Public share access (no auth — token IS the auth)
- Share revocation and lifecycle management
"""

import logging
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

from .models import (
    ErrorResponse,
    ShareCreateRequest,
    ShareListResponse,
    ShareResponse,
    SharedSessionResponse,
)
from .protocols import (
    ShareExpiredError,
    ShareNotFoundError,
    SharePermissionError,
    ShareServiceError,
    ShareValidationError,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .sharing_service import SharingService
from .factory import create_sharing_service

# Initialize configuration
config_manager = ConfigManager("sharing_service")
config = config_manager.get_service_config()

# Setup loggers
logger = setup_service_logger("sharing_service")


class SharingMicroservice:
    """Sharing microservice core class"""

    def __init__(self):
        self.sharing_service = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self, event_bus=None):
        """Initialize the microservice"""
        try:
            self.event_bus = event_bus
            self.sharing_service = create_sharing_service(
                config=config_manager,
                event_bus=event_bus,
            )
            logger.info("Sharing microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize sharing microservice: {e}")
            raise

    async def shutdown(self):
        """Shutdown the microservice"""
        try:
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("Sharing service deregistered from Consul")
                except Exception as e:
                    logger.error(f"Failed to deregister from Consul: {e}")

            if self.event_bus:
                await self.event_bus.close()
                logger.info("Event bus closed")
            logger.info("Sharing microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
sharing_microservice = SharingMicroservice()
shutdown_manager = GracefulShutdown("sharing_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    shutdown_manager.install_signal_handlers()

    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("sharing_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(
            f"Failed to initialize event bus: {e}. Continuing without event publishing."
        )
        event_bus = None

    # Initialize microservice
    await sharing_microservice.initialize(event_bus=event_bus)

    # Consul service registration
    if config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }

            sharing_microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",
            )
            sharing_microservice.consul_registry.register()
            sharing_microservice.consul_registry.start_maintenance()
            logger.info(
                f"Service registered with Consul: {route_meta.get('route_count')} routes"
            )
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            sharing_microservice.consul_registry = None

    yield

    # Cleanup
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    await sharing_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Sharing Service",
    description="Token-based share link generation for sessions",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "sharing_service")


# Dependency injection
def get_sharing_service() -> SharingService:
    """Get sharing service instance"""
    if not sharing_microservice.sharing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sharing service not initialized",
        )
    return sharing_microservice.sharing_service


# Health check
health = HealthCheck("sharing_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_postgres(
    lambda: sharing_microservice.sharing_service.share_repo.db
    if sharing_microservice.sharing_service
    and hasattr(sharing_microservice.sharing_service, "_share_repo")
    and sharing_microservice.sharing_service._share_repo
    else None
)


@app.get("/api/v1/sharing/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()


# ============================================================================
# Share Management Endpoints
# ============================================================================


@app.post("/api/v1/sessions/{session_id}/shares", response_model=ShareResponse)
async def create_share(
    session_id: str,
    request: ShareCreateRequest,
    user_id: str = Query(..., description="Owner user ID (auth-scoped)"),
    sharing_service: SharingService = Depends(get_sharing_service),
):
    """Create a share link for a session"""
    try:
        return await sharing_service.create_share(session_id, user_id, request)
    except ShareValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SharePermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ShareServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/sessions/{session_id}/shares", response_model=ShareListResponse)
async def list_session_shares(
    session_id: str,
    user_id: str = Query(..., description="Owner user ID (auth-scoped)"),
    sharing_service: SharingService = Depends(get_sharing_service),
):
    """List all active shares for a session"""
    try:
        return await sharing_service.list_session_shares(session_id, user_id)
    except ShareValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SharePermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ShareServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ============================================================================
# Public Share Access (no auth required — token IS the auth)
# ============================================================================


@app.get("/api/v1/shares/{token}", response_model=SharedSessionResponse)
async def access_share(
    token: str,
    sharing_service: SharingService = Depends(get_sharing_service),
):
    """Access a shared session via token (public endpoint)"""
    try:
        return await sharing_service.access_share(token)
    except ShareNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ShareExpiredError as e:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e))
    except ShareServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ============================================================================
# Share Revocation (owner only)
# ============================================================================


@app.delete("/api/v1/shares/{token}")
async def revoke_share(
    token: str,
    user_id: str = Query(..., description="Owner user ID (auth-scoped)"),
    sharing_service: SharingService = Depends(get_sharing_service),
):
    """Revoke a share link (owner only)"""
    try:
        await sharing_service.revoke_share(token, user_id)
        return {"message": "Share link revoked successfully"}
    except ShareNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SharePermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ShareServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


if __name__ == "__main__":
    config_manager.print_config_summary()

    uvicorn.run(
        "microservices.sharing_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
