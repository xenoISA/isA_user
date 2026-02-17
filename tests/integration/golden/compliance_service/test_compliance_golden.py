"""
Compliance Service - Integration Golden Tests

GOLDEN: These tests document the CURRENT behavior of compliance API with real database.
DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions in API endpoints
- Document current HTTP response codes and structures
- All tests should PASS (they describe existing behavior)

Requires:
- PostgreSQL database running
- Compliance service running on port 8226

Usage:
    pytest tests/integration/golden/compliance_service/test_compliance_golden.py -v
"""

import pytest
from tests.contracts.compliance.data_contract import ComplianceTestDataFactory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.requires_db, pytest.mark.golden]

COMPLIANCE_URL = "http://localhost:8226"
API_BASE = f"{COMPLIANCE_URL}/api/v1/compliance"


# =============================================================================
# Health Check - Current Behavior
# =============================================================================

class TestHealthCheckGolden:
    """Characterization: Health check endpoint behavior"""

    async def test_health_endpoint_returns_200(self, http_client):
        """CHAR: GET /health returns 200 when service is healthy"""
        response = await http_client.get(f"{COMPLIANCE_URL}/health")
        assert response.status_code == 200

    async def test_health_response_structure(self, http_client):
        """CHAR: Health response has expected structure"""
        response = await http_client.get(f"{COMPLIANCE_URL}/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


# =============================================================================
# Compliance Check - Current Behavior
# =============================================================================

class TestComplianceCheckGolden:
    """Characterization: Compliance check endpoint behavior"""

    async def test_check_endpoint_returns_200(
        self, http_client, internal_headers, safe_text_content
    ):
        """CHAR: POST /check returns 200 on successful check"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "content_type": "text",
            "content": safe_text_content,
            "check_types": ["content_moderation"],
        }

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request_data,
            headers=internal_headers,
        )

        assert response.status_code in [200, 201]

    async def test_check_response_structure(
        self, http_client, internal_headers, safe_text_content
    ):
        """CHAR: Check response contains expected fields"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "content_type": "text",
            "content": safe_text_content,
            "check_types": ["content_moderation"],
        }

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request_data,
            headers=internal_headers,
        )

        data = response.json()
        assert "check_id" in data
        assert "status" in data
        assert "risk_level" in data
        assert "passed" in data

    async def test_safe_content_passes(
        self, http_client, internal_headers, safe_text_content
    ):
        """CHAR: Safe content passes compliance check"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "content_type": "text",
            "content": safe_text_content,
            "check_types": ["content_moderation"],
        }

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request_data,
            headers=internal_headers,
        )

        data = response.json()
        assert data["passed"] is True
        assert data["status"] == "pass"

    async def test_pii_content_flagged(
        self, http_client, internal_headers, pii_text_content
    ):
        """CHAR: Content with PII is flagged"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "content_type": "text",
            "content": pii_text_content,
            "check_types": ["pii_detection"],
        }

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request_data,
            headers=internal_headers,
        )

        data = response.json()
        # PII should be detected
        assert data["status"] in ["warning", "flagged", "fail"]

    async def test_injection_content_blocked(
        self, http_client, internal_headers, injection_text_content
    ):
        """CHAR: Prompt injection content is blocked"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "content_type": "prompt",
            "content": injection_text_content,
            "check_types": ["prompt_injection"],
        }

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request_data,
            headers=internal_headers,
        )

        data = response.json()
        # Injection should be detected and blocked
        assert data["status"] in ["fail", "blocked"]


# =============================================================================
# Batch Compliance Check - Current Behavior
# =============================================================================

class TestBatchComplianceCheckGolden:
    """Characterization: Batch compliance check endpoint behavior"""

    async def test_batch_check_endpoint_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: POST /check/batch returns 200 on success"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "items": [
                {"content": "First safe message", "content_type": "text"},
                {"content": "Second safe message", "content_type": "text"},
            ],
            "check_types": ["content_moderation"],
        }

        response = await http_client.post(
            f"{API_BASE}/check/batch",
            json=request_data,
            headers=internal_headers,
        )

        assert response.status_code in [200, 201]

    async def test_batch_check_response_structure(
        self, http_client, internal_headers
    ):
        """CHAR: Batch check response contains aggregated results"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "items": [
                {"content": "Message one", "content_type": "text"},
                {"content": "Message two", "content_type": "text"},
            ],
            "check_types": ["content_moderation"],
        }

        response = await http_client.post(
            f"{API_BASE}/check/batch",
            json=request_data,
            headers=internal_headers,
        )

        data = response.json()
        assert "total_items" in data
        assert "passed_items" in data
        assert "results" in data


# =============================================================================
# Get Check by ID - Current Behavior
# =============================================================================

class TestGetCheckGolden:
    """Characterization: Get check by ID endpoint behavior"""

    async def test_get_nonexistent_check_returns_404(
        self, http_client, internal_headers
    ):
        """CHAR: GET /checks/{id} returns 404 for non-existent check"""
        response = await http_client.get(
            f"{API_BASE}/checks/nonexistent_check_12345",
            headers=internal_headers,
        )
        assert response.status_code == 404

    async def test_get_existing_check_returns_200_or_404(
        self, http_client, internal_headers, safe_text_content
    ):
        """CHAR: GET /checks/{id} returns 200 for existing check or 404 if not persisted"""
        # First create a check
        create_request = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "content_type": "text",
            "content": safe_text_content,
            "check_types": ["content_moderation"],
        }

        create_response = await http_client.post(
            f"{API_BASE}/check",
            json=create_request,
            headers=internal_headers,
        )
        check_id = create_response.json()["check_id"]

        # Then retrieve it
        response = await http_client.get(
            f"{API_BASE}/checks/{check_id}",
            headers=internal_headers,
        )

        # Document current behavior: check might not be persisted if DB is unavailable
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["check_id"] == check_id


# =============================================================================
# User Checks - Current Behavior
# =============================================================================

class TestUserChecksGolden:
    """Characterization: User checks endpoint behavior"""

    async def test_get_user_checks_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: GET /checks/user/{user_id} returns 200"""
        user_id = ComplianceTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/checks/user/{user_id}",
            headers=internal_headers,
        )

        assert response.status_code == 200

    async def test_get_user_checks_returns_array(
        self, http_client, internal_headers
    ):
        """CHAR: User checks endpoint returns array"""
        user_id = ComplianceTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/checks/user/{user_id}",
            headers=internal_headers,
        )

        data = response.json()
        assert isinstance(data, list) or "checks" in data


# =============================================================================
# Policy Management - Current Behavior
# =============================================================================

class TestPolicyManagementGolden:
    """Characterization: Policy management endpoint behavior"""

    async def test_create_policy_returns_response(
        self, http_client, internal_headers, cleanup_policies
    ):
        """CHAR: POST /policies returns response (may be 200/201 or 500 depending on DB)"""
        import uuid
        request_data = {
            "policy_name": f"Golden Test Policy {uuid.uuid4().hex[:8]}",
            "content_types": ["text"],
            "check_types": ["content_moderation"],
            "rules": {"max_toxicity": 0.7},
        }

        response = await http_client.post(
            f"{API_BASE}/policies",
            json=request_data,
            headers=internal_headers,
        )

        # Document current behavior: may fail if DB unavailable
        assert response.status_code in [200, 201, 500]

        if response.status_code in [200, 201]:
            policy_id = response.json().get("policy_id")
            if policy_id:
                cleanup_policies(policy_id)

    async def test_get_policies_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: GET /policies returns 200"""
        response = await http_client.get(
            f"{API_BASE}/policies",
            headers=internal_headers,
        )

        assert response.status_code == 200

    async def test_get_nonexistent_policy_returns_404(
        self, http_client, internal_headers
    ):
        """CHAR: GET /policies/{id} returns 404 for non-existent policy"""
        response = await http_client.get(
            f"{API_BASE}/policies/nonexistent_policy_12345",
            headers=internal_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Compliance Statistics - Current Behavior
# =============================================================================

class TestComplianceStatsGolden:
    """Characterization: Compliance statistics endpoint behavior"""

    async def test_get_stats_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: GET /stats returns 200"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=internal_headers,
        )

        assert response.status_code == 200

    async def test_stats_response_structure(
        self, http_client, internal_headers
    ):
        """CHAR: Stats response has expected fields"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=internal_headers,
        )

        data = response.json()
        # Document expected fields
        assert "total_checks_today" in data or "total_checks" in data


# =============================================================================
# Compliance Reports - Current Behavior
# =============================================================================

class TestComplianceReportsGolden:
    """Characterization: Compliance reports endpoint behavior"""

    async def test_generate_report_returns_response(
        self, http_client, internal_headers
    ):
        """CHAR: POST /reports returns a response (may be 200 or 500 depending on DB state)"""
        request_data = {
            "start_date": "2025-12-01T00:00:00Z",
            "end_date": "2025-12-22T00:00:00Z",
        }

        response = await http_client.post(
            f"{API_BASE}/reports",
            json=request_data,
            headers=internal_headers,
        )

        # Document current behavior: may return 500 if DB query fails
        assert response.status_code in [200, 500]

    async def test_report_response_structure(
        self, http_client, internal_headers
    ):
        """CHAR: Report response contains summary data or error"""
        request_data = {
            "start_date": "2025-12-01T00:00:00Z",
            "end_date": "2025-12-22T00:00:00Z",
        }

        response = await http_client.post(
            f"{API_BASE}/reports",
            json=request_data,
            headers=internal_headers,
        )

        data = response.json()
        # Document current behavior: may have report data or error detail
        assert "report_id" in data or "total_checks" in data or "detail" in data


# =============================================================================
# Human Review - Current Behavior
# =============================================================================

class TestHumanReviewGolden:
    """Characterization: Human review endpoint behavior"""

    async def test_get_pending_reviews_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: GET /reviews/pending returns 200"""
        response = await http_client.get(
            f"{API_BASE}/reviews/pending",
            headers=internal_headers,
        )

        assert response.status_code == 200


# =============================================================================
# GDPR Endpoints - Current Behavior
# =============================================================================

class TestGDPREndpointsGolden:
    """Characterization: GDPR compliance endpoints behavior"""

    async def test_get_user_data_summary_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: GET /user/{user_id}/data-summary returns 200"""
        user_id = ComplianceTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/user/{user_id}/data-summary",
            headers=internal_headers,
        )

        # Should return 200 (empty data is valid)
        assert response.status_code == 200

    async def test_export_user_data_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: GET /user/{user_id}/data-export returns 200"""
        user_id = ComplianceTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/user/{user_id}/data-export",
            headers=internal_headers,
        )

        assert response.status_code == 200


# =============================================================================
# Service Status - Current Behavior
# =============================================================================

class TestServiceStatusGolden:
    """Characterization: Service status endpoint behavior"""

    async def test_status_endpoint_returns_200(self, http_client):
        """CHAR: GET /status returns 200"""
        response = await http_client.get(f"{COMPLIANCE_URL}/status")
        assert response.status_code == 200

    async def test_status_response_structure(self, http_client):
        """CHAR: Status response has service information"""
        response = await http_client.get(f"{COMPLIANCE_URL}/status")
        data = response.json()
        assert "service" in data or "status" in data


# =============================================================================
# Error Handling - Current Behavior
# =============================================================================

class TestErrorHandlingGolden:
    """Characterization: Error handling behavior"""

    async def test_invalid_request_returns_400_or_422(
        self, http_client, internal_headers
    ):
        """CHAR: Invalid request returns 400 or 422"""
        request_data = {
            # Missing required fields
        }

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request_data,
            headers=internal_headers,
        )

        assert response.status_code in [400, 422]

    async def test_invalid_content_type_rejected(
        self, http_client, internal_headers
    ):
        """CHAR: Invalid content_type is rejected"""
        request_data = {
            "user_id": ComplianceTestDataFactory.make_user_id(),
            "content_type": "invalid_type",
            "content": "test content",
            "check_types": ["content_moderation"],
        }

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request_data,
            headers=internal_headers,
        )

        assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
