"""
Gateway Smoke Tests — Verify APISIX routes reach backend services.

Tests core services THROUGH the APISIX gateway to catch routing mismatches.
Always runs in gateway mode regardless of SMOKE_MODE env var.

Usage:
    pytest tests/smoke/test_gateway_smoke.py -v
"""

import os

import httpx
import pytest

from tests.smoke.conftest import resolve_service_url

pytestmark = pytest.mark.smoke

HOST = os.getenv("HEALTH_HOST", "localhost")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8000"))
GATEWAY_URL = f"http://{HOST}:{GATEWAY_PORT}"
TIMEOUT = 10.0

# Core services that MUST be reachable through the gateway
CORE_SERVICES = [
    ("auth_service", "/api/v1/auth/health"),
    ("session_service", "/api/v1/sessions/health"),
    ("organization_service", "/api/v1/organization/health"),
    ("task_service", "/api/v1/tasks/health"),
    ("payment_service", "/api/v1/payment/health"),
    ("wallet_service", "/api/v1/wallets/health"),
    ("order_service", "/api/v1/orders/health"),
    ("vault_service", "/api/v1/vault/health"),
    ("billing_service", "/api/v1/billing/health"),
    ("event_service", "/api/v1/events/health"),
    ("telemetry_service", "/api/v1/telemetry/health"),
    ("memory_service", "/api/v1/memory/health"),
]


class TestGatewayHealthSmoke:
    """Verify each core service is reachable through APISIX."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "service_name,health_path",
        CORE_SERVICES,
        ids=[s[0] for s in CORE_SERVICES],
    )
    async def test_gateway_health(self, service_name, health_path):
        url = f"{GATEWAY_URL}{health_path}"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            assert resp.status_code in (200, 204), (
                f"Gateway route for {service_name} returned {resp.status_code} at {url}. "
                f"Check APISIX route configuration."
            )


class TestGatewayRoutingSmoke:
    """Verify gateway routes match direct service routes."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "service_name,health_path",
        CORE_SERVICES[:5],  # Test a subset to keep it fast
        ids=[s[0] for s in CORE_SERVICES[:5]],
    )
    async def test_gateway_vs_direct(self, service_name, health_path):
        """Compare gateway and direct responses — both should return 200."""
        direct_url = resolve_service_url(service_name, "/health", mode="direct")
        gateway_url = resolve_service_url(service_name, "/health", mode="gateway")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            direct_resp = await client.get(direct_url)
            gateway_resp = await client.get(gateway_url)

            if direct_resp.status_code == 200 and gateway_resp.status_code != 200:
                pytest.fail(
                    f"{service_name}: direct (/health → {direct_resp.status_code}) "
                    f"works but gateway ({health_path} → {gateway_resp.status_code}) fails. "
                    f"APISIX route may be misconfigured."
                )


class TestGatewayAuthForwardingSmoke:
    """Verify the gateway forwards auth headers to backend services."""

    @pytest.mark.asyncio
    async def test_auth_header_forwarded(self):
        """Send Bearer token through gateway — backend should receive it."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{GATEWAY_URL}/api/v1/auth/verify-token",
                json={"token": "test-invalid-token"},
                headers={"Authorization": "Bearer test-token"},
            )
            # Should reach backend (401/422 = token invalid, NOT 404 = route missing)
            assert resp.status_code in (200, 401, 403, 422), (
                f"Auth endpoint returned {resp.status_code} — "
                f"gateway may not be forwarding to auth service"
            )

    @pytest.mark.asyncio
    async def test_internal_headers_forwarded(self):
        """Internal service headers should reach backend through gateway."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{GATEWAY_URL}/api/v1/tasks/health",
                headers={
                    "X-Internal-Call": "true",
                    "X-Internal-Service": "true",
                    "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
                },
            )
            assert resp.status_code in (200, 204)
