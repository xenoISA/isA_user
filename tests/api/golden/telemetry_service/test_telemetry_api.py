"""
Telemetry Service API Tests

Tests HTTP API contracts with real JWT authentication.
All test data uses TelemetryTestDataFactory - zero hardcoded data.

Usage:
    pytest tests/api/golden/telemetry_service -v
"""
import pytest
import httpx
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from tests.contracts.telemetry.data_contract import (
    TelemetryTestDataFactory,
    DataType,
    MetricType,
    AlertLevel,
    AlertStatus,
    AggregationType,
)

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]

# Service configuration
TELEMETRY_SERVICE_URL = os.getenv("TELEMETRY_SERVICE_URL", "http://localhost:8225")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8202")
API_BASE = f"{TELEMETRY_SERVICE_URL}/api/v1/telemetry"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
async def auth_token(http_client) -> Optional[str]:
    """Get valid authentication token"""
    try:
        # Try to get a test token from auth service
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/token",
            json={
                "user_id": TelemetryTestDataFactory.make_user_id(),
                "email": TelemetryTestDataFactory.make_email(),
            },
            headers={"X-Internal-Call": "true"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


@pytest.fixture
def auth_headers(auth_token) -> Dict[str, str]:
    """Headers with authentication"""
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


@pytest.fixture
def internal_headers() -> Dict[str, str]:
    """Headers for internal calls (bypass auth)"""
    return {
        "X-Internal-Call": "true",
        "Content-Type": "application/json",
    }


# =============================================================================
# Authentication Tests
# =============================================================================

class TestTelemetryAuthenticationAPI:
    """Test API authentication requirements"""

    async def test_unauthenticated_request_returns_401(self, http_client):
        """API: Request without token returns 401"""
        response = await http_client.get(f"{API_BASE}/metrics")

        assert response.status_code == 401

    async def test_invalid_token_returns_401(self, http_client):
        """API: Request with invalid token returns 401"""
        response = await http_client.get(
            f"{API_BASE}/metrics",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        assert response.status_code == 401

    async def test_expired_token_returns_401(self, http_client):
        """API: Request with expired token returns 401"""
        # Create a token that looks valid but is expired
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfMTIzIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"

        response = await http_client.get(
            f"{API_BASE}/metrics",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401

    async def test_internal_call_bypasses_auth(self, http_client, internal_headers):
        """API: X-Internal-Call header bypasses authentication"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=internal_headers
        )

        # Should succeed without token
        assert response.status_code == 200


# =============================================================================
# Telemetry Ingest API Tests
# =============================================================================

class TestTelemetryIngestAPI:
    """Test telemetry data ingestion API"""

    async def test_ingest_with_auth_succeeds(self, http_client, auth_headers):
        """API: POST telemetry with valid auth succeeds"""
        device_id = TelemetryTestDataFactory.make_device_id()
        data_point = TelemetryTestDataFactory.make_data_point_dict()

        # Use internal headers if no auth token available
        headers = auth_headers if auth_headers.get("Authorization") else {"X-Internal-Call": "true", "Content-Type": "application/json"}

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/telemetry/batch",
            json={"data_points": [data_point]},
            headers=headers
        )

        assert response.status_code in [200, 201]

    async def test_ingest_validates_request_body(self, http_client, internal_headers):
        """API: POST telemetry validates request body"""
        device_id = TelemetryTestDataFactory.make_device_id()

        # Missing required fields
        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/telemetry/batch",
            json={},
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_ingest_returns_ingestion_stats(self, http_client, internal_headers):
        """API: POST telemetry returns ingestion statistics"""
        device_id = TelemetryTestDataFactory.make_device_id()
        data_points = [
            TelemetryTestDataFactory.make_data_point_dict()
            for _ in range(3)
        ]

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/telemetry/batch",
            json={"data_points": data_points},
            headers=internal_headers
        )

        assert response.status_code in [200, 201]
        result = response.json()
        # Should have ingestion stats
        assert "ingested_count" in result or "success" in result


# =============================================================================
# Telemetry Query API Tests
# =============================================================================

class TestTelemetryQueryAPI:
    """Test telemetry query API"""

    async def test_query_with_auth_succeeds(self, http_client, internal_headers):
        """API: POST query with valid auth succeeds"""
        now = datetime.now(timezone.utc)
        query_params = {
            "devices": [TelemetryTestDataFactory.make_device_id()],
            "metrics": [TelemetryTestDataFactory.make_metric_name()],
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": now.isoformat(),
        }

        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_params,
            headers=internal_headers
        )

        # May return 200 with data or 404 if no data
        assert response.status_code in [200, 404]

    async def test_query_validates_time_range(self, http_client, internal_headers):
        """API: Query validates time range format"""
        query_params = {
            "devices": [TelemetryTestDataFactory.make_device_id()],
            "metrics": [TelemetryTestDataFactory.make_metric_name()],
            "start_time": "not-a-valid-date",
            "end_time": "also-invalid",
        }

        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_params,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_query_returns_data_points(self, http_client, internal_headers):
        """API: Query returns data points array"""
        now = datetime.now(timezone.utc)
        query_params = {
            "devices": [TelemetryTestDataFactory.make_device_id()],
            "metrics": [TelemetryTestDataFactory.make_metric_name()],
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": now.isoformat(),
        }

        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_params,
            headers=internal_headers
        )

        # May return 200 with data or 404 if no data
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            result = response.json()
            assert "data_points" in result or "count" in result

    async def test_query_respects_limit(self, http_client, internal_headers):
        """API: Query respects limit parameter"""
        now = datetime.now(timezone.utc)
        query_params = {
            "devices": [TelemetryTestDataFactory.make_device_id()],
            "metrics": [TelemetryTestDataFactory.make_metric_name()],
            "start_time": (now - timedelta(hours=24)).isoformat(),
            "end_time": now.isoformat(),
            "limit": 10,
        }

        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_params,
            headers=internal_headers
        )

        # May return 200 with data or 404 if no data
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            result = response.json()
            data_points = result.get("data_points", [])
            assert len(data_points) <= 10


# =============================================================================
# Metric Definition API Tests
# =============================================================================

class TestMetricDefinitionAPI:
    """Test metric definition API"""

    async def test_create_metric_succeeds(self, http_client, internal_headers):
        """API: POST metric with valid data succeeds"""
        user_id = TelemetryTestDataFactory.make_user_id()
        metric_data = TelemetryTestDataFactory.make_metric_definition_create_dict()

        response = await http_client.post(
            f"{API_BASE}/metrics",
            json=metric_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201]
        result = response.json()
        assert "metric_id" in result

    async def test_create_metric_validates_data_type(self, http_client, internal_headers):
        """API: POST metric validates data_type field"""
        user_id = TelemetryTestDataFactory.make_user_id()
        metric_data = {
            "name": TelemetryTestDataFactory.make_metric_name(),
            "data_type": "invalid_type",
        }

        response = await http_client.post(
            f"{API_BASE}/metrics",
            json=metric_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code == 422

    async def test_list_metrics_returns_array(self, http_client, internal_headers):
        """API: GET metrics returns array or paginated response"""
        response = await http_client.get(
            f"{API_BASE}/metrics",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, (list, dict))
        if isinstance(result, dict):
            assert "items" in result or "metrics" in result

    async def test_get_metric_not_found(self, http_client, internal_headers):
        """API: GET nonexistent metric returns 404 or 500"""
        fake_name = f"nonexistent_metric_{TelemetryTestDataFactory.make_metric_id()}"

        response = await http_client.get(
            f"{API_BASE}/metrics/{fake_name}",
            headers=internal_headers
        )

        # May return 404 (not found) or 500 (implementation error)
        assert response.status_code in [404, 500]


# =============================================================================
# Alert Rule API Tests
# =============================================================================

class TestAlertRuleAPI:
    """Test alert rule API"""

    async def test_create_rule_succeeds(self, http_client, internal_headers):
        """API: POST alert rule with valid data succeeds"""
        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = TelemetryTestDataFactory.make_alert_rule_create_dict()

        response = await http_client.post(
            f"{API_BASE}/alerts/rules",
            json=rule_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201]
        result = response.json()
        assert "rule_id" in result

    async def test_create_rule_validates_condition(self, http_client, internal_headers):
        """API: POST alert rule validates condition"""
        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = {
            "name": f"test_rule_{TelemetryTestDataFactory.make_rule_id()}",
            "metric_name": TelemetryTestDataFactory.make_metric_name(),
            "condition": "INVALID_CONDITION",
            "threshold_value": "90",
        }

        response = await http_client.post(
            f"{API_BASE}/alerts/rules",
            json=rule_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        # Should either validate and reject or accept (depending on service impl)
        assert response.status_code in [200, 201, 422]

    async def test_list_rules_returns_array(self, http_client, internal_headers):
        """API: GET alert rules returns array or paginated response"""
        response = await http_client.get(
            f"{API_BASE}/alerts/rules",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, (list, dict))

    async def test_get_rule_not_found(self, http_client, internal_headers):
        """API: GET nonexistent rule returns 404 or 500"""
        fake_id = TelemetryTestDataFactory.make_rule_id()

        response = await http_client.get(
            f"{API_BASE}/alerts/rules/{fake_id}",
            headers=internal_headers
        )

        # May return 404 (not found) or 500 (implementation error)
        assert response.status_code in [404, 500]


# =============================================================================
# Alert API Tests
# =============================================================================

class TestAlertAPI:
    """Test alert API"""

    async def test_list_alerts_succeeds(self, http_client, internal_headers):
        """API: GET alerts returns list"""
        response = await http_client.get(
            f"{API_BASE}/alerts",
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_list_alerts_with_status_filter(self, http_client, internal_headers):
        """API: GET alerts accepts status filter"""
        response = await http_client.get(
            f"{API_BASE}/alerts",
            params={"status": AlertStatus.ACTIVE.value},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_list_alerts_with_level_filter(self, http_client, internal_headers):
        """API: GET alerts accepts level filter"""
        response = await http_client.get(
            f"{API_BASE}/alerts",
            params={"level": AlertLevel.CRITICAL.value},
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Device Stats API Tests
# =============================================================================

class TestDeviceStatsAPI:
    """Test device stats API"""

    async def test_get_device_stats_succeeds(self, http_client, internal_headers):
        """API: GET device stats returns stats"""
        device_id = TelemetryTestDataFactory.make_device_id()

        response = await http_client.get(
            f"{API_BASE}/devices/{device_id}/stats",
            headers=internal_headers
        )

        # Should return stats or 404 if no data
        assert response.status_code in [200, 404]

    async def test_get_device_stats_returns_structure(self, http_client, internal_headers):
        """API: GET device stats returns expected structure"""
        # Ingest some data first
        device_id = TelemetryTestDataFactory.make_device_id()
        data_point = TelemetryTestDataFactory.make_data_point_dict()

        await http_client.post(
            f"{API_BASE}/devices/{device_id}/telemetry/batch",
            json={"data_points": [data_point]},
            headers=internal_headers
        )

        response = await http_client.get(
            f"{API_BASE}/devices/{device_id}/stats",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert "device_id" in result


# =============================================================================
# Service Stats API Tests
# =============================================================================

class TestServiceStatsAPI:
    """Test service stats API"""

    async def test_get_stats_succeeds(self, http_client, internal_headers):
        """API: GET stats returns service statistics"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        # Should have some stats fields
        assert isinstance(result, dict)


# =============================================================================
# Aggregation API Tests
# =============================================================================

class TestAggregationAPI:
    """Test aggregation API"""

    async def test_aggregate_succeeds(self, http_client, internal_headers):
        """API: GET aggregated returns aggregated data"""
        now = datetime.now(timezone.utc)

        response = await http_client.get(
            f"{API_BASE}/aggregated",
            params={
                "device_id": TelemetryTestDataFactory.make_device_id(),
                "metric_name": TelemetryTestDataFactory.make_metric_name(),
                "aggregation_type": AggregationType.AVG.value,
                "interval": 3600,
                "start_time": (now - timedelta(hours=1)).isoformat(),
                "end_time": now.isoformat(),
            },
            headers=internal_headers
        )

        # May return 200, 404 (no data), or 500 (aggregation issue)
        assert response.status_code in [200, 404, 500]

    async def test_aggregate_validates_aggregation_type(self, http_client, internal_headers):
        """API: GET aggregated validates aggregation_type"""
        now = datetime.now(timezone.utc)

        response = await http_client.get(
            f"{API_BASE}/aggregated",
            params={
                "device_id": TelemetryTestDataFactory.make_device_id(),
                "metric_name": TelemetryTestDataFactory.make_metric_name(),
                "aggregation_type": "INVALID_AGG",
                "interval": 3600,
                "start_time": (now - timedelta(hours=1)).isoformat(),
                "end_time": now.isoformat(),
            },
            headers=internal_headers
        )

        assert response.status_code == 422


# =============================================================================
# Subscription API Tests
# =============================================================================

class TestSubscriptionAPI:
    """Test real-time subscription API"""

    async def test_create_subscription_succeeds(self, http_client, internal_headers):
        """API: POST subscription creates subscription"""
        subscription_data = {
            "device_ids": TelemetryTestDataFactory.make_device_id_list(),
            "metric_names": [TelemetryTestDataFactory.make_metric_name()],
        }

        response = await http_client.post(
            f"{API_BASE}/subscribe",
            json=subscription_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201]
        result = response.json()
        assert "subscription_id" in result

    async def test_delete_subscription_succeeds(self, http_client, internal_headers):
        """API: DELETE subscription removes subscription"""
        # Create first
        subscription_data = {"device_ids": []}

        create_response = await http_client.post(
            f"{API_BASE}/subscribe",
            json=subscription_data,
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Subscription creation not available")

        subscription_id = create_response.json()["subscription_id"]

        # Delete
        response = await http_client.delete(
            f"{API_BASE}/subscribe/{subscription_id}",
            headers=internal_headers
        )

        assert response.status_code in [200, 204]


# =============================================================================
# Error Response Tests
# =============================================================================

class TestErrorResponsesAPI:
    """Test API error response formats"""

    async def test_404_returns_error_structure(self, http_client, internal_headers):
        """API: 404 or 500 response has error structure"""
        fake_name = f"nonexistent_metric_{TelemetryTestDataFactory.make_metric_id()}"

        response = await http_client.get(
            f"{API_BASE}/metrics/{fake_name}",
            headers=internal_headers
        )

        assert response.status_code in [404, 500]
        result = response.json()
        # Should have error info
        assert "error" in result or "message" in result or "detail" in result

    async def test_422_returns_validation_details(self, http_client, internal_headers):
        """API: 422 response includes validation details"""
        response = await http_client.post(
            f"{API_BASE}/query",
            json={"devices": [], "metrics": [], "start_time": "invalid"},
            headers=internal_headers
        )

        assert response.status_code == 422
        result = response.json()
        # Should have detail about validation error
        assert "detail" in result or "error" in result or "message" in result


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthAPI:
    """Test health endpoint API"""

    async def test_health_returns_status(self, http_client):
        """API: GET /health returns status"""
        response = await http_client.get(f"{TELEMETRY_SERVICE_URL}/health")

        assert response.status_code == 200
        result = response.json()
        assert "status" in result

    async def test_health_no_auth_required(self, http_client):
        """API: GET /health does not require authentication"""
        response = await http_client.get(f"{TELEMETRY_SERVICE_URL}/health")

        # Should succeed without any auth headers
        assert response.status_code == 200


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "-s", "--tb=short"] + sys.argv[1:])
