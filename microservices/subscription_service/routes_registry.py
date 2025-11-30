"""
Subscription Service Routes Registry

Defines service metadata and routes for Consul registration.
"""

SERVICE_METADATA = {
    "service_name": "subscription",
    "version": "1.0.0",
    "tags": ["subscription", "credits", "billing", "microservice"],
    "capabilities": [
        "subscription_management",
        "credit_allocation",
        "credit_consumption",
        "subscription_history",
        "tier_management"
    ]
}

# Route definitions for API documentation and Consul
ROUTES = [
    # Health endpoints
    {"path": "/health", "methods": ["GET"], "description": "Health check"},
    {"path": "/health/detailed", "methods": ["GET"], "description": "Detailed health check"},

    # Subscription CRUD
    {"path": "/api/v1/subscriptions", "methods": ["POST"], "description": "Create subscription"},
    {"path": "/api/v1/subscriptions", "methods": ["GET"], "description": "List subscriptions"},
    {"path": "/api/v1/subscriptions/{subscription_id}", "methods": ["GET"], "description": "Get subscription"},
    {"path": "/api/v1/subscriptions/{subscription_id}/cancel", "methods": ["POST"], "description": "Cancel subscription"},
    {"path": "/api/v1/subscriptions/{subscription_id}/history", "methods": ["GET"], "description": "Get subscription history"},

    # User subscription
    {"path": "/api/v1/subscriptions/user/{user_id}", "methods": ["GET"], "description": "Get user subscription"},

    # Credits
    {"path": "/api/v1/subscriptions/credits/balance", "methods": ["GET"], "description": "Get credit balance"},
    {"path": "/api/v1/subscriptions/credits/consume", "methods": ["POST"], "description": "Consume credits"},
]


def get_routes_for_consul():
    """Get route metadata for Consul registration"""
    route_paths = [r["path"] for r in ROUTES]
    return {
        "route_count": str(len(ROUTES)),
        "routes": ",".join(route_paths[:10]),  # First 10 routes
        "api_version": "v1",
        "base_path": "/api/v1/subscriptions",  # Required for APISIX route sync
    }


__all__ = ["SERVICE_METADATA", "ROUTES", "get_routes_for_consul"]
