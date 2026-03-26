"""Client ID Metadata Document (CIMD) fetcher and cache.

When client_id is a URL (https://...), fetch the metadata document
to discover client properties like redirect_uris, client_name, etc.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)

CIMD_CACHE_TTL = int(os.environ.get("CIMD_CACHE_TTL_SECONDS", "3600"))
CIMD_FETCH_TIMEOUT = int(os.environ.get("CIMD_FETCH_TIMEOUT_SECONDS", "5"))
CIMD_MAX_SIZE = int(os.environ.get("CIMD_MAX_DOCUMENT_SIZE_BYTES", "65536"))


class ClientIdMetadataService:
    """Fetch, validate, and cache Client ID Metadata Documents."""

    def __init__(self, metadata_repo=None):
        self._repo = metadata_repo  # Optional DB-backed cache
        self._memory_cache: Dict[str, Dict[str, Any]] = {}  # In-memory fallback

    def is_metadata_client_id(self, client_id: str) -> bool:
        """Check if client_id is a URL (CIMD-based client)."""
        return client_id.startswith("https://") or client_id.startswith("http://")

    async def get_or_fetch(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get cached metadata or fetch from URL."""
        # Check memory cache first
        cached = self._memory_cache.get(client_id)
        if cached and cached.get(
            "expires_at", datetime.min.replace(tzinfo=timezone.utc)
        ) > datetime.now(timezone.utc):
            return cached.get("metadata")

        # Check DB cache
        if self._repo:
            db_cached = await self._repo.get_metadata(client_id)
            if (
                db_cached
                and db_cached.get("expires_at")
                and db_cached["expires_at"] > datetime.now(timezone.utc)
            ):
                self._memory_cache[client_id] = db_cached
                return db_cached.get("metadata")

        # Fetch from URL
        metadata = await self._fetch_metadata(client_id)
        if metadata:
            cache_entry = {
                "client_id": client_id,
                "metadata_document_url": client_id,
                "metadata": metadata,
                "client_type": metadata.get("client_type", "public"),
                "redirect_uris": metadata.get("redirect_uris", []),
                "client_name": metadata.get("client_name", ""),
                "cached_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=CIMD_CACHE_TTL),
                "is_valid": True,
            }
            self._memory_cache[client_id] = cache_entry

            # Store in DB cache if available
            if self._repo:
                try:
                    await self._repo.upsert_metadata(cache_entry)
                except Exception as e:
                    logger.warning(f"Failed to cache CIMD in DB: {e}")

            return metadata

        return None

    async def _fetch_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata document from URL."""
        # Security: only HTTPS in production
        if not url.startswith("https://") and os.environ.get("ENV", "local") != "local":
            logger.error(f"CIMD fetch rejected: non-HTTPS URL {url}")
            return None

        try:
            timeout = aiohttp.ClientTimeout(total=CIMD_FETCH_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"CIMD fetch failed: {url} returned {resp.status}"
                        )
                        return None

                    # Check size
                    content_length = resp.content_length or 0
                    if content_length > CIMD_MAX_SIZE:
                        logger.warning(
                            f"CIMD too large: {url} ({content_length} bytes)"
                        )
                        return None

                    body = await resp.read()
                    if len(body) > CIMD_MAX_SIZE:
                        logger.warning(f"CIMD too large: {url} ({len(body)} bytes)")
                        return None

                    metadata = json.loads(body)

                    # Validate required fields
                    if not self._validate_metadata(metadata):
                        return None

                    return metadata

        except Exception as e:
            logger.error(f"CIMD fetch error for {url}: {e}")
            return None

    def _validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate CIMD document structure."""
        if not isinstance(metadata, dict):
            logger.warning("CIMD: not a JSON object")
            return False

        # redirect_uris is required and must be non-empty
        redirect_uris = metadata.get("redirect_uris")
        if not redirect_uris or not isinstance(redirect_uris, list):
            logger.warning("CIMD: missing or empty redirect_uris")
            return False

        # client_name recommended
        if not metadata.get("client_name"):
            logger.info("CIMD: missing client_name (optional)")

        return True

    def invalidate(self, client_id: str):
        """Remove from cache."""
        self._memory_cache.pop(client_id, None)
