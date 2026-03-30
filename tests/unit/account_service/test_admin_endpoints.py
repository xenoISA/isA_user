"""
Unit tests for admin endpoint models and validation (#193).

Tests model validation rules for the new admin management models:
- AdminStatusUpdateRequest
- AdminNoteRequest
- AdminAccountDetailResponse

No I/O, no mocks -- pure model validation.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from microservices.account_service.models import (
    ACCOUNT_STATUSES,
    AdminStatusUpdateRequest,
    AdminNoteRequest,
    AdminNote,
    AdminAccountDetailResponse,
    AdminNoteResponse,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


# =============================================================================
# AdminStatusUpdateRequest validation
# =============================================================================


class TestAdminStatusUpdateRequest:
    """Validate AdminStatusUpdateRequest model constraints."""

    def test_valid_statuses(self):
        """Each allowed status value should be accepted."""
        for s in ACCOUNT_STATUSES:
            req = AdminStatusUpdateRequest(status=s)
            assert req.status == s

    def test_invalid_status_rejected(self):
        """Unknown status values should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            AdminStatusUpdateRequest(status="deleted")
        assert "status" in str(exc_info.value).lower()

    def test_reason_is_optional(self):
        """reason can be omitted."""
        req = AdminStatusUpdateRequest(status="suspended")
        assert req.reason is None

    def test_reason_accepted(self):
        """reason is stored when provided."""
        req = AdminStatusUpdateRequest(status="banned", reason="Abuse detected")
        assert req.reason == "Abuse detected"

    def test_reason_max_length(self):
        """reason exceeding 500 chars should fail."""
        with pytest.raises(ValidationError):
            AdminStatusUpdateRequest(status="suspended", reason="x" * 501)

    def test_status_required(self):
        """Missing status should fail."""
        with pytest.raises(ValidationError):
            AdminStatusUpdateRequest()


# =============================================================================
# AdminNoteRequest validation
# =============================================================================


class TestAdminNoteRequest:
    """Validate AdminNoteRequest model constraints."""

    def test_valid_note(self):
        req = AdminNoteRequest(note="Customer called about billing issue")
        assert req.note == "Customer called about billing issue"

    def test_empty_note_rejected(self):
        """Empty string should fail min_length=1."""
        with pytest.raises(ValidationError):
            AdminNoteRequest(note="")

    def test_note_max_length(self):
        """Note exceeding 2000 chars should fail."""
        with pytest.raises(ValidationError):
            AdminNoteRequest(note="x" * 2001)

    def test_note_required(self):
        with pytest.raises(ValidationError):
            AdminNoteRequest()


# =============================================================================
# AdminNote model
# =============================================================================


class TestAdminNote:
    """Validate AdminNote data model."""

    def test_create_note(self):
        now = datetime.now(timezone.utc)
        note = AdminNote(
            note_id="note_abc123",
            user_id="usr_1",
            author_id="admin_1",
            note="Support note",
            created_at=now,
        )
        assert note.note_id == "note_abc123"
        assert note.user_id == "usr_1"
        assert note.author_id == "admin_1"
        assert note.created_at == now


# =============================================================================
# AdminAccountDetailResponse model
# =============================================================================


class TestAdminAccountDetailResponse:
    """Validate AdminAccountDetailResponse model."""

    def test_minimal_detail(self):
        resp = AdminAccountDetailResponse(
            user_id="usr_1",
            is_active=True,
        )
        assert resp.user_id == "usr_1"
        assert resp.account_status == "active"
        assert resp.notes == []
        assert resp.admin_roles is None

    def test_full_detail(self):
        now = datetime.now(timezone.utc)
        note = AdminNote(
            note_id="note_1",
            user_id="usr_1",
            author_id="admin_1",
            note="Test note",
            created_at=now,
        )
        resp = AdminAccountDetailResponse(
            user_id="usr_1",
            email="test@example.com",
            name="Test User",
            is_active=False,
            account_status="suspended",
            status_reason="Policy violation",
            admin_roles=["super_admin"],
            preferences={"theme": "dark"},
            notes=[note],
            created_at=now,
            updated_at=now,
        )
        assert resp.account_status == "suspended"
        assert resp.status_reason == "Policy violation"
        assert len(resp.notes) == 1
        assert resp.notes[0].note_id == "note_1"


# =============================================================================
# AdminNoteResponse model
# =============================================================================


class TestAdminNoteResponse:
    """Validate AdminNoteResponse model."""

    def test_create_response(self):
        now = datetime.now(timezone.utc)
        resp = AdminNoteResponse(
            note_id="note_abc",
            user_id="usr_1",
            author_id="admin_1",
            note="Response note",
            created_at=now,
        )
        assert resp.note_id == "note_abc"
        assert resp.author_id == "admin_1"
