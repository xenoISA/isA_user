"""
Memory Service API Tests (Golden)

Characterization tests for memory service API endpoints.
Tests HTTP contract validation, authentication, error handling.

Related Documents:
- Domain: docs/domain/memory_service.md
- PRD: docs/prd/memory_service.md
- Design: docs/design/memory_service.md
- Data Contract: tests/contracts/memory/data_contract.py

Port: 8223
"""

import pytest
import httpx
import os
from datetime import datetime
from typing import Dict, Any

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:8223")
API_BASE = f"{MEMORY_SERVICE_URL}/api/v1"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Create HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate test user ID"""
    return f"api_test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def test_session_id():
    """Generate test session ID"""
    return f"api_test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def auth_headers(test_user_id):
    """Mock authentication headers for API testing"""
    return {
        "Authorization": "Bearer api_test_token_12345",
        "X-User-ID": test_user_id,
        "X-Request-ID": f"api-test-{datetime.now().timestamp()}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def internal_headers(test_user_id):
    """Internal service call headers (bypass auth)"""
    return {
        "X-User-ID": test_user_id,
        "X-Internal-Call": "true",
        "X-Request-ID": f"internal-test-{datetime.now().timestamp()}",
        "Content-Type": "application/json"
    }


# =============================================================================
# Health Check API Tests
# =============================================================================

class TestMemoryServiceHealthAPI:
    """Test memory service health endpoints"""

    async def test_health_returns_200(self, http_client):
        """CHAR: GET /health returns 200"""
        response = await http_client.get(f"{MEMORY_SERVICE_URL}/health")
        assert response.status_code == 200

    async def test_health_returns_json(self, http_client):
        """CHAR: GET /health returns JSON content type"""
        response = await http_client.get(f"{MEMORY_SERVICE_URL}/health")
        assert "application/json" in response.headers.get("content-type", "")

    async def test_health_contains_status(self, http_client):
        """CHAR: Health response contains status field"""
        response = await http_client.get(f"{MEMORY_SERVICE_URL}/health")
        data = response.json()
        assert "status" in data

    async def test_health_identifies_service(self, http_client):
        """CHAR: Health response identifies service"""
        response = await http_client.get(f"{MEMORY_SERVICE_URL}/health")
        data = response.json()
        assert data.get("service") == "memory_service"

    async def test_health_shows_database_status(self, http_client):
        """CHAR: Health shows database connection status"""
        response = await http_client.get(f"{MEMORY_SERVICE_URL}/health")
        data = response.json()
        assert "database_connected" in data


# =============================================================================
# Factual Memory API Tests
# =============================================================================

class TestFactualMemoryAPI:
    """Test factual memory extraction API endpoints"""

    async def test_extract_factual_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/memories/factual/extract endpoint exists"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "John works at Apple as a software engineer.",
            "importance_score": 0.7
        }

        response = await http_client.post(
            f"{API_BASE}/memories/factual/extract",
            json=request_data,
            headers=internal_headers
        )

        # Endpoint exists (may fail if AI service unavailable)
        assert response.status_code in [200, 201, 500, 503]

    async def test_search_factual_by_subject_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories/factual/search/subject returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/subject",
            params={"user_id": test_user_id, "subject": "test", "limit": 10},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_search_factual_returns_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Factual search returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/subject",
            params={"user_id": test_user_id, "subject": "test", "limit": 10},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data

    async def test_search_factual_validates_user_id(
        self, http_client, internal_headers
    ):
        """CHAR: Factual search requires user_id parameter"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/subject",
            params={"subject": "test"},  # Missing user_id
            headers=internal_headers
        )

        assert response.status_code == 422


# =============================================================================
# Episodic Memory API Tests
# =============================================================================

class TestEpisodicMemoryAPI:
    """Test episodic memory extraction API endpoints"""

    async def test_extract_episodic_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/memories/episodic/extract endpoint exists"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "Last week I visited Tokyo with friends.",
            "importance_score": 0.8
        }

        response = await http_client.post(
            f"{API_BASE}/memories/episodic/extract",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 500, 503]

    async def test_search_episodic_by_event_type_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories/episodic/search/event_type returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/episodic/search/event_type",
            params={"user_id": test_user_id, "event_type": "travel", "limit": 10},
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Procedural Memory API Tests
# =============================================================================

class TestProceduralMemoryAPI:
    """Test procedural memory extraction API endpoints"""

    async def test_extract_procedural_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/memories/procedural/extract endpoint exists"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "To deploy: run tests, build image, push to registry.",
            "importance_score": 0.6
        }

        response = await http_client.post(
            f"{API_BASE}/memories/procedural/extract",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 500, 503]


# =============================================================================
# Semantic Memory API Tests
# =============================================================================

class TestSemanticMemoryAPI:
    """Test semantic memory extraction API endpoints"""

    async def test_extract_semantic_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/memories/semantic/extract endpoint exists"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "Machine learning is a branch of AI.",
            "importance_score": 0.65
        }

        response = await http_client.post(
            f"{API_BASE}/memories/semantic/extract",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 500, 503]

    async def test_search_semantic_by_category_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories/semantic/search/category returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/semantic/search/category",
            params={"user_id": test_user_id, "category": "technology", "limit": 10},
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Session Memory API Tests
# =============================================================================

class TestSessionMemoryAPI:
    """Test session memory API endpoints"""

    async def test_store_session_message_returns_success(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: POST /api/v1/memories/session/store returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "session_id": test_session_id,
            "message_content": "Hello, this is an API test message.",
            "message_type": "human",
            "role": "user"
        }

        response = await http_client.post(
            f"{API_BASE}/memories/session/store",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_store_session_validates_required_fields(
        self, http_client, internal_headers
    ):
        """CHAR: POST /api/v1/memories/session/store validates fields"""
        request_data = {
            "message_content": "Missing user_id and session_id"
        }

        response = await http_client.post(
            f"{API_BASE}/memories/session/store",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_get_session_memories_returns_200(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: GET /api/v1/memories/session/{id} returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/session/{test_session_id}",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404]

    async def test_get_session_context_returns_200(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: GET /api/v1/memories/session/{id}/context returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/session/{test_session_id}/context",
            params={
                "user_id": test_user_id,
                "include_summaries": True,
                "max_recent_messages": 5
            },
            headers=internal_headers
        )

        assert response.status_code in [200, 404]

    async def test_deactivate_session_returns_200(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: POST /api/v1/memories/session/{id}/deactivate returns 200"""
        response = await http_client.post(
            f"{API_BASE}/memories/session/{test_session_id}/deactivate",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404]


# =============================================================================
# Working Memory API Tests
# =============================================================================

class TestWorkingMemoryAPI:
    """Test working memory API endpoints"""

    async def test_store_working_memory_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/memories/working/store returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "Analyzing data for API test task",
            "ttl_seconds": 1800,
            "importance_score": 0.7
        }

        response = await http_client.post(
            f"{API_BASE}/memories/working/store",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_get_active_working_memories_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories/working/active returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/working/active",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_active_working_returns_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Active working memories returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/working/active",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data

    async def test_cleanup_expired_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/memories/working/cleanup returns 200"""
        response = await http_client.post(
            f"{API_BASE}/memories/working/cleanup",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Generic Memory CRUD API Tests
# =============================================================================

class TestGenericMemoryAPI:
    """Test generic memory CRUD API endpoints"""

    async def test_create_memory_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/memories returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "memory_type": "factual",
            "content": "API test memory content",
            "importance_score": 0.5,
            "confidence": 0.8,
            "tags": ["api_test"],
            "context": {"source": "api_test"}
        }

        response = await http_client.post(
            f"{API_BASE}/memories",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_list_memories_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories",
            params={"user_id": test_user_id, "limit": 50},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_list_memories_with_type_filter(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories with type filter returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories",
            params={
                "user_id": test_user_id,
                "memory_type": "factual",
                "limit": 50
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_list_memories_returns_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: List memories returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data

    async def test_get_nonexistent_memory_returns_404(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET nonexistent memory returns 404"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/nonexistent_memory_api_12345",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 404


# =============================================================================
# Universal Search API Tests
# =============================================================================

class TestUniversalSearchAPI:
    """Test universal search API endpoints"""

    async def test_universal_search_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories/search returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/search",
            params={
                "user_id": test_user_id,
                "query": "test",
                "limit": 10
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_universal_search_with_types(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Universal search with memory_types parameter"""
        response = await http_client.get(
            f"{API_BASE}/memories/search",
            params={
                "user_id": test_user_id,
                "query": "test",
                "memory_types": "factual,episodic",
                "limit": 10
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_universal_search_returns_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Universal search returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/search",
            params={
                "user_id": test_user_id,
                "query": "test",
                "limit": 10
            },
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "query" in data
            assert "user_id" in data
            assert "results" in data
            assert "total_count" in data

    async def test_universal_search_validates_user_id(
        self, http_client, internal_headers
    ):
        """CHAR: Universal search requires user_id"""
        response = await http_client.get(
            f"{API_BASE}/memories/search",
            params={"query": "test"},  # Missing user_id
            headers=internal_headers
        )

        assert response.status_code == 422


# =============================================================================
# Statistics API Tests
# =============================================================================

class TestStatisticsAPI:
    """Test memory statistics API endpoints"""

    async def test_get_statistics_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/memories/statistics returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/statistics",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_statistics_returns_dict(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Statistics returns dictionary structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/statistics",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


# =============================================================================
# Error Handling API Tests
# =============================================================================

class TestMemoryAPIErrorHandling:
    """Test API error handling"""

    async def test_malformed_json_returns_400(
        self, http_client, internal_headers
    ):
        """CHAR: Malformed JSON returns 400/422"""
        headers = {**internal_headers}
        headers["Content-Type"] = "application/json"

        response = await http_client.post(
            f"{API_BASE}/memories",
            content="invalid json {",
            headers=headers
        )

        assert response.status_code in [400, 422]

    async def test_invalid_memory_type_returns_422(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Invalid memory_type returns 422"""
        request_data = {
            "user_id": test_user_id,
            "memory_type": "invalid_type",
            "content": "Test content"
        }

        response = await http_client.post(
            f"{API_BASE}/memories",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_missing_required_field_returns_422(
        self, http_client, internal_headers
    ):
        """CHAR: Missing required field returns 422"""
        request_data = {
            "memory_type": "factual"
            # Missing user_id and content
        }

        response = await http_client.post(
            f"{API_BASE}/memories",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code == 422


# =============================================================================
# API Response Headers Tests
# =============================================================================

class TestMemoryAPIResponseHeaders:
    """Test API response headers"""

    async def test_content_type_json(self, http_client):
        """CHAR: API responses have JSON content type"""
        response = await http_client.get(f"{MEMORY_SERVICE_URL}/health")

        assert "application/json" in response.headers.get("content-type", "")

    async def test_response_has_content_type(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: API endpoints return content-type header"""
        response = await http_client.get(
            f"{API_BASE}/memories",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        if response.status_code == 200:
            assert "content-type" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
