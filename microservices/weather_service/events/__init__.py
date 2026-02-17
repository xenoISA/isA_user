"""
Weather Service Events Module

Event-driven architecture for weather-related events.
Follows the standard event-driven architecture pattern.
"""

from .handlers import get_event_handlers
from .models import (
    WeatherAlertEventData,
    WeatherLocationSavedEventData,
    create_weather_alert_event_data,
    create_weather_location_saved_event_data,
)
from .publishers import (
    publish_weather_alert,
    publish_weather_location_saved,
)

__all__ = [
    # Handlers
    "get_event_handlers",
    # Models
    "WeatherLocationSavedEventData",
    "WeatherAlertEventData",
    "create_weather_location_saved_event_data",
    "create_weather_alert_event_data",
    # Publishers
    "publish_weather_location_saved",
    "publish_weather_alert",
]
