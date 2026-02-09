"""
Account Models Golden Tests

🔒 GOLDEN: These tests document the CURRENT behavior of account models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what the code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden -v
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

# Import models that don't have I/O dependencies
from microservices.account_service.models import (
    User,
    AccountEnsureRequest,
    AccountUpdateRequest,
    AccountPreferencesRequest,
    AccountStatusChangeRequest,
    AccountProfileResponse,
    AccountSummaryResponse,
    AccountSearchResponse,
    AccountStatsResponse,
    AccountListParams,
    AccountSearchParams,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# AccountEnsureRequest - Current Behavior
# =============================================================================

class TestAccountEnsureRequestChar:
    """Characterization: AccountEnsureRequest current behavior"""

    def test_accepts_valid_data(self):
        """CHAR: Valid request is accepted"""
        req = AccountEnsureRequest(
            user_id="usr_123",
            email="test@example.com",
            name="Test User"
        )
        assert req.user_id == "usr_123"

    def test_requires_user_id(self):
        """CHAR: user_id is required"""
        with pytest.raises(ValidationError):
            AccountEnsureRequest(email="test@example.com", name="Test")

    def test_requires_valid_email(self):
        """CHAR: email must be valid format"""
        with pytest.raises(ValidationError):
            AccountEnsureRequest(user_id="usr_123", email="invalid", name="Test")

    def test_requires_name(self):
        """CHAR: name is required"""
        with pytest.raises(ValidationError):
            AccountEnsureRequest(user_id="usr_123", email="test@example.com")


# =============================================================================
# AccountUpdateRequest - Current Behavior
# =============================================================================

class TestAccountUpdateRequestChar:
    """Characterization: AccountUpdateRequest current behavior"""

    def test_all_fields_optional(self):
        """CHAR: All fields are optional"""
        req = AccountUpdateRequest()
        assert req.name is None
        assert req.email is None
        assert req.preferences is None

    def test_name_max_length_100(self):
        """CHAR: Name max length is 100"""
        with pytest.raises(ValidationError):
            AccountUpdateRequest(name="x" * 101)

    def test_accepts_preferences_dict(self):
        """CHAR: Preferences accepts dict"""
        req = AccountUpdateRequest(preferences={"theme": "dark"})
        assert req.preferences["theme"] == "dark"


# =============================================================================
# AccountPreferencesRequest - Current Behavior
# =============================================================================

class TestAccountPreferencesRequestChar:
    """Characterization: AccountPreferencesRequest current behavior"""

    def test_theme_valid_values(self):
        """CHAR: Theme accepts light, dark, auto"""
        for theme in ["light", "dark", "auto"]:
            req = AccountPreferencesRequest(theme=theme)
            assert req.theme == theme

    def test_theme_rejects_invalid(self):
        """CHAR: Theme rejects invalid values"""
        with pytest.raises(ValidationError):
            AccountPreferencesRequest(theme="blue")

    def test_language_max_5_chars(self):
        """CHAR: Language max 5 characters"""
        req = AccountPreferencesRequest(language="zh-CN")
        assert req.language == "zh-CN"

        with pytest.raises(ValidationError):
            AccountPreferencesRequest(language="toolong")


# =============================================================================
# AccountStatusChangeRequest - Current Behavior
# =============================================================================

class TestAccountStatusChangeRequestChar:
    """Characterization: AccountStatusChangeRequest current behavior"""

    def test_is_active_required(self):
        """CHAR: is_active is required"""
        with pytest.raises(ValidationError):
            AccountStatusChangeRequest()

    def test_reason_optional(self):
        """CHAR: reason is optional"""
        req = AccountStatusChangeRequest(is_active=False)
        assert req.reason is None

    def test_reason_max_255(self):
        """CHAR: reason max 255 characters"""
        with pytest.raises(ValidationError):
            AccountStatusChangeRequest(is_active=False, reason="x" * 256)


# =============================================================================
# User Model - Current Behavior
# =============================================================================

class TestUserModelChar:
    """Characterization: User model current behavior"""

    def test_preferences_parses_json_string(self):
        """CHAR: preferences parses JSON string"""
        user = User(user_id="usr_123", preferences='{"theme": "dark"}')
        assert user.preferences["theme"] == "dark"

    def test_preferences_accepts_dict(self):
        """CHAR: preferences accepts dict directly"""
        user = User(user_id="usr_123", preferences={"lang": "en"})
        assert user.preferences["lang"] == "en"

    def test_preferences_defaults_empty(self):
        """CHAR: preferences defaults to empty dict"""
        user = User(user_id="usr_123")
        assert user.preferences == {}

    def test_invalid_json_becomes_empty(self):
        """CHAR: invalid JSON preferences becomes empty dict"""
        user = User(user_id="usr_123", preferences="not json")
        assert user.preferences == {}

    def test_is_active_defaults_true(self):
        """CHAR: is_active defaults to True"""
        user = User(user_id="usr_123")
        assert user.is_active is True


# =============================================================================
# Pagination Models - Current Behavior
# =============================================================================

class TestAccountListParamsChar:
    """Characterization: AccountListParams current behavior"""

    def test_defaults(self):
        """CHAR: Default values"""
        params = AccountListParams()
        assert params.page == 1
        assert params.page_size == 50

    def test_page_min_1(self):
        """CHAR: page minimum is 1"""
        with pytest.raises(ValidationError):
            AccountListParams(page=0)

    def test_page_size_range_1_100(self):
        """CHAR: page_size range is 1-100"""
        with pytest.raises(ValidationError):
            AccountListParams(page_size=0)
        with pytest.raises(ValidationError):
            AccountListParams(page_size=101)


class TestAccountSearchParamsChar:
    """Characterization: AccountSearchParams current behavior"""

    def test_query_required(self):
        """CHAR: query is required"""
        with pytest.raises(ValidationError):
            AccountSearchParams()

    def test_limit_default_50(self):
        """CHAR: limit defaults to 50"""
        params = AccountSearchParams(query="test")
        assert params.limit == 50

    def test_include_inactive_default_false(self):
        """CHAR: include_inactive defaults to False"""
        params = AccountSearchParams(query="test")
        assert params.include_inactive is False
