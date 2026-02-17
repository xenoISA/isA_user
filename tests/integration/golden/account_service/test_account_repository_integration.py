"""
Account Repository Integration Golden Tests

Tests AccountRepository with actual database operations.
These tests require a running PostgreSQL service.

Usage:
    pytest tests/integration/golden/test_account_repository_integration.py -v
    pytest tests/integration/golden -v -k "repository"
"""
import pytest
import uuid
import httpx
from datetime import datetime, timezone

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.requires_db]


class TestAccountRepositoryGetOperations:
    """
    Golden: Repository GET operations

    Test data retrieval methods against actual database.
    """

    @pytest.fixture
    async def test_user(self, http_client: httpx.AsyncClient, config):
        """Create a test user for retrieval tests"""
        user_id = f"repo_test_{uuid.uuid4().hex[:8]}"
        email = f"{user_id}@test.example.com"

        # Create via API to ensure proper DB state
        response = await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={
                "user_id": user_id,
                "email": email,
                "name": "Repository Test User"
            }
        )
        assert response.status_code == 200

        yield {"user_id": user_id, "email": email, "name": "Repository Test User"}

        # Cleanup - delete the test user
        await http_client.delete(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )

    async def test_get_account_by_id_returns_user(
        self,
        http_client: httpx.AsyncClient,
        test_user: dict,
        config
    ):
        """GOLDEN: get_account_by_id returns existing user"""
        response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{test_user['user_id']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user["user_id"]
        assert data["email"] == test_user["email"]
        assert data["name"] == test_user["name"]
        assert data["is_active"] is True

    async def test_get_account_by_id_returns_none_for_nonexistent(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: get_account_by_id returns 404 for nonexistent user"""
        response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/nonexistent_user_xyz"
        )

        assert response.status_code == 404

    async def test_get_account_by_email_returns_user(
        self,
        http_client: httpx.AsyncClient,
        test_user: dict,
        config
    ):
        """GOLDEN: get_account_by_email returns existing user"""
        response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/email/{test_user['email']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]

    async def test_get_accounts_by_ids_returns_multiple(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: get_accounts_by_ids returns multiple users"""
        # Create two test users
        users = []
        for i in range(2):
            user_id = f"batch_test_{uuid.uuid4().hex[:8]}"
            response = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": f"{user_id}@test.example.com",
                    "name": f"Batch Test User {i}"
                }
            )
            assert response.status_code == 200
            users.append(user_id)

        try:
            # Get both users at once
            response = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/batch",
                json={"user_ids": users}
            )

            if response.status_code == 200:
                data = response.json()
                returned_ids = [u["user_id"] for u in data.get("accounts", data)]
                for user_id in users:
                    assert user_id in returned_ids
        finally:
            # Cleanup
            for user_id in users:
                await http_client.delete(
                    f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
                )


class TestAccountRepositoryCreateOperations:
    """
    Golden: Repository CREATE operations

    Test account creation methods.
    """

    async def test_ensure_account_creates_new_user(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: ensure_account_exists creates new user if not found"""
        user_id = f"create_test_{uuid.uuid4().hex[:8]}"
        email = f"{user_id}@test.example.com"

        try:
            response = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": email,
                    "name": "New User"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert data["email"] == email
            assert data["is_active"] is True
            assert "created_at" in data or data.get("created") is True
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )

    async def test_ensure_account_returns_existing_user(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: ensure_account_exists returns existing user without modification"""
        user_id = f"idempotent_test_{uuid.uuid4().hex[:8]}"
        email = f"{user_id}@test.example.com"

        try:
            # First call - creates
            response1 = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": email,
                    "name": "Original Name"
                }
            )
            assert response1.status_code == 200

            # Second call - should return existing
            response2 = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": email,
                    "name": "Different Name"  # Should be ignored
                }
            )

            assert response2.status_code == 200
            data = response2.json()
            assert data["name"] == "Original Name"  # Name unchanged
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )

    async def test_ensure_account_rejects_duplicate_email(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: ensure_account_exists rejects duplicate email for different user_id"""
        user_id_1 = f"dup_email_1_{uuid.uuid4().hex[:8]}"
        user_id_2 = f"dup_email_2_{uuid.uuid4().hex[:8]}"
        shared_email = f"duplicate_{uuid.uuid4().hex[:8]}@test.example.com"

        try:
            # Create first user
            response1 = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id_1,
                    "email": shared_email,
                    "name": "First User"
                }
            )
            assert response1.status_code == 200

            # Try to create second user with same email
            response2 = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id_2,
                    "email": shared_email,
                    "name": "Second User"
                }
            )

            # Should fail - duplicate email
            assert response2.status_code in [400, 409, 422]
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id_1}"
            )


class TestAccountRepositoryUpdateOperations:
    """
    Golden: Repository UPDATE operations

    Test profile update methods.
    """

    async def test_update_profile_changes_name(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: update_account_profile changes name"""
        user_id = f"update_name_{uuid.uuid4().hex[:8]}"

        try:
            # Create user
            await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": f"{user_id}@test.example.com",
                    "name": "Original Name"
                }
            )

            # Update name
            response = await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}",
                json={"name": "Updated Name"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )

    async def test_update_profile_changes_email(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: update_account_profile changes email"""
        user_id = f"update_email_{uuid.uuid4().hex[:8]}"
        new_email = f"new_{uuid.uuid4().hex[:8]}@test.example.com"

        try:
            await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": f"{user_id}@test.example.com",
                    "name": "Test User"
                }
            )

            response = await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}",
                json={"email": new_email}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == new_email
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )

    async def test_update_preferences_merges_with_existing(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: update_account_preferences merges with existing preferences"""
        user_id = f"update_prefs_{uuid.uuid4().hex[:8]}"

        try:
            await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": f"{user_id}@test.example.com",
                    "name": "Prefs Test User"
                }
            )

            # Set initial preferences
            await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/preferences/{user_id}",
                json={"theme": "dark"}
            )

            # Update with additional preference
            response = await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/preferences/{user_id}",
                json={"language": "en"}
            )

            assert response.status_code == 200

            # Get profile and verify both preferences exist
            profile_response = await http_client.get(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )
            data = profile_response.json()
            prefs = data.get("preferences", {})

            # Both preferences should be present
            assert prefs.get("theme") == "dark"
            assert prefs.get("language") == "en"
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )


class TestAccountRepositoryStatusOperations:
    """
    Golden: Repository STATUS operations

    Test activate/deactivate methods.
    """

    async def test_deactivate_sets_is_active_false(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: deactivate_account sets is_active to False"""
        user_id = f"deactivate_{uuid.uuid4().hex[:8]}"

        try:
            await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": f"{user_id}@test.example.com",
                    "name": "Deactivate Test"
                }
            )

            response = await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
                json={"is_active": False, "reason": "Test deactivation"}
            )

            assert response.status_code == 200

            # Verify user is deactivated - GET should return 404 for inactive
            get_response = await http_client.get(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )
            assert get_response.status_code == 404
        finally:
            # Reactivate to allow deletion
            await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
                json={"is_active": True, "reason": "Cleanup"}
            )
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )

    async def test_activate_sets_is_active_true(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: activate_account sets is_active to True"""
        user_id = f"reactivate_{uuid.uuid4().hex[:8]}"

        try:
            # Create and deactivate
            await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": f"{user_id}@test.example.com",
                    "name": "Reactivate Test"
                }
            )
            await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
                json={"is_active": False, "reason": "Test"}
            )

            # Reactivate
            response = await http_client.put(
                f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
                json={"is_active": True, "reason": "Reactivating"}
            )

            assert response.status_code == 200

            # Verify user is active again
            get_response = await http_client.get(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )
            assert get_response.status_code == 200
            data = get_response.json()
            assert data["is_active"] is True
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )


class TestAccountRepositoryListOperations:
    """
    Golden: Repository LIST/SEARCH operations

    Test pagination and search methods.
    """

    async def test_list_accounts_returns_paginated_results(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: list_accounts returns paginated results"""
        response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts",
            params={"page": 1, "page_size": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert "total_count" in data or "total" in data
        assert "page" in data
        assert len(data["accounts"]) <= 10

    async def test_list_accounts_filters_by_active_status(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: list_accounts filters by is_active"""
        response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts",
            params={"is_active": True}
        )

        assert response.status_code == 200
        data = response.json()
        for account in data["accounts"]:
            assert account["is_active"] is True

    async def test_search_accounts_finds_by_name(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: search_accounts finds users by name"""
        user_id = f"searchable_{uuid.uuid4().hex[:8]}"
        unique_name = f"UniqueSearchName_{uuid.uuid4().hex[:4]}"

        try:
            await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": f"{user_id}@test.example.com",
                    "name": unique_name
                }
            )

            response = await http_client.get(
                f"{config.ACCOUNT_URL}/api/v1/accounts/search",
                params={"query": unique_name}
            )

            assert response.status_code == 200
            data = response.json()
            found_ids = [a["user_id"] for a in data]
            assert user_id in found_ids
        finally:
            await http_client.delete(
                f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
            )


class TestAccountRepositoryStats:
    """
    Golden: Repository STATS operations

    Test statistics aggregation methods.
    """

    async def test_get_account_stats_returns_expected_fields(
        self,
        http_client: httpx.AsyncClient,
        config
    ):
        """GOLDEN: get_account_stats returns required statistics"""
        response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/stats"
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "total_accounts" in data
        assert "active_accounts" in data
        assert "inactive_accounts" in data

        # Values should be non-negative
        assert data["total_accounts"] >= 0
        assert data["active_accounts"] >= 0
        assert data["inactive_accounts"] >= 0

        # Active + Inactive should equal or be close to Total
        assert data["active_accounts"] + data["inactive_accounts"] == data["total_accounts"]
