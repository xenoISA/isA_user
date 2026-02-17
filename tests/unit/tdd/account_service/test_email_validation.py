"""
Email Validation TDD Tests

RED: These tests define the CORRECT behavior for email validation.
Currently FAILING - need to fix implementation.

Issue Found: The email regex accepts emails with spaces like "spaces in@email.com"

Expected: All these invalid formats should be rejected
"""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.unit]


class TestEmailValidationTDD:
    """
    TDD RED: Email validation should reject invalid formats

    The current regex ``^[^@]+@[^@]+\\.[^@]+$`` has these issues:
    - Accepts emails with spaces
    - Accepts emails with other invalid characters
    """

    def _create_service(self):
        """Create AccountService with mock repository"""
        from microservices.account_service.account_service import AccountService
        return AccountService(repository=MagicMock())

    def _create_mock_request(self, email):
        """Create mock request with specified email"""
        request = MagicMock()
        request.user_id = "usr_123"
        request.email = email
        request.name = "Test User"
        return request

    def test_rejects_email_with_spaces(self):
        """RED: Should reject email with spaces"""
        from microservices.account_service.account_service import AccountValidationError

        service = self._create_service()
        request = self._create_mock_request("spaces in@email.com")

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "email" in str(exc_info.value).lower()

    def test_rejects_email_with_leading_space(self):
        """RED: Should reject email with leading space"""
        from microservices.account_service.account_service import AccountValidationError

        service = self._create_service()
        request = self._create_mock_request(" leading@email.com")

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "email" in str(exc_info.value).lower()

    def test_rejects_email_with_trailing_space(self):
        """RED: Should reject email with trailing space"""
        from microservices.account_service.account_service import AccountValidationError

        service = self._create_service()
        request = self._create_mock_request("trailing@email.com ")

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "email" in str(exc_info.value).lower()

    def test_rejects_email_with_tab(self):
        """RED: Should reject email with tab character"""
        from microservices.account_service.account_service import AccountValidationError

        service = self._create_service()
        request = self._create_mock_request("has\ttab@email.com")

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "email" in str(exc_info.value).lower()

    def test_rejects_email_with_newline(self):
        """RED: Should reject email with newline"""
        from microservices.account_service.account_service import AccountValidationError

        service = self._create_service()
        request = self._create_mock_request("has\nnewline@email.com")

        with pytest.raises(AccountValidationError) as exc_info:
            service._validate_account_ensure_request(request)

        assert "email" in str(exc_info.value).lower()

    # Valid emails should still pass
    def test_accepts_valid_simple_email(self):
        """GREEN: Should accept valid simple email"""
        service = self._create_service()
        request = self._create_mock_request("user@example.com")

        # Should not raise
        service._validate_account_ensure_request(request)

    def test_accepts_valid_email_with_plus(self):
        """GREEN: Should accept email with + tag"""
        service = self._create_service()
        request = self._create_mock_request("user+tag@example.com")

        service._validate_account_ensure_request(request)

    def test_accepts_valid_email_with_dots(self):
        """GREEN: Should accept email with dots in local part"""
        service = self._create_service()
        request = self._create_mock_request("first.last@example.com")

        service._validate_account_ensure_request(request)

    def test_accepts_valid_email_with_subdomain(self):
        """GREEN: Should accept email with subdomain"""
        service = self._create_service()
        request = self._create_mock_request("user@mail.example.com")

        service._validate_account_ensure_request(request)
