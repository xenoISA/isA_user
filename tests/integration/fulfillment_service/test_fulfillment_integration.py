"""
L3 Integration Tests — Fulfillment Service

Tests service layer with mock repository + event capture.
Verifies end-to-end business flows within the service boundary.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from tests.contracts.fulfillment.data_contract import FulfillmentFactory
from microservices.fulfillment_service.fulfillment_service import FulfillmentService


# ============================================================================
# Fixtures — Mock repo with state tracking
# ============================================================================

@pytest.fixture
def stateful_repository():
    """Repository mock that tracks state across calls."""
    repo = AsyncMock()
    repo._shipments = {}
    repo._counter = 0

    async def create_shipment(**kwargs):
        repo._counter += 1
        shipment_id = f"shp_int_{repo._counter}"
        shipment = {
            "shipment_id": shipment_id,
            "order_id": kwargs["order_id"],
            "user_id": kwargs["user_id"],
            "items": kwargs["items"],
            "shipping_address": kwargs["shipping_address"],
            "tracking_number": kwargs.get("tracking_number"),
            "status": kwargs.get("status", "created"),
            "carrier": None,
            "label_url": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        repo._shipments[shipment_id] = shipment
        return shipment

    async def get_shipment(shipment_id):
        return repo._shipments.get(shipment_id)

    async def get_shipment_by_order(order_id):
        for s in repo._shipments.values():
            if s["order_id"] == order_id:
                return s
        return None

    async def get_shipment_by_tracking(tracking_number):
        for s in repo._shipments.values():
            if s["tracking_number"] == tracking_number:
                return s
        return None

    async def create_label(shipment_id, carrier, tracking_number, **kw):
        if shipment_id in repo._shipments:
            repo._shipments[shipment_id]["status"] = "label_purchased"
            repo._shipments[shipment_id]["carrier"] = carrier
            repo._shipments[shipment_id]["tracking_number"] = tracking_number
            return repo._shipments[shipment_id]
        return None

    async def cancel_shipment(shipment_id, reason=None):
        if shipment_id in repo._shipments:
            repo._shipments[shipment_id]["status"] = "failed"
            return repo._shipments[shipment_id]
        return None

    repo.create_shipment = create_shipment
    repo.get_shipment = get_shipment
    repo.get_shipment_by_order = get_shipment_by_order
    repo.get_shipment_by_tracking = get_shipment_by_tracking
    repo.create_label = create_label
    repo.cancel_shipment = cancel_shipment
    return repo


@pytest.fixture
def capturing_event_bus():
    """Event bus that captures published events."""
    bus = AsyncMock()
    bus.published_events = []

    async def capture(event):
        bus.published_events.append(event)

    bus.publish_event = AsyncMock(side_effect=capture)
    return bus


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.create_shipment.return_value = {
        "tracking_number": "trk_int_test",
        "status": "created",
    }
    return provider


@pytest.fixture
def service(stateful_repository, capturing_event_bus, mock_provider):
    return FulfillmentService(
        repository=stateful_repository,
        event_bus=capturing_event_bus,
        provider=mock_provider,
    )


# ============================================================================
# Full lifecycle flows
# ============================================================================

@pytest.mark.integration
class TestShipmentLifecycle:

    async def test_create_then_label(self, service, stateful_repository, capturing_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        shipment = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"], user_id=req["user_id"],
        )

        label = await service.create_label(shipment["shipment_id"])

        assert label["status"] == "label_created"
        assert label["carrier"] == "USPS"
        assert len(capturing_event_bus.published_events) == 2

    async def test_create_then_cancel(self, service, capturing_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        shipment = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )

        result = await service.cancel_shipment(shipment["shipment_id"])

        assert result["status"] == "canceled"
        assert result["refund_shipping"] is False
        assert len(capturing_event_bus.published_events) == 2

    async def test_create_label_then_cancel_refunds_shipping(self, service, capturing_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        shipment = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )
        await service.create_label(shipment["shipment_id"])

        result = await service.cancel_shipment(shipment["shipment_id"])

        assert result["refund_shipping"] is True
        assert len(capturing_event_bus.published_events) == 3

    async def test_get_shipment_by_order_after_create(self, service):
        req = FulfillmentFactory.create_shipment_request()
        await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )

        found = await service.get_shipment_by_order(req["order_id"])

        assert found is not None
        assert found["order_id"] == req["order_id"]

    async def test_get_returns_none_for_unknown_order(self, service):
        result = await service.get_shipment_by_order("ord_does_not_exist")
        assert result is None


# ============================================================================
# Event verification
# ============================================================================

@pytest.mark.integration
class TestFulfillmentEvents:

    async def test_create_shipment_publishes_prepared_event(self, service, capturing_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"], user_id="usr_test",
        )

        assert len(capturing_event_bus.published_events) == 1
        event = capturing_event_bus.published_events[0]
        assert event.type == "fulfillment.shipment.prepared"

    async def test_create_label_publishes_label_event(self, service, capturing_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        ship = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )
        capturing_event_bus.published_events.clear()

        await service.create_label(ship["shipment_id"])

        assert len(capturing_event_bus.published_events) == 1
        event = capturing_event_bus.published_events[0]
        assert event.type == "fulfillment.label.created"

    async def test_cancel_publishes_canceled_event(self, service, capturing_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        ship = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )
        capturing_event_bus.published_events.clear()

        await service.cancel_shipment(ship["shipment_id"])

        assert len(capturing_event_bus.published_events) == 1
        event = capturing_event_bus.published_events[0]
        assert event.type == "fulfillment.shipment.canceled"

    async def test_cancel_already_failed_no_event(self, service, capturing_event_bus, stateful_repository):
        req = FulfillmentFactory.create_shipment_request()
        ship = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )
        await service.cancel_shipment(ship["shipment_id"])
        capturing_event_bus.published_events.clear()

        await service.cancel_shipment(ship["shipment_id"])

        assert len(capturing_event_bus.published_events) == 0

    async def test_idempotent_label_no_extra_event(self, service, capturing_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        ship = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )
        await service.create_label(ship["shipment_id"])
        capturing_event_bus.published_events.clear()

        await service.create_label(ship["shipment_id"])

        assert len(capturing_event_bus.published_events) == 0
