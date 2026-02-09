"""
Smoke Tests for Service Health

Tests that the campaign service is healthy and responsive.
"""

import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


@pytest.mark.smoke
class TestServiceHealth:
    """Smoke tests for service health"""

    @pytest.mark.asyncio
    async def test_service_is_healthy(self, http_client, smoke_config):
        """Test campaign service is healthy"""
        # When: GET /health
        response = await http_client.get("/health")

        # Then: Service is healthy
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_service_is_ready(self, http_client, smoke_config):
        """Test campaign service is ready (all dependencies healthy)"""
        # When: GET /health/ready
        response = await http_client.get("/health/ready")

        # Then: Service is ready
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    @pytest.mark.asyncio
    async def test_service_is_alive(self, http_client, smoke_config):
        """Test campaign service is alive"""
        # When: GET /health/live
        response = await http_client.get("/health/live")

        # Then: Service is alive
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


@pytest.mark.smoke
class TestDatabaseConnectivity:
    """Smoke tests for database connectivity"""

    @pytest.mark.asyncio
    async def test_database_is_healthy(self, http_client, smoke_config):
        """Test database connection is healthy"""
        # When: GET /health/ready
        response = await http_client.get("/health/ready")

        # Then: Database is healthy
        data = response.json()
        assert data["checks"]["database"] is True


@pytest.mark.smoke
class TestNATSConnectivity:
    """Smoke tests for NATS connectivity"""

    @pytest.mark.asyncio
    async def test_nats_is_healthy(self, http_client, smoke_config):
        """Test NATS connection is healthy"""
        # When: GET /health/ready
        response = await http_client.get("/health/ready")

        # Then: NATS is healthy
        data = response.json()
        assert data["checks"]["nats"] is True


@pytest.mark.smoke
class TestRedisConnectivity:
    """Smoke tests for Redis connectivity"""

    @pytest.mark.asyncio
    async def test_redis_is_healthy(self, http_client, smoke_config):
        """Test Redis connection is healthy"""
        pytest.skip("Requires campaign_service to be running")

        # When: GET /health/ready
        response = await http_client.get("/health/ready")

        # Then: Redis is healthy
        data = response.json()
        assert data["checks"]["redis"]["status"] == "healthy"


@pytest.mark.smoke
class TestConsulRegistration:
    """Smoke tests for Consul registration"""

    @pytest.mark.asyncio
    async def test_service_registered_with_consul(self, smoke_config):
        """Test campaign service is registered with Consul"""
        pytest.skip("Requires Consul to be running")

        import httpx

        # When: Query Consul for service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{smoke_config.CONSUL_HOST}:{smoke_config.CONSUL_PORT}"
                f"/v1/catalog/service/campaign_service"
            )

        # Then: Service is registered
        assert response.status_code == 200
        services = response.json()
        assert len(services) > 0
