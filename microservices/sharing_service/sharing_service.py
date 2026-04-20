"""
Sharing Service Business Logic

Handles share link generation, access, and revocation.

Uses dependency injection for testability:
- Repository is injected, not created at import time
- Event publishers are lazily loaded
"""

import logging
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .models import (
    Share,
    ShareCreateRequest,
    ShareListResponse,
    SharePermission,
    ShareResponse,
    SharedSessionResponse,
)
from .protocols import (
    EventBusProtocol,
    SessionClientProtocol,
    ShareExpiredError,
    ShareNotFoundError,
    SharePermissionError,
    ShareRepositoryProtocol,
    ShareServiceError,
    ShareValidationError,
)

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from core.nats_client import Event

logger = logging.getLogger(__name__)

# Base URL for share links — override via environment variable
SHARE_BASE_URL = os.getenv("SHARE_BASE_URL", "https://app.isa.dev/s")


class SharingService:
    """
    Share link management business logic service.

    Uses dependency injection for testability.
    """

    def __init__(
        self,
        share_repo: Optional[ShareRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        session_client: Optional[SessionClientProtocol] = None,
        config=None,
    ):
        self._share_repo = share_repo
        self.event_bus = event_bus
        self._session_client = session_client
        self._config = config
        self._repos_initialized = False

    def _ensure_repos_initialized(self):
        """Lazy initialization of repositories if not injected"""
        if self._repos_initialized:
            return

        if self._share_repo is None:
            from .sharing_repository import ShareRepository
            self._share_repo = ShareRepository(config=self._config)

        if self._session_client is None:
            from .clients.session_client import SessionServiceClient
            self._session_client = SessionServiceClient()

        self._repos_initialized = True

    @property
    def share_repo(self) -> ShareRepositoryProtocol:
        self._ensure_repos_initialized()
        return self._share_repo

    @property
    def session_client(self) -> SessionClientProtocol:
        self._ensure_repos_initialized()
        return self._session_client

    # ========================================================================
    # Share Operations
    # ========================================================================

    async def create_share(
        self,
        session_id: str,
        owner_id: str,
        request: ShareCreateRequest,
    ) -> ShareResponse:
        """
        Create a share link for a session.

        Args:
            session_id: Session to share
            owner_id: User creating the share (must own the session)
            request: Share creation parameters

        Returns:
            ShareResponse with token and URL

        Raises:
            ShareValidationError: If session doesn't exist or user doesn't own it
        """
        try:
            # Verify session exists and belongs to this user
            session = await self.session_client.get_session(session_id)
            if not session:
                raise ShareValidationError(f"Session not found: {session_id}")
            if session.get("user_id") != owner_id:
                raise SharePermissionError("You can only share your own sessions")

            # Generate token: 128 bits entropy → 22-char URL-safe base64
            share_token = secrets.token_urlsafe(16)

            # Calculate expiry
            expires_at = None
            if request.expires_in_hours:
                expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=request.expires_in_hours
                )

            share_data = {
                "session_id": session_id,
                "owner_id": owner_id,
                "share_token": share_token,
                "permissions": request.permissions.value,
                "expires_at": expires_at,
            }

            share = await self.share_repo.create_share(share_data)
            if not share:
                raise ShareServiceError("Failed to create share")

            logger.info(
                f"Share created: {share.id} for session {session_id} by {owner_id}"
            )

            # Publish event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="share.created",
                        source="sharing_service",
                        data={
                            "share_id": share.id,
                            "session_id": session_id,
                            "owner_id": owner_id,
                            "share_token": share_token,
                            "permissions": request.permissions.value,
                            "expires_at": expires_at.isoformat() if expires_at else None,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish share.created event: {e}")

            return self._share_to_response(share)

        except (ShareValidationError, SharePermissionError):
            raise
        except Exception as e:
            logger.error(f"Error creating share: {e}", exc_info=True)
            raise ShareServiceError(f"Failed to create share: {str(e)}")

    async def access_share(self, share_token: str) -> SharedSessionResponse:
        """
        Access a shared session via token.

        This is the public endpoint — no auth required, token IS the auth.

        Args:
            share_token: The share token from the URL

        Returns:
            SharedSessionResponse with session data per permissions

        Raises:
            ShareNotFoundError: If token is invalid
            ShareExpiredError: If share has expired
        """
        try:
            share = await self.share_repo.get_by_token(share_token)
            if not share:
                raise ShareNotFoundError("Share link not found or has been revoked")

            # Check expiry
            if share.expires_at and share.expires_at < datetime.now(timezone.utc):
                raise ShareExpiredError("This share link has expired")

            # Increment access count
            await self.share_repo.increment_access_count(share.id)

            # Fetch session data from session service
            session = await self.session_client.get_session(share.session_id)
            if not session:
                raise ShareServiceError("Shared session no longer exists")

            messages = await self.session_client.get_session_messages(
                share.session_id
            )

            # Publish access event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="share.accessed",
                        source="sharing_service",
                        data={
                            "share_id": share.id,
                            "session_id": share.session_id,
                            "share_token": share_token,
                            "access_count": share.access_count + 1,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish share.accessed event: {e}")

            return SharedSessionResponse(
                session_id=share.session_id,
                session_summary=session.get("session_summary", ""),
                permissions=share.permissions,
                messages=messages,
                message_count=len(messages),
                created_at=session.get("created_at"),
                last_activity=session.get("last_activity"),
            )

        except (ShareNotFoundError, ShareExpiredError):
            raise
        except Exception as e:
            logger.error(f"Error accessing share: {e}", exc_info=True)
            raise ShareServiceError(f"Failed to access share: {str(e)}")

    async def revoke_share(self, share_token: str, owner_id: str) -> bool:
        """
        Revoke a share link (owner only).

        Args:
            share_token: Token to revoke
            owner_id: Must match share owner

        Returns:
            True if revoked

        Raises:
            ShareNotFoundError: If token not found
            SharePermissionError: If user doesn't own the share
        """
        try:
            share = await self.share_repo.get_by_token(share_token)
            if not share:
                raise ShareNotFoundError("Share link not found")

            if share.owner_id != owner_id:
                raise SharePermissionError("Only the share owner can revoke it")

            success = await self.share_repo.delete_by_token(share_token)
            if not success:
                raise ShareServiceError("Failed to revoke share")

            logger.info(f"Share revoked: {share.id} by {owner_id}")

            # Publish event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="share.revoked",
                        source="sharing_service",
                        data={
                            "share_id": share.id,
                            "session_id": share.session_id,
                            "owner_id": owner_id,
                            "share_token": share_token,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish share.revoked event: {e}")

            return True

        except (ShareNotFoundError, SharePermissionError):
            raise
        except Exception as e:
            logger.error(f"Error revoking share: {e}", exc_info=True)
            raise ShareServiceError(f"Failed to revoke share: {str(e)}")

    async def list_session_shares(
        self, session_id: str, owner_id: str
    ) -> ShareListResponse:
        """
        List all active shares for a session (owner only).

        Args:
            session_id: Session ID
            owner_id: Must own the session

        Returns:
            ShareListResponse with all shares
        """
        try:
            # Verify session ownership
            session = await self.session_client.get_session(session_id)
            if not session:
                raise ShareValidationError(f"Session not found: {session_id}")
            if session.get("user_id") != owner_id:
                raise SharePermissionError("You can only view shares for your own sessions")

            shares = await self.share_repo.get_session_shares(session_id, owner_id)
            share_responses = [self._share_to_response(s) for s in shares]

            return ShareListResponse(
                shares=share_responses,
                total=len(share_responses),
            )

        except (ShareValidationError, SharePermissionError):
            raise
        except Exception as e:
            logger.error(f"Error listing shares: {e}", exc_info=True)
            raise ShareServiceError(f"Failed to list shares: {str(e)}")

    # ========================================================================
    # Helpers
    # ========================================================================

    def _share_to_response(self, share: Share) -> ShareResponse:
        """Convert Share model to ShareResponse"""
        return ShareResponse(
            id=share.id,
            session_id=share.session_id,
            owner_id=share.owner_id,
            share_token=share.share_token,
            share_url=f"{SHARE_BASE_URL}/{share.share_token}",
            permissions=share.permissions,
            expires_at=share.expires_at,
            access_count=share.access_count,
            created_at=share.created_at,
        )
