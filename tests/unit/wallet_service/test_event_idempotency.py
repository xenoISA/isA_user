"""Unit tests for the durable event-processing claim layer (#380).

These exercise ``WalletRepository.claim_event_processing`` and its
companions against a hand-rolled fake DB so we can assert the SQL
shape without provisioning Postgres in the L1 layer. Real Postgres
behaviour is covered by component tests.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pytest

from microservices.wallet_service.wallet_repository import WalletRepository


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fake AsyncPostgresClient
# ---------------------------------------------------------------------------


class _FakeAsyncDB:
    """Minimal stand-in for AsyncPostgresClient used inside async-with."""

    def __init__(self):
        # Single in-memory row store keyed by claim_key
        self.rows: Dict[str, Dict[str, Any]] = {}
        self.queries: List[Dict[str, Any]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    # The repository calls ``self.db.query_row`` with positional ``params``
    # and a ``schema`` kwarg. We don't actually use the schema for routing
    # — the table is identified by string matching on the SQL itself.

    async def query_row(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        schema: str = "public",
    ) -> Optional[Dict[str, Any]]:
        params = list(params or [])
        self.queries.append({"sql": sql, "params": params, "schema": schema})
        normalised = " ".join(sql.split())
        if normalised.startswith("INSERT INTO wallet.event_processing_claims"):
            claim_key, source_event_id, processor_id, claimed_at = params[:4]
            if claim_key in self.rows:
                return None
            self.rows[claim_key] = {
                "claim_key": claim_key,
                "source_event_id": source_event_id,
                "processing_status": "processing",
                "processor_id": processor_id,
                "claimed_at": claimed_at,
                "completed_at": None,
                "last_error": None,
                "created_at": claimed_at,
                "updated_at": claimed_at,
            }
            return {"claim_key": claim_key}
        if normalised.startswith("UPDATE wallet.event_processing_claims"):
            claim_key = params[0]
            row = self.rows.get(claim_key)
            if row is None:
                return None
            # Reclaim path takes 5 params (claim_key, source_event_id,
            # processor_id, now, stale_cutoff). Status updates take 3 or 4.
            if len(params) == 5:
                _, source_event_id, processor_id, now, stale_cutoff = params
                if row["processing_status"] == "completed":
                    return None
                stale = row["updated_at"] < stale_cutoff
                if not (row["processing_status"] == "failed" or stale):
                    return None
                row.update(
                    {
                        "source_event_id": source_event_id,
                        "processing_status": "processing",
                        "processor_id": processor_id,
                        "claimed_at": now,
                        "completed_at": None,
                        "last_error": None,
                        "updated_at": now,
                    }
                )
                return {"claim_key": claim_key}
        return None

    async def execute(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        schema: str = "public",
    ) -> int:
        params = list(params or [])
        self.queries.append({"sql": sql, "params": params, "schema": schema})
        normalised = " ".join(sql.split())
        if "processing_status = 'completed'" in normalised:
            claim_key = params[0]
            row = self.rows.get(claim_key)
            if row is None:
                return 0
            row.update(
                {
                    "source_event_id": params[1],
                    "processing_status": "completed",
                    "completed_at": params[2],
                    "last_error": None,
                    "updated_at": params[2],
                }
            )
            return 1
        if "processing_status = 'failed'" in normalised:
            claim_key = params[0]
            row = self.rows.get(claim_key)
            if row is None or row["processing_status"] == "completed":
                return 0
            row.update(
                {
                    "source_event_id": params[1],
                    "processing_status": "failed",
                    "last_error": params[2],
                    "updated_at": params[3],
                }
            )
            return 1
        return 0


def _build_repository() -> WalletRepository:
    repo = object.__new__(WalletRepository)
    repo.db = _FakeAsyncDB()
    repo.schema = "wallet"
    repo.event_processing_claims_table = "event_processing_claims"
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClaimEventProcessing:
    async def test_first_claim_succeeds(self):
        repo = _build_repository()
        won = await repo.claim_event_processing(
            claim_key="wallet:payment_completed:evt_001",
            source_event_id="evt_001",
            processor_id="wallet_service:test:1",
        )
        assert won is True
        assert "wallet:payment_completed:evt_001" in repo.db.rows
        assert (
            repo.db.rows["wallet:payment_completed:evt_001"]["processing_status"]
            == "processing"
        )

    async def test_active_duplicate_is_blocked(self):
        repo = _build_repository()
        await repo.claim_event_processing(
            claim_key="wallet:payment_completed:evt_001",
            source_event_id="evt_001",
            processor_id="wallet_service:test:1",
        )

        won_again = await repo.claim_event_processing(
            claim_key="wallet:payment_completed:evt_001",
            source_event_id="evt_001",
            processor_id="wallet_service:test:2",
        )
        assert won_again is False

    async def test_completed_claim_blocks_replay(self):
        repo = _build_repository()
        await repo.claim_event_processing(
            claim_key="wallet:user_deleted:evt_007",
            source_event_id="evt_007",
            processor_id="wallet_service:test:1",
        )
        await repo.mark_event_processing_completed(
            claim_key="wallet:user_deleted:evt_007",
            source_event_id="evt_007",
        )

        replayed = await repo.claim_event_processing(
            claim_key="wallet:user_deleted:evt_007",
            source_event_id="evt_007",
            processor_id="wallet_service:test:2",
        )
        assert replayed is False
        # Status survives the replay attempt.
        assert (
            repo.db.rows["wallet:user_deleted:evt_007"]["processing_status"]
            == "completed"
        )

    async def test_failed_claim_can_be_retried(self):
        repo = _build_repository()
        await repo.claim_event_processing(
            claim_key="wallet:billing_calculated:evt_002",
            source_event_id="evt_002",
            processor_id="wallet_service:test:1",
        )
        await repo.mark_event_processing_failed(
            claim_key="wallet:billing_calculated:evt_002",
            source_event_id="evt_002",
            error_message="boom",
        )

        retried = await repo.claim_event_processing(
            claim_key="wallet:billing_calculated:evt_002",
            source_event_id="evt_002",
            processor_id="wallet_service:test:2",
        )
        assert retried is True
        assert (
            repo.db.rows["wallet:billing_calculated:evt_002"]["processing_status"]
            == "processing"
        )

    async def test_mark_completed_does_not_double_run(self):
        repo = _build_repository()
        await repo.claim_event_processing(
            claim_key="wallet:subscription_created:evt_003",
            source_event_id="evt_003",
            processor_id="wallet_service:test:1",
        )
        await repo.mark_event_processing_completed(
            claim_key="wallet:subscription_created:evt_003",
            source_event_id="evt_003",
        )

        # mark_failed should NOT downgrade a completed row (correctness
        # invariant — late-arriving error from a stale processor must
        # not reopen a successfully processed event for replay).
        await repo.mark_event_processing_failed(
            claim_key="wallet:subscription_created:evt_003",
            source_event_id="evt_003",
            error_message="late error",
        )
        assert (
            repo.db.rows["wallet:subscription_created:evt_003"]["processing_status"]
            == "completed"
        )


# ---------------------------------------------------------------------------
# Migration SQL smoke test
# ---------------------------------------------------------------------------


_MIGRATION_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "microservices",
        "wallet_service",
        "migrations",
        "003_add_event_processing_claims.sql",
    )
)
_DOWNGRADE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "microservices",
        "wallet_service",
        "migrations",
        "003_add_event_processing_claims.down.sql",
    )
)


def test_migration_creates_event_processing_claims_table():
    assert os.path.exists(_MIGRATION_PATH), f"missing migration: {_MIGRATION_PATH}"
    with open(_MIGRATION_PATH) as handle:
        sql = handle.read()

    assert "CREATE TABLE IF NOT EXISTS wallet.event_processing_claims" in sql
    assert "claim_key VARCHAR(255) UNIQUE NOT NULL" in sql
    assert "source_event_id" in sql
    assert "processor_id" in sql
    assert "processing_status" in sql
    # Indexes mirror billing migration 005 / payment migration 003.
    assert "idx_wallet_event_processing_claims_status" in sql
    assert "idx_wallet_event_processing_claims_source_event" in sql
    assert "idx_wallet_event_processing_claims_updated_at" in sql


def test_migration_is_reversible():
    assert os.path.exists(_DOWNGRADE_PATH), f"missing downgrade: {_DOWNGRADE_PATH}"
    with open(_DOWNGRADE_PATH) as handle:
        sql = handle.read()

    assert "DROP TABLE IF EXISTS wallet.event_processing_claims" in sql
    assert (
        "DROP INDEX IF EXISTS wallet.idx_wallet_event_processing_claims_status" in sql
    )
    assert (
        "DROP INDEX IF EXISTS wallet.idx_wallet_event_processing_claims_source_event"
        in sql
    )
    assert (
        "DROP INDEX IF EXISTS wallet.idx_wallet_event_processing_claims_updated_at"
        in sql
    )
    assert (
        "DROP TRIGGER IF EXISTS update_wallet_event_processing_claims_updated_at" in sql
    )
