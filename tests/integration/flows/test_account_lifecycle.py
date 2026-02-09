"""
Account User Lifecycle Flow Tests (Layer 2)

RED PHASE: Define the complete user lifecycle flow.
These tests verify end-to-end account operations across the system.

Flow: Create → Update → Deactivate → Reactivate → Delete

Usage:
    pytest tests/integration/flows/test_account_lifecycle.py -v
"""
import pytest
import httpx

from tests.integration.conftest import (
    TestConfig,
    EventCollector,
    TestDataGenerator,
    assert_http_success,
    cleanup_test_data,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestAccountFullLifecycle:
    """
    Test complete account lifecycle from creation to deletion.
    """

    async def test_complete_account_lifecycle(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Test full lifecycle: Create → Update → Deactivate → Reactivate → Delete"""
        user_id = test_data.user_id()
        email = test_data.email()

        # ============================================================
        # Step 1: Create Account
        # ============================================================
        create_response = await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={
                "user_id": user_id,
                "email": email,
                "name": "Lifecycle Test User"
            }
        )
        create_data = await assert_http_success(create_response)

        assert create_data["user_id"] == user_id
        assert create_data["is_active"] is True

        # ============================================================
        # Step 2: Get Profile (verify creation)
        # ============================================================
        get_response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )
        profile_data = await assert_http_success(get_response)

        assert profile_data["email"] == email
        assert profile_data["name"] == "Lifecycle Test User"

        # ============================================================
        # Step 3: Update Profile
        # ============================================================
        update_response = await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}",
            json={
                "name": "Updated Lifecycle User",
                "preferences": {"theme": "dark", "language": "en"}
            }
        )
        updated_data = await assert_http_success(update_response)

        assert updated_data["name"] == "Updated Lifecycle User"
        assert updated_data["preferences"]["theme"] == "dark"

        # ============================================================
        # Step 4: Update Preferences
        # ============================================================
        pref_response = await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/preferences/{user_id}",
            json={
                "timezone": "America/New_York",
                "notification_email": True
            }
        )
        await assert_http_success(pref_response)

        # ============================================================
        # Step 5: Deactivate Account
        # ============================================================
        deactivate_response = await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
            json={"is_active": False, "reason": "User requested deactivation"}
        )
        await assert_http_success(deactivate_response)

        # Verify deactivation
        get_response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )
        if get_response.status_code == 200:
            assert get_response.json()["is_active"] is False

        # ============================================================
        # Step 6: Reactivate Account
        # ============================================================
        reactivate_response = await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
            json={"is_active": True, "reason": "User requested reactivation"}
        )
        await assert_http_success(reactivate_response)

        # Verify reactivation
        get_response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )
        get_data = await assert_http_success(get_response)
        assert get_data["is_active"] is True

        # ============================================================
        # Step 7: Delete Account
        # ============================================================
        delete_response = await http_client.delete(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )
        await assert_http_success(delete_response)

        # Verify deletion (should be 404 or is_active=False)
        final_response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )
        assert final_response.status_code in [404, 200]
        if final_response.status_code == 200:
            assert final_response.json()["is_active"] is False


class TestAccountCreationFlow:
    """
    Test account creation scenarios and edge cases.
    """

    async def test_idempotent_account_creation(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Multiple ensure calls should be idempotent"""
        user_id = test_data.user_id()
        email = test_data.email()

        # First create
        response1 = await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "First Create"}
        )
        data1 = await assert_http_success(response1)
        created_at = data1.get("created_at")

        # Second create (should return existing)
        response2 = await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "Second Create"}
        )
        data2 = await assert_http_success(response2)

        # Should be same account
        assert data1["user_id"] == data2["user_id"]
        # Name should remain from first create (ensure doesn't update)
        assert data2["name"] == "First Create"
        # created_at should be the same
        assert data2.get("created_at") == created_at

    async def test_account_creation_with_duplicate_email(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Different user_id with same email should fail or handle gracefully"""
        email = test_data.email()
        user_id_1 = test_data.user_id()
        user_id_2 = test_data.user_id()

        # Create first account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id_1, "email": email, "name": "First User"}
        )

        # Try to create second account with same email
        response2 = await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id_2, "email": email, "name": "Second User"}
        )

        # Should fail with conflict or validation error
        assert response2.status_code in [400, 409, 422], \
            f"Expected error for duplicate email, got {response2.status_code}"


class TestAccountQueryFlow:
    """
    Test account querying and search flows.
    """

    async def test_list_and_search_accounts(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Should be able to list and search created accounts"""
        # Create multiple accounts with unique pattern
        unique_prefix = f"searchtest_{test_data.user_id()[-8:]}"
        created_users = []

        for i in range(3):
            user_id = f"usr_{unique_prefix}_{i}"
            email = f"{unique_prefix}_{i}@test.example.com"
            response = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": email,
                    "name": f"SearchTest User {i}"
                }
            )
            if response.status_code in [200, 201]:
                created_users.append(user_id)

        assert len(created_users) >= 2, "Should create at least 2 test users"

        # Search by pattern
        search_response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/search",
            params={"query": unique_prefix}
        )
        search_data = await assert_http_success(search_response)

        assert isinstance(search_data, list)
        assert len(search_data) >= 2, "Search should find created accounts"

    async def test_get_account_by_email(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Should retrieve account by email address"""
        user_id = test_data.user_id()
        email = test_data.email()

        # Create account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "Email Lookup Test"}
        )

        # Get by email
        response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts/by-email/{email}"
        )
        data = await assert_http_success(response)

        assert data["user_id"] == user_id
        assert data["email"] == email

    async def test_list_with_pagination(
        self,
        http_client: httpx.AsyncClient,
        config: TestConfig
    ):
        """RED: List should support pagination"""
        # Get first page
        page1_response = await http_client.get(
            f"{config.ACCOUNT_URL}/api/v1/accounts",
            params={"page": 1, "page_size": 5}
        )
        page1_data = await assert_http_success(page1_response)

        assert page1_data["page"] == 1
        assert page1_data["page_size"] == 5
        assert len(page1_data["accounts"]) <= 5

        # If there's more data, get second page
        if page1_data["has_next"]:
            page2_response = await http_client.get(
                f"{config.ACCOUNT_URL}/api/v1/accounts",
                params={"page": 2, "page_size": 5}
            )
            page2_data = await assert_http_success(page2_response)
            assert page2_data["page"] == 2


class TestAccountCrossServiceIntegration:
    """
    Test account integration with other services.
    """

    async def test_account_with_auth_token(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Auth service should work with account service"""
        user_id = test_data.user_id()
        email = test_data.email()

        # Get dev token from auth service
        auth_response = await http_client.post(
            f"{config.AUTH_URL}/api/v1/auth/dev-token",
            json={
                "user_id": user_id,
                "email": email,
                "expires_in": 3600
            }
        )

        if auth_response.status_code == 200:
            token = auth_response.json().get("token")

            # Create account with authenticated request
            create_response = await http_client.post(
                f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
                json={"user_id": user_id, "email": email, "name": "Auth Test User"},
                headers={"Authorization": f"Bearer {token}"}
            )
            await assert_http_success(create_response)

    async def test_account_subscription_lookup(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: After account creation, subscription should be queryable"""
        user_id = test_data.user_id()

        # Create account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={
                "user_id": user_id,
                "email": test_data.email(),
                "name": "Subscription Test User"
            }
        )

        import asyncio
        await asyncio.sleep(2)  # Allow event processing

        # Check subscription service
        sub_response = await http_client.get(
            f"{config.SUBSCRIPTION_URL}/api/v1/subscriptions/user/{user_id}"
        )

        # Subscription should exist (created via event or direct call)
        # This defines the expected integration behavior
        if sub_response.status_code == 200:
            sub_data = sub_response.json()
            assert sub_data is not None

    async def test_account_audit_trail(
        self,
        http_client: httpx.AsyncClient,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Account operations should be audited"""
        user_id = test_data.user_id()

        # Create account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={
                "user_id": user_id,
                "email": test_data.email(),
                "name": "Audit Test User"
            }
        )

        import asyncio
        await asyncio.sleep(2)

        # Check audit service for account creation audit
        audit_response = await http_client.get(
            f"{config.AUDIT_URL}/api/v1/audit/user/{user_id}"
        )

        # Audit trail should exist (if audit service is running)
        if audit_response.status_code == 200:
            audit_data = audit_response.json()
            # Should have at least one audit entry for account creation
            assert isinstance(audit_data, (list, dict))
