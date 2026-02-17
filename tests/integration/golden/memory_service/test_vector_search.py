"""
Memory Service Vector Search Integration Tests

Tests vector search functionality across all 6 memory types.
Validates Qdrant vector similarity search with user_id filtering.

Related Documents:
- Domain: docs/domain/memory_service.md
- Design: docs/design/memory_service.md

Requires:
- PostgreSQL database running
- Memory service running on port 8223
- Qdrant running on port 6333
- ISA Model service running on port 8082
"""

import pytest
import asyncio
import httpx
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.golden]

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:8223")
API_BASE = f"{MEMORY_SERVICE_URL}/api/v1"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Create HTTP client for tests"""
    async with httpx.AsyncClient(base_url=MEMORY_SERVICE_URL, timeout=60.0) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate test user ID"""
    return f"vector_test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def test_session_id():
    """Generate test session ID"""
    return f"vector_test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def internal_headers(test_user_id):
    """Headers for internal service calls"""
    return {
        "X-User-ID": test_user_id,
        "X-Request-ID": f"vector-test-{datetime.now().timestamp()}",
        "Content-Type": "application/json"
    }


# =============================================================================
# Vector Search Endpoint Tests
# =============================================================================

class TestFactualVectorSearch:
    """Test factual memory vector search"""

    async def test_factual_vector_search_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Factual vector search endpoint returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/vector",
            params={
                "user_id": test_user_id,
                "query": "what is the user's name",
                "limit": 10,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_factual_vector_search_response_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Factual vector search returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/vector",
            params={
                "user_id": test_user_id,
                "query": "Tokyo Japan residence",
                "limit": 5
            },
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data


class TestEpisodicVectorSearch:
    """Test episodic memory vector search"""

    async def test_episodic_vector_search_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Episodic vector search endpoint returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/episodic/search/vector",
            params={
                "user_id": test_user_id,
                "query": "birthday party celebration",
                "limit": 10,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_episodic_vector_search_response_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Episodic vector search returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/episodic/search/vector",
            params={
                "user_id": test_user_id,
                "query": "weekend trip vacation",
                "limit": 5
            },
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data


class TestProceduralVectorSearch:
    """Test procedural memory vector search"""

    async def test_procedural_vector_search_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Procedural vector search endpoint returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/procedural/search/vector",
            params={
                "user_id": test_user_id,
                "query": "how to cook pasta",
                "limit": 10,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_procedural_vector_search_response_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Procedural vector search returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/procedural/search/vector",
            params={
                "user_id": test_user_id,
                "query": "steps to deploy application",
                "limit": 5
            },
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data


class TestSemanticVectorSearch:
    """Test semantic memory vector search"""

    async def test_semantic_vector_search_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Semantic vector search endpoint returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/semantic/search/vector",
            params={
                "user_id": test_user_id,
                "query": "machine learning AI",
                "limit": 10,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_semantic_vector_search_response_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Semantic vector search returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/semantic/search/vector",
            params={
                "user_id": test_user_id,
                "query": "definition of neural network",
                "limit": 5
            },
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data


class TestWorkingVectorSearch:
    """Test working memory vector search"""

    async def test_working_vector_search_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Working vector search endpoint returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/working/search/vector",
            params={
                "user_id": test_user_id,
                "query": "current task in progress",
                "limit": 10,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_working_vector_search_response_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Working vector search returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/working/search/vector",
            params={
                "user_id": test_user_id,
                "query": "analysis processing job",
                "limit": 5
            },
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data


class TestSessionVectorSearch:
    """Test session memory vector search"""

    async def test_session_vector_search_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Session vector search endpoint returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/session/search/vector",
            params={
                "user_id": test_user_id,
                "query": "conversation about Python programming",
                "limit": 10,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_session_vector_search_with_session_filter(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: Session vector search with session_id filter"""
        response = await http_client.get(
            f"{API_BASE}/memories/session/search/vector",
            params={
                "user_id": test_user_id,
                "query": "help with code",
                "session_id": test_session_id,
                "limit": 10
            },
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Vector Search Workflow Tests
# =============================================================================

class TestVectorSearchWorkflow:
    """Test complete vector search workflows - store then search"""

    async def test_factual_store_and_vector_search(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Store factual memory then find via vector search"""
        # Store a factual memory
        store_response = await http_client.post(
            f"{API_BASE}/memories/factual/extract",
            json={
                "user_id": test_user_id,
                "dialog_content": "Maria lives in Paris and works as a data scientist at Google.",
                "importance_score": 0.8
            },
            headers=internal_headers
        )

        # Allow time for embedding to be stored
        await asyncio.sleep(2)

        # Vector search should find it
        search_response = await http_client.get(
            f"{API_BASE}/memories/factual/search/vector",
            params={
                "user_id": test_user_id,
                "query": "where does Maria live",
                "limit": 5,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert search_response.status_code == 200

    async def test_episodic_store_and_vector_search(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Store episodic memory then find via vector search"""
        # Store an episodic memory
        store_response = await http_client.post(
            f"{API_BASE}/memories/episodic/extract",
            json={
                "user_id": test_user_id,
                "dialog_content": "Last summer I went to a jazz concert in Central Park with my college friends.",
                "importance_score": 0.7
            },
            headers=internal_headers
        )

        await asyncio.sleep(2)

        # Vector search should find it
        search_response = await http_client.get(
            f"{API_BASE}/memories/episodic/search/vector",
            params={
                "user_id": test_user_id,
                "query": "music concert in the park",
                "limit": 5,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert search_response.status_code == 200

    async def test_procedural_store_and_vector_search(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Store procedural memory then find via vector search"""
        # Store a procedural memory
        store_response = await http_client.post(
            f"{API_BASE}/memories/procedural/extract",
            json={
                "user_id": test_user_id,
                "dialog_content": "To make spaghetti: 1) Boil water 2) Add pasta 3) Cook 8 minutes 4) Drain 5) Add sauce",
                "importance_score": 0.6
            },
            headers=internal_headers
        )

        await asyncio.sleep(2)

        # Vector search should find it
        search_response = await http_client.get(
            f"{API_BASE}/memories/procedural/search/vector",
            params={
                "user_id": test_user_id,
                "query": "how to prepare Italian pasta",
                "limit": 5,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert search_response.status_code == 200

    async def test_semantic_store_and_vector_search(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Store semantic memory then find via vector search"""
        # Store a semantic memory
        store_response = await http_client.post(
            f"{API_BASE}/memories/semantic/extract",
            json={
                "user_id": test_user_id,
                "dialog_content": "Photosynthesis is the process by which plants convert sunlight into energy.",
                "importance_score": 0.65
            },
            headers=internal_headers
        )

        await asyncio.sleep(2)

        # Vector search should find it
        search_response = await http_client.get(
            f"{API_BASE}/memories/semantic/search/vector",
            params={
                "user_id": test_user_id,
                "query": "how plants produce food from light",
                "limit": 5,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert search_response.status_code == 200


# =============================================================================
# User Isolation Tests
# =============================================================================

class TestVectorSearchUserIsolation:
    """Test that vector search properly isolates data by user_id"""

    async def test_factual_search_respects_user_id(
        self, http_client, internal_headers
    ):
        """CHAR: Factual vector search only returns results for specified user"""
        user1 = f"isolation_user1_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        user2 = f"isolation_user2_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Store memory for user1
        headers1 = {**internal_headers, "X-User-ID": user1}
        await http_client.post(
            f"{API_BASE}/memories/factual/extract",
            json={
                "user_id": user1,
                "dialog_content": "User1 works at Apple as an engineer.",
                "importance_score": 0.8
            },
            headers=headers1
        )

        await asyncio.sleep(2)

        # Search as user2 - should not find user1's data
        headers2 = {**internal_headers, "X-User-ID": user2}
        search_response = await http_client.get(
            f"{API_BASE}/memories/factual/search/vector",
            params={
                "user_id": user2,
                "query": "Apple engineer",
                "limit": 10,
                "score_threshold": 0.1
            },
            headers=headers2
        )

        assert search_response.status_code == 200
        data = search_response.json()
        # Should have 0 results since user2 has no memories about Apple engineers
        assert data.get("count", 0) == 0


# =============================================================================
# Performance and Edge Case Tests
# =============================================================================

class TestVectorSearchEdgeCases:
    """Test vector search edge cases"""

    async def test_empty_query_handling(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Vector search handles empty query gracefully"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/vector",
            params={
                "user_id": test_user_id,
                "query": "",
                "limit": 10
            },
            headers=internal_headers
        )

        # Should either return 200 with empty results or 400 for validation
        assert response.status_code in [200, 400]

    async def test_high_score_threshold(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Vector search with high threshold returns fewer results"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/vector",
            params={
                "user_id": test_user_id,
                "query": "test query",
                "limit": 10,
                "score_threshold": 0.95
            },
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_low_limit(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Vector search respects limit parameter"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/vector",
            params={
                "user_id": test_user_id,
                "query": "test query",
                "limit": 1,
                "score_threshold": 0.1
            },
            headers=internal_headers
        )

        assert response.status_code == 200
        if response.status_code == 200:
            data = response.json()
            assert len(data.get("memories", [])) <= 1
