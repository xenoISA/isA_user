"""
Summary + Past-Chat Service — synthesis & RAG retrieval for #428 Phase 2 hard
slice (xenoISA/isA_user#439).

This module bundles two things the FE expects from `/api/v1/memories/*`:
  1. LLM-driven summary synthesis (POST /summary/regenerate)
  2. Past-chat vector search with incognito filtering (POST /past-chats/search)

Both pieces are best-effort with deterministic fallbacks — the goal is endpoint
shape correctness even when isA_Model or Qdrant are unreachable.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from isa_common import AsyncPostgresClient

logger = logging.getLogger(__name__)

# Pulled in lazily so import failures (e.g. isa_model not installed in the test
# environment) don't break the rest of the service. We keep the symbol exported
# at module scope so tests can patch `summary_service.AsyncISAModel`.
try:
    from isa_model.inference_client import AsyncISAModel  # type: ignore

    _ISA_MODEL_AVAILABLE = True
except Exception as e:  # pragma: no cover - exercised via fallback path
    logger.warning(f"isa_model unavailable, summary/past-chats will use fallback: {e}")
    AsyncISAModel = None  # type: ignore
    _ISA_MODEL_AVAILABLE = False

# Cap input memories so we don't blow the context window on power-user accounts.
# Top-50 by importance_score (or most recent when score is absent) is the sweet
# spot for "gpt-5-nano / claude-haiku" class models.
_MAX_MEMORIES_FOR_SYNTHESIS = 50


def _model_url() -> str:
    """ISA_MODEL_URL env override → localhost:8082 default."""
    return os.getenv("ISA_MODEL_URL", "http://localhost:8082")


def _excerpt(content: Optional[str], max_len: int = 240) -> str:
    if not content:
        return ""
    text = " ".join(content.split())
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def _memory_line(m: Dict[str, Any]) -> str:
    """Render a single memory row as `[{type}] {content}` for the prompt."""
    content = m.get("content") or ""
    if not content:
        # Compose a synthetic line for type-specific shapes (factual is the
        # main offender — it stores subject/predicate/object_value separately).
        subject = m.get("subject")
        predicate = m.get("predicate")
        obj = m.get("object_value")
        if subject and predicate:
            content = f"{subject} {predicate} {obj or ''}".strip()
        else:
            content = m.get("event_type") or m.get("definition") or m.get("skill_type") or ""
    mtype = m.get("memory_type") or m.get("type") or "memory"
    return f"- [{mtype}] {content.strip()}" if content else ""


def _rank_memories(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Trim to top-N by importance_score. When importance is missing we fall back
    to most-recent ordering (rows usually come pre-sorted DESC by created_at
    from list_memories, so a stable sort preserves that).
    """

    def key(m: Dict[str, Any]) -> float:
        score = m.get("importance_score")
        if isinstance(score, (int, float)):
            return float(score)
        return 0.0

    # Stable sort: rows with the same score keep their incoming (recent-first)
    # order so the "no importance set" case degrades to "most recent N".
    ranked = sorted(memories, key=key, reverse=True)
    return ranked[:_MAX_MEMORIES_FOR_SYNTHESIS]


async def synthesize_summary(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a 3-paragraph narrative + 5 highlights from a list of memories via
    the isA_Model gateway.

    Returns: {content: str, highlights: list[str], fallback: bool}

    Fallback path (when isA_Model is unreachable, returns an error, or emits
    un-parseable output) returns a synthetic "Summary of N memories" so the
    endpoint still produces a valid MemorySummary row.

    NOTE: Input memories are capped at top-50 by importance_score (most recent
    when score is absent) to keep the prompt inside the gpt-5-nano /
    claude-haiku context budget.
    """
    n = len(memories)
    fallback_payload: Dict[str, Any] = {
        "content": f"Summary of {n} memories (LLM synthesis unavailable — fallback summary).",
        "highlights": [f"{n} memories on record"] if n else ["No memories yet."],
        "fallback": True,
    }

    if not _ISA_MODEL_AVAILABLE or n == 0:
        return fallback_payload

    # Rank + cap so power-user accounts don't blow the context window.
    top_memories = _rank_memories(memories)
    bullets = [line for line in (_memory_line(m) for m in top_memories) if line]
    if not bullets:
        return fallback_payload

    bulleted = "\n".join(bullets)
    system_prompt = (
        "You write factual user summaries from memory rows. "
        "Respond with valid JSON only. Do not invent facts beyond the supplied memories."
    )
    user_prompt = (
        "Synthesize a 3-paragraph narrative summary highlighting the user's "
        "preferences, recurring themes, and key context, based on these memories. "
        "Then list exactly 5 bullet highlights.\n\n"
        f"Memories ({len(bullets)}):\n{bulleted}\n\n"
        'Return JSON: {"content": "<markdown narrative>", '
        '"highlights": ["...", "...", "...", "...", "..."]}'
    )

    try:
        async with AsyncISAModel(base_url=_model_url()) as client:
            response = await client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                provider="openai",
            )

        # Token accounting — log usage when the SDK surfaces it (no schema change).
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                prompt_tok = getattr(usage, "prompt_tokens", None)
                completion_tok = getattr(usage, "completion_tokens", None)
                total_tok = getattr(usage, "total_tokens", None)
                logger.info(
                    "summary synthesis tokens: prompt=%s completion=%s total=%s (memories_in=%d, memories_used=%d)",
                    prompt_tok,
                    completion_tok,
                    total_tok,
                    n,
                    len(bullets),
                )
        except Exception:  # pragma: no cover - usage logging must never break the path
            pass

        raw = (response.choices[0].message.content or "").strip()
        if not raw:
            logger.warning("LLM returned empty content; using fallback summary.")
            return fallback_payload

        parsed = json.loads(raw)
        narrative = (parsed.get("content") or "").strip()
        highlights_in = parsed.get("highlights") or []
        if not isinstance(highlights_in, list):
            highlights_in = []
        highlights = [str(h).strip() for h in highlights_in if str(h).strip()][:5]

        if not narrative or not highlights:
            logger.warning(
                "LLM JSON missing fields (content=%s, highlights=%d); using fallback.",
                bool(narrative),
                len(highlights),
            )
            return fallback_payload

        return {
            "content": narrative,
            "highlights": highlights,
            "fallback": False,
        }
    except json.JSONDecodeError as e:
        logger.warning(f"LLM synthesis returned non-JSON, using fallback: {e}")
        return fallback_payload
    except Exception as e:
        logger.warning(f"LLM synthesis failed, using fallback summary: {e}")
        return fallback_payload


async def search_past_chats(
    *,
    user_id: str,
    query: str,
    k: int = 8,
    exclude_incognito: bool = True,
    project_id: Optional[str] = None,
    session_service=None,
    postgres_client_factory=None,
) -> List[Dict[str, Any]]:
    """
    Past-chat RAG search.

    Pipeline:
      1. If `session_service` (the FactoryMemoryService.session_service handle)
         is provided, attempt Qdrant vector search via its `vector_search`.
      2. If no results (collection empty, Qdrant down, or isa_model down), fall
         back to a Postgres ILIKE on `memory.session_memories.content` and
         return the most recent `k` matches.
      3. Filter out incognito turns at the row level — never trust upstream.
      4. Return [{ session_id, session_title, turn_id, excerpt, score,
                  occurred_at, project_id }] (PastChatHit shape).

    `session_service` is duck-typed against `SessionMemoryService.vector_search`
    so tests can pass any stand-in with the same signature.
    """
    hits: List[Dict[str, Any]] = []

    # Path 1: Qdrant vector search via SessionMemoryService.
    vector_results: List[Dict[str, Any]] = []
    if session_service is not None:
        try:
            vector_results = await session_service.vector_search(
                user_id=user_id,
                query=query,
                limit=max(k * 2, k),  # over-fetch so we can post-filter
            )
        except Exception as e:
            logger.warning(f"Qdrant past-chat search failed, will fall back to SQL: {e}")
            vector_results = []

    if vector_results:
        for row in vector_results:
            if _is_incognito(row) and exclude_incognito:
                continue
            hits.append(_row_to_hit(row, score=float(row.get("similarity_score", 0.0))))
            if len(hits) >= k:
                break
        if hits:
            return hits

    # Path 2: Postgres ILIKE fallback.
    try:
        pg_rows = await _ilike_fallback(
            user_id=user_id,
            query=query,
            k=k * 2,
            postgres_client_factory=postgres_client_factory,
        )
    except Exception as e:
        logger.warning(f"Postgres ILIKE fallback also failed: {e}")
        return []

    for row in pg_rows:
        if _is_incognito(row) and exclude_incognito:
            continue
        hits.append(_row_to_hit(row, score=0.5))  # opaque score — text match
        if len(hits) >= k:
            break

    return hits


def _is_incognito(row: Dict[str, Any]) -> bool:
    """Detect incognito turns from either Qdrant payload or Postgres row."""
    meta = row.get("metadata") or row.get("conversation_state") or {}
    if isinstance(meta, dict):
        flag = meta.get("incognito")
        if isinstance(flag, bool):
            return flag
        if isinstance(flag, str):
            return flag.lower() == "true"
    # Direct column some pipelines set on the row itself.
    direct = row.get("incognito")
    if isinstance(direct, bool):
        return direct
    if isinstance(direct, str):
        return direct.lower() == "true"
    return False


def _row_to_hit(row: Dict[str, Any], *, score: float) -> Dict[str, Any]:
    """Coerce a session_memories row → PastChatHit JSON-safe shape."""
    occurred_at = row.get("created_at") or row.get("updated_at")
    if hasattr(occurred_at, "isoformat"):
        occurred_at = occurred_at.isoformat()
    elif occurred_at is None:
        occurred_at = datetime.now(timezone.utc).isoformat()

    return {
        "session_id": row.get("session_id") or "",
        "session_title": row.get("session_title") or row.get("session_type") or "Past chat",
        "turn_id": str(row.get("id") or row.get("memory_id") or ""),
        "excerpt": _excerpt(row.get("content")),
        "score": max(0.0, min(1.0, score)),
        "occurred_at": occurred_at,
        "project_id": row.get("project_id"),
    }


async def _ilike_fallback(
    *,
    user_id: str,
    query: str,
    k: int,
    postgres_client_factory=None,
) -> List[Dict[str, Any]]:
    """
    Postgres ILIKE on memory.session_memories.content as the last-resort path.

    Filters out rows whose `conversation_state->>'incognito' = 'true'`.
    `postgres_client_factory` lets tests inject a fake DB; defaults to a fresh
    AsyncPostgresClient using the same env vars as BaseMemoryRepository.
    """
    factory = postgres_client_factory or _default_postgres_factory
    db = factory()

    pattern = f"%{query}%" if query else "%"
    sql = """
        SELECT id, user_id, session_id, content, conversation_state,
               session_type, created_at
        FROM memory.session_memories
        WHERE user_id = $1
          AND active = true
          AND content ILIKE $2
          AND (conversation_state->>'incognito' IS NULL
               OR conversation_state->>'incognito' <> 'true')
        ORDER BY created_at DESC
        LIMIT $3
    """
    async with db:
        rows = await db.query(sql, [user_id, pattern, k], schema="memory")
    return rows or []


def _default_postgres_factory():
    """Lazy factory matching BaseMemoryRepository env-var conventions."""
    return AsyncPostgresClient(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "isa_platform"),
        username=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        user_id="memory_service",
    )
