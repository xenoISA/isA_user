"""
PostgreSQL Client Wrapper for isA Cloud Platform

Centralized PostgreSQL client wrapper using AsyncPostgresClient from isa_common.
Provides service discovery integration and consistent database access pattern.

Pool sizing
-----------
Pool size scales with the deployment's replica count so HPA scale-out does
not exhaust the per-pod pool:

    max_pool_size = max(POOL_FLOOR,
                        DB_POOL_BASE + (POD_REPLICA_COUNT - 1) * DB_POOL_GROWTH)

Defaults: base=2, growth=1, floor=5. With 1 replica → 5 connections per pod
(floor); with 10 replicas → max(5, 2 + 9*1) = 11 per pod.

Cross-service connection budget
-------------------------------
isA's user platform runs ~35 microservices. Each pod opens its own pool, so
the per-Postgres connection cost is ``services * replicas * max_pool_size``.
The defaults above were chosen to stay close to the (conservative) shared
budget at ``replicas=2`` (~280 connections) while still letting individual
services grow under HPA load. Before raising ``DB_POOL_BASE`` /
``DB_POOL_GROWTH`` or pushing ``replicas`` past the values in the chart,
verify the Postgres ``max_connections`` ceiling — Postgres defaults to 100
and our cluster has historically run close to that ceiling. The capacity
plan (PgBouncer fronting + Postgres ``max_connections`` raise) is tracked
in `docs/runbooks/hpa-capacity.md` (pending — see issue #353) and the
follow-up infra issue linked from PR #358. Operators may override via
constructor args or the legacy ``PG_MIN_POOL_SIZE`` / ``PG_MAX_POOL_SIZE``
env vars while that work lands.

Pool utilization metrics (`pg_pool_in_use`, `pg_pool_idle`, `pg_pool_waiters`)
are exported via the standard isa_common metrics registry, scraped by
Prometheus from each service's `/metrics` endpoint.

Usage:
    from core.postgres_client import get_postgres_client

    # Get client instance
    db = await get_postgres_client("album_service")

    # Execute queries
    async with db:
        result = await db.query("SELECT * FROM albums WHERE user_id = $1", [user_id])
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from isa_common import AsyncPostgresClient
from isa_common.metrics import create_gauge

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pool sizing
# ---------------------------------------------------------------------------

# Floor: even at replica_count=1 we keep at least this many connections so
# bursty endpoints don't queue under low load. Aligned with epic #346.
_POOL_SIZE_FLOOR = 5


def _read_int_env(name: str, default: int) -> int:
    """Parse an int env var, falling back to ``default`` on missing/invalid."""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid integer for env %s=%r, falling back to default=%d",
            name,
            raw,
            default,
        )
        return default


def compute_pool_size(
    replica_count: Optional[int] = None,
    base: Optional[int] = None,
    growth: Optional[int] = None,
    floor: int = _POOL_SIZE_FLOOR,
) -> int:
    """Compute per-pod ``max_pool_size`` from replica count and growth factor.

    Formula::

        max_pool_size = max(floor, base + (replica_count - 1) * growth)

    All inputs default to env vars (``POD_REPLICA_COUNT``, ``DB_POOL_BASE``,
    ``DB_POOL_GROWTH``) so this can be called without arguments.
    """
    if replica_count is None:
        replica_count = _read_int_env("POD_REPLICA_COUNT", 1)
    if base is None:
        # Default lowered from 5 → 2 to stay within the cross-service Postgres
        # connection budget (~35 services, ~100 max_connections). See module
        # docstring and the tracking issue referenced in PR #358.
        base = _read_int_env("DB_POOL_BASE", 2)
    if growth is None:
        # Default lowered from 3 → 1 for the same reason.
        growth = _read_int_env("DB_POOL_GROWTH", 1)

    # Negative inputs are nonsensical; clamp to 1 replica / 0 growth so the
    # formula degenerates to ``max(floor, base)`` instead of going negative.
    replica_count = max(1, replica_count)
    base = max(0, base)
    growth = max(0, growth)
    floor = max(1, floor)

    computed = base + (replica_count - 1) * growth
    return max(floor, computed)


def _resolve_pool_sizes(
    explicit_min: Optional[int],
    explicit_max: Optional[int],
) -> Tuple[int, int]:
    """Resolve ``(min_pool_size, max_pool_size)`` honoring legacy overrides.

    Precedence (highest first):
      1. Explicit constructor args (used by tests / specialized callers)
      2. Legacy ``PG_MIN_POOL_SIZE`` / ``PG_MAX_POOL_SIZE`` env vars
      3. Replica-aware formula via :func:`compute_pool_size`

    ``min_pool_size`` is held to a small constant (``1..2``) so idle pods
    don't pin large numbers of Postgres connections.
    """
    legacy_max = os.getenv("PG_MAX_POOL_SIZE")
    legacy_min = os.getenv("PG_MIN_POOL_SIZE")

    if explicit_max is not None:
        max_size = explicit_max
    elif legacy_max not in (None, ""):
        max_size = _read_int_env("PG_MAX_POOL_SIZE", compute_pool_size())
    else:
        max_size = compute_pool_size()

    if explicit_min is not None:
        min_size = explicit_min
    elif legacy_min not in (None, ""):
        min_size = _read_int_env("PG_MIN_POOL_SIZE", 1)
    else:
        min_size = 2 if max_size >= 4 else 1

    # Guarantee min <= max regardless of how callers configured things.
    if min_size > max_size:
        min_size = max_size
    return min_size, max_size


# ---------------------------------------------------------------------------
# Pool utilization metrics (Prometheus gauges)
# ---------------------------------------------------------------------------

# These are module-level singletons so all wrappers within a service push to
# the same metric series. ``service`` distinguishes call sites within a pod.
PG_POOL_IN_USE = create_gauge(
    "pg_pool_in_use",
    "Postgres connections currently checked out by the application",
    ["service"],
)
PG_POOL_IDLE = create_gauge(
    "pg_pool_idle",
    "Postgres connections sitting idle in the pool",
    ["service"],
)
PG_POOL_WAITERS = create_gauge(
    "pg_pool_waiters",
    "Tasks waiting to acquire a Postgres connection",
    ["service"],
)
PG_POOL_MAX = create_gauge(
    "pg_pool_max_size",
    "Configured per-pod max pool size for Postgres",
    ["service"],
)


def _safe_pool_attr(pool: Any, *candidates: str) -> Optional[int]:
    """Return the first attribute/method result that yields an int."""
    for name in candidates:
        target = getattr(pool, name, None)
        if target is None:
            continue
        try:
            value = target() if callable(target) else target
        except Exception:  # pragma: no cover - defensive only
            continue
        if isinstance(value, int):
            return value
    return None


def sample_pool_metrics(client: AsyncPostgresClient, service_name: str) -> None:
    """Read live pool stats off the asyncpg pool and update gauges.

    Best-effort: if the underlying client hasn't connected yet (no pool) or
    the pool object doesn't expose the expected accessors, this is a no-op.
    Metrics are labelled by ``service`` for cross-service dashboards.
    """
    pool = getattr(client, "_pool", None)
    if pool is None:
        return

    size = _safe_pool_attr(pool, "get_size", "size")
    idle = _safe_pool_attr(pool, "get_idle_size", "idle_size")
    if size is not None and idle is not None:
        in_use = max(0, size - idle)
        PG_POOL_IN_USE.labels(service=service_name).set(in_use)
        PG_POOL_IDLE.labels(service=service_name).set(idle)

    # asyncpg exposes ``_queue`` as the waiter queue; fall back gracefully.
    waiters = _safe_pool_attr(pool, "get_waiters_count")
    if waiters is None:
        queue = getattr(pool, "_queue", None)
        if queue is not None and hasattr(queue, "qsize"):
            try:
                waiters = queue.qsize()
            except Exception:  # pragma: no cover
                waiters = None
    if waiters is not None:
        PG_POOL_WAITERS.labels(service=service_name).set(waiters)


class PostgresClientWrapper:
    """
    PostgreSQL client wrapper with service discovery integration.

    Wraps AsyncPostgresClient from isa_common and provides:
    - Service discovery for host/port configuration
    - Replica-aware pool sizing (epic #345 / story #346)
    - Consistent initialization pattern
    - Environment variable fallbacks
    """

    def __init__(
        self,
        service_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        min_pool_size: Optional[int] = None,
        max_pool_size: Optional[int] = None,
    ):
        """
        Initialize PostgreSQL client wrapper.

        Args:
            service_name: Name of the service using this client
            host: PostgreSQL host (defaults to env/service discovery)
            port: PostgreSQL port (defaults to 5432)
            database: Database name (defaults to 'postgres')
            username: Database username
            password: Database password
            user_id: User ID for multi-tenant operations
            organization_id: Organization ID for multi-tenant operations
            min_pool_size: Optional explicit minimum pool size (else replica-aware default)
            max_pool_size: Optional explicit maximum pool size (else replica-aware default)
        """
        from core.config_manager import ConfigManager

        self.service_name = service_name

        # Use ConfigManager for service discovery
        config = ConfigManager(service_name)
        discovered_host, discovered_port = config.discover_service(
            service_name="postgres_service",
            default_host="postgres",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )

        # Apply overrides
        self.host = host or discovered_host
        self.port = port or discovered_port
        self.database = database or os.getenv("POSTGRES_DB", "postgres")
        self.username = username or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "")
        self.user_id = user_id or service_name
        self.organization_id = organization_id or os.getenv("ORGANIZATION_ID", "default-org")

        # Pool sizing scales with replica count via Downward API (epic #345/#346).
        self._min_pool_size, self._max_pool_size = _resolve_pool_sizes(
            min_pool_size, max_pool_size
        )

        # Create underlying client
        self._client = AsyncPostgresClient(
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
            user_id=self.user_id,
            organization_id=self.organization_id,
            min_pool_size=self._min_pool_size,
            max_pool_size=self._max_pool_size,
        )
        PG_POOL_MAX.labels(service=service_name).set(self._max_pool_size)

        logger.info(
            "PostgreSQL client initialized for %s: %s:%s/%s (pool min=%d max=%d)",
            service_name,
            self.host,
            self.port,
            self.database,
            self._min_pool_size,
            self._max_pool_size,
        )

    @property
    def client(self) -> AsyncPostgresClient:
        """Get underlying AsyncPostgresClient"""
        return self._client

    @property
    def min_pool_size(self) -> int:
        """Effective minimum pool size in use."""
        return self._min_pool_size

    @property
    def max_pool_size(self) -> int:
        """Effective maximum pool size in use."""
        return self._max_pool_size

    def sample_metrics(self) -> None:
        """Refresh pool gauges from the live asyncpg pool."""
        sample_pool_metrics(self._client, self.service_name)

    async def __aenter__(self):
        """Async context manager entry"""
        await self._client.__aenter__()
        self.sample_metrics()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.sample_metrics()
        await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def health_check(self) -> Optional[Dict]:
        """Check database health"""
        result = await self._client.health_check()
        self.sample_metrics()
        return result

    async def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        try:
            return await self._client.query(sql, params)
        finally:
            self.sample_metrics()

    async def query_row(self, sql: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute query and return single row"""
        try:
            return await self._client.query_row(sql, params)
        finally:
            self.sample_metrics()

    async def execute(self, sql: str, params: Optional[List[Any]] = None) -> bool:
        """Execute SQL statement"""
        try:
            return await self._client.execute(sql, params)
        finally:
            self.sample_metrics()

    async def execute_many(self, sql: str, params_list: List[List[Any]]) -> bool:
        """Execute SQL statement with multiple parameter sets"""
        try:
            return await self._client.execute_many(sql, params_list)
        finally:
            self.sample_metrics()

    async def close(self):
        """Close connection"""
        await self._client.close()


# Singleton instances per service
_postgres_clients: Dict[str, PostgresClientWrapper] = {}
_postgres_client_lock = asyncio.Lock()


async def get_postgres_client(
    service_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    **kwargs,
) -> PostgresClientWrapper:
    """
    Get or create PostgreSQL client for a service.

    Args:
        service_name: Service name
        host: Optional host override
        port: Optional port override
        database: Optional database override
        **kwargs: Additional client options

    Returns:
        PostgresClientWrapper instance
    """
    global _postgres_clients

    if service_name in _postgres_clients:
        return _postgres_clients[service_name]

    async with _postgres_client_lock:
        if service_name not in _postgres_clients:
            client = PostgresClientWrapper(
                service_name=service_name,
                host=host,
                port=port,
                database=database,
                **kwargs,
            )
            _postgres_clients[service_name] = client

    return _postgres_clients[service_name]


__all__ = [
    "PostgresClientWrapper",
    "compute_pool_size",
    "get_postgres_client",
    "sample_pool_metrics",
    "PG_POOL_IN_USE",
    "PG_POOL_IDLE",
    "PG_POOL_WAITERS",
    "PG_POOL_MAX",
]
