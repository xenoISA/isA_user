"""
Inventory Service Routes Registry

Defines service metadata and routes for Consul registration.
"""

SERVICE_METADATA = {
    "service_name": "inventory_service",
    "version": "1.0.0",
    "tags": ['inventory', 'v1'],
    "capabilities": ['inventory_reservation', 'inventory_commit', 'inventory_release'],
}

ROUTES = [
    {"path": "/health", "methods": ["GET"], "description": "Health check"},
    {"path": "/api/v1/inventory/health", "methods": ["GET"], "description": "Service health check (API v1)"},
]


def get_routes_for_consul():
    """Get route metadata for Consul registration"""
    return {
        "route_count": str(len(ROUTES)),
        "routes": ",".join([r["path"] for r in ROUTES]),
        "api_version": "v1",
        "base_path": "/api/v1/inventory",
    }


__all__ = ["SERVICE_METADATA", "ROUTES", "get_routes_for_consul"]
