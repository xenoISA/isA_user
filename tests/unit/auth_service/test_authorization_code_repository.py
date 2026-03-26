"""
Unit tests for AuthorizationCodeRepository.

Tests:
- create_code returns a dict with code_id
- get_code retrieves by code_value
- mark_used enforces single-use (returns False on second call)
- delete_expired removes old codes

All DB calls are mocked — no real PostgreSQL needed.

Covers: xenoISA/isA_user#162
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mock_db():
    """Create a mock AsyncPostgresClient with async context manager support."""
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.execute = AsyncMock()
    mock_db.query_row = AsyncMock()
    mock_db.query = AsyncMock()
    return mock_db


@pytest.fixture
def mock_db():
    return _make_mock_db()


@pytest.fixture
def repo(mock_db):
    """Create an AuthorizationCodeRepository with a mocked DB client."""
    with patch(
        "microservices.auth_service.authorization_code_repository.AsyncPostgresClient",
        return_value=mock_db,
    ), patch(
        "microservices.auth_service.authorization_code_repository.ConfigManager",
    ) as mock_cfg_cls:
        mock_cfg = MagicMock()
        mock_cfg.discover_service.return_value = ("localhost", 5432)
        mock_cfg_cls.return_value = mock_cfg

        from microservices.auth_service.authorization_code_repository import (
            AuthorizationCodeRepository,
        )

        repository = AuthorizationCodeRepository()
        repository.db = mock_db
        # Skip table init in tests
        repository._table_initialized = True
        return repository


@pytest.fixture
def sample_code_params():
    """Standard parameters for creating an authorization code."""
    return {
        "client_id": "a2a_test_client_001",
        "redirect_uri": "https://example.com/callback",
        "state": "random-state-value",
        "resource": "https://api.example.com",
        "scopes": ["read", "write"],
        "user_id": "usr_test_001",
        "organization_id": "org_test_001",
        "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
        "code_challenge_method": "S256",
        "code_value": "auth_code_abc123",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateCode:
    """Test AuthorizationCodeRepository.create_code."""

    @pytest.mark.asyncio
    async def test_create_code_returns_id(self, repo, mock_db, sample_code_params):
        """create_code should return a dict containing a code_id."""
        generated_id = uuid.uuid4()
        mock_db.query_row.return_value = {"code_id": generated_id}

        result = await repo.create_code(**sample_code_params)

        assert result is not None
        assert result["code_id"] == str(generated_id)
        assert result["client_id"] == sample_code_params["client_id"]
        assert result["code_value"] == sample_code_params["code_value"]
        assert result["is_used"] is False

        # Verify DB was called
        mock_db.query_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_code_defaults_approved_scopes(self, repo, mock_db, sample_code_params):
        """When approved_scopes is not provided, it should default to scopes."""
        mock_db.query_row.return_value = {"code_id": uuid.uuid4()}

        result = await repo.create_code(**sample_code_params)

        assert result["approved_scopes"] == sample_code_params["scopes"]

    @pytest.mark.asyncio
    async def test_create_code_with_explicit_approved_scopes(self, repo, mock_db, sample_code_params):
        """When approved_scopes is explicitly provided, it should be used."""
        mock_db.query_row.return_value = {"code_id": uuid.uuid4()}

        sample_code_params["approved_scopes"] = ["read"]
        result = await repo.create_code(**sample_code_params)

        assert result["approved_scopes"] == ["read"]


class TestGetCode:
    """Test AuthorizationCodeRepository.get_code."""

    @pytest.mark.asyncio
    async def test_get_code_returns_data(self, repo, mock_db):
        """get_code should return the full code record when found."""
        code_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=10)

        mock_db.query_row.return_value = {
            "code_id": code_id,
            "client_id": "a2a_test_client",
            "redirect_uri": "https://example.com/callback",
            "state": "state-123",
            "resource": "https://api.example.com",
            "scopes": ["read"],
            "approved_scopes": ["read"],
            "user_id": "usr_test_001",
            "organization_id": "org_test_001",
            "code_challenge": "challenge",
            "code_challenge_method": "S256",
            "code_value": "the-code-value",
            "is_used": False,
            "used_at": None,
            "created_at": now,
            "expires_at": expires,
        }

        result = await repo.get_code("the-code-value")

        assert result is not None
        assert result["code_id"] == str(code_id)
        assert result["client_id"] == "a2a_test_client"
        assert result["code_value"] == "the-code-value"
        assert result["is_used"] is False

    @pytest.mark.asyncio
    async def test_get_code_returns_none_when_not_found(self, repo, mock_db):
        """get_code should return None for a non-existent code_value."""
        mock_db.query_row.return_value = None

        result = await repo.get_code("nonexistent-code")

        assert result is None


class TestMarkUsed:
    """Test AuthorizationCodeRepository.mark_used (single-use enforcement)."""

    @pytest.mark.asyncio
    async def test_mark_used_returns_true_on_first_use(self, repo, mock_db):
        """mark_used should return True when the code has not been used yet."""
        mock_db.execute.return_value = 1  # 1 row updated

        result = await repo.mark_used("some-code-id")

        assert result is True

    @pytest.mark.asyncio
    async def test_mark_used_prevents_reuse(self, repo, mock_db):
        """mark_used should return False if the code was already used."""
        mock_db.execute.return_value = 0  # 0 rows updated (already used)

        result = await repo.mark_used("already-used-code-id")

        assert result is False


class TestDeleteExpired:
    """Test AuthorizationCodeRepository.delete_expired."""

    @pytest.mark.asyncio
    async def test_expired_code_cleanup(self, repo, mock_db):
        """delete_expired should return the count of deleted rows."""
        mock_db.execute.return_value = 5  # 5 rows deleted

        count = await repo.delete_expired()

        assert count == 5
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_expired_returns_zero_when_none_expired(self, repo, mock_db):
        """delete_expired should return 0 when no codes are expired."""
        mock_db.execute.return_value = 0

        count = await repo.delete_expired()

        assert count == 0
