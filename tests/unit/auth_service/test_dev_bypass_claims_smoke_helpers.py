"""Unit coverage for auth dev-bypass claims smoke helpers."""

import pytest

from tests.smoke.auth_service.test_dev_bypass_claims_smoke import (
    assert_expected_claims,
    redact_payload,
    redact_token,
)


def test_redact_token_keeps_only_prefix_and_suffix():
    assert redact_token("abcdefghijklmnopqrstuvwxyz") == "abcdefgh...uvwxyz"


def test_redact_payload_removes_nested_tokens():
    payload = {
        "token": "abcdefghijklmnopqrstuvwxyz",
        "nested": {"access_token": "1234567890abcdefghijkl"},
        "items": [{"refresh_token": "token-token-token-token"}],
    }

    redacted = redact_payload(payload)

    assert redacted["token"] == "abcdefgh...uvwxyz"
    assert redacted["nested"]["access_token"] == "12345678...ghijkl"
    assert redacted["items"][0]["refresh_token"] == "token-to...-token"


def test_assert_expected_claims_accepts_admin_contract():
    assert_expected_claims(
        email="admin@example.com",
        is_admin=True,
        verify_data={
            "valid": True,
            "email": "admin@example.com",
            "role": "admin",
            "permissions": ["auth.admin"],
            "scopes": ["read", "write", "admin"],
            "organization_id": "org_1",
        },
        user_info={
            "email": "admin@example.com",
            "user_id": "usr_1",
            "organization_id": "org_1",
            "tenant_id": "org_1",
            "roles": ["admin"],
            "admin_roles": [],
            "organization_permissions": [],
            "permissions": ["auth.admin"],
        },
    )


def test_assert_expected_claims_rejects_non_admin_with_admin_permission():
    with pytest.raises(AssertionError):
        assert_expected_claims(
            email="user@example.com",
            is_admin=False,
            verify_data={
                "valid": True,
                "email": "user@example.com",
                "role": None,
                "permissions": ["auth.admin"],
                "scopes": ["read"],
                "organization_id": None,
            },
            user_info={
                "email": "user@example.com",
                "user_id": "usr_2",
                "organization_id": None,
                "tenant_id": None,
                "roles": [],
                "admin_roles": [],
                "organization_permissions": [],
                "permissions": ["auth.admin"],
            },
        )
