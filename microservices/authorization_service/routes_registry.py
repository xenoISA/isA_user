"""
Authorization Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# Define all routes
SERVICE_ROUTES = [
    # Health and Service Info
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
        "description": "Detailed health check with dependencies"
    },
    {
        "path": "/api/v1/authorization/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service information and capabilities"
    },
    {
        "path": "/api/v1/authorization/stats",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service statistics and metrics"
    },

    # Core Authorization
    {
        "path": "/api/v1/authorization/check-access",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Check resource access permission"
    },
    {
        "path": "/api/v1/authorization/grant",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Grant resource permission"
    },
    {
        "path": "/api/v1/authorization/revoke",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Revoke resource permission"
    },

    # Permission Management
    {
        "path": "/api/v1/authorization/user-permissions/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user permission summary"
    },
    {
        "path": "/api/v1/authorization/user-resources/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List user accessible resources"
    },

    # Bulk Operations
    {
        "path": "/api/v1/authorization/bulk-grant",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Bulk grant permissions"
    },
    {
        "path": "/api/v1/authorization/bulk-revoke",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Bulk revoke permissions"
    },

    # Administrative
    {
        "path": "/api/v1/authorization/cleanup-expired",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Cleanup expired permissions"
    }
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have a 512 character limit
    """
    # Categorize routes
    health_routes = []
    core_routes = []
    management_routes = []
    bulk_routes = []
    admin_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation
        compact_path = path.replace("/api/v1/authorization/", "")

        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "bulk" in path:
            bulk_routes.append(compact_path)
        elif "cleanup" in path:
            admin_routes.append(compact_path)
        elif "user-" in path:
            management_routes.append(compact_path)
        elif path.startswith("/api/v1/authorization"):
            core_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/authorization",
        "health": ",".join(health_routes),
        "core": ",".join(core_routes),
        "management": ",".join(management_routes),
        "bulk": ",".join(bulk_routes),
        "admin": ",".join(admin_routes),
        "methods": "GET,POST",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


# Service metadata
SERVICE_METADATA = {
    "service_name": "authorization_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "authorization", "permissions"],
    "capabilities": [
        "resource_access_control",
        "permission_management",
        "bulk_operations",
        "multi_level_authorization",
        "subscription_authorization",
        "organization_authorization"
    ]
}
