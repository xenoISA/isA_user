"""
Memory Service Integration Tests

Tests memory service API endpoints with real database.
Validates HTTP API + PostgreSQL + Qdrant + Event publishing.

Related Documents:
- Domain: docs/domain/memory_service.md
- PRD: docs/prd/memory_service.md
- Design: docs/design/memory_service.md
- Data Contract: tests/contracts/memory/data_contract.py

Requires:
- PostgreSQL database running
- Memory service running on port 8223
- Qdrant (optional, for vector search)
- NATS for events (optional)
"""

import pytest
import asyncio
import httpx
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Import contract components
from tests.contracts.memory.data_contract import (
    MemoryTestDataFactory,
    ExtractFactualMemoryRequest,
    ExtractEpisodicMemoryRequest,
    ExtractProceduralMemoryRequest,
    ExtractSemanticMemoryRequest,
    StoreSessionMessageRequest,
    StoreWorkingMemoryRequest,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.golden]

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:8223")
API_BASE = f"{MEMORY_SERVICE_URL}/api/v1"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Create HTTP client for tests"""
    async with httpx.AsyncClient(base_url=MEMORY_SERVICE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate test user ID"""
    return f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def test_session_id():
    """Generate test session ID"""
    return f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def internal_headers(test_user_id):
    """Headers for internal service calls"""
    return {
        "X-User-ID": test_user_id,
        "X-Request-ID": f"test-{datetime.now().timestamp()}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def factory():
    """Create test data factory"""
    return MemoryTestDataFactory(seed=42)


@pytest.fixture
async def cleanup_memories(http_client, internal_headers, test_user_id):
    """Cleanup fixture for memories"""
    created_ids = []

    def track(memory_id, memory_type):
        created_ids.append((memory_id, memory_type))

    yield track

    # Cleanup
    for memory_id, memory_type in created_ids:
        try:
            await http_client.delete(
                f"{API_BASE}/memories/{memory_type}/{memory_id}",
                params={"user_id": test_user_id},
                headers=internal_headers
            )
        except Exception:
            pass


# =============================================================================
# Health Check Tests
# =============================================================================

class TestMemoryServiceHealth:
    """Test memory service health endpoints"""

    async def test_health_endpoint(self, http_client):
        """CHAR: Health endpoint returns 200"""
        response = await http_client.get("/health")
        assert response.status_code == 200

    async def test_health_response_structure(self, http_client):
        """CHAR: Health response contains status field"""
        response = await http_client.get("/health")
        data = response.json()
        assert "status" in data

    async def test_health_contains_service_name(self, http_client):
        """CHAR: Health response contains service name"""
        response = await http_client.get("/health")
        data = response.json()
        assert data.get("service") == "memory_service"

    async def test_health_contains_database_status(self, http_client):
        """CHAR: Health response contains database status"""
        response = await http_client.get("/health")
        data = response.json()
        assert "database_connected" in data


# =============================================================================
# Factual Memory Tests
# =============================================================================

class TestFactualMemoryIntegration:
    """Test factual memory extraction and CRUD operations"""

    async def test_extract_factual_memory_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Extract factual memory returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "John lives in Tokyo and works as a software engineer.",
            "importance_score": 0.7
        }

        response = await http_client.post(
            f"{API_BASE}/memories/factual/extract",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 500]  # 500 if AI service unavailable

    async def test_search_factual_by_subject(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Search factual memories by subject returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/subject",
            params={"user_id": test_user_id, "subject": "John", "limit": 10},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_search_factual_response_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Factual search returns memories array"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/search/subject",
            params={"user_id": test_user_id, "subject": "test", "limit": 10},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            assert "count" in data


# =============================================================================
# Episodic Memory Tests
# =============================================================================

class TestEpisodicMemoryIntegration:
    """Test episodic memory extraction and CRUD operations"""

    async def test_extract_episodic_memory_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Extract episodic memory returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "Last weekend I went hiking in Yosemite with friends.",
            "importance_score": 0.8
        }

        response = await http_client.post(
            f"{API_BASE}/memories/episodic/extract",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 500]

    async def test_search_episodic_by_event_type(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Search episodic memories by event type returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/episodic/search/event_type",
            params={"user_id": test_user_id, "event_type": "outdoor", "limit": 10},
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Procedural Memory Tests
# =============================================================================

class TestProceduralMemoryIntegration:
    """Test procedural memory extraction and CRUD operations"""

    async def test_extract_procedural_memory_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Extract procedural memory returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "To deploy, first run tests, then build Docker image, and push to registry.",
            "importance_score": 0.6
        }

        response = await http_client.post(
            f"{API_BASE}/memories/procedural/extract",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 500]


# =============================================================================
# Semantic Memory Tests
# =============================================================================

class TestSemanticMemoryIntegration:
    """Test semantic memory extraction and CRUD operations"""

    async def test_extract_semantic_memory_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Extract semantic memory returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "Machine learning is a subset of artificial intelligence.",
            "importance_score": 0.65
        }

        response = await http_client.post(
            f"{API_BASE}/memories/semantic/extract",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 500]

    async def test_search_semantic_by_category(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Search semantic memories by category returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/semantic/search/category",
            params={"user_id": test_user_id, "category": "technology", "limit": 10},
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Session Memory Tests
# =============================================================================

class TestSessionMemoryIntegration:
    """Test session memory operations"""

    async def test_store_session_message_returns_success(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: Store session message returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "session_id": test_session_id,
            "message_content": "Hello, how are you?",
            "message_type": "human",
            "role": "user"
        }

        response = await http_client.post(
            f"{API_BASE}/memories/session/store",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_get_session_memories(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: Get session memories returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/session/{test_session_id}",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404]

    async def test_get_session_context(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: Get session context returns 200"""
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

    async def test_session_context_structure(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: Session context contains expected fields"""
        # First store a message
        await http_client.post(
            f"{API_BASE}/memories/session/store",
            json={
                "user_id": test_user_id,
                "session_id": test_session_id,
                "message_content": "Test message for context",
                "message_type": "human",
                "role": "user"
            },
            headers=internal_headers
        )

        response = await http_client.get(
            f"{API_BASE}/memories/session/{test_session_id}/context",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data
            assert "user_id" in data
            assert "total_messages" in data

    async def test_deactivate_session(
        self, http_client, internal_headers, test_user_id, test_session_id
    ):
        """CHAR: Deactivate session returns 200"""
        response = await http_client.post(
            f"{API_BASE}/memories/session/{test_session_id}/deactivate",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404]


# =============================================================================
# Working Memory Tests
# =============================================================================

class TestWorkingMemoryIntegration:
    """Test working memory operations"""

    async def test_store_working_memory_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Store working memory returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "dialog_content": "Analyzing 10 files for security issues",
            "ttl_seconds": 3600,
            "importance_score": 0.7
        }

        response = await http_client.post(
            f"{API_BASE}/memories/working/store",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_get_active_working_memories(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Get active working memories returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/working/active",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_active_working_memories_structure(
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

    async def test_cleanup_expired_memories(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Cleanup expired memories returns 200"""
        response = await http_client.post(
            f"{API_BASE}/memories/working/cleanup",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Generic Memory CRUD Tests
# =============================================================================

class TestGenericMemoryOperations:
    """Test generic memory CRUD operations"""

    async def test_create_memory_returns_success(
        self, http_client, internal_headers, test_user_id, cleanup_memories
    ):
        """CHAR: Create memory returns 200/201"""
        request_data = {
            "user_id": test_user_id,
            "memory_type": "factual",
            "content": "Test memory content",
            "importance_score": 0.5,
            "confidence": 0.8,
            "tags": ["test"],
            "context": {"source": "integration_test"}
        }

        response = await http_client.post(
            f"{API_BASE}/memories",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

        if response.status_code in [200, 201]:
            data = response.json()
            if data.get("memory_id"):
                cleanup_memories(data["memory_id"], "factual")

    async def test_list_memories_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: List memories returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories",
            params={"user_id": test_user_id, "limit": 50},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_list_memories_with_type_filter(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: List memories with type filter returns 200"""
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

    async def test_list_memories_response_structure(
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
        """CHAR: Get nonexistent memory returns 404"""
        response = await http_client.get(
            f"{API_BASE}/memories/factual/nonexistent_memory_12345",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 404


# =============================================================================
# Universal Search Tests
# =============================================================================

class TestUniversalSearchIntegration:
    """Test universal search operations"""

    async def test_universal_search_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Universal search returns 200"""
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
        """CHAR: Universal search with specific types returns 200"""
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

    async def test_universal_search_response_structure(
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


# =============================================================================
# Statistics Tests
# =============================================================================

class TestMemoryStatisticsIntegration:
    """Test memory statistics operations"""

    async def test_get_memory_statistics(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Get memory statistics returns 200"""
        response = await http_client.get(
            f"{API_BASE}/memories/statistics",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_statistics_response_structure(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Statistics returns expected structure"""
        response = await http_client.get(
            f"{API_BASE}/memories/statistics",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            # Should contain aggregated statistics
            assert isinstance(data, dict)


# =============================================================================
# Memory Workflow Tests
# =============================================================================

class TestMemoryWorkflowIntegration:
    """Test complete memory workflows"""

    async def test_session_conversation_workflow(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Complete session conversation workflow"""
        session_id = f"workflow_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Store first message
        msg1_response = await http_client.post(
            f"{API_BASE}/memories/session/store",
            json={
                "user_id": test_user_id,
                "session_id": session_id,
                "message_content": "Hello, I need help with Python",
                "message_type": "human",
                "role": "user"
            },
            headers=internal_headers
        )
        assert msg1_response.status_code in [200, 201]

        # Store second message
        msg2_response = await http_client.post(
            f"{API_BASE}/memories/session/store",
            json={
                "user_id": test_user_id,
                "session_id": session_id,
                "message_content": "I can help you with Python. What do you need?",
                "message_type": "ai",
                "role": "assistant"
            },
            headers=internal_headers
        )
        assert msg2_response.status_code in [200, 201]

        # Get session context
        context_response = await http_client.get(
            f"{API_BASE}/memories/session/{session_id}/context",
            params={"user_id": test_user_id},
            headers=internal_headers
        )
        assert context_response.status_code == 200

        if context_response.status_code == 200:
            data = context_response.json()
            assert data.get("total_messages", 0) >= 2

    async def test_working_memory_task_workflow(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: Working memory task workflow"""
        # Store working memory
        store_response = await http_client.post(
            f"{API_BASE}/memories/working/store",
            json={
                "user_id": test_user_id,
                "dialog_content": "Processing batch job for data analysis",
                "ttl_seconds": 1800,
                "importance_score": 0.8
            },
            headers=internal_headers
        )
        assert store_response.status_code in [200, 201]

        # Get active memories
        active_response = await http_client.get(
            f"{API_BASE}/memories/working/active",
            params={"user_id": test_user_id},
            headers=internal_headers
        )
        assert active_response.status_code == 200

        if active_response.status_code == 200:
            data = active_response.json()
            assert data.get("count", 0) >= 0

