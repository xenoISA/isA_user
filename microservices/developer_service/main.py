"""
Developer Service — backend contract for Developer Journey cockpit (#424).

Port: 8261
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status

from core.auth_dependencies import require_auth_or_internal_service
from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.health import HealthCheck
from core.logger import setup_service_logger
from isa_common.consul_client import ConsulRegistry

from .developer_service import DeveloperOverviewService
from .factory import create_developer_service
from .models import DeveloperHealthResponse, DeveloperOverviewResponse
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

config_manager = ConfigManager("developer_service")
config = config_manager.get_service_config()
logger = setup_service_logger("developer_service")

SERVICE_PORT = (
    config.service_port
    if config.service_port != 8000
    else int(SERVICE_METADATA["port"])
)

developer_service: Optional[DeveloperOverviewService] = create_developer_service()
consul_registry = None
shutdown_manager = GracefulShutdown("developer_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    shutdown_manager.install_signal_handlers()
    global developer_service, consul_registry
    logger.info("Starting Developer Service on port %s...", SERVICE_PORT)

    developer_service = create_developer_service()

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
                service_port=SERVICE_PORT,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",
            )
            consul_registry.register()
            consul_registry.start_maintenance()
            shutdown_manager.set_consul_registry(consul_registry)
            logger.info(
                "Service registered with Consul: %s routes",
                route_meta.get("route_count", "0"),
            )
        except Exception as exc:
            logger.warning("Failed to register with Consul: %s", exc)
            consul_registry = None

    logger.info("Developer Service ready")
    yield
    await shutdown_manager.shutdown_with_timeout()
    logger.info("Developer Service shutting down")


app = FastAPI(title="Developer Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)


def get_developer_service() -> DeveloperOverviewService:
    if developer_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Developer service not initialized",
        )
    return developer_service


async def get_authenticated_caller(
    caller_id: str = Depends(require_auth_or_internal_service),
) -> str:
    return caller_id


health = HealthCheck(
    "developer_service",
    version=SERVICE_METADATA["version"],
    shutdown_manager=shutdown_manager,
)


@app.get("/health")
async def health_check():
    return await health.check()


@app.get("/api/v1/developer/health", response_model=DeveloperHealthResponse)
async def developer_health(
    svc: DeveloperOverviewService = Depends(get_developer_service),
):
    return await svc.health_response(version=SERVICE_METADATA["version"])


@app.get("/api/v1/developer/overview", response_model=DeveloperOverviewResponse)
async def get_developer_overview(
    organization_id: str = Query(..., min_length=1),
    project_id: Optional[str] = Query(None, min_length=1),
    period_days: int = Query(7, ge=1, le=90),
    svc: DeveloperOverviewService = Depends(get_developer_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    return await svc.get_overview(
        user_id=caller_id,
        organization_id=organization_id,
        project_id=project_id,
        period_days=period_days,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "microservices.developer_service.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True,
    )
