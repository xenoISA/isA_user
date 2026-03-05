"""
L5 Smoke Tests — Commerce Services

End-to-end flows across inventory, tax, and fulfillment services.
Uses mocked infrastructure (repository, event bus, provider) but
exercises full service logic as integrated components.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone

from microservices.inventory_service.inventory_service import InventoryService
from microservices.tax_service.tax_service import TaxService
from microservices.fulfillment_service.fulfillment_service import FulfillmentService
from tests.contracts.inventory.data_contract import InventoryFactory
from tests.contracts.tax.data_contract import TaxFactory
from tests.contracts.fulfillment.data_contract import FulfillmentFactory


# ============================================================================
# Shared stateful mocks
# ============================================================================

@pytest.fixture
def inventory_repo():
    repo = AsyncMock()
    repo._reservations = {}
    repo._counter = 0

    async def create_reservation(**kwargs):
        repo._counter += 1
        res_id = f"res_smoke_{repo._counter}"
        reservation = {
            "reservation_id": res_id,
            "order_id": kwargs["order_id"],
            "user_id": kwargs["user_id"],
            "items": kwargs["items"],
            "status": "active",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        repo._reservations[res_id] = reservation
        return reservation

    async def get_reservation(reservation_id):
        r = repo._reservations.get(reservation_id)
        return r if r and r["status"] == "active" else None

    async def get_active_reservation_for_order(order_id):
        for r in repo._reservations.values():
            if r["order_id"] == order_id and r["status"] == "active":
                return r
        return None

    async def get_reservation_by_order(order_id, status=None):
        for r in repo._reservations.values():
            if r["order_id"] == order_id:
                return r
        return None

    async def commit_reservation(reservation_id):
        if reservation_id in repo._reservations:
            repo._reservations[reservation_id]["status"] = "committed"

    async def release_reservation(reservation_id):
        if reservation_id in repo._reservations:
            repo._reservations[reservation_id]["status"] = "released"

    repo.create_reservation = create_reservation
    repo.get_reservation = get_reservation
    repo.get_active_reservation_for_order = get_active_reservation_for_order
    repo.get_reservation_by_order = get_reservation_by_order
    repo.commit_reservation = commit_reservation
    repo.release_reservation = release_reservation
    return repo


@pytest.fixture
def tax_repo():
    repo = AsyncMock()
    repo._calculations = {}
    repo._counter = 0

    async def create_calculation(**kwargs):
        repo._counter += 1
        calc = {
            "calculation_id": f"calc_smoke_{repo._counter}",
            "order_id": kwargs["order_id"],
            "total_tax": kwargs["total_tax"],
            "currency": kwargs.get("currency", "USD"),
        }
        repo._calculations[kwargs["order_id"]] = calc
        return calc

    async def get_calculation_by_order(order_id):
        return repo._calculations.get(order_id)

    repo.create_calculation = create_calculation
    repo.get_calculation_by_order = get_calculation_by_order
    return repo


@pytest.fixture
def fulfillment_repo():
    repo = AsyncMock()
    repo._shipments = {}
    repo._counter = 0

    async def create_shipment(**kwargs):
        repo._counter += 1
        sid = f"shp_smoke_{repo._counter}"
        shipment = {
            "shipment_id": sid,
            "order_id": kwargs["order_id"],
            "user_id": kwargs["user_id"],
            "status": "created",
            "carrier": None,
            "tracking_number": kwargs.get("tracking_number"),
            "label_url": None,
        }
        repo._shipments[sid] = shipment
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

    async def cancel_shipment(shipment_id, reason=None):
        if shipment_id in repo._shipments:
            repo._shipments[shipment_id]["status"] = "failed"

    repo.create_shipment = create_shipment
    repo.get_shipment = get_shipment
    repo.get_shipment_by_order = get_shipment_by_order
    repo.get_shipment_by_tracking = get_shipment_by_tracking
    repo.create_label = create_label
    repo.cancel_shipment = cancel_shipment
    return repo


@pytest.fixture
def event_bus():
    bus = AsyncMock()
    bus.published_events = []

    async def capture(event):
        bus.published_events.append(event)

    bus.publish_event = AsyncMock(side_effect=capture)
    return bus


@pytest.fixture
def tax_provider():
    provider = AsyncMock()
    provider.calculate.return_value = {
        "currency": "USD",
        "total_tax": 8.75,
        "lines": [{"line_item_id": "li_1", "tax_amount": 8.75, "rate": 0.0875}],
    }
    return provider


@pytest.fixture
def fulfillment_provider():
    provider = AsyncMock()
    provider.create_shipment.return_value = {"tracking_number": "trk_smoke_001"}
    return provider


@pytest.fixture
def inventory_svc(inventory_repo, event_bus):
    return InventoryService(repository=inventory_repo, event_bus=event_bus)


@pytest.fixture
def tax_svc(tax_repo, event_bus, tax_provider):
    return TaxService(repository=tax_repo, event_bus=event_bus, provider=tax_provider)


@pytest.fixture
def fulfillment_svc(fulfillment_repo, event_bus, fulfillment_provider):
    return FulfillmentService(
        repository=fulfillment_repo, event_bus=event_bus, provider=fulfillment_provider,
    )


# ============================================================================
# Smoke: Happy Path — Full Order Flow
# ============================================================================

@pytest.mark.smoke
class TestCommerceHappyPath:

    async def test_reserve_tax_ship_flow(self, inventory_svc, tax_svc, fulfillment_svc, event_bus):
        """Full order: reserve inventory → calculate tax → create shipment → label"""
        order_id = InventoryFactory.order_id()
        items = [{"sku_id": "sku_widget", "quantity": 2, "unit_price": 50.0}]
        address = FulfillmentFactory.shipping_address()
        user_id = "usr_smoke"

        # Step 1: Reserve inventory
        reservation = await inventory_svc.reserve_inventory(
            order_id=order_id, items=items, user_id=user_id,
        )
        assert reservation["status"] == "active"

        # Step 2: Calculate tax
        tax = await tax_svc.calculate_tax(
            items=items, address=address, order_id=order_id, user_id=user_id,
        )
        assert "calculation_id" in tax
        assert tax["total_tax"] >= 0

        # Step 3: Create shipment
        shipment = await fulfillment_svc.create_shipment(
            order_id=order_id, items=items, address=address, user_id=user_id,
        )
        assert shipment["status"] == "created"

        # Step 4: Create label (simulates payment complete)
        label = await fulfillment_svc.create_label(shipment["shipment_id"])
        assert label["status"] == "label_created"

        # Step 5: Commit inventory
        committed = await inventory_svc.commit_reservation(
            order_id=order_id, reservation_id=reservation["reservation_id"],
        )
        assert committed["status"] == "committed"

        # Verify events published across all services
        assert len(event_bus.published_events) >= 4

    async def test_reserve_tax_cancel_flow(self, inventory_svc, tax_svc, fulfillment_svc, event_bus):
        """Order cancellation: reserve → tax → ship → cancel → release"""
        order_id = InventoryFactory.order_id()
        items = [{"sku_id": "sku_cancel", "quantity": 1, "unit_price": 30.0}]
        address = FulfillmentFactory.shipping_address()

        reservation = await inventory_svc.reserve_inventory(
            order_id=order_id, items=items,
        )

        await tax_svc.calculate_tax(
            items=items, address=address, order_id=order_id,
        )

        shipment = await fulfillment_svc.create_shipment(
            order_id=order_id, items=items, address=address,
        )

        # Cancel shipment
        cancel = await fulfillment_svc.cancel_shipment(
            shipment["shipment_id"], reason="customer_request",
        )
        assert cancel["status"] == "canceled"

        # Release inventory
        released = await inventory_svc.release_reservation(
            order_id=order_id, reservation_id=reservation["reservation_id"],
        )
        assert released["status"] == "released"


# ============================================================================
# Smoke: Edge Cases
# ============================================================================

@pytest.mark.smoke
class TestCommerceEdgeCases:

    async def test_tax_preview_without_persistence(self, tax_svc):
        """Preview tax without an order — should not persist."""
        result = await tax_svc.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
        )

        assert "calculation_id" not in result
        retrieved = await tax_svc.get_calculation("nonexistent")
        assert retrieved is None

    async def test_release_nonexistent_reservation(self, inventory_svc):
        """Releasing when no reservation exists should succeed gracefully."""
        result = await inventory_svc.release_reservation(order_id="ord_ghost")

        assert result["status"] == "released"

    async def test_idempotent_label_creation(self, fulfillment_svc):
        """Creating a label twice returns same result without error."""
        items = FulfillmentFactory.items()
        address = FulfillmentFactory.shipping_address()

        shipment = await fulfillment_svc.create_shipment(
            order_id="ord_idem", items=items, address=address,
        )
        label1 = await fulfillment_svc.create_label(shipment["shipment_id"])
        label2 = await fulfillment_svc.create_label(shipment["shipment_id"])

        assert label1["status"] == "label_created"
        assert label2["status"] == "label_created"

    async def test_cancel_with_label_refunds_shipping(self, fulfillment_svc):
        """Cancel after label → refund_shipping should be True."""
        items = FulfillmentFactory.items()
        address = FulfillmentFactory.shipping_address()

        shipment = await fulfillment_svc.create_shipment(
            order_id="ord_refund", items=items, address=address,
        )
        await fulfillment_svc.create_label(shipment["shipment_id"])

        cancel = await fulfillment_svc.cancel_shipment(shipment["shipment_id"])

        assert cancel["refund_shipping"] is True

    async def test_double_commit_fails(self, inventory_svc):
        """Committing the same reservation twice should fail on second attempt."""
        items = [{"sku_id": "sku_dbl", "quantity": 1}]
        order_id = InventoryFactory.order_id()

        res = await inventory_svc.reserve_inventory(
            order_id=order_id, items=items,
        )

        await inventory_svc.commit_reservation(
            order_id=order_id, reservation_id=res["reservation_id"],
        )

        with pytest.raises(LookupError):
            await inventory_svc.commit_reservation(
                order_id=order_id, reservation_id=res["reservation_id"],
            )
