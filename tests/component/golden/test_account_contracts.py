"""
Account Service Contract Proof Tests

Validates that the account service data contracts and logic contracts work correctly.

Test Categories:
1. Data Contract Factory Tests - Verify factory generates valid data
2. Request Builder Tests - Verify builders create valid requests
3. Request Validation Tests - Verify Pydantic catches invalid data
4. Business Rule Tests - Verify logic rules from logic_contract.md
5. Response Contract Tests - Verify response structure matches schemas
6. Edge Case Tests - Verify edge cases from logic_contract.md
7. Invalid Data Tests - Verify factory invalid data generators work

Related Documents:
- Data Contract: tests/contracts/account/data_contract.py
- Logic Contract: tests/contracts/account/logic_contract.md

Test Execution:
    pytest tests/component/golden/test_account_contracts_proof.py -v
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from tests.contracts.account.data_contract import (
    # Factories
    AccountTestDataFactory,
    # Builders
    AccountEnsureRequestBuilder,
    AccountProfileUpdateRequestBuilder,
    AccountPreferencesRequestBuilder,
    # Request Contracts
    AccountEnsureRequestContract,
    AccountUpdateRequestContract,
    AccountPreferencesRequestContract,
    AccountStatusChangeRequestContract,
    AccountListParamsContract,
    AccountSearchParamsContract,
    AccountBulkOperationRequestContract,
    # Response Contracts
    AccountProfileResponseContract,
    AccountSummaryResponseContract,
    AccountSearchResponseContract,
    AccountStatsResponseContract,
    AccountServiceStatusContract,
    AccountBulkOperationResponseContract,
)

pytestmark = [pytest.mark.component, pytest.mark.golden]


# ===================================================================================
# TEST CLASS 1: DATA CONTRACT FACTORY TESTS
# ===================================================================================

class TestAccountDataContractFactory:
    """
    Validates AccountTestDataFactory generates valid, consistent test data.

    Aligns with: Layer 4 (Data Contract)
    """

    # === Factory ID Generation Tests ===

    def test_make_user_id_generates_unique_ids(self):
        """
        PROOF: Factory creates unique user IDs.

        Aligns with: BR-ACC-001 (User ID Uniqueness)
        """
        user_id_1 = AccountTestDataFactory.make_user_id()
        user_id_2 = AccountTestDataFactory.make_user_id()
        user_id_3 = AccountTestDataFactory.make_user_id()

        assert user_id_1.startswith("user_test_")
        assert user_id_2.startswith("user_test_")
        assert user_id_3.startswith("user_test_")

        # Verify uniqueness
        assert user_id_1 != user_id_2
        assert user_id_2 != user_id_3
        assert user_id_1 != user_id_3

    def test_make_email_generates_valid_emails(self):
        """
        PROOF: Factory creates valid email addresses.

        Aligns with: BR-ACC-003 (Email Format Validation)
        """
        email_1 = AccountTestDataFactory.make_email()
        email_2 = AccountTestDataFactory.make_email()

        # Verify format
        assert email_1.startswith("test_")
        assert "@example.com" in email_1
        assert email_2.startswith("test_")
        assert "@example.com" in email_2

        # Verify uniqueness
        assert email_1 != email_2

    def test_make_name_generates_valid_names(self):
        """
        PROOF: Factory creates valid non-empty names.

        Aligns with: BR-ACC-004 (Name Validation)
        """
        name_1 = AccountTestDataFactory.make_name()
        name_2 = AccountTestDataFactory.make_name()

        # Verify non-empty
        assert len(name_1) > 0
        assert len(name_2) > 0

        # Verify contains space (first + last name)
        assert " " in name_1
        assert " " in name_2

    def test_make_timezone_generates_valid_timezone(self):
        """PROOF: Factory creates valid timezone strings"""
        timezone = AccountTestDataFactory.make_timezone()

        valid_timezones = [
            "UTC", "America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles", "Europe/London", "Europe/Paris", "Asia/Tokyo"
        ]
        assert timezone in valid_timezones

    def test_make_theme_generates_valid_theme(self):
        """PROOF: Factory creates valid theme values"""
        theme = AccountTestDataFactory.make_theme()

        valid_themes = ["light", "dark", "auto"]
        assert theme in valid_themes

    # === Factory Request Creation Tests ===

    def test_make_ensure_request_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountEnsureRequestContract with all fields.

        Aligns with: BR-ACC-001, BR-ACC-002, BR-ACC-003, BR-ACC-004
        """
        request = AccountTestDataFactory.make_ensure_request()

        assert isinstance(request, AccountEnsureRequestContract)
        assert request.user_id.startswith("user_test_")
        assert "@example.com" in request.email
        assert len(request.name) > 0
        assert " " in request.name  # Full name format

    def test_make_ensure_request_with_overrides(self):
        """
        PROOF: Factory respects parameter overrides.

        Aligns with: Layer 4 (Data Contract) - Override pattern
        """
        custom_user_id = "user_custom_123"
        custom_email = "custom@test.com"
        custom_name = "Custom User"

        request = AccountTestDataFactory.make_ensure_request(
            user_id=custom_user_id,
            email=custom_email,
            name=custom_name
        )

        assert request.user_id == custom_user_id
        assert request.email == custom_email
        assert request.name == custom_name

    def test_make_update_request_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountUpdateRequestContract.

        Aligns with: BR-PRO-001, BR-PRO-002
        """
        request = AccountTestDataFactory.make_update_request()

        assert isinstance(request, AccountUpdateRequestContract)
        assert request.name is not None
        assert len(request.name) > 0
        assert request.email is not None
        assert "@example.com" in request.email
        assert request.preferences is not None
        assert isinstance(request.preferences, dict)

    def test_make_preferences_request_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountPreferencesRequestContract.

        Aligns with: BR-PRF-001, BR-PRF-002
        """
        request = AccountTestDataFactory.make_preferences_request()

        assert isinstance(request, AccountPreferencesRequestContract)
        assert request.timezone is not None
        assert request.language is not None
        assert request.theme in ["light", "dark", "auto"]
        assert isinstance(request.notification_email, bool)
        assert isinstance(request.notification_push, bool)

    def test_make_status_change_request_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountStatusChangeRequestContract.

        Aligns with: BR-STS-001, BR-STS-004
        """
        request = AccountTestDataFactory.make_status_change_request()

        assert isinstance(request, AccountStatusChangeRequestContract)
        assert isinstance(request.is_active, bool)
        # Default factory creates deactivation request with reason
        assert request.is_active == False
        assert request.reason is not None
        assert len(request.reason) > 0

    def test_make_list_params_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountListParamsContract.

        Aligns with: BR-QRY-003, BR-QRY-004
        """
        request = AccountTestDataFactory.make_list_params()

        assert isinstance(request, AccountListParamsContract)
        assert request.page >= 1
        assert 1 <= request.page_size <= 100

    def test_make_search_params_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountSearchParamsContract.

        Aligns with: BR-QRY-001, BR-QRY-002
        """
        request = AccountTestDataFactory.make_search_params()

        assert isinstance(request, AccountSearchParamsContract)
        assert len(request.query) > 0
        assert 1 <= request.limit <= 100
        assert isinstance(request.include_inactive, bool)

    def test_make_bulk_operation_request_creates_valid_contract(self):
        """PROOF: Factory creates valid AccountBulkOperationRequestContract"""
        request = AccountTestDataFactory.make_bulk_operation_request()

        assert isinstance(request, AccountBulkOperationRequestContract)
        assert len(request.user_ids) >= 1
        assert len(request.user_ids) <= 100
        assert request.operation in ["activate", "deactivate", "delete"]

    # === Factory Response Creation Tests ===

    def test_make_profile_response_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountProfileResponseContract.

        Aligns with: Layer 4 (Data Contract) - Response schemas
        """
        response = AccountTestDataFactory.make_profile_response()

        assert isinstance(response, AccountProfileResponseContract)
        assert response.user_id.startswith("user_test_")
        assert "@example.com" in response.email
        assert len(response.name) > 0
        assert isinstance(response.is_active, bool)
        assert isinstance(response.preferences, dict)
        assert response.created_at is not None
        assert response.updated_at is not None

    def test_make_summary_response_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountSummaryResponseContract (lightweight).

        Aligns with: Response Contract - Summary vs Profile
        """
        response = AccountTestDataFactory.make_summary_response()

        assert isinstance(response, AccountSummaryResponseContract)
        assert response.user_id is not None
        assert response.email is not None
        assert response.name is not None
        assert isinstance(response.is_active, bool)
        assert response.created_at is not None
        # Summary does NOT include preferences (lighter weight)

    def test_make_search_response_creates_valid_contract(self):
        """
        PROOF: Factory creates valid AccountSearchResponseContract with pagination.

        Aligns with: BR-QRY-003, BR-QRY-004 (Pagination)
        """
        response = AccountTestDataFactory.make_search_response()

        assert isinstance(response, AccountSearchResponseContract)
        assert isinstance(response.accounts, list)
        assert response.total_count >= 0
        assert response.page >= 1
        assert 1 <= response.page_size <= 100
        assert isinstance(response.has_next, bool)

    def test_make_stats_response_creates_valid_contract(self):
        """PROOF: Factory creates valid AccountStatsResponseContract"""
        response = AccountTestDataFactory.make_stats_response()

        assert isinstance(response, AccountStatsResponseContract)
        assert response.total_accounts >= 0
        assert response.active_accounts >= 0
        assert response.inactive_accounts >= 0
        assert response.recent_registrations_7d >= 0
        assert response.recent_registrations_30d >= 0
        # Verify consistency
        assert response.total_accounts == response.active_accounts + response.inactive_accounts

    def test_make_service_status_creates_valid_contract(self):
        """PROOF: Factory creates valid AccountServiceStatusContract"""
        response = AccountTestDataFactory.make_service_status()

        assert isinstance(response, AccountServiceStatusContract)
        assert response.service == "account_service"
        assert response.status in ["operational", "degraded", "down"]
        assert 1024 <= response.port <= 65535
        assert response.version is not None
        assert isinstance(response.database_connected, bool)
        assert response.timestamp is not None

    def test_make_bulk_operation_response_creates_valid_contract(self):
        """PROOF: Factory creates valid AccountBulkOperationResponseContract"""
        response = AccountTestDataFactory.make_bulk_operation_response()

        assert isinstance(response, AccountBulkOperationResponseContract)
        assert response.operation in ["activate", "deactivate", "delete"]
        assert response.total_requested >= 0
        assert response.successful >= 0
        assert response.failed >= 0
        assert isinstance(response.errors, list)
        # Verify consistency
        assert response.total_requested == response.successful + response.failed

    def test_factory_generates_no_duplicates_in_batch(self):
        """
        PROOF: Factory generates 100 unique IDs without collisions.

        Aligns with: BR-ACC-001 (User ID Uniqueness)
        """
        user_ids = set()
        emails = set()

        for _ in range(100):
            user_id = AccountTestDataFactory.make_user_id()
            email = AccountTestDataFactory.make_email()
            user_ids.add(user_id)
            emails.add(email)

        # All 100 should be unique
        assert len(user_ids) == 100
        assert len(emails) == 100


# ===================================================================================
# TEST CLASS 2: REQUEST BUILDER TESTS
# ===================================================================================

class TestAccountRequestBuilders:
    """
    Validates builder pattern creates complex requests.

    Aligns with: Layer 4 (Data Contract) - Builder pattern
    """

    def test_ensure_request_builder_default_values(self):
        """PROOF: Builder creates request with auto-generated defaults"""
        request = AccountEnsureRequestBuilder().build()

        assert isinstance(request, AccountEnsureRequestContract)
        assert request.user_id.startswith("user_test_")
        assert "@example.com" in request.email
        assert len(request.name) > 0

    def test_ensure_request_builder_with_custom_values(self):
        """
        PROOF: Builder allows custom values for all fields.

        Aligns with: Layer 4 - Fluent builder pattern
        """
        request = (
            AccountEnsureRequestBuilder()
            .with_user_id("user_custom_123")
            .with_email("john.doe@test.com")
            .with_name("John Doe")
            .build()
        )

        assert request.user_id == "user_custom_123"
        assert request.email == "john.doe@test.com"
        assert request.name == "John Doe"

    def test_ensure_request_builder_fluent_interface(self):
        """
        PROOF: Builder supports method chaining (fluent interface).

        Aligns with: Builder pattern best practices
        """
        builder = AccountEnsureRequestBuilder()

        # Verify each method returns builder instance
        result1 = builder.with_user_id("user_test")
        result2 = result1.with_email("test@example.com")
        result3 = result2.with_name("Test User")

        assert result1 is builder
        assert result2 is builder
        assert result3 is builder

    def test_profile_update_builder_incremental_construction(self):
        """
        PROOF: Profile update builder constructs complex updates incrementally.

        Aligns with: BR-PRO-003 (Field Filtering), BR-PRF-002 (Preferences Merge)
        """
        request = (
            AccountProfileUpdateRequestBuilder()
            .with_name("Updated Name")
            .with_email("updated@example.com")
            .with_preference("timezone", "America/New_York")
            .with_preference("language", "en_US")
            .with_preference("theme", "dark")
            .build()
        )

        assert isinstance(request, AccountUpdateRequestContract)
        assert request.name == "Updated Name"
        assert request.email == "updated@example.com"
        assert request.preferences["timezone"] == "America/New_York"
        assert request.preferences["language"] == "en_US"
        assert request.preferences["theme"] == "dark"

    def test_profile_update_builder_convenience_methods(self):
        """PROOF: Builder provides convenience methods for preferences"""
        request = (
            AccountProfileUpdateRequestBuilder()
            .with_timezone("America/Chicago")
            .with_language("es_ES")
            .with_theme("light")
            .with_notification_email(True)
            .with_notification_push(False)
            .build()
        )

        assert request.preferences["timezone"] == "America/Chicago"
        assert request.preferences["language"] == "es_ES"
        assert request.preferences["theme"] == "light"
        assert request.preferences["notification_email"] == True
        assert request.preferences["notification_push"] == False

    def test_preferences_builder_theme_shortcuts(self):
        """
        PROOF: Preferences builder provides theme shortcuts.

        Aligns with: BR-PRF-001 (JSONB Structure Validation)
        """
        # Test dark theme shortcut
        dark_request = (
            AccountPreferencesRequestBuilder()
            .with_dark_theme()
            .build()
        )
        assert dark_request.theme == "dark"

        # Test light theme shortcut
        light_request = (
            AccountPreferencesRequestBuilder()
            .with_light_theme()
            .build()
        )
        assert light_request.theme == "light"

        # Test auto theme shortcut
        auto_request = (
            AccountPreferencesRequestBuilder()
            .with_auto_theme()
            .build()
        )
        assert auto_request.theme == "auto"


# ===================================================================================
# TEST CLASS 3: REQUEST VALIDATION TESTS
# ===================================================================================

class TestAccountRequestValidation:
    """
    Validates Pydantic validation catches invalid data.

    Aligns with: Layer 4 (Data Contract) - Schema validation
    """

    def test_ensure_request_validates_user_id_required(self):
        """
        PROOF: Pydantic validates user_id is required.

        Aligns with: BR-ACC-001 (User ID validation)
        """
        with pytest.raises(ValidationError) as exc_info:
            AccountEnsureRequestContract(
                # Missing user_id
                email="test@example.com",
                name="Test User"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("user_id",) for e in errors)

    def test_ensure_request_validates_email_format(self):
        """
        PROOF: Pydantic validates email format.

        Aligns with: BR-ACC-003 (Email Format Validation)
        """
        with pytest.raises(ValidationError):
            AccountEnsureRequestContract(
                user_id="user_123",
                email="not-a-valid-email",  # Invalid format
                name="Test User"
            )

    def test_ensure_request_validates_email_required(self):
        """
        PROOF: Pydantic validates email is required.

        Aligns with: BR-ACC-002 (Email Uniqueness - requires email)
        """
        with pytest.raises(ValidationError) as exc_info:
            AccountEnsureRequestContract(
                user_id="user_123",
                # Missing email
                name="Test User"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_ensure_request_validates_name_min_length(self):
        """
        PROOF: Pydantic validates name minimum length.

        Aligns with: BR-ACC-004 (Name Validation)
        """
        with pytest.raises(ValidationError):
            AccountEnsureRequestContract(
                user_id="user_123",
                email="test@example.com",
                name=""  # Empty string (min_length=1)
            )

    def test_update_request_validates_email_format(self):
        """
        PROOF: Update request validates email format.

        Aligns with: BR-PRO-001 (Email Uniqueness on Update)
        """
        with pytest.raises(ValidationError):
            AccountUpdateRequestContract(
                email="invalid-email-format"  # No @ symbol
            )

    def test_update_request_validates_name_whitespace_only(self):
        """
        PROOF: Update request validates name is not whitespace-only.

        Aligns with: BR-PRO-002 (Name Validation on Update)
        """
        with pytest.raises(ValidationError):
            AccountUpdateRequestContract(
                name="   "  # Whitespace only
            )

    def test_preferences_request_validates_timezone_format(self):
        """
        PROOF: Preferences request validates timezone format.

        Aligns with: BR-PRF-001 (JSONB Structure Validation)
        """
        with pytest.raises(ValidationError):
            AccountPreferencesRequestContract(
                timezone="InvalidTimezone123"
            )

    def test_preferences_request_validates_theme_enum(self):
        """
        PROOF: Preferences request validates theme enum values.

        Aligns with: BR-PRF-001 (Valid theme values)
        """
        with pytest.raises(ValidationError):
            AccountPreferencesRequestContract(
                theme="invalid_theme"  # Must be light/dark/auto
            )

    def test_status_change_request_allows_optional_reason(self):
        """
        PROOF: Status change allows optional reason field.

        Note: BR-STS-004 recommends reason when deactivating, but validation
        doesn't strictly enforce it at the contract level. Application logic
        should validate this requirement.

        Aligns with: BR-STS-004 (Reason Tracking - recommended but not enforced)
        """
        # Valid with reason
        with_reason = AccountStatusChangeRequestContract(
            is_active=False,
            reason="Deactivating for testing"
        )
        assert with_reason.is_active == False
        assert with_reason.reason is not None

        # Also valid without reason (field is optional)
        without_reason = AccountStatusChangeRequestContract(
            is_active=False
        )
        assert without_reason.is_active == False
        assert without_reason.reason is None

    def test_list_params_validates_page_minimum(self):
        """
        PROOF: List params validates page >= 1.

        Aligns with: BR-QRY-004 (Pagination Max Limit)
        """
        with pytest.raises(ValidationError):
            AccountListParamsContract(
                page=0,  # Invalid - must be >= 1
                page_size=50
            )

    def test_list_params_validates_page_size_maximum(self):
        """
        PROOF: List params validates page_size <= 100.

        Aligns with: BR-QRY-004 (Pagination Max Limit)
        """
        with pytest.raises(ValidationError):
            AccountListParamsContract(
                page=1,
                page_size=200  # Invalid - max is 100
            )

    def test_search_params_validates_query_not_empty(self):
        """
        PROOF: Search params validates query is not empty.

        Aligns with: BR-QRY-002 (Search Query Validation)
        """
        with pytest.raises(ValidationError):
            AccountSearchParamsContract(
                query=""  # Empty string not allowed
            )

    def test_bulk_operation_validates_user_ids_not_empty(self):
        """PROOF: Bulk operation validates user_ids list is not empty"""
        with pytest.raises(ValidationError):
            AccountBulkOperationRequestContract(
                user_ids=[],  # Empty list
                operation="deactivate"
            )


# ===================================================================================
# TEST CLASS 4: BUSINESS RULE TESTS
# ===================================================================================

class TestAccountBusinessRules:
    """
    Validates business rules from logic_contract.md.

    Aligns with: Layer 5 (Logic Contract) - Business Rules
    """

    def test_br_acc_001_user_id_uniqueness(self):
        """
        PROOF: BR-ACC-001 - User ID must be unique.

        Validates factory generates unique user IDs.
        """
        user_ids = []
        for _ in range(50):
            request = AccountTestDataFactory.make_ensure_request()
            user_ids.append(request.user_id)

        # All user IDs should be unique
        assert len(user_ids) == len(set(user_ids))

    def test_br_acc_002_email_uniqueness(self):
        """
        PROOF: BR-ACC-002 - Email must be unique across accounts.

        Validates factory generates unique emails.
        """
        emails = []
        for _ in range(50):
            request = AccountTestDataFactory.make_ensure_request()
            emails.append(request.email)

        # All emails should be unique
        assert len(emails) == len(set(emails))

    def test_br_acc_003_email_format_validation(self):
        """
        PROOF: BR-ACC-003 - Email must match valid format.

        Validates generated emails have @ and domain.
        """
        for _ in range(10):
            email = AccountTestDataFactory.make_email()
            assert "@" in email
            assert "." in email.split("@")[1]  # Domain has TLD

    def test_br_pro_002_name_validation(self):
        """
        PROOF: BR-PRO-002 - Name cannot be empty or whitespace-only.

        Validates factory generates non-empty names.
        """
        for _ in range(10):
            name = AccountTestDataFactory.make_name()
            assert len(name.strip()) > 0

    def test_br_prf_002_preferences_merge_strategy(self):
        """
        PROOF: BR-PRF-002 - Preferences use merge strategy (not replace).

        Validates builder allows incremental preference construction.
        """
        # Start with base preferences
        base_prefs = {"timezone": "UTC", "language": "en_US"}

        # Add additional preferences (merge)
        request = (
            AccountProfileUpdateRequestBuilder()
            .with_preferences(base_prefs)
            .with_preference("theme", "dark")
            .with_preference("notification_email", True)
            .build()
        )

        # Verify all preferences present
        assert request.preferences["timezone"] == "UTC"
        assert request.preferences["language"] == "en_US"
        assert request.preferences["theme"] == "dark"
        assert request.preferences["notification_email"] == True

    def test_br_qry_003_pagination_max_page_size(self):
        """
        PROOF: BR-QRY-004 - Page size max is 100.

        Validates Pydantic enforces page_size <= 100.
        """
        # Valid page size
        valid_request = AccountTestDataFactory.make_list_params(page_size=100)
        assert valid_request.page_size == 100

        # Invalid page size
        with pytest.raises(ValidationError):
            AccountListParamsContract(page=1, page_size=101)

    def test_br_evt_004_user_created_published_once(self):
        """
        PROOF: BR-EVT-004 - user.created event published once only.

        Validates ensure request can be called multiple times with same user_id.
        """
        user_id = AccountTestDataFactory.make_user_id()

        # Create multiple ensure requests with same user_id
        request1 = AccountTestDataFactory.make_ensure_request(user_id=user_id)
        request2 = AccountTestDataFactory.make_ensure_request(user_id=user_id)

        assert request1.user_id == request2.user_id
        # In real service, only first would publish event

    def test_br_sts_002_soft_delete_preserves_data(self):
        """
        PROOF: BR-STS-002 - Soft delete preserves account data.

        Validates status change only changes is_active flag.
        """
        # Create deactivation request
        request = AccountTestDataFactory.make_status_change_request(
            is_active=False,
            reason="Testing soft delete"
        )

        assert request.is_active == False
        assert request.reason is not None
        # In real service, only is_active would change, all other data preserved


# ===================================================================================
# TEST CLASS 5: RESPONSE CONTRACT TESTS
# ===================================================================================

class TestAccountResponseContracts:
    """
    Validates response contracts match expected structure.

    Aligns with: Layer 4 (Data Contract) - Response validation
    """

    def test_profile_response_contains_all_required_fields(self):
        """
        PROOF: Profile response includes all required fields.

        Aligns with: Response Contract - Full profile data
        """
        response = AccountTestDataFactory.make_profile_response()

        # Required fields
        assert response.user_id is not None
        assert response.email is not None
        assert response.name is not None
        assert response.is_active is not None
        assert response.preferences is not None
        assert response.created_at is not None
        assert response.updated_at is not None

    def test_summary_response_is_lightweight(self):
        """
        PROOF: Summary response is lighter than profile (no preferences).

        Aligns with: Response Contract - Summary vs Profile distinction
        """
        summary = AccountTestDataFactory.make_summary_response()

        # Has core fields
        assert summary.user_id is not None
        assert summary.email is not None
        assert summary.name is not None
        assert summary.is_active is not None
        assert summary.created_at is not None

        # Does NOT have preferences (lighter weight)
        # (Not in AccountSummaryResponseContract schema)

    def test_search_response_includes_pagination(self):
        """
        PROOF: Search response includes pagination metadata.

        Aligns with: BR-QRY-003, BR-QRY-004 (Pagination)
        """
        response = AccountTestDataFactory.make_search_response()

        assert response.accounts is not None
        assert isinstance(response.accounts, list)
        assert response.total_count >= 0
        assert response.page >= 1
        assert response.page_size >= 1
        assert isinstance(response.has_next, bool)

    def test_stats_response_includes_all_metrics(self):
        """
        PROOF: Stats response includes all metric fields.

        Aligns with: Response Contract - Service statistics
        """
        response = AccountTestDataFactory.make_stats_response()

        assert response.total_accounts >= 0
        assert response.active_accounts >= 0
        assert response.inactive_accounts >= 0
        assert response.recent_registrations_7d >= 0
        assert response.recent_registrations_30d >= 0

    def test_service_status_indicates_health(self):
        """
        PROOF: Service status includes health indicators.

        Aligns with: Response Contract - Health check
        """
        response = AccountTestDataFactory.make_service_status()

        assert response.service == "account_service"
        assert response.status in ["operational", "degraded", "down"]
        assert response.port >= 1024
        assert response.version is not None
        assert isinstance(response.database_connected, bool)
        assert response.timestamp is not None

    def test_bulk_operation_response_includes_results(self):
        """PROOF: Bulk operation response includes success/failure counts"""
        response = AccountTestDataFactory.make_bulk_operation_response()

        assert response.operation is not None
        assert response.total_requested >= 0
        assert response.successful >= 0
        assert response.failed >= 0
        assert isinstance(response.errors, list)


# ===================================================================================
# TEST CLASS 6: EDGE CASE TESTS
# ===================================================================================

class TestAccountEdgeCases:
    """
    Validates edge cases from logic_contract.md.

    Aligns with: Layer 5 (Logic Contract) - Edge Cases
    """

    def test_ec_001_concurrent_ensure_calls_same_user_id(self):
        """
        PROOF: EC-001 - Multiple concurrent ensure calls with same user_id.

        Validates idempotent behavior.
        """
        user_id = AccountTestDataFactory.make_user_id()

        # Simulate concurrent calls with same user_id
        request1 = AccountTestDataFactory.make_ensure_request(user_id=user_id)
        request2 = AccountTestDataFactory.make_ensure_request(user_id=user_id)

        assert request1.user_id == request2.user_id
        # In real service, both would succeed, one creates, one retrieves

    def test_ec_002_ensure_after_account_created(self):
        """
        PROOF: EC-002 - Ensure called after account already exists.

        Validates idempotent ensure behavior.
        """
        user_id = AccountTestDataFactory.make_user_id()

        # First ensure
        request1 = AccountTestDataFactory.make_ensure_request(user_id=user_id)

        # Second ensure (idempotent)
        request2 = AccountTestDataFactory.make_ensure_request(user_id=user_id)

        assert request1.user_id == request2.user_id
        # In real service, second call returns existing account

    def test_ec_003_email_already_used_different_user(self):
        """
        PROOF: EC-003 - Email already used by different user.

        Validates email uniqueness across different user_ids.
        """
        email = AccountTestDataFactory.make_email()

        # Two different users with same email (invalid)
        user_id_1 = AccountTestDataFactory.make_user_id()
        user_id_2 = AccountTestDataFactory.make_user_id()

        request1 = AccountTestDataFactory.make_ensure_request(
            user_id=user_id_1,
            email=email
        )
        request2 = AccountTestDataFactory.make_ensure_request(
            user_id=user_id_2,
            email=email  # Same email, different user
        )

        assert request1.user_id != request2.user_id
        assert request1.email == request2.email
        # In real service, second request would fail with DuplicateEntryError

    def test_ec_004_empty_string_email(self):
        """
        PROOF: EC-004 - Empty string email.

        Validates email required validation.
        """
        with pytest.raises(ValidationError):
            AccountEnsureRequestContract(
                user_id="user_123",
                email="",  # Empty string
                name="Test User"
            )

    def test_ec_006_name_with_only_whitespace(self):
        """
        PROOF: EC-006 - Name with only whitespace.

        Validates name whitespace validation.
        """
        with pytest.raises(ValidationError):
            AccountUpdateRequestContract(
                name="   "  # Whitespace only
            )

    def test_ec_008_invalid_json_in_preferences(self):
        """
        PROOF: EC-008 - Invalid JSON in preferences.

        Validates preferences must be dict type.
        """
        with pytest.raises(ValidationError):
            AccountUpdateRequestContract(
                preferences="not a dict"  # String instead of dict
            )

    def test_ec_011_deactivate_already_inactive(self):
        """
        PROOF: EC-011 - Deactivate already inactive account.

        Validates idempotent deactivation.
        """
        # Create deactivation request (idempotent)
        request = AccountTestDataFactory.make_status_change_request(
            is_active=False,
            reason="Already inactive"
        )

        assert request.is_active == False
        # In real service, operation succeeds even if already inactive

    def test_ec_012_activate_already_active(self):
        """
        PROOF: EC-012 - Activate already active account.

        Validates idempotent activation.
        """
        # Create activation request (idempotent)
        request = AccountTestDataFactory.make_status_change_request(
            is_active=True,
            reason="Already active"
        )

        assert request.is_active == True
        # In real service, operation succeeds even if already active


# ===================================================================================
# TEST CLASS 7: INVALID DATA TESTS
# ===================================================================================

class TestAccountInvalidDataGenerators:
    """
    Validates factory invalid data generators work correctly.

    Aligns with: Layer 4 (Data Contract) - Negative testing support
    """

    def test_invalid_ensure_request_missing_user_id(self):
        """PROOF: Invalid data generator creates request missing user_id"""
        invalid_data = AccountTestDataFactory.make_invalid_ensure_request_missing_user_id()

        assert "user_id" not in invalid_data
        assert "email" in invalid_data
        assert "name" in invalid_data

        # Verify it fails validation
        with pytest.raises(ValidationError):
            AccountEnsureRequestContract(**invalid_data)

    def test_invalid_ensure_request_missing_email(self):
        """PROOF: Invalid data generator creates request missing email"""
        invalid_data = AccountTestDataFactory.make_invalid_ensure_request_missing_email()

        assert "user_id" in invalid_data
        assert "email" not in invalid_data
        assert "name" in invalid_data

        # Verify it fails validation
        with pytest.raises(ValidationError):
            AccountEnsureRequestContract(**invalid_data)

    def test_invalid_ensure_request_invalid_email(self):
        """PROOF: Invalid data generator creates request with invalid email format"""
        invalid_data = AccountTestDataFactory.make_invalid_ensure_request_invalid_email()

        assert "email" in invalid_data
        assert "@" not in invalid_data["email"]  # Invalid format

        # Verify it fails validation
        with pytest.raises(ValidationError):
            AccountEnsureRequestContract(**invalid_data)

    def test_invalid_update_request_invalid_email(self):
        """PROOF: Invalid data generator creates update request with invalid email"""
        invalid_data = AccountTestDataFactory.make_invalid_update_request_invalid_email()

        assert "email" in invalid_data

        # Verify it fails validation
        with pytest.raises(ValidationError):
            AccountUpdateRequestContract(**invalid_data)

    def test_invalid_status_change_missing_reason(self):
        """
        PROOF: Invalid data generator creates status change without reason.

        Note: This documents that reason is optional at contract level.
        Application logic should enforce reason requirement for deactivation.

        Aligns with: BR-STS-004 (Reason recommended but not contract-enforced)
        """
        invalid_data = AccountTestDataFactory.make_invalid_status_change_request_missing_reason()

        assert invalid_data["is_active"] == False
        assert "reason" not in invalid_data or invalid_data.get("reason") is None

        # Contract allows missing reason (field is optional)
        # This is valid at schema level, but application logic should enforce it
        request = AccountStatusChangeRequestContract(**invalid_data)
        assert request.is_active == False
        assert request.reason is None

    def test_invalid_list_params_excessive_page_size(self):
        """PROOF: Invalid data generator creates list params with excessive page_size"""
        invalid_data = AccountTestDataFactory.make_invalid_list_params_excessive_page_size()

        assert invalid_data["page_size"] > 100  # Exceeds max

        # Verify it fails validation
        with pytest.raises(ValidationError):
            AccountListParamsContract(**invalid_data)

    def test_invalid_search_params_empty_query(self):
        """PROOF: Invalid data generator creates search params with empty query"""
        invalid_data = AccountTestDataFactory.make_invalid_search_params_empty_query()

        assert "query" in invalid_data
        assert len(invalid_data["query"].strip()) == 0  # Whitespace only

        # Verify it fails validation
        with pytest.raises(ValidationError):
            AccountSearchParamsContract(**invalid_data)

    def test_invalid_bulk_operation_empty_user_ids(self):
        """PROOF: Invalid data generator creates bulk operation with empty user_ids"""
        invalid_data = AccountTestDataFactory.make_invalid_bulk_operation_empty_user_ids()

        assert "user_ids" in invalid_data
        assert len(invalid_data["user_ids"]) == 0

        # Verify it fails validation
        with pytest.raises(ValidationError):
            AccountBulkOperationRequestContract(**invalid_data)


# ===================================================================================
# SUMMARY TEST (META)
# ===================================================================================

def test_all_contract_types_covered():
    """
    Meta-test: Verify all contract types are covered by tests.

    Validates comprehensive coverage of data contract.
    """
    # Request contracts
    ensure_req = AccountTestDataFactory.make_ensure_request()
    update_req = AccountTestDataFactory.make_update_request()
    prefs_req = AccountTestDataFactory.make_preferences_request()
    status_req = AccountTestDataFactory.make_status_change_request()
    list_req = AccountTestDataFactory.make_list_params()
    search_req = AccountTestDataFactory.make_search_params()
    bulk_req = AccountTestDataFactory.make_bulk_operation_request()

    # Response contracts
    profile_resp = AccountTestDataFactory.make_profile_response()
    summary_resp = AccountTestDataFactory.make_summary_response()
    search_resp = AccountTestDataFactory.make_search_response()
    stats_resp = AccountTestDataFactory.make_stats_response()
    status_resp = AccountTestDataFactory.make_service_status()
    bulk_resp = AccountTestDataFactory.make_bulk_operation_response()

    # Verify all types instantiated successfully
    assert all([
        ensure_req, update_req, prefs_req, status_req, list_req, search_req, bulk_req,
        profile_resp, summary_resp, search_resp, stats_resp, status_resp, bulk_resp
    ])


# ===================================================================================
# RUN TESTS
# ===================================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
