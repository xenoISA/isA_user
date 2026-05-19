"""
Connector Service — FastAPI app.

Owns:
  GET  /api/v1/connectors/catalog
  GET  /api/v1/connectors/installed
  POST /api/v1/connectors/custom              (feature-flagged)
  DELETE /api/v1/connectors/custom/{id}       (feature-flagged)
  POST /api/v1/connectors/custom/{id}/revalidate (feature-flagged)

Backend slice for xenoISA/isA_#464 — the ConnectorMarketplace UI in
isA_ has been calling these routes into a void. This service is the
home.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI

from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.health import HealthCheck
from core.logger import setup_service_logger
from core.metrics import setup_metrics
from core.nats_client import get_event_bus
from isa_common.consul_client import ConsulRegistry

from . import routes_catalog
from .factory import create_connector_repository
from .routes_custom import build_router as build_custom_router
from .routes_installed import build_router as build_installed_router
from .routes_registry import SERVICE_METADATA, get_routes_for_consul


# Initialize configuration
config_manager = ConfigManager("connector_service")
config = config_manager.get_service_config()

# Setup loggers
logger = setup_service_logger("connector_service")


class ConnectorMicroservice:
    """Connector microservice core class — owns lazily-initialized deps."""

    def __init__(self):
        self.repo = None
        self.event_bus = None
        self.consul_registry: Optional[ConsulRegistry] = None

    async def initialize(self, event_bus=None):
        try:
            self.event_bus = event_bus
            self.repo = create_connector_repository(config=config_manager)
            logger.info("Connector microservice initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize connector microservice: %s", e)
            raise

    async def shutdown(self):
        try:
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("Connector service deregistered from Consul")
                except Exception as e:
                    logger.error("Failed to deregister from Consul: %s", e)

            if self.event_bus:
                await self.event_bus.close()
                logger.info("Event bus closed")
            logger.info("Connector microservice shutdown completed")
        except Exception as e:
            logger.error("Error during shutdown: %s", e)


connector_microservice = ConnectorMicroservice()
shutdown_manager = GracefulShutdown("connector_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: NATS + Consul on startup, deregister on shutdown."""
    shutdown_manager.install_signal_handlers()

    event_bus = None
    try:
        event_bus = await get_event_bus("connector_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(
            "Failed to initialize event bus: %s. Continuing without event publishing.",
            e,
        )
        event_bus = None

    await connector_microservice.initialize(event_bus=event_bus)

    if config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }
            connector_microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",
            )
            connector_microservice.consul_registry.register()
            connector_microservice.consul_registry.start_maintenance()
            logger.info(
                "Service registered with Consul: %s routes",
                route_meta.get("route_count"),
            )
        except Exception as e:
            logger.warning("Failed to register with Consul: %s", e)
            connector_microservice.consul_registry = None

    yield

    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    await connector_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Connector Service",
    description="Connector marketplace + custom remote MCP — xenoISA/isA_#464",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "connector_service")


# ---- Dependency closures used by the route builders ------------------------


def _get_repo():
    if connector_microservice.repo is None:
        raise RuntimeError("connector repository not initialized")
    return connector_microservice.repo


def _get_event_bus():
    return connector_microservice.event_bus


# ---- Health ---------------------------------------------------------------


health = HealthCheck(
    "connector_service",
    version="1.0.0",
    shutdown_manager=shutdown_manager,
)
health.add_postgres(
    lambda: connector_microservice.repo.db if connector_microservice.repo else None
)


@app.get("/api/v1/connectors/health")
@app.get("/health")
async def health_check():
    """Service health check."""
    return await health.check()


# ---- Routes ---------------------------------------------------------------

# Catalog router is module-level — no DB needed.
app.include_router(routes_catalog.router)

# Installed + custom routers need closures over the repo + event_bus.
app.include_router(build_installed_router(_get_repo))
app.include_router(build_custom_router(_get_repo, _get_event_bus))


if __name__ == "__main__":
    config_manager.print_config_summary()
    uvicorn.run(
        "microservices.connector_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
