"""
Product Service Routes Registry

Defines all API routes for Consul service registration and discovery.
This ensures route metadata is centralized and easy to maintain.
"""

from typing import List, Dict, Any


# Route definitions for product_service
PRODUCT_SERVICE_ROUTES = [
    # Health & Info
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/api/v1/product/info", "methods": ["GET"], "auth_required": False, "description": "Service info"},

    # Product Catalog
    {"path": "/api/v1/product/categories", "methods": ["GET"], "auth_required": False, "description": "List product categories"},
    {"path": "/api/v1/product/products", "methods": ["GET"], "auth_required": False, "description": "List products"},
    {"path": "/api/v1/product/products/{product_id}", "methods": ["GET"], "auth_required": False, "description": "Get product details"},
    {"path": "/api/v1/product/products/{product_id}/pricing", "methods": ["GET"], "auth_required": False, "description": "Get product pricing"},
    {"path": "/api/v1/product/products/{product_id}/availability", "methods": ["GET"], "auth_required": False, "description": "Check product availability"},

    # Subscriptions
    {"path": "/api/v1/product/subscriptions/user/{user_id}", "methods": ["GET"], "auth_required": True, "description": "Get user subscriptions"},
    {"path": "/api/v1/product/subscriptions/{subscription_id}", "methods": ["GET"], "auth_required": True, "description": "Get subscription details"},
    {"path": "/api/v1/product/subscriptions", "methods": ["POST"], "auth_required": True, "description": "Create subscription"},

    # Usage Tracking
    {"path": "/api/v1/product/usage/record", "methods": ["POST"], "auth_required": True, "description": "Record usage"},
    {"path": "/api/v1/product/usage/records", "methods": ["GET"], "auth_required": True, "description": "Get usage records"},

    # Statistics
    {"path": "/api/v1/product/statistics/usage", "methods": ["GET"], "auth_required": True, "description": "Get usage statistics"},
    {"path": "/api/v1/product/statistics/service", "methods": ["GET"], "auth_required": True, "description": "Get service statistics"},
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul registration.
    Note: Consul meta fields have a 512 character limit per field.
    """
    # Categorize routes by functionality
    health_routes = []
    catalog_routes = []
    subscription_routes = []
    usage_routes = []
    stats_routes = []

    for route in PRODUCT_SERVICE_ROUTES:
        path = route["path"]
        # Create compact representation (remove /api/v1/product/ prefix)
        compact_path = path.replace("/api/v1/product/", "")

        if path in ["/health", "/api/v1/product/info"]:
            health_routes.append(compact_path)
        elif "subscriptions" in path:
            subscription_routes.append(compact_path)
        elif "usage" in path:
            usage_routes.append(compact_path)
        elif "statistics" in path:
            stats_routes.append(compact_path)
        else:
            catalog_routes.append(compact_path)

    return {
        "route_count": str(len(PRODUCT_SERVICE_ROUTES)),
        "base_path": "/api/v1/product",
        "health": ",".join(health_routes[:10]),
        "catalog": ",".join(catalog_routes[:10]),
        "subscriptions": ",".join(subscription_routes[:10]),
        "usage": ",".join(usage_routes[:10]),
        "stats": ",".join(stats_routes[:5]),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in PRODUCT_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in PRODUCT_SERVICE_ROUTES if r["auth_required"])),
    }


def get_categorized_routes() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get routes organized by category for documentation or other purposes.
    """
    categories = {
        "health": [],
        "catalog": [],
        "subscriptions": [],
        "usage": [],
        "statistics": []
    }

    for route in PRODUCT_SERVICE_ROUTES:
        path = route["path"]
        if path in ["/health", "/api/v1/product/info"]:
            categories["health"].append(route)
        elif "subscriptions" in path:
            categories["subscriptions"].append(route)
        elif "usage" in path:
            categories["usage"].append(route)
        elif "statistics" in path:
            categories["statistics"].append(route)
        else:
            categories["catalog"].append(route)

    return categories


# Service metadata
SERVICE_METADATA = {
    "service_name": "product_service",
    "version": "1.0.0",
    "tags": ["v1", "product", "catalog", "subscription", "user-microservice"],
    "capabilities": [
        "product_catalog",
        "pricing_management",
        "subscription_management",
        "usage_tracking",
        "quota_management",
        "service_plans"
    ]
}
