"""
Credit Service Routes Registry
Defines all API routes for Consul service registration.
Pattern: CDD System Contract - Service Registration Pattern
"""
from typing import List, Dict, Any
# Define all routes based on system_contract.md
SERVICE_ROUTES = [
    # Health and Service Info
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Basic health check endpoint"
    },
        {
            "path": "/api/v1/credits/health",
            "methods": ["GET"],
            "auth_required": False,
            "description": "Service health check (API v1)"
        },
    {
        "path": "/health/detailed",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Detailed health check with dependencies"
    },
    # Credit Account Management
    {
        "path": "/api/v1/credits/accounts",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List user accounts (GET) or create new account (POST)"
    },
    {
        "path": "/api/v1/credits/accounts/{account_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get account by ID"
    },
    # Balance Operations
    {
        "path": "/api/v1/credits/balance",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get aggregated credit balance summary"
    },
    {
        "path": "/api/v1/credits/check-availability",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Check credit availability for consumption"
    },
    # Credit Operations
    {
        "path": "/api/v1/credits/allocate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Allocate credits to user"
    },
    {
        "path": "/api/v1/credits/consume",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Consume credits with FIFO expiration"
    },
    {
        "path": "/api/v1/credits/transfer",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Transfer credits between users"
    },
    # Transaction History
    {
        "path": "/api/v1/credits/transactions",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get credit transaction history"
    },
    # Campaign Management
    {
        "path": "/api/v1/credits/campaigns",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List campaigns (GET) or create campaign (POST)"
    },
    {
        "path": "/api/v1/credits/campaigns/{campaign_id}",
        "methods": ["GET", "PUT"],
        "auth_required": True,
        "description": "Get campaign (GET) or update campaign (PUT)"
    },
    # Statistics and Analytics
    {
        "path": "/api/v1/credits/statistics",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get credit statistics and analytics"
    },
]
def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul registration.
    Note: Consul meta fields have a 512 character limit, so we compact paths
    and categorize routes for efficient storage.
    Returns:
        Dict with compact route metadata for Consul service meta
    """
    # Categorize routes
    health_routes = []
    account_routes = []
    balance_routes = []
    operation_routes = []
    campaign_routes = []
    stats_routes = []
    for route in SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation
        compact_path = path.replace("/api/v1/credits/", "")
        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "accounts" in path:
            account_routes.append(compact_path)
        elif "balance" in path or "check-availability" in path:
            balance_routes.append(compact_path)
        elif "campaigns" in path:
            campaign_routes.append(compact_path)
        elif "statistics" in path:
            stats_routes.append(compact_path)
        elif path.startswith("/api/v1/credits"):
            operation_routes.append(compact_path)
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/credits",
        "health": ",".join(health_routes),
        "accounts": ",".join(account_routes),
        "balance": ",".join(balance_routes),
        "operations": ",".join(operation_routes),
        "campaigns": ",".join(campaign_routes),
        "stats": ",".join(stats_routes),
        "methods": "GET,POST,PUT",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }
# Service metadata
SERVICE_METADATA = {
    "service_name": "credit_service",
    "version": "1.0.0",
    "tags": ["v1", "credit", "promotional", "bonus"],
    "capabilities": [
        "credit_accounts",
        "credit_allocation",
        "credit_consumption",
        "credit_expiration",
        "credit_transfer",
        "campaign_management",
        "fifo_expiration",
        "event_driven"
    ]
}
