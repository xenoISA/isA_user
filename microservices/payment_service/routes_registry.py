"""
Payment Service Routes Registry
Defines all API routes for Consul service registration
"""
from typing import List, Dict, Any
# Define all routes
SERVICE_ROUTES = [
    # Health and Service Info
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Health check endpoint"
    },
        {
            "path": "/api/v1/payment/health",
            "methods": ["GET"],
            "auth_required": False,
            "description": "Service health check (API v1)"
        },
    {
        "path": "/api/v1/payment/info",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service information"
    },
    {
        "path": "/api/v1/payment/stats",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Service statistics"
    },
    # Subscription Plans
    {
        "path": "/api/v1/payment/plans",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create subscription plan"
    },
    {
        "path": "/api/v1/payment/plans/{plan_id}",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get subscription plan"
    },
    {
        "path": "/api/v1/payment/plans",
        "methods": ["GET"],
        "auth_required": False,
        "description": "List subscription plans"
    },
    # Subscriptions
    {
        "path": "/api/v1/payment/subscriptions",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create subscription"
    },
    {
        "path": "/api/v1/payment/subscriptions/user/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user subscription"
    },
    {
        "path": "/api/v1/payment/subscriptions/{subscription_id}",
        "methods": ["PUT"],
        "auth_required": True,
        "description": "Update subscription"
    },
    {
        "path": "/api/v1/payment/subscriptions/{subscription_id}/cancel",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Cancel subscription"
    },
    # Payments
    {
        "path": "/api/v1/payment/payments/intent",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create payment intent"
    },
    {
        "path": "/api/v1/payment/payments/{payment_id}/confirm",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Confirm payment"
    },
    {
        "path": "/api/v1/payment/payments/{payment_id}/fail",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Mark payment as failed"
    },
    {
        "path": "/api/v1/payment/payments/user/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user payment history"
    },
    # Invoices
    {
        "path": "/api/v1/payment/invoices",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create invoice"
    },
    {
        "path": "/api/v1/payment/invoices/{invoice_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get invoice"
    },
    {
        "path": "/api/v1/payment/invoices/{invoice_id}/pay",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Pay invoice"
    },
    # Refunds
    {
        "path": "/api/v1/payment/refunds",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create refund"
    },
    {
        "path": "/api/v1/payment/refunds/{refund_id}/process",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Process refund"
    },
    # Webhooks & Usage
    {
        "path": "/api/v1/payment/webhooks/stripe",
        "methods": ["POST"],
        "auth_required": False,
        "description": "Stripe webhook handler"
    },
    {
        "path": "/api/v1/payment/usage",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Record usage"
    },
    # Statistics
    {
        "path": "/api/v1/payment/stats/revenue",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get revenue statistics"
    },
    {
        "path": "/api/v1/payment/stats/subscriptions",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get subscription statistics"
    }
]
def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have a 512 character limit
    """
    # Categorize routes
    health_routes = []
    plan_routes = []
    subscription_routes = []
    payment_routes = []
    invoice_routes = []
    refund_routes = []
    webhook_routes = []
    stats_routes = []
    for route in SERVICE_ROUTES:
        path = route["path"]
        # Use compact representation
        compact_path = path.replace("/api/v1/payment/", "").replace("/api/v1/", "")
        if path.startswith("/health"):
            health_routes.append(compact_path)
        elif "/plans" in path:
            plan_routes.append(compact_path)
        elif "/subscriptions" in path:
            subscription_routes.append(compact_path)
        elif "/payments/" in path:
            payment_routes.append(compact_path)
        elif "/invoices" in path:
            invoice_routes.append(compact_path)
        elif "/refunds" in path:
            refund_routes.append(compact_path)
        elif "/webhooks" in path or "/usage" in path:
            webhook_routes.append(compact_path)
        elif "/stats" in path or path.endswith("/info"):
            stats_routes.append(compact_path)
    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/payment",
        "health": ",".join(health_routes),
        "plan": ",".join(plan_routes[:3]),  # Limit to avoid 512 char limit
        "subscription": ",".join(subscription_routes[:4]),  # Limit
        "payment": ",".join(payment_routes[:4]),  # Limit
        "invoice": ",".join(invoice_routes),
        "refund": ",".join(refund_routes),
        "webhook": ",".join(webhook_routes),
        "stats": ",".join(stats_routes),
        "methods": "GET,POST,PUT",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }
# Service metadata
SERVICE_METADATA = {
    "service_name": "payment_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "payment", "billing"],
    "capabilities": [
        "subscription_management",
        "payment_processing",
        "invoice_management",
        "refund_processing",
        "stripe_integration",
        "webhook_handling",
        "usage_tracking",
        "revenue_analytics"
    ]
}
