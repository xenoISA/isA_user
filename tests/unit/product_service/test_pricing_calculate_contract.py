from __future__ import annotations

from decimal import Decimal

import pytest

from microservices.product_service.models import Currency, Product, ProductType
from microservices.product_service.product_service import ProductService


def _make_product(
    *,
    product_id: str = "advanced_agent",
    base_price: str = "0.50",
    billing_interval: str = "per_execution",
) -> Product:
    return Product(
        product_id=product_id,
        category_id="ai_agents",
        name="Advanced Agent",
        product_type=ProductType.AGENT_EXECUTION,
        base_price=Decimal(base_price),
        currency=Currency.USD,
        billing_interval=billing_interval,
        is_active=True,
    )


class FakeProductRepository:
    def __init__(self, product: Product, pricing_rows: list[dict]):
        self.product = product
        self.pricing_rows = pricing_rows

    async def get_product(self, product_id: str):
        if self.product.product_id != product_id:
            return None
        return self.product

    async def get_product_pricing_rows(self, product_id: str):
        if self.product.product_id != product_id:
            return []
        return self.pricing_rows


@pytest.mark.asyncio
async def test_calculate_price_uses_matching_pricing_tier():
    repository = FakeProductRepository(
        product=_make_product(),
        pricing_rows=[
            {
                "pricing_id": "pricing_agent_base",
                "tier_name": "base",
                "min_quantity": 0,
                "max_quantity": 1000,
                "unit_price": 0.50,
                "currency": "USD",
                "metadata": {"unit": "execution"},
            },
            {
                "pricing_id": "pricing_agent_enterprise",
                "tier_name": "enterprise",
                "min_quantity": 1001,
                "max_quantity": None,
                "unit_price": 0.40,
                "currency": "USD",
                "metadata": {"unit": "execution"},
            },
        ],
    )
    service = ProductService(repository=repository, event_bus=None)

    result = await service.calculate_price(
        product_id="advanced_agent",
        quantity=Decimal("1500"),
        unit_type="execution",
        tier_code="enterprise",
    )

    assert result["success"] is True
    assert result["pricing_found"] is True
    assert result["pricing_model_id"] == "pricing_agent_enterprise"
    assert result["tier_name"] == "enterprise"
    assert result["unit_price"] == Decimal("0.4")
    assert result["total_price"] == Decimal("600.00000000")
    assert result["metadata"]["tier_code"] == "enterprise"


@pytest.mark.asyncio
async def test_calculate_price_falls_back_to_product_base_price():
    repository = FakeProductRepository(
        product=_make_product(product_id="gpt-4o-mini", base_price="0.00015", billing_interval="per_token"),
        pricing_rows=[],
    )
    service = ProductService(repository=repository, event_bus=None)

    result = await service.calculate_price(
        product_id="gpt-4o-mini",
        quantity=Decimal("1000"),
        unit_type=None,
        tier_code=None,
    )

    assert result["success"] is True
    assert result["pricing_found"] is False
    assert result["unit_type"] == "token"
    assert result["unit_price"] == Decimal("0.00015")
    assert result["total_price"] == Decimal("0.15000000")
    assert result["metadata"]["fallback"] is True
