"""
Membership Service Routes Registry

Defines service metadata and routes for Consul registration.
"""

SERVICE_METADATA = {
    "service_name": "membership_service",
    "version": "1.0.0",
    "tags": ["v1", "membership", "loyalty", "microservice"],
    "capabilities": [
        "membership_management",
        "points_management",
        "benefits_management",
        "membership_history",
        "tier_management",
    ],
}

# Route definitions for API documentation and Consul
ROUTES = [
    # Health endpoints
    {"path": "/health", "methods": ["GET"], "description": "Health check"},
    {"path": "/api/v1/memberships/health", "methods": ["GET"], "description": "Service health check (API v1)"},

    # Service info
    {"path": "/api/v1/memberships/info", "methods": ["GET"], "description": "Service information"},

    # Membership CRUD
    {"path": "/api/v1/memberships", "methods": ["POST"], "description": "Create membership"},
    {"path": "/api/v1/memberships", "methods": ["GET"], "description": "List memberships"},
    {"path": "/api/v1/memberships/{membership_id}", "methods": ["GET"], "description": "Get membership"},
    {"path": "/api/v1/memberships/user/{user_id}", "methods": ["GET"], "description": "Get user membership"},
    {"path": "/api/v1/memberships/{membership_id}/cancel", "methods": ["POST"], "description": "Cancel membership"},
    {"path": "/api/v1/memberships/{membership_id}/suspend", "methods": ["PUT"], "description": "Suspend membership"},
    {"path": "/api/v1/memberships/{membership_id}/reactivate", "methods": ["PUT"], "description": "Reactivate membership"},

    # Points
    {"path": "/api/v1/memberships/points/earn", "methods": ["POST"], "description": "Earn points"},
    {"path": "/api/v1/memberships/points/redeem", "methods": ["POST"], "description": "Redeem points"},
    {"path": "/api/v1/memberships/points/balance", "methods": ["GET"], "description": "Points balance"},

    # Benefits & tiers
    {"path": "/api/v1/memberships/{membership_id}/tier", "methods": ["GET"], "description": "Get tier status"},
    {"path": "/api/v1/memberships/{membership_id}/benefits", "methods": ["GET"], "description": "List benefits"},
    {"path": "/api/v1/memberships/{membership_id}/benefits/use", "methods": ["POST"], "description": "Use benefit"},

    # History & stats
    {"path": "/api/v1/memberships/{membership_id}/history", "methods": ["GET"], "description": "Membership history"},
    {"path": "/api/v1/memberships/stats", "methods": ["GET"], "description": "Membership stats"},
]


def get_routes_for_consul():
    """Get route metadata for Consul registration"""
    route_paths = [r["path"] for r in ROUTES]
    return {
        "route_count": str(len(ROUTES)),
        "routes": ",".join(route_paths[:10]),
        "api_version": "v1",
        "base_path": "/api/v1/memberships",
    }


__all__ = ["SERVICE_METADATA", "ROUTES", "get_routes_for_consul"]
