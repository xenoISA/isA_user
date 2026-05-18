"""
State Repository — read/write the per-user `user_memory_state` row.

Phase 2 of xenoISA/isA_#428 (paired with xenoISA/isA_user#439). The single-row-
per-user model lets pause/resume + reset + summary freshness ride on one
upsert path. Migration `010_create_memory_state_table.sql` defines the
schema.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .base_repository import BaseMemoryRepository

logger = logging.getLogger(__name__)


class MemoryStateRepository(BaseMemoryRepository):
    """Repository for `memory.user_memory_state` — one row per user_id."""

    def __init__(self, config=None):
        super().__init__(schema="memory", table_name="user_memory_state", config=config)

    async def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return the user's state row, or None if it has never been set."""
        try:
            query = f"""
                SELECT user_id, paused, paused_at, last_synthesis_at, last_reset_at,
                       created_at, updated_at
                FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
            """
            async with self.db:
                results = await self.db.query(query, [user_id], schema=self.schema)
            if not results:
                return None
            return results[0]
        except Exception as e:
            logger.error(f"MemoryStateRepository.get({user_id}) failed: {e}")
            return None

    async def upsert(
        self,
        user_id: str,
        *,
        paused: Optional[bool] = None,
        last_synthesis_at: Optional[datetime] = None,
        last_reset_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Upsert the user's state row, touching only the fields supplied.

        Returns the new row. Callers should treat the returned dict as
        authoritative — paused_at is set on the server side when `paused`
        transitions to True.
        """
        # SET clauses are conditional so callers can mutate one field at a
        # time without clobbering siblings.
        now = datetime.now(timezone.utc)
        set_fragments = ["updated_at = $2"]
        params: list[Any] = [user_id, now]
        next_param = 3

        if paused is not None:
            set_fragments.append(f"paused = ${next_param}")
            params.append(paused)
            next_param += 1
            # paused_at flips with the truthy edge; we always rewrite to keep
            # the row coherent with the latest transition.
            set_fragments.append(f"paused_at = ${next_param}")
            params.append(now if paused else None)
            next_param += 1

        if last_synthesis_at is not None:
            set_fragments.append(f"last_synthesis_at = ${next_param}")
            params.append(last_synthesis_at)
            next_param += 1

        if last_reset_at is not None:
            set_fragments.append(f"last_reset_at = ${next_param}")
            params.append(last_reset_at)
            next_param += 1

        # Use the same parameters in the INSERT path so a fresh row gets all
        # the supplied fields. paused defaults to False when omitted on insert.
        insert_paused = paused if paused is not None else False
        insert_paused_at = now if insert_paused else None
        query = f"""
            INSERT INTO {self.schema}.{self.table_name}
                (user_id, paused, paused_at, last_synthesis_at, last_reset_at, created_at, updated_at)
            VALUES ($1, ${next_param}, ${next_param + 1}, ${next_param + 2}, ${next_param + 3}, $2, $2)
            ON CONFLICT (user_id) DO UPDATE SET {", ".join(set_fragments)}
            RETURNING user_id, paused, paused_at, last_synthesis_at, last_reset_at,
                      created_at, updated_at
        """
        params.extend([insert_paused, insert_paused_at, last_synthesis_at, last_reset_at])

        try:
            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)
            return (results or [{}])[0]
        except Exception as e:
            logger.error(f"MemoryStateRepository.upsert({user_id}) failed: {e}")
            raise
