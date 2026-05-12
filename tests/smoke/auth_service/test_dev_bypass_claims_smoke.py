"""
Auth dev-bypass claims smoke.

Validates the local auth path consumed by JupyterHub/APISIX/isA_Model:
dev-bypass token issuance, verify-token claims, and user-info claims for
seeded admin and non-admin users.

Usage:
    AUTH_DEV_BYPASS_ENABLED=true \
    AUTH_DEV_BYPASS_USERS=admin@example.com,user@example.com \
    AUTH_DEV_BYPASS_ADMINS=admin@example.com \
    pytest tests/smoke/auth_service/test_dev_bypass_claims_smoke.py -v

Optional:
    AUTH_CLAIMS_SMOKE_ADMIN_EMAIL=admin@example.com
    AUTH_CLAIMS_SMOKE_USER_EMAIL=user@example.com
    AUTH_CLAIMS_SMOKE_EVIDENCE=reports/auth-claims-smoke.json
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.smoke.conftest import resolve_base_url

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

TIMEOUT = 15.0
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_USER_EMAIL = "user@example.com"


def redact_token(token: str | None) -> str | None:
    """Return a non-sensitive token fingerprint for evidence files."""
    if not token:
        return None
    if len(token) <= 16:
        return "***"
    return f"{token[:8]}...{token[-6:]}"


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: redact_token(item)
            if key in {"token", "access_token", "refresh_token"}
            else redact_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value


def assert_expected_claims(
    *,
    email: str,
    is_admin: bool,
    verify_data: dict[str, Any],
    user_info: dict[str, Any],
) -> None:
    assert verify_data["valid"] is True
    assert verify_data["email"] == email
    assert user_info["email"] == email
    assert user_info["user_id"]
    assert "permissions" in verify_data
    assert "permissions" in user_info
    assert "organization_id" in verify_data
    assert "organization_id" in user_info
    assert "tenant_id" in user_info
    assert "roles" in user_info
    assert "admin_roles" in user_info
    assert "organization_permissions" in user_info

    if is_admin:
        assert verify_data["role"] == "admin"
        assert "auth.admin" in verify_data["permissions"]
        assert "admin" in verify_data["scopes"]
        assert "admin" in user_info["roles"]
        assert "auth.admin" in user_info["permissions"]
    else:
        assert verify_data.get("role") != "admin"
        assert "auth.admin" not in verify_data["permissions"]
        assert "admin" not in user_info["roles"]
        assert "auth.admin" not in user_info["permissions"]


async def _post_json(
    client: httpx.AsyncClient, url: str, payload: dict[str, Any]
) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code == 404:
        pytest.skip(f"Auth dev-bypass endpoint unavailable at {url}")
    if response.status_code == 403:
        pytest.skip("Auth dev-bypass user is not allowlisted in AUTH_DEV_BYPASS_USERS")
    assert (
        response.status_code == 200
    ), f"{url} failed: {response.status_code} {response.text}"
    return response.json()


async def _exercise_claims_flow(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    email: str,
    is_admin: bool,
) -> dict[str, Any]:
    bypass_data = await _post_json(
        client,
        f"{base_url}/api/v1/auth/dev-bypass",
        {"email": email, "expires_in": 900},
    )
    token = bypass_data["token"]

    verify_data = await _post_json(
        client,
        f"{base_url}/api/v1/auth/verify-token",
        {"token": token},
    )
    user_info = await _post_json(
        client,
        f"{base_url}/api/v1/auth/user-info",
        {"token": token},
    )

    assert_expected_claims(
        email=email,
        is_admin=is_admin,
        verify_data=verify_data,
        user_info=user_info,
    )

    return {
        "email": email,
        "is_admin": is_admin,
        "dev_bypass": bypass_data,
        "verify_token": verify_data,
        "user_info": user_info,
    }


def _write_evidence(evidence_path: str | None, evidence: dict[str, Any]) -> None:
    if not evidence_path:
        return
    path = Path(evidence_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(redact_payload(evidence), indent=2, sort_keys=True), encoding="utf-8"
    )


async def test_dev_bypass_admin_and_user_claims_smoke():
    if os.getenv("AUTH_DEV_BYPASS_ENABLED", "").lower() != "true":
        pytest.skip("Set AUTH_DEV_BYPASS_ENABLED=true to run dev-bypass claims smoke")

    base_url = resolve_base_url("auth_service")
    admin_email = os.getenv("AUTH_CLAIMS_SMOKE_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)
    user_email = os.getenv("AUTH_CLAIMS_SMOKE_USER_EMAIL", DEFAULT_USER_EMAIL)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        admin_evidence = await _exercise_claims_flow(
            client=client,
            base_url=base_url,
            email=admin_email,
            is_admin=True,
        )
        user_evidence = await _exercise_claims_flow(
            client=client,
            base_url=base_url,
            email=user_email,
            is_admin=False,
        )

    evidence = {
        "service": "auth_service",
        "base_url": base_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "flows": [admin_evidence, user_evidence],
    }
    _write_evidence(os.getenv("AUTH_CLAIMS_SMOKE_EVIDENCE"), evidence)
