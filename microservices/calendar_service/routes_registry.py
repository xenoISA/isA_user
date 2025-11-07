"""
Calendar Service Routes Registry
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
    # Calendar Events
    {
        "path": "/api/v1/calendar/events",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create calendar events"
    },
    {
        "path": "/api/v1/calendar/events/{event_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete calendar event"
    },
    # Special Views
    {
        "path": "/api/v1/calendar/upcoming",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get upcoming events"
    },
    {
        "path": "/api/v1/calendar/today",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get today's events"
    },
    # Calendar Sync
    {
        "path": "/api/v1/calendar/sync",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Sync calendar with external source"
    },
    {
        "path": "/api/v1/calendar/sync/status",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get sync status"
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
    view_routes = []
    sync_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        # 使用紧凑表示：只保留路径的关键部分
        if "health" in path:
            health_routes.append("h")
        elif "/sync" in path:
            sync_routes.append("s")
        elif "/upcoming" in path or "/today" in path:
            view_routes.append("v")
        elif "/events" in path:
            event_routes.append("e")

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/calendar",
        "health": str(len(health_routes)),
        "events": str(len(event_routes)),
        "views": str(len(view_routes)),
        "sync": str(len(sync_routes)),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "calendar_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "calendar-management"],
    "capabilities": [
        "event_management",
        "calendar_views",
        "external_sync",
        "upcoming_events",
        "today_events"
    ]
}
