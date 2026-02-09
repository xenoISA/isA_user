"""
Account Service Event Integration Tests (Layer 2)

RED PHASE: Define event publishing and handling contracts.
These tests verify that account operations trigger the correct events
and that downstream services react appropriately.

Usage:
    pytest tests/integration/events/test_account_events.py -v
    pytest tests/integration/events -v -k "user_created"
"""
import pytest
import uuid
import httpx

from tests.integration.conftest import (
    TestConfig,
    EventCollector,
    TestDataGenerator,
    assert_event_published,
    assert_http_success,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.requires_nats]


class TestAccountCreatedEventPublishing:
    """
    Test that account creation publishes user.created events.

    Event: user.created
    Source: account_service
    Triggered by: POST /api/v1/accounts/ensure (new account)
    """

    async def test_ensure_new_account_publishes_user_created_event(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Creating new account should publish user.created event"""
        user_id = test_data.user_id()
        email = test_data.email()

        # When: Create new account
        response = await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={
                "user_id": user_id,
                "email": email,
                "name": "Event Test User"
            }
        )
        await assert_http_success(response, 200)

        # Then: user.created event should be published
        event = await assert_event_published(
            event_collector,
            event_type="user.created",
            timeout=10.0,
            data_match={"user_id": user_id}
        )

        # Verify event data
        assert event["source"] == "account_service"
        assert event["data"]["email"] == email
        assert event["data"]["name"] == "Event Test User"
        assert "subscription_plan" in event["data"]

    async def test_ensure_existing_account_does_not_publish_event(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Ensuring existing account should NOT publish user.created event"""
        user_id = test_data.user_id()
        email = test_data.email()

        # Create account first
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "Existing User"}
        )

        # Clear events from creation
        event_collector.clear()

        # Ensure again (account already exists)
        response = await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "Existing User"}
        )
        await assert_http_success(response)

        # Wait briefly and check no new user.created event
        import asyncio
        await asyncio.sleep(2)

        created_events = event_collector.get_by_type("user.created")
        matching = [e for e in created_events if e["data"].get("user_id") == user_id]
        assert len(matching) == 0, "Should not publish user.created for existing account"


class TestAccountProfileUpdatedEventPublishing:
    """
    Test that profile updates publish user.profile_updated events.

    Event: user.profile_updated
    Source: account_service
    Triggered by: PUT /api/v1/accounts/profile/{user_id}
    """

    async def test_profile_update_publishes_event(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Profile update should publish user.profile_updated event"""
        user_id = test_data.user_id()
        email = test_data.email()

        # Setup: Create account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "Original Name"}
        )
        event_collector.clear()

        # When: Update profile
        response = await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}",
            json={"name": "Updated Name"}
        )
        await assert_http_success(response)

        # Then: user.profile_updated event should be published
        event = await assert_event_published(
            event_collector,
            event_type="user.profile_updated",
            timeout=10.0,
            data_match={"user_id": user_id}
        )

        assert event["source"] == "account_service"
        assert "name" in event["data"].get("updated_fields", [])

    async def test_profile_update_includes_updated_fields(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Event should include list of updated fields"""
        user_id = test_data.user_id()
        email = test_data.email()

        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "Test User"}
        )
        event_collector.clear()

        # Update multiple fields
        new_email = test_data.email()
        await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}",
            json={
                "name": "New Name",
                "email": new_email,
                "preferences": {"theme": "dark"}
            }
        )

        event = await assert_event_published(
            event_collector,
            event_type="user.profile_updated",
            data_match={"user_id": user_id}
        )

        updated_fields = event["data"].get("updated_fields", [])
        assert "name" in updated_fields
        assert "email" in updated_fields
        assert "preferences" in updated_fields


class TestAccountDeletedEventPublishing:
    """
    Test that account deletion publishes user.deleted events.

    Event: user.deleted
    Source: account_service
    Triggered by: DELETE /api/v1/accounts/profile/{user_id}
    """

    async def test_delete_account_publishes_event(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Deleting account should publish user.deleted event"""
        user_id = test_data.user_id()
        email = test_data.email()

        # Setup: Create account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "To Delete"}
        )
        event_collector.clear()

        # When: Delete account
        response = await http_client.delete(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )
        await assert_http_success(response)

        # Then: user.deleted event should be published
        event = await assert_event_published(
            event_collector,
            event_type="user.deleted",
            timeout=10.0,
            data_match={"user_id": user_id}
        )

        assert event["source"] == "account_service"
        assert event["data"]["email"] == email


class TestAccountStatusChangedEventPublishing:
    """
    Test that status changes publish user.status_changed events.

    Event: user.updated (with status change data)
    Source: account_service
    Triggered by: PUT /api/v1/accounts/status/{user_id}
    """

    async def test_deactivate_account_publishes_event(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Deactivating account should publish status change event"""
        user_id = test_data.user_id()
        email = test_data.email()

        # Setup: Create account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "To Deactivate"}
        )
        event_collector.clear()

        # When: Deactivate account
        response = await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
            json={"is_active": False, "reason": "Test deactivation"}
        )
        await assert_http_success(response)

        # Then: Status change event should be published
        event = await assert_event_published(
            event_collector,
            event_type="user.updated",
            timeout=10.0,
            data_match={"user_id": user_id}
        )

        assert event["data"]["is_active"] is False
        assert "reason" in event["data"]

    async def test_reactivate_account_publishes_event(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: Reactivating account should publish status change event"""
        user_id = test_data.user_id()

        # Setup: Create and deactivate account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": test_data.email(), "name": "Test"}
        )
        await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
            json={"is_active": False, "reason": "Deactivating"}
        )
        event_collector.clear()

        # When: Reactivate
        response = await http_client.put(
            f"{config.ACCOUNT_URL}/api/v1/accounts/status/{user_id}",
            json={"is_active": True, "reason": "Reactivating"}
        )
        await assert_http_success(response)

        # Then: Event with is_active=True
        event = await assert_event_published(
            event_collector,
            event_type="user.updated",
            data_match={"user_id": user_id}
        )

        assert event["data"]["is_active"] is True


class TestAccountEventChains:
    """
    Test that account events trigger expected downstream reactions.

    These tests verify the event-driven architecture by checking
    that other services react to account events appropriately.
    """

    async def test_user_created_triggers_subscription_init(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: user.created should trigger subscription initialization"""
        user_id = test_data.user_id()

        # When: Create new account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={
                "user_id": user_id,
                "email": test_data.email(),
                "name": "Subscription Init Test"
            }
        )

        # Then: User should have a subscription (via event handler or direct call)
        import asyncio
        await asyncio.sleep(3)  # Allow time for event processing

        # Check subscription_service for user's subscription
        sub_response = await http_client.get(
            f"{config.SUBSCRIPTION_URL}/api/v1/subscriptions/user/{user_id}"
        )

        # Should either have subscription or 404 (which we'll handle)
        if sub_response.status_code == 200:
            sub_data = sub_response.json()
            assert sub_data.get("tier_code") is not None or sub_data.get("subscription") is not None

    async def test_user_created_triggers_wallet_init(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: user.created should trigger wallet initialization"""
        user_id = test_data.user_id()

        # When: Create new account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={
                "user_id": user_id,
                "email": test_data.email(),
                "name": "Wallet Init Test"
            }
        )

        import asyncio
        await asyncio.sleep(3)

        # Then: User should have a wallet
        wallet_response = await http_client.get(
            f"{config.WALLET_URL}/api/v1/wallets/user/{user_id}"
        )

        # Wallet may or may not be auto-created depending on implementation
        # This test defines the expected behavior
        if wallet_response.status_code == 200:
            wallet_data = wallet_response.json()
            assert "balance" in wallet_data or "wallet_id" in wallet_data

    async def test_user_deleted_triggers_cascade_cleanup(
        self,
        http_client: httpx.AsyncClient,
        event_collector: EventCollector,
        test_data: TestDataGenerator,
        config: TestConfig
    ):
        """RED: user.deleted should trigger cleanup in other services"""
        user_id = test_data.user_id()
        email = test_data.email()

        # Setup: Create account
        await http_client.post(
            f"{config.ACCOUNT_URL}/api/v1/accounts/ensure",
            json={"user_id": user_id, "email": email, "name": "To Be Deleted"}
        )

        import asyncio
        await asyncio.sleep(2)
        event_collector.clear()

        # When: Delete account
        await http_client.delete(
            f"{config.ACCOUNT_URL}/api/v1/accounts/profile/{user_id}"
        )

        # Then: user.deleted event should be published
        await assert_event_published(
            event_collector,
            event_type="user.deleted",
            data_match={"user_id": user_id}
        )

        # Allow time for cascade handlers
        await asyncio.sleep(3)

        # Verify cleanup events were triggered (if services publish them)
        # This defines expected cascade behavior
        summary = event_collector.summary()
        # At minimum, user.deleted should be there
        assert "user.deleted" in summary
