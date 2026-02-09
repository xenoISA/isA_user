"""
Account Service CRUD Integration Tests

Tests account lifecycle operations with real database persistence.
These tests verify data flows through the service and persists correctly.

Usage:
    pytest tests/integration/services/account/test_account_crud_integration.py -v
"""
import pytest
import pytest_asyncio
import httpx
from typing import List

from tests.fixtures import (
    make_user_id,
    make_email,
    make_account_ensure_request,
    make_account_update_request,
    make_preferences_update,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

ACCOUNT_SERVICE_URL = "http://localhost:8202"
API_BASE = f"{ACCOUNT_SERVICE_URL}/api/v1/accounts"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for integration tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate unique user ID for test isolation"""
    return make_user_id()


@pytest.fixture
def test_email():
    """Generate unique email for test isolation"""
    return make_email()


@pytest_asyncio.fixture
async def cleanup_accounts(http_client):
    """Track and cleanup accounts created during tests"""
    created_user_ids: List[str] = []

    def track(user_id: str):
        created_user_ids.append(user_id)
        return user_id

    yield track

    # Cleanup after test
    for user_id in created_user_ids:
        try:
            await http_client.delete(f"{API_BASE}/profile/{user_id}")
        except Exception:
            pass


# ============================================================================
# Account Lifecycle Integration Tests
# ============================================================================

class TestAccountLifecycleIntegration:
    """
    Integration tests for account CRUD lifecycle.
    Tests data persistence across create/read/update/delete operations.
    """

    async def test_full_account_lifecycle(self, http_client, test_user_id, test_email, cleanup_accounts):
        """
        Integration: Full account lifecycle - ensure, read, update, delete

        1. Create account with /ensure and verify persisted
        2. Read profile and verify data matches
        3. Update profile and verify changes persist
        4. Delete account and verify removal
        """
        cleanup_accounts(test_user_id)

        # 1. ENSURE (Create)
        ensure_request = make_account_ensure_request(
            user_id=test_user_id,
            email=test_email,
            name="Integration Test User",
        )

        ensure_response = await http_client.post(
            f"{API_BASE}/ensure",
            json=ensure_request,
        )
        assert ensure_response.status_code == 200, f"Ensure failed: {ensure_response.text}"

        account_data = ensure_response.json()
        assert account_data["user_id"] == test_user_id
        assert account_data["email"] == test_email
        assert account_data["name"] == "Integration Test User"

        # 2. READ - verify persisted
        get_response = await http_client.get(f"{API_BASE}/profile/{test_user_id}")
        assert get_response.status_code == 200

        read_data = get_response.json()
        assert read_data["user_id"] == test_user_id
        assert read_data["email"] == test_email

        # 3. UPDATE
        update_request = make_account_update_request(
            name="Updated Integration User",
            phone="+15551234567",
        )

        update_response = await http_client.put(
            f"{API_BASE}/profile/{test_user_id}",
            json=update_request,
        )
        assert update_response.status_code == 200

        updated_data = update_response.json()
        assert updated_data["name"] == "Updated Integration User"

        # Verify update persisted
        verify_response = await http_client.get(f"{API_BASE}/profile/{test_user_id}")
        verify_data = verify_response.json()
        assert verify_data["name"] == "Updated Integration User"

        # 4. DELETE
        delete_response = await http_client.delete(f"{API_BASE}/profile/{test_user_id}")
        assert delete_response.status_code == 200

        # Verify deleted
        get_deleted_response = await http_client.get(f"{API_BASE}/profile/{test_user_id}")
        assert get_deleted_response.status_code == 404


class TestAccountEnsureIdempotency:
    """
    Integration tests for account ensure idempotency.
    """

    async def test_ensure_is_idempotent(self, http_client, test_user_id, test_email, cleanup_accounts):
        """
        Integration: Ensure is idempotent - calling twice returns same account

        1. Call ensure to create account
        2. Call ensure again with same data
        3. Verify same account returned, not duplicated
        """
        cleanup_accounts(test_user_id)

        request = make_account_ensure_request(
            user_id=test_user_id,
            email=test_email,
            name="Idempotent Test",
        )

        # First call - creates account
        first_response = await http_client.post(f"{API_BASE}/ensure", json=request)
        assert first_response.status_code == 200
        first_data = first_response.json()

        # Second call - returns existing account
        second_response = await http_client.post(f"{API_BASE}/ensure", json=request)
        assert second_response.status_code == 200
        second_data = second_response.json()

        # Same account
        assert first_data["user_id"] == second_data["user_id"]
        assert first_data["email"] == second_data["email"]


class TestAccountPreferencesIntegration:
    """
    Integration tests for account preferences management.
    """

    async def test_preferences_merge_behavior(self, http_client, test_user_id, test_email, cleanup_accounts):
        """
        Integration: Preferences should merge, not replace

        1. Create account
        2. Set initial preferences (language, theme)
        3. Update with new preference (timezone)
        4. Verify all preferences preserved
        """
        cleanup_accounts(test_user_id)

        # Create account
        await http_client.post(
            f"{API_BASE}/ensure",
            json=make_account_ensure_request(
                user_id=test_user_id,
                email=test_email,
                name="Preferences Test",
            ),
        )

        # Set initial preferences
        initial_prefs = make_preferences_update(
            language="en",
            theme="dark",
        )
        await http_client.put(
            f"{API_BASE}/preferences/{test_user_id}",
            json=initial_prefs,
        )

        # Update with new preference
        new_prefs = make_preferences_update(timezone="UTC")
        await http_client.put(
            f"{API_BASE}/preferences/{test_user_id}",
            json=new_prefs,
        )

        # Verify all preferences preserved
        profile_response = await http_client.get(f"{API_BASE}/profile/{test_user_id}")
        profile_data = profile_response.json()
        prefs = profile_data.get("preferences", {})

        assert prefs.get("language") == "en", "Language should be preserved"
        assert prefs.get("theme") == "dark", "Theme should be preserved"
        assert prefs.get("timezone") == "UTC", "Timezone should be set"


class TestAccountListingIntegration:
    """
    Integration tests for account listing and search.
    """

    async def test_account_listing_pagination(self, http_client, cleanup_accounts):
        """
        Integration: Account listing with pagination

        1. Create multiple accounts
        2. List with default pagination
        3. List with custom page size
        4. Verify pagination metadata
        """
        # Create 5 accounts
        user_ids = []
        for i in range(5):
            user_id = make_user_id()
            email = make_email()
            response = await http_client.post(
                f"{API_BASE}/ensure",
                json=make_account_ensure_request(
                    user_id=user_id,
                    email=email,
                    name=f"List Test User {i}",
                ),
            )
            assert response.status_code == 200
            user_ids.append(user_id)
            cleanup_accounts(user_id)

        # List all
        list_response = await http_client.get(API_BASE)
        assert list_response.status_code == 200

        list_data = list_response.json()
        assert "accounts" in list_data
        assert "total_count" in list_data
        assert list_data["total_count"] >= 5

        # List with page_size=2
        paginated_response = await http_client.get(
            API_BASE,
            params={"page": 1, "page_size": 2},
        )
        assert paginated_response.status_code == 200

        paginated_data = paginated_response.json()
        assert len(paginated_data["accounts"]) == 2
        assert paginated_data["page_size"] == 2

    async def test_account_search(self, http_client, test_user_id, cleanup_accounts):
        """
        Integration: Account search by query

        1. Create account with unique name
        2. Search for account by name
        3. Verify account found in results
        """
        cleanup_accounts(test_user_id)

        unique_name = f"SearchTest_{test_user_id[:8]}"
        await http_client.post(
            f"{API_BASE}/ensure",
            json=make_account_ensure_request(
                user_id=test_user_id,
                email=make_email(),
                name=unique_name,
            ),
        )

        # Search by name
        search_response = await http_client.get(
            f"{API_BASE}/search",
            params={"query": unique_name[:10]},
        )
        assert search_response.status_code == 200

        results = search_response.json()
        assert isinstance(results, list)
        # Should find our account
        found = any(r.get("user_id") == test_user_id for r in results)
        assert found, f"Account {test_user_id} not found in search results"


class TestAccountEmailLookup:
    """
    Integration tests for account email lookup.
    """

    async def test_get_account_by_email(self, http_client, test_user_id, test_email, cleanup_accounts):
        """
        Integration: Get account by email

        1. Create account with email
        2. Lookup by email
        3. Verify correct account returned
        """
        cleanup_accounts(test_user_id)

        await http_client.post(
            f"{API_BASE}/ensure",
            json=make_account_ensure_request(
                user_id=test_user_id,
                email=test_email,
                name="Email Lookup Test",
            ),
        )

        # Lookup by email
        response = await http_client.get(f"{API_BASE}/by-email/{test_email}")
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["email"] == test_email

    async def test_email_not_found(self, http_client):
        """
        Integration: Email lookup returns 404 for non-existent email
        """
        response = await http_client.get(f"{API_BASE}/by-email/nonexistent@nowhere.com")
        assert response.status_code == 404


class TestAccountValidationIntegration:
    """
    Integration tests for account validation.
    """

    async def test_duplicate_email_rejected(self, http_client, test_user_id, test_email, cleanup_accounts):
        """
        Integration: Duplicate email for different user is rejected

        1. Create first account with email
        2. Try to create second account with same email
        3. Verify rejection with appropriate error
        """
        cleanup_accounts(test_user_id)

        # Create first account
        first_response = await http_client.post(
            f"{API_BASE}/ensure",
            json=make_account_ensure_request(
                user_id=test_user_id,
                email=test_email,
                name="First User",
            ),
        )
        assert first_response.status_code == 200

        # Try to create second account with same email
        second_user_id = make_user_id()
        cleanup_accounts(second_user_id)

        second_response = await http_client.post(
            f"{API_BASE}/ensure",
            json=make_account_ensure_request(
                user_id=second_user_id,
                email=test_email,  # Same email!
                name="Second User",
            ),
        )

        # Should be rejected
        assert second_response.status_code == 400
        assert "already exists" in second_response.text.lower()
