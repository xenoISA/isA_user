"""
Album Service Routes Registry
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
            "path": "/api/v1/albums/health",
            "methods": ["GET"],
            "auth_required": False,
            "description": "Service health check (API v1)"
        },
    # Album Management
    {
        "path": "/api/v1/albums",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create albums"
    },
    {
        "path": "/api/v1/albums/{album_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete album"
    },
    # Album Photos
    {
        "path": "/api/v1/albums/{album_id}/photos",
        "methods": ["GET", "POST", "DELETE"],
        "auth_required": True,
        "description": "Manage album photos"
    },
    # Album Sync
    {
        "path": "/api/v1/albums/{album_id}/sync",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Sync album to frame"
    },
    {
        "path": "/api/v1/albums/{album_id}/sync/{frame_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get album sync status"
    },
]
def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    album_routes = []
    photo_routes = []
    sync_routes = []
    for route in SERVICE_ROUTES:
        path = route["path"]
        # 使用紧凑表示：只保留路径的关键部分
        if "health" in path or path == "/":
            health_routes.append("h")
        elif "/photos" in path:
            photo_routes.append("p")
        elif "/sync" in path:
            sync_routes.append("s")
        elif "/albums" in path:
            album_routes.append("a")
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/albums",
        "health": str(len(health_routes)),
        "albums": str(len(album_routes)),
        "photos": str(len(photo_routes)),
        "sync": str(len(sync_routes)),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }
# 服务元数据
SERVICE_METADATA = {
    "service_name": "album_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "album-management", "photo-organization"],
    "capabilities": [
        "album_management",
        "photo_organization",
        "album_sync",
        "frame_integration",
        "photo_sharing"
    ]
}
