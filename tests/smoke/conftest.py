"""
Shared fixtures for isA_user smoke tests.

Supports SMOKE_MODE=gateway|direct to route tests through APISIX or direct to service ports.

Usage:
    pytest tests/smoke/ -v                          # direct mode (default)
    SMOKE_MODE=gateway pytest tests/smoke/ -v       # through APISIX gateway
"""

import os

import pytest

# ── Gateway routing map ──
# Maps service_name → (direct_port, gateway_prefix)
# Gateway prefix is the APISIX route segment: /api/v1/{prefix}/...
SERVICE_ROUTING = {
    "auth_service": (8201, "auth"),
    "account_service": (8202, "accounts"),
    "session_service": (8203, "sessions"),
    "authorization_service": (8204, "authorization"),
    "audit_service": (8205, "audit"),
    "notification_service": (8206, "notifications"),
    "payment_service": (8207, "payment"),
    "wallet_service": (8208, "wallets"),
    "storage_service": (8209, "storage"),
    "order_service": (8210, "orders"),
    "task_service": (8211, "tasks"),
    "organization_service": (8212, "organization"),
    "invitation_service": (8213, "invitations"),
    "vault_service": (8214, "vault"),
    "product_service": (8215, "products"),
    "billing_service": (8216, "billing"),
    "calendar_service": (8217, "calendar"),
    "weather_service": (8218, "weather"),
    "album_service": (8219, "albums"),
    "device_service": (8220, "devices"),
    "ota_service": (8221, "ota"),
    "media_service": (8222, "media"),
    "memory_service": (8223, "memory"),
    "location_service": (8224, "locations"),
    "telemetry_service": (8225, "telemetry"),
    "compliance_service": (8226, "compliance"),
    "document_service": (8227, "documents"),
    "subscription_service": (8228, "subscriptions"),
    "event_service": (8230, "events"),
    # Newer services (not in TestConfig.SERVICES)
    "campaign_service": (8251, "campaigns"),
    "inventory_service": (8252, "inventory"),
    "tax_service": (8253, "tax"),
    "fulfillment_service": (8254, "fulfillment"),
}

GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8000"))
HOST = os.getenv("HEALTH_HOST", "localhost")


@pytest.fixture(scope="session")
def smoke_mode():
    """Returns 'gateway' or 'direct'."""
    return os.getenv("SMOKE_MODE", "direct")


def base_url_for(service_name: str, mode: str = None) -> str:
    """
    Get the base URL for a service based on smoke mode.

    Gateway mode:  http://localhost:8000  (all services via APISIX)
    Direct mode:   http://localhost:{port} (per-service port)
    """
    if mode is None:
        mode = os.getenv("SMOKE_MODE", "direct")

    routing = SERVICE_ROUTING.get(service_name)
    if not routing:
        raise ValueError(f"Unknown service: {service_name}. Add it to SERVICE_ROUTING.")

    port, _prefix = routing

    if mode == "gateway":
        return f"http://{HOST}:{GATEWAY_PORT}"
    return f"http://{HOST}:{port}"


def api_path_for(service_name: str, path: str, mode: str = None) -> str:
    """
    Get the full URL for an API path based on smoke mode.

    In gateway mode, the path is prefixed with /api/v1/{gateway_prefix}/
    In direct mode, the path is used as-is against the service port.

    Example:
        api_path_for("auth_service", "/api/v1/auth/health")
        → gateway: http://localhost:8000/api/v1/auth/health
        → direct:  http://localhost:8201/api/v1/auth/health
    """
    base = base_url_for(service_name, mode)
    return f"{base}{path}"
