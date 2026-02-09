"""
Audit Service - Unit Tests: TestDataFactory

Tests for AuditTestDataFactory methods:
- ID generation
- String generation
- Timestamp generation
- Request/Response generation
- Invalid data generation
- Edge case generation

No I/O, no mocks, no fixtures needed.
All factory methods must generate unique, valid data.
"""
import pytest
from datetime import datetime, timezone, timedelta

from tests.contracts.audit.data_contract import (
    AuditTestDataFactory,
    EventType,
    AuditCategory,
    EventSeverity,
    EventStatus,
    ComplianceStandard,
    AuditEventCreateRequestContract,
    AuditQueryRequestContract,
    SecurityAlertRequestContract,
    UserActivityQueryRequestContract,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# ID Generation Tests (12 tests)
# =============================================================================

class TestAuditTestDataFactoryIds:
    """Test ID generation methods"""

    def test_make_audit_event_id_format(self):
        """make_audit_event_id returns correctly formatted ID"""
        event_id = AuditTestDataFactory.make_audit_event_id()
        assert event_id.startswith("audit_")
        assert len(event_id) > 10

    def test_make_audit_event_id_uniqueness(self):
        """make_audit_event_id generates unique IDs"""
        ids = [AuditTestDataFactory.make_audit_event_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_make_security_event_id_format(self):
        """make_security_event_id returns correctly formatted ID"""
        event_id = AuditTestDataFactory.make_security_event_id()
        assert event_id.startswith("sec_")
        assert len(event_id) > 8

    def test_make_security_event_id_uniqueness(self):
        """make_security_event_id generates unique IDs"""
        ids = [AuditTestDataFactory.make_security_event_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_make_user_id_format(self):
        """make_user_id returns correctly formatted ID"""
        user_id = AuditTestDataFactory.make_user_id()
        assert user_id.startswith("user_")

    def test_make_user_id_uniqueness(self):
        """make_user_id generates unique IDs"""
        ids = [AuditTestDataFactory.make_user_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_make_session_id_format(self):
        """make_session_id returns correctly formatted ID"""
        session_id = AuditTestDataFactory.make_session_id()
        assert session_id.startswith("sess_")

    def test_make_organization_id_format(self):
        """make_organization_id returns correctly formatted ID"""
        org_id = AuditTestDataFactory.make_organization_id()
        assert org_id.startswith("org_")

    def test_make_resource_id_format(self):
        """make_resource_id returns correctly formatted ID"""
        resource_id = AuditTestDataFactory.make_resource_id()
        assert "_" in resource_id

    def test_make_uuid_format(self):
        """make_uuid returns valid UUID string"""
        uuid_str = AuditTestDataFactory.make_uuid()
        assert len(uuid_str) == 36
        assert uuid_str.count('-') == 4

    def test_make_uuid_uniqueness(self):
        """make_uuid generates unique UUIDs"""
        uuids = [AuditTestDataFactory.make_uuid() for _ in range(100)]
        assert len(set(uuids)) == 100

    def test_make_correlation_id_format(self):
        """make_correlation_id returns correctly formatted ID"""
        corr_id = AuditTestDataFactory.make_correlation_id()
        assert corr_id.startswith("corr_")


# =============================================================================
# String Generation Tests (8 tests)
# =============================================================================

class TestAuditTestDataFactoryStrings:
    """Test string generation methods"""

    def test_make_action_non_empty(self):
        """make_action generates non-empty strings"""
        action = AuditTestDataFactory.make_action()
        assert len(action) > 0

    def test_make_action_uniqueness(self):
        """make_action generates unique strings"""
        actions = [AuditTestDataFactory.make_action() for _ in range(100)]
        assert len(set(actions)) == 100

    def test_make_description_non_empty(self):
        """make_description generates non-empty strings"""
        desc = AuditTestDataFactory.make_description()
        assert len(desc) > 0

    def test_make_resource_type_valid(self):
        """make_resource_type returns valid resource type"""
        resource_type = AuditTestDataFactory.make_resource_type()
        assert resource_type in ["file", "folder", "document", "user", "organization", "device", "album", "photo"]

    def test_make_resource_name_non_empty(self):
        """make_resource_name generates non-empty strings"""
        name = AuditTestDataFactory.make_resource_name()
        assert len(name) > 0

    def test_make_ip_address_valid_format(self):
        """make_ip_address generates valid IP format"""
        ip = AuditTestDataFactory.make_ip_address()
        parts = ip.split(".")
        assert len(parts) == 4
        for part in parts:
            assert 0 <= int(part) <= 255

    def test_make_user_agent_non_empty(self):
        """make_user_agent generates non-empty string"""
        ua = AuditTestDataFactory.make_user_agent()
        assert len(ua) > 0

    def test_make_threat_type_non_empty(self):
        """make_threat_type returns non-empty string"""
        threat = AuditTestDataFactory.make_threat_type()
        assert len(threat) > 0


# =============================================================================
# Timestamp Generation Tests (8 tests)
# =============================================================================

class TestAuditTestDataFactoryTimestamps:
    """Test timestamp generation methods"""

    def test_make_timestamp_utc(self):
        """make_timestamp returns UTC datetime"""
        ts = AuditTestDataFactory.make_timestamp()
        assert ts.tzinfo == timezone.utc

    def test_make_timestamp_recent(self):
        """make_timestamp returns recent timestamp"""
        ts = AuditTestDataFactory.make_timestamp()
        now = datetime.now(timezone.utc)
        diff = abs((now - ts).total_seconds())
        assert diff < 5  # Within 5 seconds

    def test_make_past_timestamp_in_past(self):
        """make_past_timestamp returns past datetime"""
        ts = AuditTestDataFactory.make_past_timestamp()
        now = datetime.now(timezone.utc)
        assert ts < now

    def test_make_past_timestamp_within_range(self):
        """make_past_timestamp within specified range"""
        ts = AuditTestDataFactory.make_past_timestamp(days=7)
        now = datetime.now(timezone.utc)
        min_ts = now - timedelta(days=7)
        assert ts >= min_ts
        assert ts < now

    def test_make_future_timestamp_in_future(self):
        """make_future_timestamp returns future datetime"""
        ts = AuditTestDataFactory.make_future_timestamp()
        now = datetime.now(timezone.utc)
        assert ts > now

    def test_make_future_timestamp_within_range(self):
        """make_future_timestamp within specified range"""
        ts = AuditTestDataFactory.make_future_timestamp(days=7)
        now = datetime.now(timezone.utc)
        max_ts = now + timedelta(days=7)
        assert ts <= max_ts
        assert ts > now

    def test_make_timestamp_iso_format(self):
        """make_timestamp_iso returns ISO format string"""
        ts_iso = AuditTestDataFactory.make_timestamp_iso()
        assert isinstance(ts_iso, str)
        assert "T" in ts_iso  # ISO format contains T separator

    def test_make_timestamp_iso_parseable(self):
        """make_timestamp_iso returns parseable ISO string"""
        ts_iso = AuditTestDataFactory.make_timestamp_iso()
        # Should be parseable
        parsed = datetime.fromisoformat(ts_iso.replace('Z', '+00:00'))
        assert parsed is not None


# =============================================================================
# Enum Generation Tests (7 tests)
# =============================================================================

class TestAuditTestDataFactoryEnums:
    """Test enum generation methods"""

    def test_make_event_type_valid(self):
        """make_event_type returns valid EventType"""
        event_type = AuditTestDataFactory.make_event_type()
        assert isinstance(event_type, EventType)

    def test_make_category_valid(self):
        """make_category returns valid AuditCategory"""
        category = AuditTestDataFactory.make_category()
        assert isinstance(category, AuditCategory)

    def test_make_severity_valid(self):
        """make_severity returns valid EventSeverity"""
        severity = AuditTestDataFactory.make_severity()
        assert isinstance(severity, EventSeverity)

    def test_make_status_valid(self):
        """make_status returns valid EventStatus"""
        status = AuditTestDataFactory.make_status()
        assert isinstance(status, EventStatus)

    def test_make_compliance_standard_valid(self):
        """make_compliance_standard returns valid ComplianceStandard"""
        standard = AuditTestDataFactory.make_compliance_standard()
        assert isinstance(standard, ComplianceStandard)

    def test_make_metadata_returns_dict(self):
        """make_metadata returns dict"""
        metadata = AuditTestDataFactory.make_metadata()
        assert isinstance(metadata, dict)

    def test_make_tags_returns_list(self):
        """make_tags returns list of strings"""
        tags = AuditTestDataFactory.make_tags()
        assert isinstance(tags, list)
        assert all(isinstance(t, str) for t in tags)


# =============================================================================
# Request Generation Tests (10 tests)
# =============================================================================

class TestAuditTestDataFactoryRequests:
    """Test request generation methods"""

    def test_make_audit_event_create_request_valid(self):
        """make_audit_event_create_request generates valid request"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        assert isinstance(request, AuditEventCreateRequestContract)
        assert request.event_type is not None
        assert request.action is not None

    def test_make_audit_event_create_request_with_overrides(self):
        """make_audit_event_create_request accepts overrides"""
        request = AuditTestDataFactory.make_audit_event_create_request(
            event_type=EventType.SECURITY_ALERT,
            severity=EventSeverity.CRITICAL,
        )
        assert request.event_type == EventType.SECURITY_ALERT
        assert request.severity == EventSeverity.CRITICAL

    def test_make_audit_event_create_request_uniqueness(self):
        """make_audit_event_create_request generates unique data"""
        requests = [AuditTestDataFactory.make_audit_event_create_request() for _ in range(10)]
        actions = [r.action for r in requests]
        assert len(set(actions)) == 10  # All unique

    def test_make_audit_query_request_valid(self):
        """make_audit_query_request generates valid request"""
        request = AuditTestDataFactory.make_audit_query_request()
        assert isinstance(request, AuditQueryRequestContract)
        assert request.limit > 0

    def test_make_audit_query_request_with_filters(self):
        """make_audit_query_request accepts filter overrides"""
        request = AuditTestDataFactory.make_audit_query_request(
            event_types=[EventType.USER_LOGIN],
            severities=[EventSeverity.HIGH],
        )
        assert EventType.USER_LOGIN in request.event_types
        assert EventSeverity.HIGH in request.severities

    def test_make_security_alert_request_valid(self):
        """make_security_alert_request generates valid request"""
        request = AuditTestDataFactory.make_security_alert_request()
        assert isinstance(request, SecurityAlertRequestContract)
        assert request.threat_type is not None

    def test_make_security_alert_request_with_overrides(self):
        """make_security_alert_request accepts overrides"""
        request = AuditTestDataFactory.make_security_alert_request(
            threat_type="brute_force",
        )
        assert request.threat_type == "brute_force"

    def test_make_user_activity_query_request_valid(self):
        """make_user_activity_query_request generates valid request"""
        request = AuditTestDataFactory.make_user_activity_query_request()
        assert isinstance(request, UserActivityQueryRequestContract)
        assert request.days > 0
        assert request.limit > 0

    def test_make_compliance_report_request_valid(self):
        """make_compliance_report_request generates valid request"""
        request = AuditTestDataFactory.make_compliance_report_request()
        assert request.compliance_standard is not None

    def test_make_data_cleanup_request_valid(self):
        """make_data_cleanup_request generates valid request"""
        request = AuditTestDataFactory.make_data_cleanup_request()
        assert request.retention_days > 0


# =============================================================================
# Response Generation Tests (8 tests)
# =============================================================================

class TestAuditTestDataFactoryResponses:
    """Test response generation methods"""

    def test_make_audit_event_response_valid(self):
        """make_audit_event_response generates valid response data"""
        response = AuditTestDataFactory.make_audit_event_response()
        assert "id" in response
        assert "event_type" in response
        assert "action" in response

    def test_make_audit_event_response_with_overrides(self):
        """make_audit_event_response accepts overrides"""
        custom_id = AuditTestDataFactory.make_audit_event_id()
        response = AuditTestDataFactory.make_audit_event_response(id=custom_id)
        assert response["id"] == custom_id

    def test_make_audit_query_response_valid(self):
        """make_audit_query_response generates valid response data"""
        response = AuditTestDataFactory.make_audit_query_response(count=5)
        assert "events" in response
        assert len(response["events"]) == 5
        assert response["total_count"] == 5

    def test_make_security_event_response_valid(self):
        """make_security_event_response generates valid response data"""
        response = AuditTestDataFactory.make_security_event_response()
        assert "id" in response
        assert "severity" in response

    def test_make_user_activity_summary_response_valid(self):
        """make_user_activity_summary_response generates valid data"""
        response = AuditTestDataFactory.make_user_activity_summary_response()
        assert "user_id" in response
        assert "total_activities" in response

    def test_make_compliance_report_response_valid(self):
        """make_compliance_report_response generates valid data"""
        response = AuditTestDataFactory.make_compliance_report_response()
        assert "compliance_standard" in response
        assert "compliance_score" in response

    def test_make_service_health_response_valid(self):
        """make_service_health_response generates valid health data"""
        response = AuditTestDataFactory.make_service_health_response()
        assert response["status"] in ["healthy", "degraded", "unhealthy"]
        assert response["service"] == "audit_service"

    def test_make_data_cleanup_response_valid(self):
        """make_data_cleanup_response generates valid cleanup data"""
        response = AuditTestDataFactory.make_data_cleanup_response()
        assert "cleaned_events" in response
        assert "retention_days" in response


# =============================================================================
# Invalid Data Generation Tests (10 tests)
# =============================================================================

class TestAuditTestDataFactoryInvalid:
    """Test invalid data generation methods"""

    def test_make_invalid_audit_event_missing_action(self):
        """make_invalid_audit_event_missing_action has no action"""
        data = AuditTestDataFactory.make_invalid_audit_event_missing_action()
        assert "action" not in data

    def test_make_invalid_audit_event_empty_action(self):
        """make_invalid_audit_event_empty_action has empty action"""
        data = AuditTestDataFactory.make_invalid_audit_event_empty_action()
        assert data.get("action") == ""

    def test_make_invalid_audit_event_whitespace_action(self):
        """make_invalid_audit_event_whitespace_action has whitespace action"""
        data = AuditTestDataFactory.make_invalid_audit_event_whitespace_action()
        assert data.get("action", "").strip() == ""

    def test_make_invalid_query_limit_zero(self):
        """make_invalid_query_limit_zero returns zero limit"""
        data = AuditTestDataFactory.make_invalid_query_limit_zero()
        assert data.get("limit") == 0

    def test_make_invalid_query_limit_negative(self):
        """make_invalid_query_limit_negative returns negative limit"""
        data = AuditTestDataFactory.make_invalid_query_limit_negative()
        assert data.get("limit") < 0

    def test_make_invalid_query_limit_too_large(self):
        """make_invalid_query_limit_too_large exceeds maximum"""
        data = AuditTestDataFactory.make_invalid_query_limit_too_large()
        assert data.get("limit") > 1000

    def test_make_invalid_query_offset_negative(self):
        """make_invalid_query_offset_negative returns negative offset"""
        data = AuditTestDataFactory.make_invalid_query_offset_negative()
        assert data.get("offset") < 0

    def test_make_invalid_batch_empty(self):
        """make_invalid_batch_empty returns empty batch"""
        data = AuditTestDataFactory.make_invalid_batch_empty()
        assert data.get("events") == []

    def test_make_invalid_security_alert_empty_threat_type(self):
        """make_invalid_security_alert_empty_threat_type has empty threat_type"""
        data = AuditTestDataFactory.make_invalid_security_alert_empty_threat_type()
        assert data.get("threat_type") == ""

    def test_make_invalid_cleanup_retention_too_short(self):
        """make_invalid_cleanup_retention_too_short has short retention"""
        data = AuditTestDataFactory.make_invalid_cleanup_retention_too_short()
        assert data.get("retention_days") < 30  # Min is 30 per contract


# =============================================================================
# Edge Case Generation Tests (6 tests)
# =============================================================================

class TestAuditTestDataFactoryEdgeCases:
    """Test edge case generation methods"""

    def test_make_unicode_action(self):
        """make_unicode_action generates action with unicode"""
        action = AuditTestDataFactory.make_unicode_action()
        # Should contain non-ASCII characters
        assert any(ord(c) > 127 for c in action)

    def test_make_special_chars_action(self):
        """make_special_chars_action generates action with special chars"""
        action = AuditTestDataFactory.make_special_chars_action()
        special_chars = "!@#$%^&*(){}[]|\\:\";<>?,./~`"
        assert any(c in action for c in special_chars)

    def test_make_max_length_action(self):
        """make_max_length_action generates max length action"""
        action = AuditTestDataFactory.make_max_length_action()
        assert len(action) >= 200  # At or near max length

    def test_make_min_length_action(self):
        """make_min_length_action generates minimal action"""
        action = AuditTestDataFactory.make_min_length_action()
        assert len(action) == 1

    def test_make_batch_audit_event_ids(self):
        """make_batch_audit_event_ids generates multiple unique IDs"""
        ids = AuditTestDataFactory.make_batch_audit_event_ids(count=10)
        assert len(ids) == 10
        assert len(set(ids)) == 10  # All unique

    def test_make_batch_create_requests(self):
        """make_batch_create_requests generates multiple requests"""
        requests = AuditTestDataFactory.make_batch_create_requests(count=5)
        assert len(requests) == 5
        assert all(isinstance(r, AuditEventCreateRequestContract) for r in requests)
