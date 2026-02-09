"""Inventory Service API with NATS Event Integration and PostgreSQL."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException

# Add parent directory to path for core imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from isa_common.consul_client import ConsulRegistry
from core.nats_client import get_event_bus
from core.config_manager import ConfigManager

from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .inventory_repository import InventoryRepository

logger = logging.getLogger(__name__)

consul_registry: Optional[ConsulRegistry] = None
event_bus = None
repository: Optional[InventoryRepository] = None
config_manager: Optional[ConfigManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry, event_bus, repository, config_manager

    # Initialize config manager
    config_manager = ConfigManager("inventory_service")

    # Initialize repository (PostgreSQL)
    try:
        repository = InventoryRepository(config=config_manager)
        logger.info("Inventory repository initialized with PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to initialize repository: {e}")
        repository = None

    # Initialize event bus for event-driven communication
    try:
        event_bus = await get_event_bus("inventory_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

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
            # Start TTL heartbeat - added for consistency with isA_Model
            logger.info("Service registered with Consul")
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            consul_registry = None

    logger.info("Inventory Service started")

    yield

    # Cleanup
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


@app.get("/api/v1/inventory/health")
@app.get("/health")
async def health():
    return {"status": "ok", "service": "inventory_service"}


@app.post("/api/v1/inventory/reserve")
async def reserve_inventory(payload: Dict[str, Any]):
    """
    Reserve inventory for an order (HTTP API).

    Note: This endpoint is also triggered by order.created events via NATS.
    """
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    order_id = payload.get("order_id")
    items = payload.get("items") or []
    user_id = payload.get("user_id", "unknown")

    if not order_id or not items:
        raise HTTPException(status_code=400, detail="order_id and items are required")

    # Create reservation in database
    reservation = await repository.create_reservation(
        order_id=order_id,
        user_id=user_id,
        items=items,
        expires_in_minutes=30
    )

    reservation_id = reservation["reservation_id"]
    expires_at = reservation["expires_at"]

    # Publish event if event bus is available
    if event_bus:
        try:
            from .events.publishers import publish_stock_reserved
            from .events.models import ReservedItem

            reserved_items = []
            for item in items:
                sku_id = item.get("sku_id") or item.get("product_id") or item.get("id")
                if sku_id:
                    reserved_items.append(ReservedItem(
                        sku_id=sku_id,
                        quantity=item.get("quantity", 1),
                        unit_price=item.get("unit_price") or item.get("price")
                    ))

            if reserved_items:
                await publish_stock_reserved(
                    event_bus=event_bus,
                    order_id=order_id,
                    reservation_id=reservation_id,
                    user_id=user_id,
                    items=reserved_items,
                    expires_at=expires_at
                )
        except Exception as e:
            logger.error(f"Failed to publish stock reserved event: {e}")

    return {"reservation_id": reservation_id, "status": "active", "expires_at": expires_at}


@app.post("/api/v1/inventory/commit")
async def commit_inventory(payload: Dict[str, Any]):
    """
    Commit inventory reservation (after payment).

    Note: This endpoint is also triggered by payment.completed events via NATS.
    """
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    order_id = payload.get("order_id")
    reservation_id = payload.get("reservation_id")

    if not order_id:
        raise HTTPException(status_code=400, detail="order_id is required")

    # Find reservation
    reservation = None
    if reservation_id:
        reservation = await repository.get_reservation(reservation_id)
    if not reservation:
        reservation = await repository.get_active_reservation_for_order(order_id)

    if not reservation:
        raise HTTPException(status_code=404, detail="No active reservation found")

    res_id = reservation["reservation_id"]

    # Commit reservation in database
    await repository.commit_reservation(res_id)

    # Publish event if event bus is available
    if event_bus:
        try:
            from .events.publishers import publish_stock_committed
            from .events.models import ReservedItem

            items = reservation.get("items", [])
            reserved_items = [ReservedItem(**item) for item in items]
            await publish_stock_committed(
                event_bus=event_bus,
                order_id=order_id,
                reservation_id=res_id,
                user_id=reservation.get("user_id", "unknown"),
                items=reserved_items
            )
        except Exception as e:
            logger.error(f"Failed to publish stock committed event: {e}")

    return {"order_id": order_id, "reservation_id": res_id, "status": "committed"}


@app.post("/api/v1/inventory/release")
async def release_inventory(payload: Dict[str, Any]):
    """
    Release inventory reservation (order canceled).

    Note: This endpoint is also triggered by order.canceled events via NATS.
    """
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    order_id = payload.get("order_id")
    reservation_id = payload.get("reservation_id")
    reason = payload.get("reason", "manual_release")

    if not order_id:
        raise HTTPException(status_code=400, detail="order_id is required")

    # Find reservation
    reservation = None
    if reservation_id:
        reservation = await repository.get_reservation(reservation_id)
    if not reservation:
        reservation = await repository.get_active_reservation_for_order(order_id)

    if not reservation:
        # Already released or never existed
        return {"order_id": order_id, "status": "released", "message": "No active reservation found"}

    res_id = reservation["reservation_id"]

    # Release reservation in database
    await repository.release_reservation(res_id)

    # Publish event if event bus is available
    if event_bus:
        try:
            from .events.publishers import publish_stock_released
            from .events.models import ReservedItem

            items = reservation.get("items", [])
            reserved_items = [ReservedItem(**item) for item in items]
            await publish_stock_released(
                event_bus=event_bus,
                order_id=order_id,
                reservation_id=res_id,
                user_id=reservation.get("user_id", "unknown"),
                items=reserved_items,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to publish stock released event: {e}")

    return {"order_id": order_id, "reservation_id": res_id, "status": "released"}


@app.get("/api/v1/inventory/reservations/{order_id}")
async def get_reservation(order_id: str):
    """Get reservation status for an order."""
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    reservation = await repository.get_reservation_by_order(order_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    return reservation
