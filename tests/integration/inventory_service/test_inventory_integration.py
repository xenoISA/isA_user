"""
L3 Integration Tests — Inventory Service

Tests service layer with stateful mock repository + event capture.
Verifies end-to-end business flows within the service boundary.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone

from tests.contracts.inventory.data_contract import InventoryFactory
from microservices.inventory_service.inventory_service import InventoryService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def stateful_repository():
    """Repository mock that tracks reservation state."""
    repo = AsyncMock()
    repo._reservations = {}
    repo._counter = 0

    async def create_reservation(**kwargs):
        repo._counter += 1
        res_id = f"res_int_{repo._counter}"
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=kwargs.get("expires_in_minutes", 30)
        )
        reservation = {
            "reservation_id": res_id,
            "order_id": kwargs["order_id"],
            "user_id": kwargs["user_id"],
            "items": kwargs["items"],
            "status": "active",
            "expires_at": expires_at,
        }
        repo._reservations[res_id] = reservation
        return reservation

    async def get_reservation(reservation_id):
        r = repo._reservations.get(reservation_id)
        if r and r["status"] == "active":
            return r
        return None

    async def get_reservation_by_order(order_id, status=None):
        for r in repo._reservations.values():
            if r["order_id"] == order_id:
                if status is None or r["status"] == status:
                    return r
        return None

    async def get_active_reservation_for_order(order_id):
        for r in repo._reservations.values():
            if r["order_id"] == order_id and r["status"] == "active":
                return r
        return None

    async def commit_reservation(reservation_id):
        if reservation_id in repo._reservations:
            repo._reservations[reservation_id]["status"] = "committed"
            return repo._reservations[reservation_id]
        return None

    async def release_reservation(reservation_id):
        if reservation_id in repo._reservations:
            repo._reservations[reservation_id]["status"] = "released"
            return repo._reservations[reservation_id]
        return None

    repo.create_reservation = create_reservation
    repo.get_reservation = get_reservation
    repo.get_reservation_by_order = get_reservation_by_order
    repo.get_active_reservation_for_order = get_active_reservation_for_order
    repo.commit_reservation = commit_reservation
    repo.release_reservation = release_reservation
    return repo


@pytest.fixture
def capturing_event_bus():
    bus = AsyncMock()
    bus.published_events = []

    async def capture(event):
        bus.published_events.append(event)

    bus.publish_event = AsyncMock(side_effect=capture)
    return bus


@pytest.fixture
def service(stateful_repository, capturing_event_bus):
    return InventoryService(repository=stateful_repository, event_bus=capturing_event_bus)


# ============================================================================
# Full lifecycle flows
# ============================================================================

@pytest.mark.integration
class TestReservationLifecycle:

    async def test_reserve_then_commit(self, service, capturing_event_bus):
        items = InventoryFactory.items()
        order_id = InventoryFactory.order_id()

        reservation = await service.reserve_inventory(
            order_id=order_id, items=items, user_id="usr_1",
        )

        result = await service.commit_reservation(
            order_id=order_id, reservation_id=reservation["reservation_id"],
        )

        assert result["status"] == "committed"
        assert len(capturing_event_bus.published_events) == 2

    async def test_reserve_then_release(self, service, capturing_event_bus):
        items = InventoryFactory.items()
        order_id = InventoryFactory.order_id()

        reservation = await service.reserve_inventory(
            order_id=order_id, items=items,
        )

        result = await service.release_reservation(
            order_id=order_id, reservation_id=reservation["reservation_id"],
        )

        assert result["status"] == "released"
        assert len(capturing_event_bus.published_events) == 2

    async def test_commit_by_order_id_without_reservation_id(self, service):
        items = InventoryFactory.items()
        order_id = InventoryFactory.order_id()

        await service.reserve_inventory(order_id=order_id, items=items)

        result = await service.commit_reservation(order_id=order_id)

        assert result["status"] == "committed"

    async def test_release_by_order_id_without_reservation_id(self, service):
        items = InventoryFactory.items()
        order_id = InventoryFactory.order_id()

        await service.reserve_inventory(order_id=order_id, items=items)

        result = await service.release_reservation(order_id=order_id)

        assert result["status"] == "released"

    async def test_commit_after_release_fails(self, service):
        items = InventoryFactory.items()
        order_id = InventoryFactory.order_id()

        reservation = await service.reserve_inventory(
            order_id=order_id, items=items,
        )
        await service.release_reservation(
            order_id=order_id, reservation_id=reservation["reservation_id"],
        )

        with pytest.raises(LookupError, match="No active reservation"):
            await service.commit_reservation(
                order_id=order_id, reservation_id=reservation["reservation_id"],
            )

    async def test_release_nonexistent_is_graceful(self, service):
        result = await service.release_reservation(order_id="ord_does_not_exist")

        assert result["status"] == "released"
        assert "No active reservation" in result["message"]


# ============================================================================
# Event verification
# ============================================================================

@pytest.mark.integration
class TestInventoryEvents:

    async def test_reserve_publishes_event(self, service, capturing_event_bus):
        items = [{"sku_id": "sku_1", "quantity": 2, "unit_price": 10.0}]
        await service.reserve_inventory(order_id="ord_e", items=items)

        assert len(capturing_event_bus.published_events) == 1
        event = capturing_event_bus.published_events[0]
        assert event.type == "inventory.reserved"

    async def test_commit_publishes_event(self, service, capturing_event_bus):
        items = [{"sku_id": "sku_1", "quantity": 1}]
        res = await service.reserve_inventory(order_id="ord_c", items=items)
        capturing_event_bus.published_events.clear()

        await service.commit_reservation(
            order_id="ord_c", reservation_id=res["reservation_id"],
        )

        assert len(capturing_event_bus.published_events) == 1
        event = capturing_event_bus.published_events[0]
        assert event.type == "inventory.committed"

    async def test_release_publishes_event(self, service, capturing_event_bus):
        items = [{"sku_id": "sku_1", "quantity": 1}]
        res = await service.reserve_inventory(order_id="ord_r", items=items)
        capturing_event_bus.published_events.clear()

        await service.release_reservation(
            order_id="ord_r", reservation_id=res["reservation_id"],
        )

        assert len(capturing_event_bus.published_events) == 1
        event = capturing_event_bus.published_events[0]
        assert event.type == "inventory.released"

    async def test_release_nonexistent_no_event(self, service, capturing_event_bus):
        await service.release_reservation(order_id="ord_ghost")

        assert len(capturing_event_bus.published_events) == 0


# ============================================================================
# Multiple reservations
# ============================================================================

@pytest.mark.integration
class TestMultipleReservations:

    async def test_two_orders_independent(self, service):
        items = InventoryFactory.items(1)
        res1 = await service.reserve_inventory(order_id="ord_a", items=items)
        res2 = await service.reserve_inventory(order_id="ord_b", items=items)

        assert res1["reservation_id"] != res2["reservation_id"]

    async def test_get_reservation_after_create(self, service):
        items = InventoryFactory.items(1)
        order_id = InventoryFactory.order_id()
        await service.reserve_inventory(order_id=order_id, items=items)

        found = await service.get_reservation(order_id)

        assert found is not None
        assert found["order_id"] == order_id

    async def test_get_reservation_returns_none_for_unknown(self, service):
        result = await service.get_reservation("ord_unknown")
        assert result is None
