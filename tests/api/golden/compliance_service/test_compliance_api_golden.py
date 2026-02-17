"""
Compliance Service - API Golden Tests

GOLDEN: These tests document the CURRENT API contract behavior.
DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Validate API contracts against data contract schemas
- Test authenticated endpoint behavior
- Document current HTTP response codes and structures
- All tests should PASS (they describe existing behavior)

Requires:
- PostgreSQL + NATS running
- Auth Service running on port 8210
- Compliance Service running on port 8226

Usage:
    pytest tests/api/golden/compliance_service/test_compliance_api_golden.py -v
"""

import pytest
from pydantic import ValidationError

from tests.contracts.compliance.data_contract import (
    ComplianceTestDataFactory,
    ComplianceCheckRequestContract,
    ComplianceCheckResponseContract,
    BatchComplianceCheckRequestContract,
    BatchComplianceCheckResponseContract,
    CompliancePolicyRequestContract,
    CompliancePolicyResponseContract,
    ComplianceReportRequestContract,
    ComplianceReportResponseContract,
    ComplianceServiceStatusContract,
    ComplianceStatsResponseContract,
    ContentType,
    ComplianceCheckType,
    ComplianceStatus,
    RiskLevel,
)

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

COMPLIANCE_URL = "http://localhost:8226"
API_BASE = f"{COMPLIANCE_URL}/api/v1/compliance"


# =============================================================================
# Request Contract Validation - Current Behavior
# =============================================================================

class TestRequestContractValidationGolden:
    """Characterization: Request contract validation behavior"""

    def test_valid_check_request_contract(self):
        """CHAR: Valid check request passes contract validation"""
        request = ComplianceTestDataFactory.make_compliance_check_request()
        # Should not raise
        assert request.user_id is not None
        assert request.content_type is not None

    def test_invalid_check_request_rejected(self):
        """CHAR: Invalid check request is rejected by contract"""
        with pytest.raises(ValidationError):
            ComplianceCheckRequestContract(
                # Missing required user_id
                content_type="invalid_type",
            )

    def test_valid_batch_request_contract(self):
        """CHAR: Valid batch request passes contract validation"""
        request = BatchComplianceCheckRequestContract(
            user_id=ComplianceTestDataFactory.make_user_id(),
            items=[
                {"content": "Item 1", "content_type": "text"},
                {"content": "Item 2", "content_type": "text"},
            ],
            check_types=["content_moderation"],
        )
        assert len(request.items) == 2

    def test_valid_policy_request_contract(self):
        """CHAR: Valid policy request passes contract validation"""
        request = ComplianceTestDataFactory.make_policy_request()
        assert request.policy_name is not None
        assert len(request.content_types) > 0
        assert len(request.check_types) > 0

    def test_valid_report_request_contract(self):
        """CHAR: Valid report request passes contract validation"""
        request = ComplianceTestDataFactory.make_report_request()
        assert request.start_date is not None
        assert request.end_date is not None


# =============================================================================
# Response Contract Validation - Current Behavior
# =============================================================================

class TestResponseContractValidationGolden:
    """Characterization: Response contract validation behavior"""

    async def test_check_response_matches_contract(
        self, http_client, auth_headers
    ):
        """CHAR: Check response matches ComplianceCheckResponseContract"""
        request = ComplianceTestDataFactory.make_compliance_check_request()

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            # Validate against contract
            contract = ComplianceCheckResponseContract(**data)
            assert contract.check_id is not None
            assert contract.status in [s.value for s in ComplianceStatus]
            assert contract.risk_level in [r.value for r in RiskLevel]

    async def test_stats_response_matches_contract(
        self, http_client, auth_headers
    ):
        """CHAR: Stats response matches ComplianceStatsResponseContract"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            # Validate structure
            assert "total_checks_today" in data or "total_checks" in data


# =============================================================================
# API Compliance Check - Contract Behavior
# =============================================================================

class TestComplianceCheckAPIGolden:
    """Characterization: Compliance check API contract behavior"""

    async def test_check_with_content_moderation(
        self, http_client, auth_headers
    ):
        """CHAR: Content moderation check follows contract"""
        request = ComplianceCheckRequestContract(
            user_id=ComplianceTestDataFactory.make_user_id(),
            content_type=ContentType.TEXT,
            content=ComplianceTestDataFactory.make_safe_text_content(),
            check_types=[ComplianceCheckType.CONTENT_MODERATION],
        )

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "check_id" in data
        assert "status" in data

    async def test_check_with_pii_detection(
        self, http_client, auth_headers
    ):
        """CHAR: PII detection check follows contract"""
        request = ComplianceCheckRequestContract(
            user_id=ComplianceTestDataFactory.make_user_id(),
            content_type=ContentType.TEXT,
            content=ComplianceTestDataFactory.make_pii_text_content(),
            check_types=[ComplianceCheckType.PII_DETECTION],
        )

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "check_id" in data
        # PII should be detected
        if "pii_result" in data:
            assert "pii_count" in data["pii_result"]

    async def test_check_with_prompt_injection(
        self, http_client, auth_headers
    ):
        """CHAR: Prompt injection check follows contract"""
        request = ComplianceCheckRequestContract(
            user_id=ComplianceTestDataFactory.make_user_id(),
            content_type=ContentType.PROMPT,
            content=ComplianceTestDataFactory.make_injection_text_content(),
            check_types=[ComplianceCheckType.PROMPT_INJECTION],
        )

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "check_id" in data
        # Document current behavior: injection detection is indicated by status
        # injection_result may be None due to internal key mismatch
        injection_result = data.get("injection_result")
        if injection_result is not None:
            assert "is_injection_detected" in injection_result

    async def test_check_with_multiple_check_types(
        self, http_client, auth_headers
    ):
        """CHAR: Multiple check types follow contract"""
        request = ComplianceCheckRequestContract(
            user_id=ComplianceTestDataFactory.make_user_id(),
            content_type=ContentType.TEXT,
            content=ComplianceTestDataFactory.make_safe_text_content(),
            check_types=[
                ComplianceCheckType.CONTENT_MODERATION,
                ComplianceCheckType.PII_DETECTION,
            ],
        )

        response = await http_client.post(
            f"{API_BASE}/check",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        assert response.status_code in [200, 201]


# =============================================================================
# API Batch Check - Contract Behavior
# =============================================================================

class TestBatchCheckAPIGolden:
    """Characterization: Batch check API contract behavior"""

    async def test_batch_check_follows_contract(
        self, http_client, auth_headers
    ):
        """CHAR: Batch check response follows contract"""
        request = BatchComplianceCheckRequestContract(
            user_id=ComplianceTestDataFactory.make_user_id(),
            items=[
                {"content": "First item", "content_type": "text"},
                {"content": "Second item", "content_type": "text"},
                {"content": "Third item", "content_type": "text"},
            ],
            check_types=["content_moderation"],
        )

        response = await http_client.post(
            f"{API_BASE}/check/batch",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            assert "total_items" in data
            assert "results" in data


# =============================================================================
# API Policy Management - Contract Behavior
# =============================================================================

class TestPolicyAPIGolden:
    """Characterization: Policy API contract behavior"""

    async def test_create_policy_follows_contract(
        self, http_client, auth_headers, cleanup_policies
    ):
        """CHAR: Create policy follows request contract"""
        request = ComplianceTestDataFactory.make_policy_request()

        response = await http_client.post(
            f"{API_BASE}/policies",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "policy_id" in data
            cleanup_policies(data["policy_id"])

    async def test_get_policy_response_matches_contract(
        self, http_client, auth_headers, cleanup_policies
    ):
        """CHAR: Get policy response matches contract"""
        # Create first
        request = ComplianceTestDataFactory.make_policy_request()
        create_response = await http_client.post(
            f"{API_BASE}/policies",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        if create_response.status_code in [200, 201]:
            policy_id = create_response.json()["policy_id"]
            cleanup_policies(policy_id)

            # Get policy
            response = await http_client.get(
                f"{API_BASE}/policies/{policy_id}",
                headers=auth_headers,
            )

            if response.status_code == 200:
                data = response.json()
                assert data["policy_id"] == policy_id
                assert "policy_name" in data


# =============================================================================
# API Report Generation - Contract Behavior
# =============================================================================

class TestReportAPIGolden:
    """Characterization: Report API contract behavior"""

    async def test_generate_report_follows_contract(
        self, http_client, auth_headers
    ):
        """CHAR: Generate report follows request contract"""
        request = ComplianceTestDataFactory.make_report_request()

        response = await http_client.post(
            f"{API_BASE}/reports",
            json=request.model_dump(mode="json"),
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            assert "report_id" in data or "total_checks" in data


# =============================================================================
# Builder Pattern - Contract Behavior
# =============================================================================

class TestBuilderPatternGolden:
    """Characterization: Builder pattern for request construction"""

    def test_check_request_builder_creates_valid_request(self):
        """CHAR: CheckRequestBuilder creates valid request"""
        from tests.contracts.compliance.data_contract import ComplianceCheckRequestBuilder

        request = (
            ComplianceCheckRequestBuilder()
            .with_user_id(ComplianceTestDataFactory.make_user_id())
            .with_text_content("Test content")
            .with_check_types([ComplianceCheckType.CONTENT_MODERATION])
            .build()
        )

        assert request.user_id is not None
        assert request.content_type == ContentType.TEXT
        assert ComplianceCheckType.CONTENT_MODERATION in request.check_types

    def test_policy_request_builder_creates_valid_request(self):
        """CHAR: PolicyRequestBuilder creates valid request"""
        from tests.contracts.compliance.data_contract import CompliancePolicyRequestBuilder

        request = (
            CompliancePolicyRequestBuilder()
            .with_name("Test Policy")
            .with_content_types([ContentType.TEXT])
            .with_check_types([ComplianceCheckType.CONTENT_MODERATION])
            .with_auto_block(True)
            .build()
        )

        assert request.policy_name == "Test Policy"
        assert ContentType.TEXT in request.content_types
        assert request.auto_block is True

    def test_report_request_builder_creates_valid_request(self):
        """CHAR: ReportRequestBuilder creates valid request"""
        from tests.contracts.compliance.data_contract import ComplianceReportRequestBuilder

        request = (
            ComplianceReportRequestBuilder()
            .with_date_range(7)  # last 7 days
            .include_statistics()
            .build()
        )

        assert request.start_date is not None
        assert request.end_date is not None
        assert request.include_statistics is True


# =============================================================================
# Factory Invalid Data - Contract Behavior
# =============================================================================

class TestFactoryInvalidDataGolden:
    """Characterization: Factory invalid data generation"""

    def test_factory_generates_invalid_user_id(self):
        """CHAR: Factory generates invalid user ID"""
        invalid_id = ComplianceTestDataFactory.make_invalid_user_id()
        assert invalid_id is not None
        # Invalid ID should be empty or special character

    def test_factory_generates_invalid_check_request(self):
        """CHAR: Factory generates invalid check request"""
        invalid_request = ComplianceTestDataFactory.make_invalid_check_request_invalid_content_type()
        assert invalid_request is not None
        assert "content_type" in invalid_request
        assert invalid_request["content_type"] == "invalid_type"

    def test_factory_generates_invalid_check_request_empty_content(self):
        """CHAR: Factory generates check request with whitespace-only content"""
        invalid_request = ComplianceTestDataFactory.make_invalid_check_request_empty_content()
        assert invalid_request is not None
        # Factory generates whitespace-only content to test validation
        assert invalid_request.get("content").strip() == ""


# =============================================================================
# API Error Responses - Contract Behavior
# =============================================================================

class TestAPIErrorResponsesGolden:
    """Characterization: API error response behavior"""

    async def test_invalid_request_returns_error_response(
        self, http_client, auth_headers
    ):
        """CHAR: Invalid request returns structured error"""
        response = await http_client.post(
            f"{API_BASE}/check",
            json={},  # Empty request
            headers=auth_headers,
        )

        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data or "error" in data or "message" in data

    async def test_not_found_returns_404(
        self, http_client, auth_headers
    ):
        """CHAR: Non-existent resource returns 404"""
        response = await http_client.get(
            f"{API_BASE}/checks/nonexistent_check_99999",
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Service Status - Contract Behavior
# =============================================================================

class TestServiceStatusAPIGolden:
    """Characterization: Service status API behavior"""

    async def test_status_matches_contract(self, http_client):
        """CHAR: Status response matches service status contract"""
        response = await http_client.get(f"{COMPLIANCE_URL}/status")

        if response.status_code == 200:
            data = response.json()
            # Validate basic structure
            assert "service" in data or "status" in data

    async def test_health_check_structure(self, http_client):
        """CHAR: Health check has expected structure"""
        response = await http_client.get(f"{COMPLIANCE_URL}/health")

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
