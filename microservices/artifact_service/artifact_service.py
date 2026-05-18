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
    # POST /api/v1/artifacts/{id}/runtime/invoke — Phase 3 ships this as a
    # synthetic-response stub (no real LLM call) so we can exercise the quota
    # gate and the per-day usage row end-to-end. The real isA_Model call lands
    # in the follow-up once gateway-issued JWTs reach this service.
    #
    # Quota:
    #   - cap = ARTIFACT_DAILY_QUOTA env (defaults to 50/user/day)
    #   - 429 + Retry-After=<seconds until 00:00 UTC tomorrow>
    #   - the row is keyed (artifact_id, user_id, UTC date); the upsert
    #     happens AFTER the cap check so we don't book a call we refused.

    async def runtime_invoke(
        self, artifact_id: str, request: "ArtifactRuntimeInvokeRequest"
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

        # Stubbed synthesis — replace with isA_Model proxy in follow-up.
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

    async def mcp_call(self, artifact_id: str, request: "MCPCallRequest") -> "MCPCallResponse":
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

        # Stubbed tool result — replace with real MCP transport in follow-up.
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
