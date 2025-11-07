"""
Location Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# 定义所有路由
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
    # Location Management
    {
        "path": "/api/v1/locations",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create location record"
    },
    {
        "path": "/api/v1/locations/batch",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Batch create locations"
    },
    {
        "path": "/api/v1/locations/{location_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete location"
    },
    {
        "path": "/api/v1/locations/device/{device_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device locations"
    },
    {
        "path": "/api/v1/locations/device/{device_id}/latest",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device latest location"
    },
    {
        "path": "/api/v1/locations/device/{device_id}/history",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device location history"
    },
    {
        "path": "/api/v1/locations/user/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user locations"
    },
    # Geofences
    {
        "path": "/api/v1/geofences",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create geofences"
    },
    {
        "path": "/api/v1/geofences/{geofence_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete geofence"
    },
    {
        "path": "/api/v1/geofences/{geofence_id}/activate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Activate geofence"
    },
    {
        "path": "/api/v1/geofences/{geofence_id}/deactivate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Deactivate geofence"
    },
    {
        "path": "/api/v1/geofences/{geofence_id}/events",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get geofence events"
    },
    {
        "path": "/api/v1/geofences/device/{device_id}/check",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Check device in geofences"
    },
    # Places
    {
        "path": "/api/v1/places",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create place"
    },
    {
        "path": "/api/v1/places/user/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user places"
    },
    {
        "path": "/api/v1/places/{place_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete place"
    },
    # Location Search
    {
        "path": "/api/v1/locations/nearby",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search nearby locations"
    },
    {
        "path": "/api/v1/locations/search/radius",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Search within radius"
    },
    {
        "path": "/api/v1/locations/search/polygon",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Search within polygon"
    },
    # Distance & Stats
    {
        "path": "/api/v1/locations/distance",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Calculate distance between locations"
    },
    {
        "path": "/api/v1/distance",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Calculate distance"
    },
    {
        "path": "/api/v1/stats/user/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user location statistics"
    },
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = 0
    location_routes = 0
    geofence_routes = 0
    place_routes = 0
    search_routes = 0
    stats_routes = 0

    for route in SERVICE_ROUTES:
        path = route["path"]

        if "health" in path or path == "/":
            health_routes += 1
        elif "/geofences" in path:
            geofence_routes += 1
        elif "/places" in path:
            place_routes += 1
        elif "/search" in path or "/nearby" in path:
            search_routes += 1
        elif "/stats" in path or "/distance" in path:
            stats_routes += 1
        elif "/locations" in path:
            location_routes += 1

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1",
        "health": str(health_routes),
        "locations": str(location_routes),
        "geofences": str(geofence_routes),
        "places": str(place_routes),
        "search": str(search_routes),
        "stats": str(stats_routes),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "location_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "location-tracking", "geofencing"],
    "capabilities": [
        "location_tracking",
        "geofencing",
        "place_management",
        "location_search",
        "distance_calculation",
        "location_history",
        "geofence_events"
    ]
}
