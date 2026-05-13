from unittest.mock import AsyncMock

import pytest

from microservices.memory_service.events.publishers import (
    publish_billing_usage_recorded,
)
from microservices.memory_service.memory_service import MemoryService


@pytest.mark.asyncio
async def test_memory_billing_usage_publisher_emits_canonical_vector_event():
    event_bus = AsyncMock()

    result = await publish_billing_usage_recorded(
        event_bus,
        user_id="user_123",
        product_id="memory_vector_query",
        usage_amount=1,
        unit_type="request",
        operation_type="vector_query",
        resource_name="factual",
        usage_details={"memory_type": "factual", "result_count": 3},
    )

    assert result is True
    event = event_bus.publish_event.call_args.args[0]
    assert event.type == "billing.usage.recorded.vector_query"
    assert event.source == "memory_service"
    assert event.data["service_type"] == "vector_storage"
    assert event.data["product_id"] == "memory_vector_query"
    assert event.data["operation_type"] == "vector_query"
    assert event.data["unit_type"] == "request"
    assert event.data["cost_components"][0]["provider"] == "qdrant"


@pytest.mark.asyncio
async def test_memory_vector_search_records_billing_usage():
    factual_service = AsyncMock()
    factual_service.vector_search.return_value = [
        {"id": "mem_1", "content": "expected memory"}
    ]

    service = MemoryService(
        event_bus=AsyncMock(),
        factual_service=factual_service,
        procedural_service=AsyncMock(),
        episodic_service=AsyncMock(),
        semantic_service=AsyncMock(),
        working_service=AsyncMock(),
        session_service=AsyncMock(),
        association_service=AsyncMock(),
    )

    results = await service.vector_search_factual(
        "user_123", "expected", limit=5, score_threshold=0.2
    )

    assert results == [{"id": "mem_1", "content": "expected memory"}]
    event = service.event_bus.publish_event.call_args.args[0]
    assert event.type == "billing.usage.recorded.vector_query"
    assert event.data["product_id"] == "memory_vector_query"
    assert event.data["usage_details"]["memory_type"] == "factual"
    assert event.data["usage_details"]["result_count"] == 1
    assert event.data["usage_details"]["limit"] == 5
