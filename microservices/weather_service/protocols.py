"""
Weather Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

# Import only models (no I/O dependencies)
from .models import FavoriteLocation, WeatherAlert


# =============================================================================
# Custom Exceptions (defined here to avoid importing repository)
# =============================================================================


class WeatherServiceError(Exception):
    """Base exception for weather service"""
    pass


class WeatherNotFoundError(WeatherServiceError):
    """Raised when weather data is not available for location"""
    def __init__(self, location: str):
        self.location = location
        super().__init__(f"Weather data not found for: {location}")


class ProviderError(WeatherServiceError):
    """Raised when external weather provider fails"""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"Provider {provider} error: {message}")


class ProviderConfigurationError(WeatherServiceError):
    """Raised when provider API key is missing"""
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"API key not configured for: {provider}")


class LocationNotFoundError(WeatherServiceError):
    """Raised when saved location not found"""
    def __init__(self, location_id: int):
        self.location_id = location_id
        super().__init__(f"Location not found: {location_id}")


class InvalidCoordinatesError(WeatherServiceError):
    """Raised when coordinates are invalid"""
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        super().__init__(f"Invalid coordinates: ({latitude}, {longitude})")


class ForecastDaysExceededError(WeatherServiceError):
    """Raised when forecast days exceed provider limit"""
    def __init__(self, requested: int, maximum: int):
        self.requested = requested
        self.maximum = maximum
        super().__init__(f"Forecast days {requested} exceeds maximum {maximum}")


class LocationLimitExceededError(WeatherServiceError):
    """Raised when user exceeds saved location limit"""
    def __init__(self, user_id: str, limit: int):
        self.user_id = user_id
        self.limit = limit
        super().__init__(f"User {user_id} exceeded location limit of {limit}")


# =============================================================================
# Repository Protocol
# =============================================================================


@runtime_checkable
class WeatherRepositoryProtocol(Protocol):
    """
    Interface for Weather Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.

    Implementations:
    - WeatherRepository (production - PostgreSQL + Redis)
    - MockWeatherRepository (testing)
    """

    # -------------------------------------------------------------------------
    # Cache Operations
    # -------------------------------------------------------------------------

    async def get_cached_weather(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached weather data.

        Two-tier lookup: Redis (hot) -> PostgreSQL (warm)

        Args:
            cache_key: Cache key (e.g., "weather:current:London:metric")

        Returns:
            Cached weather data or None if cache miss/expired
        """
        ...

    async def set_cached_weather(
        self, cache_key: str, data: Dict[str, Any], ttl_seconds: int = 900
    ) -> bool:
        """
        Cache weather data in both Redis and PostgreSQL.

        Args:
            cache_key: Cache key
            data: Weather data to cache
            ttl_seconds: Time-to-live in seconds (default 15 minutes)

        Returns:
            True if cached successfully
        """
        ...

    async def clear_location_cache(self, location: str) -> None:
        """
        Clear all cache entries for a location.

        Args:
            location: Location name to clear
        """
        ...

    # -------------------------------------------------------------------------
    # Favorite Locations
    # -------------------------------------------------------------------------

    async def save_location(
        self, location_data: Dict[str, Any]
    ) -> Optional[FavoriteLocation]:
        """
        Save user's favorite location.

        If is_default=True, unsets other defaults first.

        Args:
            location_data: Location data including user_id, location, lat/lon

        Returns:
            Created FavoriteLocation or None if failed
        """
        ...

    async def get_user_locations(self, user_id: str) -> List[FavoriteLocation]:
        """
        Get all saved locations for a user.

        Args:
            user_id: User identifier

        Returns:
            List of FavoriteLocation, default first
        """
        ...

    async def get_default_location(self, user_id: str) -> Optional[FavoriteLocation]:
        """
        Get user's default location.

        Args:
            user_id: User identifier

        Returns:
            Default FavoriteLocation or None
        """
        ...

    async def delete_location(self, location_id: int, user_id: str) -> bool:
        """
        Delete a saved location.

        Args:
            location_id: Location to delete
            user_id: Owner user ID (for authorization)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        ...

    # -------------------------------------------------------------------------
    # Weather Alerts
    # -------------------------------------------------------------------------

    async def save_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Save weather alert.

        Args:
            alert_data: Alert data including location, type, severity, times

        Returns:
            True if saved successfully
        """
        ...

    async def get_active_alerts(self, location: str) -> List[Dict[str, Any]]:
        """
        Get active alerts for a location.

        Args:
            location: Location name

        Returns:
            List of active alerts (end_time >= now), sorted by severity
        """
        ...


# =============================================================================
# Event Bus Protocol
# =============================================================================


@runtime_checkable
class EventBusProtocol(Protocol):
    """
    Interface for Event Bus - no I/O imports.

    Implementations:
    - NATSClient (production)
    - MockEventBus (testing)
    """

    async def publish_event(self, event: Any) -> None:
        """
        Publish an event to NATS.

        Args:
            event: Event object with event_type and data
        """
        ...

    async def close(self) -> None:
        """Close event bus connection."""
        ...


# =============================================================================
# Weather Provider Protocol
# =============================================================================


@runtime_checkable
class WeatherProviderProtocol(Protocol):
    """
    Interface for external weather provider clients.

    Implementations:
    - OpenWeatherMapClient (production)
    - WeatherAPIClient (production)
    - MockWeatherProvider (testing)
    """

    @property
    def is_configured(self) -> bool:
        """Check if provider API key is configured."""
        ...

    async def get_current_weather(
        self, location: str, units: str = "metric"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch current weather from provider.

        Args:
            location: City name or coordinates
            units: "metric" (Celsius) or "imperial" (Fahrenheit)

        Returns:
            Normalized weather data or None if failed
        """
        ...

    async def get_forecast(
        self, location: str, days: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch weather forecast from provider.

        Args:
            location: City name or coordinates
            days: Number of forecast days

        Returns:
            Normalized forecast data or None if failed
        """
        ...

    async def close(self) -> None:
        """Close HTTP client connections."""
        ...


# =============================================================================
# Cache Protocol (for Redis)
# =============================================================================


@runtime_checkable
class CacheProtocol(Protocol):
    """
    Interface for Redis cache operations.

    Implementations:
    - redis.Redis (production)
    - MockCache (testing)
    """

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        ...

    def setex(self, key: str, time: int, value: str) -> None:
        """Set value with TTL in seconds."""
        ...

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        ...

    def scan_iter(self, match: str) -> Any:
        """Scan keys matching pattern."""
        ...


# =============================================================================
# Client Protocols (for service-to-service communication)
# =============================================================================


@runtime_checkable
class AccountClientProtocol(Protocol):
    """
    Client for account_service.

    Used to verify user existence when saving locations.
    """

    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by ID."""
        ...

    async def verify_account_exists(self, account_id: str) -> bool:
        """Check if account exists."""
        ...

    async def close(self) -> None:
        """Close HTTP client."""
        ...
