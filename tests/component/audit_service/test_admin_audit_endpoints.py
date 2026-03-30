"""
Component Tests -- Admin Audit Endpoints

L2: Tests audit_service admin action endpoints with mocked repository.
Uses FastAPI TestClient to exercise request/response contracts.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from microservices.audit_service.admin_audit_models import AdminAuditLogEntry
from microservices.audit_service.admin_audit_repository import AdminAuditRepository


def _sample_entry(**overrides) -> AdminAuditLogEntry:
    defaults = dict(
        id=1,
        audit_id="admin_audit_abc123",
        admin_user_id="admin_001",
        admin_email="admin@test.com",
        action="create_product",
        resource_type="product",
        resource_id="prod_123",
        changes={"after": {"name": "Widget"}},
        ip_address="10.0.0.1",
        user_agent="TestAgent",
        timestamp=datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc),
        metadata={"source": "product_service"},
    )
    defaults.update(overrides)
    return AdminAuditLogEntry(**defaults)


@pytest.fixture
def mock_admin_audit_repo():
    return AsyncMock(spec=AdminAuditRepository)


@pytest.fixture
def client(mock_admin_audit_repo):
    """Create TestClient with mocked dependencies, bypassing lifespan"""
    import microservices.audit_service.main as audit_main

    # Replace lifespan with a no-op to avoid real DB/NATS/signal setup
    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    orig_lifespan = audit_main.app.router.lifespan_context
    audit_main.app.router.lifespan_context = noop_lifespan

    # Inject mock globals
    orig_audit_service = audit_main.audit_service
    orig_admin_audit_repo = audit_main.admin_audit_repo

    mock_audit_svc = AsyncMock()
    audit_main.audit_service = mock_audit_svc
    audit_main.admin_audit_repo = mock_admin_audit_repo

    with TestClient(audit_main.app, raise_server_exceptions=False) as c:
        yield c

    # Restore
    audit_main.audit_service = orig_audit_service
    audit_main.admin_audit_repo = orig_admin_audit_repo
    audit_main.app.router.lifespan_context = orig_lifespan


class TestGetAdminActions:
    """GET /api/v1/audit/admin/actions"""

    def test_returns_actions_with_filters(self, client, mock_admin_audit_repo):
        """Should return filtered admin actions"""
        entry = _sample_entry()
        mock_admin_audit_repo.query_admin_audit_log = AsyncMock(return_value=([entry], 1))

        resp = client.get(
            "/api/v1/audit/admin/actions",
            params={"admin_user_id": "admin_001", "resource_type": "product"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 1
        assert len(body["actions"]) == 1
        assert body["actions"][0]["audit_id"] == "admin_audit_abc123"
        assert body["actions"][0]["action"] == "create_product"
        assert body["filters_applied"]["admin_user_id"] == "admin_001"

    def test_returns_empty_list_when_no_results(self, client, mock_admin_audit_repo):
        """Should return empty actions list"""
        mock_admin_audit_repo.query_admin_audit_log = AsyncMock(return_value=([], 0))

        resp = client.get("/api/v1/audit/admin/actions")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 0
        assert body["actions"] == []

    def test_pagination_params_forwarded(self, client, mock_admin_audit_repo):
        """limit and offset should appear in response"""
        mock_admin_audit_repo.query_admin_audit_log = AsyncMock(return_value=([], 0))

        resp = client.get(
            "/api/v1/audit/admin/actions",
            params={"limit": 50, "offset": 10},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 50
        assert body["offset"] == 10

    def test_action_filter(self, client, mock_admin_audit_repo):
        """Should filter by action"""
        entry = _sample_entry(action="delete_product")
        mock_admin_audit_repo.query_admin_audit_log = AsyncMock(return_value=([entry], 1))

        resp = client.get(
            "/api/v1/audit/admin/actions",
            params={"action": "delete_product"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["actions"][0]["action"] == "delete_product"
        assert body["filters_applied"]["action"] == "delete_product"


class TestPostAdminAction:
    """POST /api/v1/audit/admin/actions"""

    def test_records_admin_action(self, client, mock_admin_audit_repo):
        """Should create an admin audit entry and return it"""
        entry = _sample_entry()
        mock_admin_audit_repo.create_admin_audit_entry = AsyncMock(return_value=entry)

        resp = client.post(
            "/api/v1/audit/admin/actions",
            json={
                "admin_user_id": "admin_001",
                "admin_email": "admin@test.com",
                "action": "create_product",
                "resource_type": "product",
                "resource_id": "prod_123",
                "changes": {"after": {"name": "Widget"}},
            },
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["admin_user_id"] == "admin_001"
        assert body["action"] == "create_product"
        assert body["resource_type"] == "product"
        assert body["audit_id"] == "admin_audit_abc123"

    def test_returns_422_for_missing_required_fields(self, client, mock_admin_audit_repo):
        """Missing admin_user_id or action should fail validation"""
        resp = client.post(
            "/api/v1/audit/admin/actions",
            json={"resource_type": "product"},
        )

        assert resp.status_code == 422

    def test_returns_500_when_repo_fails(self, client, mock_admin_audit_repo):
        """When repo returns None, should return 500"""
        mock_admin_audit_repo.create_admin_audit_entry = AsyncMock(return_value=None)

        resp = client.post(
            "/api/v1/audit/admin/actions",
            json={
                "admin_user_id": "admin_001",
                "action": "create_product",
                "resource_type": "product",
            },
        )

        assert resp.status_code == 500

    def test_changes_field_is_optional(self, client, mock_admin_audit_repo):
        """changes field should default to empty dict if not provided"""
        entry = _sample_entry(changes={})
        mock_admin_audit_repo.create_admin_audit_entry = AsyncMock(return_value=entry)

        resp = client.post(
            "/api/v1/audit/admin/actions",
            json={
                "admin_user_id": "admin_001",
                "action": "delete_product",
                "resource_type": "product",
                "resource_id": "prod_999",
            },
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["changes"] == {}
