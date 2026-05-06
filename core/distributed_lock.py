"""
Redis-based distributed lock primitive — issue #348.

Why this exists
---------------
HPA scale-out broke per-replica idempotency in the event handlers. Two
``wallet_service`` / ``billing_service`` / ``payment_service`` replicas can
receive the same ``event_id`` concurrently (NATS at-least-once + retries +
multiple consumers), and the existing in-memory ``_processed_event_ids``
sets are per-pod — they don't catch the duplicate. The result is
double-charges / duplicate billing rows / duplicate deposits.

What this provides
------------------
* :class:`DistributedLock` — async ``acquire(key, ttl_seconds)`` /
  ``release(token)`` over Redis ``SET key token NX EX <ttl>``. The
  ``NX``+``EX`` pair is atomic, so two replicas racing on the same key
  cannot both win.
* Token-based release. ``acquire`` returns a unique token; ``release``
  runs a Lua compare-and-delete so a coroutine can never release
  another holder's lock (e.g. after a TTL-driven expiry handed it to
  someone else).
* :meth:`DistributedLock.guard` — ``async with`` context manager that
  acquires on entry and releases on exit, plus a result cache so
  retries of the same event ID short-circuit to the previously
  computed result (the "idempotent retry contract").
* Half-open recovery — same pattern as :mod:`core.redis_cache`. On
  Redis blip the latch trips; after a cooldown a single probe is
  attempted before reads / writes resume.
* Fail-closed semantics. A Redis outage raises
  :class:`DistributedLockError` rather than silently allowing
  unsynchronised processing. Correctness > availability for
  charge / billing / deposit handlers (see issue #348 ACs).

What this does NOT provide
--------------------------
* **Two-phase commit across DB + lock.** A handler that acquires the
  lock, writes to its DB, then crashes between handler completion and
  lock release has the same correctness as today: the DB row is
  committed and the lock TTL eventually frees the key. **There is a
  per-service asymmetry callers MUST understand:**

  - ``billing_service`` has a DB-level second-line defence
    (``billing_repository.claim_event_processing`` materialises a
    durable claim row keyed by the event id). A crash + TTL-driven
    replay re-runs the handler, but the DB claim short-circuits the
    second pass before any duplicate billing.
  - ``wallet_service`` and ``payment_service`` currently rely on the
    distributed lock alone. If a worker crashes after the DB commit
    but before the lock is released, NATS replay after the lock TTL
    expires will re-cancel / re-refund / re-deposit. The window for
    this is bounded by the lock TTL (default 120s; see
    ``<SERVICE>_EVENT_LOCK_TTL_SECONDS``).

  Operational implications:

  - Keep lock TTL conservative — it is the dedupe window for those
    two services until DB-level claims are added.
  - Monitor ``event_lock_acquires_total`` for retry storms; sudden
    growth past expected event rate is the leading indicator of
    crash-and-replay duplicate processing.
  - Adding a DB-level claim to ``wallet_service`` and
    ``payment_service`` is tracked in issue #378 as a follow-up to
    #348 (rather than expanding the scope of #348 itself).

  Same boundary as PR #357's revoke fail-closed semantics.
* **Redlock multi-master.** Single Redis is sufficient per the issue
  scope. If/when we move to Redis Sentinel, swap the client builder
  here without touching call sites.

Idempotent retry contract
-------------------------
Callers wrap their event handler with::

    async with DistributedLock(redis_client, namespace=service_name).guard(
        key=event_id,
        ttl_seconds=120,
        result_cache=cache,  # core.redis_cache.RedisCache
    ) as outcome:
        if outcome.cached_result is not None:
            return outcome.cached_result
        result = await do_real_work()
        outcome.set_result(result)
        return result

Semantics:

* First acquire wins; the handler does the work and caches the result
  before the ``async with`` exits.
* Concurrent acquires of the same key see ``LockContended`` and either
  spin briefly until the first holder publishes the cached result, or
  return without doing the work (caller decides).
* Lock auto-expires after ``ttl_seconds`` if the holder crashes — the
  next replay re-acquires and re-runs (or, if the prior holder finished
  the DB write, the DB-level idempotency claim short-circuits).
* Releasing with the matching token is the only path that frees the
  lock early; lost-token releases are rejected.

Reuses :mod:`core.redis_cache` for client construction, URL resolution,
and the half-open recovery primitives so we don't duplicate connection
management.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# Re-export the URL resolver and the lazy client builder from redis_cache
# so adopters import from a single place. distributed_lock IS part of
# the same Redis-client story, not a separate consumer.
from core.redis_cache import resolve_cache_redis_url

logger = logging.getLogger(__name__)

__all__ = [
    "DistributedLock",
    "DistributedLockError",
    "LockAcquireTimeout",
    "LockContended",
    "LockOutcome",
    "build_distributed_lock",
]


# ----------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------


class DistributedLockError(RuntimeError):
    """Raised when the lock layer cannot guarantee mutual exclusion.

    All other lock-specific errors inherit from this so callers can
    ``except DistributedLockError`` and fail closed (return 503,
    do not process the event).
    """


class LockAcquireTimeout(DistributedLockError):
    """Raised when acquire() exhausts its retry budget."""


class LockContended(DistributedLockError):
    """Raised when another holder owns the lock and the caller chose
    not to wait."""


# ----------------------------------------------------------------------
# Metrics — best-effort, no-op shim when isa_common.metrics is absent.
# Mirrors the pattern from core.postgres_client and core.redis_cache.
# ----------------------------------------------------------------------

try:
    from isa_common.metrics import create_counter  # type: ignore[attr-defined]

    LOCK_CONTENTION = create_counter(
        "event_lock_contention_total",
        "Total times an event handler observed a contended distributed lock",
        ["service"],
    )
    LOCK_ACQUIRES = create_counter(
        "event_lock_acquires_total",
        "Total successful distributed lock acquisitions",
        ["service"],
    )
    LOCK_ERRORS = create_counter(
        "event_lock_errors_total",
        "Total distributed lock errors (Redis unavailable, latch tripped)",
        ["service", "operation"],
    )
except Exception:  # pragma: no cover - exercised when isa_common is absent

    class _NoopCounter:
        def labels(self, *_args: Any, **_kwargs: Any) -> "_NoopCounter":
            return self

        def inc(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    LOCK_CONTENTION = _NoopCounter()
    LOCK_ACQUIRES = _NoopCounter()
    LOCK_ERRORS = _NoopCounter()


# ----------------------------------------------------------------------
# Lua scripts
# ----------------------------------------------------------------------

# Compare-and-delete: only delete if the stored token matches ours.
# Returns 1 if the key was deleted (we owned the lock), 0 otherwise
# (someone else owns it, or it already expired).
_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""

# Compare-and-extend: only refresh TTL if the token matches ours.
# Useful for long-running handlers that want to keep the lock alive.
_EXTEND_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('pexpire', KEYS[1], ARGV[2])
else
    return 0
end
"""


# ----------------------------------------------------------------------
# Outcome dataclass — passed to the ``guard`` context manager.
# ----------------------------------------------------------------------


@dataclass
class LockOutcome:
    """Per-acquire context exposed by :meth:`DistributedLock.guard`.

    The handler writes its result via :meth:`set_result` so that subsequent
    retries of the same event ID return the cached value without
    re-running the work.
    """

    key: str
    token: str
    cached_result: Any = None
    """Populated when the result cache already has an entry for ``key``.

    A non-``None`` value means the work was already done by an earlier
    attempt — the handler should return ``cached_result`` and skip
    re-processing.
    """

    is_cached: bool = False
    _result: Any = field(default=None, repr=False)
    _result_set: bool = field(default=False, repr=False)

    def set_result(self, value: Any) -> None:
        """Record the handler's result so it gets cached on exit."""
        self._result = value
        self._result_set = True


# ----------------------------------------------------------------------
# DistributedLock
# ----------------------------------------------------------------------


class DistributedLock:
    """Async distributed lock backed by Redis ``SET NX EX``.

    Construct one ``DistributedLock`` per service (the ``namespace``
    keeps keys from colliding across services that share a Redis
    instance). Then either:

    * call :meth:`acquire` / :meth:`release` directly, or
    * use :meth:`guard` as an ``async with`` for the idempotent-retry
      contract documented in the module docstring.
    """

    DEFAULT_RECOVERY_COOLDOWN_SECONDS: float = 30.0

    def __init__(
        self,
        namespace: str,
        client: Any = None,
        *,
        url: Optional[str] = None,
        default_ttl_seconds: int = 60,
        service_label: Optional[str] = None,
        recovery_cooldown_seconds: Optional[float] = None,
    ):
        if not namespace:
            raise ValueError("DistributedLock requires a non-empty namespace")
        self.namespace = namespace
        # ``service_label`` is what shows up on the metric. Default to
        # the namespace because that's almost always the service name.
        self.service_label = service_label or namespace
        self.default_ttl_seconds = default_ttl_seconds
        self._client = client
        self._url = url
        self._available: bool = client is not None or bool(url)
        self._healthy: bool = self._available
        self._recovery_cooldown: float = (
            recovery_cooldown_seconds
            if recovery_cooldown_seconds is not None
            else self.DEFAULT_RECOVERY_COOLDOWN_SECONDS
        )
        self._unhealthy_since: Optional[float] = None
        self._recovery_lock = asyncio.Lock()

    # -- Connection management -----------------------------------------

    async def _ensure_client(self) -> Any:
        """Return an async redis client, building one lazily from URL.

        Raises :class:`DistributedLockError` when no client is
        configured. The caller MUST treat that as fail-closed — we do
        not silently degrade because the entire point of the lock is
        correctness.
        """
        if self._client is not None:
            return self._client
        if not self._url:
            LOCK_ERRORS.labels(service=self.service_label, operation="connect").inc()
            raise DistributedLockError(
                f"distributed_lock({self.namespace}): no Redis client / URL "
                "configured; refusing to silently skip the lock"
            )
        try:
            import redis.asyncio as redis_async  # local — keep redis optional

            self._client = redis_async.from_url(self._url, decode_responses=False)
            return self._client
        except Exception as exc:
            LOCK_ERRORS.labels(service=self.service_label, operation="connect").inc()
            self._available = False
            self._healthy = False
            raise DistributedLockError(
                f"distributed_lock({self.namespace}): failed to construct "
                f"Redis client: {exc}"
            ) from exc

    # -- Health / recovery ---------------------------------------------

    def _mark_unhealthy(self) -> None:
        now = time.monotonic()
        self._healthy = False
        if self._unhealthy_since is None:
            self._unhealthy_since = now

    def _should_attempt_recovery(self) -> bool:
        if self._healthy:
            return False
        if self._unhealthy_since is None:
            return True
        return (time.monotonic() - self._unhealthy_since) >= self._recovery_cooldown

    async def _attempt_recovery(self, client: Any) -> bool:
        if self._healthy:
            return True
        if self._recovery_lock.locked():
            return False
        async with self._recovery_lock:
            if self._healthy:
                return True
            try:
                pong = await client.ping()
            except Exception as exc:
                self._unhealthy_since = time.monotonic()
                logger.debug(
                    "distributed_lock(%s): recovery probe failed: %s",
                    self.namespace,
                    exc,
                )
                LOCK_ERRORS.labels(
                    service=self.service_label, operation="recovery"
                ).inc()
                return False
            if not pong:
                self._unhealthy_since = time.monotonic()
                return False
            self._healthy = True
            self._unhealthy_since = None
            logger.info(
                "distributed_lock(%s): recovered after probe",
                self.namespace,
            )
            return True

    async def _ensure_healthy(self, client: Any, *, operation: str) -> None:
        """Block writes/reads when the latch is open.

        On Redis blip we either recover (probe succeeds) or raise
        :class:`DistributedLockError` so the caller can fail closed.
        """
        if self._healthy:
            return
        if not self._should_attempt_recovery():
            LOCK_ERRORS.labels(service=self.service_label, operation=operation).inc()
            raise DistributedLockError(
                f"distributed_lock({self.namespace}): Redis latch open; "
                f"refusing {operation} until recovery cooldown elapses"
            )
        recovered = await self._attempt_recovery(client)
        if not recovered:
            LOCK_ERRORS.labels(service=self.service_label, operation=operation).inc()
            raise DistributedLockError(
                f"distributed_lock({self.namespace}): Redis still unreachable "
                f"after recovery probe; cannot {operation}"
            )

    @property
    def healthy(self) -> bool:
        return self._available and self._healthy

    @property
    def available(self) -> bool:
        return self._available

    async def close(self) -> None:
        if self._client is None:
            return
        try:
            close_fn = getattr(self._client, "aclose", None) or getattr(
                self._client, "close", None
            )
            if close_fn is None:
                return
            result = close_fn()
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.debug("distributed_lock(%s): close failed: %s", self.namespace, exc)

    # -- Key helpers ---------------------------------------------------

    def _full_key(self, key: str) -> str:
        return f"lock:{self.namespace}:{key}"

    # -- Acquire / release --------------------------------------------

    async def acquire(
        self,
        key: str,
        ttl_seconds: Optional[int] = None,
    ) -> Optional[str]:
        """Attempt to acquire the lock.

        Returns the unique token on success, ``None`` if another holder
        owns the lock. Raises :class:`DistributedLockError` on Redis
        failure (fail closed).

        ``ttl_seconds`` defaults to :attr:`default_ttl_seconds`. The
        recommended value is 2× the expected max processing time so a
        crashed handler eventually frees the key without holding up
        retries indefinitely.
        """
        client = await self._ensure_client()
        await self._ensure_healthy(client, operation="acquire")
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        if ttl <= 0:
            raise ValueError("ttl_seconds must be > 0")
        token = secrets.token_hex(16)
        full_key = self._full_key(key)
        try:
            ok = await client.set(full_key, token, nx=True, ex=ttl)
        except Exception as exc:
            self._mark_unhealthy()
            LOCK_ERRORS.labels(service=self.service_label, operation="acquire").inc()
            raise DistributedLockError(
                f"distributed_lock({self.namespace}): SET NX failed for "
                f"{full_key!r}: {exc}"
            ) from exc

        if not ok:
            LOCK_CONTENTION.labels(service=self.service_label).inc()
            return None

        LOCK_ACQUIRES.labels(service=self.service_label).inc()
        return token

    async def release(self, key: str, token: str) -> bool:
        """Release the lock if and only if ``token`` matches the holder.

        Returns True if we released the lock, False if the token was
        wrong or the key was already gone (TTL expired). Raises
        :class:`DistributedLockError` on Redis failure.
        """
        if not token:
            raise ValueError("release() requires the token returned by acquire()")
        client = await self._ensure_client()
        await self._ensure_healthy(client, operation="release")
        full_key = self._full_key(key)
        try:
            result = await client.eval(_RELEASE_SCRIPT, 1, full_key, token)
        except Exception as exc:
            self._mark_unhealthy()
            LOCK_ERRORS.labels(service=self.service_label, operation="release").inc()
            raise DistributedLockError(
                f"distributed_lock({self.namespace}): release Lua eval "
                f"failed for {full_key!r}: {exc}"
            ) from exc
        return bool(result)

    async def extend(self, key: str, token: str, ttl_seconds: int) -> bool:
        """Extend the TTL on an owned lock.

        Returns True on success. Used by long-running handlers that
        legitimately need to hold the lock past the original TTL.
        """
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        client = await self._ensure_client()
        await self._ensure_healthy(client, operation="extend")
        full_key = self._full_key(key)
        try:
            # PEXPIRE takes milliseconds.
            result = await client.eval(
                _EXTEND_SCRIPT, 1, full_key, token, str(ttl_seconds * 1000)
            )
        except Exception as exc:
            self._mark_unhealthy()
            LOCK_ERRORS.labels(service=self.service_label, operation="extend").inc()
            raise DistributedLockError(
                f"distributed_lock({self.namespace}): extend Lua eval "
                f"failed for {full_key!r}: {exc}"
            ) from exc
        return bool(result)

    async def ping(self) -> bool:
        """Probe Redis liveness — used by health checks.

        Mirrors :meth:`core.redis_cache.RedisCache.ping`. Failure flips
        the latch so subsequent operations short-circuit until a
        recovery probe succeeds.
        """
        try:
            client = await self._ensure_client()
        except DistributedLockError:
            return False
        try:
            pong = await client.ping()
        except Exception as exc:
            self._mark_unhealthy()
            LOCK_ERRORS.labels(service=self.service_label, operation="ping").inc()
            logger.debug("distributed_lock(%s): ping failed: %s", self.namespace, exc)
            return False
        if not pong:
            self._mark_unhealthy()
            return False
        self._healthy = True
        self._unhealthy_since = None
        return True

    # -- Idempotent-retry context manager ------------------------------

    @contextlib.asynccontextmanager
    async def guard(
        self,
        key: str,
        *,
        ttl_seconds: Optional[int] = None,
        result_cache: Any = None,
        result_cache_ttl: Optional[int] = None,
        wait_seconds: float = 0.0,
        wait_poll_interval: float = 0.05,
        on_contended: str = "raise",
    ):
        """Acquire-on-enter, release-on-exit context manager.

        :param key: Logical lock key — typically the event ID. Will be
            namespaced under ``lock:<namespace>:`` in Redis.
        :param ttl_seconds: Lock TTL. Defaults to
            :attr:`default_ttl_seconds`.
        :param result_cache: Optional :class:`core.redis_cache.RedisCache`
            for caching results across retries. When set, the second
            acquirer of the same ``key`` sees ``outcome.cached_result``
            and ``outcome.is_cached=True`` instead of doing the work.
        :param result_cache_ttl: TTL for the cached result; defaults to
            the cache's own ``default_ttl``.
        :param wait_seconds: How long to wait for a contended lock
            before giving up. Useful when the first holder is expected
            to finish quickly and publish the cached result.
        :param wait_poll_interval: How often to re-check while waiting.
        :param on_contended: ``"raise"`` (default) raises
            :class:`LockContended`; ``"return"`` yields an outcome with
            ``token=""`` and ``cached_result=None`` so the caller can
            decide.

        On exit, if the handler called ``outcome.set_result(value)``
        AND a ``result_cache`` was supplied, the value is written to
        the cache before the lock is released. That ordering is
        deliberate: subsequent retries that arrive after release must
        find the cached entry, otherwise they would re-run the work.
        """
        # Result cache short-circuit — check before bothering with the lock.
        cached: Any = None
        cache_key = key  # cached under the same logical key (caller controls)
        if result_cache is not None:
            try:
                cached = await result_cache.get(cache_key)
            except Exception as exc:
                # Cache faults are not lock faults — log and continue.
                logger.debug(
                    "distributed_lock(%s): result_cache.get failed: %s",
                    self.namespace,
                    exc,
                )
                cached = None
        if cached is not None:
            yield LockOutcome(
                key=cache_key,
                token="",
                cached_result=cached,
                is_cached=True,
            )
            return

        # Try to acquire, optionally waiting briefly for the holder to
        # publish the cached result.
        deadline = time.monotonic() + max(wait_seconds, 0.0)
        token: Optional[str] = None
        while True:
            token = await self.acquire(cache_key, ttl_seconds=ttl_seconds)
            if token is not None:
                break
            # Contended — re-check the cache; the first holder may have
            # just finished.
            if result_cache is not None:
                try:
                    cached = await result_cache.get(cache_key)
                except Exception:
                    cached = None
                if cached is not None:
                    yield LockOutcome(
                        key=cache_key,
                        token="",
                        cached_result=cached,
                        is_cached=True,
                    )
                    return
            if time.monotonic() >= deadline:
                if on_contended == "return":
                    yield LockOutcome(
                        key=cache_key,
                        token="",
                        cached_result=None,
                        is_cached=False,
                    )
                    return
                raise LockContended(
                    f"distributed_lock({self.namespace}): key {cache_key!r} "
                    "is held by another holder"
                )
            await asyncio.sleep(wait_poll_interval)

        # We just acquired the lock — but the prior holder may have
        # written the result to the cache and released *between* our
        # last cache.get() and our successful acquire(). Re-check the
        # cache one final time before doing the work so a late acquirer
        # short-circuits to the cached result instead of re-running the
        # handler. This closes the race that otherwise lets concurrent
        # replays each acquire-after-release and re-process the event.
        if result_cache is not None:
            try:
                cached = await result_cache.get(cache_key)
            except Exception as exc:
                logger.debug(
                    "distributed_lock(%s): post-acquire cache.get failed: %s",
                    self.namespace,
                    exc,
                )
                cached = None
            if cached is not None:
                # Release the lock we just took — we won't be doing the
                # work — then yield the cached outcome.
                try:
                    await self.release(cache_key, token)
                except DistributedLockError as exc:
                    logger.debug(
                        "distributed_lock(%s): release after cache hit "
                        "failed for %r: %s",
                        self.namespace,
                        cache_key,
                        exc,
                    )
                yield LockOutcome(
                    key=cache_key,
                    token="",
                    cached_result=cached,
                    is_cached=True,
                )
                return

        outcome = LockOutcome(key=cache_key, token=token)
        try:
            yield outcome
            # Persist the result BEFORE releasing the lock so retries
            # that arrive after release see the cache hit.
            if outcome._result_set and result_cache is not None:
                try:
                    await result_cache.set(
                        cache_key, outcome._result, ttl=result_cache_ttl
                    )
                except Exception as exc:
                    logger.warning(
                        "distributed_lock(%s): result_cache.set failed for "
                        "%r: %s — retries may re-run the handler",
                        self.namespace,
                        cache_key,
                        exc,
                    )
        finally:
            try:
                await self.release(cache_key, token)
            except DistributedLockError as exc:
                # Release failure on a Redis blip — log loudly. The TTL
                # will eventually free the key, so retries are bounded
                # rather than wedged.
                logger.warning(
                    "distributed_lock(%s): release failed for %r: %s",
                    self.namespace,
                    cache_key,
                    exc,
                )


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


def build_distributed_lock(
    namespace: str,
    *,
    service_name: Optional[str] = None,
    default_ttl_seconds: int = 60,
    client: Any = None,
    url: Optional[str] = None,
) -> DistributedLock:
    """Construct a :class:`DistributedLock` for ``service_name``.

    Resolution order matches :func:`core.redis_cache.build_redis_cache`:

    1. Explicit ``client`` (typically fakeredis under test).
    2. Explicit ``url`` argument.
    3. ``<SERVICE>_CACHE_REDIS_URL`` / ``CACHE_REDIS_URL`` / ``REDIS_URL``.

    If no Redis URL can be resolved, the lock is constructed but
    every operation will raise :class:`DistributedLockError` — this
    is **deliberate**: silently skipping the lock would re-introduce
    the double-charge bug we're closing.
    """
    if client is not None:
        return DistributedLock(
            namespace,
            client=client,
            default_ttl_seconds=default_ttl_seconds,
            service_label=service_name or namespace,
        )

    resolved_url = url or resolve_cache_redis_url(service_name=service_name)
    if not resolved_url:
        logger.warning(
            "distributed_lock(%s): no REDIS_URL configured for %s; "
            "every acquire/release will raise DistributedLockError",
            namespace,
            service_name or "service",
        )
        # Construct an "always errors" lock so callers get the explicit
        # signal instead of silent best-effort idempotency.
        lock = DistributedLock(
            namespace,
            client=None,
            default_ttl_seconds=default_ttl_seconds,
            service_label=service_name or namespace,
        )
        lock._available = False  # type: ignore[attr-defined]
        lock._healthy = False  # type: ignore[attr-defined]
        return lock

    logger.info(
        "distributed_lock(%s): backed by Redis (%s) ttl=%ss",
        namespace,
        resolved_url,
        default_ttl_seconds,
    )
    return DistributedLock(
        namespace,
        client=None,
        url=resolved_url,
        default_ttl_seconds=default_ttl_seconds,
        service_label=service_name or namespace,
    )
