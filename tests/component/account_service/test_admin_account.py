"""
Component tests for admin account management endpoints (#193).

Tests the new admin endpoints with a mocked repository:
- GET  /api/v1/account/admin/accounts/{user_id}  (account detail)
- PUT  /api/v1/account/admin/accounts/{user_id}/status  (status change)
- POST /api/v1/account/admin/accounts/{user_id}/note  (add note)

Uses MockAccountRepository extended with the new repo methods.
"""
import pytest
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from microservices.account_service.models import (
    AdminNote,
    AdminAccountDetailResponse,
    AdminNoteResponse,
    AdminStatusUpdateRequest,
    AdminNoteRequest,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


# =============================================================================
# Extended mock repository with new admin methods
# =============================================================================


class MockAdminAccountRepository:
    """Mock repo that supports the new admin methods (get_account_detail,
    update_account_status, add_admin_note) alongside existing methods."""

    def __init__(self):
        self._users: Dict[str, Dict[str, Any]] = {}
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._notes: Dict[str, List[AdminNote]] = {}

    def seed_user(
        self,
        user_id: str,
        email: str = "test@example.com",
        name: str = "Test User",
        is_active: bool = True,
        admin_roles: Optional[List[str]] = None,
        account_status: str = "active",
        status_reason: Optional[str] = None,
    ):
        from microservices.account_service.models import User

        self._users[user_id] = {
            "user": User(
                user_id=user_id,
                email=email,
                name=name,
                is_active=is_active,
                admin_roles=admin_roles,
                preferences={},
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
            ),
            "account_status": account_status,
            "status_reason": status_reason,
        }
        self._notes.setdefault(user_id, [])

    async def get_account_by_id_include_inactive(self, user_id: str):
        entry = self._users.get(user_id)
        return entry["user"] if entry else None

    async def get_account_detail(self, user_id: str) -> Optional[Dict[str, Any]]:
        entry = self._users.get(user_id)
        if not entry:
            return None
        user = entry["user"]
        return {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
            "account_status": entry["account_status"],
            "status_reason": entry["status_reason"],
            "admin_roles": user.admin_roles,
            "preferences": user.preferences,
            "notes": self._notes.get(user_id, []),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    async def update_account_status(
        self, user_id: str, status: str, reason: Optional[str] = None
    ) -> bool:
        from microservices.account_service.protocols import UserNotFoundError

        entry = self._users.get(user_id)
        if not entry:
            raise UserNotFoundError(f"Account not found: {user_id}")
        entry["account_status"] = status
        entry["status_reason"] = reason
        # Update is_active based on status
        user = entry["user"]
        from microservices.account_service.models import User

        entry["user"] = User(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            is_active=(status == "active"),
            admin_roles=user.admin_roles,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        return True

    async def add_admin_note(
        self, user_id: str, author_id: str, note: str
    ) -> Optional[AdminNote]:
        from microservices.account_service.protocols import UserNotFoundError

        if user_id not in self._users:
            raise UserNotFoundError(f"Account not found: {user_id}")
        now = datetime.now(timezone.utc)
        admin_note = AdminNote(
            note_id=f"note_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            author_id=author_id,
            note=note,
            created_at=now,
        )
        self._notes.setdefault(user_id, []).append(admin_note)
        return admin_note


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repo():
    repo = MockAdminAccountRepository()
    repo.seed_user(
        user_id="usr_admin_test",
        email="admin.test@example.com",
        name="Admin Test User",
        is_active=True,
        admin_roles=["support_admin"],
        account_status="active",
    )
    repo.seed_user(
        user_id="usr_suspended",
        email="suspended@example.com",
        name="Suspended User",
        is_active=False,
        account_status="suspended",
        status_reason="Policy violation",
    )
    return repo


# =============================================================================
# get_account_detail tests
# =============================================================================


class TestAdminGetAccountDetail:
    """Component: repo.get_account_detail() returns full account info."""

    async def test_returns_detail_for_existing_user(self, mock_repo):
        detail = await mock_repo.get_account_detail("usr_admin_test")
        assert detail is not None
        assert detail["user_id"] == "usr_admin_test"
        assert detail["email"] == "admin.test@example.com"
        assert detail["account_status"] == "active"
        assert detail["admin_roles"] == ["support_admin"]
        assert detail["notes"] == []

    async def test_returns_none_for_missing_user(self, mock_repo):
        detail = await mock_repo.get_account_detail("usr_nonexistent")
        assert detail is None

    async def test_returns_suspended_status(self, mock_repo):
        detail = await mock_repo.get_account_detail("usr_suspended")
        assert detail["account_status"] == "suspended"
        assert detail["status_reason"] == "Policy violation"
        assert detail["is_active"] is False

    async def test_detail_includes_notes(self, mock_repo):
        """After adding a note, get_account_detail should include it."""
        await mock_repo.add_admin_note("usr_admin_test", "admin_1", "Test note")
        detail = await mock_repo.get_account_detail("usr_admin_test")
        assert len(detail["notes"]) == 1
        assert detail["notes"][0].note == "Test note"

    async def test_detail_serializes_to_response_model(self, mock_repo):
        """Detail dict should be valid for AdminAccountDetailResponse."""
        detail = await mock_repo.get_account_detail("usr_admin_test")
        resp = AdminAccountDetailResponse(**detail)
        assert resp.user_id == "usr_admin_test"
        assert resp.account_status == "active"


# =============================================================================
# update_account_status tests
# =============================================================================


class TestAdminUpdateAccountStatus:
    """Component: repo.update_account_status() changes status and is_active."""

    async def test_suspend_active_account(self, mock_repo):
        success = await mock_repo.update_account_status(
            "usr_admin_test", "suspended", "Terms violation"
        )
        assert success is True

        detail = await mock_repo.get_account_detail("usr_admin_test")
        assert detail["account_status"] == "suspended"
        assert detail["status_reason"] == "Terms violation"
        assert detail["is_active"] is False

    async def test_ban_account(self, mock_repo):
        success = await mock_repo.update_account_status(
            "usr_admin_test", "banned", "Fraud"
        )
        assert success is True

        detail = await mock_repo.get_account_detail("usr_admin_test")
        assert detail["account_status"] == "banned"
        assert detail["is_active"] is False

    async def test_reactivate_suspended_account(self, mock_repo):
        success = await mock_repo.update_account_status(
            "usr_suspended", "active", "Reactivation approved"
        )
        assert success is True

        detail = await mock_repo.get_account_detail("usr_suspended")
        assert detail["account_status"] == "active"
        assert detail["is_active"] is True

    async def test_status_update_not_found_raises(self, mock_repo):
        from microservices.account_service.protocols import UserNotFoundError

        with pytest.raises(UserNotFoundError):
            await mock_repo.update_account_status("usr_ghost", "active")


# =============================================================================
# add_admin_note tests
# =============================================================================


class TestAdminAddNote:
    """Component: repo.add_admin_note() persists notes."""

    async def test_add_note_returns_admin_note(self, mock_repo):
        result = await mock_repo.add_admin_note(
            "usr_admin_test", "admin_1", "Called about billing"
        )
        assert result is not None
        assert isinstance(result, AdminNote)
        assert result.user_id == "usr_admin_test"
        assert result.author_id == "admin_1"
        assert result.note == "Called about billing"
        assert result.note_id.startswith("note_")

    async def test_add_multiple_notes(self, mock_repo):
        await mock_repo.add_admin_note("usr_admin_test", "admin_1", "First note")
        await mock_repo.add_admin_note("usr_admin_test", "admin_2", "Second note")

        detail = await mock_repo.get_account_detail("usr_admin_test")
        assert len(detail["notes"]) == 2

    async def test_add_note_not_found_raises(self, mock_repo):
        from microservices.account_service.protocols import UserNotFoundError

        with pytest.raises(UserNotFoundError):
            await mock_repo.add_admin_note("usr_ghost", "admin_1", "Note")

    async def test_note_serializes_to_response_model(self, mock_repo):
        result = await mock_repo.add_admin_note(
            "usr_admin_test", "admin_1", "Serialization test"
        )
        resp = AdminNoteResponse(
            note_id=result.note_id,
            user_id=result.user_id,
            author_id=result.author_id,
            note=result.note,
            created_at=result.created_at,
        )
        assert resp.note_id == result.note_id
