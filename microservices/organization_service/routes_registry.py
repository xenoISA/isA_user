"""
Organization Service Routes Registry
Defines all API routes for Consul service registration and discovery.
This ensures route metadata is centralized and easy to maintain.
"""
from typing import List, Dict, Any
# Route definitions for organization_service
ORGANIZATION_SERVICE_ROUTES = [
    # Health & Info endpoints
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check"
    },
    {
        "path": "/api/v1/organization/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check (API v1)"
    },
    {
        "path": "/api/v1/organization/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service information"
    },
    {
        "path": "/api/v1/organization/stats",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service statistics"
    },
    # Organization Management
    {
        "path": "/api/v1/organization/organizations",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create organization"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Organization CRUD operations"
    },
    {
        "path": "/api/v1/organization/organizations",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user organizations (user_id from auth)"
    },
    # Member Management
    {
        "path": "/api/v1/organization/organizations/{organization_id}/members",
        "methods": ["POST", "GET"],
        "auth_required": True,
        "description": "Organization member management"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}/members/{member_user_id}",
        "methods": ["PUT", "DELETE"],
        "auth_required": True,
        "description": "Update/remove organization member"
    },
    # Context Switching
    {
        "path": "/api/v1/organization/organizations/context",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Switch organization context"
    },
    # Statistics and Analytics
    {
        "path": "/api/v1/organization/organizations/{organization_id}/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get organization statistics"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}/usage",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get organization usage"
    },
    # Platform Admin
    {
        "path": "/api/v1/organization/admin/organizations",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List all organizations (admin)"
    },
    # Family Sharing
    {
        "path": "/api/v1/organization/organizations/{organization_id}/sharing",
        "methods": ["POST", "GET"],
        "auth_required": True,
        "description": "Create/list shared resources"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}/sharing/{sharing_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Shared resource CRUD"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}/sharing/{sharing_id}/members",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Update member sharing permission"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}/sharing/{sharing_id}/members/{member_user_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Revoke member access"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}/members/{member_user_id}/shared-resources",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get member shared resources"
    },
    {
        "path": "/api/v1/organization/organizations/{organization_id}/sharing/{sharing_id}/usage",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get sharing usage stats"
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
    organization_routes = []
    member_routes = []
    sharing_routes = []
    admin_routes = []
    for route in ORGANIZATION_SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation: just the unique part after base path
        compact_path = path.replace("/api/v1/organization/organizations/", "").replace("/api/v1/organization/", "").replace("/api/v1/", "")
        if path in ["/health", "/api/v1/organization/info", "/api/v1/organization/stats", "/api/v1/organization/health"]:
            health_routes.append(compact_path)
        elif "admin" in path:
            admin_routes.append(compact_path)
        elif "sharing" in path:
            sharing_routes.append(compact_path)
        elif "members" in path:
            member_routes.append(compact_path)
        else:
            organization_routes.append(compact_path)
    # Create compact route representation for meta
    # Split into multiple fields to avoid 512 char limit
    route_meta = {
        "route_count": str(len(ORGANIZATION_SERVICE_ROUTES)),
        "base_path": "/api/v1/organization",
        # Category summaries (under 512 chars each)
        "health": ",".join(health_routes),
        "organization": ",".join(organization_routes),
        "member": ",".join(member_routes),
        "sharing": ",".join(sharing_routes),
        "admin": ",".join(admin_routes),
        # Methods and auth summary
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in ORGANIZATION_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in ORGANIZATION_SERVICE_ROUTES if r["auth_required"])),
        # Endpoint for full route details
        "routes_endpoint": "/api/v1/organization/info"
    }
    return route_meta
def get_all_routes() -> List[Dict[str, Any]]:
    """
    Get all route definitions
    Returns:
        List of all route definitions
    """
    return ORGANIZATION_SERVICE_ROUTES
def get_routes_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get routes grouped by category
    Returns:
        Dictionary of routes grouped by category
    """
    categories = {
        "health": [],
        "organization_management": [],
        "member_management": [],
        "family_sharing": [],
        "admin": []
    }
    for route in ORGANIZATION_SERVICE_ROUTES:
        path = route["path"]
        if path in ["/health", "/api/v1/organization/info", "/api/v1/organization/stats", "/api/v1/organization/health"]:
            categories["health"].append(route)
        elif "admin" in path:
            categories["admin"].append(route)
        elif "sharing" in path:
            categories["family_sharing"].append(route)
        elif "members" in path:
            categories["member_management"].append(route)
        else:
            categories["organization_management"].append(route)
    return categories
# Service metadata for Consul registration
SERVICE_METADATA = {
    "service_name": "organization_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "organization"],
    "capabilities": [
        "organization_management",
        "member_management",
        "family_sharing",
        "context_switching",
        "usage_tracking"
    ]
}
