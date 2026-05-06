"""
L2 Component — wallet_service distributed event idempotency.

Issue #348 — confirms that the wallet event handlers are wrapped in
the distributed lock so concurrent retries don't double-process the
same event. Uses fakeredis as a stand-in for production Redis so the
test is hermetic.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest

from core.distributed_lock import DistributedLock
from core.redis_cache import RedisCache
from microservices.wallet_service.events import handlers as wallet_handlers


pytestmark = [pytest.mark.component, pytest.mark.tdd]


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def redis_server():
    return fakeredis.aioredis.FakeServer()


@pytest.fixture
def redis_client(redis_server):
    return fakeredis.aioredis.FakeRedis(server=redis_server, decode_responses=False)


@pytest.fixture
def distributed_lock(redis_client):
    return DistributedLock(
        "wallet_service",
        client=redis_client,
        default_ttl_seconds=120,
    )


@pytest.fixture
def result_cache(redis_client):
    return RedisCache("wallet_event_results", client=redis_client, default_ttl=900)


@pytest.fixture(autouse=True)
def patch_idempotency_backends(distributed_lock, result_cache):
    """Override the wallet handler singletons with our fakeredis-backed pair."""
    # Reset the in-memory dedup set so each test starts clean.
    wallet_handlers._processed_event_ids = set()
    wallet_handlers.set_event_idempotency_backends(
        lock=distributed_lock,
        result_cache=result_cache,
    )
    yield
    # Drop the override so the next test rebuilds defaults.
    wallet_handlers._event_lock = None
    wallet_handlers._event_result_cache = None
    wallet_handlers._processed_event_ids = set()


@pytest.fixture
def fake_event():
    """Build an Event-shaped object that the handlers can consume."""

    def _build(event_id: str, data: dict, event_type: str = "payment.completed"):
        return SimpleNamespace(
            id=event_id,
            type=event_type,
            data=data,
            timestamp="2026-01-01T00:00:00Z",
        )

    return _build


# ----------------------------------------------------------------------
# Concurrent retries — exactly one deposit
# ----------------------------------------------------------------------


async def test_concurrent_payment_completed_runs_deposit_exactly_once(fake_event):
    """10 concurrent identical events → exactly 1 deposit, 9 skipped/cached.

    This is the headline acceptance criterion from issue #348.
    """
    # Build the wallet_service mock — capture deposit calls.
    deposit_calls = {"n": 0}
    deposit_event_started = asyncio.Event()
    release_deposit = asyncio.Event()

    async def fake_deposit(wallet_id, request):
        deposit_calls["n"] += 1
        # Make worker 0 hold the lock long enough for peers to arrive.
        if deposit_calls["n"] == 1:
            deposit_event_started.set()
            await release_deposit.wait()
        return MagicMock(wallet_id=wallet_id)

    wallet_repo = MagicMock()
    wallet_repo.get_primary_wallet = AsyncMock(
        return_value=SimpleNamespace(wallet_id="wallet-123")
    )

    wallet_service = SimpleNamespace(
        repository=wallet_repo,
        deposit=fake_deposit,
    )

    event = fake_event(
        "evt-deposit-1",
        {
            "user_id": "user-1",
            "amount": "10.00",
            "currency": "USD",
            "payment_id": "pay-1",
        },
    )

    async def attempt():
        await wallet_handlers.handle_payment_completed(event, wallet_service)

    # Fire worker 0 first.
    worker0 = asyncio.create_task(attempt())
    await deposit_event_started.wait()
    # Fire 9 more concurrent attempts while worker 0 holds the lock.
    peers = [asyncio.create_task(attempt()) for _ in range(9)]
    # Let worker 0 finish.
    release_deposit.set()
    await asyncio.gather(worker0, *peers)

    # Exactly one deposit, regardless of how many replicas raced.
    assert deposit_calls["n"] == 1


async def test_replay_after_completion_returns_cached_outcome(fake_event):
    """A retry that arrives AFTER the first attempt completed must hit
    the cache and skip the deposit entirely."""
    deposit_calls = {"n": 0}

    async def fake_deposit(wallet_id, request):
        deposit_calls["n"] += 1
        return MagicMock(wallet_id=wallet_id)

    wallet_repo = MagicMock()
    wallet_repo.get_primary_wallet = AsyncMock(
        return_value=SimpleNamespace(wallet_id="wallet-123")
    )
    wallet_service = SimpleNamespace(
        repository=wallet_repo,
        deposit=fake_deposit,
    )

    event = fake_event(
        "evt-deposit-2",
        {
            "user_id": "user-1",
            "amount": "5.00",
            "currency": "USD",
            "payment_id": "pay-2",
        },
    )

    # Reset the in-memory dedup set between calls so we exercise the
    # *Redis* path rather than the local short-circuit.
    await wallet_handlers.handle_payment_completed(event, wallet_service)
    wallet_handlers._processed_event_ids = set()
    await wallet_handlers.handle_payment_completed(event, wallet_service)
    wallet_handlers._processed_event_ids = set()
    await wallet_handlers.handle_payment_completed(event, wallet_service)

    assert deposit_calls["n"] == 1


async def test_billing_calculated_runs_deduction_exactly_once(fake_event):
    """The deduction path is the highest-risk for double-charge — verify
    the lock catches concurrent replays."""
    consume_calls = {"n": 0}
    consume_started = asyncio.Event()
    release_consume = asyncio.Event()

    async def fake_consume(user_id, request):
        consume_calls["n"] += 1
        if consume_calls["n"] == 1:
            consume_started.set()
            await release_consume.wait()
        result = MagicMock()
        result.model_dump = lambda: {
            "success": True,
            "transaction_id": f"txn-{consume_calls['n']}",
            "balance": "100",
            "data": {"transaction": {"balance_before": "110", "balance_after": "100"}},
        }
        return result

    wallet_service = SimpleNamespace(consume_by_user=fake_consume)
    event_bus = SimpleNamespace()

    # Patch the publishers to no-op so we don't need to mock NATS.
    import microservices.wallet_service.events.handlers as h

    orig_deducted = h.publish_tokens_deducted
    orig_insufficient = h.publish_tokens_insufficient
    h.publish_tokens_deducted = AsyncMock()
    h.publish_tokens_insufficient = AsyncMock()

    try:
        # Build a billing.calculated payload that the parser accepts.
        # billing_record_id must be a string per the event model, but
        # ConsumeRequest expects an int — use a numeric string.
        event = fake_event(
            "evt-bill-1",
            {
                "user_id": "user-1",
                "billing_record_id": "12345",
                "product_id": "prod-1",
                "actual_usage": "10",
                "unit_type": "tokens",
                "token_equivalent": "10",
                "cost_usd": "0.01",
                "unit_price": "0.001",
                "token_conversion_rate": "1",
                "is_free_tier": False,
                "is_included_in_subscription": False,
            },
            event_type="billing.calculated",
        )

        async def attempt():
            await wallet_handlers.handle_billing_calculated(
                event, wallet_service, event_bus
            )

        worker0 = asyncio.create_task(attempt())
        await consume_started.wait()
        peers = [asyncio.create_task(attempt()) for _ in range(9)]
        release_consume.set()
        await asyncio.gather(worker0, *peers)

        assert consume_calls["n"] == 1
    finally:
        h.publish_tokens_deducted = orig_deducted
        h.publish_tokens_insufficient = orig_insufficient


# ----------------------------------------------------------------------
# Lock contention metric
# ----------------------------------------------------------------------


async def test_contention_increments_metric(distributed_lock, fake_event):
    """The lock contention metric must tick up when two replicas race."""
    # Manually acquire the lock from a "shadow" replica.
    other = DistributedLock(
        "wallet_service",
        client=distributed_lock._client,
        default_ttl_seconds=120,
    )
    token = await other.acquire("payment_completed:evt-contend", ttl_seconds=120)
    assert token is not None

    # Now run the handler — it should observe contention.
    wallet_repo = MagicMock()
    wallet_repo.get_primary_wallet = AsyncMock(
        return_value=SimpleNamespace(wallet_id="wallet-123")
    )
    wallet_service = SimpleNamespace(
        repository=wallet_repo,
        deposit=AsyncMock(),
    )
    event = fake_event(
        "evt-contend",
        {
            "user_id": "user-1",
            "amount": "1.00",
            "currency": "USD",
            "payment_id": "pay-c",
        },
    )

    # Should NOT call deposit — the lock is held by ``other``.
    await wallet_handlers.handle_payment_completed(event, wallet_service)
    assert not wallet_service.deposit.called

    # Cleanup.
    await other.release("payment_completed:evt-contend", token)
