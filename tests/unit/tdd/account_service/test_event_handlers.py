"""
Account Service Event Handlers TDD Tests

RED: These tests verify that event handlers work with Event objects.
Currently FAILING - handlers call .get() on Event objects.

Issue Found: Event handlers receive Event objects with .data attribute,
but some handlers try to call .get() directly on the Event object.
"""
import pytest
from datetime import datetime

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class MockEvent:
    """Mock event object that mimics NATS CloudEvent"""

    def __init__(self, data: dict, event_type: str = "test.event"):
        self.data = data
        self.type = event_type
        self.source = "test"
        self.id = "test_event_id"
        self.timestamp = datetime.utcnow().isoformat()


class TestWalletCreatedHandlerDirect:
    """
    TDD RED: wallet.created handler should work with Event objects
    Test the raw handler function directly to avoid import issues
    """

    async def test_handles_event_object(self):
        """RED: Should handle Event object (not just dict)"""
        from microservices.account_service.events.handlers import handle_wallet_created

        # Create mock Event object (like NATS would send)
        event = MockEvent(
            data={
                "user_id": "usr_123",
                "wallet_id": "wal_456",
                "currency": "USD"
            },
            event_type="wallet.created"
        )

        # This will fail with: AttributeError: 'MockEvent' object has no attribute 'get'
        # Because handle_wallet_created expects a dict and calls event_data.get()
        await handle_wallet_created(event)

    async def test_handles_dict_directly(self):
        """GREEN: Works with dict"""
        from microservices.account_service.events.handlers import handle_wallet_created

        data = {
            "user_id": "usr_123",
            "wallet_id": "wal_456",
            "currency": "USD"
        }

        # Works fine with dict
        await handle_wallet_created(data)


class TestOrganizationMemberAddedHandlerDirect:
    """
    TDD RED: organization.member_added handler should work with Event objects
    """

    async def test_handles_event_object(self):
        """RED: Should handle Event object"""
        from microservices.account_service.events.handlers import handle_organization_member_added

        event = MockEvent(
            data={
                "organization_id": "org_123",
                "user_id": "usr_456",
                "role": "member"
            },
            event_type="organization.member_added"
        )

        # This will fail with: AttributeError: 'MockEvent' object has no attribute 'get'
        await handle_organization_member_added(event)

    async def test_handles_dict_directly(self):
        """GREEN: Works with dict"""
        from microservices.account_service.events.handlers import handle_organization_member_added

        data = {
            "organization_id": "org_123",
            "user_id": "usr_456",
            "role": "member"
        }

        await handle_organization_member_added(data)


class TestPaymentCompletedHandlerDirect:
    """
    TDD RED: payment.completed handler should work with Event objects
    """

    async def test_handles_event_object(self):
        """RED: Should handle Event object"""
        from microservices.account_service.events.handlers import handle_payment_completed

        event = MockEvent(
            data={
                "user_id": "usr_123",
                "payment_type": "subscription",
                "subscription_plan": "premium",
                "amount": 9.99
            },
            event_type="payment.completed"
        )

        # This will fail with: AttributeError: 'MockEvent' object has no attribute 'get'
        await handle_payment_completed(event)

    async def test_handles_dict_directly(self):
        """GREEN: Works with dict"""
        from microservices.account_service.events.handlers import handle_payment_completed

        data = {
            "user_id": "usr_123",
            "payment_type": "subscription",
            "subscription_plan": "premium",
            "amount": 9.99
        }

        await handle_payment_completed(data)
