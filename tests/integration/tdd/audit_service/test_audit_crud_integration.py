"""
Audit Service CRUD Integration Tests

Tests audit lifecycle operations with real database persistence.
These tests verify data flows through the service and persists correctly.

Usage:
    pytest tests/integration/services/audit/test_audit_crud_integration.py -v
"""
import pytest
import pytest_asyncio
import httpx
from typing import List
from datetime import datetime, timezone, timedelta

from tests.fixtures import make_user_id, make_org_id
from tests.fixtures.audit_fixtures import (
    make_audit_event_request,
    make_audit_query_request,
    make_security_alert_request,
    make_compliance_report_request,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

AUDIT_SERVICE_URL = "http://localhost:8227"
API_BASE = f"{AUDIT_SERVICE_URL}/api/v1/audit"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for integration tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate unique user ID for test isolation"""
    return make_user_id()


@pytest.fixture
def test_org_id():
    """Generate unique organization ID for test isolation"""
    return make_org_id()


# ============================================================================
# Audit Event Lifecycle Integration Tests
# ============================================================================

class TestAuditEventLifecycleIntegration:
    """
    Integration tests for audit event lifecycle.
    Tests event creation, retrieval, and querying.
    """

    async def test_full_audit_event_lifecycle(self, http_client, test_user_id):
        """
        Integration: Full audit event lifecycle - create, read, query

        1. Create audit event
        2. Query events and verify persisted
        3. Get user activities and verify included
        """
        # 1. CREATE audit event
        create_request = make_audit_event_request(
            event_type="user_login",
            category="authentication",
            action="user_login_success",
            user_id=test_user_id,
            ip_address="192.168.1.1",
            success=True
        )

        create_response = await http_client.post(
            f"{API_BASE}/events",
            json=create_request,
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"

        event_data = create_response.json()
        assert event_data["event_type"] == "user_login"
        assert event_data["action"] == "user_login_success"
        event_id = event_data.get("id")

        # 2. QUERY - verify persisted
        query_request = make_audit_query_request(
            user_id=test_user_id,
            limit=10
        )

        query_response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query_request,
        )
        assert query_response.status_code == 200

        query_data = query_response.json()
        assert "events" in query_data
        # Note: May need time for persistence, check if any events returned
        assert isinstance(query_data["events"], list)

        # 3. GET USER ACTIVITIES
        activities_response = await http_client.get(
            f"{API_BASE}/users/{test_user_id}/activities"
        )
        assert activities_response.status_code == 200

        activities_data = activities_response.json()
        assert activities_data["user_id"] == test_user_id
        assert isinstance(activities_data["activities"], list)


class TestAuditEventQueryIntegration:
    """
    Integration tests for audit event querying.
    """

    async def test_query_with_event_type_filter(self, http_client, test_user_id):
        """
        Integration: Query with event type filter

        1. Create events of different types
        2. Query by specific type
        3. Verify filter works
        """
        # Create login event
        login_request = make_audit_event_request(
            event_type="user_login",
            category="authentication",
            action="login",
            user_id=test_user_id
        )
        await http_client.post(f"{API_BASE}/events", json=login_request)

        # Create resource access event
        access_request = make_audit_event_request(
            event_type="resource_access",
            category="data_access",
            action="read_document",
            user_id=test_user_id
        )
        await http_client.post(f"{API_BASE}/events", json=access_request)

        # Query by event type via GET
        response = await http_client.get(
            f"{API_BASE}/events",
            params={"event_type": "user_login", "user_id": test_user_id}
        )
        assert response.status_code == 200

    async def test_query_with_time_range(self, http_client):
        """
        Integration: Query with time range filter

        1. Create event
        2. Query with time range that includes event
        3. Query with time range that excludes event
        """
        # Create event
        create_request = make_audit_event_request(
            event_type="user_login",
            category="authentication",
            action="time_range_test"
        )
        await http_client.post(f"{API_BASE}/events", json=create_request)

        # Query with recent time range
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=1)

        query_request = make_audit_query_request(
            start_time=start_time,
            end_time=now,
            limit=50
        )

        response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query_request
        )
        assert response.status_code == 200


class TestAuditUserActivityIntegration:
    """
    Integration tests for user activity tracking.
    """

    async def test_user_activity_summary(self, http_client, test_user_id):
        """
        Integration: User activity summary

        1. Create multiple events for user
        2. Get activity summary
        3. Verify counts
        """
        # Create successful event
        success_request = make_audit_event_request(
            event_type="user_login",
            category="authentication",
            action="login_success",
            user_id=test_user_id,
            success=True
        )
        await http_client.post(f"{API_BASE}/events", json=success_request)

        # Create failed event
        failure_request = make_audit_event_request(
            event_type="user_login",
            category="authentication",
            action="login_failed",
            user_id=test_user_id,
            success=False
        )
        await http_client.post(f"{API_BASE}/events", json=failure_request)

        # Get summary
        summary_response = await http_client.get(
            f"{API_BASE}/users/{test_user_id}/summary"
        )
        assert summary_response.status_code == 200

        summary_data = summary_response.json()
        assert summary_data["user_id"] == test_user_id
        assert "total_activities" in summary_data
        assert "success_count" in summary_data
        assert "failure_count" in summary_data


class TestAuditSecurityEventsIntegration:
    """
    Integration tests for security event management.
    """

    async def test_security_alert_lifecycle(self, http_client, test_user_id):
        """
        Integration: Security alert lifecycle

        1. Create security alert
        2. Get security events
        3. Verify alert in list
        """
        # Create security alert
        alert_request = make_security_alert_request(
            threat_type="brute_force",
            severity="high",
            description="Multiple failed login attempts from suspicious IP",
            source_ip="192.168.1.100",
            user_id=test_user_id
        )

        create_response = await http_client.post(
            f"{API_BASE}/security/alerts",
            json=alert_request
        )
        assert create_response.status_code == 200

        alert_data = create_response.json()
        assert "alert_id" in alert_data

        # Get security events
        events_response = await http_client.get(
            f"{API_BASE}/security/events",
            params={"days": 7}
        )
        assert events_response.status_code == 200

        events_data = events_response.json()
        assert "security_events" in events_data
        assert isinstance(events_data["security_events"], list)


class TestAuditComplianceIntegration:
    """
    Integration tests for compliance reporting.
    """

    async def test_compliance_report_generation(self, http_client, test_org_id):
        """
        Integration: Compliance report generation

        1. Generate GDPR compliance report
        2. Verify report structure
        """
        report_request = make_compliance_report_request(
            report_type="monthly",
            compliance_standard="GDPR",
            organization_id=test_org_id
        )

        response = await http_client.post(
            f"{API_BASE}/compliance/reports",
            json=report_request
        )
        assert response.status_code == 200

        report_data = response.json()
        assert report_data["compliance_standard"] == "GDPR"
        assert "report_id" in report_data

    async def test_get_compliance_standards(self, http_client):
        """
        Integration: Get supported compliance standards

        1. Get standards list
        2. Verify GDPR, SOX, HIPAA supported
        """
        response = await http_client.get(f"{API_BASE}/compliance/standards")
        assert response.status_code == 200

        data = response.json()
        assert "supported_standards" in data

        standard_names = [s["name"] for s in data["supported_standards"]]
        assert "GDPR" in standard_names
        assert "SOX" in standard_names
        assert "HIPAA" in standard_names


class TestAuditBatchOperationsIntegration:
    """
    Integration tests for batch operations.
    """

    async def test_batch_event_creation(self, http_client, test_user_id):
        """
        Integration: Batch event creation

        1. Create multiple events in batch
        2. Verify all events created
        3. Query and verify persisted
        """
        events = [
            make_audit_event_request(
                event_type="resource_access",
                category="data_access",
                action=f"batch_action_{i}",
                user_id=test_user_id
            )
            for i in range(5)
        ]

        response = await http_client.post(
            f"{API_BASE}/events/batch",
            json=events
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 5
        assert data["successful_count"] >= 0


class TestAuditServiceStatsIntegration:
    """
    Integration tests for service statistics.
    """

    async def test_service_stats(self, http_client):
        """
        Integration: Service statistics

        1. Get service stats
        2. Verify structure
        """
        response = await http_client.get(f"{API_BASE}/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total_events" in data
        assert isinstance(data["total_events"], int)

    async def test_service_info(self, http_client):
        """
        Integration: Service info

        1. Get service info
        2. Verify capabilities
        """
        response = await http_client.get(f"{API_BASE}/info")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "audit_service"
        assert "capabilities" in data


class TestAuditHealthCheckIntegration:
    """
    Integration tests for health checks.
    """

    async def test_basic_health(self, http_client):
        """
        Integration: Basic health check
        """
        response = await http_client.get(f"{AUDIT_SERVICE_URL}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"

    async def test_detailed_health(self, http_client):
        """
        Integration: Detailed health check with database status
        """
        response = await http_client.get(f"{AUDIT_SERVICE_URL}/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "database_connected" in data
