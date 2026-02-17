"""
Audit Service Component Golden Tests

These tests document CURRENT AuditService behavior with mocked deps.
Uses proper dependency injection - no patching needed!

Usage:
    pytest tests/component/golden/test_audit_service_golden.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from tests.component.golden.audit_service.mocks import MockAuditRepository
from tests.component.golden.audit_service.conftest import MockEventBus

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Create a fresh MockAuditRepository"""
    return MockAuditRepository()


@pytest.fixture
def mock_repo_with_events():
    """Create MockAuditRepository with existing events"""
    from microservices.audit_service.models import EventType, AuditCategory, EventSeverity

    repo = MockAuditRepository()
    repo.set_event(
        event_id="evt_001",
        event_type="user.logged_in",
        category=AuditCategory.AUTHENTICATION,
        severity=EventSeverity.LOW,
        action="user_login",
        user_id="usr_123"
    )
    repo.set_event(
        event_id="evt_002",
        event_type="audit.resource.update",
        category=AuditCategory.DATA_ACCESS,
        severity=EventSeverity.MEDIUM,
        action="update_document",
        user_id="usr_123",
        resource_type="document",
        resource_id="doc_456"
    )
    return repo


# =============================================================================
# AuditService.log_event() Tests
# =============================================================================

class TestAuditServiceLogEventGolden:
    """Golden: AuditService.log_event() current behavior"""

    async def test_log_event_creates_audit_event(self, mock_repo):
        """GOLDEN: log_event creates audit event and returns response"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import (
            AuditEventCreateRequest, AuditEventResponse,  AuditCategory, EventSeverity
        )

        service = AuditService(repository=mock_repo)
        request = AuditEventCreateRequest(
            event_type="user.logged_in",
            category=AuditCategory.AUTHENTICATION,
            severity=EventSeverity.LOW,
            action="user_login",
            user_id="usr_123",
            ip_address="192.168.1.1"
        )

        result = await service.log_event(request)

        assert result is not None
        assert isinstance(result, AuditEventResponse)
        assert result.event_type == "user.logged_in"
        assert result.action == "user_login"
        assert result.user_id == "usr_123"

        # Verify repository was called
        mock_repo.assert_called("create_audit_event")

    async def test_log_event_handles_failure_status(self, mock_repo):
        """GOLDEN: log_event correctly handles failure status"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import (
            AuditEventCreateRequest,  AuditCategory, EventSeverity
        )

        service = AuditService(repository=mock_repo)
        request = AuditEventCreateRequest(
            event_type="user.logged_in",
            category=AuditCategory.AUTHENTICATION,
            action="user_login",
            success=False,
            error_message="Invalid credentials"
        )

        result = await service.log_event(request)

        assert result is not None
        assert result.success is False

    async def test_log_event_returns_none_on_repository_error(self, mock_repo):
        """GOLDEN: log_event returns None when repository fails"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import (
            AuditEventCreateRequest,  AuditCategory
        )

        mock_repo.set_error(Exception("Database error"))

        service = AuditService(repository=mock_repo)
        request = AuditEventCreateRequest(
            event_type="user.logged_in",
            category=AuditCategory.AUTHENTICATION,
            action="login"
        )

        result = await service.log_event(request)

        assert result is None


# =============================================================================
# AuditService.query_events() Tests
# =============================================================================

class TestAuditServiceQueryEventsGolden:
    """Golden: AuditService.query_events() current behavior"""

    async def test_query_events_returns_response(self, mock_repo_with_events):
        """GOLDEN: query_events returns AuditQueryResponse"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import AuditQueryRequest, AuditQueryResponse

        service = AuditService(repository=mock_repo_with_events)
        query = AuditQueryRequest(user_id="usr_123", limit=10)

        result = await service.query_events(query)

        assert isinstance(result, AuditQueryResponse)
        assert result.total_count >= 0
        assert "events" in result.model_dump()

    async def test_query_events_empty_returns_empty_list(self, mock_repo):
        """GOLDEN: query_events returns empty list when no events"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import AuditQueryRequest

        service = AuditService(repository=mock_repo)
        query = AuditQueryRequest()

        result = await service.query_events(query)

        assert len(result.events) == 0
        assert result.total_count == 0


# =============================================================================
# AuditService.get_user_activities() Tests
# =============================================================================

class TestAuditServiceUserActivitiesGolden:
    """Golden: AuditService.get_user_activities() current behavior"""

    async def test_get_user_activities_returns_list(self, mock_repo_with_events):
        """GOLDEN: get_user_activities returns list of activities"""
        from microservices.audit_service.audit_service import AuditService

        service = AuditService(repository=mock_repo_with_events)
        result = await service.get_user_activities("usr_123", days=30)

        assert isinstance(result, list)
        mock_repo_with_events.assert_called("get_user_activities")

    async def test_get_user_activities_empty_for_unknown_user(self, mock_repo):
        """GOLDEN: get_user_activities returns empty list for unknown user"""
        from microservices.audit_service.audit_service import AuditService

        service = AuditService(repository=mock_repo)
        result = await service.get_user_activities("usr_unknown")

        assert result == []


# =============================================================================
# AuditService.get_user_activity_summary() Tests
# =============================================================================

class TestAuditServiceUserActivitySummaryGolden:
    """Golden: AuditService.get_user_activity_summary() current behavior"""

    async def test_get_activity_summary_returns_summary(self, mock_repo_with_events):
        """GOLDEN: get_user_activity_summary returns UserActivitySummary"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import UserActivitySummary

        service = AuditService(repository=mock_repo_with_events)
        result = await service.get_user_activity_summary("usr_123")

        assert isinstance(result, UserActivitySummary)
        assert result.user_id == "usr_123"

    async def test_get_activity_summary_returns_zeros_for_unknown_user(self, mock_repo):
        """GOLDEN: get_user_activity_summary returns zeros for unknown user"""
        from microservices.audit_service.audit_service import AuditService

        service = AuditService(repository=mock_repo)
        result = await service.get_user_activity_summary("usr_unknown")

        assert result.total_activities == 0
        assert result.success_count == 0


# =============================================================================
# AuditService.create_security_alert() Tests
# =============================================================================

class TestAuditServiceSecurityAlertGolden:
    """Golden: AuditService.create_security_alert() current behavior"""

    async def test_create_security_alert_returns_event(self, mock_repo):
        """GOLDEN: create_security_alert returns SecurityEvent"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import SecurityAlertRequest, EventSeverity

        service = AuditService(repository=mock_repo)
        alert = SecurityAlertRequest(
            threat_type="brute_force",
            severity=EventSeverity.HIGH,
            description="Multiple failed login attempts",
            source_ip="192.168.1.100"
        )

        result = await service.create_security_alert(alert)

        assert result is not None
        mock_repo.assert_called("create_security_event")


# =============================================================================
# AuditService.get_security_events() Tests
# =============================================================================

class TestAuditServiceGetSecurityEventsGolden:
    """Golden: AuditService.get_security_events() current behavior"""

    async def test_get_security_events_returns_list(self, mock_repo):
        """GOLDEN: get_security_events returns list"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import EventType, EventSeverity

        # Add security events
        mock_repo.set_security_event(
            event_id="sec_001",
            event_type="audit.security.alert",
            severity=EventSeverity.HIGH,
            threat_level="high"
        )

        service = AuditService(repository=mock_repo)
        result = await service.get_security_events(days=7)

        assert isinstance(result, list)


# =============================================================================
# AuditService.generate_compliance_report() Tests
# =============================================================================

class TestAuditServiceComplianceReportGolden:
    """Golden: AuditService.generate_compliance_report() current behavior"""

    async def test_generate_report_returns_report(self, mock_repo_with_events):
        """GOLDEN: generate_compliance_report returns ComplianceReport"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import (
            ComplianceReportRequest, ComplianceReport
        )

        service = AuditService(repository=mock_repo_with_events)
        request = ComplianceReportRequest(
            report_type="monthly",
            compliance_standard="GDPR",
            period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2024, 1, 31, tzinfo=timezone.utc)
        )

        result = await service.generate_compliance_report(request)

        assert result is not None
        assert isinstance(result, ComplianceReport)
        assert result.compliance_standard == "GDPR"

    async def test_generate_report_unsupported_standard_returns_none(self, mock_repo):
        """GOLDEN: generate_compliance_report returns None for unsupported standard"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import ComplianceReportRequest

        service = AuditService(repository=mock_repo)
        request = ComplianceReportRequest(
            report_type="monthly",
            compliance_standard="UNKNOWN_STANDARD",
            period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2024, 1, 31, tzinfo=timezone.utc)
        )

        result = await service.generate_compliance_report(request)

        assert result is None


# =============================================================================
# AuditService.get_service_statistics() Tests
# =============================================================================

class TestAuditServiceStatisticsGolden:
    """Golden: AuditService.get_service_statistics() current behavior"""

    async def test_get_stats_returns_dict(self, mock_repo):
        """GOLDEN: get_service_statistics returns dict"""
        from microservices.audit_service.audit_service import AuditService

        mock_repo.set_stats(
            total_events=1000,
            critical_events=5,
            error_events=50,
            failed_events=25
        )

        service = AuditService(repository=mock_repo)
        result = await service.get_service_statistics()

        assert isinstance(result, dict)
        assert "total_events" in result


# =============================================================================
# AuditService.cleanup_old_data() Tests
# =============================================================================

class TestAuditServiceCleanupGolden:
    """Golden: AuditService.cleanup_old_data() current behavior"""

    async def test_cleanup_returns_dict(self, mock_repo):
        """GOLDEN: cleanup_old_data returns dict with cleaned count"""
        from microservices.audit_service.audit_service import AuditService

        service = AuditService(repository=mock_repo)
        result = await service.cleanup_old_data(retention_days=365)

        assert isinstance(result, dict)
        assert "cleaned_events" in result
        assert "retention_days" in result
        assert result["retention_days"] == 365


# =============================================================================
# AuditService Error Handling Tests
# =============================================================================

class TestAuditServiceErrorHandlingGolden:
    """Golden: AuditService error handling current behavior"""

    async def test_query_events_returns_empty_on_error(self, mock_repo):
        """GOLDEN: query_events returns empty response on error"""
        from microservices.audit_service.audit_service import AuditService
        from microservices.audit_service.models import AuditQueryRequest

        mock_repo.set_error(Exception("Database error"))

        service = AuditService(repository=mock_repo)
        query = AuditQueryRequest()

        result = await service.query_events(query)

        assert len(result.events) == 0

    async def test_get_statistics_returns_defaults_on_error(self, mock_repo):
        """GOLDEN: get_service_statistics returns defaults on error"""
        from microservices.audit_service.audit_service import AuditService

        mock_repo.set_error(Exception("Database error"))

        service = AuditService(repository=mock_repo)
        result = await service.get_service_statistics()

        assert result["total_events"] == 0
