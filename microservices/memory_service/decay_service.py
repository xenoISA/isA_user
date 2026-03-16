"""
Ebbinghaus Memory Decay Service

Applies the Ebbinghaus forgetting curve to reduce importance_score of unaccessed
memories over time.  Each access resets the decay timer (spaced repetition effect)
because last_accessed_at is already updated on every access.

Formula:
    importance_new = importance_original * exp(-ln(2) / half_life * hours_since_last_access)

No schema changes required — uses existing importance_score, access_count, and
last_accessed_at fields.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .memory_service import MemoryService

logger = logging.getLogger(__name__)


# ==================== Pure functions ====================


def compute_decayed_importance(
    original_importance: float,
    hours_since_last_access: float,
    half_life_hours: float,
) -> float:
    """
    Compute decayed importance using the Ebbinghaus forgetting curve.

    Formula: importance * e^(-ln(2)/half_life * t)

    This ensures that after exactly one half-life the importance is halved.

    Args:
        original_importance: The current importance score (0.0 - 1.0).
        hours_since_last_access: Hours elapsed since the memory was last accessed.
        half_life_hours: Number of hours for importance to halve.

    Returns:
        Decayed importance (clamped to [0.0, original_importance]).
    """
    if original_importance <= 0.0:
        return 0.0
    if hours_since_last_access <= 0.0:
        return original_importance

    decay_rate = math.log(2) / half_life_hours
    decayed = original_importance * math.exp(-decay_rate * hours_since_last_access)
    return max(0.0, min(decayed, original_importance))


# ==================== Configuration ====================


@dataclass
class DecayConfig:
    """Configuration for the decay service."""

    half_life_days: int = 30
    """Number of days for an unaccessed memory's importance to halve."""

    floor_threshold: float = 0.1
    """Memories that decay below this are soft-deleted (importance set to 0.0)."""

    protected_threshold: float = 0.8
    """Memories with importance >= this value are never decayed."""

    min_decay_delta: float = 0.001
    """Minimum change in importance to bother persisting an update."""

    batch_size: int = 1000
    """Maximum number of memories to fetch per query batch."""

    @property
    def half_life_hours(self) -> float:
        return self.half_life_days * 24.0


# ==================== Service ====================


# Memory types that support decay (working and session are transient)
_DECAYABLE_TYPES = ("factual", "procedural", "episodic", "semantic")

# Map memory type name to the attribute on MemoryService
_SERVICE_ATTR = {
    "factual": "factual_service",
    "procedural": "procedural_service",
    "episodic": "episodic_service",
    "semantic": "semantic_service",
}

# Allowlists for SQL identifier validation (prevents SQL injection)
_ALLOWED_SCHEMAS = frozenset({"memory", "public"})
_ALLOWED_TABLES = frozenset({
    "memories", "factual_memories", "procedural_memories",
    "episodic_memories", "semantic_memories",
})


class DecayService:
    """
    Runs Ebbinghaus decay cycles against memory repositories.

    Designed for dependency injection — accepts a MemoryService and config.
    """

    def __init__(
        self,
        memory_service: "MemoryService",
        config: Optional[DecayConfig] = None,
    ):
        self.memory_service = memory_service
        self.config = config or DecayConfig()

    async def run_decay_cycle(
        self,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run a full decay cycle across all decayable memory types.

        Args:
            user_id: If provided, only process this user's memories.
                     If None, process all users (global).

        Returns:
            Summary dict with counts: total_processed, decayed_count,
            floored_count, protected_count, skipped_count.
        """
        totals = {
            "total_processed": 0,
            "decayed_count": 0,
            "floored_count": 0,
            "protected_count": 0,
            "skipped_count": 0,
        }

        for memory_type in _DECAYABLE_TYPES:
            try:
                result = await self._decay_memory_type(memory_type, user_id)
                for key in totals:
                    totals[key] += result.get(key, 0)
            except Exception as e:
                logger.error(f"Error decaying {memory_type} memories: {e}", exc_info=True)

        logger.info(
            f"Decay cycle complete: {totals['total_processed']} processed, "
            f"{totals['decayed_count']} decayed, {totals['floored_count']} floored, "
            f"{totals['protected_count']} protected"
        )
        return totals

    async def _decay_memory_type(
        self,
        memory_type: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Decay all memories of a given type."""
        attr_name = _SERVICE_ATTR.get(memory_type)
        if not attr_name:
            return {"total_processed": 0, "decayed_count": 0, "floored_count": 0,
                    "protected_count": 0, "skipped_count": 0}

        sub_service = getattr(self.memory_service, attr_name, None)
        if not sub_service or not hasattr(sub_service, "repository"):
            return {"total_processed": 0, "decayed_count": 0, "floored_count": 0,
                    "protected_count": 0, "skipped_count": 0}

        repo = sub_service.repository

        # Fetch candidate memories — those below the protected threshold
        memories = await self._fetch_decayable_memories(repo, user_id)

        counts = {
            "total_processed": 0,
            "decayed_count": 0,
            "floored_count": 0,
            "protected_count": 0,
            "skipped_count": 0,
        }

        now = datetime.now(timezone.utc)

        for mem in memories:
            counts["total_processed"] += 1
            importance = mem.get("importance_score", 0.0)

            # Protected check
            if importance >= self.config.protected_threshold:
                counts["protected_count"] += 1
                continue

            # Already at zero — nothing to do
            if importance <= 0.0:
                counts["skipped_count"] += 1
                continue

            # Determine time since last access
            last_accessed = mem.get("last_accessed_at")
            if last_accessed is None:
                last_accessed = mem.get("created_at")
            if last_accessed is None:
                counts["skipped_count"] += 1
                continue

            # Ensure timezone-aware
            if last_accessed.tzinfo is None:
                last_accessed = last_accessed.replace(tzinfo=timezone.utc)

            hours_since = (now - last_accessed).total_seconds() / 3600.0

            new_importance = compute_decayed_importance(
                original_importance=importance,
                hours_since_last_access=hours_since,
                half_life_hours=self.config.half_life_hours,
            )

            # Floor check — set to 0.0 as soft-delete
            if new_importance < self.config.floor_threshold:
                new_importance = 0.0
                counts["floored_count"] += 1

            delta = abs(importance - new_importance)
            if delta < self.config.min_decay_delta:
                counts["skipped_count"] += 1
                continue

            # Persist the update
            try:
                await repo.update(
                    mem["id"],
                    {"importance_score": new_importance},
                    mem.get("user_id"),
                )
                counts["decayed_count"] += 1
            except Exception as e:
                logger.error(f"Failed to update memory {mem['id']}: {e}")
                counts["skipped_count"] += 1

        return counts

    async def _fetch_decayable_memories(
        self,
        repo,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch memories that are candidates for decay.

        We query for memories where importance_score > 0 and
        importance_score < protected_threshold, in batches to avoid
        unbounded result sets.
        """
        schema = getattr(repo, "schema", "memory")
        table = getattr(repo, "table_name", "memories")

        # Validate schema/table against allowlist to prevent SQL injection
        if schema not in _ALLOWED_SCHEMAS:
            logger.error(f"Rejected unknown schema: {schema!r}")
            return []
        if table not in _ALLOWED_TABLES:
            logger.error(f"Rejected unknown table: {table!r}")
            return []

        all_results: List[Dict[str, Any]] = []
        offset = 0
        batch_size = self.config.batch_size

        while True:
            if user_id:
                query = f"""
                    SELECT id, user_id, importance_score, access_count,
                           last_accessed_at, created_at
                    FROM {schema}.{table}
                    WHERE user_id = $1
                      AND importance_score > 0
                      AND importance_score < $2
                    ORDER BY id
                    LIMIT $3 OFFSET $4
                """
                params = [user_id, self.config.protected_threshold, batch_size, offset]
            else:
                query = f"""
                    SELECT id, user_id, importance_score, access_count,
                           last_accessed_at, created_at
                    FROM {schema}.{table}
                    WHERE importance_score > 0
                      AND importance_score < $1
                    ORDER BY id
                    LIMIT $2 OFFSET $3
                """
                params = [self.config.protected_threshold, batch_size, offset]

            try:
                async with repo.db:
                    batch = await repo.db.query(query, params, schema=schema)
                batch = batch or []
                all_results.extend(batch)
                if len(batch) < batch_size:
                    break
                offset += batch_size
            except Exception as e:
                logger.error(f"Error fetching decayable memories from {table}: {e}")
                break

        return all_results
