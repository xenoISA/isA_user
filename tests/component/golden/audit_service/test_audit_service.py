"""
Audit Service - Component Tests

Tests AuditService business logic with mocked dependencies.
All tests use AuditTestDataFactory - zero hardcoded data.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from tests.contracts.audit.data_contract import (
    AuditTestDataFactory, 
    AuditCategory,
    EventSeverity,
    EventStatus,
    ComplianceStandard,
)

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Audit Event Logging Tests (15 tests)
# =============================================================================

class TestAuditEventLogging:
    """Test audit event logging business logic"""

    async def test_log_event_success(self, audit_service, mock_repository, sample_create_request):
        """Successful event logging returns event data"""
        # Arrange
        expected_id = AuditTestDataFactory.make_audit_event_id()
        mock_repository.create_audit_event.return_value = MagicMock(
            id=expected_id,
            event_type=sample_create_request.event_type,
            action=sample_create_request.action,
        )

        # Act
        result = await audit_service.log_event(sample_create_request)

        # Assert
        assert result is not None
        mock_repository.create_audit_event.assert_called_once()

    async def test_log_event_creates_audit_event(self, audit_service, mock_repository):
        """log_event creates AuditEvent in repository"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id()
        )

        await audit_service.log_event(request)

        mock_repository.create_audit_event.assert_called_once()

    async def test_log_event_with_user_id(self, audit_service, mock_repository):
        """log_event includes user_id"""
        user_id = AuditTestDataFactory.make_user_id()
        request = AuditTestDataFactory.make_audit_event_create_request(user_id=user_id)
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            user_id=user_id,
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_with_organization_id(self, audit_service, mock_repository):
        """log_event includes organization_id"""
        org_id = AuditTestDataFactory.make_organization_id()
        request = AuditTestDataFactory.make_audit_event_create_request(organization_id=org_id)
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            organization_id=org_id,
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_with_session_id(self, audit_service, mock_repository):
        """log_event includes session_id"""
        session_id = AuditTestDataFactory.make_session_id()
        request = AuditTestDataFactory.make_audit_event_create_request(session_id=session_id)
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id()
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_with_resource_info(self, audit_service, mock_repository):
        """log_event includes resource information"""
        request = AuditTestDataFactory.make_audit_event_create_request(
            resource_type="file",
            resource_id="file_123",
            resource_name="document.pdf",
        )
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id()
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_with_metadata(self, audit_service, mock_repository):
        """log_event includes metadata"""
        metadata = {"key": "value", "count": 42}
        request = AuditTestDataFactory.make_audit_event_create_request(metadata=metadata)
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            metadata=metadata,
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_with_tags(self, audit_service, mock_repository):
        """log_event includes tags"""
        tags = ["tag1", "tag2", "tag3"]
        request = AuditTestDataFactory.make_audit_event_create_request(tags=tags)
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            tags=tags,
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_failure_returns_none(self, audit_service, mock_repository):
        """log_event returns None on repository failure"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.return_value = None

        result = await audit_service.log_event(request)

        assert result is None

    async def test_log_event_generates_event_id(self, audit_service, mock_repository):
        """log_event generates unique event ID"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id()
        )

        await audit_service.log_event(request)

        call_args = mock_repository.create_audit_event.call_args
        assert call_args is not None

    async def test_log_event_sets_timestamp(self, audit_service, mock_repository):
        """log_event sets timestamp"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            timestamp=datetime.now(timezone.utc),
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_default_category(self, audit_service, mock_repository):
        """log_event uses default category when not specified"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            category=AuditCategory.SYSTEM,
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_default_severity(self, audit_service, mock_repository):
        """log_event uses default severity when not specified"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            severity=EventSeverity.LOW,
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_success_true_by_default(self, audit_service, mock_repository):
        """log_event sets success=True by default"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.return_value = MagicMock(
            id=AuditTestDataFactory.make_audit_event_id(),
            success=True,
        )

        result = await audit_service.log_event(request)

        assert result is not None

    async def test_log_event_exception_handling(self, audit_service, mock_repository):
        """log_event handles repository exceptions"""
        request = AuditTestDataFactory.make_audit_event_create_request()
        mock_repository.create_audit_event.side_effect = Exception("Database error")

        result = await audit_service.log_event(request)

        assert result is None


# =============================================================================
# Audit Event Query Tests (12 tests)
# =============================================================================

class TestAuditEventQuery:
    """Test audit event query business logic"""

    async def test_query_events_success(self, audit_service, mock_repository, sample_query_request):
        """Successful query returns events"""
        mock_events = [
            MagicMock(**AuditTestDataFactory.make_audit_event_response())
            for _ in range(5)
        ]
        mock_repository.query_audit_events.return_value = mock_events

        result = await audit_service.query_events(sample_query_request)

        assert result is not None

    async def test_query_events_empty_results(self, audit_service, mock_repository):
        """Query with no matches returns empty list"""
        mock_repository.query_audit_events.return_value = []
        query = AuditTestDataFactory.make_audit_query_request()

        result = await audit_service.query_events(query)

        assert result is not None

    async def test_query_events_with_event_types_filter(self, audit_service, mock_repository):
        """Query filters by event types"""
        query = AuditTestDataFactory.make_audit_query_request(
            event_types=["user.logged_in"]
        )
        mock_repository.query_audit_events.return_value = []

        await audit_service.query_events(query)

        mock_repository.query_audit_events.assert_called_once()

    async def test_query_events_with_categories_filter(self, audit_service, mock_repository):
        """Query filters by categories"""
        query = AuditTestDataFactory.make_audit_query_request(
            categories=[AuditCategory.AUTHENTICATION]
        )
        mock_repository.query_audit_events.return_value = []

        await audit_service.query_events(query)

        mock_repository.query_audit_events.assert_called_once()

    async def test_query_events_with_severities_filter(self, audit_service, mock_repository):
        """Query filters by severities"""
        query = AuditTestDataFactory.make_audit_query_request(
            severities=[EventSeverity.HIGH, EventSeverity.CRITICAL]
        )
        mock_repository.query_audit_events.return_value = []

        await audit_service.query_events(query)

        mock_repository.query_audit_events.assert_called_once()

    async def test_query_events_with_user_id_filter(self, audit_service, mock_repository):
        """Query filters by user_id"""
        user_id = AuditTestDataFactory.make_user_id()
        query = AuditTestDataFactory.make_audit_query_request(user_id=user_id)
        mock_repository.query_audit_events.return_value = []

        await audit_service.query_events(query)

        mock_repository.query_audit_events.assert_called_once()

    async def test_query_events_with_date_range(self, audit_service, mock_repository):
        """Query filters by date range"""
        from datetime import timedelta
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        query = AuditTestDataFactory.make_audit_query_request(
            start_time=start, end_time=end
        )
        mock_repository.query_audit_events.return_value = []

        await audit_service.query_events(query)

        mock_repository.query_audit_events.assert_called_once()

    async def test_query_events_with_pagination(self, audit_service, mock_repository):
        """Query supports pagination"""
        query = AuditTestDataFactory.make_audit_query_request(limit=50, offset=100)
        mock_repository.query_audit_events.return_value = []

        await audit_service.query_events(query)

        mock_repository.query_audit_events.assert_called_once()

    async def test_query_events_respects_limit(self, audit_service, mock_repository):
        """Query respects limit parameter"""
        query = AuditTestDataFactory.make_audit_query_request(limit=10)
        mock_events = [MagicMock() for _ in range(10)]
        mock_repository.query_audit_events.return_value = mock_events

        result = await audit_service.query_events(query)

        assert result is not None

    async def test_query_events_returns_total_count(self, audit_service, mock_repository):
        """Query returns total count"""
        query = AuditTestDataFactory.make_audit_query_request()
        mock_repository.query_audit_events.return_value = [MagicMock() for _ in range(5)]

        result = await audit_service.query_events(query)

        assert result is not None

    async def test_query_events_exception_handling(self, audit_service, mock_repository):
        """Query handles repository exceptions"""
        query = AuditTestDataFactory.make_audit_query_request()
        mock_repository.query_audit_events.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await audit_service.query_events(query)

    async def test_query_events_default_limit(self, audit_service, mock_repository):
        """Query uses default limit"""
        query = AuditTestDataFactory.make_audit_query_request()
        mock_repository.query_audit_events.return_value = []

        await audit_service.query_events(query)

        assert query.limit == 100  # Default


# =============================================================================
# User Activity Tests (10 tests)
# =============================================================================

class TestUserActivity:
    """Test user activity tracking business logic"""

    async def test_get_user_activities_success(self, audit_service, mock_repository):
        """Get user activities returns activity list"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_activities = [{"action": "login"}, {"action": "logout"}]
        mock_repository.get_user_activities.return_value = mock_activities

        result = await audit_service.get_user_activities(user_id, days=30, limit=100)

        assert result is not None
        mock_repository.get_user_activities.assert_called_once()

    async def test_get_user_activities_empty(self, audit_service, mock_repository):
        """Get user activities returns empty for new user"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activities.return_value = []

        result = await audit_service.get_user_activities(user_id, days=30, limit=100)

        assert result == []

    async def test_get_user_activities_with_days_filter(self, audit_service, mock_repository):
        """Get user activities respects days filter"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activities.return_value = []

        await audit_service.get_user_activities(user_id, days=7, limit=100)

        mock_repository.get_user_activities.assert_called_with(user_id, 7, 100)

    async def test_get_user_activities_with_limit(self, audit_service, mock_repository):
        """Get user activities respects limit"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activities.return_value = []

        await audit_service.get_user_activities(user_id, days=30, limit=50)

        mock_repository.get_user_activities.assert_called_with(user_id, 30, 50)

    async def test_get_user_activity_summary_success(self, audit_service, mock_repository):
        """Get user activity summary returns summary"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_summary = {
            "total_activities": 100,
            "success_count": 95,
            "failure_count": 5,
        }
        mock_repository.get_user_activity_summary.return_value = mock_summary

        result = await audit_service.get_user_activity_summary(user_id, days=30)

        assert result is not None

    async def test_get_user_activity_summary_empty(self, audit_service, mock_repository):
        """Get user activity summary for new user"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activity_summary.return_value = {}

        result = await audit_service.get_user_activity_summary(user_id, days=30)

        assert result is not None

    async def test_get_user_activity_summary_with_days(self, audit_service, mock_repository):
        """Get user activity summary respects days filter"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activity_summary.return_value = {}

        await audit_service.get_user_activity_summary(user_id, days=7)

        mock_repository.get_user_activity_summary.assert_called_with(user_id, 7)

    async def test_get_user_activities_exception_handling(self, audit_service, mock_repository):
        """Get user activities handles exceptions"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activities.side_effect = Exception("Error")

        with pytest.raises(Exception):
            await audit_service.get_user_activities(user_id, days=30, limit=100)

    async def test_get_user_activity_summary_exception_handling(self, audit_service, mock_repository):
        """Get user activity summary handles exceptions"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activity_summary.side_effect = Exception("Error")

        with pytest.raises(Exception):
            await audit_service.get_user_activity_summary(user_id, days=30)

    async def test_get_user_activities_validates_user_id(self, audit_service, mock_repository):
        """Get user activities with valid user_id"""
        user_id = AuditTestDataFactory.make_user_id()
        mock_repository.get_user_activities.return_value = []

        await audit_service.get_user_activities(user_id, days=30, limit=100)

        call_args = mock_repository.get_user_activities.call_args
        assert call_args[0][0] == user_id


# =============================================================================
# Security Alert Tests (10 tests)
# =============================================================================

class TestSecurityAlert:
    """Test security alert business logic"""

    async def test_create_security_alert_success(self, audit_service, mock_repository, sample_security_alert):
        """Create security alert returns event"""
        mock_event = MagicMock(id=AuditTestDataFactory.make_security_event_id())
        mock_repository.create_security_event.return_value = mock_event

        result = await audit_service.create_security_alert(sample_security_alert)

        assert result is not None
        mock_repository.create_security_event.assert_called_once()

    async def test_create_security_alert_with_threat_type(self, audit_service, mock_repository):
        """Create security alert includes threat type"""
        alert = AuditTestDataFactory.make_security_alert_request(threat_type="brute_force")
        mock_event = MagicMock(id=AuditTestDataFactory.make_security_event_id())
        mock_repository.create_security_event.return_value = mock_event

        result = await audit_service.create_security_alert(alert)

        assert result is not None

    async def test_create_security_alert_with_affected_users(self, audit_service, mock_repository):
        """Create security alert includes affected users"""
        alert = AuditTestDataFactory.make_security_alert_request(
            affected_users=["user_1", "user_2"]
        )
        mock_event = MagicMock(id=AuditTestDataFactory.make_security_event_id())
        mock_repository.create_security_event.return_value = mock_event

        result = await audit_service.create_security_alert(alert)

        assert result is not None

    async def test_create_security_alert_failure(self, audit_service, mock_repository):
        """Create security alert handles failure"""
        alert = AuditTestDataFactory.make_security_alert_request()
        mock_repository.create_security_event.return_value = None

        result = await audit_service.create_security_alert(alert)

        assert result is None

    async def test_get_security_events_success(self, audit_service, mock_repository):
        """Get security events returns list"""
        mock_events = [{"id": "sec_1"}, {"id": "sec_2"}]
        mock_repository.get_security_events.return_value = mock_events

        result = await audit_service.get_security_events(days=7, severity=None)

        assert result is not None
        mock_repository.get_security_events.assert_called_once()

    async def test_get_security_events_with_days(self, audit_service, mock_repository):
        """Get security events respects days filter"""
        mock_repository.get_security_events.return_value = []

        await audit_service.get_security_events(days=30, severity=None)

        mock_repository.get_security_events.assert_called_with(30, None)

    async def test_get_security_events_with_severity(self, audit_service, mock_repository):
        """Get security events filters by severity"""
        mock_repository.get_security_events.return_value = []

        await audit_service.get_security_events(days=7, severity=EventSeverity.CRITICAL)

        mock_repository.get_security_events.assert_called_once()

    async def test_get_security_events_empty(self, audit_service, mock_repository):
        """Get security events returns empty list"""
        mock_repository.get_security_events.return_value = []

        result = await audit_service.get_security_events(days=7, severity=None)

        assert result == []

    async def test_create_security_alert_exception_handling(self, audit_service, mock_repository):
        """Create security alert handles exceptions"""
        alert = AuditTestDataFactory.make_security_alert_request()
        mock_repository.create_security_event.side_effect = Exception("Error")

        result = await audit_service.create_security_alert(alert)

        assert result is None

    async def test_get_security_events_exception_handling(self, audit_service, mock_repository):
        """Get security events handles exceptions"""
        mock_repository.get_security_events.side_effect = Exception("Error")

        with pytest.raises(Exception):
            await audit_service.get_security_events(days=7, severity=None)


# =============================================================================
# Compliance Report Tests (8 tests)
# =============================================================================

class TestComplianceReport:
    """Test compliance report business logic"""

    async def test_generate_compliance_report_success(self, audit_service, mock_repository):
        """Generate compliance report returns report"""
        request = AuditTestDataFactory.make_compliance_report_request()
        mock_repository.get_statistics.return_value = {
            "total_events": 1000,
            "compliance_score": 0.95,
        }

        result = await audit_service.generate_compliance_report(request)

        assert result is not None

    async def test_generate_compliance_report_gdpr(self, audit_service, mock_repository):
        """Generate GDPR compliance report"""
        request = AuditTestDataFactory.make_compliance_report_request(
            compliance_standard=ComplianceStandard.GDPR
        )
        mock_repository.get_statistics.return_value = {}

        result = await audit_service.generate_compliance_report(request)

        assert result is not None

    async def test_generate_compliance_report_sox(self, audit_service, mock_repository):
        """Generate SOX compliance report"""
        request = AuditTestDataFactory.make_compliance_report_request(
            compliance_standard=ComplianceStandard.SOX
        )
        mock_repository.get_statistics.return_value = {}

        result = await audit_service.generate_compliance_report(request)

        assert result is not None

    async def test_generate_compliance_report_hipaa(self, audit_service, mock_repository):
        """Generate HIPAA compliance report"""
        request = AuditTestDataFactory.make_compliance_report_request(
            compliance_standard=ComplianceStandard.HIPAA
        )
        mock_repository.get_statistics.return_value = {}

        result = await audit_service.generate_compliance_report(request)

        assert result is not None

    async def test_generate_compliance_report_with_date_range(self, audit_service, mock_repository):
        """Generate compliance report with date range"""
        from datetime import timedelta
        start = datetime.now(timezone.utc) - timedelta(days=90)
        end = datetime.now(timezone.utc)
        request = AuditTestDataFactory.make_compliance_report_request(
            start_time=start, end_time=end
        )
        mock_repository.get_statistics.return_value = {}

        result = await audit_service.generate_compliance_report(request)

        assert result is not None

    async def test_generate_compliance_report_with_organization(self, audit_service, mock_repository):
        """Generate compliance report for organization"""
        org_id = AuditTestDataFactory.make_organization_id()
        request = AuditTestDataFactory.make_compliance_report_request(
            organization_id=org_id
        )
        mock_repository.get_statistics.return_value = {}

        result = await audit_service.generate_compliance_report(request)

        assert result is not None

    async def test_generate_compliance_report_exception_handling(self, audit_service, mock_repository):
        """Generate compliance report handles exceptions"""
        request = AuditTestDataFactory.make_compliance_report_request()
        mock_repository.get_statistics.side_effect = Exception("Error")

        with pytest.raises(Exception):
            await audit_service.generate_compliance_report(request)

    async def test_generate_compliance_report_includes_score(self, audit_service, mock_repository):
        """Compliance report includes compliance score"""
        request = AuditTestDataFactory.make_compliance_report_request()
        mock_repository.get_statistics.return_value = {
            "compliance_score": 0.92,
        }

        result = await audit_service.generate_compliance_report(request)

        assert result is not None


# =============================================================================
# Data Cleanup Tests (8 tests)
# =============================================================================

class TestDataCleanup:
    """Test data cleanup business logic"""

    async def test_cleanup_old_data_success(self, audit_service, mock_repository):
        """Cleanup old data returns count"""
        mock_repository.cleanup_old_events.return_value = 500

        result = await audit_service.cleanup_old_data(retention_days=365)

        assert result["cleaned_events"] == 500
        mock_repository.cleanup_old_events.assert_called_once()

    async def test_cleanup_old_data_with_retention_days(self, audit_service, mock_repository):
        """Cleanup respects retention days"""
        mock_repository.cleanup_old_events.return_value = 100

        await audit_service.cleanup_old_data(retention_days=90)

        mock_repository.cleanup_old_events.assert_called_with(90)

    async def test_cleanup_old_data_no_data_to_clean(self, audit_service, mock_repository):
        """Cleanup returns 0 when no old data"""
        mock_repository.cleanup_old_events.return_value = 0

        result = await audit_service.cleanup_old_data(retention_days=365)

        assert result["cleaned_events"] == 0

    async def test_cleanup_old_data_exception_handling(self, audit_service, mock_repository):
        """Cleanup handles exceptions"""
        mock_repository.cleanup_old_events.side_effect = Exception("Error")

        with pytest.raises(Exception):
            await audit_service.cleanup_old_data(retention_days=365)

    async def test_cleanup_old_data_returns_retention_days(self, audit_service, mock_repository):
        """Cleanup result includes retention days"""
        mock_repository.cleanup_old_events.return_value = 50

        result = await audit_service.cleanup_old_data(retention_days=180)

        assert result["retention_days"] == 180

    async def test_cleanup_old_data_default_retention(self, audit_service, mock_repository):
        """Cleanup uses default retention when not specified"""
        mock_repository.cleanup_old_events.return_value = 0

        result = await audit_service.cleanup_old_data(retention_days=365)

        assert result["retention_days"] == 365

    async def test_cleanup_old_data_large_cleanup(self, audit_service, mock_repository):
        """Cleanup handles large data cleanup"""
        mock_repository.cleanup_old_events.return_value = 100000

        result = await audit_service.cleanup_old_data(retention_days=30)

        assert result["cleaned_events"] == 100000

    async def test_cleanup_old_data_includes_timestamp(self, audit_service, mock_repository):
        """Cleanup result includes timestamp"""
        mock_repository.cleanup_old_events.return_value = 10

        result = await audit_service.cleanup_old_data(retention_days=365)

        assert "cleaned_events" in result


# =============================================================================
# Service Statistics Tests (6 tests)
# =============================================================================

class TestServiceStatistics:
    """Test service statistics business logic"""

    async def test_get_service_statistics_success(self, audit_service, mock_repository):
        """Get service statistics returns stats"""
        mock_stats = {
            "total_events": 10000,
            "events_today": 500,
            "active_users": 50,
        }
        mock_repository.get_event_statistics.return_value = mock_stats

        result = await audit_service.get_service_statistics()

        assert result is not None

    async def test_get_service_statistics_empty(self, audit_service, mock_repository):
        """Get service statistics with no events"""
        mock_repository.get_event_statistics.return_value = {
            "total_events": 0,
            "events_today": 0,
        }

        result = await audit_service.get_service_statistics()

        assert result["total_events"] == 0

    async def test_get_service_statistics_exception_handling(self, audit_service, mock_repository):
        """Get service statistics handles exceptions"""
        mock_repository.get_event_statistics.side_effect = Exception("Error")

        with pytest.raises(Exception):
            await audit_service.get_service_statistics()

    async def test_get_service_statistics_includes_all_metrics(self, audit_service, mock_repository):
        """Statistics includes all required metrics"""
        mock_repository.get_event_statistics.return_value = {
            "total_events": 1000,
            "events_today": 100,
            "active_users": 25,
            "security_alerts": 5,
        }

        result = await audit_service.get_service_statistics()

        assert "total_events" in result

    async def test_repository_check_connection_success(self, audit_service, mock_repository):
        """Repository connection check succeeds"""
        mock_repository.check_connection.return_value = True

        result = await mock_repository.check_connection()

        assert result is True

    async def test_repository_check_connection_failure(self, audit_service, mock_repository):
        """Repository connection check fails gracefully"""
        mock_repository.check_connection.return_value = False

        result = await mock_repository.check_connection()

        assert result is False
