"""
L2 Component Tests — Inventory Service

Tests service business logic with mocked repository and event bus.
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
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    return AsyncMock()


@pytest.fixture
def service(mock_repository, mock_event_bus):
    return InventoryService(repository=mock_repository, event_bus=mock_event_bus)


# ============================================================================
# Service Initialization
# ============================================================================

@pytest.mark.component
class TestInventoryServiceInit:

    def test_initializes_with_all_deps(self, mock_repository, mock_event_bus):
        svc = InventoryService(repository=mock_repository, event_bus=mock_event_bus)
        assert svc.repository is mock_repository
        assert svc.event_bus is mock_event_bus

    def test_initializes_without_event_bus(self, mock_repository):
        svc = InventoryService(repository=mock_repository)
        assert svc.event_bus is None


# ============================================================================
# reserve_inventory
# ============================================================================

@pytest.mark.component
class TestReserveInventory:

    async def test_reserves_successfully(self, service, mock_repository):
        req = InventoryFactory.reserve_request()
        expires = datetime.now(timezone.utc) + timedelta(minutes=30)
        mock_repository.create_reservation.return_value = {
            "reservation_id": "res_001",
            "expires_at": expires,
        }

        result = await service.reserve_inventory(
            order_id=req["order_id"], items=req["items"], user_id=req["user_id"],
        )

        assert result["reservation_id"] == "res_001"
        assert result["status"] == "active"
        assert result["expires_at"] == expires

    async def test_calls_repository_with_30_min_expiry(self, service, mock_repository):
        req = InventoryFactory.reserve_request()
        mock_repository.create_reservation.return_value = {
            "reservation_id": "res_x", "expires_at": datetime.now(timezone.utc),
        }

        await service.reserve_inventory(
            order_id=req["order_id"], items=req["items"],
        )

        call_kwargs = mock_repository.create_reservation.call_args.kwargs
        assert call_kwargs["expires_in_minutes"] == 30

    async def test_publishes_stock_reserved_event(self, service, mock_repository, mock_event_bus):
        items = [{"sku_id": "sku_1", "quantity": 2, "unit_price": 10.0}]
        mock_repository.create_reservation.return_value = {
            "reservation_id": "res_e",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        }

        await service.reserve_inventory(order_id="ord_1", items=items, user_id="usr_1")

        mock_event_bus.publish_event.assert_called_once()

    async def test_no_event_when_items_have_no_identifiers(self, service, mock_repository, mock_event_bus):
        items = [{"name": "Widget"}]
        mock_repository.create_reservation.return_value = {
            "reservation_id": "res_n",
            "expires_at": datetime.now(timezone.utc),
        }

        await service.reserve_inventory(order_id="ord_1", items=items)

        mock_event_bus.publish_event.assert_not_called()

    async def test_raises_value_error_missing_order_id(self, service):
        with pytest.raises(ValueError, match="order_id.*required"):
            await service.reserve_inventory(order_id="", items=[{"sku_id": "a"}])

    async def test_raises_value_error_missing_items(self, service):
        with pytest.raises(ValueError, match="items.*required"):
            await service.reserve_inventory(order_id="ord_1", items=[])

    async def test_default_user_id(self, service, mock_repository):
        mock_repository.create_reservation.return_value = {
            "reservation_id": "res_d", "expires_at": datetime.now(timezone.utc),
        }

        await service.reserve_inventory(order_id="ord_1", items=[{"sku_id": "a"}])

        call_kwargs = mock_repository.create_reservation.call_args.kwargs
        assert call_kwargs["user_id"] == "unknown"


# ============================================================================
# commit_reservation
# ============================================================================

@pytest.mark.component
class TestCommitReservation:

    async def test_commits_by_reservation_id(self, service, mock_repository):
        mock_repository.get_reservation.return_value = {
            "reservation_id": "res_1",
            "order_id": "ord_1",
            "user_id": "usr_1",
            "items": [{"sku_id": "s1", "quantity": 1}],
        }

        result = await service.commit_reservation(
            order_id="ord_1", reservation_id="res_1",
        )

        assert result["status"] == "committed"
        assert result["reservation_id"] == "res_1"
        mock_repository.commit_reservation.assert_called_once_with("res_1")

    async def test_commits_by_order_id_fallback(self, service, mock_repository):
        mock_repository.get_reservation.return_value = None
        mock_repository.get_active_reservation_for_order.return_value = {
            "reservation_id": "res_2",
            "order_id": "ord_1",
            "user_id": "usr_1",
            "items": [],
        }

        result = await service.commit_reservation(order_id="ord_1")

        assert result["reservation_id"] == "res_2"

    async def test_raises_lookup_error_not_found(self, service, mock_repository):
        mock_repository.get_reservation.return_value = None
        mock_repository.get_active_reservation_for_order.return_value = None

        with pytest.raises(LookupError, match="No active reservation"):
            await service.commit_reservation(order_id="ord_1", reservation_id="res_x")

    async def test_raises_value_error_missing_order_id(self, service):
        with pytest.raises(ValueError, match="order_id.*required"):
            await service.commit_reservation(order_id="")

    async def test_publishes_committed_event(self, service, mock_repository, mock_event_bus):
        mock_repository.get_reservation.return_value = {
            "reservation_id": "res_1",
            "order_id": "ord_1",
            "user_id": "usr_1",
            "items": [{"sku_id": "s1", "quantity": 1}],
        }

        await service.commit_reservation(order_id="ord_1", reservation_id="res_1")

        mock_event_bus.publish_event.assert_called_once()


# ============================================================================
# release_reservation
# ============================================================================

@pytest.mark.component
class TestReleaseReservation:

    async def test_releases_existing_reservation(self, service, mock_repository):
        mock_repository.get_reservation.return_value = {
            "reservation_id": "res_1",
            "order_id": "ord_1",
            "user_id": "usr_1",
            "items": [{"sku_id": "s1", "quantity": 1}],
        }

        result = await service.release_reservation(
            order_id="ord_1", reservation_id="res_1",
        )

        assert result["status"] == "released"
        mock_repository.release_reservation.assert_called_once_with("res_1")

    async def test_graceful_when_no_reservation(self, service, mock_repository):
        mock_repository.get_reservation.return_value = None
        mock_repository.get_active_reservation_for_order.return_value = None

        result = await service.release_reservation(order_id="ord_1")

        assert result["status"] == "released"
        assert "No active reservation" in result["message"]
        mock_repository.release_reservation.assert_not_called()

    async def test_raises_value_error_missing_order_id(self, service):
        with pytest.raises(ValueError, match="order_id.*required"):
            await service.release_reservation(order_id="")

    async def test_publishes_released_event(self, service, mock_repository, mock_event_bus):
        mock_repository.get_reservation.return_value = {
            "reservation_id": "res_1",
            "order_id": "ord_1",
            "user_id": "usr_1",
            "items": [{"sku_id": "s1", "quantity": 1}],
        }

        await service.release_reservation(order_id="ord_1", reservation_id="res_1")

        mock_event_bus.publish_event.assert_called_once()

    async def test_passes_reason(self, service, mock_repository, mock_event_bus):
        mock_repository.get_reservation.return_value = {
            "reservation_id": "res_1",
            "order_id": "ord_1",
            "user_id": "usr_1",
            "items": [],
        }

        await service.release_reservation(
            order_id="ord_1", reservation_id="res_1", reason="order_canceled",
        )

        mock_repository.release_reservation.assert_called_once()

    async def test_default_reason(self, service, mock_repository):
        mock_repository.get_reservation.return_value = None
        mock_repository.get_active_reservation_for_order.return_value = {
            "reservation_id": "res_1",
            "order_id": "ord_1",
            "user_id": "usr_1",
            "items": [],
        }

        await service.release_reservation(order_id="ord_1")

        mock_repository.release_reservation.assert_called_once()


# ============================================================================
# get_reservation
# ============================================================================

@pytest.mark.component
class TestGetReservation:

    async def test_delegates_to_repository(self, service, mock_repository):
        mock_repository.get_reservation_by_order.return_value = {"reservation_id": "res_1"}

        result = await service.get_reservation("ord_1")

        assert result["reservation_id"] == "res_1"
        mock_repository.get_reservation_by_order.assert_called_once_with("ord_1")

    async def test_returns_none_when_not_found(self, service, mock_repository):
        mock_repository.get_reservation_by_order.return_value = None

        result = await service.get_reservation("ord_missing")

        assert result is None


# ============================================================================
# _find_reservation (internal helper)
# ============================================================================

@pytest.mark.component
class TestFindReservation:

    async def test_finds_by_reservation_id_first(self, service, mock_repository):
        mock_repository.get_reservation.return_value = {"reservation_id": "res_1"}

        result = await service._find_reservation("ord_1", "res_1")

        assert result["reservation_id"] == "res_1"
        mock_repository.get_active_reservation_for_order.assert_not_called()

    async def test_falls_back_to_order_id(self, service, mock_repository):
        mock_repository.get_reservation.return_value = None
        mock_repository.get_active_reservation_for_order.return_value = {"reservation_id": "res_2"}

        result = await service._find_reservation("ord_1", "res_nonexistent")

        assert result["reservation_id"] == "res_2"

    async def test_order_id_only(self, service, mock_repository):
        mock_repository.get_active_reservation_for_order.return_value = {"reservation_id": "res_3"}

        result = await service._find_reservation("ord_1")

        assert result["reservation_id"] == "res_3"
        mock_repository.get_reservation.assert_not_called()

    async def test_returns_none_when_nothing_found(self, service, mock_repository):
        mock_repository.get_reservation.return_value = None
        mock_repository.get_active_reservation_for_order.return_value = None

        result = await service._find_reservation("ord_1", "res_x")

        assert result is None
