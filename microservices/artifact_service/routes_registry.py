"""
Artifact Service Routes Registry — feeds Consul service metadata so the APISIX
gateway can route ``/api/v1/artifacts/*`` to this service.
"""

SERVICE_METADATA = {
    "service_name": "artifact_service",
    "version": "1.0.0",
    "capabilities": [
        "artifact_library",
        "artifact_versioning",
        "artifact_visibility",
        "artifact_soft_delete",
        "artifact_publish",
        "artifact_remix",
        "artifact_runtime_quota",
        "artifact_mcp_grants",
        "artifact_kv_storage",
    ],
    "tags": [
        "v1",
        "artifact",
        "library",
        "versioning",
        "runtime",
        "mcp",
        "kv",
    ],
}

API_ROUTES = {
    "GET /health": "Service health check",
    "GET /api/v1/artifacts/health": "Service health check (API v1)",
    "POST /api/v1/artifacts": "Create artifact (with first version)",
    "GET /api/v1/artifacts": "List user's artifacts (scope, q, cursor)",
    "GET /api/v1/artifacts/{artifact_id}": "Get artifact with all versions",
    "PATCH /api/v1/artifacts/{artifact_id}": "Update artifact (title, visibility, flags)",
    "DELETE /api/v1/artifacts/{artifact_id}": "Soft delete artifact",
    "POST /api/v1/artifacts/{artifact_id}/versions": "Add a new version",
    # Phase 2
    "POST /api/v1/artifacts/{artifact_id}/publish": "Mint a share token",
    "POST /api/v1/artifacts/{artifact_id}/revoke": "Revoke share token(s)",
    "GET /api/v1/artifacts/{artifact_id}/shares": "List shares for artifact",
    "GET /api/v1/shares/artifacts/{token}": "Public artifact reader",
    "POST /api/v1/artifacts/remix": "Clone a published artifact",
    # Phase 3
    "POST /api/v1/artifacts/{artifact_id}/runtime/invoke": "AI runtime (stubbed) + quota gate",
    "GET /api/v1/artifacts/{artifact_id}/runtime/usage": "Today's runtime usage + cap",
    "POST /api/v1/artifacts/{artifact_id}/mcp/approve": "Persist MCP tool grant",
    "POST /api/v1/artifacts/{artifact_id}/mcp/call": "Approval-gated MCP tool call",
    "GET /api/v1/artifacts/{artifact_id}/mcp/grants": "List MCP grants for user",
    "GET /api/v1/artifacts/{artifact_id}/kv/{key}": "Read artifact KV (scope+user_id)",
    "PUT /api/v1/artifacts/{artifact_id}/kv/{key}": "Upsert artifact KV value",
    "DELETE /api/v1/artifacts/{artifact_id}/kv/{key}": "Delete artifact KV key",
}


def get_routes_for_consul():
    return {
        "route_count": str(len(API_ROUTES)),
        "routes": ",".join(list(API_ROUTES.keys())[:10]),
        "api_version": "v1",
        "base_path": "/api/v1/artifacts",
    }
