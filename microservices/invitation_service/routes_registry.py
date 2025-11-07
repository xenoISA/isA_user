"""
Invitation Service Routes Registry
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
        "path": "/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service information"
    },
    {
        "path": "/api/v1/invitations/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Invitation service info"
    },
    # Invitation Management
    {
        "path": "/api/v1/invitations/organizations/{organization_id}",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create organization invitations"
    },
    {
        "path": "/api/v1/invitations/{invitation_token}",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get invitation details by token"
    },
    {
        "path": "/api/v1/invitations/{invitation_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete invitation"
    },
    {
        "path": "/api/v1/invitations/accept",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Accept invitation"
    },
    {
        "path": "/api/v1/invitations/{invitation_id}/resend",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Resend invitation"
    },
    # Admin Operations
    {
        "path": "/api/v1/admin/expire-invitations",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Expire old invitations (admin)"
    },
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    invitation_routes = []
    admin_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        # 使用紧凑表示：只保留路径的关键部分
        if "health" in path or "/info" in path:
            health_routes.append("h")
        elif "/admin/" in path:
            admin_routes.append("a")
        elif "/invitations" in path:
            invitation_routes.append("i")

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/invitations",
        "health": str(len(health_routes)),
        "invitations": str(len(invitation_routes)),
        "admin": str(len(admin_routes)),
        "methods": "GET,POST,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "invitation_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "invitation-management", "organization"],
    "capabilities": [
        "invitation_creation",
        "invitation_acceptance",
        "invitation_management",
        "organization_invites",
        "email_notifications",
        "invitation_expiration"
    ]
}
