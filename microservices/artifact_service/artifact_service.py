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
import uuid
from datetime import datetime
from typing import Optional

from core.nats_client import Event

from .models import (
    Artifact,
    ArtifactCreateRequest,
    ArtifactScope,
    ArtifactShare,
    ArtifactShareVisibility,
    ArtifactSharesListResponse,
    ArtifactUpdateRequest,
    ArtifactVersion,
    ArtifactVersionCreateRequest,
    ArtifactVisibility,
    ArtifactListItem,
    ArtifactListResponse,
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

    # ==================== Health ====================

    async def check_health(self) -> dict:
        ok = await self.repo.check_connection()
        return {
            "service": "artifact_service",
            "status": "healthy" if ok else "unhealthy",
            "database": "connected" if ok else "disconnected",
        }
