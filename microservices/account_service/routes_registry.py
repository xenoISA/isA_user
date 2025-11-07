"""
Account Service Routes Registry

Defines all API routes for Consul service registration and discovery.
This ensures route metadata is centralized and easy to maintain.
"""

from typing import List, Dict, Any


# Route definitions for account_service
ACCOUNT_SERVICE_ROUTES = [
    # Health & Info endpoints
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check"
    },
    {
        "path": "/health/detailed",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Detailed health check with database connectivity"
    },

    # Core Account Management
    {
        "path": "/api/v1/accounts/ensure",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Ensure user account exists, create if needed"
    },
    {
        "path": "/api/v1/accounts/profile/{user_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Account profile CRUD operations"
    },
    {
        "path": "/api/v1/accounts/preferences/{user_id}",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Update account preferences"
    },

    # Account Query
    {
        "path": "/api/v1/accounts",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List accounts with filtering and pagination"
    },
    {
        "path": "/api/v1/accounts/search",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search accounts by query"
    },
    {
        "path": "/api/v1/accounts/by-email/{email}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get account by email address"
    },

    # Admin Operations
    {
        "path": "/api/v1/accounts/status/{user_id}",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Change account status (admin)"
    },

    # Service Statistics
    {
        "path": "/api/v1/accounts/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get account service statistics"
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
    account_routes = []
    query_routes = []
    admin_routes = []

    for route in ACCOUNT_SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation: just the unique part after base path
        compact_path = path.replace("/api/v1/accounts/", "").replace("/api/v1/accounts", "root")

        if "health" in path:
            health_routes.append(compact_path)
        elif "status" in path:
            admin_routes.append(compact_path)
        elif path in ["/api/v1/accounts", "/api/v1/accounts/search", "/api/v1/accounts/by-email/{email}"]:
            query_routes.append(compact_path)
        else:
            account_routes.append(compact_path)

    # Create compact route representation for meta
    # Split into multiple fields to avoid 512 char limit
    route_meta = {
        "route_count": str(len(ACCOUNT_SERVICE_ROUTES)),
        "base_path": "/api/v1/accounts",

        # Category summaries (under 512 chars each)
        "health": ",".join(health_routes),
        "account": ",".join(account_routes),
        "query": ",".join(query_routes),
        "admin": ",".join(admin_routes),

        # Methods and auth summary
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in ACCOUNT_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in ACCOUNT_SERVICE_ROUTES if r["auth_required"])),

        # Endpoint for full route details
        "routes_endpoint": "/health"
    }

    return route_meta


def get_all_routes() -> List[Dict[str, Any]]:
    """
    Get all route definitions

    Returns:
        List of all route definitions
    """
    return ACCOUNT_SERVICE_ROUTES


def get_routes_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get routes grouped by category

    Returns:
        Dictionary of routes grouped by category
    """
    categories = {
        "health": [],
        "account_management": [],
        "account_query": [],
        "admin": []
    }

    for route in ACCOUNT_SERVICE_ROUTES:
        path = route["path"]
        if "health" in path:
            categories["health"].append(route)
        elif "status" in path:
            categories["admin"].append(route)
        elif path in ["/api/v1/accounts", "/api/v1/accounts/search", "/api/v1/accounts/by-email/{email}"]:
            categories["account_query"].append(route)
        else:
            categories["account_management"].append(route)

    return categories


# Service metadata for Consul registration
SERVICE_METADATA = {
    "service_name": "account_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "account"],
    "capabilities": [
        "account_management",
        "profile_management",
        "preferences_management",
        "account_search",
        "status_management"
    ]
}
