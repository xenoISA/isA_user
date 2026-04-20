"""
Component tests for the authorization_service role-assignment endpoint.

Hits the FastAPI route via starlette's TestClient, with all I/O
dependencies of the service mocked out. Validates:
    - Assigning a valid role with an authorized assigner succeeds (200).
    - An invalid role string returns HTTP 400 with the violated rule.
    - An unauthorized assigner (e.g. member assigning owner) returns
      HTTP 403 and logs a structured denial.
    - Logged denial includes the rule name as a structured `extra` field.

Issue: xenoISA/isA_user#273 (parent epic #270).
"""
from __future__ import annotations

import logging
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

pytestmark = pytest.mark.component


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_service():
    """
    Build an AuthorizationService with a mocked repository so we can wire
    it into the FastAPI app without any I/O.
    """
    from microservices.authorization_service.authorization_service import (
        AuthorizationService,
    )

    repo = AsyncMock()
    return AuthorizationService(repository=repo, event_bus=None)


@pytest.fixture
def client(mock_service):
    """
    A TestClient bound to the real FastAPI app with the module-level
    `authorization_service` global swapped for our mocked instance.
    """
    # Import here to avoid top-level FastAPI app side effects during
    # collection.
    from microservices.authorization_service import main as authz_main

    original = authz_main.authorization_service
    authz_main.authorization_service = mock_service
    try:
        yield TestClient(authz_main.app)
    finally:
        authz_main.authorization_service = original


# ---------------------------------------------------------------------------
# /api/v1/authorization/assign-role
# ---------------------------------------------------------------------------

def test_valid_role_assignment_succeeds(client):
    """owner assigning member at org scope -> 200."""
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_owner_1",
            "assigner_role": "owner",
            "assignee_user_id": "usr_target_1",
            "assignee_role": "member",
            "scope": "organization",
            "organization_id": "org_1",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["normalized_role"] == "member"
    assert body["scope"] == "organization"


def test_legacy_editor_normalized_to_member(client):
    """Legacy `editor` alias is accepted and normalized to `member`."""
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_owner_1",
            "assigner_role": "owner",
            "assignee_user_id": "usr_target_2",
            "assignee_role": "editor",
            "scope": "organization",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["normalized_role"] == "member"


def test_invalid_role_string_returns_400(client):
    """
    Garbage role string -> HTTP 400 with `invalid_org_role` rule.
    """
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_owner_1",
            "assigner_role": "owner",
            "assignee_user_id": "usr_target_3",
            "assignee_role": "super_cool_hacker",
            "scope": "organization",
        },
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["rule"] == "invalid_org_role"
    assert "role-taxonomy.md" in detail["message"]


def test_platform_role_rejected_at_org_scope(client):
    """A platform-admin string is not a valid org-scope role input."""
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_owner_1",
            "assigner_role": "owner",
            "assignee_user_id": "usr_target_4",
            "assignee_role": "super_admin",
            "scope": "organization",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["rule"] == "invalid_org_role"


def test_member_assigning_owner_is_denied(client, caplog):
    """
    Valid role strings but the assigner lacks authority.
    Expect HTTP 403 and a structured `role assignment denied` warning
    carrying the rule name.
    """
    with caplog.at_level(logging.WARNING):
        resp = client.post(
            "/api/v1/authorization/assign-role",
            json={
                "assigner_user_id": "usr_member_1",
                "assigner_role": "member",
                "assignee_user_id": "usr_target_5",
                "assignee_role": "owner",
                "scope": "organization",
            },
        )

    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert detail["rule"] == "assigner_not_authorized"

    # At least one warning carrying the rule name must be present.
    matching = [
        r for r in caplog.records
        if r.message == "role assignment denied"
        and getattr(r, "rule", None) == "assigner_not_authorized"
    ]
    assert matching, (
        "expected at least one structured 'role assignment denied' log "
        f"record with rule=assigner_not_authorized, got: "
        f"{[(r.message, getattr(r, 'rule', None)) for r in caplog.records]}"
    )
    record = matching[0]
    assert record.assigner == "usr_member_1"
    assert record.assignee == "usr_target_5"
    assert record.scope == "organization"


def test_admin_cannot_assign_owner(client):
    """
    Taxonomy callout: admin's ceiling is below owner.
    """
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_admin_1",
            "assigner_role": "admin",
            "assignee_user_id": "usr_target_6",
            "assignee_role": "owner",
            "scope": "organization",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["rule"] == "assigner_not_authorized"


def test_platform_scope_invalid_role_returns_400(client):
    """A non-platform role at platform scope -> 400."""
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_super_1",
            "assigner_role": "super_admin",
            "assignee_user_id": "usr_target_7",
            "assignee_role": "member",
            "scope": "platform",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["rule"] == "invalid_platform_role"


def test_super_admin_assigns_platform_role(client):
    """super_admin assigning billing_admin -> 200."""
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_super_1",
            "assigner_role": "super_admin",
            "assignee_user_id": "usr_target_8",
            "assignee_role": "billing_admin",
            "scope": "platform",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["normalized_role"] == "billing_admin"
    assert body["scope"] == "platform"


def test_app_scope_never_assignable(client):
    """c-users are provisioned by the consuming app, not by this service."""
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_owner_1",
            "assigner_role": "owner",
            "assignee_user_id": "usr_target_9",
            "assignee_role": "consumer",
            "scope": "app",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["rule"] == "app_scope_not_assignable"


def test_unknown_scope_returns_400(client):
    resp = client.post(
        "/api/v1/authorization/assign-role",
        json={
            "assigner_user_id": "usr_owner_1",
            "assigner_role": "owner",
            "assignee_user_id": "usr_target_10",
            "assignee_role": "member",
            "scope": "galactic",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["rule"] == "unknown_scope"
