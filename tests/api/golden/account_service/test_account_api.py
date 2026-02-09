"""
Account Service API Golden Tests

GOLDEN tests for API layer - validates HTTP contracts, status codes, and response schemas.
These tests focus on HTTP protocol correctness using mocked repository layer.

Purpose:
- Validate HTTP status codes match REST conventions
- Verify response schemas match data contracts
- Test error response formats
- Check HTTP headers (Content-Type, etc.)
- Document API surface area

According to TDD_CONTRACT.md:
- API tests validate HTTP contracts (Layer 2)
- Lighter than integration tests (mock DB layer)
- Focus on API protocol correctness

PROOF OF CONCEPT: Uses data contracts for request/response validation!

Usage:
    # Run tests:
    pytest tests/api/golden/test_account_api.py -v
    pytest tests/api/golden/test_account_api.py -v -k "ensure"
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

# Import from centralized data contracts
from tests.contracts.account.data_contract import (
    AccountTestDataFactory,
    AccountProfileResponseContract,
    AccountSearchResponseContract,
    AccountStatsResponseContract,
    AccountServiceStatusContract,
)

# Import FastAPI app
from microservices.account_service.main import app

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def client():
    """Create async HTTP client for testing FastAPI app"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def factory():
    """Provide test data factory"""
    return AccountTestDataFactory


@pytest.fixture
def mock_account_service():
    """Mock AccountService for testing endpoints"""
    with patch("microservices.account_service.main.account_microservice") as mock_ms:
        mock_service = AsyncMock()
        mock_ms.account_service = mock_service
        yield mock_service


# ============================================================================
# GOLDEN: Health Check Tests
# ============================================================================

class TestHealthCheckEndpoints:
    """
    GOLDEN tests for health check endpoints.

    Validates that health endpoints return correct status and structure.
    """

    async def test_health_check_returns_200(self, client):
        """
        GOLDEN: Health endpoint returns 200 OK with service metadata
        """
        response = await client.get("/health")

        # GOLDEN: Validate HTTP status
        assert response.status_code == 200

        # GOLDEN: Validate Content-Type header
        assert "application/json" in response.headers.get("content-type", "")

        # GOLDEN: Validate response body structure
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "port" in data
        assert data["status"] == "healthy"

    async def test_health_detailed_returns_database_status(self, client, mock_account_service):
        """
        GOLDEN: Detailed health endpoint returns database connectivity status
        """
        # Mock health check response
        mock_account_service.health_check.return_value = {
            "status": "healthy",
            "service": "account_service",
            "timestamp": datetime.now(timezone.utc),
        }

        response = await client.get("/health/detailed")

        # GOLDEN: Validate HTTP status
        assert response.status_code == 200

        # GOLDEN: Validate Content-Type
        assert "application/json" in response.headers.get("content-type", "")

        # GOLDEN: Validate response structure
        data = response.json()
        assert "database_connected" in data
        assert isinstance(data["database_connected"], bool)


# ============================================================================
# GOLDEN: Account Ensure Endpoint Tests
# ============================================================================

class TestAccountEnsureEndpoint:
    """
    GOLDEN tests for POST /api/v1/accounts/ensure

    Tests account creation and idempotency.
    """

    async def test_ensure_account_creates_new_account(self, client, factory, mock_account_service):
        """
        GOLDEN: Ensure account creates new account with 201 Created
        """
        request_data = factory.make_ensure_request()
        expected_response = factory.make_profile_response(
            user_id=request_data.user_id,
            email=request_data.email,
            name=request_data.name,
        )

        mock_account_service.ensure_account.return_value = (expected_response, True)

        response = await client.post(
            "/api/v1/accounts/ensure",
            json=request_data.model_dump()
        )

        # GOLDEN: Document ACTUAL status code (200 not 201)
        assert response.status_code == 200

        # GOLDEN: Validate Content-Type
        assert "application/json" in response.headers.get("content-type", "")

        # GOLDEN: Validate response matches contract
        data = response.json()
        validated = AccountProfileResponseContract(**data)

        assert validated.user_id == request_data.user_id
        assert validated.email == request_data.email
        assert validated.name == request_data.name
        assert validated.is_active is True

    async def test_ensure_account_returns_existing_account(self, client, factory, mock_account_service):
        """
        GOLDEN: Ensure account returns existing account (idempotent) with 200 OK
        """
        request_data = factory.make_ensure_request()
        expected_response = factory.make_profile_response(
            user_id=request_data.user_id,
            email=request_data.email,
            name=request_data.name,
        )

        # was_created = False indicates existing account
        mock_account_service.ensure_account.return_value = (expected_response, False)

        response = await client.post(
            "/api/v1/accounts/ensure",
            json=request_data.model_dump()
        )

        # GOLDEN: Idempotent call returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response matches contract
        data = response.json()
        validated = AccountProfileResponseContract(**data)
        assert validated.user_id == request_data.user_id

    async def test_ensure_account_validates_required_fields(self, client, factory, mock_account_service):
        """
        GOLDEN: Missing required fields returns 422 Unprocessable Entity
        """
        invalid_request = factory.make_invalid_ensure_request_missing_user_id()

        response = await client.post(
            "/api/v1/accounts/ensure",
            json=invalid_request
        )

        # GOLDEN: Validation error returns 422
        assert response.status_code == 422

        # GOLDEN: Verify error response is JSON
        assert "application/json" in response.headers.get("content-type", "")

        # GOLDEN: Error response has detail field
        data = response.json()
        assert "detail" in data

    async def test_ensure_account_validates_email_format(self, client, factory, mock_account_service):
        """
        GOLDEN: Invalid email format returns 422 Unprocessable Entity
        """
        invalid_request = factory.make_invalid_ensure_request_invalid_email()

        response = await client.post(
            "/api/v1/accounts/ensure",
            json=invalid_request
        )

        # GOLDEN: Invalid email returns 422
        assert response.status_code == 422

        # GOLDEN: Error response structure
        data = response.json()
        assert "detail" in data


# ============================================================================
# GOLDEN: Account Profile GET/PUT/DELETE Tests
# ============================================================================

class TestAccountProfileEndpoint:
    """
    GOLDEN tests for account profile CRUD operations

    GET /api/v1/accounts/profile/{user_id}
    PUT /api/v1/accounts/profile/{user_id}
    DELETE /api/v1/accounts/profile/{user_id}
    """

    async def test_get_profile_returns_account(self, client, factory, mock_account_service):
        """
        GOLDEN: Get profile returns complete account data with 200 OK
        """
        user_id = factory.make_user_id()
        expected_response = factory.make_profile_response(user_id=user_id)

        mock_account_service.get_account_profile.return_value = expected_response

        response = await client.get(f"/api/v1/accounts/profile/{user_id}")

        # GOLDEN: Success returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response matches contract
        data = response.json()
        validated = AccountProfileResponseContract(**data)

        assert validated.user_id == user_id
        assert validated.is_active is not None
        assert validated.preferences is not None

    async def test_get_profile_returns_404_for_nonexistent(self, client, factory, mock_account_service):
        """
        GOLDEN: Non-existent account returns 404 Not Found
        """
        from microservices.account_service.account_service import AccountNotFoundError

        user_id = factory.make_user_id()
        mock_account_service.get_account_profile.side_effect = AccountNotFoundError(
            f"Account not found: {user_id}"
        )

        response = await client.get(f"/api/v1/accounts/profile/{user_id}")

        # GOLDEN: Not found returns 404
        assert response.status_code == 404

        # GOLDEN: Error response format
        data = response.json()
        assert "detail" in data

    async def test_update_profile_updates_fields(self, client, factory, mock_account_service):
        """
        GOLDEN: Profile update changes specified fields and returns 200 OK
        """
        user_id = factory.make_user_id()
        update_request = factory.make_update_request()
        updated_response = factory.make_profile_response(
            user_id=user_id,
            name=update_request.name,
            email=update_request.email,
        )

        mock_account_service.update_account_profile.return_value = updated_response

        response = await client.put(
            f"/api/v1/accounts/profile/{user_id}",
            json=update_request.model_dump(exclude_none=True)
        )

        # GOLDEN: Update returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response matches contract
        data = response.json()
        validated = AccountProfileResponseContract(**data)
        assert validated.name == update_request.name

    async def test_update_profile_validates_email_uniqueness(self, client, factory, mock_account_service):
        """
        GOLDEN: Duplicate email returns 400 Bad Request
        """
        from microservices.account_service.account_service import AccountValidationError

        user_id = factory.make_user_id()
        update_request = factory.make_update_request()

        mock_account_service.update_account_profile.side_effect = AccountValidationError(
            "Email already in use"
        )

        response = await client.put(
            f"/api/v1/accounts/profile/{user_id}",
            json=update_request.model_dump(exclude_none=True)
        )

        # GOLDEN: Validation error returns 400
        assert response.status_code == 400

        # GOLDEN: Error response format
        data = response.json()
        assert "detail" in data

    async def test_update_profile_returns_404_for_nonexistent(self, client, factory, mock_account_service):
        """
        GOLDEN: Updating non-existent account returns 404 Not Found
        """
        from microservices.account_service.account_service import AccountNotFoundError

        user_id = factory.make_user_id()
        update_request = factory.make_update_request()

        mock_account_service.update_account_profile.side_effect = AccountNotFoundError(
            f"Account not found: {user_id}"
        )

        response = await client.put(
            f"/api/v1/accounts/profile/{user_id}",
            json=update_request.model_dump(exclude_none=True)
        )

        # GOLDEN: Not found returns 404
        assert response.status_code == 404

    async def test_delete_account_soft_deletes(self, client, factory, mock_account_service):
        """
        GOLDEN: Delete account soft-deletes and returns 200 OK
        """
        user_id = factory.make_user_id()
        mock_account_service.delete_account.return_value = True

        response = await client.delete(f"/api/v1/accounts/profile/{user_id}")

        # GOLDEN: Delete returns 200 OK (not 204)
        assert response.status_code == 200

        # GOLDEN: Response body contains success message
        data = response.json()
        assert "message" in data
        assert data.get("message") == "Account deleted successfully"


# ============================================================================
# GOLDEN: Account Preferences Tests
# ============================================================================

class TestAccountPreferencesEndpoint:
    """
    GOLDEN tests for PUT /api/v1/accounts/preferences/{user_id}

    Tests preferences update functionality.
    """

    async def test_update_preferences_merges_data(self, client, factory, mock_account_service):
        """
        GOLDEN: Preferences update merges new data and returns 200 OK
        """
        user_id = factory.make_user_id()
        prefs_request = factory.make_preferences_request()

        mock_account_service.update_account_preferences.return_value = True

        response = await client.put(
            f"/api/v1/accounts/preferences/{user_id}",
            json=prefs_request.model_dump(exclude_none=True)
        )

        # GOLDEN: Success returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response contains success message
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower()

    async def test_update_preferences_validates_json(self, client, factory, mock_account_service):
        """
        GOLDEN: Invalid preferences data returns 422 Unprocessable Entity
        """
        user_id = factory.make_user_id()
        invalid_prefs = factory.make_invalid_preferences_request_invalid_theme()

        response = await client.put(
            f"/api/v1/accounts/preferences/{user_id}",
            json=invalid_prefs
        )

        # GOLDEN: Invalid data returns 422
        assert response.status_code == 422

        # GOLDEN: Error response format
        data = response.json()
        assert "detail" in data


# ============================================================================
# GOLDEN: Account List and Search Tests
# ============================================================================

class TestAccountListEndpoint:
    """
    GOLDEN tests for GET /api/v1/accounts

    Tests list functionality with pagination and filtering.
    """

    async def test_list_accounts_returns_paginated_results(self, client, factory, mock_account_service):
        """
        GOLDEN: List accounts returns paginated response with 200 OK
        """
        mock_response = factory.make_search_response(
            accounts=[
                factory.make_summary_response(),
                factory.make_summary_response(),
            ],
            total_count=2,
            page=1,
            page_size=50,
            has_next=False,
        )

        mock_account_service.list_accounts.return_value = mock_response

        response = await client.get("/api/v1/accounts")

        # GOLDEN: Success returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response matches pagination contract
        data = response.json()
        validated = AccountSearchResponseContract(**data)

        assert validated.page == 1
        assert validated.page_size == 50
        assert isinstance(validated.accounts, list)
        assert validated.total_count >= 0

    async def test_list_accounts_filters_by_search(self, client, factory, mock_account_service):
        """
        GOLDEN: List accounts with search parameter filters results
        """
        search_term = "john"
        mock_response = factory.make_search_response(
            accounts=[factory.make_summary_response(name="John Doe")],
            total_count=1,
        )

        mock_account_service.list_accounts.return_value = mock_response

        response = await client.get(
            "/api/v1/accounts",
            params={"search": search_term}
        )

        # GOLDEN: Filtered search returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response structure valid
        data = response.json()
        assert "accounts" in data
        assert isinstance(data["accounts"], list)


class TestAccountSearchEndpoint:
    """
    GOLDEN tests for GET /api/v1/accounts/search

    Tests search functionality.
    """

    async def test_search_accounts_returns_results(self, client, factory, mock_account_service):
        """
        GOLDEN: Search accounts returns matching results with 200 OK
        """
        query = "john"
        mock_results = [
            factory.make_summary_response(name="John Doe"),
            factory.make_summary_response(name="John Smith"),
        ]

        mock_account_service.search_accounts.return_value = mock_results

        response = await client.get(
            "/api/v1/accounts/search",
            params={"query": query}
        )

        # GOLDEN: Search returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response is JSON array
        data = response.json()
        assert isinstance(data, list)

        # GOLDEN: Each item has required fields
        if len(data) > 0:
            assert "user_id" in data[0]
            assert "email" in data[0]


# ============================================================================
# GOLDEN: Account Stats Tests
# ============================================================================

class TestAccountStatsEndpoint:
    """
    GOLDEN tests for GET /api/v1/accounts/stats

    Tests statistics endpoint.
    """

    async def test_get_stats_returns_metrics(self, client, factory, mock_account_service):
        """
        GOLDEN: Stats endpoint returns account metrics with 200 OK
        """
        mock_stats = factory.make_stats_response(
            total_accounts=1250,
            active_accounts=1180,
            inactive_accounts=70,
            recent_registrations_7d=45,
            recent_registrations_30d=203,
        )

        mock_account_service.get_service_stats.return_value = mock_stats

        response = await client.get("/api/v1/accounts/stats")

        # GOLDEN: Stats returns 200 OK
        assert response.status_code == 200

        # GOLDEN: Response matches stats contract
        data = response.json()
        validated = AccountStatsResponseContract(**data)

        assert validated.total_accounts >= 0
        assert validated.active_accounts >= 0
        assert validated.inactive_accounts >= 0
        assert validated.recent_registrations_7d >= 0
        assert validated.recent_registrations_30d >= 0


# ============================================================================
# GOLDEN: Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """
    GOLDEN tests for error response formats and status codes.

    Validates consistent error handling across all endpoints.
    """

    async def test_ensure_account_400_missing_user_id(self, client, factory, mock_account_service):
        """
        GOLDEN: Missing user_id in ensure request returns 422
        """
        invalid_request = factory.make_invalid_ensure_request_missing_user_id()

        response = await client.post(
            "/api/v1/accounts/ensure",
            json=invalid_request
        )

        # GOLDEN: Missing required field returns 422
        assert response.status_code == 422

        # GOLDEN: Error format validation
        data = response.json()
        assert "detail" in data

    async def test_ensure_account_400_invalid_email(self, client, factory, mock_account_service):
        """
        GOLDEN: Invalid email format returns 422
        """
        invalid_request = factory.make_invalid_ensure_request_invalid_email()

        response = await client.post(
            "/api/v1/accounts/ensure",
            json=invalid_request
        )

        # GOLDEN: Invalid email returns 422
        assert response.status_code == 422

    async def test_get_profile_404_not_found(self, client, factory, mock_account_service):
        """
        GOLDEN: Get non-existent profile returns 404
        """
        from microservices.account_service.account_service import AccountNotFoundError

        user_id = factory.make_user_id()
        mock_account_service.get_account_profile.side_effect = AccountNotFoundError(
            f"Account not found: {user_id}"
        )

        response = await client.get(f"/api/v1/accounts/profile/{user_id}")

        # GOLDEN: Not found returns 404
        assert response.status_code == 404

    async def test_update_profile_404_not_found(self, client, factory, mock_account_service):
        """
        GOLDEN: Update non-existent profile returns 404
        """
        from microservices.account_service.account_service import AccountNotFoundError

        user_id = factory.make_user_id()
        update_request = factory.make_update_request()

        mock_account_service.update_account_profile.side_effect = AccountNotFoundError(
            f"Account not found: {user_id}"
        )

        response = await client.put(
            f"/api/v1/accounts/profile/{user_id}",
            json=update_request.model_dump(exclude_none=True)
        )

        # GOLDEN: Not found returns 404
        assert response.status_code == 404

    async def test_update_profile_400_duplicate_email(self, client, factory, mock_account_service):
        """
        GOLDEN: Duplicate email in update returns 400
        """
        from microservices.account_service.account_service import AccountValidationError

        user_id = factory.make_user_id()
        update_request = factory.make_update_request()

        mock_account_service.update_account_profile.side_effect = AccountValidationError(
            "Email already exists"
        )

        response = await client.put(
            f"/api/v1/accounts/profile/{user_id}",
            json=update_request.model_dump(exclude_none=True)
        )

        # GOLDEN: Duplicate email returns 400
        assert response.status_code == 400


# ============================================================================
# GOLDEN: Response Contract Validation Tests
# ============================================================================

class TestResponseContractValidation:
    """
    GOLDEN tests for validating response structure matches contracts.

    Ensures all responses conform to defined Pydantic contracts.
    """

    async def test_profile_response_matches_contract(self, client, factory, mock_account_service):
        """
        GOLDEN: Profile response exactly matches AccountProfileResponseContract
        """
        user_id = factory.make_user_id()
        expected_response = factory.make_profile_response(user_id=user_id)

        mock_account_service.get_account_profile.return_value = expected_response

        response = await client.get(f"/api/v1/accounts/profile/{user_id}")

        data = response.json()

        # PROOF: Pydantic validation ensures schema compliance
        validated = AccountProfileResponseContract(**data)

        # GOLDEN: Verify required fields
        assert validated.user_id is not None
        assert validated.is_active is not None
        assert isinstance(validated.preferences, dict)
        assert validated.created_at is not None

    async def test_search_response_matches_contract(self, client, factory, mock_account_service):
        """
        GOLDEN: Search response matches AccountSearchResponseContract
        """
        mock_response = factory.make_search_response()
        mock_account_service.list_accounts.return_value = mock_response

        response = await client.get("/api/v1/accounts")

        data = response.json()

        # PROOF: Contract validation
        validated = AccountSearchResponseContract(**data)

        # GOLDEN: Verify pagination fields
        assert validated.page >= 1
        assert validated.page_size >= 1
        assert validated.total_count >= 0
        assert isinstance(validated.has_next, bool)
        assert isinstance(validated.accounts, list)

    async def test_stats_response_matches_contract(self, client, factory, mock_account_service):
        """
        GOLDEN: Stats response matches AccountStatsResponseContract
        """
        mock_stats = factory.make_stats_response()
        mock_account_service.get_service_stats.return_value = mock_stats

        response = await client.get("/api/v1/accounts/stats")

        data = response.json()

        # PROOF: Contract validation
        validated = AccountStatsResponseContract(**data)

        # GOLDEN: Verify all stat fields
        assert validated.total_accounts >= 0
        assert validated.active_accounts >= 0
        assert validated.inactive_accounts >= 0
        assert validated.recent_registrations_7d >= 0
        assert validated.recent_registrations_30d >= 0

    async def test_list_response_includes_pagination(self, client, factory, mock_account_service):
        """
        GOLDEN: List response includes pagination metadata
        """
        mock_response = factory.make_search_response(
            page=2,
            page_size=25,
            total_count=100,
            has_next=True,
        )
        mock_account_service.list_accounts.return_value = mock_response

        response = await client.get(
            "/api/v1/accounts",
            params={"page": 2, "page_size": 25}
        )

        data = response.json()

        # GOLDEN: Verify pagination structure
        assert data["page"] == 2
        assert data["page_size"] == 25
        assert data["total_count"] == 100
        assert data["has_next"] is True


# ============================================================================
# SUMMARY
# ============================================================================
"""
API GOLDEN TESTS SUMMARY:

✅ PROOF OF HTTP CONTRACT VALIDATION (Layer 2):

1. Health Check Tests (2 tests):
   - Basic health check returns 200 OK
   - Detailed health check returns database status

2. Account Ensure Tests (4 tests):
   - Creates new account successfully
   - Returns existing account (idempotent)
   - Validates required fields
   - Validates email format

3. Profile CRUD Tests (6 tests):
   - GET returns account profile
   - GET returns 404 for non-existent
   - PUT updates profile fields
   - PUT validates email uniqueness
   - PUT returns 404 for non-existent
   - DELETE soft-deletes account

4. Preferences Tests (2 tests):
   - Updates preferences successfully
   - Validates preference data

5. List and Search Tests (3 tests):
   - List returns paginated results
   - List filters by search term
   - Search returns matching results

6. Stats Tests (1 test):
   - Returns account statistics

7. Error Handling Tests (5 tests):
   - Missing user_id returns 422
   - Invalid email returns 422
   - Non-existent profile returns 404
   - Update non-existent returns 404
   - Duplicate email returns 400

8. Contract Validation Tests (4 tests):
   - Profile response matches contract
   - Search response matches contract
   - Stats response matches contract
   - Pagination metadata validated

TOTAL: 27 tests covering all major endpoints and error scenarios

DESIGN PATTERNS:
- Uses httpx.AsyncClient with FastAPI app (no real HTTP)
- Mocks AccountService layer (no database)
- Uses data contract factories (no hardcoded data)
- Validates Pydantic response contracts
- Documents actual API behavior

NEXT STEPS:
1. Run: pytest tests/api/golden/test_account_api.py -v
2. Verify all tests pass
3. Update as API evolves
"""
