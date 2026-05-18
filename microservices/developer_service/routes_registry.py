"""Developer Service Routes Registry (#424)."""

from typing import Any, Dict, List

DEVELOPER_SERVICE_ROUTES = [
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Health check",
    },
    {
        "path": "/api/v1/developer/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Developer service dependency health",
    },
    {
        "path": "/api/v1/developer/overview",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Developer Journey overview",
    },
    {
        "path": "/api/v1/developer/first-call",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Developer first-call verification",
    },
]

API_PATH = "/api/v1/developer"

SERVICE_METADATA = {
    "service_name": "developer_service",
    "port": 8261,
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "developer", "journey"],
    "capabilities": ["developer_overview", "setup_progress", "journey_actions"],
    "health_check_path": "/health",
    "health_check_interval": "10s",
}


def get_routes_for_consul() -> Dict[str, Any]:
    return {
        "route_count": str(len(DEVELOPER_SERVICE_ROUTES)),
        "base_path": API_PATH,
        "api_path": API_PATH,
        # APISIX auth_required controls gateway-level jwt-auth. Existing
        # user services keep auth in the app layer and expose health publicly.
        "auth_required": "false",
        "rate_limit": "100",
        "methods": "GET,POST",
        "public_count": str(
            sum(1 for route in DEVELOPER_SERVICE_ROUTES if not route["auth_required"])
        ),
        "protected_count": str(
            sum(1 for route in DEVELOPER_SERVICE_ROUTES if route["auth_required"])
        ),
    }


def get_all_routes() -> List[Dict[str, Any]]:
    return DEVELOPER_SERVICE_ROUTES
