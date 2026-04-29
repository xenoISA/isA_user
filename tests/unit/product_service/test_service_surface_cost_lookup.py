from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from microservices.product_service.models import Currency, Product, ProductType
from microservices.product_service.product_service import ProductService


@pytest.mark.asyncio
async def test_lookup_cost_uses_product_id_as_service_surface_and_returns_runtime_components():
    repository = AsyncMock()
    repository.get_cost_definitions = AsyncMock(
        return_value=[
            {
                "cost_id": "cost_local_gpu_input",
                "product_id": "local-gpu",
                "service_type": "model_inference",
                "provider": "vllm",
                "model_name": None,
                "operation_type": "input",
                "cost_per_unit": 52,
                "unit_type": "token",
                "unit_size": 1000,
                "free_tier_limit": 0,
                "free_tier_period": "monthly",
                "metadata": {
                    "service_surface": "local-gpu",
                    "backend": "local_gpu",
                    "engine_used": "vllm",
                },
            },
            {
                "cost_id": "cost_local_gpu_output",
                "product_id": "local-gpu",
                "service_type": "model_inference",
                "provider": "vllm",
                "model_name": None,
                "operation_type": "output",
                "cost_per_unit": 208,
                "unit_type": "token",
                "unit_size": 1000,
                "free_tier_limit": 0,
                "free_tier_period": "monthly",
                "metadata": {
                    "service_surface": "local-gpu",
                    "backend": "local_gpu",
                    "engine_used": "vllm",
                },
            },
            {
                "cost_id": "cost_local_gpu_runtime",
                "product_id": "local-gpu",
                "service_type": "model_inference",
                "provider": "vllm",
                "model_name": None,
                "operation_type": "gpu_seconds",
                "cost_per_unit": 22,
                "unit_type": "second",
                "unit_size": 1,
                "free_tier_limit": 0,
                "free_tier_period": "monthly",
                "metadata": {
                    "service_surface": "local-gpu",
                    "backend": "local_gpu",
                    "engine_used": "vllm",
                    "tenancy_mode": "shared",
                },
            },
            {
                "cost_id": "cost_local_gpu_prefill",
                "product_id": "local-gpu",
                "service_type": "model_inference",
                "provider": None,
                "model_name": None,
                "operation_type": "prefill_seconds",
                "cost_per_unit": 10,
                "unit_type": "second",
                "unit_size": 1,
                "free_tier_limit": 0,
                "free_tier_period": "monthly",
                "metadata": {
                    "service_surface": "local-gpu",
                    "backend": "local_gpu",
                    "tenancy_mode": "shared",
                },
            },
            {
                "cost_id": "cost_cloud_gpu_input",
                "product_id": "cloud-gpu",
                "service_type": "model_inference",
                "provider": None,
                "model_name": None,
                "operation_type": "input",
                "cost_per_unit": 65,
                "unit_type": "token",
                "unit_size": 1000,
                "free_tier_limit": 0,
                "free_tier_period": "monthly",
                "metadata": {
                    "service_surface": "cloud-gpu",
                    "backend": "modal",
                    "tenancy_mode": "shared",
                },
            },
        ]
    )
    service = ProductService(repository=repository)

    result = await service.lookup_cost(
        service_type="model_inference",
        product_id="local-gpu",
        provider="vllm",
        backend="local_gpu",
        engine_used="vllm",
        gpu_count=1,
        prefill_seconds=0.4,
        generation_seconds=1.25,
        tenancy_mode="shared",
    )

    assert result["success"] is True
    assert result["cost_definition"]["product_id"] == "local-gpu"
    assert result["input_cost_per_unit"] == 52
    assert result["output_cost_per_unit"] == 208
    assert result["hybrid_pricing_available"] is True
    assert [item["cost_id"] for item in result["runtime_cost_components"]] == [
        "cost_local_gpu_runtime",
        "cost_local_gpu_prefill",
    ]
    assert result["runtime_pricing_context"]["service_surface"] == "local-gpu"
    assert result["runtime_pricing_context"]["backend"] == "local_gpu"
    assert result["runtime_pricing_context"]["engine_used"] == "vllm"


class ProductBackedLookupRepository:
    def __init__(self, product: Product, pricing_rows: list[dict]):
        self.product = product
        self.pricing_rows = pricing_rows

    async def get_cost_definitions(self, **_: object):
        return []

    async def get_product(self, product_id: str):
        if product_id != self.product.product_id:
            return None
        return self.product

    async def get_product_pricing_rows(self, product_id: str):
        if product_id != self.product.product_id:
            return []
        return self.pricing_rows


@pytest.mark.asyncio
async def test_lookup_cost_falls_back_to_product_backed_pricing():
    product = Product(
        product_id="gpu_training_job",
        category_id="compute",
        name="GPU Training Job",
        product_type=ProductType.COMPUTATION,
        base_price=Decimal("0.0030"),
        currency=Currency.USD,
        billing_interval="per_second",
        is_active=True,
        metadata={
            "service_type": "gpu_training",
            "operation_type": "gpu_seconds",
        },
    )
    repository = ProductBackedLookupRepository(
        product=product,
        pricing_rows=[
            {
                "pricing_id": "pricing_gpu_training_default",
                "tier_name": "default",
                "min_quantity": 0,
                "max_quantity": None,
                "unit_price": 0.0030,
                "currency": "USD",
                "metadata": {
                    "unit": "second",
                    "meter_type": "gpu_seconds",
                },
            }
        ],
    )
    service = ProductService(repository=repository)

    result = await service.lookup_cost(
        service_type="gpu_training",
        product_id="gpu_training_job",
        unit_type="second",
        meter_type="gpu_seconds",
    )

    assert result["success"] is True
    assert result["product_backed_pricing"] is True
    assert result["pricing_model_id"] == "pricing_gpu_training_default"
    assert result["tier_name"] == "default"
    assert result["cost_definition"]["product_id"] == "gpu_training_job"
    assert result["cost_definition"]["operation_type"] == "gpu_seconds"
    assert result["cost_definition"]["unit_type"] == "second"
