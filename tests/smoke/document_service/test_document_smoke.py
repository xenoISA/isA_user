"""
Document Service Smoke Tests

Quick sanity checks to verify document_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Purpose:
- Verify service is up and responding
- Test basic CRUD operations work
- Test critical user flows (create doc, list, update, delete)
- Validate data contracts are honored

Usage:
    pytest tests/smoke/document_service -v
    pytest tests/smoke/document_service -v -k "health"

Environment Variables:
    DOCUMENT_BASE_URL: Base URL for document service (default: http://localhost:8227)
"""

import os
import pytest
import uuid
import httpx

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("DOCUMENT_BASE_URL", "http://localhost:8227")
API_V1 = f"{BASE_URL}/api/v1/documents"
TIMEOUT = 15.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for smoke tests"""
    return f"smoke_test_{uuid.uuid4().hex[:8]}"


def unique_file_id() -> str:
    """Generate unique file ID for smoke tests"""
    return f"file_smoke_{uuid.uuid4().hex[:12]}"


def make_document_request(**overrides) -> dict:
    """Create document request with defaults"""
    defaults = {
        "title": f"Smoke Test Doc {uuid.uuid4().hex[:8]}",
        "description": "Smoke test description",
        "doc_type": "pdf",
        "file_id": unique_file_id(),
        "access_level": "private",
        "tags": ["smoke", "test"],
        "chunking_strategy": "semantic",
        "metadata": {"smoke_test": True},
    }
    defaults.update(overrides)
    return defaults


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client for smoke tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
async def internal_headers():
    """Headers for internal service calls (bypass auth)"""
    return {"X-Internal-Call": "true"}


@pytest.fixture
async def test_document(http_client, internal_headers):
    """
    Create a test document for smoke tests.

    This fixture creates a document, yields it for testing,
    and cleans it up afterward.
    """
    user_id = unique_user_id()

    # Create document
    response = await http_client.post(
        API_V1,
        json=make_document_request(title="Smoke Test Document"),
        params={"user_id": user_id},
        headers=internal_headers,
    )

    if response.status_code in [200, 201]:
        doc_data = response.json()
        doc_data["_test_user_id"] = user_id
        yield doc_data

        # Cleanup - try to delete the document
        try:
            doc_id = doc_data["doc_id"]
            await http_client.delete(
                f"{API_V1}/{doc_id}",
                params={"user_id": user_id, "permanent": "true"},
                headers=internal_headers,
            )
        except Exception:
            pass  # Ignore cleanup errors
    else:
        pytest.skip(f"Could not create test document: {response.status_code}")


# =============================================================================
# SMOKE TEST 1: Health Checks
# =============================================================================

class TestHealthSmoke:
    """Smoke: Health endpoint sanity checks"""

    async def test_root_endpoint_responds(self, http_client):
        """SMOKE: GET / returns 200"""
        response = await http_client.get(f"{BASE_URL}/")
        assert response.status_code == 200, \
            f"Root check failed: {response.status_code}"

        data = response.json()
        assert data["service"] == "document_service"
        assert "status" in data

    async def test_health_endpoint_responds(self, http_client):
        """SMOKE: GET /health returns 200"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code in [200, 503], \
            f"Health check failed: {response.status_code}"

        data = response.json()
        assert data["service"] == "document_service"
        assert "status" in data
        assert "database" in data


# =============================================================================
# SMOKE TEST 2: Document CRUD
# =============================================================================

class TestDocumentCRUDSmoke:
    """Smoke: Document CRUD operation sanity checks"""

    async def test_create_document_works(self, http_client, internal_headers):
        """SMOKE: POST /documents creates a document"""
        user_id = unique_user_id()

        response = await http_client.post(
            API_V1,
            json=make_document_request(),
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code in [200, 201], \
            f"Create document failed: {response.status_code} - {response.text}"

        data = response.json()
        assert "doc_id" in data, "Response missing doc_id"
        assert data["user_id"] == user_id, "User ID mismatch"
        assert data["status"] in ["draft", "indexing", "indexed"], "Invalid status"

        # Cleanup
        await http_client.delete(
            f"{API_V1}/{data['doc_id']}",
            params={"user_id": user_id, "permanent": "true"},
            headers=internal_headers,
        )

    async def test_get_document_works(self, http_client, internal_headers, test_document):
        """SMOKE: GET /documents/{id} retrieves document"""
        doc_id = test_document["doc_id"]
        user_id = test_document["_test_user_id"]

        response = await http_client.get(
            f"{API_V1}/{doc_id}",
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code == 200, \
            f"Get document failed: {response.status_code}"

        data = response.json()
        assert data["doc_id"] == doc_id

    async def test_list_documents_works(self, http_client, internal_headers, test_document):
        """SMOKE: GET /documents returns document list"""
        user_id = test_document["_test_user_id"]

        response = await http_client.get(
            API_V1,
            params={"user_id": user_id, "limit": 50},
            headers=internal_headers,
        )

        assert response.status_code == 200, \
            f"List documents failed: {response.status_code}"

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1, "Should have at least 1 document"

    async def test_delete_document_works(self, http_client, internal_headers):
        """SMOKE: DELETE /documents/{id} deletes document"""
        user_id = unique_user_id()

        # Create document to delete
        create_response = await http_client.post(
            API_V1,
            json=make_document_request(title="Doc to Delete"),
            params={"user_id": user_id},
            headers=internal_headers,
        )
        doc_id = create_response.json()["doc_id"]

        # Delete document
        response = await http_client.delete(
            f"{API_V1}/{doc_id}",
            params={"user_id": user_id, "permanent": "true"},
            headers=internal_headers,
        )

        assert response.status_code == 200, \
            f"Delete document failed: {response.status_code}"

        # Verify deletion
        get_response = await http_client.get(
            f"{API_V1}/{doc_id}",
            params={"user_id": user_id},
            headers=internal_headers,
        )
        assert get_response.status_code == 404


# =============================================================================
# SMOKE TEST 3: Permission Management
# =============================================================================

class TestPermissionSmoke:
    """Smoke: Permission operation sanity checks"""

    async def test_get_permissions_works(self, http_client, internal_headers, test_document):
        """SMOKE: GET /documents/{id}/permissions returns permissions"""
        doc_id = test_document["doc_id"]
        user_id = test_document["_test_user_id"]

        response = await http_client.get(
            f"{API_V1}/{doc_id}/permissions",
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code == 200, \
            f"Get permissions failed: {response.status_code}"

        data = response.json()
        assert data["doc_id"] == doc_id
        assert "access_level" in data
        assert "allowed_users" in data

    async def test_update_permissions_works(self, http_client, internal_headers, test_document):
        """SMOKE: PUT /documents/{id}/permissions updates permissions"""
        doc_id = test_document["doc_id"]
        user_id = test_document["_test_user_id"]

        response = await http_client.put(
            f"{API_V1}/{doc_id}/permissions",
            json={
                "access_level": "team",
                "add_users": ["smoke_user_1"],
                "remove_users": [],
                "add_groups": [],
                "remove_groups": [],
            },
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code == 200, \
            f"Update permissions failed: {response.status_code}"

        data = response.json()
        assert data["access_level"] == "team"
        assert "smoke_user_1" in data["allowed_users"]


# =============================================================================
# SMOKE TEST 4: Statistics
# =============================================================================

class TestStatsSmoke:
    """Smoke: Statistics sanity checks"""

    async def test_get_stats_works(self, http_client, internal_headers, test_document):
        """SMOKE: GET /documents/stats returns user statistics"""
        user_id = test_document["_test_user_id"]

        response = await http_client.get(
            f"{API_V1}/stats",
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code == 200, \
            f"Get stats failed: {response.status_code}"

        data = response.json()
        assert data["user_id"] == user_id
        assert "total_documents" in data
        assert data["total_documents"] >= 1


# =============================================================================
# SMOKE TEST 5: RAG Operations
# =============================================================================

class TestRAGSmoke:
    """Smoke: RAG operation sanity checks"""

    async def test_rag_query_endpoint_responds(self, http_client, internal_headers):
        """SMOKE: POST /documents/rag/query responds"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/rag/query",
            json={
                "query": "What is machine learning?",
                "top_k": 5,
            },
            params={"user_id": user_id},
            headers=internal_headers,
        )

        # RAG may fail if Digital Analytics is not available, but endpoint should respond
        assert response.status_code in [200, 500], \
            f"RAG query endpoint failed: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert "query" in data
            assert "answer" in data

    async def test_search_endpoint_responds(self, http_client, internal_headers):
        """SMOKE: POST /documents/search responds"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{API_V1}/search",
            json={
                "query": "neural networks",
                "top_k": 10,
            },
            params={"user_id": user_id},
            headers=internal_headers,
        )

        # Search may fail if Digital Analytics is not available
        assert response.status_code in [200, 500], \
            f"Search endpoint failed: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert "query" in data
            assert "results" in data


# =============================================================================
# SMOKE TEST 6: Critical User Flow
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical user flow end-to-end"""

    async def test_complete_document_lifecycle(self, http_client, internal_headers):
        """
        SMOKE: Complete document lifecycle works end-to-end

        Tests: Create -> Get -> Update Permissions -> Get Stats -> Delete
        """
        user_id = unique_user_id()
        doc_id = None

        try:
            # Step 1: Create document
            create_response = await http_client.post(
                API_V1,
                json=make_document_request(title="Lifecycle Test Doc"),
                params={"user_id": user_id},
                headers=internal_headers,
            )
            assert create_response.status_code in [200, 201], "Failed to create document"
            doc_id = create_response.json()["doc_id"]

            # Step 2: Get document
            get_response = await http_client.get(
                f"{API_V1}/{doc_id}",
                params={"user_id": user_id},
                headers=internal_headers,
            )
            assert get_response.status_code == 200, "Failed to get document"
            assert get_response.json()["doc_id"] == doc_id

            # Step 3: Update permissions
            perm_response = await http_client.put(
                f"{API_V1}/{doc_id}/permissions",
                json={
                    "access_level": "team",
                    "add_users": ["lifecycle_user"],
                },
                params={"user_id": user_id},
                headers=internal_headers,
            )
            assert perm_response.status_code == 200, "Failed to update permissions"

            # Step 4: Get user stats
            stats_response = await http_client.get(
                f"{API_V1}/stats",
                params={"user_id": user_id},
                headers=internal_headers,
            )
            assert stats_response.status_code == 200, "Failed to get stats"
            assert stats_response.json()["total_documents"] >= 1

            # Step 5: Delete document
            delete_response = await http_client.delete(
                f"{API_V1}/{doc_id}",
                params={"user_id": user_id, "permanent": "true"},
                headers=internal_headers,
            )
            assert delete_response.status_code == 200, "Failed to delete document"

            # Step 6: Verify deletion
            verify_response = await http_client.get(
                f"{API_V1}/{doc_id}",
                params={"user_id": user_id},
                headers=internal_headers,
            )
            assert verify_response.status_code == 404, "Document should be deleted"

        finally:
            # Cleanup if document was created but test failed mid-way
            if doc_id:
                try:
                    await http_client.delete(
                        f"{API_V1}/{doc_id}",
                        params={"user_id": user_id, "permanent": "true"},
                        headers=internal_headers,
                    )
                except Exception:
                    pass


# =============================================================================
# SMOKE TEST 7: Error Handling
# =============================================================================

class TestErrorHandlingSmoke:
    """Smoke: Error handling sanity checks"""

    async def test_not_found_returns_404(self, http_client, internal_headers):
        """SMOKE: Non-existent document returns 404"""
        fake_doc_id = f"doc_nonexistent_{uuid.uuid4().hex[:8]}"
        user_id = unique_user_id()

        response = await http_client.get(
            f"{API_V1}/{fake_doc_id}",
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code in [404, 403], \
            f"Expected 404/403, got {response.status_code}"

    async def test_invalid_request_returns_error(self, http_client, internal_headers):
        """SMOKE: Invalid request returns 400 or 422"""
        user_id = unique_user_id()

        response = await http_client.post(
            API_V1,
            json={"doc_type": "pdf"},  # Missing required title
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_invalid_doc_type_returns_error(self, http_client, internal_headers):
        """SMOKE: Invalid doc_type returns validation error"""
        user_id = unique_user_id()

        response = await http_client.post(
            API_V1,
            json=make_document_request(doc_type="invalid_type"),
            params={"user_id": user_id},
            headers=internal_headers,
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# SUMMARY
# =============================================================================
"""
DOCUMENT SERVICE SMOKE TESTS SUMMARY:

Test Coverage (16 tests total):

1. Health (2 tests):
   - / responds with 200
   - /health responds with 200/503

2. Document CRUD (4 tests):
   - Create document works
   - Get document works
   - List documents works
   - Delete document works

3. Permissions (2 tests):
   - Get permissions works
   - Update permissions works

4. Statistics (1 test):
   - Get stats works

5. RAG (2 tests):
   - RAG query endpoint responds
   - Search endpoint responds

6. Critical Flow (1 test):
   - Complete lifecycle: Create -> Get -> Permissions -> Stats -> Delete

7. Error Handling (3 tests):
   - Not found returns 404
   - Invalid request returns error
   - Invalid doc_type returns error

Characteristics:
- Fast execution (< 30 seconds)
- No external dependencies (other than running document_service)
- Tests critical paths only
- Validates deployment health

Run with:
    pytest tests/smoke/document_service -v
    pytest tests/smoke/document_service -v --timeout=60
"""
