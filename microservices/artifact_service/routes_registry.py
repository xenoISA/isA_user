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
    ],
    "tags": [
        "v1",
        "artifact",
        "library",
        "versioning",
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
}


def get_routes_for_consul():
    return {
        "route_count": str(len(API_ROUTES)),
        "routes": ",".join(list(API_ROUTES.keys())[:10]),
        "api_version": "v1",
        "base_path": "/api/v1/artifacts",
    }
