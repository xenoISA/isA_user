"""
OTA Service Routes Registry
Defines all API routes for Consul service registration
"""
from typing import List, Dict, Any
# 定义所有路由
SERVICE_ROUTES = [
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Basic health check"
    },
        {
            "path": "/api/v1/ota/health",
            "methods": ["GET"],
            "auth_required": False,
            "description": "Service health check (API v1)"
        },
    {
        "path": "/health/detailed",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Detailed health check"
    },
    # Firmware Management
    {
        "path": "/api/v1/firmware",
        "methods": ["POST", "GET"],
        "auth_required": True,
        "description": "Create/list firmware versions"
    },
    {
        "path": "/api/v1/firmware/{firmware_id}",
        "methods": ["GET", "DELETE"],
        "auth_required": True,
        "description": "Get/delete firmware version"
    },
    {
        "path": "/api/v1/firmware/{firmware_id}/download",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Download firmware file"
    },
    # Update Campaigns
    {
        "path": "/api/v1/campaigns",
        "methods": ["POST", "GET"],
        "auth_required": True,
        "description": "Create/list update campaigns"
    },
    {
        "path": "/api/v1/campaigns/{campaign_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get campaign details"
    },
    {
        "path": "/api/v1/campaigns/{campaign_id}/start",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Start campaign"
    },
    {
        "path": "/api/v1/campaigns/{campaign_id}/pause",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Pause campaign"
    },
    {
        "path": "/api/v1/campaigns/{campaign_id}/cancel",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Cancel campaign"
    },
    {
        "path": "/api/v1/campaigns/{campaign_id}/approve",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Approve campaign"
    },
    {
        "path": "/api/v1/campaigns/{campaign_id}/rollback",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Rollback campaign"
    },
    # Device Updates
    {
        "path": "/api/v1/devices/{device_id}/update",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Initiate device update"
    },
    {
        "path": "/api/v1/devices/{device_id}/updates",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get device update history"
    },
    {
        "path": "/api/v1/devices/{device_id}/rollback",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Rollback device update"
    },
    {
        "path": "/api/v1/devices/bulk/update",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Bulk device update"
    },
    # Update Management
    {
        "path": "/api/v1/updates/{update_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get update details"
    },
    {
        "path": "/api/v1/updates/{update_id}/cancel",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Cancel update"
    },
    {
        "path": "/api/v1/updates/{update_id}/retry",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Retry failed update"
    },
    # Statistics
    {
        "path": "/api/v1/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get update statistics"
    },
    {
        "path": "/api/v1/stats/campaigns/{campaign_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get campaign statistics"
    },
    {
        "path": "/api/v1/service/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get service statistics"
    }
]
def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    firmware_routes = []
    campaign_routes = []
    device_routes = []
    update_routes = []
    stats_routes = []
    for route in SERVICE_ROUTES:
        path = route["path"]
        # 使用紧凑表示：只保留路径的关键部分
        compact_path = path.replace("/api/v1/", "").replace("{", ":").replace("}", "")
        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "/firmware" in path:
            firmware_routes.append(compact_path)
        elif "/campaigns" in path:
            campaign_routes.append(compact_path)
        elif "/devices" in path:
            device_routes.append(compact_path)
        elif "/updates" in path:
            update_routes.append(compact_path)
        elif "/stats" in path:
            stats_routes.append(compact_path)
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/ota",
        "health": ",".join(health_routes),
        "firmware": ",".join(firmware_routes[:5]),  # Limit to avoid 512 char limit
        "campaign": ",".join(campaign_routes[:5]),
        "device": ",".join(device_routes[:5]),
        "update": ",".join(update_routes[:3]),
        "stats": ",".join(stats_routes),
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }
# 服务元数据
SERVICE_METADATA = {
    "service_name": "ota_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "ota", "firmware"],
    "capabilities": [
        "firmware_management",
        "update_campaigns",
        "device_updates",
        "rollback_management",
        "update_statistics"
    ]
}
