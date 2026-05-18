"""
Project Sharing Service Routes Registry

Defines all API routes for Consul service registration.
"""

from typing import Any, Dict

SERVICE_ROUTES = [
    # Health
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Basic health check",
    },
    {
        "path": "/api/v1/project-sharing/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check (API v1)",
    },
    # Invite / list
    {
        "path": "/api/v1/projects/{project_id}/shares",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Invite a user to a project",
    },
    {
        "path": "/api/v1/projects/{project_id}/shares",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List project shares (optionally filter by status)",
    },
    # Update / revoke
    {
        "path": "/api/v1/projects/{project_id}/shares/{share_id}",
        "methods": ["PATCH"],
        "auth_required": True,
        "description": "Update role on a project share",
    },
    {
        "path": "/api/v1/projects/{project_id}/shares/{share_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Revoke a project share (nulls invite_token)",
    },
    # Accept (public — token IS the auth)
    {
        "path": "/api/v1/shares/accept/{token}",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Accept a project share invite via token",
    },
]


def get_routes_for_consul() -> Dict[str, Any]:
    """Generate compact route metadata for Consul."""
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1",
        "methods": "GET,POST,PATCH,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


SERVICE_METADATA = {
    "service_name": "project_sharing_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "project-sharing", "collaboration"],
    "capabilities": [
        "project_invite",
        "project_share_accept",
        "project_share_revoke",
        "project_share_role_update",
        "event_driven",
    ],
}
