"""
Campaign Service Routes Registry

Defines service metadata and routes for Consul registration.
"""

SERVICE_METADATA = {
    "service_name": "campaign_service",
    "version": "1.0.0",
    "tags": ['campaign', 'marketing', 'v1'],
    "capabilities": ['campaign_management'],
}

ROUTES = [
    {"path": "/health", "methods": ["GET"], "description": "Health check"},
    {"path": "/api/v1/campaigns/health", "methods": ["GET"], "description": "Service health check (API v1)"},
]


def get_routes_for_consul():
    """Get route metadata for Consul registration"""
    return {
        "route_count": str(len(ROUTES)),
        "routes": ",".join([r["path"] for r in ROUTES]),
        "api_version": "v1",
        "base_path": "/api/v1/campaigns",
    }


__all__ = ["SERVICE_METADATA", "ROUTES", "get_routes_for_consul"]
