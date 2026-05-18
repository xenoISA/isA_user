"""
Project Sharing Service Business Logic

Handles invite -> accept -> revoke for project collaboration.

Uses dependency injection for testability:
- Repository is injected, not created at import time
- Event bus is lazily loaded and optional
"""

import logging
import os
import secrets
import string
import sys
from datetime import datetime, timezone
from typing import List, Optional

from .models import (
    AcceptShareRequest,
    CreateShareRequest,
    ProjectShare,
    ProjectShareStatus,
    RevokeResponse,
    ShareListResponse,
    ShareResponse,
    UpdateShareRequest,
)
from .protocols import (
    EventBusProtocol,
    ProjectShareConflictError,
    ProjectShareNotFoundError,
    ProjectShareRepositoryProtocol,
    ProjectShareServiceError,
    ProjectShareValidationError,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.nats_client import Event

logger = logging.getLogger(__name__)

# Base URL for accept links. Frontend handles the /shares/accept/<token> route.
SHARE_ACCEPT_BASE_URL = os.getenv("PROJECT_SHARE_ACCEPT_BASE_URL", "https://app.isa.dev/shares/accept")

# 22-char base62 token => log2(62^22) ~= 131 bits entropy (> 128 required).
_BASE62_ALPHABET = string.ascii_letters + string.digits
_TOKEN_LENGTH = 22


def _generate_invite_token() -> str:
    """Generate a 22-char base62 invite token (~131 bits entropy)."""
    return "".join(secrets.choice(_BASE62_ALPHABET) for _ in range(_TOKEN_LENGTH))


class ProjectSharingService:
    """Project share / invitation business logic."""

    def __init__(
        self,
        share_repo: Optional[ProjectShareRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        config=None,
    ):
        self._share_repo = share_repo
        self.event_bus = event_bus
        self._config = config
        self._repos_initialized = False

    def _ensure_repos_initialized(self):
        """Lazy initialization of the repository if not injected."""
        if self._repos_initialized:
            return
        if self._share_repo is None:
            from .project_share_repository import ProjectShareRepository

            self._share_repo = ProjectShareRepository(config=self._config)
        self._repos_initialized = True

    @property
    def share_repo(self) -> ProjectShareRepositoryProtocol:
        self._ensure_repos_initialized()
        return self._share_repo

    # ========================================================================
    # Invite
    # ========================================================================

    async def invite(self, project_id: str, request: CreateShareRequest) -> ShareResponse:
        """Invite a user to a project.

        If a pending invite already exists for (project_id, lower(email)),
        return that same row (idempotent) instead of creating a duplicate.
        """
        try:
            existing = await self.share_repo.find_pending_by_email(project_id, request.invitee_email)
            if existing is not None:
                logger.info(
                    "Idempotent invite: returning existing pending share %s for project %s",
                    existing.id,
                    project_id,
                )
                return self._share_to_response(existing)

            token = _generate_invite_token()
            share_data = {
                "project_id": project_id,
                "invitee_email": request.invitee_email,
                "role": request.role.value,
                "invite_token": token,
                "status": ProjectShareStatus.PENDING.value,
            }

            share = await self.share_repo.create_share(share_data)
            if not share:
                raise ProjectShareServiceError("Failed to create project share")

            logger.info(
                "Project share created: %s for project %s (%s, role=%s)",
                share.id,
                project_id,
                request.invitee_email,
                request.role.value,
            )

            await self._publish_event(
                "project_share.created",
                {
                    "share_id": share.id,
                    "project_id": project_id,
                    "invitee_email": request.invitee_email,
                    "role": request.role.value,
                    "invite_token": token,
                },
            )

            return self._share_to_response(share)
        except ProjectShareServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating share: {e}", exc_info=True)
            raise ProjectShareServiceError(f"Failed to create share: {str(e)}")

    # ========================================================================
    # List
    # ========================================================================

    async def list_shares(self, project_id: str, status: Optional[str] = None) -> ShareListResponse:
        """List shares for a project, optionally filtered by status."""
        try:
            if status is not None:
                # Validate against the enum to catch typos early.
                try:
                    ProjectShareStatus(status)
                except ValueError as exc:
                    raise ProjectShareValidationError(
                        f"Invalid status filter: {status!r}. Allowed: pending, accepted, revoked"
                    ) from exc

            shares: List[ProjectShare] = await self.share_repo.list_for_project(project_id, status=status)
            return ShareListResponse(
                shares=[self._share_to_response(s) for s in shares],
                total=len(shares),
            )
        except ProjectShareValidationError:
            raise
        except Exception as e:
            logger.error(f"Error listing shares: {e}", exc_info=True)
            raise ProjectShareServiceError(f"Failed to list shares: {str(e)}")

    # ========================================================================
    # Update role
    # ========================================================================

    async def update_role(self, project_id: str, share_id: str, request: UpdateShareRequest) -> ShareResponse:
        """Patch the role on an existing share row."""
        try:
            share = await self.share_repo.get_by_id(share_id)
            if share is None or share.project_id != project_id:
                raise ProjectShareNotFoundError(f"Share {share_id} not found for project {project_id}")

            updated = await self.share_repo.update_role(share_id, request.role.value)
            if updated is None:
                raise ProjectShareServiceError("Failed to update share role")

            await self._publish_event(
                "project_share.role_updated",
                {
                    "share_id": share_id,
                    "project_id": project_id,
                    "role": request.role.value,
                },
            )
            return self._share_to_response(updated)
        except (ProjectShareNotFoundError, ProjectShareServiceError):
            raise
        except Exception as e:
            logger.error(f"Error updating role: {e}", exc_info=True)
            raise ProjectShareServiceError(f"Failed to update role: {str(e)}")

    # ========================================================================
    # Revoke
    # ========================================================================

    async def revoke(self, project_id: str, share_id: str) -> RevokeResponse:
        """Revoke a share: status=revoked, revoked_at=now, invite_token nulled."""
        try:
            share = await self.share_repo.get_by_id(share_id)
            if share is None or share.project_id != project_id:
                raise ProjectShareNotFoundError(f"Share {share_id} not found for project {project_id}")

            if share.status == ProjectShareStatus.REVOKED:
                # Idempotent revoke
                return RevokeResponse(
                    id=share.id,
                    project_id=share.project_id,
                    status=share.status,
                    revoked_at=share.revoked_at,
                )

            revoked = await self.share_repo.revoke(share_id)
            if revoked is None:
                raise ProjectShareServiceError("Failed to revoke share")

            await self._publish_event(
                "project_share.revoked",
                {
                    "share_id": share_id,
                    "project_id": project_id,
                },
            )

            return RevokeResponse(
                id=revoked.id,
                project_id=revoked.project_id,
                status=revoked.status,
                revoked_at=revoked.revoked_at,
            )
        except (ProjectShareNotFoundError, ProjectShareServiceError):
            raise
        except Exception as e:
            logger.error(f"Error revoking share: {e}", exc_info=True)
            raise ProjectShareServiceError(f"Failed to revoke share: {str(e)}")

    # ========================================================================
    # Accept
    # ========================================================================

    async def accept(self, token: str, request: AcceptShareRequest) -> ShareResponse:
        """Accept an invite by token.

        404 if the token is unknown OR has been revoked (token is nulled on revoke,
        so the lookup naturally returns None).
        Idempotent on already-accepted invites: returns the current row.
        """
        try:
            share = await self.share_repo.get_by_token(token)
            if share is None:
                raise ProjectShareNotFoundError("Invite token not found or has been revoked")

            if share.status == ProjectShareStatus.REVOKED:
                # Defense in depth — the token should already be NULL after revoke.
                raise ProjectShareNotFoundError("Invite token has been revoked")

            if share.status == ProjectShareStatus.ACCEPTED:
                # Idempotent: already accepted. Return the current row.
                logger.info("Accept on already-accepted share %s (idempotent)", share.id)
                return self._share_to_response(share)

            accepted = await self.share_repo.mark_accepted(share.id, request.invitee_user_id)
            if accepted is None:
                raise ProjectShareServiceError("Failed to accept invite")

            await self._publish_event(
                "project_share.accepted",
                {
                    "share_id": accepted.id,
                    "project_id": accepted.project_id,
                    "invitee_user_id": request.invitee_user_id,
                },
            )
            return self._share_to_response(accepted)
        except (ProjectShareNotFoundError, ProjectShareConflictError, ProjectShareServiceError):
            raise
        except Exception as e:
            logger.error(f"Error accepting share: {e}", exc_info=True)
            raise ProjectShareServiceError(f"Failed to accept share: {str(e)}")

    # ========================================================================
    # Helpers
    # ========================================================================

    def _share_to_response(self, share: ProjectShare) -> ShareResponse:
        """Convert domain model to API response (adds share_url)."""
        share_url = f"{SHARE_ACCEPT_BASE_URL}/{share.invite_token}" if share.invite_token else None
        return ShareResponse(
            id=share.id,
            project_id=share.project_id,
            invitee_user_id=share.invitee_user_id,
            invitee_email=share.invitee_email,
            role=share.role,
            invite_token=share.invite_token,
            share_url=share_url,
            status=share.status,
            created_at=share.created_at,
            accepted_at=share.accepted_at,
            revoked_at=share.revoked_at,
        )

    async def _publish_event(self, event_type: str, data: dict) -> None:
        """Best-effort event publish — never fail a request because NATS is down."""
        if not self.event_bus:
            return
        try:
            event = Event(
                event_type=event_type,
                source="project_sharing_service",
                data={
                    **data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
        except Exception as e:
            logger.error(f"Failed to publish {event_type}: {e}")
