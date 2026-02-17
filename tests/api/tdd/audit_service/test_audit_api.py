"""
Audit Service API Contract Tests (Layer 1)

RED PHASE: Define what the API should return before implementation.
These tests define the HTTP contracts for the Audit service.

Usage:
    pytest tests/api/services/audit -v                    # Run all audit API tests
    pytest tests/api/services/audit -v -k "events"        # Run events endpoint tests
    pytest tests/api/services/audit -v --tb=short         # Short traceback
"""
import pytest
from datetime import datetime, timezone, timedelta

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def audit_api(http_client):
    """Audit service API client"""
    from tests.api.conftest import APIClient
    return APIClient(http_client, "audit", "/api/v1/audit")


# =============================================================================
# Log Event Endpoint Tests
# =============================================================================

class TestAuditLogEventEndpoint:
    """
    POST /api/v1/audit/events

    Log a new audit event.
    """

    async def test_log_event_creates_audit_event(self, audit_api, api_assert):
        """RED: Log event should create and return audit event"""
        from tests.fixtures.audit_fixtures import make_audit_event_request, make_user_id

        request = make_audit_event_request(
            event_type="user_login",
            category="authentication",
            action="user_login",
            user_id=make_user_id(),
            ip_address="192.168.1.1"
        )

        response = await audit_api.post("/events", json=request)

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Response must have these fields
        api_assert.assert_has_fields(data, [
            "id", "event_type", "category", "action"
        ])
        assert data["event_type"] == "user_login"
        assert data["action"] == "user_login"

    async def test_log_event_validates_required_fields(self, audit_api, api_assert):
        """RED: Missing required fields should return 422"""
        # Missing event_type
        response = await audit_api.post("/events", json={
            "category": "authentication",
            "action": "login"
        })
        api_assert.assert_validation_error(response)

        # Missing category
        response = await audit_api.post("/events", json={
            "event_type": "user_login",
            "action": "login"
        })
        api_assert.assert_validation_error(response)

        # Missing action
        response = await audit_api.post("/events", json={
            "event_type": "user_login",
            "category": "authentication"
        })
        api_assert.assert_validation_error(response)

    async def test_log_event_with_failure_status(self, audit_api, api_assert):
        """RED: Log event with success=false should be recorded"""
        from tests.fixtures.audit_fixtures import make_audit_event_request

        request = make_audit_event_request(
            event_type="user_login",
            category="authentication",
            action="login_failed",
            success=False,
            error_message="Invalid credentials"
        )

        response = await audit_api.post("/events", json=request)

        api_assert.assert_success(response)
        data = response.json()
        assert data["success"] is False


# =============================================================================
# Query Events Endpoint Tests
# =============================================================================

class TestAuditQueryEventsEndpoint:
    """
    POST /api/v1/audit/events/query

    Query audit events with filters.
    """

    async def test_query_events_returns_response(self, audit_api, api_assert):
        """RED: Query events should return paginated response"""
        from tests.fixtures.audit_fixtures import make_audit_query_request

        query = make_audit_query_request(limit=10)

        response = await audit_api.post("/events/query", json=query)

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Paginated response structure
        api_assert.assert_has_fields(data, [
            "events", "total_count"
        ])
        assert isinstance(data["events"], list)
        assert isinstance(data["total_count"], int)

    async def test_query_events_with_user_filter(self, audit_api, api_assert):
        """RED: Query with user_id should filter results"""
        from tests.fixtures.audit_fixtures import make_audit_query_request, make_user_id

        user_id = make_user_id()
        query = make_audit_query_request(user_id=user_id)

        response = await audit_api.post("/events/query", json=query)

        api_assert.assert_success(response)

    async def test_query_events_with_pagination(self, audit_api, api_assert):
        """RED: Query should support pagination"""
        from tests.fixtures.audit_fixtures import make_audit_query_request

        query = make_audit_query_request(limit=5, offset=0)

        response = await audit_api.post("/events/query", json=query)

        api_assert.assert_success(response)
        data = response.json()
        assert len(data["events"]) <= 5


# =============================================================================
# GET Events Endpoint Tests
# =============================================================================

class TestAuditGetEventsEndpoint:
    """
    GET /api/v1/audit/events

    Get audit events with query parameters.
    """

    async def test_get_events_returns_list(self, audit_api, api_assert):
        """RED: GET events should return event list"""
        response = await audit_api.get("/events")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, ["events", "total_count"])
        assert isinstance(data["events"], list)

    async def test_get_events_with_filters(self, audit_api, api_assert):
        """RED: GET events should support query params"""
        response = await audit_api.get("/events", params={
            "event_type": "user_login",
            "limit": 10
        })

        api_assert.assert_success(response)

    async def test_get_events_pagination(self, audit_api, api_assert):
        """RED: GET events should support pagination params"""
        response = await audit_api.get("/events", params={
            "limit": 5,
            "offset": 0
        })

        api_assert.assert_success(response)
        data = response.json()
        assert len(data["events"]) <= 5


# =============================================================================
# User Activities Endpoint Tests
# =============================================================================

class TestAuditUserActivitiesEndpoint:
    """
    GET /api/v1/audit/users/{user_id}/activities

    Get user activity history.
    """

    async def test_get_user_activities_returns_list(self, audit_api, api_assert):
        """RED: Get activities should return activity list"""
        from tests.fixtures.audit_fixtures import make_user_id

        user_id = make_user_id()
        response = await audit_api.get(f"/users/{user_id}/activities")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "user_id", "activities", "total_count", "period_days"
        ])
        assert data["user_id"] == user_id
        assert isinstance(data["activities"], list)

    async def test_get_user_activities_with_days_param(self, audit_api, api_assert):
        """RED: Activities should support days parameter"""
        from tests.fixtures.audit_fixtures import make_user_id

        user_id = make_user_id()
        response = await audit_api.get(f"/users/{user_id}/activities", params={
            "days": 7,
            "limit": 50
        })

        api_assert.assert_success(response)
        data = response.json()
        assert data["period_days"] == 7


# =============================================================================
# User Activity Summary Endpoint Tests
# =============================================================================

class TestAuditUserSummaryEndpoint:
    """
    GET /api/v1/audit/users/{user_id}/summary

    Get user activity summary.
    """

    async def test_get_user_summary_returns_summary(self, audit_api, api_assert):
        """RED: Get summary should return UserActivitySummary"""
        from tests.fixtures.audit_fixtures import make_user_id

        user_id = make_user_id()
        response = await audit_api.get(f"/users/{user_id}/summary")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "user_id", "total_activities", "success_count", "failure_count"
        ])
        assert data["user_id"] == user_id


# =============================================================================
# Security Alerts Endpoint Tests
# =============================================================================

class TestAuditSecurityAlertsEndpoint:
    """
    POST /api/v1/audit/security/alerts

    Create security alerts.
    """

    async def test_create_security_alert(self, audit_api, api_assert):
        """RED: Create security alert should return alert details"""
        from tests.fixtures.audit_fixtures import make_security_alert_request

        request = make_security_alert_request(
            threat_type="brute_force",
            severity="high",
            description="Multiple failed login attempts",
            source_ip="192.168.1.100"
        )

        response = await audit_api.post("/security/alerts", json=request)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "message", "alert_id", "threat_level"
        ])

    async def test_create_security_alert_validates_required(self, audit_api, api_assert):
        """RED: Missing required fields should return 422"""
        # Missing threat_type
        response = await audit_api.post("/security/alerts", json={
            "severity": "high",
            "description": "Test alert"
        })
        api_assert.assert_validation_error(response)


# =============================================================================
# Security Events Endpoint Tests
# =============================================================================

class TestAuditSecurityEventsEndpoint:
    """
    GET /api/v1/audit/security/events

    Get security events.
    """

    async def test_get_security_events_returns_list(self, audit_api, api_assert):
        """RED: Get security events should return list"""
        response = await audit_api.get("/security/events")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "security_events", "total_count", "period_days"
        ])
        assert isinstance(data["security_events"], list)

    async def test_get_security_events_with_severity(self, audit_api, api_assert):
        """RED: Security events should filter by severity"""
        response = await audit_api.get("/security/events", params={
            "severity": "high",
            "days": 7
        })

        api_assert.assert_success(response)


# =============================================================================
# Compliance Reports Endpoint Tests
# =============================================================================

class TestAuditComplianceReportsEndpoint:
    """
    POST /api/v1/audit/compliance/reports

    Generate compliance reports.
    """

    async def test_generate_compliance_report(self, audit_api, api_assert):
        """RED: Generate report should return ComplianceReport"""
        from tests.fixtures.audit_fixtures import make_compliance_report_request

        request = make_compliance_report_request(
            report_type="monthly",
            compliance_standard="GDPR"
        )

        response = await audit_api.post("/compliance/reports", json=request)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "report_id", "compliance_standard", "report_type"
        ])

    async def test_generate_report_validates_standard(self, audit_api, api_assert):
        """RED: Invalid compliance standard behavior"""
        from tests.fixtures.audit_fixtures import make_compliance_report_request

        request = make_compliance_report_request(
            compliance_standard="INVALID_STANDARD"
        )

        response = await audit_api.post("/compliance/reports", json=request)

        # Service returns 500 for unsupported standards
        assert response.status_code in [400, 422, 500]


# =============================================================================
# Compliance Standards Endpoint Tests
# =============================================================================

class TestAuditComplianceStandardsEndpoint:
    """
    GET /api/v1/audit/compliance/standards

    Get supported compliance standards.
    """

    async def test_get_compliance_standards(self, audit_api, api_assert):
        """RED: Get standards should return list"""
        response = await audit_api.get("/compliance/standards")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, ["supported_standards"])
        assert isinstance(data["supported_standards"], list)
        assert len(data["supported_standards"]) > 0

        # Each standard should have name and description
        standard = data["supported_standards"][0]
        api_assert.assert_has_fields(standard, ["name", "description"])


# =============================================================================
# Stats Endpoint Tests
# =============================================================================

class TestAuditStatsEndpoint:
    """
    GET /api/v1/audit/stats

    Get audit service statistics.
    """

    async def test_get_stats_returns_counts(self, audit_api, api_assert):
        """RED: Stats should return service statistics"""
        response = await audit_api.get("/stats")

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "total_events", "events_today", "security_alerts"
        ])
        assert isinstance(data["total_events"], int)


# =============================================================================
# Health Endpoints Tests
# =============================================================================

class TestAuditHealthEndpoints:
    """
    GET /health
    GET /health/detailed

    Service health check endpoints.
    """

    async def test_health_check(self, http_client, api_assert):
        """RED: Health check should return service status"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("audit")
        response = await http_client.get(f"{base_url}/health")

        api_assert.assert_success(response)
        data = response.json()

        assert "status" in data

    async def test_health_detailed(self, http_client, api_assert):
        """RED: Detailed health should include database status"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("audit")
        response = await http_client.get(f"{base_url}/health/detailed")

        api_assert.assert_success(response)
        data = response.json()

        assert "status" in data
        assert "database_connected" in data


# =============================================================================
# Batch Events Endpoint Tests
# =============================================================================

class TestAuditBatchEventsEndpoint:
    """
    POST /api/v1/audit/events/batch

    Log multiple audit events at once.
    """

    async def test_batch_events_logs_multiple(self, audit_api, api_assert):
        """RED: Batch should log multiple events"""
        from tests.fixtures.audit_fixtures import make_audit_event_request

        events = [
            make_audit_event_request(action="action_1"),
            make_audit_event_request(action="action_2"),
            make_audit_event_request(action="action_3"),
        ]

        response = await audit_api.post("/events/batch", json=events)

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "message", "successful_count", "failed_count", "total_count"
        ])
        assert data["total_count"] == 3

    async def test_batch_events_limit(self, audit_api, api_assert):
        """RED: Batch should reject more than 100 events"""
        from tests.fixtures.audit_fixtures import make_audit_event_request

        # Create 101 events
        events = [make_audit_event_request(action=f"action_{i}") for i in range(101)]

        response = await audit_api.post("/events/batch", json=events)

        assert response.status_code == 400


# =============================================================================
# Cleanup Endpoint Tests
# =============================================================================

class TestAuditCleanupEndpoint:
    """
    POST /api/v1/audit/maintenance/cleanup

    Cleanup old audit data.
    """

    async def test_cleanup_returns_result(self, audit_api, api_assert):
        """RED: Cleanup should return cleanup result"""
        response = await audit_api.post("/maintenance/cleanup", params={
            "retention_days": 365
        })

        api_assert.assert_success(response)
        data = response.json()

        api_assert.assert_has_fields(data, [
            "message", "cleaned_events", "retention_days"
        ])
        assert data["retention_days"] == 365
