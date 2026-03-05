"""
L2 Component Tests — Tax Service

Tests service business logic with mocked repository, event bus, and provider.
"""

import pytest
from unittest.mock import AsyncMock

from tests.contracts.tax.data_contract import TaxFactory
from microservices.tax_service.tax_service import TaxService


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
def mock_provider():
    provider = AsyncMock()
    provider.calculate.return_value = {
        "currency": "USD",
        "total_tax": 8.75,
        "lines": [
            {
                "line_item_id": "li_1",
                "sku_id": "sku_1",
                "tax_amount": 8.75,
                "rate": 0.0875,
                "jurisdiction": "CA",
            }
        ],
    }
    return provider


@pytest.fixture
def service(mock_repository, mock_event_bus, mock_provider):
    return TaxService(
        repository=mock_repository,
        event_bus=mock_event_bus,
        provider=mock_provider,
    )


# ============================================================================
# Service Initialization
# ============================================================================

@pytest.mark.component
class TestTaxServiceInit:

    def test_initializes_with_all_deps(self, mock_repository, mock_event_bus, mock_provider):
        svc = TaxService(
            repository=mock_repository, event_bus=mock_event_bus, provider=mock_provider
        )
        assert svc.repository is mock_repository
        assert svc.event_bus is mock_event_bus
        assert svc.provider is mock_provider

    def test_initializes_without_event_bus(self, mock_repository, mock_provider):
        svc = TaxService(repository=mock_repository, provider=mock_provider)
        assert svc.event_bus is None

    def test_initializes_without_provider(self, mock_repository, mock_event_bus):
        svc = TaxService(repository=mock_repository, event_bus=mock_event_bus)
        assert svc.provider is None


# ============================================================================
# calculate_tax — preview (no order_id)
# ============================================================================

@pytest.mark.component
class TestCalculateTaxPreview:

    async def test_preview_returns_provider_result(self, service, mock_provider):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()

        result = await service.calculate_tax(items=items, address=address)

        assert result["total_tax"] == 8.75
        assert result["currency"] == "USD"
        mock_provider.calculate.assert_called_once()

    async def test_preview_does_not_persist(self, service, mock_repository):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()

        await service.calculate_tax(items=items, address=address)

        mock_repository.create_calculation.assert_not_called()

    async def test_preview_does_not_publish_event(self, service, mock_event_bus):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()

        await service.calculate_tax(items=items, address=address)

        mock_event_bus.publish_event.assert_not_called()

    async def test_preview_no_calculation_id_in_result(self, service):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()

        result = await service.calculate_tax(items=items, address=address)

        assert "calculation_id" not in result
        assert "order_id" not in result


# ============================================================================
# calculate_tax — persisted (with order_id)
# ============================================================================

@pytest.mark.component
class TestCalculateTaxPersisted:

    async def test_persists_when_order_id_provided(self, service, mock_repository):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()
        order_id = TaxFactory.order_id()
        mock_repository.create_calculation.return_value = {
            "calculation_id": "calc_001",
        }

        result = await service.calculate_tax(
            items=items, address=address, order_id=order_id,
        )

        assert result["calculation_id"] == "calc_001"
        assert result["order_id"] == order_id
        mock_repository.create_calculation.assert_called_once()

    async def test_passes_subtotal_to_repository(self, service, mock_repository):
        items = [{"unit_price": 10.0, "quantity": 3}]
        address = TaxFactory.shipping_address()
        mock_repository.create_calculation.return_value = {"calculation_id": "calc_x"}

        await service.calculate_tax(
            items=items, address=address, order_id="ord_1",
        )

        call_kwargs = mock_repository.create_calculation.call_args.kwargs
        assert call_kwargs["subtotal"] == 30.0

    async def test_passes_total_tax_from_provider(self, service, mock_repository, mock_provider):
        mock_provider.calculate.return_value = {"total_tax": 12.50, "lines": []}
        mock_repository.create_calculation.return_value = {"calculation_id": "calc_x"}

        await service.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            order_id="ord_1",
        )

        call_kwargs = mock_repository.create_calculation.call_args.kwargs
        assert call_kwargs["total_tax"] == 12.50

    async def test_publishes_tax_calculated_event(self, service, mock_repository, mock_event_bus):
        mock_repository.create_calculation.return_value = {"calculation_id": "calc_e"}

        await service.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            order_id="ord_1",
            user_id="usr_1",
        )

        mock_event_bus.publish_event.assert_called_once()

    async def test_passes_currency(self, service, mock_repository, mock_provider):
        mock_repository.create_calculation.return_value = {"calculation_id": "calc_c"}

        await service.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            order_id="ord_1",
            currency="EUR",
        )

        call_kwargs = mock_provider.calculate.call_args.kwargs
        assert call_kwargs["currency"] == "EUR"

    async def test_default_user_id(self, service, mock_repository):
        mock_repository.create_calculation.return_value = {"calculation_id": "calc_d"}

        await service.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            order_id="ord_1",
        )

        call_kwargs = mock_repository.create_calculation.call_args.kwargs
        assert call_kwargs["user_id"] == "unknown"


# ============================================================================
# calculate_tax — validation
# ============================================================================

@pytest.mark.component
class TestCalculateTaxValidation:

    async def test_raises_value_error_missing_items(self, service):
        with pytest.raises(ValueError, match="items.*required"):
            await service.calculate_tax(
                items=[], address=TaxFactory.shipping_address(),
            )

    async def test_raises_value_error_missing_address(self, service):
        with pytest.raises(ValueError, match="address.*required"):
            await service.calculate_tax(
                items=TaxFactory.items(), address={},
            )


# ============================================================================
# get_calculation
# ============================================================================

@pytest.mark.component
class TestGetCalculation:

    async def test_delegates_to_repository(self, service, mock_repository):
        mock_repository.get_calculation_by_order.return_value = {
            "calculation_id": "calc_1",
        }

        result = await service.get_calculation("ord_1")

        assert result["calculation_id"] == "calc_1"
        mock_repository.get_calculation_by_order.assert_called_once_with("ord_1")

    async def test_returns_none_when_not_found(self, service, mock_repository):
        mock_repository.get_calculation_by_order.return_value = None

        result = await service.get_calculation("ord_missing")

        assert result is None
