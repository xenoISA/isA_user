"""
Unit tests for ClientIdMetadataService.

Tests:
- is_metadata_client_id detection (HTTPS URLs vs plain strings)
- _validate_metadata (valid doc, missing redirect_uris, non-dict)
- get_or_fetch (memory cache hit, expired cache refetch)
- _fetch_metadata (success, too large, non-200)
- invalidate (cache cleared)

All HTTP calls are mocked — no real network needed.

Covers: xenoISA/isA_user#166
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from microservices.auth_service.client_id_metadata_service import (
    ClientIdMetadataService,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_METADATA = {
    "client_name": "Test App",
    "redirect_uris": ["https://app.example.com/callback"],
    "client_type": "public",
    "grant_types": ["authorization_code"],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return ClientIdMetadataService()


@pytest.fixture
def service_with_repo():
    repo = MagicMock()
    repo.get_metadata = AsyncMock(return_value=None)
    repo.upsert_metadata = AsyncMock()
    return ClientIdMetadataService(metadata_repo=repo), repo


# ---------------------------------------------------------------------------
# is_metadata_client_id
# ---------------------------------------------------------------------------


class TestIsMetadataClientId:
    def test_https_url_returns_true(self, service):
        assert service.is_metadata_client_id("https://app.example.com") is True

    def test_http_url_returns_true(self, service):
        assert service.is_metadata_client_id("http://localhost:8080") is True

    def test_normal_string_returns_false(self, service):
        assert service.is_metadata_client_id("my-desktop-app") is False

    def test_empty_string_returns_false(self, service):
        assert service.is_metadata_client_id("") is False


# ---------------------------------------------------------------------------
# _validate_metadata
# ---------------------------------------------------------------------------


class TestValidateMetadata:
    def test_valid_document(self, service):
        assert service._validate_metadata(VALID_METADATA) is True

    def test_missing_redirect_uris(self, service):
        doc = {"client_name": "Test App"}
        assert service._validate_metadata(doc) is False

    def test_empty_redirect_uris(self, service):
        doc = {"client_name": "Test App", "redirect_uris": []}
        assert service._validate_metadata(doc) is False

    def test_not_a_dict(self, service):
        assert service._validate_metadata("not a dict") is False

    def test_redirect_uris_not_list(self, service):
        doc = {"redirect_uris": "https://example.com/callback"}
        assert service._validate_metadata(doc) is False

    def test_missing_client_name_still_valid(self, service):
        doc = {"redirect_uris": ["https://example.com/callback"]}
        assert service._validate_metadata(doc) is True


# ---------------------------------------------------------------------------
# get_or_fetch — memory cache
# ---------------------------------------------------------------------------


class TestGetOrFetchCache:
    async def test_returns_cached_metadata(self, service):
        """Memory cache hit returns metadata without fetching."""
        client_id = "https://app.example.com"
        service._memory_cache[client_id] = {
            "metadata": VALID_METADATA,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        result = await service.get_or_fetch(client_id)
        assert result == VALID_METADATA

    async def test_expired_cache_refetches(self, service):
        """Expired memory cache triggers a fresh fetch."""
        client_id = "https://app.example.com"
        service._memory_cache[client_id] = {
            "metadata": VALID_METADATA,
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
        }

        with patch.object(
            service, "_fetch_metadata", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = VALID_METADATA
            result = await service.get_or_fetch(client_id)

        assert result == VALID_METADATA
        mock_fetch.assert_awaited_once_with(client_id)


# ---------------------------------------------------------------------------
# _fetch_metadata
# ---------------------------------------------------------------------------


class TestFetchMetadata:
    async def test_success(self, service):
        """Successful HTTP fetch returns parsed metadata."""
        url = "https://app.example.com"
        body = json.dumps(VALID_METADATA).encode()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_length = len(body)
        mock_resp.read = AsyncMock(return_value=body)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_session_ctx)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_client_ctx):
            result = await service._fetch_metadata(url)

        assert result == VALID_METADATA

    async def test_too_large_by_content_length(self, service):
        """Document exceeding max size by Content-Length is rejected."""
        url = "https://app.example.com"

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_length = 100_000  # > 65536 default

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_session_ctx)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_client_ctx):
            result = await service._fetch_metadata(url)

        assert result is None

    async def test_too_large_by_body(self, service):
        """Document exceeding max size by body length is rejected."""
        url = "https://app.example.com"
        body = b"x" * 100_000

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.content_length = 0  # Unknown content length
        mock_resp.read = AsyncMock(return_value=body)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_session_ctx)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_client_ctx):
            result = await service._fetch_metadata(url)

        assert result is None

    async def test_non_200_returns_none(self, service):
        """Non-200 HTTP status returns None."""
        url = "https://app.example.com"

        mock_resp = AsyncMock()
        mock_resp.status = 404

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_session_ctx)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_client_ctx):
            result = await service._fetch_metadata(url)

        assert result is None

    async def test_non_https_rejected_in_production(self, service):
        """HTTP URLs are rejected when ENV != local."""
        with patch.dict(os.environ, {"ENV": "production"}):
            result = await service._fetch_metadata("http://insecure.example.com")
        assert result is None


# ---------------------------------------------------------------------------
# invalidate
# ---------------------------------------------------------------------------


class TestInvalidate:
    def test_removes_from_cache(self, service):
        client_id = "https://app.example.com"
        service._memory_cache[client_id] = {
            "metadata": VALID_METADATA,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        service.invalidate(client_id)
        assert client_id not in service._memory_cache

    def test_invalidate_nonexistent_is_noop(self, service):
        """Invalidating a key not in cache doesn't raise."""
        service.invalidate("https://not-cached.example.com")
