"""
Account Service API Golden Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Usage:
    pytest tests/api/golden/account_service -v
    pytest tests/api/golden/account_service -v -k "health"
"""
import pytest
import uuid
from datetime import datetime

from tests.api.conftest import APIClient, APIAssertions

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for tests"""
    return f"api_test_{uuid.uuid4().hex[:12]}"


def unique_email() -> str:
    """Generate unique email for tests"""
    return f"api_test_{uuid.uuid4().hex[:8]}@example.com"


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestAccountHealthAPIGolden:
    """GOLDEN: Account service health endpoint contracts"""

    async def test_health_endpoint_returns_200(self, account_api: APIClient):
        """GOLDEN: GET /health returns 200 OK"""
        response = await account_api.get_raw("/health")
        assert response.status_code == 200

    async def test_health_detailed_returns_200(self, account_api: APIClient):
        """GOLDEN: GET /health/detailed returns 200 with component status"""
        response = await account_api.get_raw("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# =============================================================================
# Account Ensure (Create) Tests
# =============================================================================

class TestAccountEnsureAPIGolden:
    """GOLDEN: POST /api/v1/accounts/ensure endpoint contracts"""

    async def test_ensure_creates_new_account(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /ensure creates account and returns profile"""
        user_id = unique_user_id()
        email = unique_email()

        response = await account_api.post(
            "/ensure",
            json={
                "user_id": user_id,
                "email": email,
                "name": "API Test User"
            }
        )

        api_assert.assert_created(response)
        data = response.json()
        api_assert.assert_has_fields(data, ["user_id", "email", "name"])
        assert data["user_id"] == user_id
        assert data["email"] == email

    async def test_ensure_returns_existing_account(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /ensure with existing user_id returns existing account"""
        user_id = unique_user_id()
        email = unique_email()

        # First call - creates account
        response1 = await account_api.post(
            "/ensure",
            json={"user_id": user_id, "email": email, "name": "Test User"}
        )
        api_assert.assert_created(response1)

        # Second call - returns same account (idempotent)
        response2 = await account_api.post(
            "/ensure",
            json={"user_id": user_id, "email": email, "name": "Test User"}
        )
        api_assert.assert_created(response2)

        assert response1.json()["user_id"] == response2.json()["user_id"]

    async def test_ensure_rejects_invalid_email(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /ensure with invalid email returns 422"""
        response = await account_api.post(
            "/ensure",
            json={
                "user_id": unique_user_id(),
                "email": "not-an-email",
                "name": "Test User"
            }
        )
        api_assert.assert_validation_error(response)

    async def test_ensure_rejects_empty_name(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /ensure with empty name returns 422"""
        response = await account_api.post(
            "/ensure",
            json={
                "user_id": unique_user_id(),
                "email": unique_email(),
                "name": ""
            }
        )
        api_assert.assert_validation_error(response)


# =============================================================================
# Get Profile Tests
# =============================================================================

class TestAccountProfileAPIGolden:
    """GOLDEN: GET /api/v1/accounts/profile/{user_id} endpoint contracts"""

    async def test_get_profile_returns_account(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /profile/{user_id} returns account profile"""
        user_id = unique_user_id()
        email = unique_email()

        # Create account first
        await account_api.post(
            "/ensure",
            json={"user_id": user_id, "email": email, "name": "Profile Test"}
        )

        # Get profile
        response = await account_api.get(f"/profile/{user_id}")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["user_id", "email", "name", "is_active"])
        assert data["user_id"] == user_id

    async def test_get_profile_nonexistent_returns_404(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /profile/{nonexistent_id} returns 404"""
        response = await account_api.get(f"/profile/nonexistent_{uuid.uuid4().hex}")
        api_assert.assert_not_found(response)


# =============================================================================
# Update Profile Tests
# =============================================================================

class TestAccountUpdateProfileAPIGolden:
    """GOLDEN: PUT /api/v1/accounts/profile/{user_id} endpoint contracts"""

    async def test_update_profile_changes_name(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: PUT /profile/{user_id} updates profile fields"""
        user_id = unique_user_id()
        email = unique_email()

        # Create account
        await account_api.post(
            "/ensure",
            json={"user_id": user_id, "email": email, "name": "Original Name"}
        )

        # Update profile
        response = await account_api.put(
            f"/profile/{user_id}",
            json={"name": "Updated Name"}
        )
        api_assert.assert_success(response)

        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_update_profile_nonexistent_returns_404(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: PUT /profile/{nonexistent_id} returns 404"""
        response = await account_api.put(
            f"/profile/nonexistent_{uuid.uuid4().hex}",
            json={"name": "Test"}
        )
        api_assert.assert_not_found(response)


# =============================================================================
# Search Tests
# =============================================================================

class TestAccountSearchAPIGolden:
    """GOLDEN: GET /api/v1/accounts/search endpoint contracts"""

    async def test_search_returns_matching_accounts(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /search?query=xxx returns matching accounts"""
        # Create a searchable account
        unique_name = f"SearchableUser_{uuid.uuid4().hex[:8]}"
        user_id = unique_user_id()

        await account_api.post(
            "/ensure",
            json={"user_id": user_id, "email": unique_email(), "name": unique_name}
        )

        # Search for it
        response = await account_api.get(f"/search?query={unique_name[:10]}")
        api_assert.assert_success(response)

        data = response.json()
        assert isinstance(data, list)

    async def test_search_with_limit(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /search?query=xxx&limit=10 respects limit"""
        response = await account_api.get("/search?query=test&limit=5")
        api_assert.assert_success(response)

        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5


# =============================================================================
# Preferences Tests
# =============================================================================

class TestAccountPreferencesAPIGolden:
    """GOLDEN: Preferences endpoint contracts"""

    async def test_update_preferences_merges_data(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: PUT /preferences/{user_id} merges preferences"""
        user_id = unique_user_id()

        # Create account
        await account_api.post(
            "/ensure",
            json={"user_id": user_id, "email": unique_email(), "name": "Prefs Test"}
        )

        # Update preferences
        response = await account_api.put(
            f"/preferences/{user_id}",
            json={"theme": "dark", "language": "en"}
        )
        api_assert.assert_success(response)


# =============================================================================
# Account List Tests
# =============================================================================

class TestAccountListAPIGolden:
    """GOLDEN: GET /api/v1/accounts endpoint contracts"""

    async def test_list_accounts_returns_paginated(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET / returns paginated list of accounts"""
        response = await account_api.get("?page=1&page_size=10")
        api_assert.assert_success(response)

        data = response.json()
        assert isinstance(data, list)

    async def test_list_accounts_respects_page_size(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?page_size=5 returns at most 5 accounts"""
        response = await account_api.get("?page_size=5")
        api_assert.assert_success(response)

        data = response.json()
        assert len(data) <= 5


# =============================================================================
# Stats Tests
# =============================================================================

class TestAccountStatsAPIGolden:
    """GOLDEN: GET /api/v1/accounts/stats endpoint contracts"""

    async def test_stats_returns_counts(
        self, account_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /stats returns account statistics"""
        response = await account_api.get("/stats")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["total_accounts", "active_accounts"])
