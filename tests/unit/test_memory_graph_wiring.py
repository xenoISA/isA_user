"""Runtime wiring tests for memory_service graph reads."""

import importlib
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _NoopMetric:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        return None

    def observe(self, *args, **kwargs):
        return None


def _install_main_import_stubs():
    """Keep main importable in CI's minimal isa_common test environment."""
    try:
        importlib.import_module("isa_common.observability")
    except ModuleNotFoundError:
        observability = ModuleType("isa_common.observability")
        observability.setup_observability = lambda *args, **kwargs: {
            "metrics": False,
            "logging": False,
            "tracing": False,
        }
        sys.modules["isa_common.observability"] = observability

    try:
        importlib.import_module("isa_common.metrics")
    except ModuleNotFoundError:
        metrics = ModuleType("isa_common.metrics")
        metrics.create_counter = lambda *args, **kwargs: _NoopMetric()
        metrics.create_histogram = lambda *args, **kwargs: _NoopMetric()
        sys.modules["isa_common.metrics"] = metrics

    try:
        importlib.import_module("isa_common.consul_client")
    except ModuleNotFoundError:
        consul_client = ModuleType("isa_common.consul_client")

        class ConsulRegistry:
            def __init__(self, *args, **kwargs):
                pass

            def register(self):
                return None

            def start_maintenance(self):
                return None

        consul_client.ConsulRegistry = ConsulRegistry
        sys.modules["isa_common.consul_client"] = consul_client


_install_main_import_stubs()


@pytest.fixture
def fake_memory_service():
    service = AsyncMock()
    service.factual_service = AsyncMock()
    service.factual_service._generate_embedding = AsyncMock(return_value=[0.1, 0.2])

    async def vector_result(*args, **kwargs):
        return [{"id": "mem-1", "content": "vector memory", "relevance_score": 0.9}]

    service.vector_search_factual = AsyncMock(side_effect=vector_result)
    service.vector_search_episodic = AsyncMock(return_value=[])
    service.vector_search_procedural = AsyncMock(return_value=[])
    service.vector_search_semantic = AsyncMock(return_value=[])
    service.vector_search_working = AsyncMock(return_value=[])
    service.vector_search_session = AsyncMock(return_value=[])
    return service


@pytest.mark.anyio
async def test_build_graph_client_returns_memory_graph_adapter():
    import microservices.memory_service.main as main_module
    from microservices.memory_service.memory_graph import MemoryGraphAdapter

    assert isinstance(main_module._build_graph_client(), MemoryGraphAdapter)


@pytest.mark.anyio
async def test_hybrid_search_uses_global_memory_graph_adapter(fake_memory_service):
    import microservices.memory_service.main as main_module

    graph_adapter = AsyncMock()
    graph_adapter.health_check = AsyncMock(return_value=True)
    graph_adapter.search_entities = AsyncMock(
        return_value={
            "entities": [
                {
                    "id": "graph-1",
                    "name": "Falkor memory graph",
                    "type": "project",
                    "content": "relationship context",
                    "relevance_score": 0.75,
                }
            ],
            "total": 1,
        }
    )

    original_service = main_module.memory_service
    original_graph = main_module.graph_client
    main_module.memory_service = fake_memory_service
    main_module.graph_client = graph_adapter

    try:
        with patch(
            "microservices.memory_service.graph_client.GraphClient",
            MagicMock(side_effect=AssertionError("legacy GraphClient should not run")),
        ) as legacy_graph:
            response = await main_module.hybrid_search(
                query="Falkor graph",
                user_id="usr-1",
                memory_types="factual",
                limit=5,
                vector_weight=0.6,
                graph_weight=0.4,
            )
    finally:
        main_module.memory_service = original_service
        main_module.graph_client = original_graph

    legacy_graph.assert_not_called()
    graph_adapter.health_check.assert_awaited_once()
    graph_adapter.search_entities.assert_awaited_once_with(
        query="Falkor graph", user_id="usr-1", limit=5
    )
    assert response["graph_available"] is True
    assert response["total_count"] >= 1


@pytest.mark.anyio
async def test_hybrid_search_keeps_vector_fallback_when_graph_unavailable(
    fake_memory_service,
):
    import microservices.memory_service.main as main_module

    graph_adapter = AsyncMock()
    graph_adapter.health_check = AsyncMock(return_value=False)

    original_service = main_module.memory_service
    original_graph = main_module.graph_client
    main_module.memory_service = fake_memory_service
    main_module.graph_client = graph_adapter

    try:
        response = await main_module.hybrid_search(
            query="only vector",
            user_id="usr-1",
            memory_types="factual",
            limit=5,
            vector_weight=0.6,
            graph_weight=0.4,
        )
    finally:
        main_module.memory_service = original_service
        main_module.graph_client = original_graph

    graph_adapter.health_check.assert_awaited_once()
    graph_adapter.search_entities.assert_not_awaited()
    assert response["graph_available"] is False
    assert response["results"]
    assert response["results"][0]["content"] == "vector memory"
