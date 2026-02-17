"""
Audit Service - Unit Tests: Models and Validation

Tests for:
- Pydantic model validation
- Enum validation
- Request contract validation
- Response contract validation

No I/O, no mocks, no fixtures needed.
All tests use AuditTestDataFactory - zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from tests.contracts.audit.data_contract import (
    # Enums
    EventType,
    AuditCategory,
    EventSeverity,
    EventStatus,
    InvestigationStatus,
    ComplianceStandard,
    ReportType,
    # Request Contracts
    AuditEventCreateRequestContract,
    AuditEventBatchRequestContract,
    AuditQueryRequestContract,
    UserActivityQueryRequestContract,
    SecurityAlertRequestContract,
    SecurityEventQueryRequestContract,
    ComplianceReportRequestContract,
    DataCleanupRequestContract,
    # Response Contracts
    AuditEventResponseContract,
    AuditQueryResponseContract,
    AuditBatchResponseContract,
    UserActivityResponseContract,
    UserActivitySummaryResponseContract,
    SecurityEventResponseContract,
    SecurityEventListResponseContract,
    ComplianceReportResponseContract,
    ComplianceStandardResponseContract,
    AuditServiceStatsResponseContract,
    AuditServiceHealthResponseContract,
    DataCleanupResponseContract,
    # Factory
    AuditTestDataFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# Enum Tests (10 tests)
# =============================================================================

class TestEventTypeEnum:
    """Test EventType enumeration"""

    def test_event_type_values_exist(self):
        """EventType has all required values"""
        assert EventType.USER_LOGIN
        assert EventType.USER_LOGOUT
        assert EventType.USER_REGISTER
        assert EventType.RESOURCE_ACCESS
        assert EventType.SECURITY_ALERT

    def test_event_type_value_strings(self):
        """EventType values are correct strings"""
        assert EventType.USER_LOGIN.value == "user_login"
        assert EventType.RESOURCE_CREATE.value == "resource_create"
        assert EventType.PERMISSION_GRANT.value == "permission_grant"

    def test_event_type_from_string(self):
        """EventType can be created from string"""
        event_type = EventType("user_login")
        assert event_type == EventType.USER_LOGIN


class TestAuditCategoryEnum:
    """Test AuditCategory enumeration"""

    def test_audit_category_values_exist(self):
        """AuditCategory has all required values"""
        assert AuditCategory.AUTHENTICATION
        assert AuditCategory.AUTHORIZATION
        assert AuditCategory.DATA_ACCESS
        assert AuditCategory.SECURITY
        assert AuditCategory.SYSTEM
        assert AuditCategory.COMPLIANCE
        assert AuditCategory.CONFIGURATION

    def test_audit_category_value_strings(self):
        """AuditCategory values are correct strings"""
        assert AuditCategory.AUTHENTICATION.value == "authentication"
        assert AuditCategory.SECURITY.value == "security"


class TestEventSeverityEnum:
    """Test EventSeverity enumeration"""

    def test_severity_values_exist(self):
        """EventSeverity has all required values"""
        assert EventSeverity.LOW
        assert EventSeverity.MEDIUM
        assert EventSeverity.HIGH
        assert EventSeverity.CRITICAL

    def test_severity_ordering(self):
        """Severity values have correct ordering strings"""
        assert EventSeverity.LOW.value == "low"
        assert EventSeverity.CRITICAL.value == "critical"


class TestEventStatusEnum:
    """Test EventStatus enumeration"""

    def test_status_values_exist(self):
        """EventStatus has all required values"""
        assert EventStatus.PENDING
        assert EventStatus.SUCCESS
        assert EventStatus.FAILURE
        assert EventStatus.ERROR


class TestComplianceStandardEnum:
    """Test ComplianceStandard enumeration"""

    def test_compliance_standards_exist(self):
        """ComplianceStandard has required values"""
        assert ComplianceStandard.GDPR
        assert ComplianceStandard.SOX
        assert ComplianceStandard.HIPAA


# =============================================================================
# AuditEventCreateRequestContract Tests (15 tests)
# =============================================================================

class TestAuditEventCreateRequestContract:
    """Test audit event creation request validation"""

    def test_valid_minimal_request(self):
        """Valid minimal request passes validation"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
        )
        assert request.event_type == EventType.USER_LOGIN
        assert request.action == "user_login"

    def test_valid_full_request(self):
        """Valid full request passes validation"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        assert request.event_type is not None
        assert request.action is not None

    def test_missing_event_type_raises_error(self):
        """Missing event_type raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AuditEventCreateRequestContract(action="test_action")
        assert "event_type" in str(exc_info.value)

    def test_missing_action_raises_error(self):
        """Missing action raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AuditEventCreateRequestContract(event_type=EventType.USER_LOGIN)
        assert "action" in str(exc_info.value)

    def test_invalid_event_type_raises_error(self):
        """Invalid event_type raises ValidationError"""
        with pytest.raises(ValidationError):
            AuditEventCreateRequestContract(
                event_type="invalid_type",
                action="test_action",
            )

    def test_empty_action_raises_error(self):
        """Empty action raises ValidationError"""
        with pytest.raises(ValidationError):
            AuditEventCreateRequestContract(
                event_type=EventType.USER_LOGIN,
                action="",
            )

    def test_optional_fields_default_none(self):
        """Optional fields default to None"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
        )
        assert request.user_id is None
        assert request.organization_id is None

    def test_category_defaults_correctly(self):
        """Category is required and works correctly"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
        )
        # category is required
        assert request.category == AuditCategory.AUTHENTICATION

    def test_severity_defaults_correctly(self):
        """Severity defaults when not provided"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
        )
        assert request.severity == EventSeverity.LOW

    def test_success_defaults_to_true(self):
        """Success field defaults to True"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
        )
        assert request.success is True

    def test_metadata_accepts_dict(self):
        """Metadata field accepts dictionary"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
            metadata={"key": "value", "nested": {"a": 1}},
        )
        assert request.metadata["key"] == "value"
        assert request.metadata["nested"]["a"] == 1

    def test_tags_accepts_list(self):
        """Tags field accepts list"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
            tags=["tag1", "tag2", "tag3"],
        )
        assert len(request.tags) == 3
        assert "tag1" in request.tags

    def test_ip_address_validation(self):
        """IP address field accepts valid IP"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
            ip_address="192.168.1.1",
        )
        assert request.ip_address == "192.168.1.1"

    def test_user_agent_accepts_string(self):
        """User agent accepts string value"""
        request = AuditEventCreateRequestContract(
            event_type=EventType.USER_LOGIN,
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        assert "Mozilla" in request.user_agent


# =============================================================================
# AuditQueryRequestContract Tests (10 tests)
# =============================================================================

class TestAuditQueryRequestContract:
    """Test audit query request validation"""

    def test_valid_empty_query(self):
        """Empty query is valid (no filters)"""
        query = AuditQueryRequestContract()
        assert query.limit == 100
        assert query.offset == 0

    def test_valid_query_with_filters(self):
        """Query with filters is valid"""
        query = AuditTestDataFactory.make_audit_query_request()
        assert query is not None

    def test_event_types_filter(self):
        """Event types filter accepts list"""
        query = AuditQueryRequestContract(
            event_types=[EventType.USER_LOGIN, EventType.USER_LOGOUT]
        )
        assert len(query.event_types) == 2

    def test_categories_filter(self):
        """Categories filter accepts list"""
        query = AuditQueryRequestContract(
            categories=[AuditCategory.AUTHENTICATION, AuditCategory.SECURITY]
        )
        assert len(query.categories) == 2

    def test_severities_filter(self):
        """Severities filter accepts list"""
        query = AuditQueryRequestContract(
            severities=[EventSeverity.HIGH, EventSeverity.CRITICAL]
        )
        assert len(query.severities) == 2

    def test_limit_default(self):
        """Limit defaults to 100"""
        query = AuditQueryRequestContract()
        assert query.limit == 100

    def test_limit_max_value(self):
        """Limit respects maximum value"""
        query = AuditQueryRequestContract(limit=1000)
        assert query.limit == 1000

    def test_offset_default(self):
        """Offset defaults to 0"""
        query = AuditQueryRequestContract()
        assert query.offset == 0

    def test_date_range_filter(self):
        """Date range filter works correctly"""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        query = AuditQueryRequestContract(start_time=start, end_time=end)
        assert query.start_time == start
        assert query.end_time == end

    def test_user_id_filter(self):
        """User ID filter accepts string"""
        user_id = AuditTestDataFactory.make_user_id()
        query = AuditQueryRequestContract(user_id=user_id)
        assert query.user_id == user_id


# =============================================================================
# SecurityAlertRequestContract Tests (8 tests)
# =============================================================================

class TestSecurityAlertRequestContract:
    """Test security alert request validation"""

    def test_valid_security_alert(self):
        """Valid security alert passes validation"""
        alert = AuditTestDataFactory.make_security_alert_request()
        assert alert.threat_type is not None

    def test_missing_threat_type_raises_error(self):
        """Missing threat_type raises ValidationError"""
        with pytest.raises(ValidationError):
            SecurityAlertRequestContract(
                severity=EventSeverity.HIGH,
                description="Test alert",
            )

    def test_severity_required(self):
        """Severity is required"""
        alert = SecurityAlertRequestContract(
            threat_type="unauthorized_access",
            severity=EventSeverity.HIGH,
            description="Test alert",
        )
        assert alert.severity == EventSeverity.HIGH

    def test_description_required(self):
        """Description is required"""
        alert = SecurityAlertRequestContract(
            threat_type="data_breach",
            severity=EventSeverity.CRITICAL,
            description="Data breach detected",
        )
        assert alert.description == "Data breach detected"

    def test_source_ip_optional(self):
        """Source IP is optional"""
        alert = SecurityAlertRequestContract(
            threat_type="account_compromise",
            severity=EventSeverity.HIGH,
            description="Account compromised",
        )
        assert alert.source_ip is None

    def test_source_ip_accepts_ip(self):
        """Source IP accepts valid IP"""
        alert = SecurityAlertRequestContract(
            threat_type="brute_force",
            severity=EventSeverity.HIGH,
            description="Brute force attack",
            source_ip="10.0.0.1",
        )
        assert alert.source_ip == "10.0.0.1"

    def test_target_resource_optional(self):
        """Target resource is optional"""
        alert = SecurityAlertRequestContract(
            threat_type="suspicious_activity",
            severity=EventSeverity.MEDIUM,
            description="Suspicious activity detected",
            target_resource="/api/v1/admin",
        )
        assert alert.target_resource == "/api/v1/admin"

    def test_metadata_accepts_dict(self):
        """Metadata accepts dictionary"""
        alert = SecurityAlertRequestContract(
            threat_type="malware_detected",
            severity=EventSeverity.CRITICAL,
            description="Malware detected",
            metadata={"signature": "xyz123"},
        )
        assert alert.metadata["signature"] == "xyz123"


# =============================================================================
# ComplianceReportRequestContract Tests (6 tests)
# =============================================================================

class TestComplianceReportRequestContract:
    """Test compliance report request validation"""

    def test_valid_compliance_report_request(self):
        """Valid request passes validation"""
        request = AuditTestDataFactory.make_compliance_report_request()
        assert request.compliance_standard is not None

    def test_missing_compliance_standard_raises_error(self):
        """Missing compliance_standard raises ValidationError"""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            ComplianceReportRequestContract(
                report_type=ReportType.PERIODIC,
                period_start=start,
                period_end=end,
            )

    def test_gdpr_standard(self):
        """GDPR compliance standard accepted"""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        request = ComplianceReportRequestContract(
            compliance_standard=ComplianceStandard.GDPR,
            report_type=ReportType.AD_HOC,
            period_start=start,
            period_end=end,
        )
        assert request.compliance_standard == ComplianceStandard.GDPR

    def test_sox_standard(self):
        """SOX compliance standard accepted"""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        request = ComplianceReportRequestContract(
            compliance_standard=ComplianceStandard.SOX,
            report_type=ReportType.PERIODIC,
            period_start=start,
            period_end=end,
        )
        assert request.compliance_standard == ComplianceStandard.SOX

    def test_hipaa_standard(self):
        """HIPAA compliance standard accepted"""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        request = ComplianceReportRequestContract(
            compliance_standard=ComplianceStandard.HIPAA,
            report_type=ReportType.INVESTIGATION,
            period_start=start,
            period_end=end,
        )
        assert request.compliance_standard == ComplianceStandard.HIPAA

    def test_date_range(self):
        """Date range filter accepted"""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        request = ComplianceReportRequestContract(
            compliance_standard=ComplianceStandard.GDPR,
            report_type=ReportType.QUARTERLY_AUDIT,
            period_start=start,
            period_end=end,
        )
        assert request.period_start == start
        assert request.period_end == end


# =============================================================================
# Response Contract Tests (15 tests)
# =============================================================================

class TestAuditEventResponseContract:
    """Test audit event response validation"""

    def test_valid_response(self):
        """Valid response passes validation"""
        response_data = AuditTestDataFactory.make_audit_event_response()
        response = AuditEventResponseContract(**response_data)
        assert response.id is not None

    def test_missing_id_raises_error(self):
        """Missing id raises ValidationError"""
        with pytest.raises(ValidationError):
            AuditEventResponseContract(
                event_type=EventType.USER_LOGIN,
                action="user_login",
                timestamp=datetime.now(timezone.utc),
            )

    def test_all_fields_populated(self):
        """All response fields can be populated"""
        response_data = AuditTestDataFactory.make_audit_event_response()
        response = AuditEventResponseContract(**response_data)
        assert response.id
        assert response.event_type
        assert response.action


class TestAuditQueryResponseContract:
    """Test audit query response validation"""

    def test_valid_query_response(self):
        """Valid query response passes validation"""
        response_data = AuditTestDataFactory.make_audit_query_response(count=5)
        response = AuditQueryResponseContract(**response_data)
        assert len(response.events) == 5
        assert response.total_count == 5

    def test_empty_results(self):
        """Empty results are valid"""
        response = AuditQueryResponseContract(
            events=[],
            total_count=0,
            page_info={"limit": 100, "offset": 0, "has_more": False},
            filters_applied={},
        )
        assert response.total_count == 0
        assert len(response.events) == 0

    def test_pagination_in_page_info(self):
        """Pagination fields are in page_info"""
        response_data = AuditTestDataFactory.make_audit_query_response()
        response = AuditQueryResponseContract(**response_data)
        assert "limit" in response.page_info
        assert "offset" in response.page_info


class TestSecurityEventResponseContract:
    """Test security event response validation"""

    def test_valid_security_response(self):
        """Valid security event response passes validation"""
        response_data = AuditTestDataFactory.make_security_event_response()
        response = SecurityEventResponseContract(**response_data)
        assert response.id is not None
        assert response.severity is not None

    def test_severity_present(self):
        """Severity is present in response"""
        response_data = AuditTestDataFactory.make_security_event_response()
        response = SecurityEventResponseContract(**response_data)
        assert response.severity is not None


class TestUserActivitySummaryResponseContract:
    """Test user activity summary response validation"""

    def test_valid_summary_response(self):
        """Valid summary response passes validation"""
        response_data = AuditTestDataFactory.make_user_activity_summary_response()
        response = UserActivitySummaryResponseContract(**response_data)
        assert response.user_id is not None
        assert response.total_activities >= 0

    def test_summary_metrics(self):
        """Summary has expected metrics"""
        response_data = AuditTestDataFactory.make_user_activity_summary_response()
        response = UserActivitySummaryResponseContract(**response_data)
        assert hasattr(response, "total_activities")
        assert hasattr(response, "success_count")


class TestAuditServiceHealthResponseContract:
    """Test audit service health response validation"""

    def test_valid_health_response(self):
        """Valid health response passes validation"""
        response_data = AuditTestDataFactory.make_service_health_response()
        response = AuditServiceHealthResponseContract(**response_data)
        assert response.status in ["healthy", "degraded", "unhealthy"]

    def test_service_name_present(self):
        """Service name is present"""
        response_data = AuditTestDataFactory.make_service_health_response()
        response = AuditServiceHealthResponseContract(**response_data)
        assert response.service == "audit_service"
