"""
Task Service Routes Registry

Defines all API routes for Consul service registration and discovery.
This ensures route metadata is centralized and easy to maintain.
"""

from typing import List, Dict, Any


# Route definitions for task_service
TASK_SERVICE_ROUTES = [
    # Health & Info
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False, "description": "Detailed health check"},

    # Task CRUD
    {"path": "/api/v1/tasks", "methods": ["POST"], "auth_required": True, "description": "Create task"},
    {"path": "/api/v1/tasks/{task_id}", "methods": ["GET"], "auth_required": True, "description": "Get task"},
    {"path": "/api/v1/tasks/{task_id}", "methods": ["PUT"], "auth_required": True, "description": "Update task"},
    {"path": "/api/v1/tasks/{task_id}", "methods": ["DELETE"], "auth_required": True, "description": "Delete task"},
    {"path": "/api/v1/tasks", "methods": ["GET"], "auth_required": True, "description": "List tasks"},

    # Task Execution
    {"path": "/api/v1/tasks/{task_id}/execute", "methods": ["POST"], "auth_required": True, "description": "Execute task"},
    {"path": "/api/v1/tasks/{task_id}/executions", "methods": ["GET"], "auth_required": True, "description": "Get task executions"},

    # Templates
    {"path": "/api/v1/templates", "methods": ["GET"], "auth_required": True, "description": "List task templates"},
    {"path": "/api/v1/tasks/from-template", "methods": ["POST"], "auth_required": True, "description": "Create task from template"},

    # Analytics
    {"path": "/api/v1/analytics", "methods": ["GET"], "auth_required": True, "description": "Get task analytics"},

    # Scheduler
    {"path": "/api/v1/scheduler/pending", "methods": ["GET"], "auth_required": True, "description": "Get pending tasks"},
    {"path": "/api/v1/scheduler/execute/{task_id}", "methods": ["POST"], "auth_required": True, "description": "Execute scheduled task"},

    # Service Statistics
    {"path": "/api/v1/service/stats", "methods": ["GET"], "auth_required": True, "description": "Get service statistics"},
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul registration.
    Note: Consul meta fields have a 512 character limit per field.
    """
    # Categorize routes by functionality
    health_routes = []
    task_routes = []
    execution_routes = []
    template_routes = []
    analytics_routes = []
    scheduler_routes = []
    stats_routes = []

    for route in TASK_SERVICE_ROUTES:
        path = route["path"]
        # Create compact representation (remove /api/v1/ prefix)
        compact_path = path.replace("/api/v1/", "")

        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "execute" in path or "executions" in path:
            execution_routes.append(compact_path)
        elif "template" in path:
            template_routes.append(compact_path)
        elif "analytics" in path:
            analytics_routes.append(compact_path)
        elif "scheduler" in path:
            scheduler_routes.append(compact_path)
        elif "stats" in path:
            stats_routes.append(compact_path)
        elif "tasks" in path:
            task_routes.append(compact_path)

    return {
        "route_count": str(len(TASK_SERVICE_ROUTES)),
        "base_path": "/api/v1",
        "health": ",".join(health_routes[:10]),
        "tasks": ",".join(task_routes[:10]),
        "execution": ",".join(execution_routes[:10]),
        "templates": ",".join(template_routes[:10]),
        "analytics": ",".join(analytics_routes[:5]),
        "scheduler": ",".join(scheduler_routes[:5]),
        "stats": ",".join(stats_routes[:5]),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in TASK_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in TASK_SERVICE_ROUTES if r["auth_required"])),
    }


def get_categorized_routes() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get routes organized by category for documentation or other purposes.
    """
    categories = {
        "health": [],
        "tasks": [],
        "execution": [],
        "templates": [],
        "analytics": [],
        "scheduler": [],
        "statistics": []
    }

    for route in TASK_SERVICE_ROUTES:
        path = route["path"]
        if path.startswith("/health"):
            categories["health"].append(route)
        elif "execute" in path or "executions" in path:
            categories["execution"].append(route)
        elif "template" in path:
            categories["templates"].append(route)
        elif "analytics" in path:
            categories["analytics"].append(route)
        elif "scheduler" in path:
            categories["scheduler"].append(route)
        elif "stats" in path:
            categories["statistics"].append(route)
        elif "tasks" in path:
            categories["tasks"].append(route)

    return categories


# Service metadata
SERVICE_METADATA = {
    "service_name": "task_service",
    "version": "1.0.0",
    "tags": ["v1", "task", "todo", "scheduler", "user-microservice"],
    "capabilities": [
        "task_management",
        "task_execution",
        "task_templates",
        "task_scheduling",
        "task_analytics",
        "todo_lists"
    ]
}
