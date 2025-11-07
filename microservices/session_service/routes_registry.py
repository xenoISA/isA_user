"""
Session Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# Define all routes
SERVICE_ROUTES = [
    # Health Check
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

    # Session Management
    {
        "path": "/api/v1/sessions",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create new session"
    },
    {
        "path": "/api/v1/sessions/{session_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get session details"
    },
    {
        "path": "/api/v1/sessions/{session_id}",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Update session"
    },
    {
        "path": "/api/v1/sessions/{session_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete session"
    },
    {
        "path": "/api/v1/users/{user_id}/sessions",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List user sessions"
    },

    # Session Messages
    {
        "path": "/api/v1/sessions/{session_id}/messages",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Add message to session"
    },
    {
        "path": "/api/v1/sessions/{session_id}/messages",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get session messages"
    },

    # Session Analytics
    {
        "path": "/api/v1/sessions/{session_id}/summary",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get session summary"
    },
    {
        "path": "/api/v1/sessions/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get session statistics"
    }
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have a 512 character limit
    """
    # Categorize routes
    health_routes = []
    session_routes = []
    message_routes = []
    stats_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation
        compact_path = path.replace("/api/v1/sessions/", "").replace("/api/v1/", "")

        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "/messages" in path:
            message_routes.append(compact_path)
        elif "/stats" in path or "/summary" in path:
            stats_routes.append(compact_path)
        elif path.startswith("/api/v1/sessions") or "/sessions" in path:
            session_routes.append(compact_path)

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/sessions",
        "health": ",".join(health_routes),
        "session": ",".join(session_routes[:5]),  # Limit to avoid 512 char limit
        "message": ",".join(message_routes),
        "stats": ",".join(stats_routes),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }


# Service metadata
SERVICE_METADATA = {
    "service_name": "session_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "session", "conversation"],
    "capabilities": [
        "session_management",
        "message_management",
        "session_analytics",
        "conversation_tracking",
        "session_persistence",
        "event_driven"
    ]
}
