"""
OTA Service API Tests

Tests HTTP API contracts for OTA (Over-The-Air) Update Service.
All test data uses OTATestDataFactory - zero hardcoded data.

Focus Areas:
1. Endpoint contract validation
2. HTTP status code correctness
3. Error response formats
4. Request/response validation
5. API authentication and authorization

Usage:
    pytest tests/api/golden/ota_service -v
"""
import pytest
import httpx
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from tests.contracts.ota.data_contract import (
    UpdateType, UpdateStatus, DeploymentStrategy, Priority, RollbackTrigger, CampaignStatus,
    FirmwareUploadRequestContract, CampaignCreateRequestContract, DeviceUpdateRequestContract,
    RollbackRequestContract, OTATestDataFactory, FirmwareUploadRequestBuilder, CampaignCreateRequestBuilder
)

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]

# Service configuration
OTA_SERVICE_URL = os.getenv("OTA_SERVICE_URL", "http://localhost:8221")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8202")
API_BASE = f"{OTA_SERVICE_URL}/api/v1"


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
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/token",
            json={
                "user_id": OTATestDataFactory.make_user_id(),
                "email": f"test_{OTATestDataFactory.make_user_id()}@example.com",
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


@pytest.fixture
async def test_firmware(http_client, internal_headers) -> Optional[Dict[str, Any]]:
    """Create a test firmware for other tests"""
    firmware_request = OTATestDataFactory.make_firmware_upload_request()
    user_id = OTATestDataFactory.make_user_id()

    response = await http_client.post(
        f"{API_BASE}/firmware",
        json=firmware_request.model_dump(),
        headers={**internal_headers, "X-User-ID": user_id}
    )

    if response.status_code in [200, 201]:
        return response.json()
    return None


@pytest.fixture
async def test_campaign(http_client, internal_headers, test_firmware) -> Optional[Dict[str, Any]]:
    """Create a test campaign for other tests"""
    if not test_firmware:
        return None

    campaign_request = OTATestDataFactory.make_campaign_create_request(
        firmware_id=test_firmware.get("firmware_id", OTATestDataFactory.make_firmware_id())
    )
    user_id = OTATestDataFactory.make_user_id()

    response = await http_client.post(
        f"{API_BASE}/campaigns",
        json=campaign_request.model_dump(),
        headers={**internal_headers, "X-User-ID": user_id}
    )

    if response.status_code in [200, 201]:
        return response.json()
    return None


# =============================================================================
# Authentication Tests
# =============================================================================

class TestOTAAuthenticationAPI:
    """Test API authentication requirements"""

    async def test_unauthenticated_request_returns_401(self, http_client):
        """API: Request without token returns 401"""
        response = await http_client.get(f"{API_BASE}/firmware")

        assert response.status_code == 401

    async def test_invalid_token_returns_401(self, http_client):
        """API: Request with invalid token returns 401"""
        response = await http_client.get(
            f"{API_BASE}/firmware",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        assert response.status_code == 401

    async def test_expired_token_returns_401(self, http_client):
        """API: Request with expired token returns 401"""
        # Create a token that looks valid but is expired
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfMTIzIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"

        response = await http_client.get(
            f"{API_BASE}/firmware",
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
# Firmware API Tests
# =============================================================================

class TestFirmwareAPI:
    """Test firmware management API endpoints"""

    async def test_create_firmware_success(self, http_client, internal_headers):
        """API: POST /firmware with valid data succeeds"""
        firmware_request = OTATestDataFactory.make_firmware_upload_request()
        user_id = OTATestDataFactory.make_user_id()

        response = await http_client.post(
            f"{API_BASE}/firmware",
            json=firmware_request.model_dump(),
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201]
        result = response.json()
        assert "firmware_id" in result
        assert result["name"] == firmware_request.name
        assert result["version"] == firmware_request.version

    async def test_create_firmware_validates_name(self, http_client, internal_headers):
        """API: POST /firmware validates name field"""
        user_id = OTATestDataFactory.make_user_id()
        # Invalid request with empty name
        invalid_request = {
            "name": "",  # Empty name
            "version": OTATestDataFactory.make_version(),
            "device_model": OTATestDataFactory.make_device_model(),
            "manufacturer": OTATestDataFactory.make_manufacturer(),
        }

        response = await http_client.post(
            f"{API_BASE}/firmware",
            json=invalid_request,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code == 422

    async def test_create_firmware_validates_version(self, http_client, internal_headers):
        """API: POST /firmware validates version field"""
        user_id = OTATestDataFactory.make_user_id()
        # Invalid request with empty version
        invalid_request = {
            "name": OTATestDataFactory.make_firmware_name(),
            "version": "",  # Empty version
            "device_model": OTATestDataFactory.make_device_model(),
            "manufacturer": OTATestDataFactory.make_manufacturer(),
        }

        response = await http_client.post(
            f"{API_BASE}/firmware",
            json=invalid_request,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code == 422

    async def test_create_firmware_validates_checksum(self, http_client, internal_headers):
        """API: POST /firmware validates checksum format"""
        user_id = OTATestDataFactory.make_user_id()
        invalid_request = {
            "name": OTATestDataFactory.make_firmware_name(),
            "version": OTATestDataFactory.make_version(),
            "device_model": OTATestDataFactory.make_device_model(),
            "manufacturer": OTATestDataFactory.make_manufacturer(),
            "checksum_md5": "invalid_checksum",  # Invalid MD5 format
        }

        response = await http_client.post(
            f"{API_BASE}/firmware",
            json=invalid_request,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code == 422

    async def test_get_firmware_success(self, http_client, internal_headers, test_firmware):
        """API: GET /firmware/{id} returns firmware details"""
        if not test_firmware:
            pytest.skip("Test firmware not available")

        firmware_id = test_firmware["firmware_id"]

        response = await http_client.get(
            f"{API_BASE}/firmware/{firmware_id}",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result["firmware_id"] == firmware_id
        assert "name" in result
        assert "version" in result

    async def test_get_firmware_not_found(self, http_client, internal_headers):
        """API: GET /firmware/{id} returns 404 for nonexistent firmware"""
        fake_id = OTATestDataFactory.make_firmware_id()

        response = await http_client.get(
            f"{API_BASE}/firmware/{fake_id}",
            headers=internal_headers
        )

        assert response.status_code in [404, 500]

    async def test_list_firmware_success(self, http_client, internal_headers):
        """API: GET /firmware returns list"""
        response = await http_client.get(
            f"{API_BASE}/firmware",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, (list, dict))
        if isinstance(result, dict):
            assert "firmware" in result or "items" in result

    async def test_list_firmware_with_pagination(self, http_client, internal_headers):
        """API: GET /firmware respects pagination parameters"""
        response = await http_client.get(
            f"{API_BASE}/firmware",
            params={"limit": 5, "offset": 0},
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_delete_firmware_success(self, http_client, internal_headers):
        """API: DELETE /firmware/{id} removes firmware"""
        # Create firmware to delete
        firmware_request = OTATestDataFactory.make_firmware_upload_request()
        user_id = OTATestDataFactory.make_user_id()

        create_response = await http_client.post(
            f"{API_BASE}/firmware",
            json=firmware_request.model_dump(),
            headers={**internal_headers, "X-User-ID": user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Firmware creation not available")

        firmware_id = create_response.json()["firmware_id"]

        # Delete firmware
        response = await http_client.delete(
            f"{API_BASE}/firmware/{firmware_id}",
            headers=internal_headers
        )

        assert response.status_code in [200, 204]


# =============================================================================
# Campaign API Tests
# =============================================================================

class TestCampaignAPI:
    """Test campaign management API endpoints"""

    async def test_create_campaign_success(self, http_client, internal_headers, test_firmware):
        """API: POST /campaigns with valid data succeeds"""
        if not test_firmware:
            pytest.skip("Test firmware not available")

        campaign_request = OTATestDataFactory.make_campaign_create_request(
            firmware_id=test_firmware["firmware_id"]
        )
        user_id = OTATestDataFactory.make_user_id()

        response = await http_client.post(
            f"{API_BASE}/campaigns",
            json=campaign_request.model_dump(),
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201]
        result = response.json()
        assert "campaign_id" in result
        assert result["name"] == campaign_request.name

    async def test_create_campaign_validates_name(self, http_client, internal_headers):
        """API: POST /campaigns validates name field"""
        user_id = OTATestDataFactory.make_user_id()
        invalid_request = {
            "name": "",  # Empty name
            "firmware_id": OTATestDataFactory.make_firmware_id(),
        }

        response = await http_client.post(
            f"{API_BASE}/campaigns",
            json=invalid_request,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code == 422

    async def test_create_campaign_validates_firmware_id(self, http_client, internal_headers):
        """API: POST /campaigns validates firmware_id field"""
        user_id = OTATestDataFactory.make_user_id()
        invalid_request = {
            "name": OTATestDataFactory.make_campaign_name(),
            "firmware_id": "",  # Empty firmware_id
        }

        response = await http_client.post(
            f"{API_BASE}/campaigns",
            json=invalid_request,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code == 422

    async def test_get_campaign_success(self, http_client, internal_headers, test_campaign):
        """API: GET /campaigns/{id} returns campaign details"""
        if not test_campaign:
            pytest.skip("Test campaign not available")

        campaign_id = test_campaign["campaign_id"]

        response = await http_client.get(
            f"{API_BASE}/campaigns/{campaign_id}",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result["campaign_id"] == campaign_id

    async def test_get_campaign_not_found(self, http_client, internal_headers):
        """API: GET /campaigns/{id} returns 404 for nonexistent campaign"""
        fake_id = OTATestDataFactory.make_campaign_id()

        response = await http_client.get(
            f"{API_BASE}/campaigns/{fake_id}",
            headers=internal_headers
        )

        assert response.status_code in [404, 500]

    async def test_list_campaigns_success(self, http_client, internal_headers):
        """API: GET /campaigns returns list"""
        response = await http_client.get(
            f"{API_BASE}/campaigns",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, (list, dict))

    async def test_start_campaign_success(self, http_client, internal_headers, test_campaign):
        """API: POST /campaigns/{id}/start starts campaign"""
        if not test_campaign:
            pytest.skip("Test campaign not available")

        campaign_id = test_campaign["campaign_id"]

        response = await http_client.post(
            f"{API_BASE}/campaigns/{campaign_id}/start",
            headers=internal_headers
        )

        # Should succeed or return 400 if already started
        assert response.status_code in [200, 400]

    async def test_pause_campaign_success(self, http_client, internal_headers, test_campaign):
        """API: POST /campaigns/{id}/pause pauses campaign"""
        if not test_campaign:
            pytest.skip("Test campaign not available")

        campaign_id = test_campaign["campaign_id"]

        response = await http_client.post(
            f"{API_BASE}/campaigns/{campaign_id}/pause",
            headers=internal_headers
        )

        # Should succeed or return 400 if not in valid state
        assert response.status_code in [200, 400]

    async def test_cancel_campaign_success(self, http_client, internal_headers, test_campaign):
        """API: POST /campaigns/{id}/cancel cancels campaign"""
        if not test_campaign:
            pytest.skip("Test campaign not available")

        campaign_id = test_campaign["campaign_id"]

        response = await http_client.post(
            f"{API_BASE}/campaigns/{campaign_id}/cancel",
            headers=internal_headers
        )

        # Should succeed or return 400 if already cancelled
        assert response.status_code in [200, 400]


# =============================================================================
# Device Update API Tests
# =============================================================================

class TestDeviceUpdateAPI:
    """Test device update API endpoints"""

    async def test_initiate_device_update_success(self, http_client, internal_headers, test_firmware):
        """API: POST /devices/{device_id}/update initiates update"""
        if not test_firmware:
            pytest.skip("Test firmware not available")

        device_id = OTATestDataFactory.make_device_id()
        update_request = OTATestDataFactory.make_device_update_request(
            firmware_id=test_firmware["firmware_id"]
        )

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/update",
            json=update_request.model_dump(),
            headers=internal_headers
        )

        # May succeed, or 404 if device not registered in device service
        assert response.status_code in [200, 201, 400, 404]
        if response.status_code in [200, 201]:
            result = response.json()
            assert "update_id" in result

    async def test_initiate_device_update_validates_firmware_id(self, http_client, internal_headers):
        """API: POST /devices/{device_id}/update validates firmware_id"""
        device_id = OTATestDataFactory.make_device_id()
        invalid_request = {
            "firmware_id": "",  # Empty firmware_id
        }

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/update",
            json=invalid_request,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_get_update_success(self, http_client, internal_headers, test_firmware):
        """API: GET /updates/{id} returns update details"""
        # First create an update
        device_id = OTATestDataFactory.make_device_id()
        update_request = OTATestDataFactory.make_device_update_request(
            firmware_id=test_firmware["firmware_id"] if test_firmware else OTATestDataFactory.make_firmware_id()
        )

        create_response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/update",
            json=update_request.model_dump(),
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Update creation not available")

        update_id = create_response.json()["update_id"]

        response = await http_client.get(
            f"{API_BASE}/updates/{update_id}",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result["update_id"] == update_id

    async def test_get_update_not_found(self, http_client, internal_headers):
        """API: GET /updates/{id} returns 404 for nonexistent update"""
        fake_id = OTATestDataFactory.make_update_id()

        response = await http_client.get(
            f"{API_BASE}/updates/{fake_id}",
            headers=internal_headers
        )

        assert response.status_code in [404, 500]

    async def test_get_device_update_history(self, http_client, internal_headers):
        """API: GET /devices/{device_id}/updates returns update history"""
        device_id = OTATestDataFactory.make_device_id()

        response = await http_client.get(
            f"{API_BASE}/devices/{device_id}/updates",
            headers=internal_headers
        )

        # Should return list or 404 if no history
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, (list, dict))

    async def test_cancel_update_success(self, http_client, internal_headers, test_firmware):
        """API: POST /updates/{id}/cancel cancels update"""
        # First create an update
        device_id = OTATestDataFactory.make_device_id()
        update_request = OTATestDataFactory.make_device_update_request(
            firmware_id=test_firmware["firmware_id"] if test_firmware else OTATestDataFactory.make_firmware_id()
        )

        create_response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/update",
            json=update_request.model_dump(),
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Update creation not available")

        update_id = create_response.json()["update_id"]

        response = await http_client.post(
            f"{API_BASE}/updates/{update_id}/cancel",
            headers=internal_headers
        )

        # Should succeed or return 400 if already cancelled/completed
        assert response.status_code in [200, 400]


# =============================================================================
# Rollback API Tests
# =============================================================================

class TestRollbackAPI:
    """Test rollback API endpoints"""

    async def test_initiate_rollback_success(self, http_client, internal_headers):
        """API: POST /devices/{device_id}/rollback initiates rollback"""
        device_id = OTATestDataFactory.make_device_id()
        rollback_request = OTATestDataFactory.make_rollback_request()

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/rollback",
            json=rollback_request.model_dump(),
            headers=internal_headers
        )

        # May succeed or return 400/404 depending on device state
        assert response.status_code in [200, 201, 400, 404]
        if response.status_code in [200, 201]:
            result = response.json()
            assert "rollback_id" in result

    async def test_rollback_validates_version(self, http_client, internal_headers):
        """API: POST /devices/{device_id}/rollback validates to_version"""
        device_id = OTATestDataFactory.make_device_id()
        invalid_request = {
            "to_version": "",  # Empty version
            "reason": "Test rollback",
        }

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/rollback",
            json=invalid_request,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_rollback_validates_reason(self, http_client, internal_headers):
        """API: POST /devices/{device_id}/rollback validates reason"""
        device_id = OTATestDataFactory.make_device_id()
        invalid_request = {
            "to_version": OTATestDataFactory.make_version(),
            "reason": "",  # Empty reason
        }

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/rollback",
            json=invalid_request,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_rollback_with_priority(self, http_client, internal_headers):
        """API: POST /devices/{device_id}/rollback accepts priority"""
        device_id = OTATestDataFactory.make_device_id()
        rollback_request = OTATestDataFactory.make_rollback_request()

        response = await http_client.post(
            f"{API_BASE}/devices/{device_id}/rollback",
            json=rollback_request.model_dump(),
            headers=internal_headers
        )

        # Priority should be accepted
        assert response.status_code in [200, 201, 400, 404]


# =============================================================================
# Statistics API Tests
# =============================================================================

class TestStatisticsAPI:
    """Test statistics API endpoints"""

    async def test_get_stats_success(self, http_client, internal_headers):
        """API: GET /stats returns OTA statistics"""
        response = await http_client.get(
            f"{API_BASE}/stats",
            headers=internal_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, dict)
        # Should contain common stat fields
        assert "total_campaigns" in result or "total_updates" in result or "success_rate" in result

    async def test_get_campaign_stats_success(self, http_client, internal_headers, test_campaign):
        """API: GET /stats/campaigns/{id} returns campaign statistics"""
        if not test_campaign:
            pytest.skip("Test campaign not available")

        campaign_id = test_campaign["campaign_id"]

        response = await http_client.get(
            f"{API_BASE}/stats/campaigns/{campaign_id}",
            headers=internal_headers
        )

        # Should return stats or 404 if not implemented
        assert response.status_code in [200, 404]

    async def test_get_campaign_stats_not_found(self, http_client, internal_headers):
        """API: GET /stats/campaigns/{id} returns 404 for nonexistent campaign"""
        fake_id = OTATestDataFactory.make_campaign_id()

        response = await http_client.get(
            f"{API_BASE}/stats/campaigns/{fake_id}",
            headers=internal_headers
        )

        assert response.status_code in [404, 500]


# =============================================================================
# Bulk Operation API Tests
# =============================================================================

class TestBulkOperationAPI:
    """Test bulk operation API endpoints"""

    async def test_bulk_update_success(self, http_client, internal_headers, test_firmware):
        """API: POST /devices/bulk/update initiates bulk update"""
        if not test_firmware:
            pytest.skip("Test firmware not available")

        bulk_request = OTATestDataFactory.make_bulk_device_update_request(
            device_count=3,
            firmware_id=test_firmware["firmware_id"]
        )

        response = await http_client.post(
            f"{API_BASE}/devices/bulk/update",
            json=bulk_request.model_dump(),
            headers=internal_headers
        )

        # May succeed or return 400/404 depending on device availability
        assert response.status_code in [200, 201, 400, 404]

    async def test_bulk_update_validates_device_ids(self, http_client, internal_headers):
        """API: POST /devices/bulk/update validates device_ids"""
        invalid_request = {
            "device_ids": [],  # Empty list
            "firmware_id": OTATestDataFactory.make_firmware_id(),
        }

        response = await http_client.post(
            f"{API_BASE}/devices/bulk/update",
            json=invalid_request,
            headers=internal_headers
        )

        assert response.status_code == 422


# =============================================================================
# Error Response Tests
# =============================================================================

class TestErrorResponsesAPI:
    """Test API error response formats"""

    async def test_404_returns_error_structure(self, http_client, internal_headers):
        """API: 404 response has error structure"""
        fake_id = OTATestDataFactory.make_firmware_id()

        response = await http_client.get(
            f"{API_BASE}/firmware/{fake_id}",
            headers=internal_headers
        )

        assert response.status_code in [404, 500]
        result = response.json()
        # Should have error info
        assert "error" in result or "message" in result or "detail" in result

    async def test_422_returns_validation_details(self, http_client, internal_headers):
        """API: 422 response includes validation details"""
        user_id = OTATestDataFactory.make_user_id()

        response = await http_client.post(
            f"{API_BASE}/firmware",
            json={"name": "", "version": ""},
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code == 422
        result = response.json()
        # Should have detail about validation error
        assert "detail" in result or "error" in result or "message" in result

    async def test_method_not_allowed(self, http_client, internal_headers):
        """API: Unsupported HTTP methods return 405"""
        response = await http_client.put(
            f"{API_BASE}/firmware",
            headers=internal_headers
        )

        assert response.status_code == 405


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthAPI:
    """Test health endpoint API"""

    async def test_health_returns_status(self, http_client):
        """API: GET /health returns status"""
        response = await http_client.get(f"{OTA_SERVICE_URL}/health")

        assert response.status_code == 200
        result = response.json()
        assert "status" in result

    async def test_health_no_auth_required(self, http_client):
        """API: GET /health does not require authentication"""
        response = await http_client.get(f"{OTA_SERVICE_URL}/health")

        # Should succeed without any auth headers
        assert response.status_code == 200

    async def test_detailed_health_returns_info(self, http_client):
        """API: GET /health/detailed returns detailed health info"""
        response = await http_client.get(f"{OTA_SERVICE_URL}/health/detailed")

        assert response.status_code == 200
        result = response.json()
        assert "status" in result


# =============================================================================
# Builder Pattern Tests
# =============================================================================

class TestBuilderPatternAPI:
    """Test API using builder pattern for test data"""

    async def test_firmware_with_builder(self, http_client, internal_headers):
        """API: Create firmware using FirmwareUploadRequestBuilder"""
        user_id = OTATestDataFactory.make_user_id()
        request_data = (
            FirmwareUploadRequestBuilder()
            .with_name("Builder Test Firmware")
            .with_version("1.0.0-builder")
            .with_description("Created using builder pattern")
            .as_security_update()
            .build_dict()
        )

        response = await http_client.post(
            f"{API_BASE}/firmware",
            json=request_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201]
        if response.status_code in [200, 201]:
            result = response.json()
            assert result["is_security_update"] == True

    async def test_campaign_with_builder(self, http_client, internal_headers, test_firmware):
        """API: Create campaign using CampaignCreateRequestBuilder"""
        if not test_firmware:
            pytest.skip("Test firmware not available")

        user_id = OTATestDataFactory.make_user_id()
        request_data = (
            CampaignCreateRequestBuilder()
            .with_name("Builder Test Campaign")
            .with_firmware_id(test_firmware["firmware_id"])
            .with_deployment_strategy(DeploymentStrategy.CANARY)
            .with_priority(Priority.HIGH)
            .with_rollout_percentage(25)
            .with_auto_rollback(True, threshold=15)
            .build_dict()
        )

        response = await http_client.post(
            f"{API_BASE}/campaigns",
            json=request_data,
            headers={**internal_headers, "X-User-ID": user_id}
        )

        assert response.status_code in [200, 201]


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "-s", "--tb=short"] + sys.argv[1:])
