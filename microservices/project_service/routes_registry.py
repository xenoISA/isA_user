"""Project Service Routes Registry (#258, #299)"""
from typing import List, Dict, Any

PROJECT_SERVICE_ROUTES = [
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/api/v1/projects/health", "methods": ["GET"], "auth_required": False, "description": "Health check (prefixed)"},
    {"path": "/api/v1/projects", "methods": ["POST"], "auth_required": True, "description": "Create project"},
    {"path": "/api/v1/projects", "methods": ["GET"], "auth_required": True, "description": "List projects"},
    {"path": "/api/v1/projects/{project_id}", "methods": ["GET"], "auth_required": True, "description": "Get project"},
    {"path": "/api/v1/projects/{project_id}", "methods": ["PUT"], "auth_required": True, "description": "Update project"},
    {"path": "/api/v1/projects/{project_id}", "methods": ["DELETE"], "auth_required": True, "description": "Delete project"},
    {"path": "/api/v1/projects/{project_id}/instructions", "methods": ["PUT"], "auth_required": True, "description": "Set instructions"},
    {"path": "/api/v1/projects/{project_id}/files", "methods": ["GET"], "auth_required": True, "description": "List project knowledge files"},
    {"path": "/api/v1/projects/{project_id}/files", "methods": ["POST"], "auth_required": True, "description": "Upload project knowledge file"},
    {"path": "/api/v1/projects/{project_id}/files/{file_id}", "methods": ["DELETE"], "auth_required": True, "description": "Delete project knowledge file"},
]

SERVICE_METADATA = {
    "service_name": "project_service",
    "port": 8260,
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "projects"],
    "capabilities": ["project_crud", "knowledge_base", "custom_instructions"],
    "health_check_path": "/health",
    "health_check_interval": "10s",
}


def get_routes_for_consul() -> Dict[str, Any]:
    return {
        "route_count": str(len(PROJECT_SERVICE_ROUTES)),
        "base_path": "/api/v1/projects",
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in PROJECT_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in PROJECT_SERVICE_ROUTES if r["auth_required"])),
    }


def get_all_routes() -> List[Dict[str, Any]]:
    return PROJECT_SERVICE_ROUTES
