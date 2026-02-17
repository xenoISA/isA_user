"""Fulfillment Service API with NATS Event Integration and PostgreSQL."""

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
from .providers.mock import MockFulfillmentProvider
from .fulfillment_repository import FulfillmentRepository

logger = logging.getLogger(__name__)

consul_registry: Optional[ConsulRegistry] = None
event_bus = None
provider = MockFulfillmentProvider()
repository: Optional[FulfillmentRepository] = None
config_manager: Optional[ConfigManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry, event_bus, repository, config_manager

    # Initialize config manager
    config_manager = ConfigManager("fulfillment_service")

    # Initialize repository (PostgreSQL)
    try:
        repository = FulfillmentRepository(config=config_manager)
        logger.info("Fulfillment repository initialized with PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to initialize repository: {e}")
        repository = None

    # Initialize event bus for event-driven communication
    try:
        event_bus = await get_event_bus("fulfillment_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

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
                service_port=int(os.getenv("PORT", "8254")),
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

    logger.info("Fulfillment Service started")

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

    logger.info("Fulfillment Service shutting down...")


app = FastAPI(title="fulfillment_service", version="0.1.0", lifespan=lifespan)


@app.get("/api/v1/fulfillment/health")
@app.get("/health")
async def health():
    return {"status": "ok", "service": "fulfillment_service"}


@app.post("/api/v1/fulfillment/shipments")
async def create_shipment(payload: Dict[str, Any]):
    """
    Create shipment for an order (HTTP API).

    Note: Shipments are also created automatically via tax.calculated events.
    """
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    order_id = payload.get("order_id")
    items = payload.get("items") or []
    address = payload.get("address")
    user_id = payload.get("user_id", "unknown")

    if not order_id or not items or not address:
        raise HTTPException(status_code=400, detail="order_id, items, and address are required")

    # Create shipment using provider to get tracking info
    result = await provider.create_shipment(order_id=order_id, items=items, address=address)

    # Store shipment in database
    shipment = await repository.create_shipment(
        order_id=order_id,
        user_id=user_id,
        items=items,
        shipping_address=address,
        tracking_number=result.get("tracking_number"),
        status="created"
    )

    shipment_id = shipment["shipment_id"]

    # Publish event if event bus is available
    if event_bus:
        try:
            from .events.publishers import publish_shipment_prepared
            from .events.models import ShipmentItem

            shipment_items = [
                ShipmentItem(
                    sku_id=item.get("sku_id") or item.get("product_id") or "unknown",
                    quantity=item.get("quantity", 1),
                    weight_grams=item.get("weight_grams", 500)
                )
                for item in items
            ]

            await publish_shipment_prepared(
                event_bus=event_bus,
                order_id=order_id,
                shipment_id=shipment_id,
                user_id=user_id,
                items=shipment_items,
                shipping_address=address
            )
        except Exception as e:
            logger.error(f"Failed to publish shipment prepared event: {e}")

    return {
        "shipment_id": shipment_id,
        "order_id": order_id,
        "status": "created",
        "tracking_number": result.get("tracking_number")
    }


@app.post("/api/v1/fulfillment/shipments/{shipment_id}/label")
async def create_label(shipment_id: str, payload: Dict[str, Any] = None):
    """
    Create shipping label for a shipment (HTTP API).

    Note: Labels are also created automatically via payment.completed events.
    """
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    shipment = await repository.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if shipment["status"] == "label_purchased":
        return {
            "shipment_id": shipment_id,
            "tracking_number": shipment["tracking_number"],
            "carrier": shipment["carrier"],
            "label_url": shipment["label_url"],
            "status": "label_created"
        }

    # Create label
    tracking_number = f"trk_{uuid4().hex[:10]}"
    carrier = "USPS"

    # Update shipment in database
    await repository.create_label(
        shipment_id=shipment_id,
        carrier=carrier,
        tracking_number=tracking_number
    )

    # Publish event if event bus is available
    if event_bus:
        try:
            from .events.publishers import publish_label_created

            await publish_label_created(
                event_bus=event_bus,
                order_id=shipment["order_id"],
                shipment_id=shipment_id,
                user_id=shipment.get("user_id", "unknown"),
                carrier=carrier,
                tracking_number=tracking_number,
                estimated_delivery=datetime.now(timezone.utc) + timedelta(days=5)
            )
        except Exception as e:
            logger.error(f"Failed to publish label created event: {e}")

    return {
        "shipment_id": shipment_id,
        "tracking_number": tracking_number,
        "carrier": carrier,
        "status": "label_created"
    }


@app.post("/api/v1/fulfillment/shipments/{shipment_id}/cancel")
async def cancel_shipment(shipment_id: str, payload: Dict[str, Any] = None):
    """
    Cancel a shipment (HTTP API).

    Note: Shipments are also canceled automatically via order.canceled events.
    """
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    shipment = await repository.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    payload = payload or {}

    if shipment["status"] == "failed":
        return {"shipment_id": shipment_id, "status": "canceled", "message": "Already canceled"}

    reason = payload.get("reason", "manual_cancellation")
    refund_shipping = shipment["status"] == "label_purchased"

    # Cancel shipment in database
    await repository.cancel_shipment(shipment_id, reason=reason)

    # Publish event if event bus is available
    if event_bus:
        try:
            from .events.publishers import publish_shipment_canceled

            await publish_shipment_canceled(
                event_bus=event_bus,
                order_id=shipment["order_id"],
                shipment_id=shipment_id,
                user_id=shipment.get("user_id", "unknown"),
                reason=reason,
                refund_shipping=refund_shipping
            )
        except Exception as e:
            logger.error(f"Failed to publish shipment canceled event: {e}")

    return {
        "shipment_id": shipment_id,
        "status": "canceled",
        "refund_shipping": refund_shipping
    }


@app.get("/api/v1/fulfillment/shipments/{order_id}")
async def get_shipment(order_id: str):
    """Get shipment for an order."""
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    shipment = await repository.get_shipment_by_order(order_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return shipment


@app.get("/api/v1/fulfillment/tracking/{tracking_number}")
async def get_tracking(tracking_number: str):
    """Get shipment by tracking number."""
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    shipment = await repository.get_shipment_by_tracking(tracking_number)
    if not shipment:
        raise HTTPException(status_code=404, detail="Tracking number not found")

    return {
        "tracking_number": tracking_number,
        "carrier": shipment["carrier"],
        "status": shipment["status"],
        "order_id": shipment["order_id"],
        "shipment_id": shipment["shipment_id"]
    }
