"""
Weather Service Microservice

天气服务微服务 - 提供天气数据查询和缓存功能
"""

from .client import WeatherServiceClient
from .weather_service import WeatherService
from .weather_repository import WeatherRepository
from .models import (
    WeatherData,
    WeatherForecast,
    WeatherCurrentRequest,
    WeatherForecastRequest,
    WeatherCurrentResponse,
    WeatherForecastResponse,
    WeatherProvider
)

__version__ = "1.0.0"
__all__ = [
    "WeatherServiceClient",
    "WeatherService",
    "WeatherRepository",
    "WeatherData",
    "WeatherForecast",
    "WeatherCurrentRequest",
    "WeatherForecastRequest",
    "WeatherCurrentResponse",
    "WeatherForecastResponse",
    "WeatherProvider"
]

