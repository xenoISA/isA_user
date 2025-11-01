"""
Weather Service - Business Logic

天气服务业务逻辑层 - 集成外部天气API
"""

import os
import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .weather_repository import WeatherRepository
from .models import (
    WeatherCurrentRequest, WeatherForecastRequest, LocationSaveRequest,
    WeatherCurrentResponse, WeatherForecastResponse, ForecastDay,
    LocationListResponse, WeatherAlertResponse, WeatherAlert,
    WeatherProvider
)
from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger(__name__)


class WeatherService:
    """天气服务业务逻辑"""

    def __init__(self, event_bus=None):
        self.repository = WeatherRepository()
        self.event_bus = event_bus
        
        # Load API keys from environment
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY", "")
        self.weatherapi_key = os.getenv("WEATHERAPI_KEY", "")
        
        # Cache TTL settings (in seconds)
        self.current_weather_ttl = int(os.getenv("WEATHER_CACHE_TTL", "900"))  # 15 min
        self.forecast_ttl = int(os.getenv("FORECAST_CACHE_TTL", "1800"))  # 30 min
        self.alerts_ttl = int(os.getenv("ALERTS_CACHE_TTL", "600"))  # 10 min
        
        # Default provider
        self.default_provider = os.getenv("WEATHER_PROVIDER", WeatherProvider.OPENWEATHERMAP.value)
        
        # HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
    
    # =============================================================================
    # Current Weather
    # =============================================================================
    
    async def get_current_weather(self, request: WeatherCurrentRequest) -> Optional[WeatherCurrentResponse]:
        """获取当前天气"""
        try:
            cache_key = f"weather:current:{request.location}:{request.units}"
            
            # Check cache
            cached = await self.repository.get_cached_weather(cache_key)
            if cached:
                cached["cached"] = True
                return WeatherCurrentResponse(**cached)
            
            # Fetch from API
            weather_data = await self._fetch_current_weather(request.location, request.units)
            
            if not weather_data:
                return None
            
            # Cache the result
            await self.repository.set_cached_weather(
                cache_key,
                weather_data,
                self.current_weather_ttl
            )

            # Publish weather data fetched event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.WEATHER_DATA_FETCHED,
                        source=ServiceSource.WEATHER_SERVICE,
                        data={
                            "location": request.location,
                            "temperature": weather_data.get("temperature"),
                            "condition": weather_data.get("condition"),
                            "units": request.units,
                            "provider": self.default_provider,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish weather.data.fetched event: {e}")

            weather_data["cached"] = False
            return WeatherCurrentResponse(**weather_data)
            
        except Exception as e:
            logger.error(f"Failed to get current weather: {e}")
            return None
    
    async def _fetch_current_weather(self, location: str, units: str = "metric") -> Optional[Dict[str, Any]]:
        """从外部API获取当前天气"""
        if self.default_provider == WeatherProvider.OPENWEATHERMAP.value:
            return await self._fetch_openweathermap_current(location, units)
        elif self.default_provider == WeatherProvider.WEATHERAPI.value:
            return await self._fetch_weatherapi_current(location)
        else:
            logger.error(f"Unsupported provider: {self.default_provider}")
            return None
    
    async def _fetch_openweathermap_current(self, location: str, units: str) -> Optional[Dict[str, Any]]:
        """从OpenWeatherMap获取当前天气"""
        try:
            if not self.openweather_api_key:
                logger.error("OpenWeatherMap API key not configured")
                return None
            
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": self.openweather_api_key,
                "units": units
            }
            
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Transform to our format
            return {
                "location": data["name"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "condition": data["weather"][0]["main"].lower(),
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "wind_speed": data.get("wind", {}).get("speed"),
                "observed_at": datetime.utcnow()
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenWeatherMap API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None
    
    async def _fetch_weatherapi_current(self, location: str) -> Optional[Dict[str, Any]]:
        """从WeatherAPI获取当前天气"""
        try:
            if not self.weatherapi_key:
                logger.error("WeatherAPI key not configured")
                return None
            
            url = "https://api.weatherapi.com/v1/current.json"
            params = {
                "key": self.weatherapi_key,
                "q": location
            }
            
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "location": data["location"]["name"],
                "temperature": data["current"]["temp_c"],
                "feels_like": data["current"]["feelslike_c"],
                "humidity": data["current"]["humidity"],
                "condition": data["current"]["condition"]["text"].lower(),
                "description": data["current"]["condition"]["text"],
                "icon": data["current"]["condition"]["icon"],
                "wind_speed": data["current"]["wind_kph"] / 3.6,  # Convert to m/s
                "observed_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error fetching weather from WeatherAPI: {e}")
            return None
    
    # =============================================================================
    # Weather Forecast
    # =============================================================================
    
    async def get_forecast(self, request: WeatherForecastRequest) -> Optional[WeatherForecastResponse]:
        """获取天气预报"""
        try:
            cache_key = f"weather:forecast:{request.location}:{request.days}"
            
            # Check cache
            cached = await self.repository.get_cached_weather(cache_key)
            if cached:
                cached["cached"] = True
                return WeatherForecastResponse(**cached)
            
            # Fetch from API
            forecast_data = await self._fetch_forecast(request.location, request.days)
            
            if not forecast_data:
                return None
            
            # Cache the result
            await self.repository.set_cached_weather(
                cache_key,
                forecast_data,
                self.forecast_ttl
            )
            
            forecast_data["cached"] = False
            return WeatherForecastResponse(**forecast_data)
            
        except Exception as e:
            logger.error(f"Failed to get forecast: {e}")
            return None
    
    async def _fetch_forecast(self, location: str, days: int) -> Optional[Dict[str, Any]]:
        """从外部API获取天气预报"""
        if self.default_provider == WeatherProvider.OPENWEATHERMAP.value:
            return await self._fetch_openweathermap_forecast(location, days)
        elif self.default_provider == WeatherProvider.WEATHERAPI.value:
            return await self._fetch_weatherapi_forecast(location, days)
        else:
            return None
    
    async def _fetch_openweathermap_forecast(self, location: str, days: int) -> Optional[Dict[str, Any]]:
        """从OpenWeatherMap获取天气预报"""
        try:
            if not self.openweather_api_key:
                return None
            
            # OpenWeatherMap free tier only supports 5-day forecast
            cnt = min(days * 8, 40)  # 8 data points per day (3-hour intervals)
            
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "q": location,
                "appid": self.openweather_api_key,
                "units": "metric",
                "cnt": cnt
            }
            
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Group by day and aggregate
            daily_forecasts = {}
            for item in data["list"]:
                date = datetime.fromtimestamp(item["dt"]).date()
                
                if date not in daily_forecasts:
                    daily_forecasts[date] = {
                        "temps": [],
                        "condition": item["weather"][0]["main"].lower(),
                        "description": item["weather"][0]["description"],
                        "icon": item["weather"][0]["icon"],
                        "humidity": item["main"]["humidity"],
                        "wind_speed": item["wind"]["speed"]
                    }
                
                daily_forecasts[date]["temps"].append(item["main"]["temp"])
            
            # Create forecast days
            forecast_days = []
            for date, day_data in list(daily_forecasts.items())[:days]:
                forecast_days.append(ForecastDay(
                    date=datetime.combine(date, datetime.min.time()),
                    temp_max=max(day_data["temps"]),
                    temp_min=min(day_data["temps"]),
                    temp_avg=sum(day_data["temps"]) / len(day_data["temps"]),
                    condition=day_data["condition"],
                    description=day_data["description"],
                    icon=day_data["icon"],
                    humidity=day_data["humidity"],
                    wind_speed=day_data["wind_speed"]
                ).dict())
            
            return {
                "location": data["city"]["name"],
                "forecast": forecast_days,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error fetching forecast from OpenWeatherMap: {e}")
            return None
    
    async def _fetch_weatherapi_forecast(self, location: str, days: int) -> Optional[Dict[str, Any]]:
        """从WeatherAPI获取天气预报"""
        # Similar implementation for WeatherAPI
        logger.warning("WeatherAPI forecast not fully implemented")
        return None
    
    # =============================================================================
    # Weather Alerts
    # =============================================================================
    
    async def get_weather_alerts(self, location: str) -> WeatherAlertResponse:
        """获取天气预警"""
        try:
            # Check database for active alerts
            alerts = await self.repository.get_active_alerts(location)
            
            # Also fetch from API if configured
            # (OpenWeatherMap One Call API supports alerts)
            
            alert_objects = [
                WeatherAlert(**alert) for alert in alerts
            ] if alerts else []

            # Publish weather alert event if alerts exist
            if alert_objects and self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.WEATHER_ALERT_CREATED,
                        source=ServiceSource.WEATHER_SERVICE,
                        data={
                            "location": location,
                            "alert_count": len(alert_objects),
                            "alerts": [{"severity": a.severity, "alert_type": a.alert_type, "headline": a.headline} for a in alert_objects],
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish weather.alert.created event: {e}")

            return WeatherAlertResponse(
                alerts=alert_objects,
                location=location,
                checked_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to get weather alerts: {e}")
            return WeatherAlertResponse(
                alerts=[],
                location=location,
                checked_at=datetime.utcnow()
            )
    
    # =============================================================================
    # Favorite Locations
    # =============================================================================
    
    async def save_location(self, request: LocationSaveRequest) -> Optional[Dict[str, Any]]:
        """保存收藏地点"""
        try:
            location = await self.repository.save_location(request.dict())
            
            if location:
                return location.dict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to save location: {e}")
            return None
    
    async def get_user_locations(self, user_id: str) -> LocationListResponse:
        """获取用户的收藏地点"""
        try:
            locations = await self.repository.get_user_locations(user_id)
            
            return LocationListResponse(
                locations=locations,
                total=len(locations)
            )
            
        except Exception as e:
            logger.error(f"Failed to get user locations: {e}")
            return LocationListResponse(locations=[], total=0)
    
    async def delete_location(self, location_id: int, user_id: str) -> bool:
        """删除收藏地点"""
        return await self.repository.delete_location(location_id, user_id)


__all__ = ["WeatherService"]

