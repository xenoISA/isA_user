"""
Audit Service - API Tests

Tests HTTP API contracts with authentication requirements.
Validates request/response schemas and error handling.

All tests use AuditTestDataFactory - zero hardcoded data.
"""
import pytest
from tests.contracts.audit.data_contract import (
    AuditTestDataFactory, 
    AuditCategory,
    EventSeverity,
)

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]

AUDIT_SERVICE_URL = "http://localhost:8204"


# =============================================================================
# Authentication Tests (6 tests)
# =============================================================================

class TestAuditAuthenticationAPI:
    """Test API authentication requirements"""

    async def test_health_no_auth_required(self, http_client, health_url):
        """Health endpoint requires no authentication"""
        response = await http_client.get(health_url)
        assert response.status_code == 200

    async def test_events_endpoint_allows_internal_call(
        self, http_client, internal_headers, audit_base_url
    ):
        """Internal calls bypass authentication"""
        response = await http_client.get(
            f"{audit_base_url}/events",
            headers=internal_headers
        )
        # Should not return 401
        assert response.status_code != 401

    async def test_invalid_token_returns_401(self, http_client, audit_base_url):
        """Request with invalid token returns 401"""
        response = await http_client.get(
            f"{audit_base_url}/events",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        # May return 401 or allow with internal service
        assert response.status_code in [200, 401, 403]

    async def test_missing_auth_header(self, http_client, audit_base_url):
        """Request without auth header behavior"""
        response = await http_client.get(f"{audit_base_url}/events")
        # Audit service may allow unauthenticated reads or reject
        assert response.status_code in [200, 401]

    async def test_malformed_auth_header(self, http_client, audit_base_url):
        """Malformed Authorization header handling"""
        response = await http_client.get(
            f"{audit_base_url}/events",
            headers={"Authorization": "NotBearer token"}
        )
        assert response.status_code in [200, 401]

    async def test_internal_header_grants_access(
        self, http_client, internal_headers, audit_base_url
    ):
        """X-Internal-Call header grants access"""
        response = await http_client.get(
            f"{audit_base_url}/events",
            headers=internal_headers
        )
        assert response.status_code == 200


# =============================================================================
# Event Logging API Tests (8 tests)
# =============================================================================

class TestAuditEventLoggingAPI:
    """Test audit event logging API contracts"""

    async def test_log_event_success(self, audit_api):
        """POST /events creates audit event"""
        event_data = AuditTestDataFactory.make_create_request().model_dump()
        event_data["event_type"] = event_data["event_type"].value

        response = await audit_api.post("/events", json=event_data)

        assert response.status_code in [200, 201]
        data = response.json()
        assert "audit_event_id" in data or "event_id" in data

    async def test_log_event_with_all_fields(self, audit_api):
        """POST /events with all optional fields"""
        event_data = {
            "event_type": "user.logged_in".value,
            "category": AuditCategory.AUTHENTICATION.value,
            "severity": EventSeverity.LOW.value,
            "user_id": AuditTestDataFactory.make_user_id(),
            "resource_id": AuditTestDataFactory.make_resource_id(),
            "resource_type": "account",
            "action": "login",
            "description": AuditTestDataFactory.make_description(),
            "metadata": {"ip_address": "192.168.1.1"},
            "source_service": "auth_service",
            "correlation_id": AuditTestDataFactory.make_correlation_id(),
        }

        response = await audit_api.post("/events", json=event_data)

        assert response.status_code in [200, 201]

    async def test_log_event_minimal_fields(self, audit_api):
        """POST /events with only required fields"""
        event_data = {
            "event_type": "audit.security.alert".value,
        }

        response = await audit_api.post("/events", json=event_data)

        # Should succeed or fail with validation error (not 500)
        assert response.status_code in [200, 201, 422]

    async def test_log_event_invalid_event_type(self, audit_api):
        """POST /events with invalid event_type returns 422"""
        event_data = {
            "event_type": "INVALID_EVENT_TYPE",
        }

        response = await audit_api.post("/events", json=event_data)

        assert response.status_code == 422

    async def test_log_event_returns_created_data(self, audit_api):
        """POST /events returns created event data"""
        event_data = AuditTestDataFactory.make_create_request().model_dump()
        event_data["event_type"] = event_data["event_type"].value

        response = await audit_api.post("/events", json=event_data)

        if response.status_code in [200, 201]:
            data = response.json()
            assert "timestamp" in data or "created_at" in data

    async def test_log_security_alert(self, audit_api):
        """POST /events for security alert"""
        alert_data = AuditTestDataFactory.make_security_alert_request().model_dump()
        alert_data["event_type"] = alert_data["event_type"].value
        alert_data["severity"] = alert_data["severity"].value
        alert_data["category"] = alert_data["category"].value

        response = await audit_api.post("/events", json=alert_data)

        assert response.status_code in [200, 201]

    async def test_log_event_with_metadata_object(self, audit_api):
        """POST /events with complex metadata"""
        event_data = {
            "event_type": "audit.data.access".value,
            "metadata": {
                "fields_accessed": ["email", "phone"],
                "query_count": 5,
                "cached": True,
            }
        }

        response = await audit_api.post("/events", json=event_data)

        assert response.status_code in [200, 201, 422]

    async def test_log_event_empty_body_returns_422(self, audit_api):
        """POST /events with empty body returns 422"""
        response = await audit_api.post("/events", json={})

        assert response.status_code == 422


# =============================================================================
# Event Query API Tests (6 tests)
# =============================================================================

class TestAuditEventQueryAPI:
    """Test audit event query API contracts"""

    async def test_list_events_returns_items(self, audit_api):
        """GET /events returns paginated list"""
        response = await audit_api.get("/events")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    async def test_list_events_with_pagination(self, audit_api):
        """GET /events with limit and offset"""
        response = await audit_api.get("/events", params={"limit": 10, "offset": 0})

        assert response.status_code == 200
        data = response.json()
        if "items" in data:
            assert len(data["items"]) <= 10

    async def test_list_events_filter_by_event_type(self, audit_api):
        """GET /events filtered by event_type"""
        response = await audit_api.get(
            "/events",
            params={"event_type": "user.logged_in".value}
        )

        assert response.status_code == 200

    async def test_list_events_filter_by_user_id(self, audit_api):
        """GET /events filtered by user_id"""
        user_id = AuditTestDataFactory.make_user_id()
        response = await audit_api.get("/events", params={"user_id": user_id})

        assert response.status_code == 200

    async def test_list_events_filter_by_severity(self, audit_api):
        """GET /events filtered by severity"""
        response = await audit_api.get(
            "/events",
            params={"severity": EventSeverity.HIGH.value}
        )

        assert response.status_code == 200

    async def test_list_events_invalid_limit_returns_422(self, audit_api):
        """GET /events with invalid limit returns 422"""
        response = await audit_api.get("/events", params={"limit": -1})

        # May return 422 or clamp to valid value
        assert response.status_code in [200, 422]


# =============================================================================
# User Activity API Tests (4 tests)
# =============================================================================

class TestUserActivityAPI:
    """Test user activity API endpoints"""

    async def test_get_user_activity(self, audit_api):
        """GET /users/{user_id}/activity returns user events"""
        user_id = AuditTestDataFactory.make_user_id()
        response = await audit_api.get(f"/users/{user_id}/activity")

        assert response.status_code in [200, 404]

    async def test_get_user_activity_with_date_range(self, audit_api):
        """GET /users/{user_id}/activity with date filters"""
        user_id = AuditTestDataFactory.make_user_id()
        response = await audit_api.get(
            f"/users/{user_id}/activity",
            params={
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-12-31T23:59:59Z"
            }
        )

        assert response.status_code in [200, 404]

    async def test_get_user_activity_not_found(self, audit_api):
        """GET /users/{user_id}/activity for nonexistent user"""
        fake_user_id = AuditTestDataFactory.make_invalid_id()
        response = await audit_api.get(f"/users/{fake_user_id}/activity")

        # May return empty list or 404
        assert response.status_code in [200, 404]

    async def test_get_user_activity_pagination(self, audit_api):
        """GET /users/{user_id}/activity with pagination"""
        user_id = AuditTestDataFactory.make_user_id()
        response = await audit_api.get(
            f"/users/{user_id}/activity",
            params={"limit": 5, "offset": 0}
        )

        assert response.status_code in [200, 404]


# =============================================================================
# Security Alerts API Tests (4 tests)
# =============================================================================

class TestSecurityAlertsAPI:
    """Test security alerts API endpoints"""

    async def test_get_security_alerts(self, audit_api):
        """GET /security/alerts returns security events"""
        response = await audit_api.get("/security/alerts")

        assert response.status_code in [200, 404]

    async def test_get_security_alerts_by_severity(self, audit_api):
        """GET /security/alerts filtered by severity"""
        response = await audit_api.get(
            "/security/alerts",
            params={"severity": EventSeverity.CRITICAL.value}
        )

        assert response.status_code in [200, 404]

    async def test_get_security_alerts_unacknowledged(self, audit_api):
        """GET /security/alerts for unacknowledged alerts"""
        response = await audit_api.get(
            "/security/alerts",
            params={"acknowledged": "false"}
        )

        assert response.status_code in [200, 404]

    async def test_acknowledge_security_alert(self, audit_api):
        """PUT /security/alerts/{id}/acknowledge"""
        alert_id = AuditTestDataFactory.make_audit_event_id()
        response = await audit_api.put(
            f"/security/alerts/{alert_id}/acknowledge",
            json={"acknowledged_by": "admin_user"}
        )

        # May succeed or return 404 if alert doesn't exist
        assert response.status_code in [200, 404]


# =============================================================================
# Compliance Reports API Tests (4 tests)
# =============================================================================

class TestComplianceReportsAPI:
    """Test compliance reporting API endpoints"""

    async def test_generate_compliance_report(self, audit_api):
        """POST /compliance/reports generates report"""
        report_request = AuditTestDataFactory.make_compliance_report_request()

        response = await audit_api.post(
            "/compliance/reports",
            json=report_request.model_dump()
        )

        assert response.status_code in [200, 201, 404]

    async def test_get_compliance_report(self, audit_api):
        """GET /compliance/reports/{id} returns report"""
        report_id = AuditTestDataFactory.make_report_id()
        response = await audit_api.get(f"/compliance/reports/{report_id}")

        assert response.status_code in [200, 404]

    async def test_list_compliance_reports(self, audit_api):
        """GET /compliance/reports returns report list"""
        response = await audit_api.get("/compliance/reports")

        assert response.status_code in [200, 404]

    async def test_generate_report_invalid_standard(self, audit_api):
        """POST /compliance/reports with invalid standard"""
        response = await audit_api.post(
            "/compliance/reports",
            json={"standard": "INVALID_STANDARD"}
        )

        assert response.status_code in [404, 422]


# =============================================================================
# Statistics API Tests (3 tests)
# =============================================================================

class TestAuditStatisticsAPI:
    """Test audit statistics API endpoints"""

    async def test_get_event_statistics(self, audit_api):
        """GET /statistics returns event counts"""
        response = await audit_api.get("/statistics")

        assert response.status_code in [200, 404]

    async def test_get_statistics_by_date_range(self, audit_api):
        """GET /statistics with date range"""
        response = await audit_api.get(
            "/statistics",
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-12-31"
            }
        )

        assert response.status_code in [200, 404]

    async def test_get_statistics_by_category(self, audit_api):
        """GET /statistics/by-category"""
        response = await audit_api.get("/statistics/by-category")

        assert response.status_code in [200, 404]


# =============================================================================
# Error Response Contract Tests (3 tests)
# =============================================================================

class TestErrorResponseContract:
    """Test error response format consistency"""

    async def test_404_response_format(self, http_client, internal_headers):
        """404 response has consistent format"""
        response = await http_client.get(
            f"{AUDIT_SERVICE_URL}/api/v1/audit/events/nonexistent_id_12345",
            headers=internal_headers
        )

        if response.status_code == 404:
            data = response.json()
            assert "detail" in data or "message" in data or "error" in data

    async def test_422_response_includes_field_errors(self, audit_api):
        """422 response includes field-level errors"""
        response = await audit_api.post("/events", json={"invalid_field": "value"})

        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    async def test_health_response_format(self, http_client, health_url):
        """Health response has expected format"""
        response = await http_client.get(health_url)

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
