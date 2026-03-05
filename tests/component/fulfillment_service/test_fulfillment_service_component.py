"""
L2 Component Tests — Fulfillment Service

Tests service business logic with mocked repository, event bus, and provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from tests.contracts.fulfillment.data_contract import FulfillmentFactory
from microservices.fulfillment_service.fulfillment_service import FulfillmentService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_event_bus():
    bus = AsyncMock()
    return bus


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.create_shipment.return_value = {
        "shipment_id": "shp_mock",
        "tracking_number": "trk_mock123",
        "status": "created",
    }
    return provider


@pytest.fixture
def service(mock_repository, mock_event_bus, mock_provider):
    return FulfillmentService(
        repository=mock_repository,
        event_bus=mock_event_bus,
        provider=mock_provider,
    )


# ============================================================================
# Service Initialization
# ============================================================================

@pytest.mark.component
class TestFulfillmentServiceInit:

    def test_initializes_with_all_deps(self, mock_repository, mock_event_bus, mock_provider):
        svc = FulfillmentService(
            repository=mock_repository, event_bus=mock_event_bus, provider=mock_provider
        )
        assert svc.repository is mock_repository
        assert svc.event_bus is mock_event_bus
        assert svc.provider is mock_provider

    def test_initializes_without_event_bus(self, mock_repository, mock_provider):
        svc = FulfillmentService(repository=mock_repository, provider=mock_provider)
        assert svc.event_bus is None

    def test_initializes_without_provider(self, mock_repository, mock_event_bus):
        svc = FulfillmentService(repository=mock_repository, event_bus=mock_event_bus)
        assert svc.provider is None


# ============================================================================
# create_shipment
# ============================================================================

@pytest.mark.component
class TestCreateShipment:

    async def test_creates_shipment_successfully(self, service, mock_repository):
        req = FulfillmentFactory.create_shipment_request()
        mock_repository.create_shipment.return_value = {
            "shipment_id": "shp_001",
            "order_id": req["order_id"],
        }

        result = await service.create_shipment(
            order_id=req["order_id"],
            items=req["items"],
            address=req["address"],
            user_id=req["user_id"],
        )

        assert result["shipment_id"] == "shp_001"
        assert result["status"] == "created"
        assert result["order_id"] == req["order_id"]
        mock_repository.create_shipment.assert_called_once()

    async def test_calls_provider_before_repository(self, service, mock_provider, mock_repository):
        req = FulfillmentFactory.create_shipment_request()
        mock_repository.create_shipment.return_value = {"shipment_id": "shp_x"}

        await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"], user_id=req["user_id"],
        )

        mock_provider.create_shipment.assert_called_once()

    async def test_passes_tracking_number_from_provider(self, service, mock_provider, mock_repository):
        mock_provider.create_shipment.return_value = {"tracking_number": "trk_prov"}
        mock_repository.create_shipment.return_value = {"shipment_id": "shp_x"}
        req = FulfillmentFactory.create_shipment_request()

        result = await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"],
        )

        assert result["tracking_number"] == "trk_prov"

    async def test_publishes_shipment_prepared_event(self, service, mock_repository, mock_event_bus):
        req = FulfillmentFactory.create_shipment_request()
        mock_repository.create_shipment.return_value = {"shipment_id": "shp_e"}

        await service.create_shipment(
            order_id=req["order_id"], items=req["items"],
            address=req["address"], user_id=req["user_id"],
        )

        mock_event_bus.publish_event.assert_called_once()

    async def test_raises_value_error_missing_order_id(self, service):
        with pytest.raises(ValueError, match="order_id.*required"):
            await service.create_shipment(
                order_id="", items=[{"sku_id": "a"}],
                address={"city": "SF"},
            )

    async def test_raises_value_error_missing_items(self, service):
        with pytest.raises(ValueError, match="items.*required"):
            await service.create_shipment(
                order_id="ord_1", items=[], address={"city": "SF"},
            )

    async def test_raises_value_error_missing_address(self, service):
        with pytest.raises(ValueError, match="address.*required"):
            await service.create_shipment(
                order_id="ord_1", items=[{"sku_id": "a"}], address={},
            )

    async def test_default_user_id_is_unknown(self, service, mock_repository):
        mock_repository.create_shipment.return_value = {"shipment_id": "shp_d"}
        req = FulfillmentFactory.create_shipment_request()

        await service.create_shipment(
            order_id=req["order_id"], items=req["items"], address=req["address"],
        )

        call_kwargs = mock_repository.create_shipment.call_args.kwargs
        assert call_kwargs["user_id"] == "unknown"


# ============================================================================
# create_label
# ============================================================================

@pytest.mark.component
class TestCreateLabel:

    async def test_creates_label_for_existing_shipment(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "user_id": "usr_1",
        }

        result = await service.create_label("shp_1")

        assert result["shipment_id"] == "shp_1"
        assert result["status"] == "label_created"
        assert "tracking_number" in result
        assert result["carrier"] == "USPS"

    async def test_idempotent_returns_existing_label(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "status": "label_purchased",
            "tracking_number": "trk_existing",
            "carrier": "FedEx",
            "label_url": "https://example.com/label",
        }

        result = await service.create_label("shp_1")

        assert result["tracking_number"] == "trk_existing"
        assert result["carrier"] == "FedEx"
        mock_repository.create_label.assert_not_called()

    async def test_raises_lookup_error_not_found(self, service, mock_repository):
        mock_repository.get_shipment.return_value = None

        with pytest.raises(LookupError, match="Shipment not found"):
            await service.create_label("shp_nonexistent")

    async def test_publishes_label_created_event(self, service, mock_repository, mock_event_bus):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "user_id": "usr_1",
        }

        await service.create_label("shp_1")

        mock_event_bus.publish_event.assert_called_once()

    async def test_calls_repository_create_label(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "user_id": "usr_1",
        }

        await service.create_label("shp_1")

        mock_repository.create_label.assert_called_once()
        call_kwargs = mock_repository.create_label.call_args.kwargs
        assert call_kwargs["shipment_id"] == "shp_1"
        assert call_kwargs["carrier"] == "USPS"


# ============================================================================
# cancel_shipment
# ============================================================================

@pytest.mark.component
class TestCancelShipment:

    async def test_cancels_created_shipment(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "user_id": "usr_1",
        }

        result = await service.cancel_shipment("shp_1")

        assert result["status"] == "canceled"
        assert result["refund_shipping"] is False

    async def test_refund_shipping_when_label_purchased(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "label_purchased",
            "user_id": "usr_1",
        }

        result = await service.cancel_shipment("shp_1")

        assert result["refund_shipping"] is True

    async def test_idempotent_already_failed(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "failed",
        }

        result = await service.cancel_shipment("shp_1")

        assert result["status"] == "canceled"
        assert result["message"] == "Already canceled"
        mock_repository.cancel_shipment.assert_not_called()

    async def test_raises_lookup_error_not_found(self, service, mock_repository):
        mock_repository.get_shipment.return_value = None

        with pytest.raises(LookupError, match="Shipment not found"):
            await service.cancel_shipment("shp_nonexistent")

    async def test_publishes_canceled_event(self, service, mock_repository, mock_event_bus):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "user_id": "usr_1",
        }

        await service.cancel_shipment("shp_1", reason="customer_request")

        mock_event_bus.publish_event.assert_called_once()

    async def test_passes_reason_to_repository(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "user_id": "usr_1",
        }

        await service.cancel_shipment("shp_1", reason="out_of_stock")

        mock_repository.cancel_shipment.assert_called_once_with("shp_1", reason="out_of_stock")

    async def test_default_reason(self, service, mock_repository):
        mock_repository.get_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "user_id": "usr_1",
        }

        await service.cancel_shipment("shp_1")

        mock_repository.cancel_shipment.assert_called_once_with("shp_1", reason="manual_cancellation")


# ============================================================================
# get_shipment_by_order / get_shipment_by_tracking
# ============================================================================

@pytest.mark.component
class TestGetShipment:

    async def test_get_by_order_delegates_to_repository(self, service, mock_repository):
        mock_repository.get_shipment_by_order.return_value = {"shipment_id": "shp_1"}

        result = await service.get_shipment_by_order("ord_1")

        assert result["shipment_id"] == "shp_1"
        mock_repository.get_shipment_by_order.assert_called_once_with("ord_1")

    async def test_get_by_order_returns_none(self, service, mock_repository):
        mock_repository.get_shipment_by_order.return_value = None

        result = await service.get_shipment_by_order("ord_nonexistent")

        assert result is None

    async def test_get_by_tracking_delegates_to_repository(self, service, mock_repository):
        mock_repository.get_shipment_by_tracking.return_value = {"shipment_id": "shp_1"}

        result = await service.get_shipment_by_tracking("trk_abc")

        assert result["shipment_id"] == "shp_1"
        mock_repository.get_shipment_by_tracking.assert_called_once_with("trk_abc")

    async def test_get_by_tracking_returns_none(self, service, mock_repository):
        mock_repository.get_shipment_by_tracking.return_value = None

        result = await service.get_shipment_by_tracking("trk_nonexistent")

        assert result is None
