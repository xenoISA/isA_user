"""
Document Service Integration Golden Tests

GOLDEN tests capture the ACTUAL behavior of the document service at integration level.
These tests use real HTTP requests + real DB (via port-forward to staging K8s).

Purpose:
- Document the current integration behavior
- Find bugs/gotchas in HTTP endpoints + database interactions
- If bugs found → Write TDD RED tests → Fix → GREEN

According to TDD_CONTRACT.md:
- For OLD/EXISTING services, write GOLDEN tests first at ALL layers
- Integration tests use X-Internal-Call header (bypass auth)
- Run golden tests to find bugs
- Write TDD tests for bugs found

Usage:
    # Start port-forward first:
    kubectl port-forward -n isa-cloud-staging svc/document 8227:8227

    # Run tests:
    pytest tests/integration/golden/test_document_crud_golden.py -v
"""

import pytest
import pytest_asyncio
import httpx
import uuid
from typing import List

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

DOCUMENT_SERVICE_URL = "http://localhost:8227"
API_BASE = f"{DOCUMENT_SERVICE_URL}/api/v1/documents"
TIMEOUT = 30.0


# ============================================================================
# Helper Functions
# ============================================================================

def make_document_create_request(**overrides):
    """Create document creation request with defaults"""
    defaults = {
        "title": f"Test Document {uuid.uuid4().hex[:8]}",
        "description": "Test description",
        "doc_type": "pdf",
        "file_id": f"file_{uuid.uuid4().hex[:12]}",
        "access_level": "private",
        "tags": ["test", "golden"],
        "chunking_strategy": "semantic",
        "metadata": {},
    }
    defaults.update(overrides)
    return defaults


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for integration tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def internal_headers():
    """
    Internal service authentication headers.
    For integration tests, we use internal bypass (no JWT required).
    """
    return {"X-Internal-Call": "true"}


@pytest_asyncio.fixture
async def test_user_id():
    """Test user ID for integration tests"""
    return f"user_golden_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def cleanup_documents(http_client, internal_headers):
    """Track and cleanup documents created during tests"""
    created_doc_ids: List[str] = []

    def track(doc_id: str):
        created_doc_ids.append(doc_id)
        return doc_id

    yield track

    # Cleanup after test
    for doc_id in created_doc_ids:
        try:
            # Use the user_id that was used to create the document
            await http_client.delete(
                f"{API_BASE}/{doc_id}",
                params={"user_id": "cleanup_user", "permanent": "true"},
                headers=internal_headers
            )
        except Exception:
            pass


# ============================================================================
# GOLDEN: Service Health Check
# ============================================================================

class TestDocumentServiceHealthGolden:
    """
    GOLDEN tests for document service health and status endpoints.
    """

    async def test_root_endpoint_golden(self, http_client):
        """
        GOLDEN: Capture actual behavior of / endpoint
        """
        response = await http_client.get(f"{DOCUMENT_SERVICE_URL}/")

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "document_service"
        assert "status" in data
        assert "database_connected" in data
        assert "timestamp" in data

    async def test_health_endpoint_golden(self, http_client):
        """
        GOLDEN: Capture actual behavior of /health endpoint
        """
        response = await http_client.get(f"{DOCUMENT_SERVICE_URL}/health")

        # GOLDEN: Document ACTUAL response
        assert response.status_code in [200, 503]

        data = response.json()
        assert data["service"] == "document_service"
        assert "status" in data
        assert "database" in data


# ============================================================================
# GOLDEN: Document CRUD Operations
# ============================================================================

class TestDocumentCRUDGolden:
    """
    GOLDEN tests for document CRUD operations via HTTP.
    Captures ACTUAL integration behavior with real DB.
    """

    async def test_create_document_golden(
        self, http_client, internal_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of POST /api/v1/documents

        Tests document creation with all required fields.
        """
        # Create request
        request = make_document_create_request(
            title="Golden Test Document",
            description="Testing document creation",
            doc_type="pdf",
        )

        # Execute
        response = await http_client.post(
            API_BASE,
            json=request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code == 201

        data = response.json()
        assert "doc_id" in data
        assert data["title"] == request["title"]
        assert data["description"] == request["description"]
        assert data["doc_type"] == request["doc_type"]
        assert data["file_id"] == request["file_id"]
        assert data["user_id"] == test_user_id
        assert data["status"] in ["draft", "indexing", "indexed"]
        assert data["access_level"] == "private"
        assert data["tags"] == request["tags"]

        cleanup_documents(data["doc_id"])

    async def test_get_document_golden(
        self, http_client, internal_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents/{doc_id}

        Tests retrieving a document by ID.
        """
        # First create a document
        create_request = make_document_create_request(title="Document to Get")

        create_response = await http_client.post(
            API_BASE,
            json=create_request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )
        assert create_response.status_code == 201

        created_doc = create_response.json()
        doc_id = created_doc["doc_id"]
        cleanup_documents(doc_id)

        # Now GET the document
        get_response = await http_client.get(
            f"{API_BASE}/{doc_id}",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert get_response.status_code == 200

        retrieved_doc = get_response.json()
        assert retrieved_doc["doc_id"] == doc_id
        assert retrieved_doc["title"] == create_request["title"]
        assert retrieved_doc["user_id"] == test_user_id

    async def test_get_document_not_found_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior of GET for non-existent document
        """
        fake_doc_id = f"doc_nonexistent_{uuid.uuid4().hex[:12]}"

        response = await http_client.get(
            f"{API_BASE}/{fake_doc_id}",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        # Could be 404 or 403 depending on permission check order
        assert response.status_code in [404, 403]

    async def test_list_documents_golden(
        self, http_client, internal_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents (list)

        Tests listing documents for a user.
        """
        # Create multiple documents
        created_docs = []
        for i in range(3):
            request = make_document_create_request(
                title=f"List Test Document {i}",
            )

            response = await http_client.post(
                API_BASE,
                json=request,
                params={"user_id": test_user_id},
                headers=internal_headers,
            )
            assert response.status_code == 201

            doc = response.json()
            created_docs.append(doc)
            cleanup_documents(doc["doc_id"])

        # List documents
        list_response = await http_client.get(
            API_BASE,
            params={"user_id": test_user_id, "limit": 50},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert list_response.status_code == 200

        documents = list_response.json()
        assert isinstance(documents, list)

        # Verify our created documents are in the list
        doc_ids_in_list = [d["doc_id"] for d in documents]
        created_doc_ids = [d["doc_id"] for d in created_docs]

        for created_id in created_doc_ids:
            assert created_id in doc_ids_in_list

    async def test_delete_document_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior of DELETE /api/v1/documents/{doc_id}

        Tests document deletion (permanent).
        """
        # Create document
        request = make_document_create_request(title="Document to Delete")

        create_response = await http_client.post(
            API_BASE,
            json=request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )
        doc_id = create_response.json()["doc_id"]

        # Delete document
        delete_response = await http_client.delete(
            f"{API_BASE}/{doc_id}",
            params={"user_id": test_user_id, "permanent": "true"},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert delete_response.status_code == 200

        data = delete_response.json()
        assert data.get("success") is True

        # Verify document is deleted (GET should return 404)
        get_response = await http_client.get(
            f"{API_BASE}/{doc_id}",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )
        assert get_response.status_code == 404


# ============================================================================
# GOLDEN: Permission Management
# ============================================================================

class TestPermissionManagementGolden:
    """
    GOLDEN tests for permission management operations.
    """

    async def test_get_document_permissions_golden(
        self, http_client, internal_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents/{doc_id}/permissions
        """
        # Create document
        request = make_document_create_request(
            title="Permission Test Document",
            access_level="private",
        )

        create_response = await http_client.post(
            API_BASE,
            json=request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )
        doc_id = create_response.json()["doc_id"]
        cleanup_documents(doc_id)

        # Get permissions
        perm_response = await http_client.get(
            f"{API_BASE}/{doc_id}/permissions",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert perm_response.status_code == 200

        permissions = perm_response.json()
        assert permissions["doc_id"] == doc_id
        assert permissions["access_level"] == "private"
        assert "allowed_users" in permissions
        assert "allowed_groups" in permissions

    async def test_update_document_permissions_golden(
        self, http_client, internal_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of PUT /api/v1/documents/{doc_id}/permissions
        """
        # Create document
        request = make_document_create_request(
            title="Update Permissions Document",
            access_level="private",
        )

        create_response = await http_client.post(
            API_BASE,
            json=request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )
        doc_id = create_response.json()["doc_id"]
        cleanup_documents(doc_id)

        # Update permissions
        update_request = {
            "access_level": "team",
            "add_users": ["user_a", "user_b"],
            "remove_users": [],
            "add_groups": ["group_1"],
            "remove_groups": [],
        }

        update_response = await http_client.put(
            f"{API_BASE}/{doc_id}/permissions",
            json=update_request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert update_response.status_code == 200

        permissions = update_response.json()
        assert permissions["doc_id"] == doc_id
        assert permissions["access_level"] == "team"
        assert "user_a" in permissions["allowed_users"]
        assert "user_b" in permissions["allowed_users"]
        assert "group_1" in permissions["allowed_groups"]


# ============================================================================
# GOLDEN: Statistics
# ============================================================================

class TestStatisticsGolden:
    """
    GOLDEN tests for statistics operations.
    """

    async def test_get_user_stats_golden(
        self, http_client, internal_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents/stats
        """
        # Create a few documents first
        for i in range(2):
            request = make_document_create_request(title=f"Stats Test Document {i}")

            response = await http_client.post(
                API_BASE,
                json=request,
                params={"user_id": test_user_id},
                headers=internal_headers,
            )
            cleanup_documents(response.json()["doc_id"])

        # Get stats
        stats_response = await http_client.get(
            f"{API_BASE}/stats",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert stats_response.status_code == 200

        stats = stats_response.json()
        assert stats["user_id"] == test_user_id
        assert stats["total_documents"] >= 2
        assert "indexed_documents" in stats
        assert "total_chunks" in stats
        assert "by_type" in stats
        assert "by_status" in stats


# ============================================================================
# GOLDEN: RAG Operations
# ============================================================================

class TestRAGOperationsGolden:
    """
    GOLDEN tests for RAG query and semantic search operations.
    """

    async def test_rag_query_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior of POST /api/v1/documents/rag/query

        Note: May not have actual indexed documents, so response might be minimal.
        This test documents the ACTUAL API response format.
        """
        # RAG query request
        query_request = {
            "query": "What is machine learning?",
            "top_k": 5,
            "temperature": 0.7,
            "max_tokens": 500,
        }

        response = await http_client.post(
            f"{API_BASE}/rag/query",
            json=query_request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        # May be 200 with empty results, or 500 if Digital Analytics unavailable
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["query"] == query_request["query"]
            assert "answer" in data
            assert "sources" in data
            assert "confidence" in data

    async def test_semantic_search_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior of POST /api/v1/documents/search

        Note: May not have actual indexed documents.
        This test documents the ACTUAL API response format.
        """
        # Search request
        search_request = {
            "query": "neural networks",
            "top_k": 10,
            "min_score": 0.5,
        }

        response = await http_client.post(
            f"{API_BASE}/search",
            json=search_request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        # May be 200 with empty results, or 500 if Digital Analytics unavailable
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["query"] == search_request["query"]
            assert "results" in data
            assert "total_count" in data
            assert isinstance(data["results"], list)


# ============================================================================
# GOLDEN: Validation and Error Handling
# ============================================================================

class TestValidationGolden:
    """
    GOLDEN tests for input validation and error handling.
    """

    async def test_create_document_missing_required_fields_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior when required fields are missing
        """
        # Missing title
        invalid_request = {
            "doc_type": "pdf",
            "file_id": "file_123",
        }

        response = await http_client.post(
            API_BASE,
            json=invalid_request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        # Should be 422 (validation error) or 400 (bad request)
        assert response.status_code in [400, 422]

    async def test_create_document_invalid_doc_type_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior with invalid doc_type
        """
        invalid_request = make_document_create_request(
            doc_type="invalid_type",
        )

        response = await http_client.post(
            API_BASE,
            json=invalid_request,
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [400, 422]

    async def test_missing_user_id_parameter_golden(
        self, http_client, internal_headers
    ):
        """
        GOLDEN: Capture actual behavior when user_id parameter is missing
        """
        request = make_document_create_request()

        response = await http_client.post(
            API_BASE,
            json=request,
            # No user_id parameter
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        # Should be 400 or 422
        assert response.status_code in [400, 422]
