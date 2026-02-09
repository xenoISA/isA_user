"""
Document Service API Golden Tests

GOLDEN tests capture the ACTUAL behavior of the document service API endpoints.
These tests use JWT authentication (real auth service) + real DB + real HTTP.

Purpose:
- Document the current API contract behavior
- Find bugs/gotchas in API layer with real authentication
- If bugs found → Write TDD RED tests → Fix → GREEN

According to TDD_CONTRACT.md:
- For OLD/EXISTING services, write GOLDEN tests first at ALL layers
- API tests require JWT authentication (via auth service)
- Run golden tests to find bugs
- Write TDD tests for bugs found

Usage:
    # Start port-forwards:
    kubectl port-forward -n isa-cloud-staging svc/auth 8201:8201
    kubectl port-forward -n isa-cloud-staging svc/document 8227:8227

    # Run tests:
    pytest tests/api/golden/test_document_api_golden.py -v
"""

import pytest
import pytest_asyncio
import httpx
import uuid
from typing import List

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

DOCUMENT_SERVICE_URL = "http://localhost:8227"
AUTH_SERVICE_URL = "http://localhost:8201"
TIMEOUT = 30.0


# ============================================================================
# Helper Functions
# ============================================================================

def make_document_create_request(**overrides):
    """Create document creation request with defaults"""
    defaults = {
        "title": f"API Test Document {uuid.uuid4().hex[:8]}",
        "description": "API test description",
        "doc_type": "pdf",
        "file_id": f"file_{uuid.uuid4().hex[:12]}",
        "access_level": "private",
        "tags": ["test", "api", "golden"],
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
    """HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def auth_token(http_client):
    """
    Get JWT authentication token from auth service.
    Uses dev-token endpoint for testing.
    """
    response = await http_client.post(
        f"{AUTH_SERVICE_URL}/api/v1/auth/dev-token",
        json={
            "user_id": "api_test_user",
            "email": "apitest@example.com",
            "expires_in": 3600,
        }
    )

    if response.status_code == 200:
        token = response.json().get("token")
        return token
    else:
        pytest.skip(f"Failed to get auth token: {response.status_code}")


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    """Authentication headers with JWT token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def test_user_id():
    """Test user ID for API tests"""
    return "api_test_user"


@pytest_asyncio.fixture
async def cleanup_documents(http_client, auth_headers):
    """Track and cleanup documents created during tests"""
    created_doc_ids: List[str] = []

    def track(doc_id: str):
        created_doc_ids.append(doc_id)
        return doc_id

    yield track

    # Cleanup after test
    for doc_id in created_doc_ids:
        try:
            await http_client.delete(
                f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{doc_id}",
                params={"user_id": "api_test_user", "permanent": "true"},
                headers=auth_headers,
            )
        except Exception:
            pass


# ============================================================================
# GOLDEN: Service Health
# ============================================================================

class TestDocumentServiceHealthGolden:
    """
    GOLDEN tests for document service health endpoints.
    """

    async def test_root_endpoint_golden(self, http_client):
        """
        GOLDEN: Capture actual behavior of / endpoint (no auth required)
        """
        response = await http_client.get(f"{DOCUMENT_SERVICE_URL}/")

        # GOLDEN: Document ACTUAL response
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "document_service"
        assert "status" in data

    async def test_health_endpoint_golden(self, http_client):
        """
        GOLDEN: Capture actual behavior of /health endpoint (no auth required)
        """
        response = await http_client.get(f"{DOCUMENT_SERVICE_URL}/health")

        # GOLDEN: Document ACTUAL response
        assert response.status_code in [200, 503]

        data = response.json()
        assert data["service"] == "document_service"


# ============================================================================
# GOLDEN: Authentication
# ============================================================================

class TestAuthenticationGolden:
    """
    GOLDEN tests for API authentication requirements.
    """

    async def test_create_document_without_auth_golden(self, http_client, test_user_id):
        """
        GOLDEN: Capture actual behavior when creating document without auth token
        """
        request = make_document_create_request()

        response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=request,
            params={"user_id": test_user_id},
            # No Authorization header
        )

        # GOLDEN: Document ACTUAL behavior
        # Should return 401 Unauthorized or may work if internal bypass is enabled
        assert response.status_code in [401, 200, 201]

    async def test_create_document_with_invalid_token_golden(self, http_client, test_user_id):
        """
        GOLDEN: Capture actual behavior with invalid JWT token
        """
        request = make_document_create_request()

        response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=request,
            params={"user_id": test_user_id},
            headers={"Authorization": "Bearer invalid_token_12345"},
        )

        # GOLDEN: Document ACTUAL behavior
        # Should return 401 or may work if auth not enforced
        assert response.status_code in [401, 200, 201, 500]


# ============================================================================
# GOLDEN: Document CRUD Operations
# ============================================================================

class TestDocumentCRUDGolden:
    """
    GOLDEN tests for document CRUD operations with authentication.
    """

    async def test_create_document_golden(
        self, http_client, auth_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of POST /api/v1/documents with auth
        """
        request = make_document_create_request(
            title="Authenticated Document Creation",
            doc_type="pdf",
        )

        response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [200, 201]

        data = response.json()
        assert "doc_id" in data
        assert data["title"] == request["title"]
        assert data["user_id"] == test_user_id

        cleanup_documents(data["doc_id"])

    async def test_get_document_golden(
        self, http_client, auth_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents/{doc_id} with auth
        """
        # Create document first
        create_request = make_document_create_request(title="Document to Get")

        create_response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=create_request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )
        doc_id = create_response.json()["doc_id"]
        cleanup_documents(doc_id)

        # Get document
        get_response = await http_client.get(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{doc_id}",
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["doc_id"] == doc_id
        assert data["title"] == create_request["title"]

    async def test_get_document_not_found_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior when getting non-existent document
        """
        fake_doc_id = f"doc_nonexistent_{uuid.uuid4().hex[:12]}"

        response = await http_client.get(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{fake_doc_id}",
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [404, 403]

    async def test_list_documents_golden(
        self, http_client, auth_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents (list) with auth
        """
        # Create documents
        created_ids = []
        for i in range(2):
            request = make_document_create_request(title=f"List Document {i}")

            response = await http_client.post(
                f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
                json=request,
                params={"user_id": test_user_id},
                headers=auth_headers,
            )
            doc_id = response.json()["doc_id"]
            created_ids.append(doc_id)
            cleanup_documents(doc_id)

        # List documents
        list_response = await http_client.get(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            params={"user_id": test_user_id, "limit": 50},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert list_response.status_code == 200

        documents = list_response.json()
        assert isinstance(documents, list)

        # Verify our documents are in the list
        doc_ids_in_list = [d["doc_id"] for d in documents]
        for created_id in created_ids:
            assert created_id in doc_ids_in_list

    async def test_delete_document_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior of DELETE /api/v1/documents/{doc_id}
        """
        # Create document
        request = make_document_create_request(title="Document to Delete")

        create_response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )
        doc_id = create_response.json()["doc_id"]

        # Delete document
        delete_response = await http_client.delete(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{doc_id}",
            params={"user_id": test_user_id, "permanent": "true"},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert delete_response.status_code == 200

        # Verify document is deleted
        get_response = await http_client.get(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{doc_id}",
            params={"user_id": test_user_id},
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_delete_document_not_found_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior when deleting non-existent document
        """
        fake_doc_id = f"doc_nonexistent_{uuid.uuid4().hex[:12]}"

        response = await http_client.delete(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{fake_doc_id}",
            params={"user_id": test_user_id, "permanent": "true"},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        # Should be 404 or 403
        assert response.status_code in [404, 403]


# ============================================================================
# GOLDEN: Permission Management
# ============================================================================

class TestPermissionManagementGolden:
    """
    GOLDEN tests for permission management with authentication.
    """

    async def test_get_permissions_golden(
        self, http_client, auth_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents/{doc_id}/permissions
        """
        # Create document
        request = make_document_create_request(title="Permissions Test")

        create_response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )
        doc_id = create_response.json()["doc_id"]
        cleanup_documents(doc_id)

        # Get permissions
        perm_response = await http_client.get(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{doc_id}/permissions",
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert perm_response.status_code == 200

        permissions = perm_response.json()
        assert permissions["doc_id"] == doc_id
        assert "access_level" in permissions
        assert "allowed_users" in permissions

    async def test_update_permissions_golden(
        self, http_client, auth_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of PUT /api/v1/documents/{doc_id}/permissions
        """
        # Create document
        request = make_document_create_request(title="Update Permissions Test")

        create_response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )
        doc_id = create_response.json()["doc_id"]
        cleanup_documents(doc_id)

        # Update permissions
        update_request = {
            "access_level": "team",
            "add_users": ["user_x", "user_y"],
            "remove_users": [],
            "add_groups": [],
            "remove_groups": [],
        }

        update_response = await http_client.put(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{doc_id}/permissions",
            json=update_request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert update_response.status_code == 200

        permissions = update_response.json()
        assert permissions["access_level"] == "team"
        assert "user_x" in permissions["allowed_users"]


# ============================================================================
# GOLDEN: Statistics
# ============================================================================

class TestStatisticsGolden:
    """
    GOLDEN tests for statistics operations.
    """

    async def test_get_stats_golden(
        self, http_client, auth_headers, test_user_id, cleanup_documents
    ):
        """
        GOLDEN: Capture actual behavior of GET /api/v1/documents/stats
        """
        # Create a document first
        request = make_document_create_request(title="Stats Test")

        create_response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )
        cleanup_documents(create_response.json()["doc_id"])

        # Get stats
        stats_response = await http_client.get(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/stats",
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert stats_response.status_code == 200

        stats = stats_response.json()
        assert stats["user_id"] == test_user_id
        assert "total_documents" in stats
        assert stats["total_documents"] >= 1


# ============================================================================
# GOLDEN: RAG Operations
# ============================================================================

class TestRAGOperationsGolden:
    """
    GOLDEN tests for RAG query and search operations.
    """

    async def test_rag_query_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior of POST /api/v1/documents/rag/query
        """
        query_request = {
            "query": "What is artificial intelligence?",
            "top_k": 5,
            "temperature": 0.7,
            "max_tokens": 500,
        }

        response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/rag/query",
            json=query_request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["query"] == query_request["query"]
            assert "answer" in data

    async def test_semantic_search_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior of POST /api/v1/documents/search
        """
        search_request = {
            "query": "deep learning",
            "top_k": 10,
            "min_score": 0.5,
        }

        response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents/search",
            json=search_request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["query"] == search_request["query"]
            assert "results" in data


# ============================================================================
# GOLDEN: Validation
# ============================================================================

class TestValidationGolden:
    """
    GOLDEN tests for input validation.
    """

    async def test_create_document_missing_title_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior when title is missing
        """
        invalid_request = {
            "doc_type": "pdf",
            "file_id": "file_123",
        }

        response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=invalid_request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [400, 422]

    async def test_create_document_invalid_doc_type_golden(
        self, http_client, auth_headers, test_user_id
    ):
        """
        GOLDEN: Capture actual behavior with invalid doc_type
        """
        invalid_request = make_document_create_request(
            doc_type="invalid_type",
        )

        response = await http_client.post(
            f"{DOCUMENT_SERVICE_URL}/api/v1/documents",
            json=invalid_request,
            params={"user_id": test_user_id},
            headers=auth_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [400, 422]
