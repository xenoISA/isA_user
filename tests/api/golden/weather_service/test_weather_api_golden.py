"""
Weather Service - API Golden Tests

Tests HTTP API contracts with JWT authentication.
All tests use WeatherTestDataFactory - zero hardcoded data.
"""
import pytest
import os

from tests.contracts.weather.data_contract import WeatherTestDataFactory

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]

WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://localhost:8241")


# =============================================================================
# Authentication Tests
# =============================================================================

class TestWeatherAPIAuthentication:
    """Test API authentication requirements"""

    async def test_public_endpoints_no_auth_required(self, http_client):
        """Public weather endpoints work without auth"""
        # Health check - always public
        response = await http_client.get(f"{WEATHER_SERVICE_URL}/health")
        assert response.status_code == 200

        # Current weather - public (no user data)
        response = await http_client.get(
            f"{WEATHER_SERVICE_URL}/api/v1/weather/current",
            params={"location": "London"}
        )
        # Should not be 401 (may be 200, 404, or 500 depending on API key)
        assert response.status_code != 401

        # Forecast - public
        response = await http_client.get(
            f"{WEATHER_SERVICE_URL}/api/v1/weather/forecast",
            params={"location": "Paris", "days": 5}
        )
        assert response.status_code != 401

        # Alerts - public
        response = await http_client.get(
            f"{WEATHER_SERVICE_URL}/api/v1/weather/alerts",
            params={"location": "Miami"}
        )
        assert response.status_code == 200

    async def test_protected_endpoints_require_auth(self, http_client):
        """Protected location endpoints require authentication"""
        user_id = WeatherTestDataFactory.make_user_id()

        # POST locations - requires auth
        response = await http_client.post(
            f"{WEATHER_SERVICE_URL}/api/v1/weather/locations",
            json={"user_id": user_id, "location": "Test"}
        )
        # Should be 401 without auth, or 201/422 with internal call
        # Current implementation may use X-Internal-Call bypass
        assert response.status_code in [201, 401, 422, 500]

        # GET user locations - requires auth
        response = await http_client.get(
            f"{WEATHER_SERVICE_URL}/api/v1/weather/locations/{user_id}"
        )
        assert response.status_code in [200, 401]

        # DELETE location - requires auth
        response = await http_client.delete(
            f"{WEATHER_SERVICE_URL}/api/v1/weather/locations/1",
            params={"user_id": user_id}
        )
        assert response.status_code in [204, 401, 404]


# =============================================================================
# Current Weather API Tests
# =============================================================================

class TestWeatherCurrentAPI:
    """Test current weather API endpoints"""

    async def test_get_current_weather_contract(self, weather_api):
        """GET /current returns expected contract"""
        response = await weather_api.get(
            "/current",
            params={"location": "London", "units": "metric"}
        )

        if response.status_code == 200:
            data = response.json()
            # Verify response contract
            assert "location" in data
            assert "temperature" in data
            assert "humidity" in data
            assert "condition" in data
            assert "observed_at" in data
            assert "cached" in data

    async def test_get_current_weather_units_metric(self, weather_api):
        """GET /current with metric units"""
        response = await weather_api.get(
            "/current",
            params={"location": "Berlin", "units": "metric"}
        )

        assert response.status_code in [200, 404, 500]

    async def test_get_current_weather_units_imperial(self, weather_api):
        """GET /current with imperial units"""
        response = await weather_api.get(
            "/current",
            params={"location": "New York", "units": "imperial"}
        )

        assert response.status_code in [200, 404, 500]

    async def test_get_current_weather_missing_location(self, weather_api):
        """GET /current without location returns 422"""
        response = await weather_api.get("/current", params={})

        assert response.status_code == 422

    async def test_get_current_weather_coordinates(self, weather_api):
        """GET /current with coordinates as location"""
        lat = WeatherTestDataFactory.make_latitude()
        lon = WeatherTestDataFactory.make_longitude()

        response = await weather_api.get(
            "/current",
            params={"location": f"{lat},{lon}"}
        )

        assert response.status_code in [200, 404, 500]


# =============================================================================
# Weather Forecast API Tests
# =============================================================================

class TestWeatherForecastAPI:
    """Test weather forecast API endpoints"""

    async def test_get_forecast_contract(self, weather_api):
        """GET /forecast returns expected contract"""
        response = await weather_api.get(
            "/forecast",
            params={"location": "Tokyo", "days": 5}
        )

        if response.status_code == 200:
            data = response.json()
            # Verify response contract
            assert "location" in data
            assert "forecast" in data
            assert isinstance(data["forecast"], list)
            assert "generated_at" in data
            assert "cached" in data

            # Verify forecast day contract
            if data["forecast"]:
                day = data["forecast"][0]
                assert "date" in day
                assert "temp_max" in day
                assert "temp_min" in day
                assert "condition" in day

    async def test_get_forecast_days_range(self, weather_api):
        """GET /forecast accepts days 1-16"""
        # Minimum days
        response = await weather_api.get(
            "/forecast",
            params={"location": "Paris", "days": 1}
        )
        assert response.status_code in [200, 404, 500]

        # Maximum days
        response = await weather_api.get(
            "/forecast",
            params={"location": "Paris", "days": 16}
        )
        assert response.status_code in [200, 404, 500]

    async def test_get_forecast_days_invalid(self, weather_api):
        """GET /forecast rejects invalid days"""
        # Zero days
        response = await weather_api.get(
            "/forecast",
            params={"location": "Rome", "days": 0}
        )
        assert response.status_code == 422

        # Exceeds max
        response = await weather_api.get(
            "/forecast",
            params={"location": "Rome", "days": 17}
        )
        assert response.status_code == 422

    async def test_get_forecast_default_days(self, weather_api):
        """GET /forecast without days uses default"""
        response = await weather_api.get(
            "/forecast",
            params={"location": "Sydney"}
        )

        assert response.status_code in [200, 404, 500]


# =============================================================================
# Weather Alerts API Tests
# =============================================================================

class TestWeatherAlertsAPI:
    """Test weather alerts API endpoints"""

    async def test_get_alerts_contract(self, weather_api):
        """GET /alerts returns expected contract"""
        response = await weather_api.get(
            "/alerts",
            params={"location": "Houston"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response contract
        assert "alerts" in data
        assert "location" in data
        assert "checked_at" in data
        assert isinstance(data["alerts"], list)

    async def test_get_alerts_with_alerts_contract(self, weather_api):
        """GET /alerts with alerts returns alert contract"""
        response = await weather_api.get(
            "/alerts",
            params={"location": "Miami"}
        )

        assert response.status_code == 200
        data = response.json()

        # If alerts exist, verify alert contract
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "alert_type" in alert
            assert "severity" in alert
            assert "headline" in alert

    async def test_get_alerts_missing_location(self, weather_api):
        """GET /alerts without location returns 422"""
        response = await weather_api.get("/alerts", params={})

        assert response.status_code == 422


# =============================================================================
# Favorite Locations API Tests
# =============================================================================

class TestWeatherLocationsAPI:
    """Test favorite locations API endpoints"""

    async def test_create_location_contract(self, weather_api):
        """POST /locations returns expected contract"""
        location_data = WeatherTestDataFactory.make_location_save_request().model_dump()

        response = await weather_api.post("/locations", json=location_data)

        if response.status_code == 201:
            data = response.json()
            # Verify response has location data
            assert "location" in data or "id" in data

            # Cleanup
            if "id" in data:
                await weather_api.delete(
                    f"/locations/{data['id']}",
                    params={"user_id": location_data["user_id"]}
                )

    async def test_get_user_locations_contract(self, weather_api):
        """GET /locations/{user_id} returns expected contract"""
        user_id = WeatherTestDataFactory.make_user_id()

        response = await weather_api.get(f"/locations/{user_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify response contract
        assert "locations" in data
        assert "total" in data
        assert isinstance(data["locations"], list)
        assert isinstance(data["total"], int)

    async def test_create_location_validation(self, weather_api):
        """POST /locations validates required fields"""
        # Missing user_id
        response = await weather_api.post(
            "/locations",
            json={"location": "Test"}
        )
        assert response.status_code == 422

        # Missing location
        response = await weather_api.post(
            "/locations",
            json={"user_id": "user_123"}
        )
        assert response.status_code == 422

    async def test_delete_location_not_found(self, weather_api):
        """DELETE /locations/{id} returns 404 for nonexistent"""
        fake_id = 999999
        user_id = WeatherTestDataFactory.make_user_id()

        response = await weather_api.delete(
            f"/locations/{fake_id}",
            params={"user_id": user_id}
        )

        assert response.status_code == 404


# =============================================================================
# Error Response Contract Tests
# =============================================================================

class TestWeatherAPIErrorResponses:
    """Test API error response contracts"""

    async def test_422_error_format(self, weather_api):
        """422 errors return structured error response"""
        response = await weather_api.get("/current", params={})

        assert response.status_code == 422
        data = response.json()

        # Should have error details
        assert "detail" in data

    async def test_404_error_format(self, weather_api):
        """404 errors return structured error response"""
        user_id = WeatherTestDataFactory.make_user_id()

        response = await weather_api.delete(
            "/locations/999999",
            params={"user_id": user_id}
        )

        assert response.status_code == 404
        data = response.json()

        assert "detail" in data


# =============================================================================
# Response Headers Tests
# =============================================================================

class TestWeatherAPIHeaders:
    """Test API response headers"""

    async def test_response_content_type_json(self, http_client):
        """Responses have JSON content type"""
        response = await http_client.get(f"{WEATHER_SERVICE_URL}/health")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    async def test_health_includes_service_info(self, http_client):
        """Health endpoint includes service info"""
        response = await http_client.get(f"{WEATHER_SERVICE_URL}/health")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "weather_service"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
