"""
Weather Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# Define all routes
SERVICE_ROUTES = [
    {
        "path": "/",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Root health check"
    },
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check"
    },
    {
        "path": "/api/v1/weather/current",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get current weather for a location"
    },
    {
        "path": "/api/v1/weather/forecast",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get weather forecast"
    },
    {
        "path": "/api/v1/weather/alerts",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get weather alerts"
    },
    {
        "path": "/api/v1/weather/locations",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Save favorite location"
    },
    {
        "path": "/api/v1/weather/locations/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user locations"
    },
    {
        "path": "/api/v1/weather/locations/{location_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete location"
    },
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have 512 character limit
    """
    # Categorize routes
    health_routes = []
    weather_routes = []
    location_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        if path in ["/", "/health"]:
            health_routes.append(path.replace("/", "root") if path == "/" else "health")
        elif "/weather/" in path and "/locations" not in path:
            # Weather data routes
            compact_path = path.replace("/api/v1/weather/", "")
            weather_routes.append(compact_path)
        elif "/locations" in path:
            # Location management routes
            compact_path = path.replace("/api/v1/weather/locations", "")
            if not compact_path:
                compact_path = "/"
            location_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/weather",
        "health": ",".join(health_routes),
        "weather": ",".join(weather_routes),
        "locations": ",".join(location_routes),
        "methods": "GET,POST,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# Service metadata
SERVICE_METADATA = {
    "service_name": "weather_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "weather", "data"],
    "capabilities": [
        "current_weather",
        "weather_forecast",
        "weather_alerts",
        "location_management",
        "weather_caching"
    ]
}
