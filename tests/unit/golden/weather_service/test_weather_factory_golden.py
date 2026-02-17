"""
Weather Service - Factory & TestDataFactory Golden Tests

Tests for:
- TestDataFactory methods
- Request builders
- Factory patterns

No I/O, no mocks - pure unit tests.
All tests use WeatherTestDataFactory - zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone

from tests.contracts.weather.data_contract import (
    WeatherTestDataFactory,
    WeatherCurrentRequestContract,
    WeatherForecastRequestContract,
    LocationSaveRequestContract,
    WeatherCurrentResponseContract,
    WeatherForecastResponseContract,
    ForecastDayContract,
    WeatherAlertContract,
    LocationResponseContract,
    WeatherCurrentRequestBuilder,
    WeatherForecastRequestBuilder,
    LocationSaveRequestBuilder,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# TestDataFactory ID Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryIds:
    """Test ID generation methods"""

    def test_make_user_id_format(self):
        """make_user_id returns correctly formatted ID"""
        user_id = WeatherTestDataFactory.make_user_id()
        assert user_id.startswith("user_")
        assert len(user_id) > 8

    def test_make_user_id_uniqueness(self):
        """make_user_id generates unique IDs"""
        ids = [WeatherTestDataFactory.make_user_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_make_location_id_format(self):
        """make_location_id returns integer ID"""
        location_id = WeatherTestDataFactory.make_location_id()
        assert isinstance(location_id, int)
        assert location_id > 0

    def test_make_location_id_uniqueness(self):
        """make_location_id generates unique IDs"""
        ids = [WeatherTestDataFactory.make_location_id() for _ in range(100)]
        assert len(set(ids)) == 100


# =============================================================================
# TestDataFactory String Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryStrings:
    """Test string generation methods"""

    def test_make_location_non_empty(self):
        """make_location generates non-empty names"""
        name = WeatherTestDataFactory.make_location()
        assert len(name) > 0
        assert isinstance(name, str)

    def test_make_unique_location_uniqueness(self):
        """make_unique_location generates unique names"""
        names = [WeatherTestDataFactory.make_unique_location() for _ in range(50)]
        # Should have high uniqueness
        assert len(set(names)) == 50

    def test_make_nickname_non_empty(self):
        """make_nickname generates non-empty nicknames"""
        nickname = WeatherTestDataFactory.make_nickname()
        assert len(nickname) > 0

    def test_make_condition_valid(self):
        """make_condition returns valid weather condition"""
        condition = WeatherTestDataFactory.make_condition()
        valid_conditions = ["clear", "cloudy", "rain", "snow", "thunderstorm", "mist", "fog", "drizzle", "overcast", "partly cloudy"]
        assert condition in valid_conditions

    def test_make_alert_type_valid(self):
        """make_alert_type returns valid alert type"""
        alert_type = WeatherTestDataFactory.make_alert_type()
        valid_types = ["storm", "flood", "heat", "cold", "wind", "snow", "hurricane", "tornado", "wildfire", "fog"]
        assert alert_type in valid_types

    def test_make_alert_severity_valid(self):
        """make_alert_severity returns valid AlertSeverity"""
        from tests.contracts.weather.data_contract import AlertSeverity
        severity = WeatherTestDataFactory.make_alert_severity()
        assert isinstance(severity, AlertSeverity)


# =============================================================================
# TestDataFactory Numeric Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryNumerics:
    """Test numeric generation methods"""

    def test_make_temperature_in_range(self):
        """make_temperature returns value in valid range"""
        temp = WeatherTestDataFactory.make_temperature()
        assert -50 <= temp <= 60

    def test_make_temperature_uniqueness(self):
        """make_temperature generates varied values"""
        temps = [WeatherTestDataFactory.make_temperature() for _ in range(100)]
        unique_temps = len(set(temps))
        assert unique_temps >= 10  # Should have some variation

    def test_make_humidity_in_range(self):
        """make_humidity returns value between 0-100"""
        humidity = WeatherTestDataFactory.make_humidity()
        assert 0 <= humidity <= 100

    def test_make_wind_speed_non_negative(self):
        """make_wind_speed returns non-negative value"""
        wind_speed = WeatherTestDataFactory.make_wind_speed()
        assert wind_speed >= 0

    def test_make_latitude_in_range(self):
        """make_latitude returns value between -90 and 90"""
        lat = WeatherTestDataFactory.make_latitude()
        assert -90 <= lat <= 90

    def test_make_longitude_in_range(self):
        """make_longitude returns value between -180 and 180"""
        lon = WeatherTestDataFactory.make_longitude()
        assert -180 <= lon <= 180

    def test_make_forecast_request_days_in_range(self):
        """make_forecast_request generates days in range 1-16"""
        request = WeatherTestDataFactory.make_forecast_request()
        assert 1 <= request.days <= 16


# =============================================================================
# TestDataFactory Timestamp Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryTimestamps:
    """Test timestamp generation methods"""

    def test_make_timestamp_utc(self):
        """make_timestamp returns UTC datetime"""
        ts = WeatherTestDataFactory.make_timestamp()
        assert ts.tzinfo == timezone.utc

    def test_make_timestamp_recent(self):
        """make_timestamp returns recent datetime"""
        ts = WeatherTestDataFactory.make_timestamp()
        now = datetime.now(timezone.utc)
        # Should be within the last hour
        assert (now - ts).total_seconds() < 3600

    def test_make_future_timestamp_in_future(self):
        """make_future_timestamp returns future datetime"""
        ts = WeatherTestDataFactory.make_future_timestamp()
        now = datetime.now(timezone.utc)
        assert ts > now


# =============================================================================
# TestDataFactory Request Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryRequests:
    """Test request generation methods"""

    def test_make_current_weather_request_valid(self):
        """make_current_weather_request generates valid request"""
        request = WeatherTestDataFactory.make_current_weather_request()
        assert isinstance(request, WeatherCurrentRequestContract)
        assert request.location
        assert request.units in ["metric", "imperial"]

    def test_make_current_weather_request_with_overrides(self):
        """make_current_weather_request accepts overrides"""
        request = WeatherTestDataFactory.make_current_weather_request(
            location="Custom Location",
            units="imperial"
        )
        assert request.location == "Custom Location"
        assert request.units == "imperial"

    def test_make_forecast_request_valid(self):
        """make_forecast_request generates valid request"""
        request = WeatherTestDataFactory.make_forecast_request()
        assert isinstance(request, WeatherForecastRequestContract)
        assert request.location
        assert 1 <= request.days <= 16

    def test_make_forecast_request_with_overrides(self):
        """make_forecast_request accepts overrides"""
        request = WeatherTestDataFactory.make_forecast_request(
            location="Paris",
            days=10
        )
        assert request.location == "Paris"
        assert request.days == 10

    def test_make_location_save_request_valid(self):
        """make_location_save_request generates valid request"""
        request = WeatherTestDataFactory.make_location_save_request()
        assert isinstance(request, LocationSaveRequestContract)
        assert request.user_id
        assert request.location

    def test_make_location_save_request_with_overrides(self):
        """make_location_save_request accepts overrides"""
        request = WeatherTestDataFactory.make_location_save_request(
            user_id="custom_user",
            location="Tokyo",
            is_default=True
        )
        assert request.user_id == "custom_user"
        assert request.location == "Tokyo"
        assert request.is_default is True


# =============================================================================
# TestDataFactory Response Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryResponses:
    """Test response generation methods"""

    def test_make_current_weather_response_valid(self):
        """make_current_weather_response generates valid response dict"""
        response = WeatherTestDataFactory.make_current_weather_response()
        assert isinstance(response, dict)
        assert response["location"]
        assert response["temperature"] is not None
        assert 0 <= response["humidity"] <= 100

    def test_make_current_weather_response_cached(self):
        """make_current_weather_response with cached=True returns cached response"""
        response = WeatherTestDataFactory.make_current_weather_response(cached=True)
        assert response["cached"] is True

    def test_make_forecast_response_valid(self):
        """make_forecast_response generates valid response dict"""
        response = WeatherTestDataFactory.make_forecast_response()
        assert isinstance(response, dict)
        assert response["location"]
        assert len(response["forecast"]) > 0

    def test_make_forecast_day_response_valid(self):
        """make_forecast_day_response generates valid forecast day dict"""
        day = WeatherTestDataFactory.make_forecast_day_response()
        assert isinstance(day, dict)
        assert day["temp_max"] >= day["temp_min"]

    def test_make_alert_response_valid(self):
        """make_alert_response generates valid alert dict"""
        alert = WeatherTestDataFactory.make_alert_response()
        assert isinstance(alert, dict)
        assert alert["location"]
        assert alert["alert_type"]
        assert alert["severity"]

    def test_make_location_response_valid(self):
        """make_location_response generates valid location dict"""
        location = WeatherTestDataFactory.make_location_response()
        assert isinstance(location, dict)
        assert location["user_id"]
        assert location["location"]


# =============================================================================
# TestDataFactory Invalid Data Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryInvalid:
    """Test invalid data generation methods"""

    def test_make_invalid_location_empty(self):
        """make_invalid_location_empty returns empty string"""
        location = WeatherTestDataFactory.make_invalid_location_empty()
        assert location == ""

    def test_make_invalid_user_id_empty(self):
        """make_invalid_user_id_empty returns empty string"""
        user_id = WeatherTestDataFactory.make_invalid_user_id_empty()
        assert user_id == ""

    def test_make_invalid_days_zero(self):
        """make_invalid_days_zero returns zero"""
        days = WeatherTestDataFactory.make_invalid_days_zero()
        assert days == 0

    def test_make_invalid_days_too_large(self):
        """make_invalid_days_too_large returns value > 16"""
        days = WeatherTestDataFactory.make_invalid_days_too_large()
        assert days > 16

    def test_make_invalid_humidity_negative(self):
        """make_invalid_humidity_negative returns negative value"""
        humidity = WeatherTestDataFactory.make_invalid_humidity_negative()
        assert humidity < 0

    def test_make_invalid_humidity_over_100(self):
        """make_invalid_humidity_over_100 returns value > 100"""
        humidity = WeatherTestDataFactory.make_invalid_humidity_over_100()
        assert humidity > 100

    def test_make_invalid_latitude_too_high(self):
        """make_invalid_latitude_too_high returns invalid latitude"""
        lat = WeatherTestDataFactory.make_invalid_latitude_too_high()
        assert lat > 90

    def test_make_invalid_longitude_too_high(self):
        """make_invalid_longitude_too_high returns invalid longitude"""
        lon = WeatherTestDataFactory.make_invalid_longitude_too_high()
        assert lon > 180


# =============================================================================
# TestDataFactory Edge Case Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryEdgeCases:
    """Test edge case generation methods"""

    def test_make_edge_temperature_extreme_hot(self):
        """make_edge_temperature_extreme_hot returns very high temp"""
        temp = WeatherTestDataFactory.make_edge_temperature_extreme_hot()
        assert temp >= 50

    def test_make_edge_temperature_extreme_cold(self):
        """make_edge_temperature_extreme_cold returns very low temp"""
        temp = WeatherTestDataFactory.make_edge_temperature_extreme_cold()
        assert temp <= -40

    def test_make_edge_latitude_boundary_low(self):
        """make_edge_latitude_boundary_low returns -90"""
        lat = WeatherTestDataFactory.make_edge_latitude_boundary_low()
        assert lat == -90.0

    def test_make_edge_latitude_boundary_high(self):
        """make_edge_latitude_boundary_high returns 90"""
        lat = WeatherTestDataFactory.make_edge_latitude_boundary_high()
        assert lat == 90.0

    def test_make_edge_forecast_days_min(self):
        """make_edge_forecast_days_min returns 1"""
        days = WeatherTestDataFactory.make_edge_forecast_days_min()
        assert days == 1

    def test_make_edge_forecast_days_max(self):
        """make_edge_forecast_days_max returns 16"""
        days = WeatherTestDataFactory.make_edge_forecast_days_max()
        assert days == 16


# =============================================================================
# Request Builder Tests
# =============================================================================

class TestWeatherCurrentRequestBuilder:
    """Test WeatherCurrentRequestBuilder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        from tests.contracts.weather.data_contract import UnitSystem
        request = WeatherCurrentRequestBuilder().build()
        assert isinstance(request, WeatherCurrentRequestContract)
        assert request.location
        assert request.units == UnitSystem.METRIC

    def test_builder_with_location(self):
        """Builder accepts custom location"""
        request = WeatherCurrentRequestBuilder().with_location("London").build()
        assert request.location == "London"

    def test_builder_with_imperial_units(self):
        """Builder accepts custom units"""
        from tests.contracts.weather.data_contract import UnitSystem
        request = WeatherCurrentRequestBuilder().with_imperial_units().build()
        assert request.units == UnitSystem.IMPERIAL

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        from tests.contracts.weather.data_contract import UnitSystem
        request = (
            WeatherCurrentRequestBuilder()
            .with_location("Paris")
            .with_metric_units()
            .build()
        )
        assert request.location == "Paris"
        assert request.units == UnitSystem.METRIC

    def test_builder_build_dict(self):
        """Builder can build as dictionary"""
        data = WeatherCurrentRequestBuilder().with_location("Berlin").build_dict()
        assert isinstance(data, dict)
        assert data["location"] == "Berlin"


class TestWeatherForecastRequestBuilder:
    """Test WeatherForecastRequestBuilder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = WeatherForecastRequestBuilder().build()
        assert isinstance(request, WeatherForecastRequestContract)
        assert request.location
        assert 1 <= request.days <= 16

    def test_builder_with_location(self):
        """Builder accepts custom location"""
        request = WeatherForecastRequestBuilder().with_location("Tokyo").build()
        assert request.location == "Tokyo"

    def test_builder_with_days(self):
        """Builder accepts custom days"""
        request = WeatherForecastRequestBuilder().with_days(10).build()
        assert request.days == 10

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        from tests.contracts.weather.data_contract import UnitSystem
        request = (
            WeatherForecastRequestBuilder()
            .with_location("Sydney")
            .with_days(7)
            .with_units(UnitSystem.IMPERIAL)
            .build()
        )
        assert request.location == "Sydney"
        assert request.days == 7
        assert request.units == UnitSystem.IMPERIAL


class TestLocationSaveRequestBuilder:
    """Test LocationSaveRequestBuilder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = LocationSaveRequestBuilder().build()
        assert isinstance(request, LocationSaveRequestContract)
        assert request.user_id
        assert request.location

    def test_builder_with_user_id(self):
        """Builder accepts custom user_id"""
        request = LocationSaveRequestBuilder().with_user_id("custom_user").build()
        assert request.user_id == "custom_user"

    def test_builder_with_location(self):
        """Builder accepts custom location"""
        request = LocationSaveRequestBuilder().with_location("Vancouver").build()
        assert request.location == "Vancouver"

    def test_builder_with_coordinates(self):
        """Builder accepts coordinates"""
        request = (
            LocationSaveRequestBuilder()
            .with_coordinates(49.2827, -123.1207)
            .build()
        )
        assert request.latitude == 49.2827
        assert request.longitude == -123.1207

    def test_builder_as_default(self):
        """Builder can set as default location"""
        request = LocationSaveRequestBuilder().as_default().build()
        assert request.is_default is True

    def test_builder_with_nickname(self):
        """Builder accepts nickname"""
        request = LocationSaveRequestBuilder().with_nickname("Home").build()
        assert request.nickname == "Home"

    def test_builder_chaining(self):
        """Builder supports full method chaining"""
        request = (
            LocationSaveRequestBuilder()
            .with_user_id("user_123")
            .with_location("San Francisco")
            .with_coordinates(37.7749, -122.4194)
            .as_default()
            .with_nickname("Office")
            .build()
        )
        assert request.user_id == "user_123"
        assert request.location == "San Francisco"
        assert request.latitude == 37.7749
        assert request.longitude == -122.4194
        assert request.is_default is True
        assert request.nickname == "Office"


# =============================================================================
# TestDataFactory Batch Generation Tests
# =============================================================================

class TestWeatherTestDataFactoryBatch:
    """Test batch generation methods"""

    def test_make_batch_locations_count(self):
        """make_batch_locations generates locations list"""
        locations = WeatherTestDataFactory.make_batch_locations()
        assert len(locations) > 0
        assert all(isinstance(loc, str) for loc in locations)

    def test_make_batch_locations_unique(self):
        """make_batch_locations generates unique locations"""
        locations = WeatherTestDataFactory.make_batch_locations()
        # Batch locations should be unique
        assert len(set(locations)) == len(locations)

    def test_make_batch_location_save_requests_count(self):
        """make_batch_location_save_requests generates correct count"""
        requests = WeatherTestDataFactory.make_batch_location_save_requests(count=7)
        assert len(requests) == 7

    def test_make_batch_user_ids_count(self):
        """make_batch_user_ids generates correct count"""
        user_ids = WeatherTestDataFactory.make_batch_user_ids(count=3)
        assert len(user_ids) == 3
        assert all(uid.startswith("user_") for uid in user_ids)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
