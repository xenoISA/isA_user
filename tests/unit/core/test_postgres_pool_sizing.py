"""
Unit tests for replica-aware Postgres pool sizing (epic #345 / story #346).

Covers ``core.postgres_client.compute_pool_size`` and the constructor's
resolution of explicit args vs env-var overrides. The underlying asyncpg
pool is never started — we just verify what ``AsyncPostgresClient`` would
receive for ``min_pool_size`` / ``max_pool_size``.
"""

from unittest.mock import MagicMock

import pytest

from core.postgres_client import (
    PostgresClientWrapper,
    _resolve_pool_sizes,
    compute_pool_size,
)


# ---------------------------------------------------------------------------
# compute_pool_size — formula correctness
# ---------------------------------------------------------------------------


class TestComputePoolSize:
    """The formula ``max(floor, base + (replicas - 1) * growth)`` (conservative
    defaults base=2, growth=1, floor=5; capacity bump tracked separately —
    see PR #358 tracking issue)."""

    def test_single_replica_returns_floor(self):
        assert compute_pool_size(replica_count=1, base=5, growth=3) == 5

    def test_two_replicas(self):
        # 5 + (2-1)*3 = 8
        assert compute_pool_size(replica_count=2, base=5, growth=3) == 8

    def test_ten_replicas_matches_acceptance_criterion(self):
        # Story #346 AC: "10 replicas: per-instance pool >= 8".
        # With explicit base=5/growth=3 → 32 (legacy/aspirational sizing
        # available once max_connections is raised).
        assert compute_pool_size(replica_count=10, base=5, growth=3) == 32

    def test_floor_respected_when_base_is_small(self):
        # base=2 with 1 replica would be 2; floor pushes to 5.
        assert compute_pool_size(replica_count=1, base=2, growth=3) == 5

    def test_zero_or_negative_replicas_treated_as_one(self):
        assert compute_pool_size(replica_count=0, base=5, growth=3) == 5
        assert compute_pool_size(replica_count=-3, base=5, growth=3) == 5

    def test_zero_growth_keeps_base(self):
        assert compute_pool_size(replica_count=10, base=8, growth=0) == 8

    def test_custom_floor(self):
        assert compute_pool_size(replica_count=1, base=3, growth=3, floor=10) == 10


class TestComputePoolSizeFromEnv:
    """When called without args, values come from env vars."""

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch):
        for key in ("POD_REPLICA_COUNT", "DB_POOL_BASE", "DB_POOL_GROWTH"):
            monkeypatch.delenv(key, raising=False)
        yield

    def test_defaults_when_unset(self):
        # 1 replica, defaults base=2, growth=1 → max(floor=5, 2) = 5
        assert compute_pool_size() == 5

    def test_reads_pod_replica_count(self, monkeypatch):
        monkeypatch.setenv("POD_REPLICA_COUNT", "4")
        # max(5, 2 + 3*1) = max(5, 5) = 5
        assert compute_pool_size() == 5

    def test_reads_db_pool_base_and_growth(self, monkeypatch):
        monkeypatch.setenv("POD_REPLICA_COUNT", "5")
        monkeypatch.setenv("DB_POOL_BASE", "10")
        monkeypatch.setenv("DB_POOL_GROWTH", "2")
        # 10 + 4*2 = 18
        assert compute_pool_size() == 18

    def test_invalid_int_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("POD_REPLICA_COUNT", "not-a-number")
        # Falls back to default 1 -> floor of 5
        assert compute_pool_size() == 5

    def test_growth_at_high_replicas_meets_floor(self, monkeypatch):
        # Conservative defaults (base=2, growth=1, floor=5): 10 replicas yields
        # max(5, 2 + 9*1) = 11 — above the floor and the story #346 AC of >= 8.
        monkeypatch.setenv("POD_REPLICA_COUNT", "10")
        assert compute_pool_size() >= 8


# ---------------------------------------------------------------------------
# _resolve_pool_sizes — precedence: explicit > legacy env > replica formula
# ---------------------------------------------------------------------------


class TestResolvePoolSizes:
    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch):
        for key in (
            "POD_REPLICA_COUNT",
            "DB_POOL_BASE",
            "DB_POOL_GROWTH",
            "PG_MIN_POOL_SIZE",
            "PG_MAX_POOL_SIZE",
        ):
            monkeypatch.delenv(key, raising=False)
        yield

    def test_explicit_args_take_precedence(self, monkeypatch):
        monkeypatch.setenv("PG_MAX_POOL_SIZE", "99")
        monkeypatch.setenv("POD_REPLICA_COUNT", "10")
        min_size, max_size = _resolve_pool_sizes(explicit_min=3, explicit_max=7)
        assert (min_size, max_size) == (3, 7)

    def test_legacy_env_overrides_replica_formula(self, monkeypatch):
        monkeypatch.setenv("PG_MAX_POOL_SIZE", "12")
        monkeypatch.setenv("PG_MIN_POOL_SIZE", "4")
        monkeypatch.setenv("POD_REPLICA_COUNT", "10")
        # Replica formula would give 32; legacy env wins.
        assert _resolve_pool_sizes(None, None) == (4, 12)

    def test_replica_formula_used_by_default(self, monkeypatch):
        monkeypatch.setenv("POD_REPLICA_COUNT", "3")
        # Conservative defaults (base=2, growth=1, floor=5):
        # max(5, 2 + 2*1) = max(5, 4) = 5
        min_size, max_size = _resolve_pool_sizes(None, None)
        assert max_size == 5
        # Default min: 2 when max >= 4
        assert min_size == 2

    def test_min_clamped_to_max(self):
        # If a caller asks for an absurd min, we clamp it.
        min_size, max_size = _resolve_pool_sizes(explicit_min=50, explicit_max=10)
        assert min_size == 10
        assert max_size == 10


# ---------------------------------------------------------------------------
# Constructor: verify values reach AsyncPostgresClient
# ---------------------------------------------------------------------------


class TestPostgresClientWrapperPoolSizing:
    """The wrapper must pass replica-aware sizes through to AsyncPostgresClient
    without ever opening a real pool."""

    @pytest.fixture(autouse=True)
    def _stub_async_client(self, monkeypatch):
        """Replace AsyncPostgresClient with a mock so __init__ doesn't touch IO."""
        for key in (
            "POD_REPLICA_COUNT",
            "DB_POOL_BASE",
            "DB_POOL_GROWTH",
            "PG_MIN_POOL_SIZE",
            "PG_MAX_POOL_SIZE",
        ):
            monkeypatch.delenv(key, raising=False)

        mock_async_client = MagicMock()
        # config_manager.discover_service is invoked from __init__; stub it.
        mock_config_manager = MagicMock()
        mock_config_manager.return_value.discover_service.return_value = (
            "stub-host",
            5432,
        )
        monkeypatch.setattr(
            "core.postgres_client.AsyncPostgresClient",
            mock_async_client,
        )
        monkeypatch.setattr(
            "core.config_manager.ConfigManager",
            mock_config_manager,
        )
        # Disable the gauge labels().set() call from blowing up if metrics
        # registry isn't fully configured during the test session.
        monkeypatch.setattr(
            "core.postgres_client.PG_POOL_MAX",
            MagicMock(),
        )
        return mock_async_client

    def test_default_uses_replica_formula(self, _stub_async_client, monkeypatch):
        monkeypatch.setenv("POD_REPLICA_COUNT", "4")
        wrapper = PostgresClientWrapper(service_name="test_service")
        # Conservative defaults (base=2, growth=1, floor=5):
        # max(5, 2 + 3*1) = max(5, 5) = 5
        assert wrapper.max_pool_size == 5
        assert wrapper.min_pool_size == 2  # default min when max >= 4
        kwargs = _stub_async_client.call_args.kwargs
        assert kwargs["min_pool_size"] == 2
        assert kwargs["max_pool_size"] == 5

    def test_explicit_override_wins(self, _stub_async_client, monkeypatch):
        monkeypatch.setenv("POD_REPLICA_COUNT", "10")
        wrapper = PostgresClientWrapper(
            service_name="test_service",
            min_pool_size=1,
            max_pool_size=2,
        )
        assert (wrapper.min_pool_size, wrapper.max_pool_size) == (1, 2)

    def test_legacy_env_still_honored(self, _stub_async_client, monkeypatch):
        monkeypatch.setenv("PG_MAX_POOL_SIZE", "9")
        wrapper = PostgresClientWrapper(service_name="test_service")
        assert wrapper.max_pool_size == 9

    def test_pool_grows_when_replica_count_increases(
        self, _stub_async_client, monkeypatch
    ):
        """Direct expression of the integration AC: pool grows with env."""
        monkeypatch.setenv("POD_REPLICA_COUNT", "1")
        small = PostgresClientWrapper(service_name="svc_small").max_pool_size

        monkeypatch.setenv("POD_REPLICA_COUNT", "10")
        large = PostgresClientWrapper(service_name="svc_large").max_pool_size

        assert large > small
        assert small >= 5  # floor
        assert large >= 8  # AC bound from story #346
