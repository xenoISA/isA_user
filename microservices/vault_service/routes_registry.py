"""
Vault Service Routes Registry
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
        "path": "/health/detailed",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Detailed health check"
    },
    {
        "path": "/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service information"
    },
    # Secret Management
    {
        "path": "/api/v1/vault/secrets",
        "methods": ["POST", "GET"],
        "auth_required": True,
        "description": "Create/list secrets"
    },
    {
        "path": "/api/v1/vault/secrets/{vault_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete secret"
    },
    {
        "path": "/api/v1/vault/secrets/{vault_id}/rotate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Rotate secret"
    },
    {
        "path": "/api/v1/vault/secrets/{vault_id}/test",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Test secret connection"
    },
    # Sharing
    {
        "path": "/api/v1/vault/secrets/{vault_id}/share",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Share secret"
    },
    {
        "path": "/api/v1/vault/shared",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List shared secrets"
    },
    # Audit & Stats
    {
        "path": "/api/v1/vault/audit-logs",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get audit logs"
    },
    {
        "path": "/api/v1/vault/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get vault statistics"
    }
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    secret_routes = []
    share_routes = []
    audit_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]
        # 使用紧凑表示：只保留路径的关键部分
        compact_path = path.replace("/api/v1/vault/", "").replace("{", ":").replace("}", "")

        if "/health" in path or "/info" in path:
            health_routes.append(compact_path)
        elif "/shared" in path or "/share" in path:
            share_routes.append(compact_path)
        elif "/audit" in path or "/stats" in path:
            audit_routes.append(compact_path)
        elif "/secrets" in path:
            secret_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/vault",
        "health": ",".join(health_routes),
        "secrets": ",".join(secret_routes[:6]),  # Limit to avoid 512 char limit
        "sharing": ",".join(share_routes),
        "audit": ",".join(audit_routes),
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "vault_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "vault", "security"],
    "capabilities": [
        "secret_management",
        "credential_storage",
        "secret_sharing",
        "audit_logging",
        "encryption"
    ]
}
