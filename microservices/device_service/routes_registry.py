"""
Device Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# Define all routes
SERVICE_ROUTES = [
    # Health Check
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Basic health check"
    },
    {
        "path": "/health/detailed",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Detailed health check"
    },

    # Device Management
    {
        "path": "/api/v1/devices",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Register new device"
    },
    {
        "path": "/api/v1/devices",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List devices"
    },
    {
        "path": "/api/v1/devices/{device_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device details"
    },
    {
        "path": "/api/v1/devices/{device_id}",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Update device"
    },
    {
        "path": "/api/v1/devices/{device_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete device"
    },

    # Device Authentication & Commands
    {
        "path": "/api/v1/devices/auth",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Device authentication"
    },
    {
        "path": "/api/v1/devices/{device_id}/commands",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Send command to device"
    },
    {
        "path": "/api/v1/devices/{device_id}/health",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device health status"
    },

    # Device Groups
    {
        "path": "/api/v1/groups",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create device group"
    },
    {
        "path": "/api/v1/groups/{group_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device group"
    },
    {
        "path": "/api/v1/groups/{group_id}/devices/{device_id}",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Add device to group"
    },

    # Bulk Operations
    {
        "path": "/api/v1/devices/bulk/register",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Bulk device registration"
    },
    {
        "path": "/api/v1/devices/bulk/commands",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Bulk device commands"
    },

    # Frame Management (Digital Photo Frame)
    {
        "path": "/api/v1/devices/frames",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List frame devices"
    },
    {
        "path": "/api/v1/devices/frames/{frame_id}/display",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Display content on frame"
    },
    {
        "path": "/api/v1/devices/frames/{frame_id}/sync",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Sync frame with cloud"
    },
    {
        "path": "/api/v1/devices/frames/{frame_id}/config",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Update frame configuration"
    },

    # Statistics & Debug
    {
        "path": "/api/v1/devices/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device statistics"
    },
    {
        "path": "/api/v1/service/stats",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get service statistics"
    },
    {
        "path": "/api/v1/debug/consul",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Debug Consul registration"
    }
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have a 512 character limit
    """
    # Categorize routes
    health_routes = []
    device_routes = []
    group_routes = []
    bulk_routes = []
    frame_routes = []
    stats_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation
        compact_path = path.replace("/api/v1/devices/", "").replace("/api/v1/", "")

        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "bulk" in path:
            bulk_routes.append(compact_path)
        elif "frames" in path or "frame_id" in path:
            frame_routes.append(compact_path)
        elif "groups" in path or "group_id" in path:
            group_routes.append(compact_path)
        elif "stats" in path or "debug" in path:
            stats_routes.append(compact_path)
        elif path.startswith("/api/v1/devices"):
            device_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/devices",
        "health": ",".join(health_routes),
        "device": ",".join(device_routes[:5]),  # Limit to avoid 512 char limit
        "group": ",".join(group_routes),
        "bulk": ",".join(bulk_routes),
        "frame": ",".join(frame_routes[:3]),  # Limit to avoid 512 char limit
        "stats": ",".join(stats_routes),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


# Service metadata
SERVICE_METADATA = {
    "service_name": "device_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "device", "iot"],
    "capabilities": [
        "device_registration",
        "device_authentication",
        "device_lifecycle",
        "device_commands",
        "device_groups",
        "bulk_operations",
        "frame_management",
        "telemetry_integration",
        "firmware_updates"
    ]
}
