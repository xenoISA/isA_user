"""
Summary Repository — read/write `memory.memory_summaries`.

Phase 2 hard slice of xenoISA/isA_#428 (paired with xenoISA/isA_user#439). One
row per (user_id, scope, scope_id) — the `version` column is bumped on every
regenerate or user-edit so the SidePanelMemory can detect drift.

Schema: see migrations/011_create_memory_summaries_table.sql.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base_repository import BaseMemoryRepository

logger = logging.getLogger(__name__)


class MemorySummaryRepository(BaseMemoryRepository):
    """Repository for `memory.memory_summaries`."""

    def __init__(self, config=None):
        super().__init__(schema="memory", table_name="memory_summaries", config=config)

    @staticmethod
    def _normalize_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Coerce JSONB columns to Python types so callers can JSON-encode safely."""
        if not row:
            return None
        out = dict(row)
        # highlights is stored as JSONB; the postgres client may return a
        # JSON-encoded string depending on the path. Normalise to a list.
        h = out.get("highlights")
        if isinstance(h, str):
            try:
                out["highlights"] = json.loads(h)
            except (json.JSONDecodeError, TypeError):
                out["highlights"] = []
        elif h is None:
            out["highlights"] = []

        sc = out.get("source_counts")
        if isinstance(sc, str):
            try:
                out["source_counts"] = json.loads(sc)
            except (json.JSONDecodeError, TypeError):
                out["source_counts"] = {"sessions": 0, "turns": 0, "memories": 0}
        elif sc is None:
            out["source_counts"] = {"sessions": 0, "turns": 0, "memories": 0}

        # Coerce timestamps to ISO strings so FastAPI's default JSON encoder
        # doesn't have to deal with whatever postgres returns.
        for field in ("generated_at", "edited_at", "created_at", "updated_at"):
            v = out.get(field)
            if hasattr(v, "isoformat"):
                out[field] = v.isoformat()
        return out

    async def get(self, user_id: str, scope: str, scope_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest summary row for the (user, scope, scope_id) tuple."""
        try:
            query = f"""
                SELECT id, user_id, scope, scope_id, content, highlights, version,
                       generated_at, edited_at, source_counts, created_at, updated_at
                FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND scope = $2 AND scope_id = $3
            """
            async with self.db:
                results = await self.db.query(query, [user_id, scope, scope_id], schema=self.schema)
            if not results:
                return None
            return self._normalize_row(results[0])
        except Exception as e:
            logger.error(f"MemorySummaryRepository.get({user_id},{scope},{scope_id}) failed: {e}")
            return None

    async def upsert(
        self,
        *,
        user_id: str,
        scope: str,
        scope_id: str,
        content: str,
        highlights: Optional[List[str]] = None,
        source_counts: Optional[Dict[str, int]] = None,
        edited: bool,
    ) -> Dict[str, Any]:
        """
        Upsert a summary row.

        `edited=True` is set when the user hand-edits via PUT /summary — we set
        `edited_at = now()` and keep the previous `generated_at`.
        `edited=False` is set on regenerate — we set `generated_at = now()` and
        clear `edited_at` so the FE knows the content is fresh from the model.

        Version is bumped from the previous row by 1 (starts at 1 for inserts).
        """
        now = datetime.now(timezone.utc)
        existing = await self.get(user_id, scope, scope_id)
        next_version = (existing.get("version", 0) + 1) if existing else 1

        # Default highlights/source_counts coalesce to JSONB defaults rather than
        # exploding when the caller doesn't have them (the edit endpoint, for
        # example, only sends a content string).
        highlights_payload = json.dumps(
            highlights if highlights is not None else (existing or {}).get("highlights", []) or []
        )
        source_counts_payload = json.dumps(
            source_counts
            if source_counts is not None
            else (existing or {}).get("source_counts", {"sessions": 0, "turns": 0, "memories": 0})
        )

        if edited:
            generated_at = (existing or {}).get("generated_at") or now
            # Reparse ISO back to a datetime where needed — keep the column happy.
            if isinstance(generated_at, str):
                try:
                    generated_at = datetime.fromisoformat(generated_at)
                except ValueError:
                    generated_at = now
            edited_at = now
        else:
            generated_at = now
            edited_at = None

        query = f"""
            INSERT INTO {self.schema}.{self.table_name}
                (user_id, scope, scope_id, content, highlights, version,
                 generated_at, edited_at, source_counts, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9::jsonb, $10, $10)
            ON CONFLICT (user_id, scope, scope_id) DO UPDATE SET
                content = EXCLUDED.content,
                highlights = EXCLUDED.highlights,
                version = EXCLUDED.version,
                generated_at = EXCLUDED.generated_at,
                edited_at = EXCLUDED.edited_at,
                source_counts = EXCLUDED.source_counts,
                updated_at = EXCLUDED.updated_at
            RETURNING id, user_id, scope, scope_id, content, highlights, version,
                      generated_at, edited_at, source_counts, created_at, updated_at
        """
        params = [
            user_id,
            scope,
            scope_id,
            content,
            highlights_payload,
            next_version,
            generated_at,
            edited_at,
            source_counts_payload,
            now,
        ]
        try:
            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)
            return self._normalize_row((results or [{}])[0])
        except Exception as e:
            logger.error(f"MemorySummaryRepository.upsert({user_id},{scope},{scope_id}) failed: {e}")
            raise
