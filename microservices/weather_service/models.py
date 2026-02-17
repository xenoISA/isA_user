"""
Weather Service Models

天气服务数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WeatherProvider(str, Enum):
    """天气数据提供商"""
    OPENWEATHERMAP = "openweathermap"
    WEATHERAPI = "weatherapi"
    VISUALCROSSING = "visualcrossing"


class WeatherCondition(str, Enum):
    """天气状况"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"
    MIST = "mist"
    FOG = "fog"


class AlertSeverity(str, Enum):
    """天气预警级别"""
    INFO = "info"
    WARNING = "warning"
    SEVERE = "severe"
    EXTREME = "extreme"


# Database Models

class WeatherData(BaseModel):
    """天气数据模型"""
    id: Optional[int] = None
    location: str = Field(..., description="Location name")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Current weather
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: Optional[float] = Field(None, description="Feels like temperature")
    humidity: int = Field(..., ge=0, le=100, description="Humidity percentage")
    pressure: Optional[int] = Field(None, description="Atmospheric pressure in hPa")
    wind_speed: Optional[float] = Field(None, description="Wind speed in m/s")
    wind_direction: Optional[int] = Field(None, ge=0, le=360, description="Wind direction in degrees")
    
    # Conditions
    condition: str = Field(..., description="Weather condition")
    description: Optional[str] = Field(None, description="Weather description")
    icon: Optional[str] = Field(None, description="Weather icon code")
    
    # Additional data
    visibility: Optional[float] = Field(None, description="Visibility in km")
    uv_index: Optional[float] = Field(None, description="UV index")
    clouds: Optional[int] = Field(None, ge=0, le=100, description="Cloudiness percentage")
    
    # Timestamps
    observed_at: datetime = Field(..., description="Observation time")
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    
    # Provider info
    provider: str = Field(WeatherProvider.OPENWEATHERMAP.value, description="Data provider")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    
    # Cache info
    cached_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WeatherForecast(BaseModel):
    """天气预报模型"""
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    forecast_days: List["ForecastDay"] = Field(default_factory=list)
    provider: str = WeatherProvider.OPENWEATHERMAP.value
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class ForecastDay(BaseModel):
    """每日天气预报"""
    date: datetime
    temp_max: float
    temp_min: float
    temp_avg: Optional[float] = None
    condition: str
    description: Optional[str] = None
    icon: Optional[str] = None
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    precipitation_chance: Optional[int] = Field(None, ge=0, le=100, description="Chance of precipitation %")
    precipitation_amount: Optional[float] = Field(None, description="Precipitation in mm")
    
    class Config:
        from_attributes = True


class WeatherAlert(BaseModel):
    """天气预警"""
    id: Optional[int] = None
    location: str
    alert_type: str = Field(..., description="Alert type (e.g., storm, flood, heat)")
    severity: AlertSeverity = AlertSeverity.INFO
    headline: str
    description: str
    start_time: datetime
    end_time: datetime
    source: str = Field(..., description="Alert source/provider")
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FavoriteLocation(BaseModel):
    """收藏的地点"""
    id: Optional[int] = None
    user_id: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False
    nickname: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Request Models

class WeatherCurrentRequest(BaseModel):
    """当前天气请求"""
    location: str = Field(..., description="Location name or coordinates")
    units: str = Field("metric", description="Units system (metric/imperial)")


class WeatherForecastRequest(BaseModel):
    """天气预报请求"""
    location: str
    days: int = Field(5, ge=1, le=16, description="Number of forecast days")
    units: str = Field("metric", description="Units system (metric/imperial)")


class LocationSaveRequest(BaseModel):
    """保存地点请求"""
    user_id: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False
    nickname: Optional[str] = None


# Response Models

class WeatherCurrentResponse(BaseModel):
    """当前天气响应"""
    location: str
    temperature: float
    feels_like: Optional[float]
    humidity: int
    condition: str
    description: Optional[str]
    icon: Optional[str]
    wind_speed: Optional[float]
    observed_at: datetime
    cached: bool = False
    
    class Config:
        from_attributes = True


class WeatherForecastResponse(BaseModel):
    """天气预报响应"""
    location: str
    forecast: List[ForecastDay]
    generated_at: datetime
    cached: bool = False
    
    class Config:
        from_attributes = True


class LocationListResponse(BaseModel):
    """地点列表响应"""
    locations: List[FavoriteLocation]
    total: int


class WeatherAlertResponse(BaseModel):
    """天气预警响应"""
    alerts: List[WeatherAlert]
    location: str
    checked_at: datetime


# Update ForecastDay reference
WeatherForecast.model_rebuild()


__all__ = [
    "WeatherData",
    "WeatherForecast",
    "ForecastDay",
    "WeatherAlert",
    "FavoriteLocation",
    "WeatherProvider",
    "WeatherCondition",
    "AlertSeverity",
    "WeatherCurrentRequest",
    "WeatherForecastRequest",
    "LocationSaveRequest",
    "WeatherCurrentResponse",
    "WeatherForecastResponse",
    "LocationListResponse",
    "WeatherAlertResponse"
]

