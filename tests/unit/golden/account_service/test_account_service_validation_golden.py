"""
Account Service Validation Logic Golden Tests

Tests the pure validation methods in AccountService.
These are synchronous methods that don't require mocks.

Usage:
    pytest tests/unit/golden/test_account_service_validation_golden.py -v
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

pytestmark = [pytest.mark.unit, pytest.mark.golden]


class TestValidateAccountEnsureRequest:
    """
    Golden: AccountService._validate_account_ensure_request()
    """

    def _create_service(self):
        """Create service without repository for validation-only tests"""
        from microservices.account_service.account_service import AccountService
        return AccountService(repository=MagicMock())

    def _create_request(self, user_id="usr_123", email="test@example.com", name="Test"):
        """Create AccountEnsureRequest"""
        from microservices.account_service.models import AccountEnsureRequest
        return AccountEnsureRequest(user_id=user_id, email=email, name=name)

    def test_valid_request_passes(self):
        """GOLDEN: Valid request passes validation"""
        from microservices.account_service.account_service import AccountService

        service = self._create_service()
        request = self._create_request()

        # Should not raise
        service._validate_account_ensure_request(request)

    def test_empty_user_id_raises(self):
        """GOLDEN: Empty user_id raises AccountValidationError"""
        from microservices.account_service.account_service import (
            AccountService,
            AccountValidationError
        )
        from microservices.account_service.models import AccountEnsureRequest

        service = self._create_service()

        # Create request with empty user_id (bypass Pydantic if needed)
        request = MagicMock()
        request.user_id = ""
        request.email = "test@example.com"
        request.name = "Test"

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "user_id" in str(exc_info.value).lower()

    def test_whitespace_user_id_raises(self):
        """GOLDEN: Whitespace-only user_id raises AccountValidationError"""
        from microservices.account_service.account_service import (
            AccountService,
            AccountValidationError
        )

        service = self._create_service()

        request = MagicMock()
        request.user_id = "   "
        request.email = "test@example.com"
        request.name = "Test"

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "user_id" in str(exc_info.value).lower()

    def test_empty_email_raises(self):
        """GOLDEN: Empty email raises AccountValidationError"""
        from microservices.account_service.account_service import (
            AccountService,
            AccountValidationError
        )

        service = self._create_service()

        request = MagicMock()
        request.user_id = "usr_123"
        request.email = ""
        request.name = "Test"

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "email" in str(exc_info.value).lower()

    def test_invalid_email_format_raises(self):
        """GOLDEN: Invalid email format raises AccountValidationError"""
        from microservices.account_service.account_service import (
            AccountService,
            AccountValidationError
        )

        service = self._create_service()

        invalid_emails = [
            "notanemail",
            "missing@tld",
            "@nodomain.com",
            "spaces in@email.com",
        ]

        for email in invalid_emails:
            request = MagicMock()
            request.user_id = "usr_123"
            request.email = email
            request.name = "Test"

            with pytest.raises(AccountValidationError) as exc_info:
                service._validate_account_ensure_request(request)

            assert "email" in str(exc_info.value).lower()

    def test_empty_name_raises(self):
        """GOLDEN: Empty name raises AccountValidationError"""
        from microservices.account_service.account_service import (
            AccountService,
            AccountValidationError
        )

        service = self._create_service()

        request = MagicMock()
        request.user_id = "usr_123"
        request.email = "test@example.com"
        request.name = ""

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "name" in str(exc_info.value).lower()


class TestValidateAccountUpdateRequest:
    """
    Golden: AccountService._validate_account_update_request()
    """

    def _create_service(self):
        """Create service without repository for validation-only tests"""
        from microservices.account_service.account_service import AccountService
        return AccountService(repository=MagicMock())

    def test_empty_update_passes(self):
        """GOLDEN: Empty update request passes validation"""
        from microservices.account_service.models import AccountUpdateRequest

        service = self._create_service()
        request = AccountUpdateRequest()

        # Should not raise
        service._validate_account_update_request(request)

    def test_valid_name_update_passes(self):
        """GOLDEN: Valid name update passes"""
        from microservices.account_service.models import AccountUpdateRequest

        service = self._create_service()
        request = AccountUpdateRequest(name="New Name")

        service._validate_account_update_request(request)

    def test_empty_string_name_raises(self):
        """GOLDEN: Empty string name raises AccountValidationError"""
        from microservices.account_service.account_service import AccountValidationError

        service = self._create_service()

        request = MagicMock()
        request.name = "   "  # Whitespace only
        request.email = None
        request.preferences = None

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_update_request(request)

        assert "name" in str(exc_info.value).lower()

    def test_invalid_email_update_raises(self):
        """GOLDEN: Invalid email format raises AccountValidationError"""
        from microservices.account_service.account_service import AccountValidationError

        service = self._create_service()

        request = MagicMock()
        request.name = None
        request.email = "invalid-email"
        request.preferences = None

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_update_request(request)

        assert "email" in str(exc_info.value).lower()

    def test_valid_email_update_passes(self):
        """GOLDEN: Valid email update passes"""
        from microservices.account_service.models import AccountUpdateRequest

        service = self._create_service()
        request = AccountUpdateRequest(email="valid@example.com")

        service._validate_account_update_request(request)


class TestUserToProfileResponse:
    """
    Golden: AccountService._user_to_profile_response()
    """

    def _create_service(self):
        """Create service without repository"""
        from microservices.account_service.account_service import AccountService
        return AccountService(repository=MagicMock())

    def _create_user(
        self,
        user_id="usr_123",
        email="test@example.com",
        name="Test User",
        is_active=True,
        preferences=None,
        created_at="DEFAULT",
        updated_at=None
    ):
        """Create a User model"""
        from microservices.account_service.models import User
        # Use sentinel value to distinguish between None and not-provided
        actual_created_at = datetime(2024, 1, 1, tzinfo=timezone.utc) if created_at == "DEFAULT" else created_at
        return User(
            user_id=user_id,
            email=email,
            name=name,
            is_active=is_active,
            preferences=preferences or {},
            created_at=actual_created_at,
            updated_at=updated_at
        )

    def test_converts_all_fields(self):
        """GOLDEN: Converts all User fields to AccountProfileResponse"""
        from microservices.account_service.models import AccountProfileResponse

        service = self._create_service()
        user = self._create_user(
            user_id="usr_test",
            email="test@example.com",
            name="Test User",
            is_active=True,
            preferences={"theme": "dark"},
            created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
            updated_at=datetime(2024, 2, 1, tzinfo=timezone.utc)
        )

        result = service._user_to_profile_response(user)

        assert isinstance(result, AccountProfileResponse)
        assert result.user_id == "usr_test"
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        assert result.is_active is True
        assert result.preferences == {"theme": "dark"}
        assert result.created_at == datetime(2024, 1, 15, tzinfo=timezone.utc)
        assert result.updated_at == datetime(2024, 2, 1, tzinfo=timezone.utc)

    def test_handles_empty_preferences(self):
        """GOLDEN: Handles empty preferences"""
        service = self._create_service()
        user = self._create_user(preferences={})

        result = service._user_to_profile_response(user)

        assert result.preferences == {}

    def test_handles_none_timestamps(self):
        """GOLDEN: Handles None timestamps"""
        service = self._create_service()
        user = self._create_user(created_at=None, updated_at=None)

        result = service._user_to_profile_response(user)

        assert result.created_at is None
        assert result.updated_at is None


class TestUserToSummaryResponse:
    """
    Golden: AccountService._user_to_summary_response()
    """

    def _create_service(self):
        """Create service without repository"""
        from microservices.account_service.account_service import AccountService
        return AccountService(repository=MagicMock())

    def _create_user(
        self,
        user_id="usr_123",
        email="test@example.com",
        name="Test User",
        is_active=True,
        created_at=None
    ):
        """Create a User model"""
        from microservices.account_service.models import User
        return User(
            user_id=user_id,
            email=email,
            name=name,
            is_active=is_active,
            created_at=created_at or datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

    def test_converts_to_summary(self):
        """GOLDEN: Converts User to AccountSummaryResponse"""
        from microservices.account_service.models import AccountSummaryResponse

        service = self._create_service()
        user = self._create_user(
            user_id="usr_test",
            email="test@example.com",
            name="Test User",
            is_active=True,
            created_at=datetime(2024, 1, 15, tzinfo=timezone.utc)
        )

        result = service._user_to_summary_response(user)

        assert isinstance(result, AccountSummaryResponse)
        assert result.user_id == "usr_test"
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        assert result.is_active is True
        assert result.created_at == datetime(2024, 1, 15, tzinfo=timezone.utc)

    def test_excludes_preferences_and_updated_at(self):
        """GOLDEN: Summary excludes preferences and updated_at"""
        from microservices.account_service.models import AccountSummaryResponse

        service = self._create_service()
        user = self._create_user()

        result = service._user_to_summary_response(user)

        # Summary should not have these fields
        assert not hasattr(result, 'preferences') or 'preferences' not in result.model_fields
        assert not hasattr(result, 'updated_at') or 'updated_at' not in result.model_fields
