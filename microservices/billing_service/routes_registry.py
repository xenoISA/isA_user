"""
Billing Service Routes Registry
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
        "description": "Health check endpoint"
    },
    {
        "path": "/api/v1/billing/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service information and capabilities"
    },

    # Core Billing APIs
    {
        "path": "/api/v1/billing/usage/record",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Record usage and bill immediately"
    },
    {
        "path": "/api/v1/billing/calculate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Calculate billing cost"
    },
    {
        "path": "/api/v1/billing/process",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Process billing (actual charge)"
    },

    # Quota Management
    {
        "path": "/api/v1/billing/quota/check",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Check quota limits"
    },

    # Query and Statistics
    {
        "path": "/api/v1/billing/records/user/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user billing records"
    },
    {
        "path": "/api/v1/billing/record/{billing_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get single billing record"
    },
    {
        "path": "/api/v1/billing/usage/aggregations",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get usage aggregations"
    },
    {
        "path": "/api/v1/billing/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get billing statistics"
    },

    # Management
    {
        "path": "/api/v1/billing/record/{billing_id}/status",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Update billing record status (admin)"
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
    query_routes = []
    quota_routes = []
    admin_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation
        compact_path = path.replace("/api/v1/billing/", "")

        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "quota" in path:
            quota_routes.append(compact_path)
        elif path.endswith("/status") or "admin" in path:
            admin_routes.append(compact_path)
        elif "/records/" in path or "/stats" in path or "aggregations" in path:
            query_routes.append(compact_path)
        elif path.startswith("/api/v1/billing"):
            core_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/billing",
        "health": ",".join(health_routes),
        "core": ",".join(core_routes),
        "query": ",".join(query_routes),
        "quota": ",".join(quota_routes),
        "admin": ",".join(admin_routes),
        "methods": "GET,POST,PUT",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


# Service metadata
SERVICE_METADATA = {
    "service_name": "billing_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "billing", "usage-tracking"],
    "capabilities": [
        "usage_tracking",
        "cost_calculation",
        "billing_processing",
        "quota_management",
        "billing_analytics",
        "wallet_deduction",
        "payment_charge",
        "event_driven_billing"
    ]
}
