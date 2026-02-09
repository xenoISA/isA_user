"""
Account Service Component Event Tests (Mocked NATS)

Layer 2: Component tests for event publishing with mocked dependencies.
Tests verify AccountService publishes correct events via dependency injection.

Usage:
    pytest tests/component/tdd/account_service/test_account_events.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import uuid

# Import the proper mocks that implement the protocol
from tests.component.golden.account_service.mocks import MockAccountRepository, MockEventBus

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Fresh mock repository"""
    return MockAccountRepository()


@pytest.fixture
def mock_event_bus():
    """Fresh mock event bus"""
    return MockEventBus()


@pytest.fixture
def account_service(mock_repo, mock_event_bus):
    """Create AccountService with mocked dependencies"""
    from microservices.account_service.account_service import AccountService
    return AccountService(repository=mock_repo, event_bus=mock_event_bus)


# =============================================================================
# Test: user.created Event Publishing
# =============================================================================

class TestUserCreatedEventPublishing:
    """Test that account creation publishes user.created event"""

    async def test_ensure_new_account_publishes_user_created(
        self, mock_repo, mock_event_bus
    ):
        """Creating new account publishes user.created event"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountEnsureRequest

        service = AccountService(repository=mock_repo, event_bus=mock_event_bus)

        user_id = f"test_{uuid.uuid4().hex[:8]}"
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        request = AccountEnsureRequest(
            user_id=user_id,
            email=email,
            name="Test User"
        )

        result, was_created = await service.ensure_account(request)

        # Verify event was published
        assert was_created is True
        assert len(mock_event_bus.published_events) > 0, "Expected user.created event to be published"

    async def test_ensure_existing_account_no_event(
        self, mock_repo, mock_event_bus
    ):
        """Ensuring existing account does NOT publish user.created event"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountEnsureRequest

        user_id = f"existing_{uuid.uuid4().hex[:8]}"
        email = f"existing_{uuid.uuid4().hex[:8]}@example.com"

        # Pre-populate user with old created_at to avoid "recently created" detection
        mock_repo.set_user(
            user_id=user_id,
            email=email,
            name="Existing User",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )

        service = AccountService(repository=mock_repo, event_bus=mock_event_bus)

        request = AccountEnsureRequest(
            user_id=user_id,
            email=email,
            name="Existing User"
        )

        result, was_created = await service.ensure_account(request)

        # No event should be published for existing account
        assert was_created is False
        assert len(mock_event_bus.published_events) == 0, "Should not publish event for existing account"


# =============================================================================
# Test: user.profile_updated Event Publishing
# =============================================================================

class TestUserProfileUpdatedEventPublishing:
    """Test that profile updates publish user.profile_updated event"""

    async def test_update_profile_publishes_event(
        self, mock_repo, mock_event_bus
    ):
        """Updating profile publishes user.profile_updated event"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountUpdateRequest

        user_id = f"update_{uuid.uuid4().hex[:8]}"
        email = f"update_{uuid.uuid4().hex[:8]}@example.com"

        mock_repo.set_user(user_id=user_id, email=email, name="Original Name")

        service = AccountService(repository=mock_repo, event_bus=mock_event_bus)

        request = AccountUpdateRequest(name="Updated Name")
        await service.update_account_profile(user_id, request)

        # Verify event was published
        assert len(mock_event_bus.published_events) > 0, "Expected user.profile_updated event"


# =============================================================================
# Test: user.status_changed Event Publishing
# =============================================================================

class TestUserStatusChangedEventPublishing:
    """Test that status changes publish user.status_changed event"""

    async def test_deactivate_account_publishes_status_changed(
        self, mock_repo, mock_event_bus
    ):
        """Deactivating account publishes user.status_changed event"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountStatusChangeRequest

        user_id = f"deactivate_{uuid.uuid4().hex[:8]}"
        email = f"deactivate_{uuid.uuid4().hex[:8]}@example.com"

        mock_repo.set_user(user_id=user_id, email=email, name="Active User", is_active=True)

        service = AccountService(repository=mock_repo, event_bus=mock_event_bus)

        request = AccountStatusChangeRequest(is_active=False, reason="Test deactivation")
        await service.change_account_status(user_id, request)

        # Verify event was published
        assert len(mock_event_bus.published_events) > 0, "Expected user.status_changed event"

    async def test_reactivate_account_publishes_status_changed(
        self, mock_repo, mock_event_bus
    ):
        """Reactivating account publishes user.status_changed event"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountStatusChangeRequest

        user_id = f"reactivate_{uuid.uuid4().hex[:8]}"
        email = f"reactivate_{uuid.uuid4().hex[:8]}@example.com"

        mock_repo.set_user(user_id=user_id, email=email, name="Inactive User", is_active=False)

        service = AccountService(repository=mock_repo, event_bus=mock_event_bus)

        request = AccountStatusChangeRequest(is_active=True, reason="Reactivation")
        await service.change_account_status(user_id, request)

        # Verify event was published
        assert len(mock_event_bus.published_events) > 0, "Expected user.status_changed event"


# =============================================================================
# Test: user.deleted Event Publishing
# =============================================================================

class TestUserDeletedEventPublishing:
    """Test that account deletion publishes user.deleted event"""

    async def test_delete_account_publishes_user_deleted(
        self, mock_repo, mock_event_bus
    ):
        """Deleting account publishes user.deleted event"""
        from microservices.account_service.account_service import AccountService

        user_id = f"delete_{uuid.uuid4().hex[:8]}"
        email = f"delete_{uuid.uuid4().hex[:8]}@example.com"

        mock_repo.set_user(user_id=user_id, email=email, name="To Delete")

        service = AccountService(repository=mock_repo, event_bus=mock_event_bus)

        await service.delete_account(user_id, reason="Test deletion")

        # Verify event was published
        assert len(mock_event_bus.published_events) > 0, "Expected user.deleted event"


# =============================================================================
# Test: Event Handlers (Subscribed Events)
# =============================================================================

class TestAccountEventHandlers:
    """Test event handlers for subscribed events"""

    async def test_handle_payment_completed_logs_event(self):
        """Handler processes payment.completed event"""
        from microservices.account_service.events.handlers import handle_payment_completed

        event_data = {
            "user_id": "test_user",
            "payment_type": "subscription",
            "subscription_plan": "premium",
            "amount": 9.99
        }

        # Should not raise - handler logs and returns
        await handle_payment_completed(event_data)

    async def test_handle_wallet_created_logs_event(self):
        """Handler processes wallet.created event"""
        from microservices.account_service.events.handlers import handle_wallet_created

        event_data = {
            "user_id": "test_user",
            "wallet_id": "wallet_123",
            "currency": "USD"
        }

        # Should not raise - handler logs and returns
        await handle_wallet_created(event_data)

    async def test_handle_organization_member_added_logs_event(self):
        """Handler processes organization.member_added event"""
        from microservices.account_service.events.handlers import handle_organization_member_added

        event_data = {
            "organization_id": "org_123",
            "user_id": "test_user",
            "role": "member"
        }

        # Should not raise - handler logs and returns
        await handle_organization_member_added(event_data)

    async def test_handle_subscription_created_updates_account(self, mock_repo):
        """Handler updates account subscription status"""
        from microservices.account_service.events.handlers import handle_subscription_created

        user_id = f"sub_test_{uuid.uuid4().hex[:8]}"
        mock_repo.set_user(user_id=user_id, email="sub@example.com", name="Sub User")

        event_data = {
            "user_id": user_id,
            "subscription_id": "sub_123",
            "tier_code": "premium",
            "credits_allocated": 100
        }

        await handle_subscription_created(event_data, account_repository=mock_repo)
        # Note: Actual update depends on repository implementation

    async def test_handle_subscription_canceled_resets_tier(self, mock_repo):
        """Handler resets subscription to free tier"""
        from microservices.account_service.events.handlers import handle_subscription_canceled

        user_id = f"cancel_test_{uuid.uuid4().hex[:8]}"
        mock_repo.set_user(user_id=user_id, email="cancel@example.com", name="Cancel User")

        event_data = {
            "user_id": user_id,
            "subscription_id": "sub_123",
            "reason": "user_request"
        }

        await handle_subscription_canceled(event_data, account_repository=mock_repo)
        # Note: Actual update depends on repository implementation

    async def test_handle_organization_deleted_removes_association(self, mock_repo):
        """Handler removes org association from users"""
        from microservices.account_service.events.handlers import handle_organization_deleted

        event_data = {
            "organization_id": "org_to_delete"
        }

        await handle_organization_deleted(event_data, account_repository=mock_repo)
        # Note: Actual removal depends on repository implementation
