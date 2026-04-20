"""
Sharing Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import Any, Dict

SERVICE_ROUTES = [
    # Health Check
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Basic health check",
    },
    {
        "path": "/api/v1/sharing/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check (API v1)",
    },
    # Share Management
    {
        "path": "/api/v1/sessions/{session_id}/shares",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create share link for a session",
    },
    {
        "path": "/api/v1/sessions/{session_id}/shares",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List shares for a session",
    },
    # Public share access (token IS the auth)
    {
        "path": "/api/v1/shares/{token}",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Access shared session via token",
    },
    # Share revocation
    {
        "path": "/api/v1/shares/{token}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Revoke a share link",
    },
]


def get_routes_for_consul() -> Dict[str, Any]:
    """Generate compact route metadata for Consul"""
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1",
        "methods": "GET,POST,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


SERVICE_METADATA = {
    "service_name": "sharing_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "sharing", "collaboration"],
    "capabilities": [
        "share_link_generation",
        "token_based_access",
        "share_revocation",
        "access_tracking",
        "event_driven",
    ],
}
