from unittest.mock import AsyncMock

import pytest

from microservices.product_service.product_service import ProductService


@pytest.mark.unit
class TestCostLookupCompatibility:
    @pytest.mark.asyncio
    async def test_lookup_cost_combines_model_input_and_output_rows(self):
        repository = AsyncMock()
        repository.get_cost_definitions = AsyncMock(
            return_value=[
                {
                    "cost_id": "cost_input",
                    "service_type": "model_inference",
                    "provider": "openai",
                    "model_name": "gpt-4o-mini",
                    "operation_type": "input",
                    "cost_per_unit": 15,
                    "unit_type": "token",
                    "unit_size": 1000000,
                    "free_tier_limit": 0,
                    "free_tier_period": "monthly",
                },
                {
                    "cost_id": "cost_output",
                    "service_type": "model_inference",
                    "provider": "openai",
                    "model_name": "gpt-4o-mini",
                    "operation_type": "output",
                    "cost_per_unit": 60,
                    "unit_type": "token",
                    "unit_size": 1000000,
                    "free_tier_limit": 0,
                    "free_tier_period": "monthly",
                },
            ]
        )
        service = ProductService(repository)

        result = await service.lookup_cost(
            service_type="model_inference",
            provider="openai",
            model_name="gpt-4o-mini",
            operation_type="chat",
        )

        assert result["success"] is True
        assert result["input_cost_per_unit"] == 15
        assert result["output_cost_per_unit"] == 60
        assert result["unit_type"] == "token"

    @pytest.mark.asyncio
    async def test_lookup_cost_uses_tool_name_alias_for_mcp_tools(self):
        repository = AsyncMock()
        repository.get_cost_definitions = AsyncMock(
            return_value=[
                {
                    "cost_id": "cost_mcp_web_search",
                    "service_type": "mcp_service",
                    "provider": "external",
                    "model_name": "web_search",
                    "operation_type": "request",
                    "cost_per_unit": 300,
                    "unit_type": "request",
                    "unit_size": 1,
                    "free_tier_limit": 100,
                    "free_tier_period": "monthly",
                }
            ]
        )
        service = ProductService(repository)

        result = await service.lookup_cost(
            service_type="mcp_service",
            tool_name="web_search",
            operation_type="tool_call",
        )

        assert result["success"] is True
        assert result["cost_per_unit"] == 300
        assert result["cost_definition"]["model_name"] == "web_search"
