"""Tax Service API with NATS Event Integration and PostgreSQL."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException

# Add parent directory to path for core imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from isa_common.consul_client import ConsulRegistry
from core.nats_client import get_event_bus
from core.config_manager import ConfigManager

from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .providers.mock import MockTaxProvider
from .tax_repository import TaxRepository

logger = logging.getLogger(__name__)

consul_registry: Optional[ConsulRegistry] = None
event_bus = None
provider = MockTaxProvider()
repository: Optional[TaxRepository] = None
config_manager: Optional[ConfigManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consul_registry, event_bus, repository, config_manager

    # Initialize config manager
    config_manager = ConfigManager("tax_service")

    # Initialize repository (PostgreSQL)
    try:
        repository = TaxRepository(config=config_manager)
        logger.info("Tax repository initialized with PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to initialize repository: {e}")
        repository = None

    # Initialize event bus for event-driven communication
    try:
        event_bus = await get_event_bus("tax_service")
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
                service_port=int(os.getenv("PORT", "8253")),
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

    logger.info("Tax Service started")

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

    logger.info("Tax Service shutting down...")


app = FastAPI(title="tax_service", version="0.1.0", lifespan=lifespan)


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
    items = payload.get("items") or []
    address = payload.get("address")
    currency = payload.get("currency", "USD")
    order_id = payload.get("order_id")
    user_id = payload.get("user_id", "unknown")

    if not items or not address:
        raise HTTPException(status_code=400, detail="items and address are required")

    result = await provider.calculate(items=items, address=address, currency=currency)

    # Store calculation if order_id provided and repository is available
    if order_id and repository:
        subtotal = sum(item.get("amount", 0) or (item.get("unit_price", 0) * item.get("quantity", 1)) for item in items)

        # Store in database
        calculation = await repository.create_calculation(
            order_id=order_id,
            user_id=user_id,
            subtotal=subtotal,
            total_tax=result.get("total_tax", 0),
            currency=currency,
            tax_lines=result.get("lines", []),
            shipping_address=address
        )

        calculation_id = calculation["calculation_id"]

        # Publish event if event bus is available
        if event_bus:
            try:
                from .events.publishers import publish_tax_calculated
                from .events.models import TaxLineItem

                tax_lines = [
                    TaxLineItem(
                        line_item_id=line.get("line_item_id", f"line_{i}"),
                        sku_id=line.get("sku_id"),
                        tax_amount=float(line.get("tax_amount", 0)),
                        tax_rate=float(line.get("rate", 0)),
                        jurisdiction=line.get("jurisdiction"),
                        tax_type=line.get("tax_type")
                    )
                    for i, line in enumerate(result.get("lines", []))
                ]

                await publish_tax_calculated(
                    event_bus=event_bus,
                    order_id=order_id,
                    calculation_id=calculation_id,
                    user_id=user_id,
                    subtotal=subtotal,
                    total_tax=result.get("total_tax", 0),
                    currency=currency,
                    tax_lines=tax_lines,
                    shipping_address=address
                )
            except Exception as e:
                logger.error(f"Failed to publish tax calculated event: {e}")

        result["calculation_id"] = calculation_id
        result["order_id"] = order_id

    return result


@app.get("/api/v1/tax/calculations/{order_id}")
async def get_tax_calculation(order_id: str):
    """Get tax calculation for an order."""
    if not repository:
        raise HTTPException(status_code=503, detail="Repository not available")

    calculation = await repository.get_calculation_by_order(order_id)
    if not calculation:
        raise HTTPException(status_code=404, detail="Tax calculation not found")

    return calculation
