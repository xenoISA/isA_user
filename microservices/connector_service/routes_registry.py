"""
Connector Service Routes Registry — Consul metadata for service discovery.

Same shape as project_sharing_service.routes_registry.
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
        "path": "/api/v1/connectors/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check (API v1)",
    },
    # Catalog (auth required at the gateway; no per-user mutation)
    {
        "path": "/api/v1/connectors/catalog",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List built-in connector catalog",
    },
    # Per-user install state
    {
        "path": "/api/v1/connectors/installed",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List the authenticated user's installed connectors + custom MCP rows",
    },
    # Custom MCP CRUD
    {
        "path": "/api/v1/connectors/custom",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Register a new custom remote MCP connector (rate-limited 10/hour)",
    },
    {
        "path": "/api/v1/connectors/custom/{connector_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Revoke + delete a custom MCP connector",
    },
    {
        "path": "/api/v1/connectors/custom/{connector_id}/revalidate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Re-run the MCP handshake against a stored custom connector",
    },
]


def get_routes_for_consul() -> Dict[str, Any]:
    """Compact route metadata for Consul registration."""
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1",
        "methods": "GET,POST,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


SERVICE_METADATA = {
    "service_name": "connector_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "connector", "marketplace", "mcp"],
    "capabilities": [
        "connector_catalog_read",
        "connector_install_state_read",
        "custom_mcp_register",
        "custom_mcp_revoke",
        "custom_mcp_revalidate",
        "event_driven",
    ],
}
