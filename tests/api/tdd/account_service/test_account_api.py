"""
Account Service API Contract Tests (Layer 1)

RED PHASE: Define what the API should return before implementation.
These tests define the HTTP contracts for the Account service.

Usage:
    pytest tests/api/account -v                    # Run all account API tests
    pytest tests/api/account -v -k "ensure"        # Run ensure endpoint tests
    pytest tests/api/account -v --tb=short         # Short traceback
"""
import pytest
import uuid
from datetime import datetime

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


class TestAccountEnsureEndpoint:
    """
    POST /api/v1/accounts/ensure

    Ensure user account exists, create if needed.
    This is the primary account creation/sync endpoint.
    """

    async def test_ensure_creates_new_account(self, account_api, api_assert):
        """RED: New account should be created with all required fields"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"

        response = await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Test User"
        })

        api_assert.assert_created(response)
        data = response.json()

        # Contract: Response must have these fields
        api_assert.assert_has_fields(data, [
            "user_id", "email", "name", "is_active",
            "preferences", "created_at"
        ])

        assert data["user_id"] == user_id
        assert data["email"] == f"{user_id}@test.example.com"
        assert data["name"] == "Test User"
        assert data["is_active"] is True
        assert isinstance(data["preferences"], dict)

    async def test_ensure_returns_existing_account(self, account_api, api_assert):
        """RED: Existing account should be returned without modification"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        email = f"{user_id}@test.example.com"

        # First call creates
        response1 = await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": email,
            "name": "Original Name"
        })
        api_assert.assert_created(response1)

        # Second call returns existing
        response2 = await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": email,
            "name": "Different Name"  # Should not update
        })
        api_assert.assert_created(response2)

        data = response2.json()
        assert data["user_id"] == user_id
        # Name should remain original (ensure doesn't update)
        assert data["name"] == "Original Name"

    async def test_ensure_validates_required_fields(self, account_api, api_assert):
        """RED: Missing required fields should return 422"""
        # Missing user_id
        response = await account_api.post("/ensure", json={
            "email": "test@example.com",
            "name": "Test User"
        })
        api_assert.assert_validation_error(response)

        # Missing email
        response = await account_api.post("/ensure", json={
            "user_id": "usr_test123",
            "name": "Test User"
        })
        api_assert.assert_validation_error(response)

        # Missing name
        response = await account_api.post("/ensure", json={
            "user_id": "usr_test123",
            "email": "test@example.com"
        })
        api_assert.assert_validation_error(response)

    async def test_ensure_validates_email_format(self, account_api, api_assert):
        """RED: Invalid email format should return 422"""
        response = await account_api.post("/ensure", json={
            "user_id": "usr_test123",
            "email": "invalid-email",
            "name": "Test User"
        })
        api_assert.assert_validation_error(response)


class TestAccountProfileEndpoint:
    """
    GET/PUT/DELETE /api/v1/accounts/profile/{user_id}

    Account profile CRUD operations.
    """

    async def test_get_profile_returns_full_account(self, account_api, api_assert):
        """RED: Get profile should return complete account data"""
        # Create account first
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Profile Test User"
        })

        # Get profile
        response = await account_api.get(f"/profile/{user_id}")

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Profile response fields
        api_assert.assert_has_fields(data, [
            "user_id", "email", "name", "is_active",
            "preferences", "created_at", "updated_at"
        ])

        assert data["user_id"] == user_id
        assert data["is_active"] is True

    async def test_get_profile_not_found(self, account_api, api_assert):
        """RED: Non-existent account should return 404"""
        response = await account_api.get("/profile/usr_nonexistent_12345")
        api_assert.assert_not_found(response)

    async def test_update_profile_name(self, account_api, api_assert):
        """RED: Profile update should change specified fields"""
        # Create account
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Original Name"
        })

        # Update name
        response = await account_api.put(f"/profile/{user_id}", json={
            "name": "Updated Name"
        })

        api_assert.assert_success(response)
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["email"] == f"{user_id}@test.example.com"  # Unchanged

    async def test_update_profile_email(self, account_api, api_assert):
        """RED: Email update should be allowed"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Test User"
        })

        new_email = f"{user_id}_updated@test.example.com"
        response = await account_api.put(f"/profile/{user_id}", json={
            "email": new_email
        })

        api_assert.assert_success(response)
        assert response.json()["email"] == new_email

    async def test_update_profile_preserves_preferences(self, account_api, api_assert):
        """RED: Profile update should preserve existing preferences (only updates name/email)"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Test User"
        })

        # Set preferences via preferences endpoint (not profile)
        await account_api.put(f"/preferences/{user_id}", json={
            "theme": "dark", "language": "en"
        })

        # Update profile (name only) - preferences should be preserved
        response = await account_api.put(f"/profile/{user_id}", json={
            "name": "Updated Name"
        })

        api_assert.assert_success(response)
        assert response.json()["name"] == "Updated Name"
        prefs = response.json()["preferences"]
        assert prefs.get("theme") == "dark"
        assert prefs.get("language") == "en"

    async def test_update_profile_not_found(self, account_api, api_assert):
        """RED: Updating non-existent account should return 404"""
        response = await account_api.put("/profile/usr_nonexistent_12345", json={
            "name": "New Name"
        })
        api_assert.assert_not_found(response)

    async def test_update_profile_validates_email_format(self, account_api, api_assert):
        """RED: Invalid email in update should return 422"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Test User"
        })

        response = await account_api.put(f"/profile/{user_id}", json={
            "email": "not-valid-email"
        })
        api_assert.assert_validation_error(response)

    async def test_delete_profile_success(self, account_api, api_assert):
        """RED: Delete should soft-delete the account"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "To Be Deleted"
        })

        response = await account_api.delete(f"/profile/{user_id}")
        api_assert.assert_success(response)

        # After delete, get should return 404 or inactive account
        get_response = await account_api.get(f"/profile/{user_id}")
        # Either 404 or is_active=False is acceptable
        if get_response.status_code == 200:
            assert get_response.json()["is_active"] is False
        else:
            assert get_response.status_code == 404

    async def test_delete_profile_idempotent(self, account_api, api_assert):
        """RED: Deleting non-existent account is idempotent (returns 200)

        Design: DELETE is idempotent - calling delete on non-existent resource
        succeeds (the resource is already in the desired state: gone).
        """
        response = await account_api.delete("/profile/usr_nonexistent_12345")
        # Idempotent DELETE: 200 is acceptable for non-existent resource
        api_assert.assert_success(response)


class TestAccountPreferencesEndpoint:
    """
    PUT /api/v1/accounts/preferences/{user_id}

    Update account preferences.
    """

    async def test_update_preferences_timezone(self, account_api, api_assert):
        """RED: Should update timezone preference"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Preferences Test"
        })

        response = await account_api.put(f"/preferences/{user_id}", json={
            "timezone": "America/New_York"
        })

        api_assert.assert_success(response)

    async def test_update_preferences_theme(self, account_api, api_assert):
        """RED: Theme must be light, dark, or auto"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Theme Test"
        })

        # Valid themes
        for theme in ["light", "dark", "auto"]:
            response = await account_api.put(f"/preferences/{user_id}", json={
                "theme": theme
            })
            api_assert.assert_success(response)

        # Invalid theme
        response = await account_api.put(f"/preferences/{user_id}", json={
            "theme": "invalid"
        })
        api_assert.assert_validation_error(response)

    async def test_update_preferences_notifications(self, account_api, api_assert):
        """RED: Should update notification preferences"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Notification Test"
        })

        response = await account_api.put(f"/preferences/{user_id}", json={
            "notification_email": True,
            "notification_push": False
        })

        api_assert.assert_success(response)

    async def test_update_preferences_language(self, account_api, api_assert):
        """RED: Language should be max 5 characters"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Language Test"
        })

        # Valid language codes
        response = await account_api.put(f"/preferences/{user_id}", json={
            "language": "en"
        })
        api_assert.assert_success(response)

        response = await account_api.put(f"/preferences/{user_id}", json={
            "language": "zh-CN"
        })
        api_assert.assert_success(response)


class TestAccountListEndpoint:
    """
    GET /api/v1/accounts

    List accounts with filtering and pagination.
    """

    async def test_list_accounts_returns_paginated_response(self, account_api, api_assert):
        """RED: List should return paginated account summaries"""
        response = await account_api.get("")

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Paginated response structure
        api_assert.assert_has_fields(data, [
            "accounts", "total_count", "page", "page_size", "has_next"
        ])

        assert isinstance(data["accounts"], list)
        assert isinstance(data["total_count"], int)
        assert data["page"] >= 1
        assert data["page_size"] >= 1

    async def test_list_accounts_pagination(self, account_api, api_assert):
        """RED: Pagination parameters should work correctly"""
        response = await account_api.get("", params={
            "page": 1,
            "page_size": 10
        })

        api_assert.assert_success(response)
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["accounts"]) <= 10

    async def test_list_accounts_filter_active(self, account_api, api_assert):
        """RED: Should filter by active status"""
        response = await account_api.get("", params={
            "is_active": True
        })

        api_assert.assert_success(response)
        data = response.json()

        # All returned accounts should be active
        for account in data["accounts"]:
            assert account["is_active"] is True

    async def test_list_accounts_search(self, account_api, api_assert):
        """RED: Should search in name/email"""
        # Create a unique account
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        unique_name = f"UniqueSearchTest_{uuid.uuid4().hex[:8]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": unique_name
        })

        response = await account_api.get("", params={
            "search": unique_name
        })

        api_assert.assert_success(response)
        data = response.json()

        # Should find the account
        assert data["total_count"] >= 1
        found = any(a["name"] == unique_name for a in data["accounts"])
        assert found, f"Expected to find account with name {unique_name}"

    async def test_list_accounts_summary_fields(self, account_api, api_assert):
        """RED: Account summaries should have required fields"""
        # Ensure at least one account exists
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Summary Test"
        })

        response = await account_api.get("")
        api_assert.assert_success(response)

        accounts = response.json()["accounts"]
        if accounts:
            # Each account summary should have these fields
            api_assert.assert_has_fields(accounts[0], [
                "user_id", "email", "name", "is_active", "created_at"
            ])


class TestAccountSearchEndpoint:
    """
    GET /api/v1/accounts/search

    Search accounts by query.
    """

    async def test_search_accounts_by_name(self, account_api, api_assert):
        """RED: Should find accounts matching name query"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        unique_name = f"SearchableUser_{uuid.uuid4().hex[:8]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": unique_name
        })

        response = await account_api.get("/search", params={
            "query": unique_name[:10]  # Partial match
        })

        api_assert.assert_success(response)
        data = response.json()

        assert isinstance(data, list)
        found = any(a["name"] == unique_name for a in data)
        assert found

    async def test_search_accounts_by_email(self, account_api, api_assert):
        """RED: Should find accounts matching email query"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@searchtest.example.com",
            "name": "Email Search Test"
        })

        response = await account_api.get("/search", params={
            "query": f"{user_id}@searchtest"
        })

        api_assert.assert_success(response)

    async def test_search_requires_query(self, account_api, api_assert):
        """RED: Search without query should return 422"""
        response = await account_api.get("/search")
        api_assert.assert_validation_error(response)

    async def test_search_respects_limit(self, account_api, api_assert):
        """RED: Search should respect limit parameter"""
        response = await account_api.get("/search", params={
            "query": "test",
            "limit": 5
        })

        api_assert.assert_success(response)
        data = response.json()
        assert len(data) <= 5


class TestAccountByEmailEndpoint:
    """
    GET /api/v1/accounts/by-email/{email}

    Get account by email address.
    """

    async def test_get_by_email_found(self, account_api, api_assert):
        """RED: Should return account for valid email"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        email = f"{user_id}@byemail.example.com"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": email,
            "name": "By Email Test"
        })

        response = await account_api.get(f"/by-email/{email}")

        api_assert.assert_success(response)
        data = response.json()

        assert data["email"] == email
        assert data["user_id"] == user_id

    async def test_get_by_email_not_found(self, account_api, api_assert):
        """RED: Non-existent email should return 404"""
        response = await account_api.get("/by-email/nonexistent@example.com")
        api_assert.assert_not_found(response)


class TestAccountStatusEndpoint:
    """
    PUT /api/v1/accounts/status/{user_id}

    Change account status (admin operation).
    """

    async def test_deactivate_account(self, account_api, api_assert):
        """RED: Should deactivate an active account"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "To Be Deactivated"
        })

        response = await account_api.put(f"/status/{user_id}", json={
            "is_active": False,
            "reason": "Test deactivation"
        })

        api_assert.assert_success(response)

        # Verify deactivation
        get_response = await account_api.get(f"/profile/{user_id}")
        if get_response.status_code == 200:
            assert get_response.json()["is_active"] is False

    async def test_reactivate_account(self, account_api, api_assert):
        """RED: Should reactivate a deactivated account"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "To Be Reactivated"
        })

        # Deactivate
        await account_api.put(f"/status/{user_id}", json={
            "is_active": False,
            "reason": "Deactivating"
        })

        # Reactivate
        response = await account_api.put(f"/status/{user_id}", json={
            "is_active": True,
            "reason": "Reactivating"
        })

        api_assert.assert_success(response)

    async def test_status_change_requires_is_active(self, account_api, api_assert):
        """RED: is_active field is required"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        await account_api.post("/ensure", json={
            "user_id": user_id,
            "email": f"{user_id}@test.example.com",
            "name": "Status Test"
        })

        response = await account_api.put(f"/status/{user_id}", json={
            "reason": "Missing is_active"
        })
        api_assert.assert_validation_error(response)


class TestAccountStatsEndpoint:
    """
    GET /api/v1/accounts/stats

    Get account service statistics.
    """

    async def test_get_stats_returns_counts(self, account_api, api_assert):
        """RED: Stats should return account counts"""
        response = await account_api.get("/stats")

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Stats response fields
        api_assert.assert_has_fields(data, [
            "total_accounts",
            "active_accounts",
            "inactive_accounts",
            "recent_registrations_7d",
            "recent_registrations_30d"
        ])

        assert isinstance(data["total_accounts"], int)
        assert isinstance(data["active_accounts"], int)
        assert data["total_accounts"] >= 0
        assert data["active_accounts"] >= 0


class TestAccountHealthEndpoints:
    """
    GET /health
    GET /health/detailed

    Service health check endpoints.
    """

    async def test_health_check(self, http_client, api_assert):
        """RED: Health check should return service status"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("account")
        response = await http_client.get(f"{base_url}/health")

        api_assert.assert_success(response)
        data = response.json()

        assert "status" in data

    async def test_health_detailed(self, http_client, api_assert):
        """RED: Detailed health should include database status"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("account")
        response = await http_client.get(f"{base_url}/health/detailed")

        api_assert.assert_success(response)
        data = response.json()

        assert "status" in data
        assert "database" in data or "database_connected" in data


class TestAccountErrorContracts:
    """
    Test error response contracts for Account API.
    """

    async def test_404_response_format(self, account_api):
        """RED: 404 errors should have consistent format"""
        response = await account_api.get("/profile/usr_nonexistent_12345")

        assert response.status_code == 404
        data = response.json()

        # Should have detail message
        assert "detail" in data or "message" in data or "error" in data

    async def test_422_response_format(self, account_api):
        """RED: 422 validation errors should have detail array"""
        response = await account_api.post("/ensure", json={
            "email": "invalid"
            # Missing required fields
        })

        assert response.status_code == 422
        data = response.json()

        # FastAPI returns detail with validation errors
        assert "detail" in data
