"""
Account Service Component Golden Tests

These tests document CURRENT AccountService behavior with mocked deps.
Uses proper dependency injection - no patching needed!

Usage:
    pytest tests/component/golden -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from .mocks import MockAccountRepository, MockEventBus

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Create a fresh MockAccountRepository"""
    return MockAccountRepository()


@pytest.fixture
def mock_repo_with_user():
    """Create MockAccountRepository with existing user"""
    repo = MockAccountRepository()
    repo.set_user(
        user_id="usr_test_123",
        email="test@example.com",
        name="Test User",
        is_active=True,
        preferences={"theme": "dark"},
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    return repo


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_subscription_client():
    """Create mock subscription client"""
    client = AsyncMock()
    client.get_or_create_subscription = AsyncMock(return_value={
        "subscription": {"tier_code": "free", "status": "active"}
    })
    return client


# =============================================================================
# AccountService.ensure_account() Tests
# =============================================================================

class TestAccountServiceEnsureGolden:
    """Golden: AccountService.ensure_account() current behavior"""

    async def test_ensure_creates_new_account_and_returns_profile(self, mock_repo, mock_event_bus):
        """GOLDEN: ensure_account creates account and returns AccountProfileResponse"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountEnsureRequest, AccountProfileResponse

        service = AccountService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = AccountEnsureRequest(
            user_id="usr_new_123",
            email="new@example.com",
            name="New User"
        )

        result, was_created = await service.ensure_account(request)

        assert isinstance(result, AccountProfileResponse)
        assert result.user_id == "usr_new_123"
        assert result.email == "new@example.com"
        assert result.name == "New User"
        assert result.is_active is True

        # Verify repository was called
        mock_repo.assert_called("ensure_account_exists")
        mock_repo.assert_called_with(
            "ensure_account_exists",
            user_id="usr_new_123",
            email="new@example.com",
            name="New User"
        )

    async def test_ensure_returns_existing_account(self, mock_repo_with_user, mock_event_bus):
        """GOLDEN: ensure_account returns existing account without creating"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountEnsureRequest

        service = AccountService(
            repository=mock_repo_with_user,
            event_bus=mock_event_bus
        )
        request = AccountEnsureRequest(
            user_id="usr_test_123",
            email="test@example.com",
            name="Test User"
        )

        result, was_created = await service.ensure_account(request)

        assert result.user_id == "usr_test_123"
        # was_created is False for existing accounts (created > 60s ago)
        assert was_created is False

    async def test_ensure_validates_empty_user_id(self, mock_repo):
        """GOLDEN: ensure_account rejects empty user_id"""
        from microservices.account_service.account_service import AccountService, AccountValidationError

        service = AccountService(repository=mock_repo)

        # Use MagicMock to bypass Pydantic validation
        request = MagicMock()
        request.user_id = ""
        request.email = "test@example.com"
        request.name = "Test"

        with pytest.raises(AccountValidationError) as exc_info:
            await service.ensure_account(request)

        assert "user_id" in str(exc_info.value).lower()

    async def test_ensure_validates_invalid_email(self, mock_repo):
        """GOLDEN: ensure_account rejects invalid email format"""
        from microservices.account_service.account_service import AccountService, AccountValidationError

        service = AccountService(repository=mock_repo)

        request = MagicMock()
        request.user_id = "usr_123"
        request.email = "invalid-email"
        request.name = "Test"

        with pytest.raises(AccountValidationError) as exc_info:
            await service.ensure_account(request)

        assert "email" in str(exc_info.value).lower()

    async def test_ensure_validates_empty_name(self, mock_repo):
        """GOLDEN: ensure_account rejects empty name"""
        from microservices.account_service.account_service import AccountService, AccountValidationError

        service = AccountService(repository=mock_repo)

        request = MagicMock()
        request.user_id = "usr_123"
        request.email = "test@example.com"
        request.name = ""

        with pytest.raises(AccountValidationError) as exc_info:
            await service.ensure_account(request)

        assert "name" in str(exc_info.value).lower()

    async def test_ensure_handles_duplicate_email(self, mock_repo):
        """GOLDEN: ensure_account handles duplicate email"""
        from microservices.account_service.account_service import AccountService, AccountValidationError
        from microservices.account_service.models import AccountEnsureRequest
        from microservices.account_service.protocols import DuplicateEntryError

        # Add existing user with email
        mock_repo.set_user(
            user_id="usr_existing",
            email="taken@example.com",
            name="Existing"
        )

        service = AccountService(repository=mock_repo)
        request = AccountEnsureRequest(
            user_id="usr_new",
            email="taken@example.com",
            name="New User"
        )

        with pytest.raises(AccountValidationError) as exc_info:
            await service.ensure_account(request)

        assert "email" in str(exc_info.value).lower()


# =============================================================================
# AccountService.get_account_profile() Tests
# =============================================================================

class TestAccountServiceGetProfileGolden:
    """Golden: AccountService.get_account_profile() current behavior"""

    async def test_get_profile_returns_account(self, mock_repo_with_user):
        """GOLDEN: get_account_profile returns AccountProfileResponse"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountProfileResponse

        service = AccountService(repository=mock_repo_with_user)
        result = await service.get_account_profile("usr_test_123")

        assert isinstance(result, AccountProfileResponse)
        assert result.user_id == "usr_test_123"
        assert result.email == "test@example.com"
        assert result.preferences == {"theme": "dark"}

    async def test_get_profile_raises_not_found(self, mock_repo):
        """GOLDEN: get_account_profile raises AccountNotFoundError when not found"""
        from microservices.account_service.account_service import AccountService, AccountNotFoundError

        service = AccountService(repository=mock_repo)

        with pytest.raises(AccountNotFoundError):
            await service.get_account_profile("usr_nonexistent")

    async def test_get_profile_excludes_inactive(self, mock_repo):
        """GOLDEN: get_account_profile doesn't return inactive accounts"""
        from microservices.account_service.account_service import AccountService, AccountNotFoundError

        mock_repo.set_user(
            user_id="usr_inactive",
            email="inactive@example.com",
            name="Inactive User",
            is_active=False
        )

        service = AccountService(repository=mock_repo)

        with pytest.raises(AccountNotFoundError):
            await service.get_account_profile("usr_inactive")


# =============================================================================
# AccountService.update_account_profile() Tests
# =============================================================================

class TestAccountServiceUpdateProfileGolden:
    """Golden: AccountService.update_account_profile() current behavior"""

    async def test_update_profile_returns_updated_profile(self, mock_repo_with_user, mock_event_bus):
        """GOLDEN: update_account_profile returns updated AccountProfileResponse"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountUpdateRequest, AccountProfileResponse

        service = AccountService(
            repository=mock_repo_with_user,
            event_bus=mock_event_bus
        )
        request = AccountUpdateRequest(name="Updated Name")
        result = await service.update_account_profile("usr_test_123", request)

        assert isinstance(result, AccountProfileResponse)
        assert result.name == "Updated Name"

        # Verify repository was called
        mock_repo_with_user.assert_called("update_account_profile")

    async def test_update_profile_raises_not_found(self, mock_repo):
        """GOLDEN: update_account_profile raises AccountNotFoundError"""
        from microservices.account_service.account_service import AccountService, AccountNotFoundError
        from microservices.account_service.models import AccountUpdateRequest

        service = AccountService(repository=mock_repo)

        with pytest.raises(AccountNotFoundError):
            request = AccountUpdateRequest(name="New Name")
            await service.update_account_profile("usr_nonexistent", request)

    async def test_update_empty_request_returns_current_profile(self, mock_repo_with_user):
        """GOLDEN: Empty update request returns current profile"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountUpdateRequest

        service = AccountService(repository=mock_repo_with_user)
        request = AccountUpdateRequest()  # No fields to update
        result = await service.update_account_profile("usr_test_123", request)

        # Should return current profile without updating
        assert result.name == "Test User"

    async def test_update_validates_empty_name(self, mock_repo_with_user):
        """GOLDEN: update_account_profile rejects empty name"""
        from microservices.account_service.account_service import AccountService, AccountValidationError

        service = AccountService(repository=mock_repo_with_user)

        request = MagicMock()
        request.name = "   "  # Whitespace only
        request.email = None
        request.preferences = None

        with pytest.raises(AccountValidationError) as exc_info:
            await service.update_account_profile("usr_test_123", request)

        assert "name" in str(exc_info.value).lower()


# =============================================================================
# AccountService.update_account_preferences() Tests
# =============================================================================

class TestAccountServicePreferencesGolden:
    """Golden: AccountService.update_account_preferences() current behavior"""

    async def test_update_preferences_returns_true(self, mock_repo_with_user):
        """GOLDEN: update_account_preferences returns True on success"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountPreferencesRequest

        service = AccountService(repository=mock_repo_with_user)
        request = AccountPreferencesRequest(theme="light", language="en")
        result = await service.update_account_preferences("usr_test_123", request)

        assert result is True
        mock_repo_with_user.assert_called("update_account_preferences")

    async def test_update_preferences_empty_returns_true(self, mock_repo_with_user):
        """GOLDEN: Empty preferences update returns True"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountPreferencesRequest

        service = AccountService(repository=mock_repo_with_user)
        request = AccountPreferencesRequest()  # No preferences to update
        result = await service.update_account_preferences("usr_test_123", request)

        assert result is True


# =============================================================================
# AccountService.delete_account() Tests
# =============================================================================

class TestAccountServiceDeleteGolden:
    """Golden: AccountService.delete_account() current behavior"""

    async def test_delete_account_returns_true(self, mock_repo_with_user, mock_event_bus):
        """GOLDEN: delete_account returns True on success"""
        from microservices.account_service.account_service import AccountService

        service = AccountService(
            repository=mock_repo_with_user,
            event_bus=mock_event_bus
        )
        result = await service.delete_account("usr_test_123", reason="User requested")

        assert result is True
        mock_repo_with_user.assert_called("delete_account")

    async def test_delete_nonexistent_returns_false(self, mock_repo, mock_event_bus):
        """GOLDEN: delete_account returns False for nonexistent account"""
        from microservices.account_service.account_service import AccountService

        service = AccountService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        result = await service.delete_account("usr_nonexistent")

        assert result is False


# =============================================================================
# AccountService.change_account_status() Tests
# =============================================================================

class TestAccountServiceStatusChangeGolden:
    """Golden: AccountService.change_account_status() current behavior"""

    async def test_deactivate_returns_true(self, mock_repo_with_user, mock_event_bus):
        """GOLDEN: change_account_status(is_active=False) returns True"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountStatusChangeRequest

        service = AccountService(
            repository=mock_repo_with_user,
            event_bus=mock_event_bus
        )
        request = AccountStatusChangeRequest(is_active=False, reason="Policy violation")
        result = await service.change_account_status("usr_test_123", request)

        assert result is True
        mock_repo_with_user.assert_called("deactivate_account")

    async def test_activate_returns_true(self, mock_repo, mock_event_bus):
        """GOLDEN: change_account_status(is_active=True) returns True"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountStatusChangeRequest

        # Add inactive user
        mock_repo.set_user(
            user_id="usr_inactive",
            email="inactive@example.com",
            name="Inactive",
            is_active=False
        )

        service = AccountService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = AccountStatusChangeRequest(is_active=True, reason="Reactivation")
        result = await service.change_account_status("usr_inactive", request)

        assert result is True
        mock_repo.assert_called("activate_account")


# =============================================================================
# AccountService.list_accounts() Tests
# =============================================================================

class TestAccountServiceListGolden:
    """Golden: AccountService.list_accounts() current behavior"""

    async def test_list_accounts_returns_response(self, mock_repo):
        """GOLDEN: list_accounts returns AccountSearchResponse"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountListParams, AccountSearchResponse

        # Add some users
        mock_repo.set_user(user_id="usr_1", email="a@test.com", name="User A")
        mock_repo.set_user(user_id="usr_2", email="b@test.com", name="User B")

        service = AccountService(repository=mock_repo)
        params = AccountListParams(page=1, page_size=10)
        result = await service.list_accounts(params)

        assert isinstance(result, AccountSearchResponse)
        assert len(result.accounts) == 2
        assert result.page == 1
        assert result.page_size == 10

    async def test_list_accounts_empty(self, mock_repo):
        """GOLDEN: list_accounts returns empty list when no accounts"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountListParams

        service = AccountService(repository=mock_repo)
        params = AccountListParams()
        result = await service.list_accounts(params)

        assert len(result.accounts) == 0
        assert result.total_count == 0


# =============================================================================
# AccountService.search_accounts() Tests
# =============================================================================

class TestAccountServiceSearchGolden:
    """Golden: AccountService.search_accounts() current behavior"""

    async def test_search_accounts_returns_matches(self, mock_repo):
        """GOLDEN: search_accounts returns matching accounts"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountSearchParams

        mock_repo.set_user(user_id="usr_1", email="john@test.com", name="John Doe")
        mock_repo.set_user(user_id="usr_2", email="jane@test.com", name="Jane Doe")
        mock_repo.set_user(user_id="usr_3", email="bob@test.com", name="Bob Smith")

        service = AccountService(repository=mock_repo)
        params = AccountSearchParams(query="doe", limit=10)
        result = await service.search_accounts(params)

        assert len(result) == 2

    async def test_search_excludes_inactive_by_default(self, mock_repo):
        """GOLDEN: search_accounts excludes inactive by default"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountSearchParams

        mock_repo.set_user(user_id="usr_1", email="active@test.com", name="Active User")
        mock_repo.set_user(user_id="usr_2", email="inactive@test.com", name="Inactive User", is_active=False)

        service = AccountService(repository=mock_repo)
        params = AccountSearchParams(query="user", limit=10, include_inactive=False)
        result = await service.search_accounts(params)

        assert len(result) == 1
        assert result[0].user_id == "usr_1"


# =============================================================================
# AccountService.get_service_stats() Tests
# =============================================================================

class TestAccountServiceStatsGolden:
    """Golden: AccountService.get_service_stats() current behavior"""

    async def test_get_stats_returns_stats_response(self, mock_repo):
        """GOLDEN: get_service_stats returns AccountStatsResponse"""
        from microservices.account_service.account_service import AccountService
        from microservices.account_service.models import AccountStatsResponse

        mock_repo.set_stats(
            total_accounts=100,
            active_accounts=85,
            inactive_accounts=15,
            recent_registrations_7d=10,
            recent_registrations_30d=25
        )

        service = AccountService(repository=mock_repo)
        result = await service.get_service_stats()

        assert isinstance(result, AccountStatsResponse)
        assert result.total_accounts == 100
        assert result.active_accounts == 85
        assert result.inactive_accounts == 15


# =============================================================================
# AccountService.health_check() Tests
# =============================================================================

class TestAccountServiceHealthGolden:
    """Golden: AccountService.health_check() current behavior"""

    async def test_health_check_healthy(self, mock_repo):
        """GOLDEN: health_check returns healthy status"""
        from microservices.account_service.account_service import AccountService

        service = AccountService(repository=mock_repo)
        result = await service.health_check()

        assert result["status"] == "healthy"
        assert result["database"] == "connected"

    async def test_health_check_unhealthy_on_db_error(self, mock_repo):
        """GOLDEN: health_check returns unhealthy on database error"""
        from microservices.account_service.account_service import AccountService

        mock_repo.set_error(Exception("Database connection failed"))

        service = AccountService(repository=mock_repo)
        result = await service.health_check()

        assert result["status"] == "unhealthy"
        assert result["database"] == "disconnected"
