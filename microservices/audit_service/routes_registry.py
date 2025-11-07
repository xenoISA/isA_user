"""
Audit Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# Define all routes
SERVICE_ROUTES = [
    # Health checks
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Basic health check"},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False, "description": "Detailed health check"},

    # Service info
    {"path": "/api/v1/audit/info", "methods": ["GET"], "auth_required": False, "description": "Service information"},
    {"path": "/api/v1/audit/stats", "methods": ["GET"], "auth_required": True, "description": "Service statistics"},

    # Audit event management
    {"path": "/api/v1/audit/events", "methods": ["GET", "POST"], "auth_required": True, "description": "List/create audit events"},
    {"path": "/api/v1/audit/events/query", "methods": ["POST"], "auth_required": True, "description": "Query audit events"},
    {"path": "/api/v1/audit/events/batch", "methods": ["POST"], "auth_required": True, "description": "Batch log events"},

    # User activity tracking
    {"path": "/api/v1/audit/users/{user_id}/activities", "methods": ["GET"], "auth_required": True, "description": "Get user activities"},
    {"path": "/api/v1/audit/users/{user_id}/summary", "methods": ["GET"], "auth_required": True, "description": "User activity summary"},

    # Security event management
    {"path": "/api/v1/audit/security/alerts", "methods": ["POST"], "auth_required": True, "description": "Create security alert"},
    {"path": "/api/v1/audit/security/events", "methods": ["GET"], "auth_required": True, "description": "Get security events"},

    # Compliance reporting
    {"path": "/api/v1/audit/compliance/reports", "methods": ["POST"], "auth_required": True, "description": "Generate compliance report"},
    {"path": "/api/v1/audit/compliance/standards", "methods": ["GET"], "auth_required": False, "description": "Get compliance standards"},

    # System maintenance
    {"path": "/api/v1/audit/maintenance/cleanup", "methods": ["POST"], "auth_required": True, "description": "Cleanup old data"},
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have 512 character limit
    """
    # Categorize routes
    health_routes = []
    event_routes = []
    user_routes = []
    security_routes = []
    compliance_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        if "/health" in path:
            health_routes.append("health" if path == "/health" else "detailed")
        elif "/events" in path:
            event_routes.append(path.split("/")[-1])
        elif "/users/" in path:
            user_routes.append(path.split("/")[-1])
        elif "/security/" in path:
            security_routes.append(path.split("/")[-1])
        elif "/compliance/" in path:
            compliance_routes.append(path.split("/")[-1])

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/audit",
        "health": ",".join(set(health_routes)),
        "events": ",".join(list(set(event_routes))[:5]),
        "user_activity": ",".join(set(user_routes)),
        "security": ",".join(set(security_routes)),
        "compliance": ",".join(set(compliance_routes)),
        "methods": "GET,POST",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# Service metadata
SERVICE_METADATA = {
    "service_name": "audit_service",
    "version": "1.0.0",
    "tags": ["v1", "governance-microservice", "audit", "compliance"],
    "capabilities": [
        "event_logging",
        "event_querying",
        "user_activity_tracking",
        "security_alerting",
        "compliance_reporting",
        "real_time_analysis",
        "data_retention"
    ]
}
