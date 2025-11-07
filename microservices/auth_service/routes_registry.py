"""
Authentication Service Routes Registry

Defines all API routes for Consul service registration and discovery.
This ensures route metadata is centralized and easy to maintain.
"""

from typing import List, Dict, Any


# Route definitions for auth_service
AUTH_SERVICE_ROUTES = [
    # Health & Info endpoints
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
        "path": "/api/v1/auth/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Authentication service information"
    },
    {
        "path": "/api/v1/auth/stats",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Authentication service statistics"
    },

    # Token verification & management
    {
        "path": "/api/v1/auth/verify-token",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Verify JWT token"
    },
    {
        "path": "/api/v1/auth/dev-token",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Generate development token"
    },
    {
        "path": "/api/v1/auth/token-pair",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Generate token pair (access + refresh)"
    },
    {
        "path": "/api/v1/auth/refresh",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Refresh access token"
    },
    {
        "path": "/api/v1/auth/user-info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Extract user info from token"
    },

    # User registration
    {
        "path": "/api/v1/auth/register",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Start user registration"
    },
    {
        "path": "/api/v1/auth/verify",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Verify registration code"
    },
    {
        "path": "/api/v1/auth/dev/pending-registration/{pending_id}",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get pending registration (dev only)"
    },

    # API Key management
    {
        "path": "/api/v1/auth/verify-api-key",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Verify API key"
    },
    {
        "path": "/api/v1/auth/api-keys",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create API key"
    },
    {
        "path": "/api/v1/auth/api-keys/{organization_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List organization API keys"
    },
    {
        "path": "/api/v1/auth/api-keys/{key_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Revoke API key"
    },

    # Device authentication
    {
        "path": "/api/v1/auth/device/register",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Register device"
    },
    {
        "path": "/api/v1/auth/device/authenticate",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Authenticate device"
    },
    {
        "path": "/api/v1/auth/device/verify-token",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Verify device token"
    },
    {
        "path": "/api/v1/auth/device/{device_id}/refresh-secret",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Refresh device secret"
    },
    {
        "path": "/api/v1/auth/device/{device_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Revoke device"
    },
    {
        "path": "/api/v1/auth/device/list",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List organization devices"
    },
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Get formatted route metadata for Consul service registration

    Note: Consul meta fields have a 512 character limit per value.
    We use compact encoding and split routes into categories.

    Returns:
        Dictionary containing route information for Consul meta field
    """
    # Group routes by category
    health_routes = []
    token_routes = []
    registration_routes = []
    api_key_routes = []
    device_routes = []

    for route in AUTH_SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation: just the unique part after base path
        compact_path = path.replace("/api/v1/auth/", "").replace("/api/v1/auth", "root")

        if path in ["/", "/health", "/api/v1/auth/info", "/api/v1/auth/stats"]:
            health_routes.append(compact_path)
        elif "token" in path or "verify" in path or "user-info" in path or "refresh" in path:
            token_routes.append(compact_path)
        elif "register" in path or "pending-registration" in path:
            registration_routes.append(compact_path)
        elif "api-key" in path:
            api_key_routes.append(compact_path)
        elif "device" in path:
            device_routes.append(compact_path)

    # Create compact route representation for meta
    # Split into multiple fields to avoid 512 char limit
    route_meta = {
        "route_count": str(len(AUTH_SERVICE_ROUTES)),
        "base_path": "/api/v1/auth",

        # Category summaries (under 512 chars each)
        "health": ",".join(health_routes),  # /,/health,info,stats
        "token": ",".join(token_routes),     # verify-token,dev-token,etc
        "registration": ",".join(registration_routes),
        "api_key": ",".join(api_key_routes),
        "device": ",".join(device_routes),

        # Methods and auth summary
        "methods": "GET,POST,DELETE",
        "public_count": str(sum(1 for r in AUTH_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in AUTH_SERVICE_ROUTES if r["auth_required"])),

        # Endpoint for full route details
        "routes_endpoint": "/api/v1/auth/info"
    }

    return route_meta


def get_all_routes() -> List[Dict[str, Any]]:
    """
    Get all route definitions

    Returns:
        List of all route definitions
    """
    return AUTH_SERVICE_ROUTES


def get_routes_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get routes grouped by category

    Returns:
        Dictionary of routes grouped by category
    """
    categories = {
        "health": [],
        "token_management": [],
        "user_registration": [],
        "api_key_management": [],
        "device_authentication": []
    }

    for route in AUTH_SERVICE_ROUTES:
        path = route["path"]
        if path in ["/", "/health", "/api/v1/auth/info", "/api/v1/auth/stats"]:
            categories["health"].append(route)
        elif "token" in path or "verify-token" in path or "user-info" in path or "refresh" in path:
            categories["token_management"].append(route)
        elif "register" in path or "pending-registration" in path:
            categories["user_registration"].append(route)
        elif "api-key" in path:
            categories["api_key_management"].append(route)
        elif "device" in path:
            categories["device_authentication"].append(route)

    return categories


# Service metadata for Consul registration
SERVICE_METADATA = {
    "service_name": "auth_service",
    "version": "2.0.0",
    "tags": ["v2", "user-microservice", "authentication"],
    "capabilities": [
        "jwt_verification",
        "api_key_management",
        "token_generation",
        "device_authentication",
        "user_registration"
    ]
}
