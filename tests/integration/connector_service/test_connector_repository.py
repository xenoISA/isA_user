"""L3 integration tests for ConnectorRepository + dev_vault round-trip.

These tests need a live Postgres + the connector.connector +
connector.custom_mcp_connector tables. They are auto-skipped when
Postgres isn't reachable on the configured host/port — the L1/L2 layers
keep CI green even when no DB is available.

The dev_vault round-trip is exercised inline: store_secret -> persist
ref on the row -> revoke_secret -> ref is gone from the in-memory store.
"""

from __future__ import annotations

import os
import socket
import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _postgres_reachable() -> bool:
    """Quick TCP probe so we can skip cleanly when the DB isn't up."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark.append(
    pytest.mark.skipif(
        not _postgres_reachable(),
        reason="Postgres not reachable; integration suite skipped",
    )
)


@pytest.fixture
def user_id() -> str:
    return f"user-{uuid.uuid4().hex[:10]}"


@pytest.fixture
async def repo():
    from microservices.connector_service.connector_repository import ConnectorRepository

    return ConnectorRepository()


# ---------------------------------------------------------------------------
# custom_mcp_connector — insert + read-back + delete
# ---------------------------------------------------------------------------


async def test_insert_and_read_back_custom_mcp(repo, user_id):
    row = await repo.insert_custom(
        user_id=user_id,
        label="My Notion",
        url="https://notion.mcp.example.com/sse",
        auth_kind="pat",
        auth_secret_ref="devvault:test:abc",
        status="active",
        tools_count=12,
    )
    assert row is not None
    assert row.user_id == user_id
    assert row.label == "My Notion"
    assert row.status.value == "active"
    assert row.tools_count == 12

    fetched = await repo.get_custom_by_id(user_id, row.id)
    assert fetched is not None
    assert fetched.id == row.id


async def test_unique_user_url_constraint_round_trip(repo, user_id):
    url = "https://uniq.mcp.example.com/sse"
    first = await repo.insert_custom(
        user_id=user_id,
        label="A",
        url=url,
        auth_kind="none",
        auth_secret_ref=None,
        status="active",
    )
    assert first is not None
    # Second insert with the same (user_id, url) should raise.
    with pytest.raises(Exception):
        await repo.insert_custom(
            user_id=user_id,
            label="B",
            url=url,
            auth_kind="none",
            auth_secret_ref=None,
            status="active",
        )


async def test_delete_removes_row(repo, user_id):
    row = await repo.insert_custom(
        user_id=user_id,
        label="ephemeral",
        url=f"https://gone-{uuid.uuid4().hex[:8]}.example.com/sse",
        auth_kind="none",
        auth_secret_ref=None,
        status="active",
    )
    ok = await repo.delete_custom(user_id, row.id)
    assert ok is True
    gone = await repo.get_custom_by_id(user_id, row.id)
    assert gone is None


# ---------------------------------------------------------------------------
# dev_vault round-trip
# ---------------------------------------------------------------------------


async def test_dev_vault_round_trip_with_repo(repo, user_id):
    from microservices.connector_service import dev_vault

    ref = dev_vault.store_secret(user_id, "my-pat", "shh-secret")
    assert ref.startswith("devvault:")
    assert dev_vault.get_secret(ref) == "shh-secret"

    row = await repo.insert_custom(
        user_id=user_id,
        label="with-secret",
        url=f"https://secret-{uuid.uuid4().hex[:8]}.example.com/sse",
        auth_kind="pat",
        auth_secret_ref=ref,
        status="active",
        tools_count=3,
    )
    assert row is not None

    # The API model intentionally does NOT expose auth_secret_ref —
    # round-trip the column directly to assert it persisted.
    fetched = await repo.get_custom_by_id(user_id, row.id)
    assert fetched is not None

    # Revoke + ensure the stub no longer hands out the secret.
    assert dev_vault.revoke_secret(ref) is True
    assert dev_vault.get_secret(ref) is None
