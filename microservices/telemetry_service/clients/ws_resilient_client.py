"""
Resilient WebSocket client for telemetry_service.

Reconnects automatically when the server drains a connection (close code
1001 — `going away`) or when the underlying socket dies. On disconnect the
client looks up healthy replicas via Consul SRV (or a configured K8s
headless service) and resumes the durable subscription using
`subscription_id`. The server reconstructs the cursor from that ID so no
acknowledged message should be lost on a graceful handoff.

Usage:
    async with ResilientTelemetryWebSocket(
        subscription_id="sub_123",
        connect_token="opaque-token",
        consul=consul_registry,
    ) as client:
        async for message in client.stream():
            handle(message)

Backoff:
    The reconnect schedule is exponential with jitter, capped at
    `max_backoff_seconds` (default 30s). The first retry waits the
    `Retry-After` hint emitted in the prior server frame when present.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
)

logger = logging.getLogger("telemetry_service.ws_resilient_client")


# Public WebSocket close code that indicates the server is going away
# (graceful shutdown / scale-down). When a connection terminates with this
# code the client should reconnect via service discovery.
WS_CODE_GOING_AWAY = 1001


@dataclass(frozen=True)
class ReplicaEndpoint:
    """A single telemetry_service replica that can serve a WS subscription."""

    address: str
    port: int
    scheme: str = "ws"

    def url_for(self, subscription_id: str, connect_token: str) -> str:
        return (
            f"{self.scheme}://{self.address}:{self.port}"
            f"/ws/telemetry/{subscription_id}?token={connect_token}"
        )


class ConsulDiscovery(Protocol):
    """Subset of ConsulRegistry that this client depends on."""

    def discover_service(
        self, service_name: str
    ) -> List[Dict[str, Any]]:  # pragma: no cover — protocol
        ...


def compute_backoff_delay(
    attempt: int,
    *,
    base_seconds: float = 0.5,
    max_seconds: float = 30.0,
    jitter: float = 0.2,
) -> float:
    """Exponential backoff with bounded jitter.

    Pure function — pulled out so it can be exercised in unit tests without
    starting a network server. The curve is `base * 2**attempt`, hard-capped
    at `max_seconds`. Jitter widens the upper bound to avoid thundering-herd
    reconnects across many clients.
    """
    if attempt < 0:
        raise ValueError("attempt must be >= 0")
    raw = base_seconds * (2**attempt)
    capped = min(raw, max_seconds)
    if jitter <= 0:
        return capped
    spread = capped * jitter
    return min(max_seconds, capped + random.uniform(0.0, spread))


def discover_replicas(
    consul: Optional[ConsulDiscovery],
    service_name: str = "telemetry_service",
    *,
    fallback: Optional[List[ReplicaEndpoint]] = None,
    scheme: str = "ws",
) -> List[ReplicaEndpoint]:
    """Resolve healthy replicas via Consul SRV-style lookups.

    Falls back to the provided static list (e.g. a K8s headless Service)
    when Consul is unavailable or returns no results. Pure-ish: only side
    effect is the Consul HTTP call performed by `discover_service`.
    """
    if consul is None:
        return list(fallback or [])
    try:
        instances = consul.discover_service(service_name) or []
    except Exception as exc:
        logger.warning("Consul discovery failed for %s: %s", service_name, exc)
        instances = []
    endpoints = [
        ReplicaEndpoint(
            address=str(inst.get("address") or "localhost"),
            port=int(inst.get("port") or 0),
            scheme=scheme,
        )
        for inst in instances
        if inst.get("port")
    ]
    if endpoints:
        return endpoints
    return list(fallback or [])


@dataclass
class ResilientTelemetryWebSocket:
    """Reconnecting WebSocket client for telemetry subscriptions.

    Parameters mirror the server contract: callers provide
    `subscription_id` (created via `POST /api/v1/telemetry/subscribe`) and
    the opaque `connect_token` returned by that call. The client itself
    only needs read access to Consul (or a static replica list) to find
    a healthy replica when the current one drops.
    """

    subscription_id: str
    connect_token: str
    consul: Optional[ConsulDiscovery] = None
    fallback_replicas: List[ReplicaEndpoint] = field(default_factory=list)
    service_name: str = "telemetry_service"
    scheme: str = "ws"
    max_backoff_seconds: float = 30.0
    base_backoff_seconds: float = 0.5
    websocket_factory: Optional[Callable[[str], Awaitable[Any]]] = None
    sleeper: Callable[[float], Awaitable[None]] = field(
        default_factory=lambda: asyncio.sleep
    )

    _socket: Any = field(default=None, init=False, repr=False)
    _session_id: Optional[str] = field(default=None, init=False, repr=False)
    _cursor: Optional[Dict[str, Any]] = field(default=None, init=False, repr=False)
    _retry_after_hint: float = field(default=0.0, init=False, repr=False)
    _attempt: int = field(default=0, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def cursor(self) -> Optional[Dict[str, Any]]:
        return self._cursor

    async def __aenter__(self) -> "ResilientTelemetryWebSocket":
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        self._closed = True
        if self._socket is not None and hasattr(self._socket, "close"):
            try:
                await self._socket.close()
            except Exception:
                logger.debug("Error while closing socket on shutdown", exc_info=True)
        self._socket = None

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield messages, reconnecting on going-away or transport errors."""
        while not self._closed:
            if self._socket is None:
                await self._connect()
            try:
                raw = await self._socket.recv()
            except Exception as exc:
                logger.info("Telemetry WS recv error: %s; reconnecting", exc)
                await self._handle_disconnect(WS_CODE_GOING_AWAY)
                continue

            try:
                msg = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
            except json.JSONDecodeError:
                logger.warning("Dropped non-JSON frame: %r", raw[:64])
                continue

            if isinstance(msg, dict) and msg.get("type") == "subscription.connected":
                self._session_id = msg.get("session_id") or self._session_id
                self._cursor = msg.get("cursor") or self._cursor
                hint = msg.get("retry_after")
                if isinstance(hint, (int, float)) and hint > 0:
                    self._retry_after_hint = float(hint)

            yield msg

    async def _connect(self) -> None:
        if self.websocket_factory is None:
            raise RuntimeError(
                "websocket_factory must be provided to open a connection"
            )

        last_error: Optional[Exception] = None
        replicas = self._select_replicas()
        if not replicas:
            raise RuntimeError(
                "No healthy telemetry_service replicas found via Consul or fallback"
            )

        for endpoint in replicas:
            url = endpoint.url_for(self.subscription_id, self.connect_token)
            try:
                self._socket = await self.websocket_factory(url)
                self._attempt = 0
                logger.debug("Connected to telemetry replica %s", url)
                return
            except Exception as exc:  # pragma: no cover — exercised in tests
                last_error = exc
                logger.warning("Failed to connect to %s: %s", url, exc)
                continue

        # All replicas failed: schedule a backed-off retry.
        await self._handle_disconnect(WS_CODE_GOING_AWAY, error=last_error)

    async def _handle_disconnect(
        self, close_code: int, *, error: Optional[Exception] = None
    ) -> None:
        if self._closed:
            return
        self._socket = None
        # Use the server-supplied retry hint for the very first delay; fall
        # back to the exponential schedule afterwards.
        if self._attempt == 0 and self._retry_after_hint > 0:
            delay = min(self._retry_after_hint, self.max_backoff_seconds)
        else:
            delay = compute_backoff_delay(
                self._attempt,
                base_seconds=self.base_backoff_seconds,
                max_seconds=self.max_backoff_seconds,
            )
        self._attempt += 1
        logger.info(
            "Telemetry WS reconnecting (attempt=%s, delay=%.2fs, code=%s)",
            self._attempt,
            delay,
            close_code,
        )
        await self.sleeper(delay)

    def _select_replicas(self) -> List[ReplicaEndpoint]:
        return discover_replicas(
            self.consul,
            service_name=self.service_name,
            fallback=self.fallback_replicas,
            scheme=self.scheme,
        )


__all__ = [
    "ResilientTelemetryWebSocket",
    "ReplicaEndpoint",
    "compute_backoff_delay",
    "discover_replicas",
    "WS_CODE_GOING_AWAY",
]
