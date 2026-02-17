"""
Unit Golden Tests: Weather Service Models

Tests model validation and serialization without external dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.weather_service.models import (
    WeatherProvider,
    WeatherCondition,
    AlertSeverity,
    WeatherData,
    WeatherForecast,
    ForecastDay,
    WeatherAlert,
    FavoriteLocation,
    WeatherCurrentRequest,
    WeatherForecastRequest,
    LocationSaveRequest,
    WeatherCurrentResponse,
    WeatherForecastResponse,
    LocationListResponse,
    WeatherAlertResponse,
)


class TestWeatherProvider:
    """Test WeatherProvider enum"""

    def test_weather_provider_values(self):
        """Test all weather provider values are defined"""
        assert WeatherProvider.OPENWEATHERMAP.value == "openweathermap"
        assert WeatherProvider.WEATHERAPI.value == "weatherapi"
        assert WeatherProvider.VISUALCROSSING.value == "visualcrossing"

    def test_weather_provider_comparison(self):
        """Test weather provider comparison"""
        assert WeatherProvider.OPENWEATHERMAP.value == "openweathermap"
        assert WeatherProvider.OPENWEATHERMAP != WeatherProvider.WEATHERAPI
        assert WeatherProvider.WEATHERAPI != WeatherProvider.VISUALCROSSING


class TestWeatherCondition:
    """Test WeatherCondition enum"""

    def test_weather_condition_values(self):
        """Test all weather condition values"""
        assert WeatherCondition.CLEAR.value == "clear"
        assert WeatherCondition.CLOUDY.value == "cloudy"
        assert WeatherCondition.RAIN.value == "rain"
        assert WeatherCondition.SNOW.value == "snow"
        assert WeatherCondition.THUNDERSTORM.value == "thunderstorm"
        assert WeatherCondition.MIST.value == "mist"
        assert WeatherCondition.FOG.value == "fog"

    def test_weather_condition_comparison(self):
        """Test weather condition comparison"""
        assert WeatherCondition.CLEAR != WeatherCondition.CLOUDY
        assert WeatherCondition.RAIN.value == "rain"
        assert WeatherCondition.SNOW != WeatherCondition.RAIN


class TestAlertSeverity:
    """Test AlertSeverity enum"""

    def test_alert_severity_values(self):
        """Test all alert severity values"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.SEVERE.value == "severe"
        assert AlertSeverity.EXTREME.value == "extreme"

    def test_alert_severity_ordering(self):
        """Test alert severity levels are distinct"""
        severities = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.SEVERE,
            AlertSeverity.EXTREME,
        ]
        assert len(set(severities)) == 4


class TestWeatherData:
    """Test WeatherData model validation"""

    def test_weather_data_creation_with_all_fields(self):
        """Test creating weather data with all fields"""
        now = datetime.now(timezone.utc)
        sunrise = now.replace(hour=6, minute=30)
        sunset = now.replace(hour=18, minute=45)

        weather = WeatherData(
            id=1,
            location="New York",
            latitude=40.7128,
            longitude=-74.0060,
            temperature=22.5,
            feels_like=21.0,
            humidity=65,
            pressure=1013,
            wind_speed=5.2,
            wind_direction=180,
            condition="clear",
            description="Clear sky",
            icon="01d",
            visibility=10.0,
            uv_index=5.5,
            clouds=20,
            observed_at=now,
            sunrise=sunrise,
            sunset=sunset,
            provider=WeatherProvider.OPENWEATHERMAP.value,
            metadata={"source": "api", "accuracy": "high"},
            cached_at=now,
            expires_at=now + timedelta(hours=1),
        )

        assert weather.id == 1
        assert weather.location == "New York"
        assert weather.latitude == 40.7128
        assert weather.longitude == -74.0060
        assert weather.temperature == 22.5
        assert weather.feels_like == 21.0
        assert weather.humidity == 65
        assert weather.pressure == 1013
        assert weather.wind_speed == 5.2
        assert weather.wind_direction == 180
        assert weather.condition == "clear"
        assert weather.description == "Clear sky"
        assert weather.icon == "01d"
        assert weather.visibility == 10.0
        assert weather.uv_index == 5.5
        assert weather.clouds == 20
        assert weather.observed_at == now
        assert weather.sunrise == sunrise
        assert weather.sunset == sunset
        assert weather.provider == WeatherProvider.OPENWEATHERMAP.value

    def test_weather_data_with_minimal_fields(self):
        """Test creating weather data with only required fields"""
        now = datetime.now(timezone.utc)

        weather = WeatherData(
            location="London",
            temperature=15.0,
            humidity=70,
            condition="rain",
            observed_at=now,
        )

        assert weather.location == "London"
        assert weather.temperature == 15.0
        assert weather.humidity == 70
        assert weather.condition == "rain"
        assert weather.observed_at == now
        assert weather.provider == WeatherProvider.OPENWEATHERMAP.value
        assert weather.id is None
        assert weather.latitude is None
        assert weather.longitude is None

    def test_weather_data_humidity_validation(self):
        """Test humidity must be between 0 and 100"""
        now = datetime.now(timezone.utc)

        # Test valid humidity
        weather = WeatherData(
            location="Test",
            temperature=20.0,
            humidity=50,
            condition="clear",
            observed_at=now,
        )
        assert weather.humidity == 50

        # Test minimum humidity
        weather_min = WeatherData(
            location="Test",
            temperature=20.0,
            humidity=0,
            condition="clear",
            observed_at=now,
        )
        assert weather_min.humidity == 0

        # Test maximum humidity
        weather_max = WeatherData(
            location="Test",
            temperature=20.0,
            humidity=100,
            condition="clear",
            observed_at=now,
        )
        assert weather_max.humidity == 100

        # Test invalid humidity (over 100)
        with pytest.raises(ValidationError):
            WeatherData(
                location="Test",
                temperature=20.0,
                humidity=101,
                condition="clear",
                observed_at=now,
            )

        # Test invalid humidity (negative)
        with pytest.raises(ValidationError):
            WeatherData(
                location="Test",
                temperature=20.0,
                humidity=-1,
                condition="clear",
                observed_at=now,
            )

    def test_weather_data_wind_direction_validation(self):
        """Test wind direction must be between 0 and 360"""
        now = datetime.now(timezone.utc)

        # Test valid wind direction
        weather = WeatherData(
            location="Test",
            temperature=20.0,
            humidity=50,
            condition="clear",
            observed_at=now,
            wind_direction=180,
        )
        assert weather.wind_direction == 180

        # Test invalid wind direction (over 360)
        with pytest.raises(ValidationError):
            WeatherData(
                location="Test",
                temperature=20.0,
                humidity=50,
                condition="clear",
                observed_at=now,
                wind_direction=361,
            )

        # Test invalid wind direction (negative)
        with pytest.raises(ValidationError):
            WeatherData(
                location="Test",
                temperature=20.0,
                humidity=50,
                condition="clear",
                observed_at=now,
                wind_direction=-1,
            )

    def test_weather_data_clouds_validation(self):
        """Test cloudiness must be between 0 and 100"""
        now = datetime.now(timezone.utc)

        # Test valid cloudiness
        weather = WeatherData(
            location="Test",
            temperature=20.0,
            humidity=50,
            condition="cloudy",
            observed_at=now,
            clouds=75,
        )
        assert weather.clouds == 75

        # Test invalid cloudiness (over 100)
        with pytest.raises(ValidationError):
            WeatherData(
                location="Test",
                temperature=20.0,
                humidity=50,
                condition="cloudy",
                observed_at=now,
                clouds=101,
            )

    def test_weather_data_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            WeatherData(location="Test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "temperature" in missing_fields
        assert "humidity" in missing_fields
        assert "condition" in missing_fields
        assert "observed_at" in missing_fields


class TestForecastDay:
    """Test ForecastDay model validation"""

    def test_forecast_day_creation_with_all_fields(self):
        """Test creating forecast day with all fields"""
        date = datetime.now(timezone.utc)

        forecast = ForecastDay(
            date=date,
            temp_max=28.5,
            temp_min=18.0,
            temp_avg=23.2,
            condition="rain",
            description="Light rain",
            icon="10d",
            humidity=80,
            wind_speed=4.5,
            precipitation_chance=70,
            precipitation_amount=5.2,
        )

        assert forecast.date == date
        assert forecast.temp_max == 28.5
        assert forecast.temp_min == 18.0
        assert forecast.temp_avg == 23.2
        assert forecast.condition == "rain"
        assert forecast.description == "Light rain"
        assert forecast.icon == "10d"
        assert forecast.humidity == 80
        assert forecast.wind_speed == 4.5
        assert forecast.precipitation_chance == 70
        assert forecast.precipitation_amount == 5.2

    def test_forecast_day_with_minimal_fields(self):
        """Test creating forecast day with only required fields"""
        date = datetime.now(timezone.utc)

        forecast = ForecastDay(
            date=date,
            temp_max=25.0,
            temp_min=15.0,
            condition="clear",
        )

        assert forecast.date == date
        assert forecast.temp_max == 25.0
        assert forecast.temp_min == 15.0
        assert forecast.condition == "clear"
        assert forecast.temp_avg is None
        assert forecast.description is None
        assert forecast.humidity is None
        assert forecast.wind_speed is None
        assert forecast.precipitation_chance is None

    def test_forecast_day_precipitation_chance_validation(self):
        """Test precipitation chance must be between 0 and 100"""
        date = datetime.now(timezone.utc)

        # Test valid precipitation chance
        forecast = ForecastDay(
            date=date,
            temp_max=25.0,
            temp_min=15.0,
            condition="rain",
            precipitation_chance=50,
        )
        assert forecast.precipitation_chance == 50

        # Test invalid precipitation chance (over 100)
        with pytest.raises(ValidationError):
            ForecastDay(
                date=date,
                temp_max=25.0,
                temp_min=15.0,
                condition="rain",
                precipitation_chance=101,
            )

        # Test invalid precipitation chance (negative)
        with pytest.raises(ValidationError):
            ForecastDay(
                date=date,
                temp_max=25.0,
                temp_min=15.0,
                condition="rain",
                precipitation_chance=-1,
            )


class TestWeatherForecast:
    """Test WeatherForecast model validation"""

    def test_weather_forecast_creation_with_all_fields(self):
        """Test creating weather forecast with all fields"""
        now = datetime.now(timezone.utc)
        forecast_days = [
            ForecastDay(
                date=now + timedelta(days=i),
                temp_max=25.0 + i,
                temp_min=15.0 + i,
                condition="clear",
            )
            for i in range(5)
        ]

        forecast = WeatherForecast(
            location="Paris",
            latitude=48.8566,
            longitude=2.3522,
            forecast_days=forecast_days,
            provider=WeatherProvider.WEATHERAPI.value,
            generated_at=now,
        )

        assert forecast.location == "Paris"
        assert forecast.latitude == 48.8566
        assert forecast.longitude == 2.3522
        assert len(forecast.forecast_days) == 5
        assert forecast.provider == WeatherProvider.WEATHERAPI.value
        assert forecast.generated_at == now

    def test_weather_forecast_with_minimal_fields(self):
        """Test creating weather forecast with only required fields"""
        forecast = WeatherForecast(location="Tokyo")

        assert forecast.location == "Tokyo"
        assert forecast.latitude is None
        assert forecast.longitude is None
        assert forecast.forecast_days == []
        assert forecast.provider == WeatherProvider.OPENWEATHERMAP.value
        assert isinstance(forecast.generated_at, datetime)

    def test_weather_forecast_empty_forecast_days(self):
        """Test weather forecast with empty forecast days list"""
        forecast = WeatherForecast(
            location="Berlin",
            forecast_days=[],
        )

        assert forecast.location == "Berlin"
        assert len(forecast.forecast_days) == 0


class TestWeatherAlert:
    """Test WeatherAlert model validation"""

    def test_weather_alert_creation_with_all_fields(self):
        """Test creating weather alert with all fields"""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=2)
        end = now + timedelta(hours=8)

        alert = WeatherAlert(
            id=1,
            location="Miami",
            alert_type="hurricane",
            severity=AlertSeverity.EXTREME,
            headline="Hurricane Warning",
            description="A major hurricane is approaching the area",
            start_time=start,
            end_time=end,
            source="National Weather Service",
            created_at=now,
        )

        assert alert.id == 1
        assert alert.location == "Miami"
        assert alert.alert_type == "hurricane"
        assert alert.severity == AlertSeverity.EXTREME
        assert alert.headline == "Hurricane Warning"
        assert alert.description == "A major hurricane is approaching the area"
        assert alert.start_time == start
        assert alert.end_time == end
        assert alert.source == "National Weather Service"
        assert alert.created_at == now

    def test_weather_alert_with_minimal_fields(self):
        """Test creating weather alert with only required fields"""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=1)
        end = now + timedelta(hours=3)

        alert = WeatherAlert(
            location="Seattle",
            alert_type="rain",
            headline="Heavy Rain Advisory",
            description="Heavy rainfall expected",
            start_time=start,
            end_time=end,
            source="Local Weather Station",
        )

        assert alert.location == "Seattle"
        assert alert.alert_type == "rain"
        assert alert.severity == AlertSeverity.INFO
        assert alert.headline == "Heavy Rain Advisory"
        assert alert.id is None
        assert alert.created_at is None

    def test_weather_alert_severity_levels(self):
        """Test weather alert with different severity levels"""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=1)
        end = now + timedelta(hours=3)

        for severity in [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.SEVERE,
            AlertSeverity.EXTREME,
        ]:
            alert = WeatherAlert(
                location="Test",
                alert_type="test",
                severity=severity,
                headline="Test Alert",
                description="Test description",
                start_time=start,
                end_time=end,
                source="Test Source",
            )
            assert alert.severity == severity

    def test_weather_alert_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            WeatherAlert(location="Test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "alert_type" in missing_fields
        assert "headline" in missing_fields
        assert "description" in missing_fields
        assert "start_time" in missing_fields
        assert "end_time" in missing_fields
        assert "source" in missing_fields


class TestFavoriteLocation:
    """Test FavoriteLocation model validation"""

    def test_favorite_location_creation_with_all_fields(self):
        """Test creating favorite location with all fields"""
        now = datetime.now(timezone.utc)

        location = FavoriteLocation(
            id=1,
            user_id="user_123",
            location="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            is_default=True,
            nickname="Home",
            created_at=now,
        )

        assert location.id == 1
        assert location.user_id == "user_123"
        assert location.location == "San Francisco"
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194
        assert location.is_default is True
        assert location.nickname == "Home"
        assert location.created_at == now

    def test_favorite_location_with_minimal_fields(self):
        """Test creating favorite location with only required fields"""
        location = FavoriteLocation(
            user_id="user_456",
            location="Boston",
        )

        assert location.user_id == "user_456"
        assert location.location == "Boston"
        assert location.latitude is None
        assert location.longitude is None
        assert location.is_default is False
        assert location.nickname is None
        assert location.id is None
        assert location.created_at is None

    def test_favorite_location_default_flag(self):
        """Test favorite location default flag"""
        location_default = FavoriteLocation(
            user_id="user_123",
            location="Chicago",
            is_default=True,
        )
        assert location_default.is_default is True

        location_not_default = FavoriteLocation(
            user_id="user_123",
            location="Austin",
            is_default=False,
        )
        assert location_not_default.is_default is False

    def test_favorite_location_with_nickname(self):
        """Test favorite location with nickname"""
        location = FavoriteLocation(
            user_id="user_789",
            location="Denver",
            nickname="Weekend Spot",
        )

        assert location.nickname == "Weekend Spot"

    def test_favorite_location_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            FavoriteLocation(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "location" in missing_fields


class TestWeatherCurrentRequest:
    """Test WeatherCurrentRequest model validation"""

    def test_weather_current_request_with_defaults(self):
        """Test current weather request with default values"""
        request = WeatherCurrentRequest(location="New York")

        assert request.location == "New York"
        assert request.units == "metric"

    def test_weather_current_request_with_imperial_units(self):
        """Test current weather request with imperial units"""
        request = WeatherCurrentRequest(
            location="Los Angeles",
            units="imperial",
        )

        assert request.location == "Los Angeles"
        assert request.units == "imperial"

    def test_weather_current_request_with_coordinates(self):
        """Test current weather request with coordinates"""
        request = WeatherCurrentRequest(
            location="40.7128,-74.0060",
            units="metric",
        )

        assert request.location == "40.7128,-74.0060"
        assert request.units == "metric"

    def test_weather_current_request_missing_location(self):
        """Test that missing location raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            WeatherCurrentRequest(units="metric")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "location" in missing_fields


class TestWeatherForecastRequest:
    """Test WeatherForecastRequest model validation"""

    def test_weather_forecast_request_with_defaults(self):
        """Test forecast request with default values"""
        request = WeatherForecastRequest(location="London")

        assert request.location == "London"
        assert request.days == 5
        assert request.units == "metric"

    def test_weather_forecast_request_custom_days(self):
        """Test forecast request with custom number of days"""
        request = WeatherForecastRequest(
            location="Paris",
            days=10,
            units="imperial",
        )

        assert request.location == "Paris"
        assert request.days == 10
        assert request.units == "imperial"

    def test_weather_forecast_request_days_validation(self):
        """Test days must be between 1 and 16"""
        # Test valid days
        request = WeatherForecastRequest(location="Test", days=1)
        assert request.days == 1

        request = WeatherForecastRequest(location="Test", days=16)
        assert request.days == 16

        # Test invalid days (less than 1)
        with pytest.raises(ValidationError):
            WeatherForecastRequest(location="Test", days=0)

        # Test invalid days (more than 16)
        with pytest.raises(ValidationError):
            WeatherForecastRequest(location="Test", days=17)

    def test_weather_forecast_request_missing_location(self):
        """Test that missing location raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            WeatherForecastRequest(days=5)

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "location" in missing_fields


class TestLocationSaveRequest:
    """Test LocationSaveRequest model validation"""

    def test_location_save_request_with_all_fields(self):
        """Test location save request with all fields"""
        request = LocationSaveRequest(
            user_id="user_123",
            location="New York",
            latitude=40.7128,
            longitude=-74.0060,
            is_default=True,
            nickname="Work",
        )

        assert request.user_id == "user_123"
        assert request.location == "New York"
        assert request.latitude == 40.7128
        assert request.longitude == -74.0060
        assert request.is_default is True
        assert request.nickname == "Work"

    def test_location_save_request_with_minimal_fields(self):
        """Test location save request with only required fields"""
        request = LocationSaveRequest(
            user_id="user_456",
            location="San Francisco",
        )

        assert request.user_id == "user_456"
        assert request.location == "San Francisco"
        assert request.latitude is None
        assert request.longitude is None
        assert request.is_default is False
        assert request.nickname is None

    def test_location_save_request_default_false(self):
        """Test location save request with is_default explicitly False"""
        request = LocationSaveRequest(
            user_id="user_789",
            location="Boston",
            is_default=False,
        )

        assert request.is_default is False

    def test_location_save_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            LocationSaveRequest(location="Test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "user_id" in missing_fields


class TestWeatherCurrentResponse:
    """Test WeatherCurrentResponse model"""

    def test_weather_current_response_creation(self):
        """Test creating weather current response"""
        now = datetime.now(timezone.utc)

        response = WeatherCurrentResponse(
            location="Tokyo",
            temperature=18.5,
            feels_like=17.0,
            humidity=75,
            condition="cloudy",
            description="Partly cloudy",
            icon="02d",
            wind_speed=3.5,
            observed_at=now,
            cached=False,
        )

        assert response.location == "Tokyo"
        assert response.temperature == 18.5
        assert response.feels_like == 17.0
        assert response.humidity == 75
        assert response.condition == "cloudy"
        assert response.description == "Partly cloudy"
        assert response.icon == "02d"
        assert response.wind_speed == 3.5
        assert response.observed_at == now
        assert response.cached is False

    def test_weather_current_response_minimal(self):
        """Test weather current response with minimal fields"""
        now = datetime.now(timezone.utc)

        response = WeatherCurrentResponse(
            location="Sydney",
            temperature=22.0,
            feels_like=None,
            humidity=60,
            condition="clear",
            description=None,
            icon=None,
            wind_speed=None,
            observed_at=now,
        )

        assert response.location == "Sydney"
        assert response.temperature == 22.0
        assert response.humidity == 60
        assert response.condition == "clear"
        assert response.cached is False

    def test_weather_current_response_cached(self):
        """Test weather current response with cached flag"""
        now = datetime.now(timezone.utc)

        response = WeatherCurrentResponse(
            location="Berlin",
            temperature=12.0,
            feels_like=10.5,
            humidity=80,
            condition="rain",
            description="Light rain",
            icon="10d",
            wind_speed=5.0,
            observed_at=now,
            cached=True,
        )

        assert response.cached is True


class TestWeatherForecastResponse:
    """Test WeatherForecastResponse model"""

    def test_weather_forecast_response_creation(self):
        """Test creating weather forecast response"""
        now = datetime.now(timezone.utc)
        forecast_days = [
            ForecastDay(
                date=now + timedelta(days=i),
                temp_max=20.0 + i,
                temp_min=10.0 + i,
                condition="clear",
            )
            for i in range(3)
        ]

        response = WeatherForecastResponse(
            location="Madrid",
            forecast=forecast_days,
            generated_at=now,
            cached=False,
        )

        assert response.location == "Madrid"
        assert len(response.forecast) == 3
        assert response.generated_at == now
        assert response.cached is False

    def test_weather_forecast_response_empty_forecast(self):
        """Test weather forecast response with empty forecast"""
        now = datetime.now(timezone.utc)

        response = WeatherForecastResponse(
            location="Rome",
            forecast=[],
            generated_at=now,
        )

        assert response.location == "Rome"
        assert len(response.forecast) == 0
        assert response.cached is False

    def test_weather_forecast_response_cached(self):
        """Test weather forecast response with cached flag"""
        now = datetime.now(timezone.utc)
        forecast_days = [
            ForecastDay(
                date=now + timedelta(days=1),
                temp_max=25.0,
                temp_min=15.0,
                condition="sunny",
            )
        ]

        response = WeatherForecastResponse(
            location="Athens",
            forecast=forecast_days,
            generated_at=now,
            cached=True,
        )

        assert response.cached is True


class TestLocationListResponse:
    """Test LocationListResponse model"""

    def test_location_list_response(self):
        """Test location list response"""
        locations = [
            FavoriteLocation(
                id=i,
                user_id="user_123",
                location=f"Location {i}",
                is_default=(i == 0),
            )
            for i in range(3)
        ]

        response = LocationListResponse(
            locations=locations,
            total=3,
        )

        assert len(response.locations) == 3
        assert response.total == 3
        assert response.locations[0].is_default is True
        assert response.locations[1].is_default is False

    def test_location_list_response_empty(self):
        """Test location list response with empty list"""
        response = LocationListResponse(
            locations=[],
            total=0,
        )

        assert len(response.locations) == 0
        assert response.total == 0

    def test_location_list_response_single_location(self):
        """Test location list response with single location"""
        location = FavoriteLocation(
            id=1,
            user_id="user_456",
            location="Vancouver",
            is_default=True,
        )

        response = LocationListResponse(
            locations=[location],
            total=1,
        )

        assert len(response.locations) == 1
        assert response.total == 1
        assert response.locations[0].location == "Vancouver"


class TestWeatherAlertResponse:
    """Test WeatherAlertResponse model"""

    def test_weather_alert_response(self):
        """Test weather alert response"""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=2)
        end = now + timedelta(hours=6)

        alerts = [
            WeatherAlert(
                id=1,
                location="Houston",
                alert_type="storm",
                severity=AlertSeverity.SEVERE,
                headline="Severe Thunderstorm Warning",
                description="Severe thunderstorms expected",
                start_time=start,
                end_time=end,
                source="NWS",
            ),
            WeatherAlert(
                id=2,
                location="Houston",
                alert_type="flood",
                severity=AlertSeverity.WARNING,
                headline="Flood Watch",
                description="Potential flooding in low areas",
                start_time=start,
                end_time=end,
                source="NWS",
            ),
        ]

        response = WeatherAlertResponse(
            alerts=alerts,
            location="Houston",
            checked_at=now,
        )

        assert len(response.alerts) == 2
        assert response.location == "Houston"
        assert response.checked_at == now
        assert response.alerts[0].severity == AlertSeverity.SEVERE
        assert response.alerts[1].severity == AlertSeverity.WARNING

    def test_weather_alert_response_no_alerts(self):
        """Test weather alert response with no alerts"""
        now = datetime.now(timezone.utc)

        response = WeatherAlertResponse(
            alerts=[],
            location="Phoenix",
            checked_at=now,
        )

        assert len(response.alerts) == 0
        assert response.location == "Phoenix"
        assert response.checked_at == now

    def test_weather_alert_response_single_alert(self):
        """Test weather alert response with single alert"""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=1)
        end = now + timedelta(hours=4)

        alert = WeatherAlert(
            location="Dallas",
            alert_type="heat",
            severity=AlertSeverity.WARNING,
            headline="Heat Advisory",
            description="Excessive heat expected",
            start_time=start,
            end_time=end,
            source="NWS",
        )

        response = WeatherAlertResponse(
            alerts=[alert],
            location="Dallas",
            checked_at=now,
        )

        assert len(response.alerts) == 1
        assert response.alerts[0].alert_type == "heat"


if __name__ == "__main__":
    pytest.main([__file__])
