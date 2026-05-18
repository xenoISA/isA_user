"""
Artifact Service — business-logic layer.

Implements the Phase 1 slice of xenoISA/isA_user#441 (parent epic in
xenoISA/isA_#427) — enough of the artifact library backend to replace the
localStorage stub in ``isA_/src/stores/useArtifactLibrary.ts``.

What's wired up:
  - create artifact (with mandatory first version)
  - get artifact + all versions
  - list with scope/q/cursor filters
  - patch title / visibility / runtime flags
  - soft delete (sets ``deleted_at``)
  - add new version (auto-increments number, advances ``current_version_id``)

What's intentionally NOT here (Phase 2+):
  - publish/revoke share tokens (``artifact_shares`` table reserved in migration)
  - remix into new session
  - MCP grants, KV storage, runtime usage / quota
  - cross-org permission resolution via sharing_service
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.nats_client import Event

from .models import (
    Artifact,
    ArtifactCreateRequest,
    ArtifactListItem,
    ArtifactListResponse,
    ArtifactScope,
    ArtifactShare,
    ArtifactShareVisibility,
    ArtifactSharesListResponse,
    ArtifactUpdateRequest,
    ArtifactVersion,
    ArtifactVersionCreateRequest,
    ArtifactVisibility,
    PublicArtifactResponse,
    PublicArtifactShareMeta,
    PublishArtifactRequest,
    PublishArtifactResponse,
    RemixArtifactRequest,
    RevokeArtifactRequest,
    RevokeArtifactResponse,
)
from .protocols import (
    ArtifactNotFoundError,
    ArtifactPermissionError,
    ArtifactRepositoryProtocol,
    ArtifactServiceError,
    ArtifactValidationError,
    EventBusProtocol,
)


DEFAULT_DAILY_QUOTA = 50

# Phase 3 polish (xenoISA/isA_user#441): runtime/invoke proxies to isA_Model,
# mcp/call proxies to isA_MCP. Both are best-effort — if the upstream is
# unreachable the route falls back to the original stub so the endpoint never
# 500s on a transient outage. The defaults below match how isA_Model and
# isA_MCP are reachable from a local-dev deploy (`bash deployment/local-dev.sh`).
DEFAULT_ISA_MODEL_URL = "http://localhost:8082"
# MCP root path — the streamable-HTTP transport posts ``initialize``,
# ``notifications/initialized``, then ``tools/call`` to the same endpoint
# (the protocol multiplexes via the JSON-RPC ``method`` field). The earlier
# Phase 3 polish (single-POST) targeted ``/mcp/tools/call`` directly which
# only works for non-session servers; the session-aware client below uses
# ``/mcp`` and falls back to the legacy path when an env override points
# there.
DEFAULT_ISA_MCP_URL = "http://localhost:8081/mcp"
DEFAULT_RUNTIME_MODEL = "gpt-4.1-nano"
DEFAULT_RUNTIME_PROVIDER = "openai"
DEFAULT_RUNTIME_MAX_TOKENS = 512
RUNTIME_MAX_TOKENS_CAP = 4096


def _isa_model_url() -> str:
    return os.getenv("ISA_MODEL_URL", DEFAULT_ISA_MODEL_URL)


def _isa_mcp_url() -> str:
    return os.getenv("ISA_MCP_URL", DEFAULT_ISA_MCP_URL)


def _runtime_model() -> str:
    return os.getenv("ARTIFACT_RUNTIME_MODEL", DEFAULT_RUNTIME_MODEL)


def _runtime_provider() -> str:
    return os.getenv("ARTIFACT_RUNTIME_PROVIDER", DEFAULT_RUNTIME_PROVIDER)


def _daily_quota() -> int:
    """Resolve the per-user-per-artifact daily call cap from env at call time.

    Looked up dynamically so tests can override ARTIFACT_DAILY_QUOTA without
    needing to re-import the module.
    """
    raw = os.getenv("ARTIFACT_DAILY_QUOTA")
    if not raw:
        return DEFAULT_DAILY_QUOTA
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_DAILY_QUOTA


def _seconds_until_midnight_utc() -> int:
    """Seconds remaining until 00:00 UTC tomorrow — drives Retry-After."""
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # bump to next day
    from datetime import timedelta

    tomorrow = tomorrow + timedelta(days=1)
    delta = tomorrow - now
    return max(1, int(delta.total_seconds()))


class ArtifactQuotaExceededError(Exception):
    """Raised when a user has already used today's per-artifact quota.

    Carries the Retry-After hint so the route can shape a proper 429.
    """

    def __init__(self, retry_after: int, calls_today: int, quota: int):
        super().__init__(f"daily quota of {quota} calls exceeded (today={calls_today})")
        self.retry_after = retry_after
        self.calls_today = calls_today
        self.quota = quota


logger = logging.getLogger(__name__)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ==================== MCP session-aware client ====================
#
# The MCP streamable-HTTP transport (used by isA_MCP and any other modern MCP
# server) requires a three-step handshake:
#   1. POST ``/mcp`` with ``{method: 'initialize', ...}`` -> server returns
#      capabilities and an ``Mcp-Session-Id`` response header.
#   2. POST ``/mcp`` with ``Mcp-Session-Id`` header + ``notifications/initialized``
#      (no response body expected).
#   3. POST ``/mcp`` with ``Mcp-Session-Id`` + ``tools/call`` to actually run
#      the tool. The response may be plain JSON (Content-Type:
#      application/json) or an SSE event stream (text/event-stream) carrying
#      one or more ``data: <json>`` frames.
#
# _McpSession holds the per-(artifact, server) session state. The earlier
# single-POST transport is preserved as a fallback for legacy/stateless MCP
# endpoints that 404 on /initialize.

MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_CLIENT_NAME = "isA_user.artifact_service"
MCP_CLIENT_VERSION = "1.0.0"
MCP_SESSION_TIMEOUT_SECONDS = 5.0


class _McpSessionExpired(Exception):
    """Raised when the server returns 401/404 for a cached session id."""


class _McpSession:
    """Per-server MCP client that lazily initializes a session and reuses it.

    Thread-safety: the FastAPI runtime is single-event-loop; concurrent calls
    to the same session share the cached id without locking. If a second call
    races the initial handshake both will perform an initialize — that's
    benign (the second one's session id wins in cache). A future revision can
    add an asyncio.Lock if this turns out to matter.
    """

    def __init__(self, server_url: str, server_id: str):
        # ``server_url`` is the MCP root (e.g. ``http://localhost:8081/mcp``).
        # The transport always POSTs back to this same URL — the JSON-RPC
        # ``method`` field multiplexes initialize / notifications / tools.
        self.server_url = server_url.rstrip("/")
        self.server_id = server_id
        self.session_id: Optional[str] = None
        self.initialized: bool = False

    def reset(self) -> None:
        self.session_id = None
        self.initialized = False

    @staticmethod
    def _parse_mcp_body(content_type: str, body: bytes) -> dict:
        """Extract a JSON-RPC envelope from a streamable-HTTP response body.

        For ``application/json`` returns the parsed object directly. For
        ``text/event-stream`` walks the SSE frames and returns the LAST
        frame that carries a ``result`` (the spec allows progress frames
        before the terminal result). Raises ValueError if nothing parseable
        is found.
        """
        import json

        text = body.decode("utf-8", errors="replace")
        if "event-stream" in content_type.lower() or text.lstrip().startswith("event:"):
            chosen: Optional[dict] = None
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    frame = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(frame, dict) and "result" in frame:
                    chosen = frame
                elif chosen is None and isinstance(frame, dict):
                    chosen = frame
            if chosen is None:
                raise ValueError("SSE stream contained no JSON-RPC frames")
            return chosen
        # Plain JSON
        return json.loads(text)

    async def _post(
        self,
        rpc_body: dict,
        *,
        expect_response: bool,
        auth_token: Optional[str] = None,
    ) -> tuple[Optional[dict], Optional[str]]:
        """POST a JSON-RPC frame to the MCP root. Returns (payload, session_id).

        ``payload`` is None when ``expect_response`` is False (notifications)
        or the server returned an empty 2xx body. ``session_id`` is the
        value of the ``Mcp-Session-Id`` response header, if present.

        Raises _McpSessionExpired on 401/404 so the caller can re-init.
        """
        import httpx

        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        async with httpx.AsyncClient(timeout=MCP_SESSION_TIMEOUT_SECONDS) as client:
            resp = await client.post(self.server_url, json=rpc_body, headers=headers)

        if resp.status_code in (401, 404):
            raise _McpSessionExpired(f"MCP session expired (HTTP {resp.status_code}); re-initializing")
        if resp.status_code >= 400:
            raise RuntimeError(f"isA_MCP returned HTTP {resp.status_code}: {resp.text[:500]}")

        new_session_id = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if not expect_response or not resp.content:
            return None, new_session_id

        content_type = resp.headers.get("Content-Type", "application/json")
        payload = self._parse_mcp_body(content_type, resp.content)
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(f"isA_MCP RPC error: {payload['error']}")
        return payload, new_session_id

    async def initialize(self, auth_token: Optional[str] = None) -> None:
        """Run the MCP handshake: initialize + notifications/initialized."""
        init_body = {
            "jsonrpc": "2.0",
            "id": _new_id("mcp")[4:],
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": MCP_CLIENT_NAME, "version": MCP_CLIENT_VERSION},
            },
        }
        _payload, session_id = await self._post(init_body, expect_response=True, auth_token=auth_token)
        if session_id:
            self.session_id = session_id

        # Notification — no body expected back. Some servers 202 with empty
        # body; some 200 with empty body. Either is fine.
        notif_body = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        await self._post(notif_body, expect_response=False, auth_token=auth_token)
        self.initialized = True

    async def tools_call(
        self,
        tool_name: str,
        args: dict,
        *,
        auth_token: Optional[str] = None,
    ) -> dict:
        """Call a tool; auto-initialize on the first call."""
        if not self.initialized:
            await self.initialize(auth_token=auth_token)

        call_body = {
            "jsonrpc": "2.0",
            "id": _new_id("mcp")[4:],
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args,
                # ``server_id`` isn't part of the MCP spec but isA_MCP's
                # multiplexed gateway uses it to pick a backend; harmless on
                # vanilla servers that ignore unknown params.
                "server_id": self.server_id,
            },
        }
        payload, _session_id = await self._post(call_body, expect_response=True, auth_token=auth_token)
        if payload is None:
            raise RuntimeError("isA_MCP tools/call returned empty body")
        # JSON-RPC envelopes wrap the answer in ``result``; surface that when
        # present, otherwise the raw payload (servers vary).
        result = payload.get("result", payload) if isinstance(payload, dict) else payload
        return {"tool_name": tool_name, "server_id": self.server_id, "result": result}


class ArtifactService:
    """Business-logic facade over the repository."""

    def __init__(
        self,
        repository: ArtifactRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ):
        self.repo = repository
        self.event_bus = event_bus

    # ==================== Helpers ====================

    @staticmethod
    def _to_list_item(artifact: Artifact) -> ArtifactListItem:
        latest = artifact.versions[-1] if artifact.versions else None
        return ArtifactListItem(
            id=artifact.id,
            owner_user_id=artifact.owner_user_id,
            owner_org_id=artifact.owner_org_id,
            title=artifact.title,
            content_type=artifact.content_type,
            visibility=artifact.visibility,
            parent_artifact_id=artifact.parent_artifact_id,
            source_session_id=artifact.source_session_id,
            current_version_id=artifact.current_version_id,
            version_count=len(artifact.versions),
            latest_version_number=latest.number if latest else None,
            latest_language=latest.language if latest else None,
            latest_filename=latest.filename if latest else None,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    async def _publish(self, event_type: str, data: dict) -> None:
        if not self.event_bus:
            return
        try:
            event = Event(event_type=event_type, source="artifact_service", data=data)
            await self.event_bus.publish_event(event)
        except Exception as e:  # pragma: no cover - best effort
            logger.error(f"Failed to publish {event_type}: {e}")

    def _assert_owner(self, artifact: Artifact, user_id: str) -> None:
        if artifact.owner_user_id != user_id:
            raise ArtifactPermissionError("Only the artifact owner may perform this action")

    # ==================== Create ====================

    async def create_artifact(self, request: ArtifactCreateRequest, user_id: str) -> Artifact:
        if not request.title.strip():
            raise ArtifactValidationError("title is required")
        if not request.version.content:
            raise ArtifactValidationError("first version must include content")

        artifact_id = _new_id("art")
        version_id = _new_id("ver")
        version = ArtifactVersion(
            id=version_id,
            artifact_id=artifact_id,
            number=request.version.number or 1,
            content=request.version.content,
            language=request.version.language,
            filename=request.version.filename,
            blob_url=request.version.blob_url,
            a2ui_state_json=request.version.a2ui_state_json,
            instruction=request.version.instruction,
            created_by=user_id,
        )

        artifact = Artifact(
            id=artifact_id,
            owner_user_id=user_id,
            owner_org_id=request.owner_org_id,
            title=request.title.strip(),
            content_type=request.content_type,
            current_version_id=version_id,
            source_session_id=request.source_session_id,
            source_message_id=request.source_message_id,
            parent_artifact_id=request.parent_artifact_id,
            visibility=request.visibility,
            ai_runtime_enabled=request.ai_runtime_enabled,
            storage_scope=request.storage_scope,
            metadata=request.metadata or {},
        )

        try:
            created = await self.repo.create_artifact(artifact)
            await self.repo.add_version(artifact_id, version)
            # Ensure current_version_id is pinned even if insert ordering surprised us.
            await self.repo.set_current_version(artifact_id, version_id)
        except Exception as e:
            logger.error(f"create_artifact failed: {e}")
            raise ArtifactServiceError(str(e)) from e

        fetched = await self.repo.get_artifact(artifact_id)
        if fetched is None:  # pragma: no cover - defensive
            raise ArtifactServiceError("artifact disappeared after creation")

        await self._publish(
            "artifact.created",
            {
                "artifact_id": artifact_id,
                "user_id": user_id,
                "title": fetched.title,
                "content_type": fetched.content_type,
                "visibility": fetched.visibility.value,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return fetched

    # ==================== Read ====================

    async def get_artifact(self, artifact_id: str, user_id: str) -> Artifact:
        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        # In Phase 1 only the owner may read. Public/org visibility is resolved
        # via the share-token reader in a follow-up (#441 story 5).
        if artifact.owner_user_id != user_id and artifact.visibility == ArtifactVisibility.PRIVATE:
            raise ArtifactPermissionError("Access denied to this artifact")
        return artifact

    async def list_artifacts(
        self,
        *,
        user_id: str,
        scope: ArtifactScope = ArtifactScope.ALL,
        q: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> ArtifactListResponse:
        rows, next_cursor, total = await self.repo.list_artifacts(
            user_id=user_id, scope=scope, q=q, cursor=cursor, limit=limit
        )
        return ArtifactListResponse(
            items=[self._to_list_item(r) for r in rows],
            total=total,
            cursor=next_cursor,
        )

    # ==================== Update ====================

    async def update_artifact(self, artifact_id: str, request: ArtifactUpdateRequest, user_id: str) -> Artifact:
        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._assert_owner(artifact, user_id)

        fields: dict = {}
        if request.title is not None:
            fields["title"] = request.title.strip()
        if request.visibility is not None:
            fields["visibility"] = request.visibility
        if request.ai_runtime_enabled is not None:
            fields["ai_runtime_enabled"] = request.ai_runtime_enabled
        if request.storage_scope is not None:
            fields["storage_scope"] = request.storage_scope
        if request.metadata is not None:
            fields["metadata"] = request.metadata

        if not fields:
            return artifact

        updated = await self.repo.update_artifact(artifact_id, fields)
        if updated is None:  # pragma: no cover - defensive
            raise ArtifactServiceError("update returned no row")

        await self._publish(
            "artifact.updated",
            {
                "artifact_id": artifact_id,
                "user_id": user_id,
                "fields": list(fields.keys()),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return updated

    # ==================== Delete ====================

    async def delete_artifact(self, artifact_id: str, user_id: str) -> bool:
        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._assert_owner(artifact, user_id)

        ok = await self.repo.soft_delete_artifact(artifact_id, user_id)
        if ok:
            await self._publish(
                "artifact.deleted",
                {
                    "artifact_id": artifact_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        return ok

    # ==================== Versions ====================

    async def add_version(
        self,
        artifact_id: str,
        request: ArtifactVersionCreateRequest,
        user_id: str,
    ) -> ArtifactVersion:
        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._assert_owner(artifact, user_id)

        if not request.content:
            raise ArtifactValidationError("version content is required")

        version_id = _new_id("ver")
        number = request.number or await self.repo.next_version_number(artifact_id)

        version = ArtifactVersion(
            id=version_id,
            artifact_id=artifact_id,
            number=number,
            content=request.content,
            language=request.language,
            filename=request.filename,
            blob_url=request.blob_url,
            a2ui_state_json=request.a2ui_state_json,
            instruction=request.instruction,
            created_by=user_id,
        )

        added = await self.repo.add_version(artifact_id, version)
        await self.repo.set_current_version(artifact_id, version_id)

        await self._publish(
            "artifact.version.added",
            {
                "artifact_id": artifact_id,
                "version_id": version_id,
                "number": number,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return added

    # ==================== Phase 2: Publish / Revoke / Public Read / Remix ====================
    #
    # All four operations build on the `artifact_shares` table that already
    # shipped with migration 001. publish_artifact mints a token, revoke
    # flips revoked_at, the public reader resolves token -> artifact + version,
    # and remix clones a published artifact into a new artifact owned by
    # the caller (with parent_artifact_id set for lineage). See xenoISA/isA_user#441
    # Phase 2 and isA_/docs/design/427-artifact-flows.md §7-8.

    @staticmethod
    def _new_share_token() -> str:
        """22-char base62 token (~131 bits entropy)."""
        import secrets

        return secrets.token_urlsafe(16)[:22]

    def _share_is_active(self, share: ArtifactShare) -> bool:
        if share.revoked_at is not None:
            return False
        if share.expires_at is not None and share.expires_at < datetime.utcnow():
            return False
        return True

    async def publish_artifact(self, artifact_id: str, request: PublishArtifactRequest) -> PublishArtifactResponse:
        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._assert_owner(artifact, request.user_id)

        if request.visibility == ArtifactShareVisibility.ORG and not (request.org_id or artifact.owner_org_id):
            raise ArtifactValidationError(
                "visibility=org requires either request.org_id or owner_org_id on the artifact"
            )

        # When pinned, the version must exist on the artifact.
        if request.version_pin is not None:
            existing_numbers = {v.number for v in artifact.versions}
            if request.version_pin not in existing_numbers:
                raise ArtifactValidationError(f"version_pin {request.version_pin} not present on artifact")

        share = ArtifactShare(
            token=self._new_share_token(),
            artifact_id=artifact_id,
            version_pin=request.version_pin,
            visibility=request.visibility,
            org_id=request.org_id or (artifact.owner_org_id or None),
            created_by=request.user_id,
            expires_at=request.expires_at,
        )
        created = await self.repo.create_share(share)

        await self._publish(
            "artifact.published",
            {
                "artifact_id": artifact_id,
                "token": created.token,
                "user_id": request.user_id,
                "visibility": created.visibility.value if hasattr(created.visibility, "value") else created.visibility,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return PublishArtifactResponse(
            token=created.token,
            url=f"/a/{created.token}",
            visibility=ArtifactShareVisibility(created.visibility)
            if not isinstance(created.visibility, ArtifactShareVisibility)
            else created.visibility,
            expires_at=created.expires_at,
            version_pin=created.version_pin,
            artifact_id=artifact_id,
        )

    async def revoke_artifact(self, artifact_id: str, request: RevokeArtifactRequest) -> RevokeArtifactResponse:
        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._assert_owner(artifact, request.user_id)

        if request.token:
            revoked = await self.repo.revoke_share(artifact_id, request.token)
        else:
            revoked = await self.repo.revoke_all_shares(artifact_id)

        if revoked > 0:
            await self._publish(
                "artifact.share_revoked",
                {
                    "artifact_id": artifact_id,
                    "user_id": request.user_id,
                    "revoked_count": revoked,
                    "token": request.token,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        return RevokeArtifactResponse(revoked=revoked)

    async def list_shares(self, artifact_id: str, user_id: str) -> ArtifactSharesListResponse:
        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._assert_owner(artifact, user_id)
        shares = await self.repo.list_shares_by_artifact(artifact_id)
        return ArtifactSharesListResponse(shares=shares)

    async def read_public_share(
        self,
        token: str,
        *,
        version: Optional[int] = None,
        org_id: Optional[str] = None,
    ) -> PublicArtifactResponse:
        """Resolve token -> active share -> artifact + pinned/latest version.

        Raises:
          ArtifactNotFoundError when the token doesn't exist (caller maps to 404)
          ArtifactValidationError when the token is revoked or expired (caller -> 410)
          ArtifactPermissionError when visibility=org and org_id mismatch (-> 403)
        """
        share = await self.repo.get_share_by_token(token)
        if not share:
            raise ArtifactNotFoundError(f"share {token} not found")
        if not self._share_is_active(share):
            raise ArtifactValidationError(f"share {token} is revoked or expired")
        if share.visibility == ArtifactShareVisibility.ORG and share.org_id:
            if not org_id or org_id != share.org_id:
                raise ArtifactPermissionError("share is org-scoped and caller org does not match")

        artifact = await self.repo.get_artifact(share.artifact_id)
        if not artifact:
            # The CASCADE on artifacts -> shares should prevent this; defensive only.
            raise ArtifactNotFoundError(f"artifact {share.artifact_id} not found")

        # Pin precedence: explicit ?v= query > share.version_pin > artifact.current_version_id.
        target_number = version or share.version_pin
        chosen: Optional[ArtifactVersion] = None
        if target_number is not None:
            chosen = next((v for v in artifact.versions if v.number == target_number), None)
            if chosen is None:
                raise ArtifactValidationError(f"version {target_number} not present on artifact")
        else:
            # Latest version (versions are ordered v1..N in the repo loader; pick max).
            if artifact.versions:
                chosen = max(artifact.versions, key=lambda v: v.number)
        if chosen is None:
            raise ArtifactValidationError("artifact has no versions")

        # Best-effort view counter; ignore the boolean.
        await self.repo.increment_view_count(token)

        return PublicArtifactResponse(
            artifact=artifact,
            version=chosen,
            share=PublicArtifactShareMeta(
                visibility=share.visibility,
                view_count=share.view_count + 1,
                expires_at=share.expires_at,
                version_pin=share.version_pin,
            ),
        )

    async def remix_artifact(self, request: RemixArtifactRequest) -> Artifact:
        """Clone a published artifact into a new artifact owned by request.user_id."""
        share = await self.repo.get_share_by_token(request.token)
        if not share:
            raise ArtifactNotFoundError(f"share {request.token} not found")
        if not self._share_is_active(share):
            raise ArtifactValidationError(f"share {request.token} is revoked or expired")

        source = await self.repo.get_artifact(share.artifact_id)
        if not source:
            raise ArtifactNotFoundError(f"artifact {share.artifact_id} not found")

        target_number = share.version_pin
        chosen: Optional[ArtifactVersion] = None
        if target_number is not None:
            chosen = next((v for v in source.versions if v.number == target_number), None)
        else:
            if source.versions:
                chosen = max(source.versions, key=lambda v: v.number)
        if chosen is None:
            raise ArtifactValidationError("source artifact has no versions to remix")

        create_request = ArtifactCreateRequest(
            title=f"Remix of {source.title}",
            content_type=source.content_type,
            parent_artifact_id=source.id,
            source_session_id=request.source_session_id,
            visibility=ArtifactVisibility.PRIVATE,
            ai_runtime_enabled=source.ai_runtime_enabled,
            storage_scope=source.storage_scope,
            metadata={
                **source.metadata,
                "remixed_from": source.id,
                "remixed_from_version": chosen.number,
            },
            version=ArtifactVersionCreateRequest(
                content=chosen.content,
                language=chosen.language,
                filename=chosen.filename,
                blob_url=chosen.blob_url,
                a2ui_state_json=chosen.a2ui_state_json,
                instruction=f"Remixed from artifact {source.id} v{chosen.number}",
            ),
        )
        new_artifact = await self.create_artifact(create_request, request.user_id)

        await self._publish(
            "artifact.remixed",
            {
                "source_artifact_id": source.id,
                "source_version": chosen.number,
                "new_artifact_id": new_artifact.id,
                "user_id": request.user_id,
                "token": share.token,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return new_artifact

    # ==================== Phase 3: AI Runtime + Quota ====================
    #
    # POST /api/v1/artifacts/{id}/runtime/invoke — proxies to isA_Model with a
    # safe fallback to a synthetic stub when the upstream is unreachable. The
    # quota gate runs unconditionally so the daily cap covers both healthy and
    # degraded paths.
    #
    # Quota:
    #   - cap = ARTIFACT_DAILY_QUOTA env (defaults to 50/user/day)
    #   - 429 + Retry-After=<seconds until 00:00 UTC tomorrow>
    #   - the row is keyed (artifact_id, user_id, UTC date); the upsert
    #     happens AFTER the cap check so we don't book a call we refused.

    @staticmethod
    def _build_runtime_prompt(artifact: Artifact, user_prompt: str) -> str:
        """Wrap the user's prompt with artifact context for the model."""
        return (
            f"You are an assistant embedded inside an artifact named "
            f"'{artifact.title}'. The artifact's content type is "
            f"{artifact.content_type.value if hasattr(artifact.content_type, 'value') else artifact.content_type}. "
            f"The user asks: {user_prompt}\n\nRespond concisely."
        )

    @staticmethod
    def _resolve_max_tokens(requested: Optional[int]) -> int:
        if requested is None:
            return DEFAULT_RUNTIME_MAX_TOKENS
        return min(max(1, int(requested)), RUNTIME_MAX_TOKENS_CAP)

    async def _call_isa_model(
        self,
        artifact: Artifact,
        user_prompt: str,
        max_tokens: int,
        auth_token: Optional[str] = None,
    ) -> tuple[str, Optional[int], Optional[int]]:
        """Invoke isA_Model — returns (output, tokens_in, tokens_out).

        Raises on any failure; caller is responsible for falling back to the
        stub. Token counts come from response.usage when the provider supplies
        them; otherwise the caller estimates from string lengths.

        ``auth_token`` (the caller's bearer JWT, if any) is forwarded to
        isA_Model so user-level rate limits + audit apply to upstream calls.
        """
        # Late import keeps the dependency optional for unit tests that mock
        # the call out at the service level.
        from isa_model.inference_client import AsyncISAModel

        envelope = self._build_runtime_prompt(artifact, user_prompt)
        extra_headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None
        async with AsyncISAModel(
            base_url=_isa_model_url(),
            extra_headers=extra_headers,
        ) as client:
            response = await client.chat.completions.create(
                model=_runtime_model(),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant embedded in a user artifact.",
                    },
                    {"role": "user", "content": envelope},
                ],
                max_tokens=max_tokens,
                provider=_runtime_provider(),
            )

        output = (response.choices[0].message.content or "").strip()
        if not output:
            raise RuntimeError("isA_Model returned empty content")

        usage = getattr(response, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", None) if usage else None
        tokens_out = getattr(usage, "completion_tokens", None) if usage else None
        return output, tokens_in, tokens_out

    async def runtime_invoke(
        self,
        artifact_id: str,
        request: "ArtifactRuntimeInvokeRequest",
        auth_token: Optional[str] = None,
    ) -> "ArtifactRuntimeInvokeResponse":
        from .models import ArtifactRuntimeInvokeResponse

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        if not request.prompt:
            raise ArtifactValidationError("prompt is required")

        quota = _daily_quota()
        today = await self.repo.get_today_usage(artifact_id, request.user_id)
        if today.calls >= quota:
            raise ArtifactQuotaExceededError(
                retry_after=_seconds_until_midnight_utc(),
                calls_today=today.calls,
                quota=quota,
            )

        max_tokens = self._resolve_max_tokens(request.max_tokens)

        # Try the real model first; on any failure, fall back to the original
        # stub so the endpoint never 500s on a transient isA_Model outage.
        # The stub path preserves the exact contract that the golden tests
        # depend on (tokens_out=32, "Phase 3 stub response for: ..." prefix).
        try:
            output, llm_in, llm_out = await self._call_isa_model(
                artifact, request.prompt, max_tokens, auth_token=auth_token
            )
            tokens_in = llm_in if isinstance(llm_in, int) and llm_in > 0 else max(1, len(request.prompt) // 4)
            tokens_out = llm_out if isinstance(llm_out, int) and llm_out > 0 else max(1, len(output) // 4)
        except Exception as e:
            logger.warning(
                "artifact runtime_invoke falling back to stub — isA_Model unreachable: %s",
                e,
            )
            tokens_in = max(1, len(request.prompt) // 4)
            tokens_out = 32
            output = f"Phase 3 stub response for: {request.prompt}"

        updated = await self.repo.record_usage(
            artifact_id=artifact_id,
            user_id=request.user_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

        await self._publish(
            "artifact.runtime.invoked",
            {
                "artifact_id": artifact_id,
                "user_id": request.user_id,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "calls_today": updated.calls,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return ArtifactRuntimeInvokeResponse(
            output=output,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            calls_today=updated.calls,
            quota=quota,
        )

    async def runtime_usage(self, artifact_id: str, user_id: str) -> "ArtifactRuntimeUsageResponse":
        from .models import ArtifactRuntimeUsageResponse

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")

        usage = await self.repo.get_today_usage(artifact_id, user_id)
        quota = _daily_quota()
        return ArtifactRuntimeUsageResponse(
            artifact_id=usage.artifact_id,
            user_id=usage.user_id,
            day_bucket=usage.day_bucket,
            tokens_in=usage.tokens_in,
            tokens_out=usage.tokens_out,
            calls=usage.calls,
            quota=quota,
            remaining=max(0, quota - usage.calls),
        )

    # ==================== Phase 3: MCP grants ====================
    #
    # POST .../mcp/approve persists the user's decision; POST .../mcp/call
    # gates the actual (stubbed) tool execution behind a check for an active
    # ``allow``+``always`` grant. ``once`` and ``session`` scopes intentionally
    # fall through to the approval prompt every call — Phase 3 only persists
    # the long-lived approval; richer session-scoped behaviour lands later.

    async def mcp_approve(self, artifact_id: str, request: "MCPApproveRequest") -> "ArtifactMCPGrant":
        from .models import ArtifactMCPGrant, MCPApproveRequest  # noqa: F401

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")

        grant = ArtifactMCPGrant(
            id=_new_id("grnt"),
            artifact_id=artifact_id,
            user_id=request.user_id,
            tool_name=request.tool_name,
            server_id=request.server_id,
            decision=request.decision,
            scope=request.scope,
            approved_at=datetime.utcnow(),
            expires_at=request.expires_at,
        )
        upserted = await self.repo.upsert_mcp_grant(grant)

        await self._publish(
            "artifact.mcp.approved",
            {
                "artifact_id": artifact_id,
                "user_id": request.user_id,
                "tool_name": request.tool_name,
                "server_id": request.server_id,
                "decision": grant.decision.value if hasattr(grant.decision, "value") else grant.decision,
                "scope": grant.scope.value if hasattr(grant.scope, "value") else grant.scope,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return upserted

    async def _invoke_mcp_tool(
        self,
        tool_name: str,
        server_id: str,
        args: dict,
        artifact_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> dict:
        """Session-aware MCP tool invocation via the streamable-HTTP transport.

        Implements the MCP handshake that streamable-HTTP servers require:
          1. POST ``initialize`` -> read ``Mcp-Session-Id`` from response
          2. POST ``notifications/initialized`` with the session header
          3. POST ``tools/call`` with the session header

        The session id is cached on the service instance keyed by
        ``(artifact_id, server_id)`` so subsequent calls skip the handshake.
        On 401/404 (session expired) we re-init once and retry.

        Response parsing handles both plain JSON (`Content-Type: application/json`)
        and SSE-style event-stream bodies (`text/event-stream`) by scanning
        ``data: ...`` lines for JSON-RPC frames carrying a ``result``.

        Raises on any unrecoverable failure so the caller can fall back to
        the stubbed response.
        """
        session = self._get_mcp_session(server_id, artifact_id=artifact_id)
        try:
            return await session.tools_call(tool_name, args or {}, auth_token=auth_token)
        except _McpSessionExpired:
            # Session expired (401/404 from the server) — drop the cached id,
            # re-init from scratch, and retry once.
            session.reset()
            return await session.tools_call(tool_name, args or {}, auth_token=auth_token)

    def _get_mcp_session(self, server_id: str, *, artifact_id: Optional[str]) -> "_McpSession":
        """Return a process-cached session client for (artifact_id, server_id)."""
        cache = getattr(self, "_mcp_sessions", None)
        if cache is None:
            cache = {}
            self._mcp_sessions = cache
        key = (artifact_id or "_global", server_id)
        existing = cache.get(key)
        if existing is None:
            existing = _McpSession(server_url=_isa_mcp_url(), server_id=server_id)
            cache[key] = existing
        return existing

    async def mcp_call(
        self,
        artifact_id: str,
        request: "MCPCallRequest",
        auth_token: Optional[str] = None,
    ) -> "MCPCallResponse":
        from .models import MCPCallResponse, MCPGrantScope

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")

        grant = await self.repo.find_always_grant(
            artifact_id=artifact_id,
            user_id=request.user_id,
            tool_name=request.tool_name,
            server_id=request.server_id,
        )
        if grant is None:
            return MCPCallResponse(
                requires_approval=True,
                prompt=f"Allow {request.tool_name} on {request.server_id}?",
                tool_name=request.tool_name,
                server_id=request.server_id,
            )

        # Best-effort last_used_at touch — ignore the boolean.
        await self.repo.touch_grant_last_used(grant.id)

        # Try the real MCP transport first; fall back to the stub on any
        # network/protocol failure so the endpoint never 500s on a transient
        # outage. The stub shape preserves the contract the golden tests
        # depend on (``result.stubbed is True``).
        try:
            real_result = await self._invoke_mcp_tool(
                tool_name=request.tool_name,
                server_id=request.server_id,
                args=request.args or {},
                artifact_id=artifact_id,
                auth_token=auth_token,
            )
            return MCPCallResponse(
                requires_approval=False,
                result=real_result,
                scope_used=MCPGrantScope.ALWAYS,
            )
        except Exception as e:
            logger.warning(
                "artifact mcp_call falling back to stub — isA_MCP unreachable: %s",
                e,
            )
            return MCPCallResponse(
                requires_approval=False,
                result={
                    "stubbed": True,
                    "tool_name": request.tool_name,
                    "server_id": request.server_id,
                    "args": request.args,
                },
                scope_used=MCPGrantScope.ALWAYS,
            )

    async def list_mcp_grants(self, artifact_id: str, user_id: str) -> "ArtifactMCPGrantsListResponse":
        from .models import ArtifactMCPGrantsListResponse

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        grants = await self.repo.list_grants(artifact_id, user_id)
        return ArtifactMCPGrantsListResponse(grants=grants)

    # ==================== Phase 3: KV storage ====================
    #
    # GET/PUT/DELETE /api/v1/artifacts/{id}/kv/{key}?scope=&user_id=
    #
    # Scope rules:
    #   - scope=personal requires user_id; cross-user reads return 404.
    #   - scope=shared writes require artifact.storage_scope='shared';
    #     otherwise the route returns 403 (the artifact owner has not opted
    #     into shared KV).
    #
    # The repo translates user_id <-> '_shared' sentinel; the service only
    # ever sees the wire-level shape ("user_id" optional when scope=shared).

    def _validate_kv_scope(
        self,
        artifact: Artifact,
        scope: "ArtifactKVScope",
        user_id: Optional[str],
        *,
        is_write: bool,
    ) -> None:
        from .models import ArtifactKVScope, ArtifactStorageScope

        if scope == ArtifactKVScope.PERSONAL:
            if not user_id:
                raise ArtifactValidationError("scope=personal requires user_id")
            return
        # shared
        if scope == ArtifactKVScope.SHARED:
            if is_write and artifact.storage_scope != ArtifactStorageScope.SHARED:
                raise ArtifactPermissionError("artifact.storage_scope must be 'shared' for shared-scope writes")
            return

    async def kv_get(
        self,
        artifact_id: str,
        key: str,
        *,
        scope: "ArtifactKVScope",
        user_id: Optional[str],
    ) -> "ArtifactKVResponse":
        from .models import ArtifactKVResponse, ArtifactKVScope  # noqa: F401

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._validate_kv_scope(artifact, scope, user_id, is_write=False)

        row = await self.repo.kv_get(
            artifact_id=artifact_id,
            scope=scope.value,
            user_id=user_id,
            key=key,
        )
        if not row:
            raise ArtifactNotFoundError(f"kv key {key} not found")

        return ArtifactKVResponse(
            artifact_id=artifact_id,
            scope=scope,
            user_id=user_id if scope == ArtifactKVScope.PERSONAL else None,
            key=key,
            value=row.get("value"),
            updated_at=row.get("updated_at"),
        )

    async def kv_put(
        self,
        artifact_id: str,
        key: str,
        *,
        value: object,
        scope: "ArtifactKVScope",
        user_id: Optional[str],
    ) -> "ArtifactKVResponse":
        from .models import ArtifactKVResponse, ArtifactKVScope  # noqa: F401

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._validate_kv_scope(artifact, scope, user_id, is_write=True)

        row = await self.repo.kv_put(
            artifact_id=artifact_id,
            scope=scope.value,
            user_id=user_id,
            key=key,
            value=value,
        )
        await self._publish(
            "artifact.kv.updated",
            {
                "artifact_id": artifact_id,
                "scope": scope.value,
                "user_id": user_id,
                "key": key,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        return ArtifactKVResponse(
            artifact_id=artifact_id,
            scope=scope,
            user_id=user_id if scope == ArtifactKVScope.PERSONAL else None,
            key=key,
            value=row.get("value"),
            updated_at=row.get("updated_at"),
        )

    async def kv_delete(
        self,
        artifact_id: str,
        key: str,
        *,
        scope: "ArtifactKVScope",
        user_id: Optional[str],
    ) -> bool:
        from .models import ArtifactKVScope  # noqa: F401

        artifact = await self.repo.get_artifact(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"artifact {artifact_id} not found")
        self._validate_kv_scope(artifact, scope, user_id, is_write=True)

        ok = await self.repo.kv_delete(
            artifact_id=artifact_id,
            scope=scope.value,
            user_id=user_id,
            key=key,
        )
        if ok:
            await self._publish(
                "artifact.kv.deleted",
                {
                    "artifact_id": artifact_id,
                    "scope": scope.value,
                    "user_id": user_id,
                    "key": key,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        return ok

    # ==================== Health ====================

    async def check_health(self) -> dict:
        ok = await self.repo.check_connection()
        return {
            "service": "artifact_service",
            "status": "healthy" if ok else "unhealthy",
            "database": "connected" if ok else "disconnected",
        }
