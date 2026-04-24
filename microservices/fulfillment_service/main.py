"""Fulfillment Service API with NATS Event Integration and PostgreSQL."""

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
from .providers.mock import MockFulfillmentProvider
from .fulfillment_service import FulfillmentService
from .fulfillment_repository import FulfillmentRepository

logger = logging.getLogger(__name__)

consul_registry: Optional[ConsulRegistry] = None
event_bus = None
provider = MockFulfillmentProvider()
service: Optional[FulfillmentService] = None
config_manager: Optional[ConfigManager] = None

# Graceful shutdown manager
shutdown_manager = GracefulShutdown("fulfillment_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry, event_bus, service, config_manager

    shutdown_manager.install_signal_handlers()

    # Initialize config manager
    config_manager = ConfigManager("fulfillment_service")

    # Initialize repository (PostgreSQL)
    repository = None
    try:
        repository = FulfillmentRepository(config=config_manager)
        logger.info("Fulfillment repository initialized with PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to initialize repository: {e}")

    # Initialize event bus for event-driven communication
    try:
        event_bus = await get_event_bus("fulfillment_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(
            f"Failed to initialize event bus: {e}. Continuing without event publishing."
        )
        event_bus = None

    # Create service layer
    if repository:
        service = FulfillmentService(
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

            logger.info(
                f"Event handlers registered successfully - Subscribed to {len(handler_map)} event types"
            )
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
                service_port=int(os.getenv("PORT", "8254")),
                consul_host=os.getenv("CONSUL_HOST", "localhost"),
                consul_port=int(os.getenv("CONSUL_PORT", "8500")),
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",  # Use TTL for reliable health checks,
            )
            consul_registry.register()
            consul_registry.start_maintenance()  # Start TTL heartbeat
            logger.info("Service registered with Consul")
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            consul_registry = None

    logger.info("Fulfillment Service started")

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

    logger.info("Fulfillment Service shutting down...")


app = FastAPI(title="fulfillment_service", version="0.1.0", lifespan=lifespan)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "fulfillment_service")


def _get_service() -> FulfillmentService:
    if not service:
        raise HTTPException(status_code=503, detail="Repository not available")
    return service


health = HealthCheck(
    "fulfillment_service", version="1.0.0", shutdown_manager=shutdown_manager
)
health.add_nats(lambda: event_bus)


@app.get("/api/v1/fulfillment/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()


@app.post("/api/v1/fulfillment/shipments")
async def create_shipment(payload: Dict[str, Any]):
    """
    Create shipment for an order (HTTP API).

    Note: Shipments are also created automatically via tax.calculated events.
    """
    svc = _get_service()
    try:
        return await svc.create_shipment(
            order_id=payload.get("order_id", ""),
            items=payload.get("items") or [],
            address=payload.get("address") or {},
            user_id=payload.get("user_id", "unknown"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/fulfillment/shipments/{shipment_id}/label")
async def create_label(shipment_id: str, payload: Dict[str, Any] = None):
    """
    Create shipping label for a shipment (HTTP API).

    Note: Labels are also created automatically via payment.completed events.
    """
    svc = _get_service()
    try:
        return await svc.create_label(shipment_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/fulfillment/shipments/{shipment_id}/cancel")
async def cancel_shipment(shipment_id: str, payload: Dict[str, Any] = None):
    """
    Cancel a shipment (HTTP API).

    Note: Shipments are also canceled automatically via order.canceled events.
    """
    svc = _get_service()
    payload = payload or {}
    try:
        return await svc.cancel_shipment(
            shipment_id=shipment_id,
            reason=payload.get("reason", "manual_cancellation"),
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/fulfillment/shipments/{order_id}")
async def get_shipment(order_id: str):
    """Get shipment for an order."""
    svc = _get_service()
    shipment = await svc.get_shipment_by_order(order_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@app.get("/api/v1/fulfillment/tracking/{tracking_number}")
async def get_tracking(tracking_number: str):
    """Get shipment by tracking number."""
    svc = _get_service()
    shipment = await svc.get_shipment_by_tracking(tracking_number)
    if not shipment:
        raise HTTPException(status_code=404, detail="Tracking number not found")
    return {
        "tracking_number": tracking_number,
        "carrier": shipment["carrier"],
        "status": shipment["status"],
        "order_id": shipment["order_id"],
        "shipment_id": shipment["shipment_id"],
    }
