"""
Weather Service - Mock Dependencies

Mock implementations for component testing.
Implements protocol interfaces for testability.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import json

from microservices.weather_service.models import FavoriteLocation, WeatherAlert


class MockWeatherRepository:
    """Mock weather repository for component testing

    Implements WeatherRepositoryProtocol interface.
    """

    def __init__(self):
        self._weather_cache: Dict[str, Dict[str, Any]] = {}
        self._locations: Dict[int, FavoriteLocation] = {}
        self._alerts: Dict[str, List[Dict[str, Any]]] = {}
        self._call_log: List[Dict] = []
        self._next_location_id = 1

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert method called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    def set_cached_weather_data(self, cache_key: str, data: Dict[str, Any]):
        """Pre-populate cache for testing"""
        self._weather_cache[cache_key] = data

    def set_location(self, location: FavoriteLocation):
        """Pre-populate location for testing"""
        if location.id is None:
            location.id = self._next_location_id
            self._next_location_id += 1
        self._locations[location.id] = location

    def set_alerts(self, location: str, alerts: List[Dict[str, Any]]):
        """Pre-populate alerts for testing"""
        self._alerts[location] = alerts

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def get_cached_weather(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached weather data"""
        self._log_call("get_cached_weather", cache_key=cache_key)
        return self._weather_cache.get(cache_key)

    async def set_cached_weather(
        self, cache_key: str, data: Dict[str, Any], ttl_seconds: int = 900
    ) -> bool:
        """Cache weather data"""
        self._log_call("set_cached_weather", cache_key=cache_key, data=data, ttl_seconds=ttl_seconds)
        self._weather_cache[cache_key] = data
        return True

    async def clear_location_cache(self, location: str) -> None:
        """Clear cache entries for a location"""
        self._log_call("clear_location_cache", location=location)
        keys_to_delete = [k for k in self._weather_cache if location in k]
        for key in keys_to_delete:
            del self._weather_cache[key]

    # =========================================================================
    # Favorite Locations
    # =========================================================================

    async def save_location(
        self, location_data: Dict[str, Any]
    ) -> Optional[FavoriteLocation]:
        """Save user's favorite location"""
        self._log_call("save_location", location_data=location_data)

        user_id = location_data.get("user_id")
        is_default = location_data.get("is_default", False)

        # If setting as default, unset others
        if is_default:
            for loc in self._locations.values():
                if loc.user_id == user_id:
                    loc.is_default = False

        # Create location
        location = FavoriteLocation(
            id=self._next_location_id,
            user_id=user_id,
            location=location_data.get("location"),
            latitude=location_data.get("latitude"),
            longitude=location_data.get("longitude"),
            is_default=is_default,
            nickname=location_data.get("nickname"),
            created_at=datetime.now(timezone.utc),
        )
        self._locations[self._next_location_id] = location
        self._next_location_id += 1

        return location

    async def get_user_locations(self, user_id: str) -> List[FavoriteLocation]:
        """Get all locations for a user"""
        self._log_call("get_user_locations", user_id=user_id)
        user_locations = [
            loc for loc in self._locations.values()
            if loc.user_id == user_id
        ]
        # Sort by is_default DESC, created_at DESC
        user_locations.sort(
            key=lambda x: (not x.is_default, x.created_at or datetime.min.replace(tzinfo=timezone.utc)),
            reverse=False
        )
        return user_locations

    async def get_default_location(self, user_id: str) -> Optional[FavoriteLocation]:
        """Get user's default location"""
        self._log_call("get_default_location", user_id=user_id)
        for loc in self._locations.values():
            if loc.user_id == user_id and loc.is_default:
                return loc
        return None

    async def delete_location(self, location_id: int, user_id: str) -> bool:
        """Delete a saved location"""
        self._log_call("delete_location", location_id=location_id, user_id=user_id)
        if location_id in self._locations:
            loc = self._locations[location_id]
            if loc.user_id == user_id:
                del self._locations[location_id]
                return True
        return False

    # =========================================================================
    # Weather Alerts
    # =========================================================================

    async def save_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Save weather alert"""
        self._log_call("save_alert", alert_data=alert_data)
        location = alert_data.get("location", "")
        if location not in self._alerts:
            self._alerts[location] = []
        self._alerts[location].append(alert_data)
        return True

    async def get_active_alerts(self, location: str) -> List[Dict[str, Any]]:
        """Get active alerts for a location"""
        self._log_call("get_active_alerts", location=location)
        now = datetime.now(timezone.utc)
        alerts = self._alerts.get(location, [])
        # Filter active alerts
        active = []
        for alert in alerts:
            end_time = alert.get("end_time")
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            if end_time and end_time >= now:
                active.append(alert)
        return active


class MockEventBus:
    """Mock NATS event bus for testing"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []
        self._connected = False

    async def connect(self) -> None:
        """Connect to event bus"""
        self._call_log.append({"method": "connect"})
        self._connected = True

    async def close(self) -> None:
        """Close event bus connection"""
        self._call_log.append({"method": "close"})
        self._connected = False

    async def publish_event(self, event: Any) -> None:
        """Publish event"""
        self._call_log.append({"method": "publish_event", "event": event})
        self.published_events.append(event)

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            event_types = [getattr(e, "event_type", str(e)) for e in self.published_events]
            assert any(event_type in str(et) for et in event_types), \
                f"Expected {event_type} event, got {event_types}"

    def assert_not_published(self):
        """Assert no events were published"""
        assert len(self.published_events) == 0, \
            f"Expected no events, but {len(self.published_events)} were published"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def clear(self):
        """Clear published events"""
        self.published_events.clear()
        self._call_log.clear()


class MockWeatherProvider:
    """Mock external weather provider for testing"""

    def __init__(self, is_configured: bool = True):
        self._is_configured = is_configured
        self._current_weather: Optional[Dict[str, Any]] = None
        self._forecast: Optional[Dict[str, Any]] = None
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    @property
    def is_configured(self) -> bool:
        """Check if provider is configured"""
        return self._is_configured

    def set_current_weather(self, data: Dict[str, Any]):
        """Set current weather response"""
        self._current_weather = data

    def set_forecast(self, data: Dict[str, Any]):
        """Set forecast response"""
        self._forecast = data

    def set_error(self, error: Exception):
        """Set error to raise"""
        self._error = error

    async def get_current_weather(
        self, location: str, units: str = "metric"
    ) -> Optional[Dict[str, Any]]:
        """Fetch current weather"""
        self._call_log.append({
            "method": "get_current_weather",
            "location": location,
            "units": units
        })

        if self._error:
            raise self._error

        if not self._is_configured:
            return None

        if self._current_weather:
            return self._current_weather

        # Default mock response
        return {
            "location": location,
            "temperature": 20.0,
            "feels_like": 19.0,
            "humidity": 65,
            "condition": "clear",
            "description": "Clear sky",
            "icon": "01d",
            "wind_speed": 5.0,
            "observed_at": datetime.now(timezone.utc),
        }

    async def get_forecast(
        self, location: str, days: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Fetch weather forecast"""
        self._call_log.append({
            "method": "get_forecast",
            "location": location,
            "days": days
        })

        if self._error:
            raise self._error

        if not self._is_configured:
            return None

        if self._forecast:
            return self._forecast

        # Default mock response
        now = datetime.now(timezone.utc)
        forecast_days = []
        for i in range(days):
            forecast_days.append({
                "date": now + timedelta(days=i),
                "temp_max": 25.0 + i,
                "temp_min": 15.0 + i,
                "condition": "clear",
                "description": "Clear sky",
                "humidity": 60,
            })

        return {
            "location": location,
            "forecast": forecast_days,
            "generated_at": now,
        }

    async def close(self) -> None:
        """Close HTTP client"""
        self._call_log.append({"method": "close"})


class MockCache:
    """Mock Redis cache for testing"""

    def __init__(self):
        self._data: Dict[str, str] = {}
        self._ttls: Dict[str, int] = {}
        self._call_log: List[Dict] = []

    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        self._call_log.append({"method": "get", "key": key})
        return self._data.get(key)

    def setex(self, key: str, time: int, value: str) -> None:
        """Set value with TTL"""
        self._call_log.append({"method": "setex", "key": key, "time": time})
        self._data[key] = value
        self._ttls[key] = time

    def delete(self, key: str) -> None:
        """Delete key from cache"""
        self._call_log.append({"method": "delete", "key": key})
        self._data.pop(key, None)
        self._ttls.pop(key, None)

    def scan_iter(self, match: str):
        """Scan keys matching pattern"""
        self._call_log.append({"method": "scan_iter", "match": match})
        import fnmatch
        for key in list(self._data.keys()):
            if fnmatch.fnmatch(key, match):
                yield key

    def clear(self):
        """Clear all data"""
        self._data.clear()
        self._ttls.clear()
        self._call_log.clear()
