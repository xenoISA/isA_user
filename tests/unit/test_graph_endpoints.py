"""
Unit tests for graph retrieval endpoints (Issue #115)

Tests:
- Graph search endpoint returns entities
- Graph neighbors endpoint returns related entities
- Fallback when graph unavailable (503)
- Client methods for graph search and neighbors
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_memory_service():
    """Create a mock memory service that passes health checks."""
    service = AsyncMock()
    service.check_connection = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_graph_client():
    """Create a mock graph client."""
    client = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    client.search_entities = AsyncMock(return_value={
        "entities": [
            {
                "id": "entity-1",
                "name": "Python",
                "type": "technology",
                "properties": {"category": "programming_language"},
            },
            {
                "id": "entity-2",
                "name": "FastAPI",
                "type": "framework",
                "properties": {"language": "python"},
            },
        ],
        "total": 2,
    })
    client.get_entity_neighbors = AsyncMock(return_value={
        "neighbors": [
            {
                "id": "entity-2",
                "name": "FastAPI",
                "type": "framework",
                "relationship": "built_with",
                "depth": 1,
            },
            {
                "id": "entity-3",
                "name": "Pydantic",
                "type": "library",
                "relationship": "depends_on",
                "depth": 1,
            },
        ],
        "entity_id": "entity-1",
    })
    return client


@pytest.fixture
def app_with_graph(mock_memory_service, mock_graph_client):
    """Create a FastAPI test app with mocked dependencies."""
    import microservices.memory_service.main as main_module

    # Save originals
    orig_service = main_module.memory_service
    orig_graph = getattr(main_module, "graph_client", None)
    orig_shutdown = main_module.shutdown_manager

    # Patch
    main_module.memory_service = mock_memory_service
    main_module.graph_client = mock_graph_client
    mock_shutdown = MagicMock()
    mock_shutdown.is_shutting_down = False
    main_module.shutdown_manager = mock_shutdown

    yield main_module.app

    # Restore
    main_module.memory_service = orig_service
    main_module.graph_client = orig_graph
    main_module.shutdown_manager = orig_shutdown


@pytest.fixture
def client(app_with_graph):
    """Create a test client."""
    return TestClient(app_with_graph)


# ---------------------------------------------------------------------------
# Graph Search Endpoint Tests
# ---------------------------------------------------------------------------

class TestGraphSearchEndpoint:
    """Tests for GET /api/v1/memories/graph/search"""

    def test_graph_search_returns_entities(self, client, mock_graph_client):
        """Graph search should return matching entities."""
        response = client.get(
            "/api/v1/memories/graph/search",
            params={"query": "Python", "user_id": "user-1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "total" in data
        assert len(data["entities"]) == 2
        assert data["entities"][0]["name"] == "Python"
        mock_graph_client.search_entities.assert_awaited_once_with(
            query="Python",
            user_id="user-1",
            limit=10,
            entity_types=None,
        )

    def test_graph_search_with_limit(self, client, mock_graph_client):
        """Graph search should respect the limit parameter."""
        response = client.get(
            "/api/v1/memories/graph/search",
            params={"query": "Python", "user_id": "user-1", "limit": 5},
        )
        assert response.status_code == 200
        mock_graph_client.search_entities.assert_awaited_once_with(
            query="Python",
            user_id="user-1",
            limit=5,
            entity_types=None,
        )

    def test_graph_search_with_max_depth(self, client, mock_graph_client):
        """Graph search should accept max_depth parameter."""
        response = client.get(
            "/api/v1/memories/graph/search",
            params={
                "query": "Python",
                "user_id": "user-1",
                "max_depth": 3,
            },
        )
        assert response.status_code == 200

    def test_graph_search_missing_query(self, client):
        """Graph search should return 422 when query is missing."""
        response = client.get(
            "/api/v1/memories/graph/search",
            params={"user_id": "user-1"},
        )
        assert response.status_code == 422

    def test_graph_search_missing_user_id(self, client):
        """Graph search should return 422 when user_id is missing."""
        response = client.get(
            "/api/v1/memories/graph/search",
            params={"query": "Python"},
        )
        assert response.status_code == 422

    def test_graph_search_unavailable_returns_503(self, client, mock_graph_client):
        """Graph search should return 503 when graph client is unavailable."""
        mock_graph_client.search_entities = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        response = client.get(
            "/api/v1/memories/graph/search",
            params={"query": "Python", "user_id": "user-1"},
        )
        assert response.status_code == 503
        data = response.json()
        assert "error" in data["detail"] or "unavailable" in data["detail"].lower()


class TestGraphSearchNoClient:
    """Tests for graph search when graph_client is None."""

    def test_graph_search_no_client_returns_503(self):
        """Graph search should return 503 when graph client is not configured."""
        import microservices.memory_service.main as main_module

        orig_service = main_module.memory_service
        orig_graph = getattr(main_module, "graph_client", None)
        orig_shutdown = main_module.shutdown_manager

        mock_service = AsyncMock()
        mock_service.check_connection = AsyncMock(return_value=True)
        main_module.memory_service = mock_service
        main_module.graph_client = None
        mock_shutdown = MagicMock()
        mock_shutdown.is_shutting_down = False
        main_module.shutdown_manager = mock_shutdown

        try:
            test_client = TestClient(main_module.app)
            response = test_client.get(
                "/api/v1/memories/graph/search",
                params={"query": "Python", "user_id": "user-1"},
            )
            assert response.status_code == 503
            data = response.json()
            assert "graph" in data["detail"].lower()
        finally:
            main_module.memory_service = orig_service
            main_module.graph_client = orig_graph
            main_module.shutdown_manager = orig_shutdown


# ---------------------------------------------------------------------------
# Graph Neighbors Endpoint Tests
# ---------------------------------------------------------------------------

class TestGraphNeighborsEndpoint:
    """Tests for GET /api/v1/memories/graph/neighbors"""

    def test_graph_neighbors_returns_entities(self, client, mock_graph_client):
        """Graph neighbors should return related entities."""
        response = client.get(
            "/api/v1/memories/graph/neighbors",
            params={"entity_id": "entity-1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "neighbors" in data
        assert "entity_id" in data
        assert len(data["neighbors"]) == 2
        assert data["entity_id"] == "entity-1"

    def test_graph_neighbors_with_depth(self, client, mock_graph_client):
        """Graph neighbors should respect the depth parameter."""
        response = client.get(
            "/api/v1/memories/graph/neighbors",
            params={"entity_id": "entity-1", "depth": 3},
        )
        assert response.status_code == 200
        mock_graph_client.get_entity_neighbors.assert_awaited_once_with(
            entity_id="entity-1",
            max_depth=3,
            relationship_types=None,
        )

    def test_graph_neighbors_with_user_id(self, client, mock_graph_client):
        """Graph neighbors should accept optional user_id."""
        response = client.get(
            "/api/v1/memories/graph/neighbors",
            params={"entity_id": "entity-1", "user_id": "user-1"},
        )
        assert response.status_code == 200

    def test_graph_neighbors_missing_entity_id(self, client):
        """Graph neighbors should return 422 when entity_id is missing."""
        response = client.get("/api/v1/memories/graph/neighbors")
        assert response.status_code == 422

    def test_graph_neighbors_unavailable_returns_503(self, client, mock_graph_client):
        """Graph neighbors should return 503 when graph client fails."""
        mock_graph_client.get_entity_neighbors = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        response = client.get(
            "/api/v1/memories/graph/neighbors",
            params={"entity_id": "entity-1"},
        )
        assert response.status_code == 503

    def test_graph_neighbors_no_client_returns_503(self):
        """Graph neighbors should return 503 when graph client is None."""
        import microservices.memory_service.main as main_module

        orig_service = main_module.memory_service
        orig_graph = getattr(main_module, "graph_client", None)
        orig_shutdown = main_module.shutdown_manager

        mock_service = AsyncMock()
        mock_service.check_connection = AsyncMock(return_value=True)
        main_module.memory_service = mock_service
        main_module.graph_client = None
        mock_shutdown = MagicMock()
        mock_shutdown.is_shutting_down = False
        main_module.shutdown_manager = mock_shutdown

        try:
            test_client = TestClient(main_module.app)
            response = test_client.get(
                "/api/v1/memories/graph/neighbors",
                params={"entity_id": "entity-1"},
            )
            assert response.status_code == 503
        finally:
            main_module.memory_service = orig_service
            main_module.graph_client = orig_graph
            main_module.shutdown_manager = orig_shutdown


# ---------------------------------------------------------------------------
# Health Endpoint — Graph Status Tests
# ---------------------------------------------------------------------------

class TestHealthGraphStatus:
    """Tests for graph status in the health endpoint."""

    def test_health_includes_graph_status(self, client, mock_graph_client):
        """Health endpoint should include graph_connected field."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "graph_connected" in data
        assert data["graph_connected"] is True

    def test_health_graph_disconnected(self, client, mock_graph_client):
        """Health should report graph_connected=False when graph is down."""
        mock_graph_client.health_check = AsyncMock(return_value=False)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["graph_connected"] is False

    def test_health_no_graph_client(self):
        """Health should report graph_connected=False when client is None."""
        import microservices.memory_service.main as main_module

        orig_service = main_module.memory_service
        orig_graph = getattr(main_module, "graph_client", None)
        orig_shutdown = main_module.shutdown_manager

        mock_service = AsyncMock()
        mock_service.check_connection = AsyncMock(return_value=True)
        main_module.memory_service = mock_service
        main_module.graph_client = None
        mock_shutdown = MagicMock()
        mock_shutdown.is_shutting_down = False
        main_module.shutdown_manager = mock_shutdown

        try:
            test_client = TestClient(main_module.app)
            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["graph_connected"] is False
        finally:
            main_module.memory_service = orig_service
            main_module.graph_client = orig_graph
            main_module.shutdown_manager = orig_shutdown


# ---------------------------------------------------------------------------
# Client Method Tests
# ---------------------------------------------------------------------------

class TestMemoryServiceClientGraphMethods:
    """Tests for graph methods on MemoryServiceClient."""

    @pytest.mark.anyio
    async def test_client_graph_search(self):
        """Client graph_search should call the correct endpoint."""
        from microservices.memory_service.client import MemoryServiceClient

        client = MemoryServiceClient(base_url="http://test:8223")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [{"id": "e1", "name": "Python"}],
            "total": 1,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await client.graph_search(
                query="Python",
                user_id="user-1",
                limit=5,
                max_depth=2,
            )

            assert result["total"] == 1
            assert result["entities"][0]["name"] == "Python"
            mock_client_instance.get.assert_awaited_once()
            call_args = mock_client_instance.get.call_args
            assert "/api/v1/memories/graph/search" in call_args.args[0]

    @pytest.mark.anyio
    async def test_client_graph_neighbors(self):
        """Client graph_neighbors should call the correct endpoint."""
        from microservices.memory_service.client import MemoryServiceClient

        client = MemoryServiceClient(base_url="http://test:8223")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "neighbors": [{"id": "e2", "name": "FastAPI"}],
            "entity_id": "entity-1",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await client.graph_neighbors(
                entity_id="entity-1",
                depth=2,
                user_id="user-1",
            )

            assert result["entity_id"] == "entity-1"
            assert len(result["neighbors"]) == 1
            mock_client_instance.get.assert_awaited_once()
            call_args = mock_client_instance.get.call_args
            assert "/api/v1/memories/graph/neighbors" in call_args.args[0]


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestGraphModels:
    """Tests for GraphSearchRequest and GraphSearchResponse models."""

    def test_graph_search_request_defaults(self):
        """GraphSearchRequest should have sensible defaults."""
        from microservices.memory_service.models import GraphSearchRequest

        req = GraphSearchRequest(query="test", user_id="user-1")
        assert req.limit == 10
        assert req.max_depth == 2
        assert req.entity_types is None

    def test_graph_search_request_custom(self):
        """GraphSearchRequest should accept custom values."""
        from microservices.memory_service.models import GraphSearchRequest

        req = GraphSearchRequest(
            query="Python",
            user_id="user-1",
            limit=5,
            max_depth=3,
            entity_types=["technology", "framework"],
        )
        assert req.limit == 5
        assert req.max_depth == 3
        assert len(req.entity_types) == 2

    def test_graph_search_response(self):
        """GraphSearchResponse should serialize correctly."""
        from microservices.memory_service.models import GraphSearchResponse, GraphEntity

        entity = GraphEntity(
            id="e1",
            name="Python",
            type="technology",
            properties={"category": "language"},
        )
        resp = GraphSearchResponse(entities=[entity], total=1)
        assert resp.total == 1
        assert resp.entities[0].name == "Python"

    def test_graph_neighbors_request_defaults(self):
        """GraphNeighborsRequest should have sensible defaults."""
        from microservices.memory_service.models import GraphNeighborsRequest

        req = GraphNeighborsRequest(entity_id="e1")
        assert req.depth == 2
        assert req.user_id is None
        assert req.relationship_types is None

    def test_graph_neighbors_response(self):
        """GraphNeighborsResponse should serialize correctly."""
        from microservices.memory_service.models import GraphNeighborsResponse, GraphNeighbor

        neighbor = GraphNeighbor(
            id="e2",
            name="FastAPI",
            type="framework",
            relationship="built_with",
            depth=1,
        )
        resp = GraphNeighborsResponse(
            neighbors=[neighbor],
            entity_id="e1",
        )
        assert resp.entity_id == "e1"
        assert len(resp.neighbors) == 1
