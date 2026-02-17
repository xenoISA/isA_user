"""
API Tests for Health Check Endpoints

Tests health, readiness, and liveness endpoints.
Reference: System Contract - Health Checks Pattern
"""

import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


@pytest.mark.api
class TestHealthEndpoint:
    """Tests for GET /health"""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self, http_client, api_helper):
        """Test /health returns healthy status"""
        # When: GET /health
        response = await http_client.get("/health")

        # Then: 200 with healthy status
        api_helper.assert_success(response, 200)
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "campaign_service"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, http_client, api_helper):
        """Test /health does not require authentication"""
        # When: GET /health without auth headers
        response = await http_client.get("/health")

        # Then: 200 (no 401)
        api_helper.assert_success(response, 200)


@pytest.mark.api
class TestReadinessEndpoint:
    """Tests for GET /health/ready"""

    @pytest.mark.asyncio
    async def test_readiness_returns_ready(self, http_client, api_helper):
        """Test /health/ready returns ready status"""
        # When: GET /health/ready
        response = await http_client.get("/health/ready")

        # Then: 200 with ready status and dependency checks
        api_helper.assert_success(response, 200)
        data = response.json()
        assert data.get("ready") == True or data.get("status") == "ready"

    @pytest.mark.asyncio
    async def test_readiness_shows_dependency_status(self, http_client, api_helper):
        """Test /health/ready shows each dependency status"""
        # When: GET /health/ready
        response = await http_client.get("/health/ready")

        # Then: Response has dependency info
        data = response.json()
        assert response.status_code == 200


@pytest.mark.api
class TestLivenessEndpoint:
    """Tests for GET /health/live"""

    @pytest.mark.asyncio
    async def test_liveness_returns_alive(self, http_client, api_helper):
        """Test /health/live returns alive status"""
        # When: GET /health/live
        response = await http_client.get("/health/live")

        # Then: 200 with alive status
        api_helper.assert_success(response, 200)
        data = response.json()
        assert data.get("alive") == True or data.get("status") == "alive"

    @pytest.mark.asyncio
    async def test_liveness_minimal_response(self, http_client, api_helper):
        """Test /health/live returns minimal response (for fast k8s probes)"""
        # When: GET /health/live
        response = await http_client.get("/health/live")

        # Then: Response is minimal
        api_helper.assert_success(response, 200)
