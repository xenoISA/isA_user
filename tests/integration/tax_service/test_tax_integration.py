"""
L3 Integration Tests — Tax Service

Tests service layer with stateful mock repository + event capture.
Verifies end-to-end business flows within the service boundary.
"""

import pytest
from unittest.mock import AsyncMock

from tests.contracts.tax.data_contract import TaxFactory
from microservices.tax_service.tax_service import TaxService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def stateful_repository():
    """Repository mock that tracks calculation state."""
    repo = AsyncMock()
    repo._calculations = {}
    repo._counter = 0

    async def create_calculation(**kwargs):
        repo._counter += 1
        calc_id = f"calc_int_{repo._counter}"
        calculation = {
            "calculation_id": calc_id,
            "order_id": kwargs["order_id"],
            "user_id": kwargs["user_id"],
            "subtotal": kwargs["subtotal"],
            "total_tax": kwargs["total_tax"],
            "currency": kwargs.get("currency", "USD"),
            "tax_lines": kwargs.get("tax_lines", []),
            "shipping_address": kwargs.get("shipping_address"),
        }
        repo._calculations[kwargs["order_id"]] = calculation
        return calculation

    async def get_calculation_by_order(order_id):
        return repo._calculations.get(order_id)

    repo.create_calculation = create_calculation
    repo.get_calculation_by_order = get_calculation_by_order
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
def mock_provider():
    provider = AsyncMock()

    async def fresh_calculate(**kwargs):
        return {
            "currency": kwargs.get("currency", "USD"),
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

    provider.calculate = AsyncMock(side_effect=fresh_calculate)
    return provider


@pytest.fixture
def service(stateful_repository, capturing_event_bus, mock_provider):
    return TaxService(
        repository=stateful_repository,
        event_bus=capturing_event_bus,
        provider=mock_provider,
    )


# ============================================================================
# Full lifecycle flows
# ============================================================================

@pytest.mark.integration
class TestTaxCalculationLifecycle:

    async def test_calculate_and_retrieve(self, service):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()
        order_id = TaxFactory.order_id()

        calc = await service.calculate_tax(
            items=items, address=address, order_id=order_id,
        )

        retrieved = await service.get_calculation(order_id)

        assert retrieved is not None
        assert retrieved["calculation_id"] == calc["calculation_id"]
        assert retrieved["total_tax"] == 8.75

    async def test_preview_not_retrievable(self, service):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()

        await service.calculate_tax(items=items, address=address)

        result = await service.get_calculation("ord_not_stored")
        assert result is None

    async def test_recalculate_overwrites_previous(self, service, stateful_repository, mock_provider):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()
        order_id = TaxFactory.order_id()

        await service.calculate_tax(
            items=items, address=address, order_id=order_id,
        )

        async def return_new_tax(**kwargs):
            return {"currency": "USD", "total_tax": 15.50, "lines": []}

        mock_provider.calculate.side_effect = return_new_tax

        await service.calculate_tax(
            items=items, address=address, order_id=order_id,
        )

        retrieved = await service.get_calculation(order_id)
        assert retrieved["total_tax"] == 15.50

    async def test_multiple_orders_independent(self, service):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()
        order_a = TaxFactory.order_id()
        order_b = TaxFactory.order_id()

        calc_a = await service.calculate_tax(
            items=items, address=address, order_id=order_a,
        )
        calc_b = await service.calculate_tax(
            items=items, address=address, order_id=order_b,
        )

        assert calc_a["calculation_id"] != calc_b["calculation_id"]


# ============================================================================
# Event verification
# ============================================================================

@pytest.mark.integration
class TestTaxEvents:

    async def test_persisted_calc_publishes_event(self, service, capturing_event_bus):
        await service.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            order_id="ord_e",
            user_id="usr_1",
        )

        assert len(capturing_event_bus.published_events) == 1
        event = capturing_event_bus.published_events[0]
        assert event.type == "tax.calculated"

    async def test_preview_does_not_publish(self, service, capturing_event_bus):
        await service.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
        )

        assert len(capturing_event_bus.published_events) == 0

    async def test_recalculate_publishes_two_events(self, service, capturing_event_bus):
        items = TaxFactory.items()
        address = TaxFactory.shipping_address()
        order_id = TaxFactory.order_id()

        await service.calculate_tax(items=items, address=address, order_id=order_id)
        await service.calculate_tax(items=items, address=address, order_id=order_id)

        assert len(capturing_event_bus.published_events) == 2


# ============================================================================
# Provider integration
# ============================================================================

@pytest.mark.integration
class TestTaxProviderIntegration:

    async def test_zero_tax_provider(self, stateful_repository, capturing_event_bus):
        zero_provider = AsyncMock()

        async def zero_calc(**kwargs):
            return {"currency": "USD", "total_tax": 0.0, "lines": []}

        zero_provider.calculate = AsyncMock(side_effect=zero_calc)
        svc = TaxService(
            repository=stateful_repository,
            event_bus=capturing_event_bus,
            provider=zero_provider,
        )

        result = await svc.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            order_id="ord_zero",
        )

        assert result["total_tax"] == 0.0

    async def test_multi_line_tax(self, stateful_repository, capturing_event_bus):
        multi_provider = AsyncMock()

        async def multi_calc(**kwargs):
            return {
                "currency": "USD",
                "total_tax": 15.0,
                "lines": [
                    {"line_item_id": "li_1", "tax_amount": 5.0, "rate": 0.05},
                    {"line_item_id": "li_2", "tax_amount": 10.0, "rate": 0.10},
                ],
            }

        multi_provider.calculate = AsyncMock(side_effect=multi_calc)
        svc = TaxService(
            repository=stateful_repository,
            event_bus=capturing_event_bus,
            provider=multi_provider,
        )

        result = await svc.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            order_id="ord_multi",
        )

        assert result["total_tax"] == 15.0
        assert len(result["lines"]) == 2

    async def test_currency_passed_through(self, service, mock_provider):
        await service.calculate_tax(
            items=TaxFactory.items(),
            address=TaxFactory.shipping_address(),
            currency="EUR",
        )

        call_kwargs = mock_provider.calculate.call_args.kwargs
        assert call_kwargs["currency"] == "EUR"
