"""Inventory Service API with NATS Event Integration and PostgreSQL."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException


from isa_common.consul_client import ConsulRegistry
from core.nats_client import get_event_bus
from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics
from core.health import HealthCheck

from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .inventory_service import InventoryService
from .inventory_repository import InventoryRepository

logger = logging.getLogger(__name__)

consul_registry: Optional[ConsulRegistry] = None
event_bus = None
service: Optional[InventoryService] = None
config_manager: Optional[ConfigManager] = None
shutdown_manager = GracefulShutdown("inventory_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry, event_bus, service, config_manager
    shutdown_manager.install_signal_handlers()

    # Initialize config manager
    config_manager = ConfigManager("inventory_service")

    # Initialize repository (PostgreSQL)
    repository = None
    try:
        repository = InventoryRepository(config=config_manager)
        logger.info("Inventory repository initialized with PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to initialize repository: {e}")

    # Initialize event bus for event-driven communication
    try:
        event_bus = await get_event_bus("inventory_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    # Create service layer
    if repository:
        service = InventoryService(repository=repository, event_bus=event_bus)

    # Register event handlers
    if event_bus and repository:
        try:
            from .events.handlers import get_event_handlers
            handler_map = get_event_handlers(repository, event_bus)

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
                service_port=int(os.getenv("PORT", "8252")),
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

    logger.info("Inventory Service started")

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

    logger.info("Inventory Service shutting down...")


app = FastAPI(title="inventory_service", version="0.1.0", lifespan=lifespan)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "inventory_service")


def _get_service() -> InventoryService:
    if not service:
        raise HTTPException(status_code=503, detail="Repository not available")
    return service


health = HealthCheck("inventory_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_nats(lambda: event_bus)


@app.get("/api/v1/inventory/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()

@app.post("/api/v1/inventory/reserve")
async def reserve_inventory(payload: Dict[str, Any]):
    """
    Reserve inventory for an order (HTTP API).

    Note: This endpoint is also triggered by order.created events via NATS.
    """
    svc = _get_service()
    try:
        return await svc.reserve_inventory(
            order_id=payload.get("order_id", ""),
            items=payload.get("items") or [],
            user_id=payload.get("user_id", "unknown"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/inventory/commit")
async def commit_inventory(payload: Dict[str, Any]):
    """
    Commit inventory reservation (after payment).

    Note: This endpoint is also triggered by payment.completed events via NATS.
    """
    svc = _get_service()
    try:
        return await svc.commit_reservation(
            order_id=payload.get("order_id", ""),
            reservation_id=payload.get("reservation_id"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/inventory/release")
async def release_inventory(payload: Dict[str, Any]):
    """
    Release inventory reservation (order canceled).

    Note: This endpoint is also triggered by order.canceled events via NATS.
    """
    svc = _get_service()
    try:
        return await svc.release_reservation(
            order_id=payload.get("order_id", ""),
            reservation_id=payload.get("reservation_id"),
            reason=payload.get("reason", "manual_release"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/inventory/reservations/{order_id}")
async def get_reservation(order_id: str):
    """Get reservation status for an order."""
    svc = _get_service()
    reservation = await svc.get_reservation(order_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation
