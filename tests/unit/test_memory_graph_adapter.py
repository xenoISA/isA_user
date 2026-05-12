"""Unit tests for the Falkor-backed memory graph adapter."""

from unittest.mock import AsyncMock

import pytest

from microservices.memory_service.memory_graph import MemoryGraphAdapter


@pytest.fixture
def falkor_client():
    client = AsyncMock()
    client.health_check = AsyncMock(
        return_value={"healthy": True, "graph": "memory_graph"}
    )
    return client


@pytest.mark.asyncio
async def test_health_check_uses_falkor_client(falkor_client):
    adapter = MemoryGraphAdapter(client=falkor_client)

    assert await adapter.health_check() is True
    falkor_client.health_check.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_returns_false_on_error(falkor_client):
    falkor_client.health_check.side_effect = RuntimeError("connection refused")
    adapter = MemoryGraphAdapter(client=falkor_client)

    assert await adapter.health_check() is False
    assert adapter._client is None


@pytest.mark.asyncio
async def test_health_check_resets_client_on_unhealthy_result(falkor_client):
    falkor_client.health_check.return_value = {"healthy": False}
    adapter = MemoryGraphAdapter(client=falkor_client)

    assert await adapter.health_check() is False
    assert adapter._client is None


@pytest.mark.asyncio
async def test_search_entities_queries_memory_graph(falkor_client):
    falkor_client.query = AsyncMock(
        return_value=[
            {
                "id": "ent-1",
                "name": "FastAPI",
                "type": "framework",
                "memory_id": "mem-1",
                "content": "FastAPI preference",
                "relevance_score": 0.91,
                "properties": {"user_id": "usr-1", "name": "FastAPI"},
            }
        ]
    )
    adapter = MemoryGraphAdapter(client=falkor_client, graph_name="memory_graph")

    result = await adapter.search_entities(
        "fast", user_id="usr-1", limit=25, entity_types=["framework"]
    )

    assert result["total"] == 1
    assert result["entities"][0]["id"] == "ent-1"
    call = falkor_client.query.await_args
    assert "MemoryEntity" in call.args[0]
    assert call.kwargs["graph"] == "memory_graph"
    assert call.kwargs["read_only"] is True
    assert call.kwargs["params"] == {
        "query": "fast",
        "user_id": "usr-1",
        "entity_types": ["framework"],
        "limit": 25,
    }


@pytest.mark.asyncio
async def test_search_entities_degrades_on_falkor_error(falkor_client):
    falkor_client.query = AsyncMock(side_effect=RuntimeError("falkor unavailable"))
    adapter = MemoryGraphAdapter(client=falkor_client)

    result = await adapter.search_entities("fast", user_id="usr-1")

    assert result["entities"] == []
    assert result["total"] == 0
    assert "error" in result
    assert adapter._client is None


@pytest.mark.asyncio
async def test_get_entity_neighbors_returns_normalized_neighbors(falkor_client):
    falkor_client.query = AsyncMock(
        return_value=[
            {
                "id": "ent-2",
                "name": "Starlette",
                "type": "framework",
                "memory_id": "mem-2",
                "depth": 1,
                "relationship_path": ["RELATED_TO"],
                "properties": {"user_id": "usr-1"},
            }
        ]
    )
    adapter = MemoryGraphAdapter(client=falkor_client)

    result = await adapter.get_entity_neighbors(
        "ent-1", max_depth=3, relationship_types=["RELATED_TO"]
    )

    assert result["entity_id"] == "ent-1"
    assert result["neighbors"][0]["id"] == "ent-2"
    assert result["neighbors"][0]["relationship_path"] == ["RELATED_TO"]
    params = falkor_client.query.await_args.kwargs["params"]
    assert params["entity_id"] == "ent-1"
    assert params["relationship_types"] == ["RELATED_TO"]


@pytest.mark.asyncio
async def test_traverse_graph_returns_paths(falkor_client):
    falkor_client.query = AsyncMock(
        return_value=[
            {
                "nodes": [{"id": "ent-1"}, {"id": "ent-2"}],
                "relationships": ["USES"],
                "depth": 1,
            }
        ]
    )
    adapter = MemoryGraphAdapter(client=falkor_client)

    result = await adapter.traverse_graph(
        "ent-1", ["USES"], max_depth=2, user_id="usr-1"
    )

    assert result == {
        "paths": [
            {
                "nodes": [{"id": "ent-1"}, {"id": "ent-2"}],
                "relationships": ["USES"],
                "depth": 1,
            }
        ],
        "total_paths": 1,
    }
    params = falkor_client.query.await_args.kwargs["params"]
    assert params["start_entity"] == "ent-1"
    assert params["relationship_types"] == ["USES"]
    assert params["user_id"] == "usr-1"


@pytest.mark.asyncio
async def test_factory_builds_async_falkor_client_with_memory_graph(monkeypatch):
    created = {}

    class FakeFalkorClient:
        def __init__(self, *, graph):
            created["graph"] = graph

        async def health_check(self):
            return {"healthy": True}

    monkeypatch.delenv("FALKOR_HOST", raising=False)
    monkeypatch.delenv("FALKORDB_HOST", raising=False)
    monkeypatch.delenv("FALKOR_PORT", raising=False)
    monkeypatch.delenv("FALKORDB_PORT", raising=False)

    adapter = MemoryGraphAdapter(
        client_factory=FakeFalkorClient, graph_name="memory_graph"
    )

    assert await adapter.health_check() is True
    assert created["graph"] == "memory_graph"


@pytest.mark.asyncio
async def test_factory_uses_falkor_host_and_port_env(monkeypatch):
    created = {}

    class FakeFalkorClient:
        def __init__(self, **kwargs):
            created.update(kwargs)

        async def health_check(self):
            return {"healthy": True}

    monkeypatch.setenv("FALKOR_HOST", "127.0.0.1")
    monkeypatch.setenv("FALKOR_PORT", "6380")

    adapter = MemoryGraphAdapter(
        client_factory=FakeFalkorClient, graph_name="memory_graph"
    )

    assert await adapter.health_check() is True
    assert created == {
        "graph": "memory_graph",
        "host": "127.0.0.1",
        "port": 6380,
    }
