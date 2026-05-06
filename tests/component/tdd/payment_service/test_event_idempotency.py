"""Component tests for payment_service event-handler idempotency (#378).

These tests run the real handler functions with a fakeredis-backed
distributed lock + result cache and a hand-rolled claim repository.
They demonstrate the crash-and-replay scenario the issue calls out:

* First delivery → handler runs, marks claim ``completed``.
* Second delivery (after lock TTL elapses on a different processor)
  → durable claim short-circuits the handler before any duplicate
  payment-intent / cancellation work.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.payment_service.events import handlers as payment_handlers


pytestmark = pytest.mark.component


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _FakeClaimRepository:
    """In-memory claim store implementing the repository contract."""

    def __init__(self) -> None:
        self.claims: Dict[str, Dict[str, Any]] = {}
        # Flat method-call log so tests can assert handler ordering.
        self.calls: List[str] = []

    async def claim_event_processing(
        self,
        claim_key: str,
        source_event_id: str,
        processor_id: str,
        stale_after_seconds: int = 300,
    ) -> bool:
        self.calls.append(f"claim:{claim_key}")
        existing = self.claims.get(claim_key)
        if existing and existing["status"] in {"processing", "completed"}:
            return False
        self.claims[claim_key] = {
            "status": "processing",
            "source_event_id": source_event_id,
            "processor_id": processor_id,
        }
        return True

    async def mark_event_processing_completed(
        self,
        claim_key: str,
        source_event_id: str,
    ) -> None:
        self.calls.append(f"complete:{claim_key}")
        self.claims[claim_key] = {
            "status": "completed",
            "source_event_id": source_event_id,
        }

    async def mark_event_processing_failed(
        self,
        claim_key: str,
        source_event_id: str,
        error_message: str,
    ) -> None:
        self.calls.append(f"fail:{claim_key}")
        existing = self.claims.get(claim_key)
        if existing and existing.get("status") == "completed":
            return
        self.claims[claim_key] = {
            "status": "failed",
            "source_event_id": source_event_id,
            "error_message": error_message,
        }


@pytest.fixture(autouse=True)
def reset_payment_event_idempotency():
    """Swap the handler's lock + result-cache singletons for fakeredis-backed
    instances and tear them down after each test so cross-test pollution is
    impossible (issue #378)."""
    import fakeredis.aioredis

    from core.distributed_lock import DistributedLock
    from core.redis_cache import RedisCache

    server = fakeredis.aioredis.FakeServer()
    lock_client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    cache_client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)

    payment_handlers.set_event_idempotency_backends(
        lock=DistributedLock(
            "payment_service",
            client=lock_client,
            default_ttl_seconds=120,
        ),
        result_cache=RedisCache(
            "payment_event_results",
            client=cache_client,
            default_ttl=900,
        ),
    )
    yield
    payment_handlers._event_lock = None
    payment_handlers._event_result_cache = None


def _make_payment_service(repository) -> MagicMock:
    payment_service = MagicMock()
    payment_service.repository = repository
    payment_service.create_payment_intent = AsyncMock()
    payment_service.calculate_prorated_refund = AsyncMock(return_value=0)
    repository.get_user_subscriptions = AsyncMock(return_value=[])
    repository.cancel_user_payment_intents = AsyncMock(return_value=0)
    repository.anonymize_user_payment_history = AsyncMock(return_value=None)
    return payment_service


# ---------------------------------------------------------------------------
# handle_order_created
# ---------------------------------------------------------------------------


class TestOrderCreatedClaim:
    async def test_first_delivery_runs_and_marks_completed(self):
        repo = _FakeClaimRepository()
        payment_service = _make_payment_service(repo)

        await payment_handlers.handle_order_created(
            {
                "order_id": "order_001",
                "user_id": "user_123",
                "total_amount": "12.34",
                "currency": "USD",
            },
            payment_service,
        )

        payment_service.create_payment_intent.assert_awaited_once()
        # Claim row is keyed by the event id resolver — order_id is used
        # because event_data has no envelope id.
        assert "payment:order_created:order_001" in repo.claims
        assert repo.claims["payment:order_created:order_001"]["status"] == "completed"

    async def test_replay_after_completion_is_short_circuited(self):
        """Crash-and-replay: a second delivery with the same event id must
        not re-create the payment intent even after the lock TTL window
        has passed (simulated by clearing the result cache)."""
        repo = _FakeClaimRepository()
        payment_service = _make_payment_service(repo)

        await payment_handlers.handle_order_created(
            {
                "order_id": "order_replay",
                "user_id": "user_123",
                "total_amount": "12.34",
                "currency": "USD",
            },
            payment_service,
        )
        assert payment_service.create_payment_intent.await_count == 1

        # Simulate TTL expiry by dropping the cached result and clearing
        # the lock so the second delivery acquires a fresh lock — the
        # durable claim is the only remaining defence.
        payment_handlers._event_result_cache._client.flushall = AsyncMock()
        await payment_handlers._event_result_cache._client.delete(
            "payment_event_results:order_created:order_replay"
        )

        await payment_handlers.handle_order_created(
            {
                "order_id": "order_replay",
                "user_id": "user_123",
                "total_amount": "12.34",
                "currency": "USD",
            },
            payment_service,
        )

        # Still only one payment intent was created — the durable claim
        # short-circuited the second pass.
        assert payment_service.create_payment_intent.await_count == 1

    async def test_handler_runs_even_without_repository_claim_contract(self):
        """A repository missing the claim methods (e.g. a legacy fake)
        must not crash the handler — it falls back to lock-only."""
        payment_service = MagicMock()
        payment_service.repository = MagicMock(spec=[])  # no claim methods
        payment_service.create_payment_intent = AsyncMock()

        await payment_handlers.handle_order_created(
            {
                "order_id": "order_legacy",
                "user_id": "user_123",
                "total_amount": "12.34",
                "currency": "USD",
            },
            payment_service,
        )

        payment_service.create_payment_intent.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle_user_deleted
# ---------------------------------------------------------------------------


class TestUserDeletedClaim:
    async def test_first_delivery_runs_full_cleanup(self):
        repo = _FakeClaimRepository()
        payment_service = _make_payment_service(repo)

        await payment_handlers.handle_user_deleted(
            {"user_id": "user_42"},
            payment_service,
        )

        repo.get_user_subscriptions.assert_awaited_once()
        repo.cancel_user_payment_intents.assert_awaited_once()
        repo.anonymize_user_payment_history.assert_awaited_once()
        assert repo.claims["payment:user_deleted:user_42"]["status"] == "completed"

    async def test_replay_does_not_double_anonymize(self):
        repo = _FakeClaimRepository()
        payment_service = _make_payment_service(repo)

        await payment_handlers.handle_user_deleted(
            {"user_id": "user_99"},
            payment_service,
        )
        assert repo.anonymize_user_payment_history.await_count == 1

        # Drop the cached result so the replay actually re-acquires the
        # lock — simulating a TTL-driven retry.
        await payment_handlers._event_result_cache._client.delete(
            "payment_event_results:user_deleted_payment:user_99"
        )

        await payment_handlers.handle_user_deleted(
            {"user_id": "user_99"},
            payment_service,
        )

        # Anonymisation must run exactly once across both deliveries.
        assert repo.anonymize_user_payment_history.await_count == 1

    async def test_failed_handler_marks_claim_failed_for_retry(self):
        repo = _FakeClaimRepository()
        payment_service = _make_payment_service(repo)
        repo.get_user_subscriptions = AsyncMock(side_effect=RuntimeError("boom"))

        await payment_handlers.handle_user_deleted(
            {"user_id": "user_oops"},
            payment_service,
        )

        # The claim is left as ``failed`` so a retry can pick it up.
        assert repo.claims["payment:user_deleted:user_oops"]["status"] == "failed"
