"""
Account Service Data Contract

Defines canonical data structures for account service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for account service test data.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator

# Import from production models for type consistency
from microservices.account_service.models import (
    User,
)


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class AccountEnsureRequestContract(BaseModel):
    """
    Contract: Account ensure request schema

    Used for creating/ensuring account existence in tests.
    Maps to account service ensure endpoint.
    """
    user_id: str = Field(..., min_length=1, description="User ID (from auth service)")
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=100, description="User display name")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123def456",
                "email": "john.doe@example.com",
                "name": "John Doe",
            }
        }


class AccountUpdateRequestContract(BaseModel):
    """
    Contract: Account profile update request schema

    Used for updating user profile information in tests.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="User display name")
    email: Optional[EmailStr] = Field(None, description="User email address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences (JSON)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Updated Doe",
                "email": "john.updated@example.com",
                "preferences": {
                    "timezone": "America/New_York",
                    "language": "en_US",
                    "theme": "dark"
                },
            }
        }


class AccountPreferencesRequestContract(BaseModel):
    """
    Contract: Account preferences update request schema

    Used for updating user preferences in tests.
    """
    timezone: Optional[str] = Field(None, description="User timezone (IANA format)")
    language: Optional[str] = Field(None, max_length=5, description="Preferred language (e.g., en_US)")
    notification_email: Optional[bool] = Field(None, description="Email notifications enabled")
    notification_push: Optional[bool] = Field(None, description="Push notifications enabled")
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$", description="UI theme preference")

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v):
        if v is not None:
            # Common timezone validation
            valid_timezones = [
                "UTC", "America/New_York", "America/Chicago", "America/Denver",
                "America/Los_Angeles", "Europe/London", "Europe/Paris", "Asia/Tokyo"
            ]
            if v not in valid_timezones and not v.startswith("America/") and not v.startswith("Europe/") and not v.startswith("Asia/"):
                raise ValueError(f"Invalid timezone format: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "timezone": "America/New_York",
                "language": "en_US",
                "notification_email": True,
                "notification_push": False,
                "theme": "dark",
            }
        }


class AccountStatusChangeRequestContract(BaseModel):
    """
    Contract: Account status change request schema

    Used for admin operations to activate/deactivate accounts in tests.
    """
    is_active: bool = Field(..., description="Account active status")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for status change")

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v, info):
        # If deactivating, reason should be provided
        if info.data.get('is_active') is False and not v:
            raise ValueError("Reason required when deactivating account")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "is_active": False,
                "reason": "Account suspended due to terms violation",
            }
        }


class AccountListParamsContract(BaseModel):
    """
    Contract: Account list query parameters schema

    Used for listing accounts with pagination and filtering in tests.
    """
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(50, ge=1, le=100, description="Items per page (max 100)")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    search: Optional[str] = Field(None, max_length=100, description="Search in name/email")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 50,
                "is_active": True,
                "search": "john",
            }
        }


class AccountSearchParamsContract(BaseModel):
    """
    Contract: Account search query parameters schema

    Used for searching accounts in tests.
    """
    query: str = Field(..., min_length=1, max_length=100, description="Search query string")
    limit: int = Field(50, ge=1, le=100, description="Maximum results to return")
    include_inactive: bool = Field(False, description="Include inactive accounts in results")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Search query cannot be empty or whitespace only")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "query": "john.doe",
                "limit": 50,
                "include_inactive": False,
            }
        }


class AccountBulkOperationRequestContract(BaseModel):
    """
    Contract: Bulk account operation request schema

    Used for bulk operations on multiple accounts in tests.
    """
    user_ids: List[str] = Field(..., min_length=1, max_length=100, description="List of user IDs to process")
    operation: str = Field(..., pattern="^(activate|deactivate|delete)$", description="Operation to perform")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for bulk operation")

    @field_validator('user_ids')
    @classmethod
    def validate_user_ids(cls, v):
        if not v:
            raise ValueError("At least one user_id required")
        if len(v) > 100:
            raise ValueError("Maximum 100 user_ids per bulk operation")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": ["user_123", "user_456", "user_789"],
                "operation": "deactivate",
                "reason": "Bulk suspension for spam accounts",
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class AccountProfileResponseContract(BaseModel):
    """
    Contract: Account profile response schema

    Validates API response structure for detailed account profiles.
    """
    user_id: str = Field(..., description="User ID")
    email: Optional[str] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    is_active: bool = Field(..., description="Account active status")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123def456",
                "email": "john.doe@example.com",
                "name": "John Doe",
                "is_active": True,
                "preferences": {
                    "timezone": "America/New_York",
                    "language": "en_US",
                    "theme": "dark"
                },
                "created_at": "2025-12-10T12:00:00Z",
                "updated_at": "2025-12-12T10:30:00Z",
            }
        }


class AccountSummaryResponseContract(BaseModel):
    """
    Contract: Account summary response schema

    Validates API response structure for account summaries (used in lists).
    """
    user_id: str = Field(..., description="User ID")
    email: Optional[str] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    is_active: bool = Field(..., description="Account active status")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123def456",
                "email": "john.doe@example.com",
                "name": "John Doe",
                "is_active": True,
                "created_at": "2025-12-10T12:00:00Z",
            }
        }


class AccountSearchResponseContract(BaseModel):
    """
    Contract: Account search response schema

    Validates API response structure for account search results with pagination.
    """
    accounts: List[AccountSummaryResponseContract] = Field(..., description="List of matching accounts")
    total_count: int = Field(..., ge=0, description="Total number of matching accounts")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(..., description="Whether there are more results")

    class Config:
        json_schema_extra = {
            "example": {
                "accounts": [
                    {
                        "user_id": "user_123",
                        "email": "john.doe@example.com",
                        "name": "John Doe",
                        "is_active": True,
                        "created_at": "2025-12-10T12:00:00Z",
                    }
                ],
                "total_count": 1,
                "page": 1,
                "page_size": 50,
                "has_next": False,
            }
        }


class AccountStatsResponseContract(BaseModel):
    """
    Contract: Account statistics response schema

    Validates API response structure for account service statistics.
    """
    total_accounts: int = Field(..., ge=0, description="Total number of accounts")
    active_accounts: int = Field(..., ge=0, description="Number of active accounts")
    inactive_accounts: int = Field(..., ge=0, description="Number of inactive accounts")
    recent_registrations_7d: int = Field(..., ge=0, description="New accounts in last 7 days")
    recent_registrations_30d: int = Field(..., ge=0, description="New accounts in last 30 days")

    class Config:
        json_schema_extra = {
            "example": {
                "total_accounts": 1250,
                "active_accounts": 1180,
                "inactive_accounts": 70,
                "recent_registrations_7d": 45,
                "recent_registrations_30d": 203,
            }
        }


class AccountServiceStatusContract(BaseModel):
    """
    Contract: Account service status response schema

    Validates API response structure for service health check.
    """
    service: str = Field(default="account_service", description="Service name")
    status: str = Field(..., pattern="^(operational|degraded|down)$", description="Service status")
    port: int = Field(..., ge=1024, le=65535, description="Service port")
    version: str = Field(..., description="Service version")
    database_connected: bool = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Status check timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "account_service",
                "status": "operational",
                "port": 8202,
                "version": "1.1.0",
                "database_connected": True,
                "timestamp": "2025-12-12T10:30:00Z",
            }
        }


class AccountBulkOperationResponseContract(BaseModel):
    """
    Contract: Bulk operation response schema

    Validates API response structure for bulk account operations.
    """
    operation: str = Field(..., description="Operation performed")
    total_requested: int = Field(..., ge=0, description="Number of accounts requested")
    successful: int = Field(..., ge=0, description="Number of successful operations")
    failed: int = Field(..., ge=0, description="Number of failed operations")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="List of errors (user_id, error)")

    class Config:
        json_schema_extra = {
            "example": {
                "operation": "deactivate",
                "total_requested": 3,
                "successful": 2,
                "failed": 1,
                "errors": [
                    {"user_id": "user_789", "error": "Account not found"}
                ],
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class AccountTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_email() -> str:
        """Generate unique test email address"""
        return f"test_{uuid.uuid4().hex[:8]}@example.com"

    @staticmethod
    def make_name() -> str:
        """Generate random test name"""
        first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        last_names = ["Doe", "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    @staticmethod
    def make_timezone() -> str:
        """Generate random timezone"""
        timezones = [
            "UTC", "America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles", "Europe/London", "Europe/Paris", "Asia/Tokyo"
        ]
        return random.choice(timezones)

    @staticmethod
    def make_language() -> str:
        """Generate random language code"""
        languages = ["en_US", "es_ES", "fr_FR", "de_DE", "ja_JP", "zh_CN"]
        return random.choice(languages)

    @staticmethod
    def make_theme() -> str:
        """Generate random theme preference"""
        themes = ["light", "dark", "auto"]
        return random.choice(themes)

    @staticmethod
    def make_preferences() -> Dict[str, Any]:
        """Generate random user preferences"""
        return {
            "timezone": AccountTestDataFactory.make_timezone(),
            "language": AccountTestDataFactory.make_language(),
            "notification_email": random.choice([True, False]),
            "notification_push": random.choice([True, False]),
            "theme": AccountTestDataFactory.make_theme(),
        }

    @staticmethod
    def make_ensure_request(**overrides) -> AccountEnsureRequestContract:
        """
        Create valid account ensure request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AccountEnsureRequestContract with valid data

        Example:
            request = AccountTestDataFactory.make_ensure_request(
                user_id="user_123",
                email="custom@example.com",
            )
        """
        defaults = {
            "user_id": AccountTestDataFactory.make_user_id(),
            "email": AccountTestDataFactory.make_email(),
            "name": AccountTestDataFactory.make_name(),
        }
        defaults.update(overrides)
        return AccountEnsureRequestContract(**defaults)

    @staticmethod
    def make_update_request(**overrides) -> AccountUpdateRequestContract:
        """
        Create valid account update request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AccountUpdateRequestContract with valid data
        """
        defaults = {
            "name": AccountTestDataFactory.make_name(),
            "email": AccountTestDataFactory.make_email(),
            "preferences": AccountTestDataFactory.make_preferences(),
        }
        defaults.update(overrides)
        return AccountUpdateRequestContract(**defaults)

    @staticmethod
    def make_preferences_request(**overrides) -> AccountPreferencesRequestContract:
        """
        Create valid preferences update request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AccountPreferencesRequestContract with valid data
        """
        defaults = {
            "timezone": AccountTestDataFactory.make_timezone(),
            "language": AccountTestDataFactory.make_language(),
            "notification_email": True,
            "notification_push": False,
            "theme": AccountTestDataFactory.make_theme(),
        }
        defaults.update(overrides)
        return AccountPreferencesRequestContract(**defaults)

    @staticmethod
    def make_status_change_request(**overrides) -> AccountStatusChangeRequestContract:
        """
        Create valid status change request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AccountStatusChangeRequestContract with valid data
        """
        defaults = {
            "is_active": False,
            "reason": "Account suspended for testing purposes",
        }
        defaults.update(overrides)
        return AccountStatusChangeRequestContract(**defaults)

    @staticmethod
    def make_list_params(**overrides) -> AccountListParamsContract:
        """
        Create valid list parameters with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AccountListParamsContract with valid data
        """
        defaults = {
            "page": 1,
            "page_size": 50,
            "is_active": None,
            "search": None,
        }
        defaults.update(overrides)
        return AccountListParamsContract(**defaults)

    @staticmethod
    def make_search_params(**overrides) -> AccountSearchParamsContract:
        """
        Create valid search parameters with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AccountSearchParamsContract with valid data
        """
        defaults = {
            "query": AccountTestDataFactory.make_name().split()[0].lower(),
            "limit": 50,
            "include_inactive": False,
        }
        defaults.update(overrides)
        return AccountSearchParamsContract(**defaults)

    @staticmethod
    def make_bulk_operation_request(**overrides) -> AccountBulkOperationRequestContract:
        """
        Create valid bulk operation request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AccountBulkOperationRequestContract with valid data
        """
        defaults = {
            "user_ids": [
                AccountTestDataFactory.make_user_id(),
                AccountTestDataFactory.make_user_id(),
                AccountTestDataFactory.make_user_id(),
            ],
            "operation": "deactivate",
            "reason": "Bulk testing operation",
        }
        defaults.update(overrides)
        return AccountBulkOperationRequestContract(**defaults)

    @staticmethod
    def make_profile_response(**overrides) -> AccountProfileResponseContract:
        """
        Create expected account profile response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "user_id": AccountTestDataFactory.make_user_id(),
            "email": AccountTestDataFactory.make_email(),
            "name": AccountTestDataFactory.make_name(),
            "is_active": True,
            "preferences": AccountTestDataFactory.make_preferences(),
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return AccountProfileResponseContract(**defaults)

    @staticmethod
    def make_summary_response(**overrides) -> AccountSummaryResponseContract:
        """
        Create expected account summary response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "user_id": AccountTestDataFactory.make_user_id(),
            "email": AccountTestDataFactory.make_email(),
            "name": AccountTestDataFactory.make_name(),
            "is_active": True,
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        }
        defaults.update(overrides)
        return AccountSummaryResponseContract(**defaults)

    @staticmethod
    def make_search_response(**overrides) -> AccountSearchResponseContract:
        """
        Create expected account search response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "accounts": [
                AccountTestDataFactory.make_summary_response()
            ],
            "total_count": 1,
            "page": 1,
            "page_size": 50,
            "has_next": False,
        }
        defaults.update(overrides)
        return AccountSearchResponseContract(**defaults)

    @staticmethod
    def make_stats_response(**overrides) -> AccountStatsResponseContract:
        """
        Create expected account stats response for assertions.

        Used in tests to validate API responses match contract.
        """
        total = random.randint(1000, 5000)
        active = int(total * 0.9)  # 90% active
        defaults = {
            "total_accounts": total,
            "active_accounts": active,
            "inactive_accounts": total - active,
            "recent_registrations_7d": random.randint(10, 100),
            "recent_registrations_30d": random.randint(100, 500),
        }
        defaults.update(overrides)
        return AccountStatsResponseContract(**defaults)

    @staticmethod
    def make_service_status(**overrides) -> AccountServiceStatusContract:
        """
        Create expected service status response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "service": "account_service",
            "status": "operational",
            "port": 8202,
            "version": "1.1.0",
            "database_connected": True,
            "timestamp": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return AccountServiceStatusContract(**defaults)

    @staticmethod
    def make_bulk_operation_response(**overrides) -> AccountBulkOperationResponseContract:
        """
        Create expected bulk operation response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "operation": "deactivate",
            "total_requested": 3,
            "successful": 3,
            "failed": 0,
            "errors": [],
        }
        defaults.update(overrides)
        return AccountBulkOperationResponseContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_ensure_request_missing_user_id() -> dict:
        """Generate ensure request missing required user_id"""
        return {
            "email": AccountTestDataFactory.make_email(),
            "name": AccountTestDataFactory.make_name(),
        }

    @staticmethod
    def make_invalid_ensure_request_missing_email() -> dict:
        """Generate ensure request missing required email"""
        return {
            "user_id": AccountTestDataFactory.make_user_id(),
            "name": AccountTestDataFactory.make_name(),
        }

    @staticmethod
    def make_invalid_ensure_request_invalid_email() -> dict:
        """Generate ensure request with invalid email format"""
        return {
            "user_id": AccountTestDataFactory.make_user_id(),
            "email": "not-a-valid-email",
            "name": AccountTestDataFactory.make_name(),
        }

    @staticmethod
    def make_invalid_ensure_request_empty_name() -> dict:
        """Generate ensure request with empty name"""
        return {
            "user_id": AccountTestDataFactory.make_user_id(),
            "email": AccountTestDataFactory.make_email(),
            "name": "",
        }

    @staticmethod
    def make_invalid_update_request_invalid_email() -> dict:
        """Generate update request with invalid email format"""
        return {
            "name": AccountTestDataFactory.make_name(),
            "email": "invalid-email-format",
        }

    @staticmethod
    def make_invalid_update_request_empty_name() -> dict:
        """Generate update request with empty name"""
        return {
            "name": "   ",  # Whitespace only
            "email": AccountTestDataFactory.make_email(),
        }

    @staticmethod
    def make_invalid_preferences_request_invalid_theme() -> dict:
        """Generate preferences request with invalid theme"""
        return {
            "timezone": "UTC",
            "language": "en_US",
            "theme": "invalid_theme",  # Invalid - must be light/dark/auto
        }

    @staticmethod
    def make_invalid_status_change_request_missing_reason() -> dict:
        """Generate status change request missing required reason when deactivating"""
        return {
            "is_active": False,
            # Missing reason (required when deactivating)
        }

    @staticmethod
    def make_invalid_search_params_empty_query() -> dict:
        """Generate search params with empty query"""
        return {
            "query": "   ",  # Whitespace only
            "limit": 50,
        }

    @staticmethod
    def make_invalid_list_params_invalid_page() -> dict:
        """Generate list params with invalid page number"""
        return {
            "page": 0,  # Invalid - must be >= 1
            "page_size": 50,
        }

    @staticmethod
    def make_invalid_list_params_excessive_page_size() -> dict:
        """Generate list params with excessive page size"""
        return {
            "page": 1,
            "page_size": 1000,  # Invalid - max is 100
        }

    @staticmethod
    def make_invalid_bulk_operation_empty_user_ids() -> dict:
        """Generate bulk operation request with empty user_ids list"""
        return {
            "user_ids": [],  # Invalid - must have at least 1
            "operation": "deactivate",
            "reason": "Testing",
        }

    @staticmethod
    def make_invalid_bulk_operation_invalid_operation() -> dict:
        """Generate bulk operation request with invalid operation"""
        return {
            "user_ids": [AccountTestDataFactory.make_user_id()],
            "operation": "invalid_operation",  # Invalid - must be activate/deactivate/delete
            "reason": "Testing",
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class AccountEnsureRequestBuilder:
    """
    Builder pattern for creating complex account ensure requests.

    Useful for tests that need to gradually construct requests.

    Example:
        request = (
            AccountEnsureRequestBuilder()
            .with_user_id("user_123")
            .with_email("john@example.com")
            .with_name("John Doe")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "user_id": AccountTestDataFactory.make_user_id(),
            "email": AccountTestDataFactory.make_email(),
            "name": AccountTestDataFactory.make_name(),
        }

    def with_user_id(self, user_id: str) -> "AccountEnsureRequestBuilder":
        """Set user ID"""
        self._data["user_id"] = user_id
        return self

    def with_email(self, email: str) -> "AccountEnsureRequestBuilder":
        """Set email address"""
        self._data["email"] = email
        return self

    def with_name(self, name: str) -> "AccountEnsureRequestBuilder":
        """Set user name"""
        self._data["name"] = name
        return self

    def build(self) -> AccountEnsureRequestContract:
        """Build the final request"""
        return AccountEnsureRequestContract(**self._data)


class AccountProfileUpdateRequestBuilder:
    """
    Builder pattern for creating complex account update requests.

    Example:
        request = (
            AccountProfileUpdateRequestBuilder()
            .with_name("John Updated")
            .with_email("john.updated@example.com")
            .with_preference("timezone", "America/New_York")
            .with_preference("theme", "dark")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "name": None,
            "email": None,
            "preferences": {},
        }

    def with_name(self, name: str) -> "AccountProfileUpdateRequestBuilder":
        """Set user name"""
        self._data["name"] = name
        return self

    def with_email(self, email: str) -> "AccountProfileUpdateRequestBuilder":
        """Set email address"""
        self._data["email"] = email
        return self

    def with_preferences(self, preferences: Dict[str, Any]) -> "AccountProfileUpdateRequestBuilder":
        """Set entire preferences dict"""
        self._data["preferences"] = preferences
        return self

    def with_preference(self, key: str, value: Any) -> "AccountProfileUpdateRequestBuilder":
        """Add a single preference"""
        if self._data["preferences"] is None:
            self._data["preferences"] = {}
        self._data["preferences"][key] = value
        return self

    def with_timezone(self, timezone: str) -> "AccountProfileUpdateRequestBuilder":
        """Set timezone preference"""
        return self.with_preference("timezone", timezone)

    def with_language(self, language: str) -> "AccountProfileUpdateRequestBuilder":
        """Set language preference"""
        return self.with_preference("language", language)

    def with_theme(self, theme: str) -> "AccountProfileUpdateRequestBuilder":
        """Set theme preference"""
        return self.with_preference("theme", theme)

    def with_notification_email(self, enabled: bool) -> "AccountProfileUpdateRequestBuilder":
        """Set email notification preference"""
        return self.with_preference("notification_email", enabled)

    def with_notification_push(self, enabled: bool) -> "AccountProfileUpdateRequestBuilder":
        """Set push notification preference"""
        return self.with_preference("notification_push", enabled)

    def build(self) -> AccountUpdateRequestContract:
        """Build the final request"""
        # Remove None values
        data = {k: v for k, v in self._data.items() if v is not None}
        return AccountUpdateRequestContract(**data)


class AccountPreferencesRequestBuilder:
    """
    Builder pattern for creating complex preferences update requests.

    Example:
        request = (
            AccountPreferencesRequestBuilder()
            .with_timezone("America/New_York")
            .with_language("en_US")
            .with_dark_theme()
            .with_email_notifications(True)
            .with_push_notifications(False)
            .build()
        )
    """

    def __init__(self):
        self._data = {}

    def with_timezone(self, timezone: str) -> "AccountPreferencesRequestBuilder":
        """Set timezone"""
        self._data["timezone"] = timezone
        return self

    def with_language(self, language: str) -> "AccountPreferencesRequestBuilder":
        """Set language"""
        self._data["language"] = language
        return self

    def with_theme(self, theme: str) -> "AccountPreferencesRequestBuilder":
        """Set theme"""
        self._data["theme"] = theme
        return self

    def with_light_theme(self) -> "AccountPreferencesRequestBuilder":
        """Set light theme"""
        return self.with_theme("light")

    def with_dark_theme(self) -> "AccountPreferencesRequestBuilder":
        """Set dark theme"""
        return self.with_theme("dark")

    def with_auto_theme(self) -> "AccountPreferencesRequestBuilder":
        """Set auto theme"""
        return self.with_theme("auto")

    def with_email_notifications(self, enabled: bool) -> "AccountPreferencesRequestBuilder":
        """Set email notifications"""
        self._data["notification_email"] = enabled
        return self

    def with_push_notifications(self, enabled: bool) -> "AccountPreferencesRequestBuilder":
        """Set push notifications"""
        self._data["notification_push"] = enabled
        return self

    def build(self) -> AccountPreferencesRequestContract:
        """Build the final request"""
        return AccountPreferencesRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Request Contracts
    "AccountEnsureRequestContract",
    "AccountUpdateRequestContract",
    "AccountPreferencesRequestContract",
    "AccountStatusChangeRequestContract",
    "AccountListParamsContract",
    "AccountSearchParamsContract",
    "AccountBulkOperationRequestContract",

    # Response Contracts
    "AccountProfileResponseContract",
    "AccountSummaryResponseContract",
    "AccountSearchResponseContract",
    "AccountStatsResponseContract",
    "AccountServiceStatusContract",
    "AccountBulkOperationResponseContract",

    # Factory
    "AccountTestDataFactory",

    # Builders
    "AccountEnsureRequestBuilder",
    "AccountProfileUpdateRequestBuilder",
    "AccountPreferencesRequestBuilder",
]
