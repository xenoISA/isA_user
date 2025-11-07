"""
Event Service Routes Registry
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
    # Event Management
    {
        "path": "/api/v1/events/create",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create single event"
    },
    {
        "path": "/api/v1/events/batch",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create batch events"
    },
    {
        "path": "/api/v1/events/{event_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get single event by ID"
    },
    {
        "path": "/api/v1/events/query",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Query events with filters"
    },
    {
        "path": "/api/v1/events/statistics",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get event statistics"
    },
    # Event Stream
    {
        "path": "/api/v1/events/stream/{stream_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get event stream"
    },
    {
        "path": "/api/v1/events/replay",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Replay events"
    },
    # Event Projections
    {
        "path": "/api/v1/events/projections/{entity_type}/{entity_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get entity projection"
    },
    # Event Subscriptions
    {
        "path": "/api/v1/events/subscriptions",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create event subscriptions"
    },
    {
        "path": "/api/v1/events/subscriptions/{subscription_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete event subscription"
    },
    # Event Processors
    {
        "path": "/api/v1/events/processors",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/register event processors"
    },
    {
        "path": "/api/v1/events/processors/{processor_id}/toggle",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Toggle event processor"
    },
    # Frontend Event Collection
    {
        "path": "/api/v1/frontend/events",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Collect single frontend event"
    },
    {
        "path": "/api/v1/frontend/events/batch",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Collect batch frontend events"
    },
    {
        "path": "/api/v1/frontend/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Frontend collection health check"
    },
    # Webhooks
    {
        "path": "/webhooks/rudderstack",
        "methods": ["POST"],
        "auth_required": False,
        "description": "RudderStack webhook endpoint"
    },
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    event_routes = []
    frontend_routes = []
    webhook_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        # 使用紧凑表示：只保留路径的关键部分
        if path in ["/", "/health"]:
            health_routes.append(path)
        elif path.startswith("/api/v1/frontend/"):
            compact_path = path.replace("/api/v1/frontend/", "")
            frontend_routes.append(compact_path)
        elif path.startswith("/webhooks/"):
            compact_path = path.replace("/webhooks/", "")
            webhook_routes.append(compact_path)
        elif path.startswith("/api/v1/events/"):
            compact_path = path.replace("/api/v1/events/", "")
            event_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/events",
        "health": ",".join(health_routes),
        "events": "|".join(event_routes[:15]),  # 限制长度
        "frontend": ",".join(frontend_routes),
        "webhooks": ",".join(webhook_routes),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "event_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "event-management", "event-sourcing"],
    "capabilities": [
        "event_creation",
        "event_query",
        "event_streaming",
        "event_replay",
        "event_subscriptions",
        "event_processors",
        "frontend_collection",
        "rudderstack_integration"
    ]
}
