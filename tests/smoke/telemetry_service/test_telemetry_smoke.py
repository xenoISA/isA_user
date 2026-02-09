"""
Telemetry Service Smoke Tests

Quick sanity checks to verify telemetry_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Purpose:
- Verify service is up and responding
- Test basic CRUD operations work
- Test critical user flows (ingest, query, create rules, trigger alerts)
- Validate data contracts are honored

Usage:
    pytest tests/smoke/telemetry -v
    pytest tests/smoke/telemetry -v -k "health"

Environment Variables:
    TELEMETRY_BASE_URL: Base URL for telemetry service (default: http://localhost:8225)
"""

import os
import pytest
import uuid
import httpx
from datetime import datetime, timezone, timedelta

from tests.contracts.telemetry.data_contract import (
    TelemetryTestDataFactory,
    DataType,
    AggregationType,
)

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("TELEMETRY_BASE_URL", "http://localhost:8225")
API_V1 = f"{BASE_URL}/api/v1/telemetry"
TIMEOUT = 10.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_device_id() -> str:
    """Generate unique device ID for smoke tests"""
    return f"smoke_device_{uuid.uuid4().hex[:8]}"


def unique_metric_name() -> str:
    """Generate unique metric name for smoke tests"""
    return f"smoke_metric_{uuid.uuid4().hex[:8]}"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client for smoke tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def internal_headers() -> dict:
    """Headers for internal calls (bypass auth)"""
    return {
        "X-Internal-Call": "true",
        "Content-Type": "application/json",
    }


@pytest.fixture
async def test_metric(http_client, internal_headers):
    """
    Create a test metric definition for smoke tests.

    This fixture creates a metric, yields it for testing,
    and cleans it up afterward.
    """
    user_id = TelemetryTestDataFactory.make_user_id()
    metric_data = TelemetryTestDataFactory.make_metric_definition_create_dict()

    # Create metric
    response = await http_client.post(
        f"{API_V1}/metrics",
        json=metric_data,
        headers={**internal_headers, "X-User-ID": user_id}
    )

    if response.status_code in [200, 201]:
        result = response.json()
        result["_test_name"] = metric_data["name"]
        yield result

        # Cleanup - try to delete the metric
        try:
            await http_client.delete(
                f"{API_V1}/metrics/{metric_data['name']}",
                headers=internal_headers
            )
        except Exception:
            pass  # Ignore cleanup errors
    else:
        pytest.skip(f"Could not create test metric: {response.status_code}")


@pytest.fixture
async def test_alert_rule(http_client, internal_headers):
    """
    Create a test alert rule for smoke tests.
    """
    user_id = TelemetryTestDataFactory.make_user_id()
    rule_data = TelemetryTestDataFactory.make_alert_rule_create_dict()

    # Create rule
    response = await http_client.post(
        f"{API_V1}/alerts/rules",
        json=rule_data,
        headers={**internal_headers, "X-User-ID": user_id}
    )

    if response.status_code in [200, 201]:
        result = response.json()
        yield result
        # Note: DELETE endpoint not implemented, so we just leave it
    else:
        pytest.skip(f"Could not create test alert rule: {response.status_code}")


# =============================================================================
# SMOKE TEST 1: Health Checks
# =============================================================================

class TestHealthSmoke:
    """Smoke: Health endpoint sanity checks"""

    async def test_health_endpoint_responds(self, http_client):
        """SMOKE: GET /health returns 200"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, \
            f"Health check failed: {response.status_code}"

    async def test_health_returns_status(self, http_client):
        """SMOKE: GET /health returns status field"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data, "Health response missing 'status' field"


# =============================================================================
# SMOKE TEST 2: Telemetry Data Ingestion
# =============================================================================

class TestTelemetryIngestSmoke:
    """Smoke: Telemetry data ingestion sanity checks"""

    async def test_ingest_single_data_point_works(self, http_client, internal_headers):
        """SMOKE: POST /devices/{id}/telemetry/batch ingests data"""
        device_id = unique_device_id()
        data_point = TelemetryTestDataFactory.make_data_point_dict()

        response = await http_client.post(
            f"{API_V1}/devices/{device_id}/telemetry/batch",
            json={"data_points": [data_point]},
            headers=internal_headers
        )

        assert response.status_code in [200, 201], \
            f"Ingest single point failed: {response.status_code} - {response.text}"

        result = response.json()
        assert result.get("success") is True or result.get("ingested_count", 0) >= 1

    async def test_ingest_multiple_data_points_works(self, http_client, internal_headers):
        """SMOKE: POST /devices/{id}/telemetry/batch ingests multiple points"""
        device_id = unique_device_id()
        data_points = [
            TelemetryTestDataFactory.make_data_point_dict()
            for _ in range(5)
        ]

        response = await http_client.post(
            f"{API_V1}/devices/{device_id}/telemetry/batch",
            json={"data_points": data_points},
            headers=internal_headers
        )

        assert response.status_code in [200, 201], \
            f"Ingest multiple points failed: {response.status_code}"

        result = response.json()
        assert result.get("ingested_count", 0) >= 5 or result.get("success") is True

    async def test_ingest_empty_batch_rejected(self, http_client, internal_headers):
        """SMOKE: POST /devices/{id}/telemetry/batch rejects empty batch"""
        device_id = unique_device_id()

        response = await http_client.post(
            f"{API_V1}/devices/{device_id}/telemetry/batch",
            json={"data_points": []},
            headers=internal_headers
        )

        assert response.status_code == 422, \
            f"Expected 422 for empty batch, got {response.status_code}"


# =============================================================================
# SMOKE TEST 3: Telemetry Query
# =============================================================================

class TestTelemetryQuerySmoke:
    """Smoke: Telemetry query sanity checks"""

    async def test_query_endpoint_works(self, http_client, internal_headers):
        """SMOKE: POST /query returns results"""
        now = datetime.now(timezone.utc)
        query_params = {
            "devices": [unique_device_id()],
            "metrics": [unique_metric_name()],
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": now.isoformat(),
        }

        response = await http_client.post(
            f"{API_V1}/query",
            json=query_params,
            headers=internal_headers
        )

        # May return 200 with empty data or 404 if no data
        assert response.status_code in [200, 404], \
            f"Query failed: {response.status_code}"

    async def test_query_returns_data_structure(self, http_client, internal_headers):
        """SMOKE: POST /query returns correct data structure"""
        # First ingest some data
        device_id = unique_device_id()
        metric_name = unique_metric_name()
        now = datetime.now(timezone.utc)

        data_point = TelemetryTestDataFactory.make_data_point_dict(
            metric_name=metric_name,
            timestamp=now.isoformat()
        )

        await http_client.post(
            f"{API_V1}/devices/{device_id}/telemetry/batch",
            json={"data_points": [data_point]},
            headers=internal_headers
        )

        # Query the data
        query_params = {
            "devices": [device_id],
            "metrics": [metric_name],
            "start_time": (now - timedelta(minutes=5)).isoformat(),
            "end_time": (now + timedelta(minutes=5)).isoformat(),
        }

        response = await http_client.post(
            f"{API_V1}/query",
            json=query_params,
            headers=internal_headers
        )

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            result = response.json()
            assert "data_points" in result or "count" in result


# =============================================================================
# SMOKE TEST 4: Metric Definitions
# =============================================================================

class TestMetricDefinitionSmoke:
    """Smoke: Metric definition sanity checks"""

    async def test_create_metric_works(self, http_client, internal_headers):
        """SMOKE: POST /metrics creates metric definition"""
        user_id = TelemetryTestDataFactory.make_user_id()
        metric_data = TelemetryTestDataFactory.make_metric_definition_create_dict()

        response = await http_client.post(
            f"{API_V1}/metrics",
            json=metric_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201], \
            f"Create metric failed: {response.status_code} - {response.text}"

        result = response.json()
        assert "metric_id" in result, "Response missing metric_id"

        # Cleanup
        await http_client.delete(
            f"{API_V1}/metrics/{metric_data['name']}",
            headers=internal_headers
        )

    async def test_list_metrics_works(self, http_client, internal_headers):
        """SMOKE: GET /metrics returns list"""
        response = await http_client.get(
            f"{API_V1}/metrics",
            headers=internal_headers
        )

        assert response.status_code == 200, \
            f"List metrics failed: {response.status_code}"

        result = response.json()
        assert "items" in result or "metrics" in result or isinstance(result, list)

    async def test_get_metric_works(self, http_client, internal_headers, test_metric):
        """SMOKE: GET /metrics/{name} retrieves metric"""
        metric_name = test_metric["_test_name"]

        response = await http_client.get(
            f"{API_V1}/metrics/{metric_name}",
            headers=internal_headers
        )

        assert response.status_code == 200, \
            f"Get metric failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 5: Alert Rules
# =============================================================================

class TestAlertRuleSmoke:
    """Smoke: Alert rule sanity checks"""

    async def test_create_alert_rule_works(self, http_client, internal_headers):
        """SMOKE: POST /alerts/rules creates alert rule"""
        user_id = TelemetryTestDataFactory.make_user_id()
        rule_data = TelemetryTestDataFactory.make_alert_rule_create_dict()

        response = await http_client.post(
            f"{API_V1}/alerts/rules",
            json=rule_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201], \
            f"Create alert rule failed: {response.status_code} - {response.text}"

        result = response.json()
        assert "rule_id" in result, "Response missing rule_id"

    async def test_list_alert_rules_works(self, http_client, internal_headers):
        """SMOKE: GET /alerts/rules returns list"""
        response = await http_client.get(
            f"{API_V1}/alerts/rules",
            headers=internal_headers
        )

        assert response.status_code == 200, \
            f"List alert rules failed: {response.status_code}"

    async def test_get_alert_rule_works(self, http_client, internal_headers, test_alert_rule):
        """SMOKE: GET /alerts/rules/{id} retrieves rule"""
        rule_id = test_alert_rule["rule_id"]

        response = await http_client.get(
            f"{API_V1}/alerts/rules/{rule_id}",
            headers=internal_headers
        )

        assert response.status_code == 200, \
            f"Get alert rule failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 6: Alerts
# =============================================================================

class TestAlertSmoke:
    """Smoke: Alert sanity checks"""

    async def test_list_alerts_works(self, http_client, internal_headers):
        """SMOKE: GET /alerts returns list"""
        response = await http_client.get(
            f"{API_V1}/alerts",
            headers=internal_headers
        )

        assert response.status_code == 200, \
            f"List alerts failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 7: Stats
# =============================================================================

class TestStatsSmoke:
    """Smoke: Service stats sanity checks"""

    async def test_service_stats_works(self, http_client, internal_headers):
        """SMOKE: GET /stats returns service statistics"""
        response = await http_client.get(
            f"{API_V1}/stats",
            headers=internal_headers
        )

        assert response.status_code == 200, \
            f"Get stats failed: {response.status_code}"

        result = response.json()
        # Should have some stats fields
        assert any(key in result for key in [
            "total_devices", "total_metrics", "total_data_points",
            "active_devices"
        ])

    async def test_device_stats_works(self, http_client, internal_headers):
        """SMOKE: GET /devices/{id}/stats returns device stats"""
        # First ingest some data
        device_id = unique_device_id()
        data_point = TelemetryTestDataFactory.make_data_point_dict()

        await http_client.post(
            f"{API_V1}/devices/{device_id}/telemetry/batch",
            json={"data_points": [data_point]},
            headers=internal_headers
        )

        response = await http_client.get(
            f"{API_V1}/devices/{device_id}/stats",
            headers=internal_headers
        )

        assert response.status_code == 200, \
            f"Get device stats failed: {response.status_code}"

        result = response.json()
        assert "device_id" in result


# =============================================================================
# SMOKE TEST 8: Real-Time Subscriptions
# =============================================================================

class TestSubscriptionSmoke:
    """Smoke: Real-time subscription sanity checks"""

    async def test_create_subscription_works(self, http_client, internal_headers):
        """SMOKE: POST /subscribe creates subscription"""
        subscription_data = {
            "device_ids": [unique_device_id()],
            "metric_names": [unique_metric_name()],
        }

        response = await http_client.post(
            f"{API_V1}/subscribe",
            json=subscription_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201], \
            f"Create subscription failed: {response.status_code}"

        result = response.json()
        assert "subscription_id" in result

        # Cleanup - unsubscribe
        sub_id = result["subscription_id"]
        await http_client.delete(
            f"{API_V1}/subscribe/{sub_id}",
            headers=internal_headers
        )


# =============================================================================
# SMOKE TEST 9: Critical User Flow
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical user flow end-to-end"""

    async def test_complete_telemetry_lifecycle(self, http_client, internal_headers):
        """
        SMOKE: Complete telemetry lifecycle works end-to-end

        Tests: Ingest -> Query -> Verify
        """
        device_id = unique_device_id()
        metric_name = unique_metric_name()
        now = datetime.now(timezone.utc)
        test_value = 42.5

        try:
            # Step 1: Ingest data
            data_point = TelemetryTestDataFactory.make_data_point_dict(
                metric_name=metric_name,
                value=test_value,
                timestamp=now.isoformat()
            )

            ingest_response = await http_client.post(
                f"{API_V1}/devices/{device_id}/telemetry/batch",
                json={"data_points": [data_point]},
                headers=internal_headers
            )
            assert ingest_response.status_code in [200, 201], "Failed to ingest data"

            # Step 2: Query data
            query_params = {
                "devices": [device_id],
                "metrics": [metric_name],
                "start_time": (now - timedelta(minutes=1)).isoformat(),
                "end_time": (now + timedelta(minutes=1)).isoformat(),
            }

            query_response = await http_client.post(
                f"{API_V1}/query",
                json=query_params,
                headers=internal_headers
            )
            assert query_response.status_code in [200, 404], "Query failed"

            # Step 3: Get device stats
            stats_response = await http_client.get(
                f"{API_V1}/devices/{device_id}/stats",
                headers=internal_headers
            )
            assert stats_response.status_code == 200, "Failed to get device stats"
            assert stats_response.json()["device_id"] == device_id

        except AssertionError:
            raise
        except Exception as e:
            pytest.fail(f"Telemetry lifecycle test failed with error: {e}")


# =============================================================================
# SMOKE TEST 10: Error Handling
# =============================================================================

class TestErrorHandlingSmoke:
    """Smoke: Error handling sanity checks"""

    async def test_not_found_returns_error(self, http_client, internal_headers):
        """SMOKE: Non-existent metric returns 404 or 500"""
        fake_metric_name = f"nonexistent_{uuid.uuid4().hex[:8]}"

        response = await http_client.get(
            f"{API_V1}/metrics/{fake_metric_name}",
            headers=internal_headers
        )

        assert response.status_code in [404, 500], \
            f"Expected 404/500, got {response.status_code}"

    async def test_invalid_request_returns_error(self, http_client, internal_headers):
        """SMOKE: Invalid request returns 422"""
        response = await http_client.post(
            f"{API_V1}/query",
            json={"start_time": "invalid-date"},
            headers=internal_headers
        )

        assert response.status_code == 422, \
            f"Expected 422, got {response.status_code}"

    async def test_unauthenticated_request_returns_401(self, http_client):
        """SMOKE: Request without auth returns 401"""
        response = await http_client.get(f"{API_V1}/metrics")

        assert response.status_code == 401, \
            f"Expected 401, got {response.status_code}"


# =============================================================================
# SUMMARY
# =============================================================================
"""
TELEMETRY SERVICE SMOKE TESTS SUMMARY:

Test Coverage (18 tests total):

1. Health (2 tests):
   - /health responds with 200
   - /health returns status field

2. Telemetry Ingestion (3 tests):
   - Ingest single data point works
   - Ingest multiple data points works
   - Empty batch rejected with 422

3. Telemetry Query (2 tests):
   - Query endpoint works
   - Query returns correct data structure

4. Metric Definitions (3 tests):
   - Create metric works
   - List metrics works
   - Get metric works

5. Alert Rules (3 tests):
   - Create alert rule works
   - List alert rules works
   - Get alert rule works

6. Alerts (1 test):
   - List alerts works

7. Stats (2 tests):
   - Service stats works
   - Device stats works

8. Subscriptions (1 test):
   - Create subscription works

9. Critical Flow (1 test):
   - Complete lifecycle: Ingest -> Query -> Stats

10. Error Handling (3 tests):
    - Not found returns error
    - Invalid request returns 422
    - Unauthenticated returns 401

Characteristics:
- Fast execution (< 30 seconds)
- No external dependencies (other than running telemetry_service)
- Tests critical paths only
- Validates deployment health

Run with:
    pytest tests/smoke/telemetry -v
    pytest tests/smoke/telemetry -v --timeout=60
"""
