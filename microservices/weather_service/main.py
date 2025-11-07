"""
Weather Service - Main Application

天气服务微服务主应用
"""

from fastapi import FastAPI, HTTPException, Query, Path, Body
from contextlib import asynccontextmanager
from typing import Optional
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from isa_common.consul_client import ConsulRegistry
from .models import (
    WeatherCurrentRequest, WeatherForecastRequest, LocationSaveRequest,
    WeatherCurrentResponse, WeatherForecastResponse,
    LocationListResponse, WeatherAlertResponse
)
from .weather_service import WeatherService
from .weather_repository import WeatherRepository
from .routes_registry import get_routes_for_consul, SERVICE_METADATA

# Initialize config
config_manager = ConfigManager("weather_service")
config = config_manager.get_service_config()

# Setup logger
app_logger = setup_service_logger("weather_service")
logger = app_logger

# Service instance
class WeatherMicroservice:
    def __init__(self):
        self.service = None
        self.repository = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self):
        # Initialize event bus
        try:
            self.event_bus = await get_event_bus("weather_service")
            logger.info("✅ Event bus initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
            self.event_bus = None

        self.repository = WeatherRepository(config=config_manager)
        self.service = WeatherService(event_bus=self.event_bus)
        logger.info("Weather service initialized")

        # Consul service registration
        if config.consul_enabled:
            try:
                # Get route metadata
                route_meta = get_routes_for_consul()

                # Merge service metadata
                consul_meta = {
                    'version': SERVICE_METADATA['version'],
                    'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                    **route_meta
                }

                self.consul_registry = ConsulRegistry(
                    service_name=SERVICE_METADATA['service_name'],
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port,
                    tags=SERVICE_METADATA['tags'],
                    meta=consul_meta,
                    health_check_type='http'
                )
                self.consul_registry.register()
                logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count')} routes")
            except Exception as e:
                logger.warning(f"⚠️  Failed to register with Consul: {e}")
                self.consul_registry = None

    async def shutdown(self):
        # Consul deregistration
        if self.consul_registry:
            try:
                self.consul_registry.deregister()
                logger.info("✅ Service deregistered from Consul")
            except Exception as e:
                logger.error(f"❌ Failed to deregister from Consul: {e}")

        if self.event_bus:
            try:
                await self.event_bus.close()
                logger.info("Weather event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")
        if self.service:
            await self.service.close()
        logger.info("Weather service shutting down")

# Global instance
microservice = WeatherMicroservice()

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    await microservice.initialize()

    yield

    # Shutdown
    await microservice.shutdown()

# Create FastAPI application
app = FastAPI(
    title="Weather Service",
    description="天气服务微服务 - Weather data fetching and caching",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "weather_service",
        "version": "1.0.0"
    }


# =============================================================================
# Weather Data Endpoints
# =============================================================================

@app.get("/api/v1/weather/current", response_model=WeatherCurrentResponse)
async def get_current_weather(
    location: str = Query(..., description="Location name (e.g., 'New York', 'London')"),
    units: str = Query("metric", description="Units system (metric/imperial)")
):
    """
    获取当前天气
    
    Get current weather for a location
    
    - **location**: Location name or coordinates
    - **units**: metric (Celsius) or imperial (Fahrenheit)
    """
    try:
        request = WeatherCurrentRequest(location=location, units=units)
        weather = await microservice.service.get_current_weather(request)
        
        if not weather:
            raise HTTPException(status_code=404, detail="Weather data not found")
        
        return weather
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/weather/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    location: str = Query(..., description="Location name"),
    days: int = Query(5, ge=1, le=16, description="Number of forecast days"),
    units: str = Query("metric", description="Units system (metric/imperial)")
):
    """
    获取天气预报
    
    Get weather forecast for multiple days
    
    - **location**: Location name
    - **days**: Number of forecast days (1-16)
    - **units**: metric or imperial
    """
    try:
        request = WeatherForecastRequest(location=location, days=days, units=units)
        forecast = await microservice.service.get_forecast(request)
        
        if not forecast:
            raise HTTPException(status_code=404, detail="Forecast data not found")
        
        return forecast
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting forecast: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/weather/alerts", response_model=WeatherAlertResponse)
async def get_weather_alerts(
    location: str = Query(..., description="Location name")
):
    """
    获取天气预警
    
    Get active weather alerts for a location
    """
    try:
        alerts = await microservice.service.get_weather_alerts(location)
        return alerts
        
    except Exception as e:
        logger.error(f"Error getting weather alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Favorite Locations Endpoints
# =============================================================================

@app.post("/api/v1/weather/locations", status_code=201)
async def save_location(request: LocationSaveRequest = Body(...)):
    """
    保存收藏地点
    
    Save a favorite location for a user
    """
    try:
        location = await microservice.service.save_location(request)
        
        if not location:
            raise HTTPException(status_code=500, detail="Failed to save location")
        
        return location
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving location: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/weather/locations/{user_id}", response_model=LocationListResponse)
async def get_user_locations(
    user_id: str = Path(..., description="User ID")
):
    """
    获取用户的收藏地点
    
    Get all saved locations for a user
    """
    try:
        locations = await microservice.service.get_user_locations(user_id)
        return locations
        
    except Exception as e:
        logger.error(f"Error getting user locations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/v1/weather/locations/{location_id}", status_code=204)
async def delete_location(
    location_id: int = Path(..., description="Location ID"),
    user_id: str = Query(..., description="User ID for authorization")
):
    """
    删除收藏地点
    
    Delete a saved location
    """
    try:
        success = await microservice.service.delete_location(location_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Location not found")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting location: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = config.service_port if hasattr(config, 'service_port') else 8241
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

