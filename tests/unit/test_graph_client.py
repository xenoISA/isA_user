"""
Unit tests for GraphClient — Neo4j knowledge graph integration via isA_Data

Tests cover:
- Entity search with mocked HTTP responses
- Neighbor traversal
- Graph traversal (multi-hop)
- Health check
- Fallback when isA_Data is unavailable
- Timeout handling
- Enriched event payload validation
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from microservices.memory_service.graph_client import GraphClient
from microservices.memory_service.events.models import MemoryCreatedEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def graph_client():
    """GraphClient with a fixed base URL (no Consul)."""
    return GraphClient(base_url="http://localhost:8300")


@pytest.fixture
def mock_response():
    """Factory for fake aiohttp response objects."""
    def _make(status=200, json_data=None):
        resp = AsyncMock()
        resp.status = status
        resp.json = AsyncMock(return_value=json_data or {})
        resp.text = AsyncMock(return_value=str(json_data))
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)
        return resp
    return _make


# ---------------------------------------------------------------------------
# 1. search_entities — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_entities_returns_results(graph_client, mock_response):
    """search_entities returns entity list from isA_Data."""
    entities = [
        {"id": "e1", "name": "Python", "type": "language", "properties": {}},
        {"id": "e2", "name": "FastAPI", "type": "framework", "properties": {}},
    ]
    resp = mock_response(200, {"entities": entities, "total": 2})

    with patch("aiohttp.ClientSession.get", return_value=resp):
        result = await graph_client.search_entities(
            query="Python", user_id="user-1", limit=10
        )

    assert result["entities"] == entities
    assert result["total"] == 2


# ---------------------------------------------------------------------------
# 2. search_entities — empty results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_entities_empty(graph_client, mock_response):
    """search_entities returns empty list when nothing matches."""
    resp = mock_response(200, {"entities": [], "total": 0})

    with patch("aiohttp.ClientSession.get", return_value=resp):
        result = await graph_client.search_entities(
            query="nonexistent", user_id="user-1"
        )

    assert result["entities"] == []
    assert result["total"] == 0


# ---------------------------------------------------------------------------
# 3. search_entities — service unavailable fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_entities_service_unavailable(graph_client, mock_response):
    """search_entities returns graceful fallback when isA_Data is down."""
    resp = mock_response(503, {"error": "Service unavailable"})

    with patch("aiohttp.ClientSession.get", return_value=resp):
        result = await graph_client.search_entities(
            query="test", user_id="user-1"
        )

    assert result["entities"] == []
    assert result.get("error") is not None


# ---------------------------------------------------------------------------
# 4. search_entities — connection error fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_entities_connection_error(graph_client):
    """search_entities degrades gracefully on connection error."""
    with patch("aiohttp.ClientSession.get", side_effect=Exception("Connection refused")):
        result = await graph_client.search_entities(
            query="test", user_id="user-1"
        )

    assert result["entities"] == []
    assert "error" in result


# ---------------------------------------------------------------------------
# 5. get_entity_neighbors — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_entity_neighbors(graph_client, mock_response):
    """get_entity_neighbors returns neighbor entities."""
    neighbors = [
        {"id": "e2", "name": "Django", "type": "framework", "relation": "RELATED_TO"},
        {"id": "e3", "name": "Flask", "type": "framework", "relation": "RELATED_TO"},
    ]
    resp = mock_response(200, {"neighbors": neighbors, "entity_id": "e1"})

    with patch("aiohttp.ClientSession.get", return_value=resp):
        result = await graph_client.get_entity_neighbors(
            entity_id="e1", max_depth=1
        )

    assert len(result["neighbors"]) == 2
    assert result["entity_id"] == "e1"


# ---------------------------------------------------------------------------
# 6. get_entity_neighbors — entity not found
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_entity_neighbors_not_found(graph_client, mock_response):
    """get_entity_neighbors returns empty when entity doesn't exist."""
    resp = mock_response(404, {"error": "Entity not found"})

    with patch("aiohttp.ClientSession.get", return_value=resp):
        result = await graph_client.get_entity_neighbors(entity_id="missing")

    assert result["neighbors"] == []


# ---------------------------------------------------------------------------
# 7. traverse_graph — multi-hop traversal
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_traverse_graph(graph_client, mock_response):
    """traverse_graph returns paths from a multi-hop traversal."""
    paths = [
        {
            "nodes": [
                {"id": "e1", "name": "Python"},
                {"id": "e2", "name": "FastAPI"},
            ],
            "relationships": [{"type": "USES", "source": "e1", "target": "e2"}],
        }
    ]
    resp = mock_response(200, {"paths": paths, "total_paths": 1})

    with patch("aiohttp.ClientSession.post", return_value=resp):
        result = await graph_client.traverse_graph(
            start_entity="e1",
            relationship_types=["USES"],
            max_depth=2,
            user_id="user-1",
        )

    assert len(result["paths"]) == 1
    assert result["total_paths"] == 1


# ---------------------------------------------------------------------------
# 8. traverse_graph — service unavailable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_traverse_graph_service_unavailable(graph_client):
    """traverse_graph degrades gracefully when service is down."""
    with patch("aiohttp.ClientSession.post", side_effect=Exception("timeout")):
        result = await graph_client.traverse_graph(
            start_entity="e1",
            relationship_types=["USES"],
            max_depth=2,
            user_id="user-1",
        )

    assert result["paths"] == []
    assert "error" in result


# ---------------------------------------------------------------------------
# 9. health_check — healthy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check_healthy(graph_client, mock_response):
    """health_check returns True when isA_Data graph endpoint is healthy."""
    resp = mock_response(200, {"status": "healthy", "neo4j": "connected"})

    with patch("aiohttp.ClientSession.get", return_value=resp):
        healthy = await graph_client.health_check()

    assert healthy is True


# ---------------------------------------------------------------------------
# 10. health_check — unhealthy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check_unhealthy(graph_client):
    """health_check returns False when isA_Data is unreachable."""
    with patch("aiohttp.ClientSession.get", side_effect=Exception("Connection refused")):
        healthy = await graph_client.health_check()

    assert healthy is False


# ---------------------------------------------------------------------------
# 11. health_check — degraded response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check_degraded(graph_client, mock_response):
    """health_check returns False on non-200 status."""
    resp = mock_response(503, {"status": "degraded"})

    with patch("aiohttp.ClientSession.get", return_value=resp):
        healthy = await graph_client.health_check()

    assert healthy is False


# ---------------------------------------------------------------------------
# 12. Enriched MemoryCreatedEvent — backward compatibility
# ---------------------------------------------------------------------------

def test_memory_created_event_enriched_fields():
    """MemoryCreatedEvent supports new memory_data field (additive, optional)."""
    # Without memory_data — backward compatible
    event_basic = MemoryCreatedEvent(
        memory_id="m1",
        memory_type="factual",
        user_id="user-1",
        content="Python is a programming language",
        timestamp="2026-03-16T00:00:00Z",
    )
    data = event_basic.model_dump(mode="json")
    assert data["content"] == "Python is a programming language"
    assert data.get("memory_data") is None

    # With memory_data — enriched payload for isA_Data extraction
    event_enriched = MemoryCreatedEvent(
        memory_id="m2",
        memory_type="factual",
        user_id="user-1",
        content="Python was created by Guido van Rossum",
        memory_data={
            "subject": "Python",
            "predicate": "created_by",
            "object_value": "Guido van Rossum",
            "fact_type": "person",
        },
        timestamp="2026-03-16T00:00:00Z",
    )
    data = event_enriched.model_dump(mode="json")
    assert data["memory_data"]["subject"] == "Python"
    assert data["memory_data"]["predicate"] == "created_by"


# ---------------------------------------------------------------------------
# 13. GraphClient default URL from env
# ---------------------------------------------------------------------------

def test_graph_client_env_fallback():
    """GraphClient falls back to DATA_SERVICE_URL env var."""
    with patch.dict(os.environ, {"DATA_SERVICE_URL": "http://data-svc:9000"}):
        client = GraphClient()
    assert client.base_url == "http://data-svc:9000"


# ---------------------------------------------------------------------------
# 14. GraphClient default URL without env
# ---------------------------------------------------------------------------

def test_graph_client_default_url():
    """GraphClient uses default URL when no env var is set."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove DATA_SERVICE_URL if it exists
        env = os.environ.copy()
        env.pop("DATA_SERVICE_URL", None)
        with patch.dict(os.environ, env, clear=True):
            client = GraphClient()
    assert "localhost" in client.base_url or "127.0.0.1" in client.base_url
