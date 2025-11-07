"""
Compliance Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# Define all routes
SERVICE_ROUTES = [
    # Health checks
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/status", "methods": ["GET"], "auth_required": False, "description": "Service status"},

    # Compliance checks
    {"path": "/api/v1/compliance/check", "methods": ["POST"], "auth_required": True, "description": "Perform compliance check"},
    {"path": "/api/v1/compliance/check/batch", "methods": ["POST"], "auth_required": True, "description": "Batch compliance check"},

    # Query and reporting
    {"path": "/api/v1/compliance/checks/{check_id}", "methods": ["GET"], "auth_required": True, "description": "Get check by ID"},
    {"path": "/api/v1/compliance/checks/user/{user_id}", "methods": ["GET"], "auth_required": True, "description": "Get user checks"},
    {"path": "/api/v1/compliance/reviews/pending", "methods": ["GET"], "auth_required": True, "description": "Get pending reviews"},
    {"path": "/api/v1/compliance/reviews/{check_id}", "methods": ["PUT"], "auth_required": True, "description": "Update review"},
    {"path": "/api/v1/compliance/reports", "methods": ["POST"], "auth_required": True, "description": "Generate report"},

    # Policy management
    {"path": "/api/v1/compliance/policies", "methods": ["GET", "POST"], "auth_required": True, "description": "List/create policies"},
    {"path": "/api/v1/compliance/policies/{policy_id}", "methods": ["GET"], "auth_required": True, "description": "Get policy"},

    # Statistics
    {"path": "/api/v1/compliance/stats", "methods": ["GET"], "auth_required": True, "description": "Get statistics"},

    # GDPR compliance
    {"path": "/api/v1/compliance/user/{user_id}/data-export", "methods": ["GET"], "auth_required": True, "description": "Export user data (GDPR)"},
    {"path": "/api/v1/compliance/user/{user_id}/data", "methods": ["DELETE"], "auth_required": True, "description": "Delete user data (GDPR)"},
    {"path": "/api/v1/compliance/user/{user_id}/data-summary", "methods": ["GET"], "auth_required": True, "description": "User data summary (GDPR)"},
    {"path": "/api/v1/compliance/user/{user_id}/consent", "methods": ["POST"], "auth_required": True, "description": "Update consent (GDPR)"},
    {"path": "/api/v1/compliance/user/{user_id}/audit-log", "methods": ["GET"], "auth_required": True, "description": "Get audit log (GDPR)"},

    # PCI-DSS compliance
    {"path": "/api/v1/compliance/pci/card-data-check", "methods": ["POST"], "auth_required": True, "description": "Check card data (PCI-DSS)"},
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have 512 character limit
    """
    # Categorize routes
    health_routes = []
    check_routes = []
    policy_routes = []
    gdpr_routes = []
    pci_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        if "/health" in path or "/status" in path:
            health_routes.append(path.split("/")[-1])
        elif "/check" in path:
            check_routes.append(path.split("/")[-1])
        elif "/policies" in path:
            policy_routes.append(path.split("/")[-1] if "{" not in path.split("/")[-1] else "*")
        elif "/user/" in path and "/pci/" not in path:
            gdpr_routes.append(path.split("/")[-1])
        elif "/pci/" in path:
            pci_routes.append(path.split("/")[-1])

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/compliance",
        "health": ",".join(set(health_routes)),
        "checks": ",".join(list(set(check_routes))[:5]),
        "policies": ",".join(set(policy_routes)),
        "gdpr": ",".join(list(set(gdpr_routes))[:5]),
        "pci": ",".join(set(pci_routes)),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# Service metadata
SERVICE_METADATA = {
    "service_name": "compliance_service",
    "version": "1.0.0",
    "tags": ["v1", "governance-microservice", "compliance", "ai-safety"],
    "capabilities": [
        "content_moderation",
        "pii_detection",
        "prompt_injection_detection",
        "gdpr_compliance",
        "pci_dss_compliance",
        "policy_enforcement",
        "compliance_reporting",
        "user_data_control"
    ]
}
