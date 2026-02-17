"""
Wallet Service Routes Registry
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
            "path": "/api/v1/wallets/health",
            "methods": ["GET"],
            "auth_required": False,
            "description": "Service health check (API v1)"
        },
    # Wallet Management
    {
        "path": "/api/v1/wallets",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create new wallet"
    },
    {
        "path": "/api/v1/wallets/{wallet_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get wallet details"
    },
    {
        "path": "/api/v1/wallets",
        "methods": ["GET"],
        "auth_required": True,
        "description": "List user wallets (with user_id query parameter)"
    },
    {
        "path": "/api/v1/wallets/{wallet_id}/balance",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get wallet balance"
    },
    # Wallet Operations
    {
        "path": "/api/v1/wallets/{wallet_id}/deposit",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Deposit funds to wallet"
    },
    {
        "path": "/api/v1/wallets/{wallet_id}/withdraw",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Withdraw funds from wallet"
    },
    {
        "path": "/api/v1/wallets/{wallet_id}/consume",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Consume wallet balance"
    },
    {
        "path": "/api/v1/wallets/credits/consume",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Consume user credits (with user_id query parameter)"
    },
    {
        "path": "/api/v1/wallets/{wallet_id}/transfer",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Transfer funds between wallets"
    },
    {
        "path": "/api/v1/transactions/{transaction_id}/refund",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Refund transaction"
    },
    # Transaction History
    {
        "path": "/api/v1/wallets/{wallet_id}/transactions",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get wallet transaction history"
    },
    {
        "path": "/api/v1/wallets/transactions",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user transaction history (with user_id query parameter)"
    },
    # Statistics & Credits
    {
        "path": "/api/v1/wallets/{wallet_id}/statistics",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get wallet statistics"
    },
    {
        "path": "/api/v1/wallets/statistics",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user wallet statistics (with user_id query parameter)"
    },
    {
        "path": "/api/v1/wallets/credits/balance",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user credit balance (with user_id query parameter)"
    },
    {
        "path": "/api/v1/wallet/stats",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get service statistics"
    }
]
def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have a 512 character limit
    """
    # Categorize routes
    health_routes = []
    wallet_routes = []
    operation_routes = []
    transaction_routes = []
    stats_routes = []
    for route in SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation
        compact_path = path.replace("/api/v1/wallets/", "").replace("/api/v1/", "")
        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "transactions" in path:
            transaction_routes.append(compact_path)
        elif "statistics" in path or "stats" in path or "credits/balance" in path:
            stats_routes.append(compact_path)
        elif "/deposit" in path or "/withdraw" in path or "/consume" in path or "/transfer" in path or "/refund" in path:
            operation_routes.append(compact_path)
        elif path.startswith("/api/v1/wallets") or "/wallets" in path:
            wallet_routes.append(compact_path)
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/wallets",
        "health": ",".join(health_routes),
        "wallet": ",".join(wallet_routes[:4]),  # Limit to avoid 512 char limit
        "operation": ",".join(operation_routes[:5]),  # Limit to avoid 512 char limit
        "transaction": ",".join(transaction_routes),
        "stats": ",".join(stats_routes[:3]),  # Limit to avoid 512 char limit
        "methods": "GET,POST",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }
# Service metadata
SERVICE_METADATA = {
    "service_name": "wallet_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "wallet", "payment"],
    "capabilities": [
        "wallet_management",
        "balance_management",
        "deposit_withdraw",
        "credit_system",
        "transaction_history",
        "wallet_transfer",
        "transaction_refund",
        "event_driven"
    ]
}
