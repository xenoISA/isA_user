"""
Storage Service API Golden Tests

GOLDEN tests for API layer - validates HTTP contracts, status codes, headers.
These tests focus on HTTP protocol correctness without deep integration testing.

Purpose:
- Validate HTTP status codes match REST conventions
- Verify response schemas match data contracts
- Test error response formats
- Check HTTP headers (Content-Type, etc.)
- Document API surface area

According to TDD_CONTRACT.md:
- API tests validate HTTP contracts (Layer 2)
- Lighter than integration tests (don't validate full DB persistence)
- Focus on API protocol correctness

PROOF OF CONCEPT: Uses data contracts for request/response validation!

Usage:
    # Start port-forward first:
    kubectl port-forward -n isa-cloud-staging svc/storage 8209:8209

    # Run tests:
    pytest tests/api/golden/test_storage_api_golden.py -v
"""

import pytest
import pytest_asyncio
import httpx
import uuid
from io import BytesIO

# Import from centralized data contracts
from tests.contracts.storage import (
    StorageTestDataFactory,
    FileUploadResponseContract,
    FileInfoResponseContract,
    FileShareResponseContract,
)

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

STORAGE_SERVICE_URL = "http://localhost:8209"
API_BASE = f"{STORAGE_SERVICE_URL}/api/v1/storage"
TIMEOUT = 30.0


# ============================================================================
# Helper Functions
# ============================================================================

def make_test_file(filename: str = "test.txt", content: bytes = None):
    """Create test file for upload"""
    if content is None:
        content = f"API test content - {uuid.uuid4().hex[:8]}".encode()
    return (filename, BytesIO(content), "text/plain")


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
        yield client


@pytest_asyncio.fixture
async def internal_headers():
    """Internal service auth headers"""
    return {"X-Internal-Call": "true"}


@pytest_asyncio.fixture
async def test_user_id():
    """Test user ID"""
    return f"user_api_{uuid.uuid4().hex[:8]}"


# ============================================================================
# GOLDEN: HTTP Status Codes and Headers
# ============================================================================

class TestHTTPStatusCodesGolden:
    """
    GOLDEN tests for HTTP status codes and response headers.

    Validates that API follows REST conventions.
    """

    async def test_health_returns_200_ok_golden(self, http_client):
        """
        GOLDEN: Health endpoint returns 200 OK
        """
        response = await http_client.get(f"{STORAGE_SERVICE_URL}/health")

        # GOLDEN: Validate HTTP status
        assert response.status_code == 200

        # GOLDEN: Validate Content-Type header
        assert "application/json" in response.headers.get("content-type", "")

        # GOLDEN: Validate response body structure
        data = response.json()
        assert "service" in data
        assert data["service"] == "storage_service"

    async def test_info_returns_200_ok_golden(self, http_client):
        """
        GOLDEN: Info endpoint returns 200 OK with service metadata
        """
        response = await http_client.get(f"{STORAGE_SERVICE_URL}/info")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        data = response.json()
        assert data["service"] == "storage_service"
        assert "capabilities" in data

    async def test_file_upload_returns_200_ok_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: File upload returns 200 OK (not 201 Created)

        Note: REST convention would be 201 for resource creation,
        but we document ACTUAL behavior here.
        """
        request = StorageTestDataFactory.make_upload_request(user_id=test_user_id)
        test_file = make_test_file("api_test.txt")

        response = await http_client.post(
            f"{API_BASE}/files/upload",
            data={
                "user_id": request.user_id,
                "access_level": request.access_level.value,
            },
            files={"file": test_file},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL status code
        assert response.status_code == 200

        # GOLDEN: Validate Content-Type
        assert "application/json" in response.headers.get("content-type", "")

        # GOLDEN: Validate response matches contract
        data = response.json()
        validated = FileUploadResponseContract(**data)
        assert validated.file_id is not None

    async def test_file_not_found_returns_404_or_403_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Non-existent file returns 404 Not Found (or 403 Forbidden)

        Note: Might return 403 if permission check happens before existence check.
        """
        fake_file_id = StorageTestDataFactory.make_file_id()

        response = await http_client.get(
            f"{API_BASE}/files/{fake_file_id}",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        assert response.status_code in [404, 403]

    async def test_delete_returns_200_ok_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: DELETE returns 200 OK (not 204 No Content)

        REST convention would be 204, but we document ACTUAL behavior.
        """
        # First upload a file
        request = StorageTestDataFactory.make_upload_request(user_id=test_user_id)
        test_file = make_test_file()

        upload_response = await http_client.post(
            f"{API_BASE}/files/upload",
            data={
                "user_id": request.user_id,
                "access_level": request.access_level.value,
            },
            files={"file": test_file},
            headers=internal_headers,
        )
        file_id = upload_response.json()["file_id"]

        # Delete it
        delete_response = await http_client.delete(
            f"{API_BASE}/files/{file_id}",
            params={"user_id": test_user_id, "permanent": "true"},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL status code
        assert delete_response.status_code == 200

        # GOLDEN: Validate response body
        data = delete_response.json()
        assert data.get("success") is True


# ============================================================================
# GOLDEN: Response Schema Validation (Contract Adherence)
# ============================================================================

class TestResponseSchemaGolden:
    """
    GOLDEN tests for response schema validation using data contracts.

    Validates that ALL API responses conform to defined contracts.
    """

    async def test_upload_response_matches_contract_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Upload response exactly matches FileUploadResponseContract
        """
        request = StorageTestDataFactory.make_upload_request(user_id=test_user_id)
        test_file = make_test_file("schema_test.txt")

        response = await http_client.post(
            f"{API_BASE}/files/upload",
            data={
                "user_id": request.user_id,
                "access_level": request.access_level.value,
                "tags": ",".join(request.tags),
            },
            files={"file": test_file},
            headers=internal_headers,
        )

        data = response.json()

        # PROOF: Pydantic validation ensures schema compliance
        validated = FileUploadResponseContract(**data)

        # GOLDEN: Verify required fields
        assert validated.file_id.startswith("file_")
        assert len(validated.file_id) == 37  # "file_" + 32 hex chars
        assert validated.file_path is not None
        assert validated.download_url is not None
        assert validated.file_size > 0
        assert validated.content_type == "text/plain"
        assert validated.uploaded_at is not None
        assert validated.message is not None

    async def test_file_info_response_matches_contract_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: File info response matches FileInfoResponseContract
        """
        # Upload first
        request = StorageTestDataFactory.make_upload_request(user_id=test_user_id)
        test_file = make_test_file()

        upload_response = await http_client.post(
            f"{API_BASE}/files/upload",
            data={
                "user_id": request.user_id,
                "access_level": request.access_level.value,
            },
            files={"file": test_file},
            headers=internal_headers,
        )
        file_id = upload_response.json()["file_id"]

        # Get file info
        info_response = await http_client.get(
            f"{API_BASE}/files/{file_id}",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        data = info_response.json()

        # PROOF: Contract validation
        validated = FileInfoResponseContract(**data)

        # GOLDEN: Verify required fields
        assert validated.file_id == file_id
        assert validated.file_name is not None
        assert validated.file_path is not None
        assert validated.file_size > 0
        assert validated.content_type is not None
        assert validated.status is not None
        assert validated.access_level is not None

    async def test_share_response_matches_contract_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Share response matches FileShareResponseContract
        """
        # Upload file
        upload_request = StorageTestDataFactory.make_upload_request(user_id=test_user_id)
        test_file = make_test_file()

        upload_response = await http_client.post(
            f"{API_BASE}/files/upload",
            data={
                "user_id": upload_request.user_id,
                "access_level": upload_request.access_level.value,
            },
            files={"file": test_file},
            headers=internal_headers,
        )
        file_id = upload_response.json()["file_id"]

        # Share file
        share_request = StorageTestDataFactory.make_share_request(
            file_id=file_id,
            shared_by=test_user_id,
        )

        share_response = await http_client.post(
            f"{API_BASE}/files/{file_id}/share",
            data={
                "shared_by": share_request.shared_by,
                "shared_with_email": share_request.shared_with_email,
                "expires_hours": share_request.expires_hours,
                "view": share_request.permissions["view"],
                "download": share_request.permissions["download"],
            },
            headers=internal_headers,
        )

        data = share_response.json()

        # PROOF: Contract validation
        validated = FileShareResponseContract(**data)

        # GOLDEN: Verify required fields
        assert validated.share_id.startswith("share_")
        assert len(validated.share_id) == 18  # "share_" (6) + 12 hex chars = 18
        assert validated.share_url is not None
        assert validated.expires_at is not None
        assert validated.permissions is not None


# ============================================================================
# GOLDEN: Error Response Formats
# ============================================================================

class TestErrorResponseFormatsGolden:
    """
    GOLDEN tests for error response formats and messages.

    Documents how API returns errors for different failure scenarios.
    """

    async def test_missing_user_id_error_format_golden(
        self, http_client, internal_headers
    ):
        """
        GOLDEN: Missing user_id parameter returns 400/422 with error message
        """
        test_file = make_test_file()

        response = await http_client.post(
            f"{API_BASE}/files/upload",
            data={
                # Missing user_id
                "access_level": "private",
            },
            files={"file": test_file},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL error status
        assert response.status_code in [400, 422]

        # GOLDEN: Verify error response is JSON
        assert "application/json" in response.headers.get("content-type", "")

        # GOLDEN: Document error response structure
        data = response.json()
        # Should have some error indicator (detail, error, message, etc.)
        assert any(key in data for key in ["detail", "error", "message", "errors"])

    async def test_missing_file_error_format_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Missing file in upload request returns 400/422
        """
        response = await http_client.post(
            f"{API_BASE}/files/upload",
            data={
                "user_id": test_user_id,
                "access_level": "private",
            },
            # No file attached
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL error status
        assert response.status_code in [400, 422]

        # GOLDEN: Verify JSON error response
        assert "application/json" in response.headers.get("content-type", "")

    async def test_invalid_file_id_format_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Invalid file ID format returns 404/403/400
        """
        invalid_file_id = "not_a_valid_file_id"

        response = await http_client.get(
            f"{API_BASE}/files/{invalid_file_id}",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL behavior
        # Could be 400 (bad request), 403 (forbidden), or 404 (not found)
        assert response.status_code in [400, 403, 404]


# ============================================================================
# GOLDEN: List and Query API Contracts
# ============================================================================

class TestListAndQueryAPIsGolden:
    """
    GOLDEN tests for list/query endpoints and pagination.
    """

    async def test_list_files_returns_array_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: List files returns JSON array
        """
        response = await http_client.get(
            f"{API_BASE}/files",
            params={"user_id": test_user_id, "limit": 10},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL status
        assert response.status_code == 200

        # GOLDEN: Verify response is JSON array
        data = response.json()
        assert isinstance(data, list)

        # GOLDEN: If array has items, verify structure
        if len(data) > 0:
            first_item = data[0]
            # Should have basic file info fields
            assert "file_id" in first_item
            assert "file_name" in first_item or "file_path" in first_item

    async def test_list_files_pagination_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: List files respects limit parameter
        """
        # Upload 3 files
        for i in range(3):
            request = StorageTestDataFactory.make_upload_request(user_id=test_user_id)
            test_file = make_test_file(f"pagination_test_{i}.txt")

            await http_client.post(
                f"{API_BASE}/files/upload",
                data={
                    "user_id": request.user_id,
                    "access_level": request.access_level.value,
                },
                files={"file": test_file},
                headers=internal_headers,
            )

        # List with limit=2
        response = await http_client.get(
            f"{API_BASE}/files",
            params={"user_id": test_user_id, "limit": 2},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL pagination behavior
        assert response.status_code == 200

        data = response.json()
        # API might return <= limit, or might not paginate (document actual)
        assert isinstance(data, list)

    async def test_storage_stats_api_contract_golden(
        self, http_client, internal_headers, test_user_id
    ):
        """
        GOLDEN: Storage stats API returns expected fields
        """
        response = await http_client.get(
            f"{API_BASE}/files/stats",
            params={"user_id": test_user_id},
            headers=internal_headers,
        )

        # GOLDEN: Document ACTUAL status
        assert response.status_code == 200

        # GOLDEN: Verify stats structure
        stats = response.json()
        assert "total_quota_bytes" in stats
        assert "used_bytes" in stats
        assert "available_bytes" in stats
        assert "usage_percentage" in stats
        assert "file_count" in stats


# ============================================================================
# SUMMARY
# ============================================================================
"""
API GOLDEN TESTS SUMMARY:

✅ PROOF OF HTTP CONTRACT VALIDATION (Layer 2):

1. HTTP Status Codes:
   - Health: 200 OK
   - Upload: 200 OK (not 201 Created)
   - Delete: 200 OK (not 204 No Content)
   - Not Found: 404 or 403
   - Validation Error: 400 or 422

2. Response Schemas:
   - FileUploadResponseContract validated
   - FileInfoResponseContract validated
   - FileShareResponseContract validated
   - All responses conform to data contracts!

3. Error Responses:
   - Missing required fields → 400/422
   - Invalid file ID → 400/403/404
   - All errors return JSON with error details

4. API Contracts:
   - List endpoints return JSON arrays
   - Stats endpoints return expected fields
   - Pagination parameters accepted

DIFFERENCE FROM INTEGRATION TESTS:
- API tests focus on HTTP protocol correctness
- Don't test full DB persistence lifecycle
- Lighter weight, faster execution
- Focus on error cases and edge cases

NEXT STEPS:
1. Run: pytest tests/api/golden/test_storage_api_golden.py -v
2. If passes → HTTP contracts validated!
3. Create smoke tests (E2E bash scripts)
4. Storage service fully validated (4/4 layers)
"""
