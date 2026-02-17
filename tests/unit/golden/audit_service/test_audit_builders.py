"""
Audit Service - Unit Tests: Request Builders

Tests for request builder classes:
- AuditEventCreateRequestBuilder
- AuditQueryRequestBuilder
- SecurityAlertRequestBuilder

No I/O, no mocks, no fixtures needed.
All builders use factory methods for default values.
"""
import pytest
from datetime import datetime, timezone, timedelta

from tests.contracts.audit.data_contract import (
    AuditTestDataFactory,
    AuditEventCreateRequestBuilder,
    AuditQueryRequestBuilder,
    SecurityAlertRequestBuilder,
    EventType,
    AuditCategory,
    EventSeverity,
    AuditEventCreateRequestContract,
    AuditQueryRequestContract,
    SecurityAlertRequestContract,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# AuditEventCreateRequestBuilder Tests (14 tests)
# =============================================================================

class TestAuditEventCreateRequestBuilder:
    """Test audit event creation request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = AuditEventCreateRequestBuilder().build()
        assert isinstance(request, AuditEventCreateRequestContract)
        assert request.event_type is not None
        assert request.action is not None

    def test_builder_with_event_type(self):
        """Builder accepts custom event type"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_event_type(EventType.USER_LOGIN)
            .build()
        )
        assert request.event_type == EventType.USER_LOGIN

    def test_builder_with_category(self):
        """Builder accepts custom category"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_category(AuditCategory.SECURITY)
            .build()
        )
        assert request.category == AuditCategory.SECURITY

    def test_builder_with_severity(self):
        """Builder accepts custom severity"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_severity(EventSeverity.CRITICAL)
            .build()
        )
        assert request.severity == EventSeverity.CRITICAL

    def test_builder_with_action(self):
        """Builder accepts custom action"""
        custom_action = "custom_action_test"
        request = (
            AuditEventCreateRequestBuilder()
            .with_action(custom_action)
            .build()
        )
        assert request.action == custom_action

    def test_builder_with_user_id(self):
        """Builder accepts custom user ID"""
        user_id = AuditTestDataFactory.make_user_id()
        request = (
            AuditEventCreateRequestBuilder()
            .with_user_id(user_id)
            .build()
        )
        assert request.user_id == user_id

    def test_builder_with_organization_id(self):
        """Builder accepts custom organization ID"""
        org_id = AuditTestDataFactory.make_organization_id()
        request = (
            AuditEventCreateRequestBuilder()
            .with_organization_id(org_id)
            .build()
        )
        assert request.organization_id == org_id

    def test_builder_with_resource(self):
        """Builder accepts resource information"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_resource("file", "file_123", "document.pdf")
            .build()
        )
        assert request.resource_type == "file"
        assert request.resource_id == "file_123"
        assert request.resource_name == "document.pdf"

    def test_builder_with_ip_address(self):
        """Builder accepts IP address"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_ip_address("192.168.1.100")
            .build()
        )
        assert request.ip_address == "192.168.1.100"

    def test_builder_with_metadata(self):
        """Builder accepts metadata dict"""
        metadata = {"key1": "value1", "key2": 42}
        request = (
            AuditEventCreateRequestBuilder()
            .with_metadata(metadata)
            .build()
        )
        assert request.metadata["key1"] == "value1"
        assert request.metadata["key2"] == 42

    def test_builder_with_tags(self):
        """Builder accepts tags list"""
        tags = ["tag1", "tag2", "tag3"]
        request = (
            AuditEventCreateRequestBuilder()
            .with_tags(tags)
            .build()
        )
        assert len(request.tags) == 3
        assert "tag1" in request.tags

    def test_builder_chaining(self):
        """Builder supports full method chaining"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_event_type(EventType.USER_LOGIN)
            .with_category(AuditCategory.AUTHENTICATION)
            .with_severity(EventSeverity.LOW)
            .with_action("user_authenticated")
            .with_user_id("user_test123")
            .with_ip_address("10.0.0.1")
            .build()
        )
        assert request.event_type == EventType.USER_LOGIN
        assert request.category == AuditCategory.AUTHENTICATION
        assert request.severity == EventSeverity.LOW
        assert request.action == "user_authenticated"
        assert request.user_id == "user_test123"
        assert request.ip_address == "10.0.0.1"

    def test_builder_build_dict(self):
        """Builder can build as dictionary"""
        data = AuditEventCreateRequestBuilder().build_dict()
        assert isinstance(data, dict)
        assert "event_type" in data
        assert "action" in data

    def test_builder_with_success(self):
        """Builder can set success status"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_success(True)
            .build()
        )
        assert request.success is True

    def test_builder_with_failure(self):
        """Builder can set failure status with error"""
        request = (
            AuditEventCreateRequestBuilder()
            .with_failure("Permission denied")
            .build()
        )
        assert request.success is False
        assert request.error_message == "Permission denied"


# =============================================================================
# AuditQueryRequestBuilder Tests (11 tests)
# =============================================================================

class TestAuditQueryRequestBuilder:
    """Test audit query request builder"""

    def test_builder_default_build(self):
        """Builder creates valid query with defaults"""
        query = AuditQueryRequestBuilder().build()
        assert isinstance(query, AuditQueryRequestContract)
        assert query.limit == 100
        assert query.offset == 0

    def test_builder_with_event_types(self):
        """Builder accepts event types filter"""
        query = (
            AuditQueryRequestBuilder()
            .with_event_types([EventType.USER_LOGIN, EventType.USER_LOGOUT])
            .build()
        )
        assert len(query.event_types) == 2
        assert EventType.USER_LOGIN in query.event_types

    def test_builder_with_categories(self):
        """Builder accepts categories filter"""
        query = (
            AuditQueryRequestBuilder()
            .with_categories([AuditCategory.AUTHENTICATION])
            .build()
        )
        assert AuditCategory.AUTHENTICATION in query.categories

    def test_builder_with_severities(self):
        """Builder accepts severities filter"""
        query = (
            AuditQueryRequestBuilder()
            .with_severities([EventSeverity.HIGH, EventSeverity.CRITICAL])
            .build()
        )
        assert len(query.severities) == 2

    def test_builder_with_user_id(self):
        """Builder accepts user ID filter"""
        user_id = AuditTestDataFactory.make_user_id()
        query = (
            AuditQueryRequestBuilder()
            .with_user_id(user_id)
            .build()
        )
        assert query.user_id == user_id

    def test_builder_with_organization_id(self):
        """Builder accepts organization ID filter"""
        org_id = AuditTestDataFactory.make_organization_id()
        query = (
            AuditQueryRequestBuilder()
            .with_organization_id(org_id)
            .build()
        )
        assert query.organization_id == org_id

    def test_builder_with_time_range(self):
        """Builder accepts time range filter"""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        query = (
            AuditQueryRequestBuilder()
            .with_time_range(start, end)
            .build()
        )
        assert query.start_time == start
        assert query.end_time == end

    def test_builder_with_pagination(self):
        """Builder accepts pagination parameters"""
        query = (
            AuditQueryRequestBuilder()
            .with_pagination(limit=50, offset=100)
            .build()
        )
        assert query.limit == 50
        assert query.offset == 100

    def test_builder_with_success_filter(self):
        """Builder accepts success filter"""
        query = (
            AuditQueryRequestBuilder()
            .with_success_filter(True)
            .build()
        )
        assert query.success is True

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        query = (
            AuditQueryRequestBuilder()
            .with_event_types([EventType.USER_LOGIN])
            .with_severities([EventSeverity.HIGH])
            .with_pagination(limit=25, offset=0)
            .build()
        )
        assert EventType.USER_LOGIN in query.event_types
        assert EventSeverity.HIGH in query.severities
        assert query.limit == 25

    def test_builder_build_dict(self):
        """Builder can build as dictionary"""
        data = AuditQueryRequestBuilder().build_dict()
        assert isinstance(data, dict)
        assert "limit" in data
        assert "offset" in data


# =============================================================================
# SecurityAlertRequestBuilder Tests (9 tests)
# =============================================================================

class TestSecurityAlertRequestBuilder:
    """Test security alert request builder"""

    def test_builder_default_build(self):
        """Builder creates valid alert with defaults"""
        alert = SecurityAlertRequestBuilder().build()
        assert isinstance(alert, SecurityAlertRequestContract)
        assert alert.threat_type is not None

    def test_builder_with_threat_type(self):
        """Builder accepts custom threat type"""
        alert = (
            SecurityAlertRequestBuilder()
            .with_threat_type("brute_force")
            .build()
        )
        assert alert.threat_type == "brute_force"

    def test_builder_with_severity(self):
        """Builder accepts custom severity"""
        alert = (
            SecurityAlertRequestBuilder()
            .with_severity(EventSeverity.CRITICAL)
            .build()
        )
        assert alert.severity == EventSeverity.CRITICAL

    def test_builder_with_description(self):
        """Builder accepts custom description"""
        desc = "Multiple failed login attempts detected"
        alert = (
            SecurityAlertRequestBuilder()
            .with_description(desc)
            .build()
        )
        assert alert.description == desc

    def test_builder_with_source_ip(self):
        """Builder accepts source IP"""
        alert = (
            SecurityAlertRequestBuilder()
            .with_source_ip("10.0.0.50")
            .build()
        )
        assert alert.source_ip == "10.0.0.50"

    def test_builder_with_target_resource(self):
        """Builder accepts target resource"""
        alert = (
            SecurityAlertRequestBuilder()
            .with_target_resource("auth_endpoint")
            .build()
        )
        assert alert.target_resource == "auth_endpoint"

    def test_builder_with_brute_force(self):
        """Builder can configure as brute force alert"""
        alert = (
            SecurityAlertRequestBuilder()
            .with_brute_force(attempt_count=100)
            .build()
        )
        assert alert.threat_type == "brute_force_attempt"
        assert alert.severity == EventSeverity.HIGH
        assert alert.metadata.get("attempt_count") == 100

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        alert = (
            SecurityAlertRequestBuilder()
            .with_threat_type("data_breach")
            .with_severity(EventSeverity.CRITICAL)
            .with_source_ip("192.168.1.50")
            .with_description("Unauthorized data access")
            .build()
        )
        assert alert.threat_type == "data_breach"
        assert alert.severity == EventSeverity.CRITICAL
        assert alert.source_ip == "192.168.1.50"

    def test_builder_build_dict(self):
        """Builder can build as dictionary"""
        data = SecurityAlertRequestBuilder().build_dict()
        assert isinstance(data, dict)
        assert "threat_type" in data
