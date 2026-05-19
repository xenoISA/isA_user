"""
MCP Streamable-HTTP Handshake Validator.

Used by routes_custom on every POST /custom and POST /custom/{id}/revalidate
before we persist (or re-activate) a user-supplied remote MCP server. The
goal is defense in depth against three classes of mistakes:

  1. Footgun URLs: ``http://``, ``file://``, ``gopher://`` schemes. Only
     ``https://`` (and ``http://`` when ALLOW_PRIVATE_MCP_HOSTS is set for
     local dev) are accepted.
  2. SSRF / private-IP targets: an unauthenticated user could otherwise
     point us at ``http://169.254.169.254/`` (cloud metadata),
     ``http://10.0.0.5/``, ``http://localhost/``, etc. We block:
        - loopback (127.0.0.0/8, ::1)
        - link-local (169.254.0.0/16, fe80::/10)
        - private RFC1918 (10/8, 172.16/12, 192.168/16)
        - reserved / unspecified (0.0.0.0, ::, multicast)
     The block is env-gated by ``ALLOW_PRIVATE_MCP_HOSTS`` so dev/CI can
     still target localhost mock servers.
  3. DNS rebinding: resolve the host once, then check the post-resolution
     IPs. If any resolved IP is in the blocked set, refuse — even if the
     hostname is benign.

If those gates pass, we run the MCP streamable-HTTP 3-message handshake:

    POST /  body={jsonrpc:"2.0", id:1, method:"initialize", ...}
    POST /  body={jsonrpc:"2.0",       method:"notifications/initialized"}
    POST /  body={jsonrpc:"2.0", id:2, method:"tools/list"}

All three within a single 10s outer timeout. Each individual request gets
the same client. On success the validator returns the tools_count from
the tools/list response. On any failure it returns a structured error
code + message — both surface verbatim in the 422 to the user so the UI
can render a useful hint.

NOTE: This is a minimal in-service implementation. There is no reusable
streamable-HTTP MCP client in the sibling isA_MCP repo (the MCP Python
SDK in .venv ships one, but pulling it into isA_user just for the
handshake would bloat the image). If the SDK gets added to user-base
later, swap ``_run_handshake`` for ``mcp.client.streamable_http``.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .feature_flags import allow_private_mcp_hosts

logger = logging.getLogger(__name__)


HANDSHAKE_TIMEOUT_SECONDS = 10.0
MCP_PROTOCOL_VERSION = "2025-03-26"
CLIENT_NAME = "isa-user-connector-service"
CLIENT_VERSION = "1.0.0"


# ============================================================================
# Result + error codes
# ============================================================================


# Stable error codes — surfaced verbatim in the 422 body so the UI can map
# them to translation keys. Adding a new code is a breaking change for the
# UI; prefer reusing an existing one.
ERR_SCHEME = "invalid_scheme"
ERR_HOSTNAME = "invalid_hostname"
ERR_PRIVATE_IP = "private_ip_blocked"
ERR_DNS = "dns_resolution_failed"
ERR_TIMEOUT = "handshake_timeout"
ERR_HTTP_STATUS = "handshake_http_error"
ERR_AUTH = "handshake_unauthorized"
ERR_TRANSPORT = "handshake_transport_error"
ERR_JSON_RPC = "handshake_protocol_error"
ERR_NO_TOOLS = "handshake_no_tools_list"


@dataclass
class HandshakeResult:
    """Outcome of validate_mcp_url. ``ok=True`` iff all gates passed and
    the 3-message handshake completed."""

    ok: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    tools_count: Optional[int] = None


# ============================================================================
# Pre-flight gates (scheme + private-IP + DNS)
# ============================================================================


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    """Return True if the IP is one of the families we refuse to target.

    Refused families (in addition to the obvious 'private'):
      - loopback (127/8, ::1)
      - link-local (169.254/16, fe80::/10)
      - reserved + unspecified (0.0.0.0, ::)
      - multicast (224.0.0.0/4, ff00::/8)
    """
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    )


def _check_scheme_and_host(
    url: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Validate the URL surface — scheme + non-empty host.

    Returns (host, error_code, error_message). If ``error_code`` is set,
    ``host`` is None and the caller should short-circuit.
    """
    try:
        parsed = urlparse(url)
    except Exception as e:  # urlparse is forgiving but defensive
        return None, ERR_SCHEME, f"Malformed URL: {e}"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("https", "http"):
        return (
            None,
            ERR_SCHEME,
            f"Unsupported scheme {scheme!r}; only https:// (or http:// in dev) is allowed",
        )
    if scheme == "http" and not allow_private_mcp_hosts():
        return (
            None,
            ERR_SCHEME,
            "Plain http:// is not allowed; use https://. (Set ALLOW_PRIVATE_MCP_HOSTS=true in dev to bypass.)",
        )

    host = parsed.hostname
    if not host:
        return None, ERR_HOSTNAME, "URL is missing a hostname"
    return host, None, None


def _resolve_host(host: str) -> Tuple[Optional[list], Optional[str], Optional[str]]:
    """DNS resolve `host` to a list of IPs. Returns (ips, error_code, error_message).

    Uses ``socket.getaddrinfo`` so we get both A and AAAA records in one
    pass. This is the post-DNS cross-check for #2 — even if the hostname
    looks benign, the resolved IPs determine whether we proceed.
    """
    try:
        # AF_UNSPEC -> both v4 + v6
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        return None, ERR_DNS, f"DNS resolution failed for {host!r}: {e}"
    except Exception as e:
        return None, ERR_DNS, f"DNS resolution error for {host!r}: {e}"

    ips = []
    for info in infos:
        # info = (family, type, proto, canonname, sockaddr)
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            ips.append(ipaddress.ip_address(ip_str))
        except ValueError:
            continue
    if not ips:
        return None, ERR_DNS, f"No usable IPs returned for {host!r}"
    return ips, None, None


def _check_resolved_ips_allowed(ips: list) -> Tuple[Optional[str], Optional[str]]:
    """Walk the resolved IPs; refuse if any is blocked (unless the dev
    override is on)."""
    if allow_private_mcp_hosts():
        return None, None
    for ip in ips:
        if _is_blocked_ip(ip):
            return (
                ERR_PRIVATE_IP,
                f"Refusing to connect to private/loopback/link-local IP {ip} — set "
                "ALLOW_PRIVATE_MCP_HOSTS=true to bypass in dev.",
            )
    return None, None


# ============================================================================
# MCP streamable-HTTP 3-message handshake
# ============================================================================


def _auth_header(auth_kind: str, auth_secret: Optional[str]) -> Dict[str, str]:
    """Build the Authorization header for the handshake.

    - ``none`` -> no header.
    - ``pat`` -> ``Bearer <secret>``.
    - ``oauth_oob`` -> ``Bearer <secret>`` (the user pasted a pre-issued token).
    """
    kind = (auth_kind or "none").lower()
    if kind == "none" or not auth_secret:
        return {}
    # Both PAT and oauth_oob use Bearer; the distinction is only how the
    # secret was obtained.
    return {"Authorization": f"Bearer {auth_secret}"}


async def _run_handshake(
    url: str,
    auth_kind: str,
    auth_secret: Optional[str],
) -> HandshakeResult:
    """Run the MCP 3-message handshake against `url`.

    Wrapped in a single 10s outer timeout. Per-request timeouts are also
    set so a slow connect doesn't eat the whole budget on the first message.
    """
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        **_auth_header(auth_kind, auth_secret),
    }

    init_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
        },
    }
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    tools_list_body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    }

    timeout = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            # ---- 1) initialize ----
            resp = await client.post(url, json=init_body, headers=headers)
            if resp.status_code == 401 or resp.status_code == 403:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_AUTH,
                    error_message=f"MCP server rejected credentials (HTTP {resp.status_code})",
                )
            if resp.status_code >= 400:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_HTTP_STATUS,
                    error_message=f"initialize returned HTTP {resp.status_code}",
                )
            # Some servers return SSE on the initialize call; for the
            # validator we only need a successful HTTP envelope and a
            # parseable JSON-RPC frame from at least the tools/list call.
            init_payload = _decode_jsonrpc(resp)
            if init_payload is None:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_JSON_RPC,
                    error_message="initialize response was not parseable JSON-RPC",
                )

            # If the server sent a session id, echo it back on subsequent
            # requests — required by the MCP streamable-HTTP spec.
            session_id = resp.headers.get("Mcp-Session-Id") or resp.headers.get(
                "mcp-session-id"
            )
            if session_id:
                headers["Mcp-Session-Id"] = session_id

            # ---- 2) notifications/initialized ----
            note = await client.post(
                url, json=initialized_notification, headers=headers
            )
            if note.status_code >= 500:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_HTTP_STATUS,
                    error_message=f"notifications/initialized returned HTTP {note.status_code}",
                )
            # 2xx + 4xx (other than 5xx) are accepted; spec says servers
            # MAY ignore notifications. 401 should already have surfaced
            # on initialize.

            # ---- 3) tools/list ----
            tools_resp = await client.post(url, json=tools_list_body, headers=headers)
            if tools_resp.status_code == 401 or tools_resp.status_code == 403:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_AUTH,
                    error_message=f"MCP server rejected credentials on tools/list (HTTP {tools_resp.status_code})",
                )
            if tools_resp.status_code >= 400:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_HTTP_STATUS,
                    error_message=f"tools/list returned HTTP {tools_resp.status_code}",
                )
            tools_payload = _decode_jsonrpc(tools_resp)
            if tools_payload is None:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_JSON_RPC,
                    error_message="tools/list response was not parseable JSON-RPC",
                )
            tools = _extract_tools_list(tools_payload)
            if tools is None:
                return HandshakeResult(
                    ok=False,
                    error_code=ERR_NO_TOOLS,
                    error_message="tools/list response did not contain a tools array",
                )
            return HandshakeResult(ok=True, tools_count=len(tools))
    except httpx.TimeoutException as e:
        return HandshakeResult(
            ok=False,
            error_code=ERR_TIMEOUT,
            error_message=f"Handshake timed out: {e}",
        )
    except httpx.HTTPError as e:
        return HandshakeResult(
            ok=False,
            error_code=ERR_TRANSPORT,
            error_message=f"HTTP transport error: {e}",
        )
    except (
        Exception
    ) as e:  # noqa: BLE001 — surface anything unexpected as a transport error
        logger.exception("Unexpected error during MCP handshake")
        return HandshakeResult(
            ok=False,
            error_code=ERR_TRANSPORT,
            error_message=f"Unexpected error during handshake: {e}",
        )


def _decode_jsonrpc(response: httpx.Response) -> Optional[Dict[str, Any]]:
    """Decode a streamable-HTTP JSON-RPC frame.

    The MCP streamable-HTTP spec lets servers return either:
      * application/json  -> a single JSON object
      * text/event-stream -> SSE; the JSON-RPC payload sits in a
        ``data:`` line. We grep the first data line for the response.
    """
    ctype = (response.headers.get("content-type") or "").lower()
    raw = response.text
    if "application/json" in ctype:
        try:
            return response.json()
        except Exception:
            return None
    if "text/event-stream" in ctype or raw.lstrip().startswith("data:"):
        import json as _json

        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if not payload:
                continue
            try:
                return _json.loads(payload)
            except Exception:
                continue
        return None
    # Fall back to a best-effort json parse.
    try:
        return response.json()
    except Exception:
        return None


def _extract_tools_list(payload: Dict[str, Any]) -> Optional[list]:
    """Pull ``result.tools`` (the spec'd location) out of a tools/list response.

    Returns None if the payload is shaped wrong, an empty list if the
    server has zero tools (still considered a successful handshake — the
    server is reachable, just empty).
    """
    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    tools = result.get("tools")
    if not isinstance(tools, list):
        return None
    return tools


# ============================================================================
# Public entry point
# ============================================================================


async def validate_mcp_url(
    url: str,
    auth_kind: str = "none",
    auth_secret: Optional[str] = None,
) -> HandshakeResult:
    """Run all gates + handshake against a candidate MCP URL.

    This is the single function routes_custom calls before persisting (or
    reactivating) a custom MCP row. It is async, never raises, and always
    returns a :class:`HandshakeResult`.
    """
    # 1) Scheme + hostname.
    host, code, message = _check_scheme_and_host(url)
    if code is not None:
        return HandshakeResult(ok=False, error_code=code, error_message=message)

    # 2) Pre-DNS host check — block obvious literal IPs before we even ask
    #    the resolver. (A literal '127.0.0.1' would still hit the post-DNS
    #    check below, but rejecting early gives a clearer error.)
    try:
        literal = ipaddress.ip_address(host)
        block_code, block_msg = _check_resolved_ips_allowed([literal])
        if block_code is not None:
            return HandshakeResult(
                ok=False, error_code=block_code, error_message=block_msg
            )
    except ValueError:
        # Not a literal IP — proceed to DNS.
        pass

    # 3) DNS resolve + cross-check the IPs we got back.
    ips, dns_code, dns_msg = _resolve_host(host)
    if dns_code is not None:
        return HandshakeResult(ok=False, error_code=dns_code, error_message=dns_msg)

    block_code, block_msg = _check_resolved_ips_allowed(ips or [])
    if block_code is not None:
        return HandshakeResult(ok=False, error_code=block_code, error_message=block_msg)

    # 4) Streamable-HTTP 3-message handshake, all under one 10s budget.
    try:
        return await asyncio.wait_for(
            _run_handshake(url, auth_kind, auth_secret),
            timeout=HANDSHAKE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return HandshakeResult(
            ok=False,
            error_code=ERR_TIMEOUT,
            error_message=f"Handshake exceeded {HANDSHAKE_TIMEOUT_SECONDS:.0f}s budget",
        )
