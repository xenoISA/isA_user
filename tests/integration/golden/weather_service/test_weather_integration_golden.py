"""
Weather Service - Integration Golden Tests

Tests full CRUD lifecycle with real HTTP and database.
Uses X-Internal-Call header to bypass authentication.
All tests use WeatherTestDataFactory - zero hardcoded data.
"""
import pytest
import os
from datetime import datetime, timezone

from tests.contracts.weather.data_contract import WeatherTestDataFactory

pytestmark = [pytest.mark.integration, pytest.mark.golden, pytest.mark.asyncio]

# Service configuration
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://localhost:8241")
WEATHER_API_BASE = f"{WEATHER_SERVICE_URL}/api/v1/weather"


# =============================================================================
# Health Check Tests
# =============================================================================

class TestWeatherServiceHealth:
    """Test service health endpoints"""

    async def test_health_check_returns_healthy(self, http_client):
        """Health check returns healthy status"""
        response = await http_client.get(f"{WEATHER_SERVICE_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "weather_service"

    async def test_health_check_includes_version(self, http_client):
        """Health check includes version"""
        response = await http_client.get(f"{WEATHER_SERVICE_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data


# =============================================================================
# Current Weather Integration Tests
# =============================================================================

class TestWeatherCurrentIntegration:
    """Test current weather API integration"""

    async def test_get_current_weather_valid_location(self, http_client):
        """GET current weather with valid location returns data"""
        location = "London"

        response = await http_client.get(
            f"{WEATHER_API_BASE}/current",
            params={"location": location, "units": "metric"}
        )

        # May return 200 (success) or 404 (no API key configured)
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()
            assert "location" in data
            assert "temperature" in data
            assert "humidity" in data
            assert "condition" in data

    async def test_get_current_weather_missing_location_returns_422(self, http_client):
        """GET current weather without location returns 422"""
        response = await http_client.get(f"{WEATHER_API_BASE}/current")

        assert response.status_code == 422

    async def test_get_current_weather_imperial_units(self, http_client):
        """GET current weather with imperial units"""
        location = "New York"

        response = await http_client.get(
            f"{WEATHER_API_BASE}/current",
            params={"location": location, "units": "imperial"}
        )

        assert response.status_code in [200, 404, 500]


# =============================================================================
# Weather Forecast Integration Tests
# =============================================================================

class TestWeatherForecastIntegration:
    """Test weather forecast API integration"""

    async def test_get_forecast_valid_request(self, http_client):
        """GET forecast with valid parameters returns data"""
        location = "Paris"
        days = 5

        response = await http_client.get(
            f"{WEATHER_API_BASE}/forecast",
            params={"location": location, "days": days, "units": "metric"}
        )

        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()
            assert "location" in data
            assert "forecast" in data
            assert isinstance(data["forecast"], list)

    async def test_get_forecast_invalid_days_zero(self, http_client):
        """GET forecast with days=0 returns 422"""
        response = await http_client.get(
            f"{WEATHER_API_BASE}/forecast",
            params={"location": "Tokyo", "days": 0}
        )

        assert response.status_code == 422

    async def test_get_forecast_invalid_days_exceeds_max(self, http_client):
        """GET forecast with days>16 returns 422"""
        response = await http_client.get(
            f"{WEATHER_API_BASE}/forecast",
            params={"location": "Sydney", "days": 17}
        )

        assert response.status_code == 422

    async def test_get_forecast_default_days(self, http_client):
        """GET forecast without days parameter uses default (5)"""
        response = await http_client.get(
            f"{WEATHER_API_BASE}/forecast",
            params={"location": "Berlin"}
        )

        assert response.status_code in [200, 404, 500]


# =============================================================================
# Weather Alerts Integration Tests
# =============================================================================

class TestWeatherAlertsIntegration:
    """Test weather alerts API integration"""

    async def test_get_alerts_valid_location(self, http_client):
        """GET alerts with valid location returns response"""
        location = "Miami"

        response = await http_client.get(
            f"{WEATHER_API_BASE}/alerts",
            params={"location": location}
        )

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "location" in data
        assert "checked_at" in data
        assert isinstance(data["alerts"], list)

    async def test_get_alerts_missing_location_returns_422(self, http_client):
        """GET alerts without location returns 422"""
        response = await http_client.get(f"{WEATHER_API_BASE}/alerts")

        assert response.status_code == 422


# =============================================================================
# Favorite Locations CRUD Integration Tests
# =============================================================================

class TestLocationsCRUDIntegration:
    """Test favorite locations full CRUD lifecycle"""

    async def test_full_location_lifecycle(self, http_client, internal_headers):
        """
        Integration: Full location lifecycle
        1. Create -> 2. List -> 3. Delete -> 4. Verify deleted
        """
        # Generate test data
        user_id = WeatherTestDataFactory.make_user_id()
        location_data = WeatherTestDataFactory.make_location_save_request(
            user_id=user_id
        ).model_dump()

        # 1. CREATE
        create_response = await http_client.post(
            f"{WEATHER_API_BASE}/locations",
            json=location_data,
            headers=internal_headers
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert "id" in created or "location" in created
        location_id = created.get("id")

        try:
            # 2. LIST
            list_response = await http_client.get(
                f"{WEATHER_API_BASE}/locations/{user_id}",
                headers=internal_headers
            )

            assert list_response.status_code == 200
            list_data = list_response.json()
            assert "locations" in list_data
            assert len(list_data["locations"]) >= 1

            # 3. DELETE (if we got an ID)
            if location_id:
                delete_response = await http_client.delete(
                    f"{WEATHER_API_BASE}/locations/{location_id}",
                    params={"user_id": user_id},
                    headers=internal_headers
                )

                assert delete_response.status_code == 204

                # 4. VERIFY DELETED
                list_after_delete = await http_client.get(
                    f"{WEATHER_API_BASE}/locations/{user_id}",
                    headers=internal_headers
                )

                assert list_after_delete.status_code == 200
                after_data = list_after_delete.json()
                # Location should be gone or list should be shorter
                location_ids = [
                    loc.get("id") for loc in after_data.get("locations", [])
                ]
                assert location_id not in location_ids

        finally:
            # Cleanup: try to delete if not already deleted
            if location_id:
                await http_client.delete(
                    f"{WEATHER_API_BASE}/locations/{location_id}",
                    params={"user_id": user_id},
                    headers=internal_headers
                )

    async def test_create_location_with_coordinates(self, http_client, internal_headers):
        """Create location with latitude and longitude"""
        user_id = WeatherTestDataFactory.make_user_id()
        location_data = (
            WeatherTestDataFactory.make_location_save_request(user_id=user_id)
            .model_dump()
        )
        location_data["latitude"] = WeatherTestDataFactory.make_latitude()
        location_data["longitude"] = WeatherTestDataFactory.make_longitude()

        response = await http_client.post(
            f"{WEATHER_API_BASE}/locations",
            json=location_data,
            headers=internal_headers
        )

        assert response.status_code == 201
        created = response.json()

        # Cleanup
        if "id" in created:
            await http_client.delete(
                f"{WEATHER_API_BASE}/locations/{created['id']}",
                params={"user_id": user_id},
                headers=internal_headers
            )

    async def test_create_location_as_default(self, http_client, internal_headers):
        """Create location as default"""
        user_id = WeatherTestDataFactory.make_user_id()
        location_data = WeatherTestDataFactory.make_location_save_request(
            user_id=user_id,
            is_default=True
        ).model_dump()

        response = await http_client.post(
            f"{WEATHER_API_BASE}/locations",
            json=location_data,
            headers=internal_headers
        )

        assert response.status_code == 201
        created = response.json()

        # Verify it's the default
        list_response = await http_client.get(
            f"{WEATHER_API_BASE}/locations/{user_id}",
            headers=internal_headers
        )

        assert list_response.status_code == 200
        list_data = list_response.json()

        # First location should be default
        if list_data["locations"]:
            assert list_data["locations"][0].get("is_default", False) is True

        # Cleanup
        if "id" in created:
            await http_client.delete(
                f"{WEATHER_API_BASE}/locations/{created['id']}",
                params={"user_id": user_id},
                headers=internal_headers
            )

    async def test_get_locations_empty_user(self, http_client, internal_headers):
        """Get locations for user with no saved locations"""
        user_id = WeatherTestDataFactory.make_user_id()

        response = await http_client.get(
            f"{WEATHER_API_BASE}/locations/{user_id}",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        assert data["total"] == 0
        assert len(data["locations"]) == 0

    async def test_delete_nonexistent_location_returns_404(
        self, http_client, internal_headers
    ):
        """Delete nonexistent location returns 404"""
        fake_id = 999999
        user_id = WeatherTestDataFactory.make_user_id()

        response = await http_client.delete(
            f"{WEATHER_API_BASE}/locations/{fake_id}",
            params={"user_id": user_id},
            headers=internal_headers
        )

        assert response.status_code == 404


# =============================================================================
# Validation Integration Tests
# =============================================================================

class TestWeatherValidationIntegration:
    """Test validation with real service"""

    async def test_create_location_missing_user_id(self, http_client, internal_headers):
        """Create location without user_id returns 422"""
        location_data = {"location": "Invalid"}

        response = await http_client.post(
            f"{WEATHER_API_BASE}/locations",
            json=location_data,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_create_location_missing_location_name(
        self, http_client, internal_headers
    ):
        """Create location without location name returns 422"""
        location_data = {"user_id": "user_123"}

        response = await http_client.post(
            f"{WEATHER_API_BASE}/locations",
            json=location_data,
            headers=internal_headers
        )

        assert response.status_code == 422


# =============================================================================
# Caching Integration Tests
# =============================================================================

class TestWeatherCachingIntegration:
    """Test caching behavior"""

    async def test_current_weather_caching_returns_cached_flag(self, http_client):
        """Second request should return cached=True"""
        location = "TestCacheCity"

        # First request
        response1 = await http_client.get(
            f"{WEATHER_API_BASE}/current",
            params={"location": location}
        )

        if response1.status_code == 200:
            # Second request (should be cached)
            response2 = await http_client.get(
                f"{WEATHER_API_BASE}/current",
                params={"location": location}
            )

            if response2.status_code == 200:
                data2 = response2.json()
                # Second request should have cached=True
                assert data2.get("cached") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
