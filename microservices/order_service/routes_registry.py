"""
Order Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# 定义所有路由
SERVICE_ROUTES = [
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
        "path": "/health/detailed",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Detailed health check"
    },
    # Order Management
    {
        "path": "/api/v1/orders",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create orders"
    },
    {
        "path": "/api/v1/orders/{order_id}",
        "methods": ["GET", "PUT"],
        "auth_required": True,
        "description": "Get/update order"
    },
    {
        "path": "/api/v1/orders/{order_id}/cancel",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Cancel order"
    },
    {
        "path": "/api/v1/orders/{order_id}/complete",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Complete order"
    },
    # Order Search & Statistics
    {
        "path": "/api/v1/orders/search",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search orders"
    },
    {
        "path": "/api/v1/orders/statistics",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get order statistics"
    },
    # User & Payment Related
    {
        "path": "/api/v1/users/{user_id}/orders",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user orders"
    },
    {
        "path": "/api/v1/payments/{payment_intent_id}/orders",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get orders by payment"
    },
    {
        "path": "/api/v1/subscriptions/{subscription_id}/orders",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get orders by subscription"
    },
    # Order Info
    {
        "path": "/api/v1/order/info",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get order information"
    },
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    order_routes = []
    search_routes = []
    user_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        # 使用紧凑表示：只保留路径的关键部分
        if "health" in path:
            health_routes.append(path.replace("/health", "h"))
        elif "/search" in path or "/statistics" in path:
            search_routes.append("s")
        elif "/users/" in path or "/payments/" in path or "/subscriptions/" in path:
            user_routes.append("u")
        elif "/orders" in path:
            order_routes.append("o")

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/orders",
        "health": ",".join(health_routes) if health_routes else "/,/health",
        "orders": str(len(order_routes)),
        "search": str(len(search_routes)),
        "user_related": str(len(user_routes)),
        "methods": "GET,POST,PUT",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "order_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "order-management", "e-commerce"],
    "capabilities": [
        "order_creation",
        "order_management",
        "order_search",
        "order_statistics",
        "order_cancellation",
        "payment_integration",
        "subscription_orders"
    ]
}
