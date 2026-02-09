"""
Audit Service - Integration Tests

Tests full audit event lifecycle with real database persistence.
Uses X-Internal-Call header to bypass authentication.
"""
import pytest
from datetime import datetime, timezone

from tests.contracts.audit.data_contract import (
    AuditTestDataFactory, 
    AuditCategory,
    EventSeverity,
    ComplianceStandard,
)

pytestmark = [pytest.mark.integration, pytest.mark.golden, pytest.mark.asyncio]

AUDIT_SERVICE_URL = "http://localhost:8204"
API_BASE = f"{AUDIT_SERVICE_URL}/api/v1/audit"


# =============================================================================
# Health Check Tests (3 tests)
# =============================================================================

class TestAuditHealthCheck:
    """Test audit service health endpoints"""

    async def test_basic_health_check(self, http_client, internal_headers):
        """Basic health check returns healthy status"""
        response = await http_client.get(
            f"{AUDIT_SERVICE_URL}/health",
            headers=internal_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "audit_service"

    async def test_detailed_health_check(self, http_client, internal_headers):
        """Detailed health check returns database status"""
        response = await http_client.get(
            f"{AUDIT_SERVICE_URL}/health/detailed",
            headers=internal_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "database_connected" in data

    async def test_service_info(self, http_client, internal_headers):
        """Service info returns capabilities"""
        response = await http_client.get(
            f"{API_BASE}/info",
            headers=internal_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "capabilities" in data
        assert data["service"] == "audit_service"


# =============================================================================
# Audit Event Creation Tests (8 tests)
# =============================================================================

class TestAuditEventCreation:
    """Test audit event creation integration"""

    async def test_create_audit_event_success(self, http_client, internal_headers, cleanup_events):
        """Create audit event returns event data"""
        create_data = AuditTestDataFactory.make_audit_event_create_request().model_dump()
        # Convert enums to values
        create_data["event_type"] = create_data["event_type"].value
        create_data["category"] = create_data["category"].value
        create_data["severity"] = create_data["severity"].value

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "event_id" in data

    async def test_create_audit_event_with_user_id(self, http_client, internal_headers):
        """Create audit event with user_id"""
        user_id = AuditTestDataFactory.make_user_id()
        request = AuditTestDataFactory.make_audit_event_create_request(user_id=user_id)
        create_data = request.model_dump()
        create_data["event_type"] = create_data["event_type"].value
        create_data["category"] = create_data["category"].value
        create_data["severity"] = create_data["severity"].value

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_create_audit_event_with_organization(self, http_client, internal_headers):
        """Create audit event with organization_id"""
        org_id = AuditTestDataFactory.make_organization_id()
        request = AuditTestDataFactory.make_audit_event_create_request(organization_id=org_id)
        create_data = request.model_dump()
        create_data["event_type"] = create_data["event_type"].value
        create_data["category"] = create_data["category"].value
        create_data["severity"] = create_data["severity"].value

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_create_security_event(self, http_client, internal_headers):
        """Create security event"""
        request = AuditTestDataFactory.make_audit_event_create_request(
            event_type="audit.security.alert",
            category=AuditCategory.SECURITY,
            severity=EventSeverity.HIGH,
        )
        create_data = request.model_dump()
        create_data["event_type"] = create_data["event_type"].value
        create_data["category"] = create_data["category"].value
        create_data["severity"] = create_data["severity"].value

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_create_audit_event_with_metadata(self, http_client, internal_headers):
        """Create audit event with metadata"""
        metadata = {"key": "value", "nested": {"a": 1}}
        request = AuditTestDataFactory.make_audit_event_create_request(metadata=metadata)
        create_data = request.model_dump()
        create_data["event_type"] = create_data["event_type"].value
        create_data["category"] = create_data["category"].value
        create_data["severity"] = create_data["severity"].value

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_create_audit_event_with_tags(self, http_client, internal_headers):
        """Create audit event with tags"""
        tags = ["tag1", "tag2", "test"]
        request = AuditTestDataFactory.make_audit_event_create_request(tags=tags)
        create_data = request.model_dump()
        create_data["event_type"] = create_data["event_type"].value
        create_data["category"] = create_data["category"].value
        create_data["severity"] = create_data["severity"].value

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_create_audit_event_invalid_data_returns_422(self, http_client, internal_headers):
        """Create audit event with invalid data returns 422"""
        invalid_data = {"action": ""}  # Missing required fields

        response = await http_client.post(
            f"{API_BASE}/events",
            json=invalid_data,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_batch_create_audit_events(self, http_client, internal_headers):
        """Batch create audit events"""
        batch = AuditTestDataFactory.make_audit_event_batch_request(count=3)
        batch_data = []
        for event in batch.events:
            event_data = event.model_dump()
            event_data["event_type"] = event_data["event_type"].value
            event_data["category"] = event_data["category"].value
            event_data["severity"] = event_data["severity"].value
            batch_data.append(event_data)

        response = await http_client.post(
            f"{API_BASE}/events/batch",
            json=batch_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]


# =============================================================================
# Audit Event Query Tests (8 tests)
# =============================================================================

class TestAuditEventQuery:
    """Test audit event query integration"""

    async def test_query_events_success(self, http_client, internal_headers):
        """Query events returns list"""
        query = AuditTestDataFactory.make_audit_query_request().model_dump()
        # Convert enums to values
        if query.get("event_types"):
            query["event_types"] = [e.value for e in query["event_types"]]
        if query.get("categories"):
            query["categories"] = [c.value for c in query["categories"]]
        if query.get("severities"):
            query["severities"] = [s.value for s in query["severities"]]

        response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query,
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_get_events_list(self, http_client, internal_headers):
        """GET events returns list"""
        response = await http_client.get(
            f"{API_BASE}/events",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_get_events_with_filters(self, http_client, internal_headers):
        """GET events with query parameters"""
        response = await http_client.get(
            f"{API_BASE}/events?limit=50&offset=0",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_query_events_by_event_type(self, http_client, internal_headers):
        """Query events by event type"""
        query = {"event_types": ["user_login"], "limit": 10}

        response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query,
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_query_events_by_category(self, http_client, internal_headers):
        """Query events by category"""
        query = {"categories": ["authentication"], "limit": 10}

        response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query,
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_query_events_by_severity(self, http_client, internal_headers):
        """Query events by severity"""
        query = {"severities": ["high", "critical"], "limit": 10}

        response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query,
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_query_events_with_pagination(self, http_client, internal_headers):
        """Query events with pagination"""
        query = {"limit": 25, "offset": 0}

        response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query,
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_query_events_by_user_id(self, http_client, internal_headers):
        """Query events by user_id"""
        user_id = AuditTestDataFactory.make_user_id()
        query = {"user_id": user_id, "limit": 10}

        response = await http_client.post(
            f"{API_BASE}/events/query",
            json=query,
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# User Activity Tests (5 tests)
# =============================================================================

class TestUserActivityIntegration:
    """Test user activity integration"""

    async def test_get_user_activities(self, http_client, internal_headers):
        """Get user activities returns list"""
        user_id = AuditTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/users/{user_id}/activities?days=30&limit=100",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_get_user_activity_summary(self, http_client, internal_headers):
        """Get user activity summary"""
        user_id = AuditTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/users/{user_id}/summary?days=30",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_get_user_activities_with_days_filter(self, http_client, internal_headers):
        """Get user activities with days filter"""
        user_id = AuditTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/users/{user_id}/activities?days=7&limit=50",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_get_user_activities_empty_results(self, http_client, internal_headers):
        """Get activities for user with no activity"""
        user_id = AuditTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/users/{user_id}/activities?days=1&limit=10",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_get_user_activity_summary_structure(self, http_client, internal_headers):
        """User activity summary has expected structure"""
        user_id = AuditTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/users/{user_id}/summary?days=30",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data


# =============================================================================
# Security Events Tests (5 tests)
# =============================================================================

class TestSecurityEventsIntegration:
    """Test security events integration"""

    async def test_create_security_alert(self, http_client, internal_headers):
        """Create security alert"""
        alert = AuditTestDataFactory.make_security_alert_request().model_dump()

        response = await http_client.post(
            f"{API_BASE}/security/alerts",
            json=alert,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_get_security_events(self, http_client, internal_headers):
        """Get security events"""
        response = await http_client.get(
            f"{API_BASE}/security/events?days=7",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_get_security_events_with_severity(self, http_client, internal_headers):
        """Get security events with severity filter"""
        response = await http_client.get(
            f"{API_BASE}/security/events?days=7&severity=high",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_create_security_alert_with_details(self, http_client, internal_headers):
        """Create security alert with full details"""
        alert = AuditTestDataFactory.make_security_alert_request(
            threat_type="brute_force",
            affected_users=["user_1", "user_2"],
            source_ip="10.0.0.50",
        ).model_dump()

        response = await http_client.post(
            f"{API_BASE}/security/alerts",
            json=alert,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_get_security_events_structure(self, http_client, internal_headers):
        """Security events response has expected structure"""
        response = await http_client.get(
            f"{API_BASE}/security/events?days=7",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "security_events" in data


# =============================================================================
# Compliance Tests (5 tests)
# =============================================================================

class TestComplianceIntegration:
    """Test compliance features integration"""

    async def test_get_compliance_standards(self, http_client, internal_headers):
        """Get supported compliance standards"""
        response = await http_client.get(
            f"{API_BASE}/compliance/standards",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "supported_standards" in data

    async def test_generate_gdpr_report(self, http_client, internal_headers):
        """Generate GDPR compliance report"""
        request = AuditTestDataFactory.make_compliance_report_request(
            compliance_standard=ComplianceStandard.GDPR
        ).model_dump()
        request["compliance_standard"] = request["compliance_standard"].value

        response = await http_client.post(
            f"{API_BASE}/compliance/reports",
            json=request,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_generate_sox_report(self, http_client, internal_headers):
        """Generate SOX compliance report"""
        request = AuditTestDataFactory.make_compliance_report_request(
            compliance_standard=ComplianceStandard.SOX
        ).model_dump()
        request["compliance_standard"] = request["compliance_standard"].value

        response = await http_client.post(
            f"{API_BASE}/compliance/reports",
            json=request,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_generate_hipaa_report(self, http_client, internal_headers):
        """Generate HIPAA compliance report"""
        request = AuditTestDataFactory.make_compliance_report_request(
            compliance_standard=ComplianceStandard.HIPAA
        ).model_dump()
        request["compliance_standard"] = request["compliance_standard"].value

        response = await http_client.post(
            f"{API_BASE}/compliance/reports",
            json=request,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]

    async def test_compliance_standards_structure(self, http_client, internal_headers):
        """Compliance standards response has expected structure"""
        response = await http_client.get(
            f"{API_BASE}/compliance/standards",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        standards = data["supported_standards"]
        assert len(standards) >= 3  # GDPR, SOX, HIPAA


# =============================================================================
# Service Statistics Tests (3 tests)
# =============================================================================

class TestServiceStatisticsIntegration:
    """Test service statistics integration"""

    async def test_get_service_stats(self, http_client, internal_headers):
        """Get service statistics"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_service_stats_structure(self, http_client, internal_headers):
        """Service stats has expected structure"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data

    async def test_cleanup_old_data(self, http_client, internal_headers):
        """Cleanup old data endpoint"""
        response = await http_client.post(
            f"{API_BASE}/maintenance/cleanup?retention_days=365",
            headers=internal_headers
        )

        # May require admin privileges
        assert response.status_code in [200, 403]
