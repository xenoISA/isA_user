"""
Notification Service Routes Registry

Defines all API routes for Consul service registration and discovery.
This ensures route metadata is centralized and easy to maintain.
"""

from typing import List, Dict, Any


# Route definitions for notification_service
NOTIFICATION_SERVICE_ROUTES = [
    # Health & Info
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/info", "methods": ["GET"], "auth_required": False, "description": "Service info"},

    # Template Management
    {"path": "/api/v1/notifications/templates", "methods": ["POST"], "auth_required": True, "description": "Create template"},
    {"path": "/api/v1/notifications/templates/{template_id}", "methods": ["GET"], "auth_required": True, "description": "Get template"},
    {"path": "/api/v1/notifications/templates", "methods": ["GET"], "auth_required": True, "description": "List templates"},
    {"path": "/api/v1/notifications/templates/{template_id}", "methods": ["PUT"], "auth_required": True, "description": "Update template"},

    # Notification Operations
    {"path": "/api/v1/notifications/send", "methods": ["POST"], "auth_required": True, "description": "Send notification"},
    {"path": "/api/v1/notifications/batch", "methods": ["POST"], "auth_required": True, "description": "Send batch notifications"},
    {"path": "/api/v1/notifications", "methods": ["GET"], "auth_required": True, "description": "List notifications"},

    # In-App Notifications
    {"path": "/api/v1/notifications/in-app/{user_id}", "methods": ["GET"], "auth_required": True, "description": "Get in-app notifications"},
    {"path": "/api/v1/notifications/in-app/{notification_id}/read", "methods": ["POST"], "auth_required": True, "description": "Mark as read"},
    {"path": "/api/v1/notifications/in-app/{notification_id}/archive", "methods": ["POST"], "auth_required": True, "description": "Archive notification"},
    {"path": "/api/v1/notifications/in-app/{user_id}/unread-count", "methods": ["GET"], "auth_required": True, "description": "Get unread count"},

    # Push Notifications
    {"path": "/api/v1/notifications/push/subscribe", "methods": ["POST"], "auth_required": True, "description": "Subscribe to push"},
    {"path": "/api/v1/notifications/push/subscriptions/{user_id}", "methods": ["GET"], "auth_required": True, "description": "List subscriptions"},
    {"path": "/api/v1/notifications/push/unsubscribe", "methods": ["DELETE"], "auth_required": True, "description": "Unsubscribe"},

    # Statistics
    {"path": "/api/v1/notifications/stats", "methods": ["GET"], "auth_required": True, "description": "Get statistics"},

    # Test Endpoints
    {"path": "/api/v1/notifications/test/email", "methods": ["POST"], "auth_required": False, "description": "Test email"},
    {"path": "/api/v1/notifications/test/in-app", "methods": ["POST"], "auth_required": False, "description": "Test in-app"},
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul registration.
    Note: Consul meta fields have a 512 character limit per field.
    """
    # Categorize routes by functionality
    health_routes = []
    template_routes = []
    notification_routes = []
    inapp_routes = []
    push_routes = []
    stats_routes = []
    test_routes = []

    for route in NOTIFICATION_SERVICE_ROUTES:
        path = route["path"]
        # Create compact representation (remove /api/v1/notifications/ prefix)
        compact_path = path.replace("/api/v1/notifications/", "")

        if path in ["/", "/health", "/info"]:
            health_routes.append(compact_path)
        elif "templates" in path:
            template_routes.append(compact_path)
        elif "in-app" in path:
            inapp_routes.append(compact_path)
        elif "push" in path:
            push_routes.append(compact_path)
        elif "stats" in path:
            stats_routes.append(compact_path)
        elif "test" in path:
            test_routes.append(compact_path)
        else:
            notification_routes.append(compact_path)

    return {
        "route_count": str(len(NOTIFICATION_SERVICE_ROUTES)),
        "base_path": "/api/v1/notifications",
        "health": ",".join(health_routes[:10]),  # Limit to avoid 512 char limit
        "templates": ",".join(template_routes[:10]),
        "notifications": ",".join(notification_routes[:10]),
        "inapp": ",".join(inapp_routes[:10]),
        "push": ",".join(push_routes[:10]),
        "stats": ",".join(stats_routes[:5]),
        "test": ",".join(test_routes[:5]),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in NOTIFICATION_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in NOTIFICATION_SERVICE_ROUTES if r["auth_required"])),
    }


def get_categorized_routes() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get routes organized by category for documentation or other purposes.
    """
    categories = {
        "health": [],
        "templates": [],
        "notifications": [],
        "inapp": [],
        "push": [],
        "stats": [],
        "test": []
    }

    for route in NOTIFICATION_SERVICE_ROUTES:
        path = route["path"]
        if path in ["/", "/health", "/info"]:
            categories["health"].append(route)
        elif "templates" in path:
            categories["templates"].append(route)
        elif "in-app" in path:
            categories["inapp"].append(route)
        elif "push" in path:
            categories["push"].append(route)
        elif "stats" in path:
            categories["stats"].append(route)
        elif "test" in path:
            categories["test"].append(route)
        else:
            categories["notifications"].append(route)

    return categories


# Service metadata
SERVICE_METADATA = {
    "service_name": "notification_service",
    "version": "1.0.0",
    "tags": ["v1", "notification", "messaging", "user-microservice"],
    "capabilities": [
        "email_notifications",
        "sms_notifications",
        "push_notifications",
        "in_app_notifications",
        "template_management",
        "batch_notifications",
        "notification_scheduling"
    ]
}
