"""Tax Service API with NATS Event Integration and PostgreSQL."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException

# Add parent directory to path for core imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from isa_common.consul_client import ConsulRegistry
from core.nats_client import get_event_bus
from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware

from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .providers.mock import MockTaxProvider
from .tax_service import TaxService
from .tax_repository import TaxRepository

logger = logging.getLogger(__name__)

consul_registry: Optional[ConsulRegistry] = None
event_bus = None
provider = MockTaxProvider()
service: Optional[TaxService] = None
config_manager: Optional[ConfigManager] = None

shutdown_manager = GracefulShutdown("tax_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry, event_bus, service, config_manager

    shutdown_manager.install_signal_handlers()
    # Initialize config manager
    config_manager = ConfigManager("tax_service")

    # Initialize repository (PostgreSQL)
    repository = None
    try:
        repository = TaxRepository(config=config_manager)
        logger.info("Tax repository initialized with PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to initialize repository: {e}")

    # Initialize event bus for event-driven communication
    try:
        event_bus = await get_event_bus("tax_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    # Create service layer (always create — service handles None repository
    # gracefully for stateless preview calculations without order_id)
    service = TaxService(
        repository=repository, event_bus=event_bus, provider=provider
    )

    # Register event handlers
    if event_bus and repository:
        try:
            from .events.handlers import get_event_handlers
            handler_map = get_event_handlers(provider, repository, event_bus)

            for event_pattern, handler_func in handler_map.items():
                await event_bus.subscribe_to_events(
                    pattern=event_pattern, handler=handler_func
                )
                logger.info(f"Subscribed to {event_pattern} events")

            logger.info(f"Event handlers registered successfully - Subscribed to {len(handler_map)} event types")
        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}")

    # Consul service registration
    if os.getenv("CONSUL_ENABLED", "false").lower() == "true":
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }
            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=int(os.getenv("PORT", "8253")),
                consul_host=os.getenv("CONSUL_HOST", "localhost"),
                consul_port=int(os.getenv("CONSUL_PORT", "8500")),
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl"  # Use TTL for reliable health checks,
            )
            consul_registry.register()
            consul_registry.start_maintenance()  # Start TTL heartbeat
            logger.info("Service registered with Consul")
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            consul_registry = None

    logger.info("Tax Service started")

    yield

    # Cleanup
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("Service deregistered from Consul")
        except Exception:
            pass

    if event_bus:
        try:
            await event_bus.close()
            logger.info("Event bus closed")
        except Exception as e:
            logger.error(f"Error closing event bus: {e}")

    logger.info("Tax Service shutting down...")


app = FastAPI(title="tax_service", version="0.1.0", lifespan=lifespan)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)


def _get_service() -> TaxService:
    if not service:
        raise HTTPException(status_code=503, detail="Repository not available")
    return service


@app.get("/api/v1/tax/health")
@app.get("/health")
async def health():
    return {"status": "ok", "service": "tax_service"}


@app.post("/api/v1/tax/calculate")
async def calculate_tax(payload: Dict[str, Any]):
    """
    Calculate tax for items (HTTP API).

    Note: Tax calculation is also triggered by inventory.reserved events via NATS.
    """
    svc = _get_service()
    try:
        return await svc.calculate_tax(
            items=payload.get("items") or [],
            address=payload.get("address") or {},
            currency=payload.get("currency", "USD"),
            order_id=payload.get("order_id"),
            user_id=payload.get("user_id", "unknown"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/tax/calculations/{order_id}")
async def get_tax_calculation(order_id: str):
    """Get tax calculation for an order."""
    svc = _get_service()
    calculation = await svc.get_calculation(order_id)
    if not calculation:
        raise HTTPException(status_code=404, detail="Tax calculation not found")
    return calculation
