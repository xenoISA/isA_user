"""
Media Service Routes Registry
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
    # File Upload
    {
        "path": "/api/v1/files/upload",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Upload media file"
    },
    # Photo Versions
    {
        "path": "/api/v1/photos/versions/save",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Save photo version"
    },
    {
        "path": "/api/v1/versions",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create photo version"
    },
    {
        "path": "/api/v1/versions/{version_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get photo version"
    },
    {
        "path": "/api/v1/photos/{photo_id}/versions",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create photo versions"
    },
    {
        "path": "/api/v1/photos/{photo_id}/versions/{version_id}/switch",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Switch active version"
    },
    {
        "path": "/api/v1/photos/versions/{version_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete photo version"
    },
    # Metadata
    {
        "path": "/api/v1/metadata/{file_id}",
        "methods": ["GET", "PUT"],
        "auth_required": True,
        "description": "Get/update photo metadata"
    },
    # Playlists
    {
        "path": "/api/v1/playlists",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create playlists"
    },
    {
        "path": "/api/v1/playlists/{playlist_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete playlist"
    },
    # Rotation Schedules
    {
        "path": "/api/v1/schedules",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create rotation schedule"
    },
    {
        "path": "/api/v1/schedules/{schedule_id}",
        "methods": ["GET", "DELETE"],
        "auth_required": True,
        "description": "Get/delete schedule"
    },
    {
        "path": "/api/v1/schedules/{schedule_id}/status",
        "methods": ["PATCH"],
        "auth_required": True,
        "description": "Update schedule status"
    },
    {
        "path": "/api/v1/frames/{frame_id}/schedules",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get frame schedules"
    },
    # Photo Cache
    {
        "path": "/api/v1/cache",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create cache entry"
    },
    {
        "path": "/api/v1/frames/{frame_id}/cache",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get frame cache"
    },
    {
        "path": "/api/v1/cache/{cache_id}/status",
        "methods": ["PATCH"],
        "auth_required": True,
        "description": "Update cache status"
    },
    # Gallery API
    {
        "path": "/api/v1/gallery/albums",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get gallery albums"
    },
    {
        "path": "/api/v1/gallery/playlists",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create gallery playlists"
    },
    {
        "path": "/api/v1/gallery/playlists/{playlist_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete gallery playlist"
    },
    {
        "path": "/api/v1/gallery/photos/random",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get random photos"
    },
    {
        "path": "/api/v1/gallery/photos/metadata",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Batch get photo metadata"
    },
    {
        "path": "/api/v1/gallery/cache/preload",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Preload cache"
    },
    {
        "path": "/api/v1/gallery/cache/{frame_id}/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get cache stats"
    },
    {
        "path": "/api/v1/gallery/cache/{frame_id}/clear",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Clear cache"
    },
    {
        "path": "/api/v1/gallery/schedules",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create gallery schedule"
    },
    {
        "path": "/api/v1/gallery/schedules/{frame_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get gallery schedules"
    },
    {
        "path": "/api/v1/gallery/frames/{frame_id}/playlists",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get frame playlists"
    },
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    version_routes = []
    playlist_routes = []
    schedule_routes = []
    cache_routes = []
    gallery_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        # 使用紧凑表示：只保留路径的关键部分
        if path in ["/", "/health"]:
            health_routes.append(path)
        elif "/versions" in path or "/photos/" in path:
            version_routes.append("v")
        elif "/playlists" in path and "/gallery/" not in path:
            playlist_routes.append("p")
        elif "/schedules" in path and "/gallery/" not in path:
            schedule_routes.append("s")
        elif "/cache" in path and "/gallery/" not in path:
            cache_routes.append("c")
        elif "/gallery/" in path:
            gallery_routes.append("g")

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1",
        "health": ",".join(health_routes),
        "versions": str(len(version_routes)),
        "playlists": str(len(playlist_routes)),
        "schedules": str(len(schedule_routes)),
        "cache": str(len(cache_routes)),
        "gallery": str(len(gallery_routes)),
        "methods": "GET,POST,PUT,DELETE,PATCH",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "media_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "media-management", "photo-frame"],
    "capabilities": [
        "file_upload",
        "photo_versions",
        "metadata_management",
        "playlist_management",
        "rotation_schedules",
        "photo_cache",
        "gallery_api"
    ]
}
