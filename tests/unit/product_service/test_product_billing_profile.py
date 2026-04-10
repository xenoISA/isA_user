from decimal import Decimal

import pytest

from microservices.product_service.models import (
    CostComponentType,
    Currency,
    Product,
    ProductBillingProfile,
    ProductCostComponent,
    ProductType,
)
from microservices.product_service.product_service import ProductService


class _Repo:
    def __init__(self, product: Product):
        self.product = product

    async def get_product(self, product_id: str):
        if product_id == self.product.product_id:
            return self.product
        return None

    async def get_product_pricing_rows(self, product_id: str):
        return []


@pytest.mark.unit
def test_product_hydrates_billing_profile_from_metadata():
    product = Product(
        product_id="web_automation",
        category_id="web_services",
        name="Web Automation",
        product_type=ProductType.API_SERVICE,
        base_price=Decimal("0.02"),
        currency=Currency.USD,
        metadata={
            "billing_profile": {
                "billing_surface": "abstract_service",
                "primary_meter": "automation_executions",
                "cost_components": [
                    {
                        "component_id": "browser_api",
                        "component_type": "external_api",
                        "provider": "internal",
                    }
                ],
            }
        },
    )

    assert product.billing_profile.primary_meter == "automation_executions"
    assert product.billing_profile.cost_components[0].component_type == CostComponentType.EXTERNAL_API
    assert product.metadata_for_storage()["billing_profile"]["cost_components"][0]["component_id"] == "browser_api"


@pytest.mark.asyncio
async def test_calculate_price_returns_billing_profile_metadata():
    product = Product(
        product_id="python_repl_execution",
        category_id="developer_tools",
        name="Python REPL Execution",
        product_type=ProductType.COMPUTATION,
        base_price=Decimal("0.005"),
        currency=Currency.USD,
        billing_interval="per_execution",
        billing_profile=ProductBillingProfile(
            primary_meter="execution_count",
            cost_components=[
                ProductCostComponent(
                    component_id="sandbox_runtime",
                    component_type=CostComponentType.RUNTIME,
                )
            ],
        ),
    )
    service = ProductService(repository=_Repo(product), event_bus=None)

    result = await service.calculate_price(
        product_id="python_repl_execution",
        quantity=Decimal("2"),
        unit_type="execution",
        tier_code=None,
    )

    assert result["success"] is True
    assert result["metadata"]["billing_profile"]["primary_meter"] == "execution_count"
    assert (
        result["metadata"]["billing_profile"]["cost_components"][0]["component_type"]
        == "runtime"
    )
