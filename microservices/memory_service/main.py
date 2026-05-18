"""
Memory Microservice

AI-powered memory service for intelligent information storage and retrieval
Supports multiple memory types: factual, procedural, episodic, semantic, working, session

Architecture:
- PostgreSQL: Structured data storage
- Qdrant: Vector embeddings for semantic search
- ISA Model: AI extraction and embeddings generation

Port: 8223
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query

from contextlib import asynccontextmanager
from pydantic import BaseModel


from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics
from core.health import HealthCheck
from isa_common.consul_client import ConsulRegistry

from .models import (
    MemoryType,
    MemoryOperationResult,
    MemoryCreateRequest,
    MemoryUpdateRequest,
    MemoryListParams,
    MemoryServiceStats,
    DecayRequest,
    DecayResponse,
    ConsolidationRequest,
    ConsolidationResponse,
    GraphSearchResponse,
    GraphNeighborsResponse,
)
from .memory_graph import MemoryGraphAdapter
from .context_ordering import order_by_importance_edges
from .context_compressor import ContextCompressor
from .mmr_reranker import apply_mmr_reranking
from .hybrid_search import merge_hybrid_results
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
from .factory import create_memory_service

# Initialize configuration
config_manager = ConfigManager("memory_service")
service_config = config_manager.get_service_config()

# Setup logger
logger = setup_service_logger("memory_service")

# Global service instance
memory_service = None
graph_client: Optional[MemoryGraphAdapter] = None
consul_registry: Optional[ConsulRegistry] = None
shutdown_manager = GracefulShutdown("memory_service")

# Lazy singleton — instantiated on first state/pause/resume/reset/export/import
# request so the rest of the service starts even when the user_memory_state
# table hasn't been migrated yet. (xenoISA/isA_user#439)
_memory_state_repo = None


def _get_state_repo():
    """Return a process-global MemoryStateRepository, instantiated on first use."""
    global _memory_state_repo
    if _memory_state_repo is None:
        from .state_repository import MemoryStateRepository

        _memory_state_repo = MemoryStateRepository()
    return _memory_state_repo


def _build_graph_client() -> MemoryGraphAdapter:
    return MemoryGraphAdapter()


async def _maybe_rerank(results, query, service, rerank, mmr_lambda, limit):
    """Apply MMR re-ranking if enabled, using the correct service's embedding generation."""
    if not rerank or not results:
        return results
    try:
        query_embedding = await service._generate_embedding(query)
        if query_embedding is not None:
            results = apply_mmr_reranking(results, query_embedding, lambda_param=mmr_lambda, top_k=limit)
    except Exception as e:
        logger.warning("MMR re-ranking failed, using raw results: %s", e)
    return results


async def _record_graph_billing_usage(
    *,
    user_id: str,
    query: str,
    operation_type: str,
    result_count: int,
    limit: int,
) -> None:
    if memory_service is None:
        return
    try:
        await memory_service._publish_vector_billing_usage(
            user_id=user_id,
            product_id="memory_graph_query",
            usage_amount=1,
            unit_type="request",
            operation_type=operation_type,
            resource_name="memory_graph",
            usage_details={
                "query_length": len(query),
                "limit": limit,
                "result_count": result_count,
                "graph_backend": "falkordb",
            },
            idempotency_key=None,
        )
    except Exception as e:
        logger.error("Failed to publish memory graph billing usage: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global memory_service, graph_client, consul_registry
    shutdown_manager.install_signal_handlers()

    logger.info("Starting Memory Service with AI capabilities...")

    # Initialize event bus for subscribing to session events
    event_bus = None
    event_handlers = None
    try:
        from .events import MemoryEventHandlers

        event_bus = await get_event_bus("memory_service")
        logger.info("✅ Event bus initialized successfully")

        # Initialize service with event bus (using factory pattern)
        memory_service = create_memory_service(event_bus=event_bus)

        # Check database connection
        if not await memory_service.check_connection():
            logger.error("Failed to connect to database")
            raise RuntimeError("Database connection failed")

        # Set up event handlers
        event_handlers = MemoryEventHandlers(memory_service)
        handler_map = event_handlers.get_event_handler_map()

        for event_pattern, handler_func in handler_map.items():
            await event_bus.subscribe_to_events(pattern=event_pattern, handler=handler_func)

        logger.info(f"✅ Memory event subscriber started ({len(handler_map)} event types)")

    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event subscriptions.")
        event_bus = None

        # Initialize service without event bus (using factory pattern)
        memory_service = create_memory_service(event_bus=None)

        # Check database connection
        if not await memory_service.check_connection():
            logger.error("Failed to connect to database")
            raise RuntimeError("Database connection failed")

    # Initialize local FalkorDB memory graph adapter.
    try:
        graph_client = _build_graph_client()
        if await graph_client.health_check():
            logger.info("Memory graph adapter connected to FalkorDB")
        else:
            logger.warning("FalkorDB memory graph not reachable — graph queries will degrade gracefully")
    except Exception as e:
        logger.warning(f"Failed to initialize memory graph adapter: {e}. Graph queries disabled.")
        graph_client = _build_graph_client()  # keep instance for graceful degradation

    # Consul 服务注册
    if service_config.consul_enabled:
        try:
            # 获取路由元数据
            route_meta = get_routes_for_consul()

            # 合并服务元数据
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }

            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=service_config.service_port,
                consul_host=service_config.consul_host,
                consul_port=service_config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl",  # Use TTL for reliable health checks
            )
            consul_registry.register()
            consul_registry.start_maintenance()  # Start TTL heartbeat
            shutdown_manager.set_consul_registry(consul_registry)
            logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count')} routes")
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with Consul: {e}")
            consul_registry = None

    logger.info("Memory Service initialized successfully")

    yield

    # Cleanup
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()

    logger.info("Shutting down Memory Service...")
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")
    if graph_client:
        await graph_client.close()
        logger.info("Memory graph adapter closed")

    # Consul deregistration is handled by shutdown_manager.initiate_shutdown()
    # so traffic stops before we reject requests with 503.


# Create FastAPI app
app = FastAPI(
    title="Memory Service",
    description="AI-powered memory service for intelligent information storage and retrieval",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "memory_service")


# ==================== Health Check ====================

health = HealthCheck("memory_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_memory_graph(lambda: graph_client)
health.add_qdrant(
    lambda: (
        memory_service.factual_service.qdrant
        if memory_service and getattr(memory_service, "factual_service", None)
        else None
    )
)


@app.get("/api/v1/memories/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()


# ============================================================================
# Memory state / lifecycle endpoints (xenoISA/isA_user#439 — paired with
# xenoISA/isA_#428 Phase 2 frontend in isA_/src/api/memoryService.ts).
# ============================================================================
#
# These six routes (state / pause / resume / reset / export / import) are
# the simplest slice of the Phase 2 backend contract — no synthesis or
# vector search required. Summary GET/PUT/POST and past-chats search land
# in a follow-up that wires the synthesis pipeline + Qdrant query.

SCHEMA_VERSION = "1.0"


def _serialize_state_row(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalise a user_memory_state row for the API response."""
    if not row:
        return {"paused": False}
    return {
        "paused": bool(row.get("paused")),
        "paused_at": row.get("paused_at"),
        "last_synthesis_at": row.get("last_synthesis_at"),
        "last_reset_at": row.get("last_reset_at"),
    }


@app.get("/api/v1/memories/state")
async def get_memory_state(user_id: str = Query(..., description="User id")):
    """Return per-user memory pipeline state (pause/synthesis/reset timestamps)."""
    try:
        row = await _get_state_repo().get(user_id)
        return _serialize_state_row(row)
    except Exception as e:
        logger.error(f"get_memory_state({user_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class MemoryPauseToggleRequest(BaseModel):
    user_id: str


@app.post("/api/v1/memories/pause")
async def pause_memory(body: MemoryPauseToggleRequest):
    """Pause memory writes for a user."""
    try:
        row = await _get_state_repo().upsert(body.user_id, paused=True)
        return _serialize_state_row(row)
    except Exception as e:
        logger.error(f"pause_memory({body.user_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memories/resume")
async def resume_memory(body: MemoryPauseToggleRequest):
    """Resume memory writes for a user."""
    try:
        row = await _get_state_repo().upsert(body.user_id, paused=False)
        return _serialize_state_row(row)
    except Exception as e:
        logger.error(f"resume_memory({body.user_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class MemoryResetRequest(BaseModel):
    user_id: str
    confirmation: str  # MUST equal "RESET" — typed confirmation matches frontend modal.


@app.post("/api/v1/memories/reset")
async def reset_memory(body: MemoryResetRequest):
    """Destructive: delete all memories for a user. Requires confirmation='RESET'."""
    if body.confirmation != "RESET":
        raise HTTPException(
            status_code=400,
            detail="confirmation must be the literal string 'RESET'",
        )
    try:
        deleted_count = 0
        for memory_type in MemoryType:
            params = MemoryListParams(
                user_id=body.user_id,
                memory_type=memory_type,
                limit=100,
                offset=0,
            )
            while True:
                batch = await memory_service.list_memories(params)
                if not batch:
                    break
                for item in batch:
                    memory_id = item.get("id") or item.get("memory_id")
                    if not memory_id:
                        continue
                    result = await memory_service.delete_memory(memory_id, memory_type, body.user_id)
                    if result.success:
                        deleted_count += 1
                if len(batch) < params.limit:
                    break
                params = MemoryListParams(
                    user_id=body.user_id,
                    memory_type=memory_type,
                    limit=params.limit,
                    offset=params.offset + params.limit,
                )

        row = await _get_state_repo().upsert(body.user_id, last_reset_at=datetime.now(timezone.utc))
        return {
            "success": True,
            "deleted": deleted_count,
            "state": _serialize_state_row(row),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"reset_memory({body.user_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/export")
async def export_memory(
    user_id: str = Query(..., description="User id"),
    scope: str = Query("user", pattern="^(user|project)$"),
    project_id: Optional[str] = Query(None),
):
    """Return a versioned MemoryExportBundle for the user's memory corpus."""
    try:
        all_memories: List[Dict[str, Any]] = []
        by_type: Dict[str, int] = {}

        for memory_type in MemoryType:
            params = MemoryListParams(
                user_id=user_id,
                memory_type=memory_type,
                limit=100,
                offset=0,
            )
            type_total = 0
            while True:
                batch = await memory_service.list_memories(params)
                if not batch:
                    break
                for item in batch:
                    all_memories.append({**item, "type": memory_type.value})
                type_total += len(batch)
                if len(batch) < params.limit:
                    break
                params = MemoryListParams(
                    user_id=user_id,
                    memory_type=memory_type,
                    limit=params.limit,
                    offset=params.offset + params.limit,
                )
            if type_total:
                by_type[memory_type.value] = type_total

        return {
            "schema_version": SCHEMA_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "scope": scope,
            "project_id": project_id,
            "summary": None,  # Wired in the summary follow-up.
            "memories": all_memories,
            "counts": {"memories": len(all_memories), "by_type": by_type},
        }
    except Exception as e:
        logger.error(f"export_memory({user_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class MemoryImportRequest(BaseModel):
    user_id: str
    mode: str = "merge"  # 'merge' | 'replace'
    payload: Dict[str, Any]


@app.post("/api/v1/memories/import")
async def import_memory(body: MemoryImportRequest):
    """
    Import a MemoryExportBundle for the user. Phase 2 minimum:
    - validates schema_version
    - mode='replace' wipes the corpus first; per-memory-type insert pipeline
      lands when the per-type extract endpoints are wired up to import.
    - mode='merge' currently returns the would-be counts so the frontend's
      import-result UI works end-to-end against a real backend.
    """
    if body.mode not in {"merge", "replace"}:
        raise HTTPException(status_code=400, detail="mode must be 'merge' or 'replace'")

    payload = body.payload or {}
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported schema_version (expected {SCHEMA_VERSION})",
        )

    memories = payload.get("memories")
    if not isinstance(memories, list):
        raise HTTPException(status_code=400, detail="payload.memories must be a list")

    errors: List[Dict[str, Any]] = []
    skipped = len(memories)
    imported = 0

    if body.mode == "replace":
        try:
            for memory_type in MemoryType:
                params = MemoryListParams(
                    user_id=body.user_id,
                    memory_type=memory_type,
                    limit=100,
                    offset=0,
                )
                while True:
                    batch = await memory_service.list_memories(params)
                    if not batch:
                        break
                    for item in batch:
                        memory_id = item.get("id") or item.get("memory_id")
                        if memory_id:
                            await memory_service.delete_memory(memory_id, memory_type, body.user_id)
                    if len(batch) < params.limit:
                        break
                    params = MemoryListParams(
                        user_id=body.user_id,
                        memory_type=memory_type,
                        limit=params.limit,
                        offset=params.offset + params.limit,
                    )
        except Exception as e:
            logger.error(f"import_memory(replace) cleanup failed: {e}")
            errors.append({"index": -1, "message": f"replace-cleanup: {e}"})

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "mode": body.mode,
    }


# ============================================================================
# Summary + Past-chat RAG endpoints (xenoISA/isA_user#439 hard slice —
# paired with #428 §4-5). These four routes round out the Phase 2 backend
# contract that #439 ships incrementally:
#   GET   /api/v1/memories/summary?scope=&scope_id=
#   PUT   /api/v1/memories/summary
#   POST  /api/v1/memories/summary/regenerate
#   POST  /api/v1/memories/past-chats/search
# ============================================================================

_summary_repo = None  # Lazy singleton — mirrors _memory_state_repo.


def _get_summary_repo():
    """Return a process-global MemorySummaryRepository, instantiated on first use."""
    global _summary_repo
    if _summary_repo is None:
        from .summary_repository import MemorySummaryRepository

        _summary_repo = MemorySummaryRepository()
    return _summary_repo


def _user_id_for_scope(scope: str, scope_id: str) -> str:
    """
    Map (scope, scope_id) → user_id for the summary row.

    For scope='user' the scope_id IS the user_id. For scope='project' the
    caller MUST supply user_id separately via the request body; the frontend
    contract embeds the user via the bearer token so for now we treat scope_id
    as user_id for 'user' scope and require explicit user_id for 'project'
    (validated in the route handlers).
    """
    return scope_id  # extended once project-scope auth lands; tracked in #428 §3.1


@app.get("/api/v1/memories/summary")
async def get_summary(
    scope: str = Query("user", pattern="^(user|project)$"),
    scope_id: str = Query(..., description="user_id for scope=user; project_id for scope=project"),
):
    """
    Fetch the latest MemorySummary for (scope, scope_id).

    Returns 404 when no summary has been generated yet — the FE's
    `getSummary` contract maps 404 → null so this matches the TS client.
    """
    try:
        row = await _get_summary_repo().get(_user_id_for_scope(scope, scope_id), scope, scope_id)
        if not row:
            raise HTTPException(status_code=404, detail="No summary yet")
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_summary({scope},{scope_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SaveSummaryRequest(BaseModel):
    scope: str
    scope_id: str
    content: str


@app.put("/api/v1/memories/summary")
async def save_summary(body: SaveSummaryRequest):
    """Persist a user-edited summary — bumps version, sets `edited_at = now()`."""
    if body.scope not in {"user", "project"}:
        raise HTTPException(status_code=400, detail="scope must be 'user' or 'project'")
    try:
        row = await _get_summary_repo().upsert(
            user_id=_user_id_for_scope(body.scope, body.scope_id),
            scope=body.scope,
            scope_id=body.scope_id,
            content=body.content,
            edited=True,
        )
        return row
    except Exception as e:
        logger.error(f"save_summary({body.scope},{body.scope_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RegenerateSummaryRequest(BaseModel):
    scope: str
    scope_id: str


@app.post("/api/v1/memories/summary/regenerate")
async def regenerate_summary(
    body: RegenerateSummaryRequest,
    authorization: Optional[str] = Header(default=None),
):
    """
    Trigger LLM synthesis from the user's memory corpus.

    Pulls memories via memory_service.list_memories, composes a prompt, calls
    isA_Model, and saves the result. If isA_Model is unreachable the synthesis
    helper returns a deterministic "Summary of N memories" fallback so the
    endpoint shape stays correct.

    When the request carries an ``Authorization: Bearer <jwt>`` header, the
    token is forwarded to isA_Model so upstream user-level quotas/audit apply.
    Absent header → falls back to isA_Model's service-level auth (no change).
    """
    if body.scope not in {"user", "project"}:
        raise HTTPException(status_code=400, detail="scope must be 'user' or 'project'")

    try:
        from .summary_service import synthesize_summary

        user_id = _user_id_for_scope(body.scope, body.scope_id)

        # Pull all memory types. MemoryListParams.limit is capped at 100 by the
        # Pydantic model, so we page once-or-twice per type — enough for
        # synthesis without blowing the LLM context budget.
        all_memories: List[Dict[str, Any]] = []
        by_type: Dict[str, int] = {}
        REGEN_PER_TYPE_CAP = 200  # synthesize_summary itself trims at 80
        for memory_type in MemoryType:
            offset = 0
            type_total = 0
            while type_total < REGEN_PER_TYPE_CAP:
                params = MemoryListParams(
                    user_id=user_id,
                    memory_type=memory_type,
                    limit=100,
                    offset=offset,
                )
                try:
                    batch = await memory_service.list_memories(params)
                except Exception as e:
                    logger.warning(f"list_memories({memory_type.value}) failed during regen: {e}")
                    batch = []
                if not batch:
                    break
                all_memories.extend(batch)
                type_total += len(batch)
                if len(batch) < 100:
                    break
                offset += 100
            if type_total:
                by_type[memory_type.value] = type_total

        synthesis = await synthesize_summary(all_memories, auth_token=authorization)
        source_counts = {
            "memories": len(all_memories),
            "by_type": by_type,
            # `sessions` / `turns` are placeholders until we wire the per-scope
            # session crawl — kept in the payload for frontend compatibility.
            "sessions": 0,
            "turns": 0,
        }

        row = await _get_summary_repo().upsert(
            user_id=user_id,
            scope=body.scope,
            scope_id=body.scope_id,
            content=synthesis["content"],
            highlights=synthesis["highlights"],
            source_counts=source_counts,
            edited=False,
        )

        # Bump last_synthesis_at on the state row so SidePanelMemory can badge
        # freshness without a second round-trip.
        try:
            await _get_state_repo().upsert(user_id, last_synthesis_at=datetime.now(timezone.utc))
        except Exception as e:
            logger.warning(f"Failed to bump last_synthesis_at for {user_id}: {e}")

        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"regenerate_summary({body.scope},{body.scope_id}) failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PastChatsSearchRequest(BaseModel):
    user_id: str
    query: str
    scope: str = "user"
    project_id: Optional[str] = None
    k: int = 8
    exclude_incognito: bool = True


@app.post("/api/v1/memories/past-chats/search")
async def search_past_chats_route(body: PastChatsSearchRequest):
    """
    Past-chat RAG search → PastChatHit[].

    Tries Qdrant (via memory_service.session_service.vector_search) first;
    falls back to a Postgres ILIKE on session_memories.content when Qdrant or
    isa_model are unavailable. Incognito turns are filtered out at the row
    level regardless of upstream — defense in depth.
    """
    if body.scope not in {"user", "project"}:
        raise HTTPException(status_code=400, detail="scope must be 'user' or 'project'")
    if not body.query or not body.query.strip():
        return []

    try:
        from .summary_service import search_past_chats

        session_handle = getattr(memory_service, "session_service", None) if memory_service else None
        hits = await search_past_chats(
            user_id=body.user_id,
            query=body.query,
            k=max(1, min(body.k, 50)),
            exclude_incognito=body.exclude_incognito,
            project_id=body.project_id,
            session_service=session_handle,
        )
        return hits
    except Exception as e:
        logger.error(f"search_past_chats({body.user_id}) failed: {e}")
        # Return empty list rather than 500 — the FE treats empty hits as
        # "no past chats matched" which is the correct UX when retrieval is
        # transiently degraded.
        return []


class StoreFactualMemoryRequest(BaseModel):
    user_id: str
    dialog_content: str
    importance_score: float = 0.5


class StoreEpisodicMemoryRequest(BaseModel):
    user_id: str
    dialog_content: str
    importance_score: float = 0.5


class StoreProceduralMemoryRequest(BaseModel):
    user_id: str
    dialog_content: str
    importance_score: float = 0.5


class StoreSemanticMemoryRequest(BaseModel):
    user_id: str
    dialog_content: str
    importance_score: float = 0.5


class StoreWorkingMemoryRequest(BaseModel):
    user_id: str
    dialog_content: str
    ttl_seconds: int = 3600
    importance_score: float = 0.5


class StoreSessionMessageRequest(BaseModel):
    user_id: str
    session_id: str
    message_content: str
    message_type: str = "human"
    role: str = "user"


class SummarizeSessionRequest(BaseModel):
    user_id: str
    force_update: bool = False
    compression_level: str = "medium"  # low, medium, high


@app.post("/api/v1/memories/factual/extract", response_model=MemoryOperationResult)
async def store_factual_memory(request: StoreFactualMemoryRequest):
    """Extract and store factual memories from dialog using AI"""
    try:
        result = await memory_service.store_factual_memory(
            user_id=request.user_id,
            dialog_content=request.dialog_content,
            importance_score=request.importance_score,
        )
        return result
    except Exception as e:
        logger.error(f"Error storing factual memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memories/episodic/extract", response_model=MemoryOperationResult)
async def store_episodic_memory(request: StoreEpisodicMemoryRequest):
    """Extract and store episodic memories from dialog using AI"""
    try:
        result = await memory_service.store_episodic_memory(
            user_id=request.user_id,
            dialog_content=request.dialog_content,
            importance_score=request.importance_score,
        )
        return result
    except Exception as e:
        logger.error(f"Error storing episodic memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memories/procedural/extract", response_model=MemoryOperationResult)
async def store_procedural_memory(request: StoreProceduralMemoryRequest):
    """Extract and store procedural memories from dialog using AI"""
    try:
        result = await memory_service.store_procedural_memory(
            user_id=request.user_id,
            dialog_content=request.dialog_content,
            importance_score=request.importance_score,
        )
        return result
    except Exception as e:
        logger.error(f"Error storing procedural memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memories/semantic/extract", response_model=MemoryOperationResult)
async def store_semantic_memory(request: StoreSemanticMemoryRequest):
    """Extract and store semantic memories from dialog using AI"""
    try:
        result = await memory_service.store_semantic_memory(
            user_id=request.user_id,
            dialog_content=request.dialog_content,
            importance_score=request.importance_score,
        )
        return result
    except Exception as e:
        logger.error(f"Error storing semantic memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== General Memory Operations ====================


@app.post("/api/v1/memories", response_model=MemoryOperationResult)
async def create_memory(request: MemoryCreateRequest):
    """Create a new memory"""
    try:
        result = await memory_service.create_memory(request)
        return result
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Session-specific Routes (must come before generic routes) ====================


@app.post("/api/v1/memories/session/store", response_model=MemoryOperationResult)
async def store_session_message(request: StoreSessionMessageRequest):
    """Store session message"""
    try:
        # Get existing session memories to determine interaction sequence
        existing_memories = await memory_service.get_session_memories(request.user_id, request.session_id)
        interaction_sequence = len(existing_memories) + 1

        # Build conversation state
        conversation_state = {
            "message_type": request.message_type,
            "role": request.role,
            "sequence": interaction_sequence,
        }

        result = await memory_service.session_service.store_session_memory(
            user_id=request.user_id,
            session_id=request.session_id,
            content=request.message_content,
            interaction_sequence=interaction_sequence,
            conversation_state=conversation_state,
            session_type="chat",
        )
        return result
    except Exception as e:
        logger.error(f"Error storing session message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/session/{session_id}/context")
async def get_session_context(
    session_id: str,
    user_id: str = Query(...),
    include_summaries: bool = Query(True),
    max_recent_messages: int = Query(5),
):
    """Get comprehensive session context"""
    try:
        # Get session memories
        memories = await memory_service.get_session_memories(user_id, session_id)

        # Sort by interaction sequence
        memories.sort(key=lambda m: m.get("interaction_sequence", 0))

        # Get recent messages
        recent_messages = memories[-max_recent_messages:] if max_recent_messages > 0 else memories

        # Build context response
        context = {
            "session_id": session_id,
            "user_id": user_id,
            "total_messages": len(memories),
            "recent_messages": recent_messages,
        }

        # Include summary if requested
        if include_summaries:
            summary = await memory_service.get_session_summary(user_id, session_id)
            context["summary"] = summary

        return context
    except Exception as e:
        logger.error(f"Error getting session context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/session/{session_id}")
async def get_session_memories(session_id: str, user_id: str = Query(...)):
    """Get memories for a specific session"""
    try:
        results = await memory_service.get_session_memories(user_id, session_id)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting session memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/memories/session/{session_id}/deactivate",
    response_model=MemoryOperationResult,
)
async def deactivate_session(session_id: str, user_id: str = Query(...)):
    """Deactivate a session"""
    try:
        result = await memory_service.deactivate_session(user_id, session_id)
        return result
    except Exception as e:
        logger.error(f"Error deactivating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/memories/session/{session_id}/summarize",
    response_model=MemoryOperationResult,
)
async def summarize_session(session_id: str, request: SummarizeSessionRequest):
    """
    Summarize session conversation intelligently.

    Creates or updates a summary of the session's messages based on compression level.
    """
    try:
        # Get all session memories
        memories = await memory_service.get_session_memories(request.user_id, session_id)

        if not memories:
            return MemoryOperationResult(
                success=False,
                operation="summarize_session",
                message="No messages found in session to summarize",
            )

        # Get existing summary if not forcing update
        existing_summary = None
        if not request.force_update:
            existing_summary = await memory_service.get_session_summary(request.user_id, session_id)
            if existing_summary:
                return MemoryOperationResult(
                    success=True,
                    operation="summarize_session",
                    message="Using existing summary (use force_update=true to regenerate)",
                    data=existing_summary,
                )

        # Extract content from memories for summarization
        contents = [m.get("content", "") for m in memories if m.get("content")]
        combined_content = "\n".join(contents)

        # Generate summary based on compression level
        if request.compression_level == "low":
            # Keep more detail
            max_sentences = 10
        elif request.compression_level == "high":
            # Very compact
            max_sentences = 3
        else:
            # Medium (default)
            max_sentences = 5

        # Simple sentence-based summarization (fallback without AI)
        sentences = combined_content.replace("\n", " ").split(". ")
        key_sentences = sentences[:max_sentences]
        summary_text = ". ".join(key_sentences)
        if summary_text and not summary_text.endswith("."):
            summary_text += "."

        # Store the summary
        import uuid

        summary_data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "summary": summary_text,
            "key_points": key_sentences[:3],
            "message_count": len(memories),
            "compression_level": request.compression_level,
            "created_at": datetime.now().isoformat(),
        }

        # Store summary via repository
        await memory_service.session_service.repository.store_session_summary(
            user_id=request.user_id, session_id=session_id, summary_data=summary_data
        )

        return MemoryOperationResult(
            success=True,
            operation="summarize_session",
            message=f"Session summarized ({len(memories)} messages → {len(key_sentences)} key points)",
            data=summary_data,
        )

    except Exception as e:
        logger.error(f"Error summarizing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Working Memory-specific Routes (must come before generic routes) ====================


@app.post("/api/v1/memories/working/store", response_model=MemoryOperationResult)
async def store_working_memory(request: StoreWorkingMemoryRequest):
    """Store working memory from dialog"""
    try:
        import uuid

        # Generate task_id and task_context from dialog
        task_id = str(uuid.uuid4())
        task_context = {
            "source": "dialog",
            "content_preview": request.dialog_content[:100]
            if len(request.dialog_content) > 100
            else request.dialog_content,
        }

        result = await memory_service.working_service.store_working_memory(
            user_id=request.user_id,
            content=request.dialog_content,
            task_id=task_id,
            task_context=task_context,
            priority=5,
            ttl_seconds=request.ttl_seconds,
        )
        return result
    except Exception as e:
        logger.error(f"Error storing working memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/working/active")
async def get_active_working_memories(user_id: str = Query(...)):
    """Get active working memories"""
    try:
        results = await memory_service.get_active_working_memories(user_id)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting active working memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memories/working/cleanup", response_model=MemoryOperationResult)
async def cleanup_expired_memories(user_id: Optional[str] = Query(None)):
    """Clean up expired working memories"""
    try:
        result = await memory_service.cleanup_expired_memories(user_id)
        return result
    except Exception as e:
        logger.error(f"Error cleaning up expired memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Graph Retrieval Endpoints ====================


@app.get("/api/v1/memories/graph/search", response_model=GraphSearchResponse)
async def graph_search(
    query: str = Query(..., description="Search query text"),
    user_id: str = Query(..., description="User ID to scope results"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    max_depth: int = Query(2, ge=1, le=5, description="Maximum traversal depth"),
    entity_types: Optional[List[str]] = Query(None, description="Filter by entity types"),
):
    """Search the knowledge graph for entities and relationships."""
    if graph_client is None:
        raise HTTPException(
            status_code=503,
            detail="Graph service unavailable — graph_client is not configured",
        )
    try:
        result = await graph_client.search_entities(
            query=query,
            user_id=user_id,
            limit=limit,
            entity_types=entity_types,
        )
        await _record_graph_billing_usage(
            user_id=user_id,
            query=query,
            operation_type="graph_query",
            result_count=result.get("total", len(result.get("entities", []))),
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error("Graph search failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Graph service unavailable: {e}",
        )


@app.get("/api/v1/memories/graph/neighbors", response_model=GraphNeighborsResponse)
async def graph_neighbors(
    entity_id: str = Query(..., description="Source entity ID"),
    depth: int = Query(2, ge=1, le=5, description="Maximum traversal depth"),
    user_id: Optional[str] = Query(None, description="Optional user ID for scoping"),
    relationship_types: Optional[List[str]] = Query(None, description="Filter by relationship types"),
):
    """Get neighbors of a graph entity."""
    if graph_client is None:
        raise HTTPException(
            status_code=503,
            detail="Graph service unavailable — graph_client is not configured",
        )
    try:
        result = await graph_client.get_entity_neighbors(
            entity_id=entity_id,
            max_depth=depth,
            relationship_types=relationship_types,
        )
        return result
    except Exception as e:
        logger.error("Graph neighbors lookup failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Graph service unavailable: {e}",
        )


# ==================== Related Memories (A-MEM Cross-Links) ====================


@app.get("/api/v1/memories/{memory_type}/{memory_id}/related")
async def get_related_memories(
    memory_type: MemoryType,
    memory_id: str,
    user_id: str = Query(...),
):
    """
    Get cross-linked memories for a given memory (A-MEM associations).

    Returns memories linked via similar_to, elaborates, or contradicts
    relationships discovered at extraction time.
    """
    try:
        results = await memory_service.get_related_memories(
            memory_id=memory_id,
            memory_type=memory_type.value,
            user_id=user_id,
        )
        return {"related_memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting related memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Generic Memory Routes ====================


@app.get("/api/v1/memories/{memory_type}/{memory_id}")
async def get_memory(memory_type: MemoryType, memory_id: str, user_id: Optional[str] = Query(None)):
    """Get memory by ID and type"""
    try:
        result = await memory_service.get_memory(memory_id, memory_type, user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Memory not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories")
async def list_memories(
    user_id: str = Query(...),
    memory_type: Optional[MemoryType] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    importance_min: Optional[float] = Query(None),
):
    """List memories for a user"""
    try:
        params = MemoryListParams(
            user_id=user_id,
            memory_type=memory_type,
            limit=limit,
            offset=offset,
            importance_min=importance_min,
        )
        result = await memory_service.list_memories(params)
        return {"memories": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/stats", response_model=MemoryServiceStats)
async def memory_stats(user_id: str = Query(...)):
    """Aggregate stats for a user's memory store.

    Returns total count, per-type breakdown, consolidation queue depth, and
    the timestamp of the most recent extraction. Used by the Agent SDK
    ``MemoryStack.getStats()`` (xenoISA/isA_Agent_SDK#736) and the upstream
    Mate ``/v1/memory/knowledge`` surface (xenoISA/isA_Mate#439).

    Empty user → 200 with all-zero counts (NOT 404).
    """
    try:
        by_type: Dict[str, int] = {}
        last_extraction: Optional[datetime] = None

        for memory_type in MemoryType:
            params = MemoryListParams(
                user_id=user_id,
                memory_type=memory_type,
                limit=100,
                offset=0,
            )
            items = await memory_service.list_memories(params)
            count = len(items)
            if count:
                by_type[memory_type.value] = count
                for item in items:
                    created = item.get("created_at")
                    if isinstance(created, datetime):
                        if last_extraction is None or created > last_extraction:
                            last_extraction = created

        # Consolidation queue depth — best-effort: skip if the consolidation
        # service hasn't been wired up yet. The acceptance criteria allow
        # zero when not available.
        consolidation_queue_depth = 0
        try:
            consol = getattr(memory_service, "consolidation_service", None)
            if consol is not None and hasattr(consol, "queue_depth"):
                consolidation_queue_depth = await consol.queue_depth(user_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Consolidation queue depth unavailable: %s", exc)

        return MemoryServiceStats(
            user_id=user_id,
            total_memories=sum(by_type.values()),
            by_type=by_type,
            consolidation_queue_depth=consolidation_queue_depth,
            last_extraction_at=last_extraction,
        )
    except Exception as e:
        logger.error("Error computing memory stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/memories/{memory_type}/{memory_id}", response_model=MemoryOperationResult)
async def update_memory(
    memory_type: MemoryType,
    memory_id: str,
    request: MemoryUpdateRequest,
    user_id: str = Query(...),
):
    """Update a memory"""
    try:
        result = await memory_service.update_memory(
            memory_id=memory_id,
            memory_type=memory_type,
            request=request,
            user_id=user_id,
        )
        return result
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/memories/{memory_type}/{memory_id}", response_model=MemoryOperationResult)
async def delete_memory(memory_type: MemoryType, memory_id: str, user_id: str = Query(...)):
    """Delete a memory"""
    try:
        result = await memory_service.delete_memory(memory_id, memory_type, user_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Search Operations ====================


@app.get("/api/v1/memories/factual/search/subject")
async def search_facts_by_subject(
    user_id: str = Query(...),
    subject: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
):
    """Search factual memories by subject"""
    try:
        results = await memory_service.search_facts_by_subject(user_id, subject, limit)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error searching facts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/episodic/search/event_type")
async def search_episodes_by_event_type(
    user_id: str = Query(...),
    event_type: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
):
    """Search episodic memories by event type"""
    try:
        results = await memory_service.search_episodes_by_event_type(user_id, event_type, limit)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error searching episodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/semantic/search/category")
async def search_concepts_by_category(
    user_id: str = Query(...),
    category: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
):
    """Search semantic memories by category"""
    try:
        results = await memory_service.search_concepts_by_category(user_id, category, limit)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error searching semantic memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Vector Search Operations ====================


@app.get("/api/v1/memories/factual/search/vector")
async def search_factual_vector(
    user_id: str = Query(...),
    query: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    score_threshold: float = Query(0.15, ge=0.0, le=1.0),
    rerank: bool = Query(False, description="Enable MMR re-ranking for diverse results"),
    mmr_lambda: float = Query(0.5, ge=0.0, le=1.0, description="MMR lambda: 0.0=diversity, 1.0=relevance"),
    order_results: bool = Query(
        False,
        description="Order results for lost-in-the-middle mitigation (highest importance at edges)",
    ),
):
    """Vector similarity search for factual memories using Qdrant"""
    try:
        results = await memory_service.vector_search_factual(
            user_id, query, limit, score_threshold, with_vectors=rerank
        )
        results = await _maybe_rerank(results, query, memory_service.factual_service, rerank, mmr_lambda, limit)
        if order_results and results:
            results = order_by_importance_edges(results)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in factual vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/episodic/search/vector")
async def search_episodic_vector(
    user_id: str = Query(...),
    query: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    score_threshold: float = Query(0.15, ge=0.0, le=1.0),
    rerank: bool = Query(False, description="Enable MMR re-ranking for diverse results"),
    mmr_lambda: float = Query(0.5, ge=0.0, le=1.0, description="MMR lambda: 0.0=diversity, 1.0=relevance"),
    order_results: bool = Query(
        False,
        description="Order results for lost-in-the-middle mitigation (highest importance at edges)",
    ),
):
    """Vector similarity search for episodic memories using Qdrant"""
    try:
        results = await memory_service.vector_search_episodic(
            user_id, query, limit, score_threshold, with_vectors=rerank
        )
        results = await _maybe_rerank(results, query, memory_service.episodic_service, rerank, mmr_lambda, limit)
        if order_results and results:
            results = order_by_importance_edges(results)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in episodic vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/procedural/search/vector")
async def search_procedural_vector(
    user_id: str = Query(...),
    query: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    score_threshold: float = Query(0.15, ge=0.0, le=1.0),
    rerank: bool = Query(False, description="Enable MMR re-ranking for diverse results"),
    mmr_lambda: float = Query(0.5, ge=0.0, le=1.0, description="MMR lambda: 0.0=diversity, 1.0=relevance"),
    order_results: bool = Query(
        False,
        description="Order results for lost-in-the-middle mitigation (highest importance at edges)",
    ),
):
    """Vector similarity search for procedural memories using Qdrant"""
    try:
        results = await memory_service.vector_search_procedural(
            user_id, query, limit, score_threshold, with_vectors=rerank
        )
        results = await _maybe_rerank(results, query, memory_service.procedural_service, rerank, mmr_lambda, limit)
        if order_results and results:
            results = order_by_importance_edges(results)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in procedural vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/semantic/search/vector")
async def search_semantic_vector(
    user_id: str = Query(...),
    query: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    score_threshold: float = Query(0.15, ge=0.0, le=1.0),
    rerank: bool = Query(False, description="Enable MMR re-ranking for diverse results"),
    mmr_lambda: float = Query(0.5, ge=0.0, le=1.0, description="MMR lambda: 0.0=diversity, 1.0=relevance"),
    order_results: bool = Query(
        False,
        description="Order results for lost-in-the-middle mitigation (highest importance at edges)",
    ),
):
    """Vector similarity search for semantic memories using Qdrant"""
    try:
        results = await memory_service.vector_search_semantic(
            user_id, query, limit, score_threshold, with_vectors=rerank
        )
        results = await _maybe_rerank(results, query, memory_service.semantic_service, rerank, mmr_lambda, limit)
        if order_results and results:
            results = order_by_importance_edges(results)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in semantic vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/working/search/vector")
async def search_working_vector(
    user_id: str = Query(...),
    query: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    score_threshold: float = Query(0.15, ge=0.0, le=1.0),
    include_expired: bool = Query(False),
    rerank: bool = Query(False, description="Enable MMR re-ranking for diverse results"),
    mmr_lambda: float = Query(0.5, ge=0.0, le=1.0, description="MMR lambda: 0.0=diversity, 1.0=relevance"),
    order_results: bool = Query(
        False,
        description="Order results for lost-in-the-middle mitigation (highest importance at edges)",
    ),
):
    """Vector similarity search for working memories using Qdrant"""
    try:
        results = await memory_service.vector_search_working(
            user_id, query, limit, score_threshold, include_expired, with_vectors=rerank
        )
        results = await _maybe_rerank(results, query, memory_service.working_service, rerank, mmr_lambda, limit)
        if order_results and results:
            results = order_by_importance_edges(results)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in working vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/session/search/vector")
async def search_session_vector(
    user_id: str = Query(...),
    query: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    score_threshold: float = Query(0.15, ge=0.0, le=1.0),
    session_id: Optional[str] = Query(None),
    rerank: bool = Query(False, description="Enable MMR re-ranking for diverse results"),
    mmr_lambda: float = Query(0.5, ge=0.0, le=1.0, description="MMR lambda: 0.0=diversity, 1.0=relevance"),
    order_results: bool = Query(
        False,
        description="Order results for lost-in-the-middle mitigation (highest importance at edges)",
    ),
):
    """Vector similarity search for session memories using Qdrant"""
    try:
        results = await memory_service.vector_search_session(
            user_id, query, limit, score_threshold, session_id, with_vectors=rerank
        )
        results = await _maybe_rerank(results, query, memory_service.session_service, rerank, mmr_lambda, limit)
        if order_results and results:
            results = order_by_importance_edges(results)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in session vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memories/search")
async def search_all_memories(
    user_id: str = Query(...),
    query: str = Query(...),
    memory_types: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    similarity_threshold: float = Query(0.15, ge=0.0, le=1.0),
    rerank: bool = Query(False, description="Enable MMR re-ranking for diverse results"),
    mmr_lambda: float = Query(
        0.5,
        ge=0.0,
        le=1.0,
        description="MMR lambda: 0.0=pure diversity, 1.0=pure relevance",
    ),
    order_results: bool = Query(
        False,
        description="Order results for lost-in-the-middle mitigation (highest importance at edges)",
    ),
    compress: bool = Query(False, description="Compress results into a focused summary using LLM"),
    target_tokens: int = Query(500, ge=50, le=5000, description="Target token count for compressed summary"),
    include_graph: bool = Query(False, description="Include local FalkorDB memory graph results"),
):
    """
    Universal semantic search across all memory types using vector similarity

    Args:
        user_id: User ID
        query: Search query string
        memory_types: Comma-separated memory types (e.g., "factual,episodic"). If not provided, searches all types.
        limit: Maximum number of results per memory type
        similarity_threshold: Minimum similarity score (0.0-1.0)
        rerank: Enable MMR (Maximal Marginal Relevance) re-ranking for diversity
        mmr_lambda: MMR trade-off parameter (0.0=diversity, 1.0=relevance)

    Returns:
        Combined search results from all specified memory types with similarity scores
    """
    try:
        results = {}
        total_count = 0

        # Parse memory types if provided, otherwise search all
        if memory_types:
            types_to_search = [t.strip().upper() for t in memory_types.split(",")]
        else:
            types_to_search = [
                "FACTUAL",
                "EPISODIC",
                "PROCEDURAL",
                "SEMANTIC",
                "WORKING",
                "SESSION",
            ]

        # Normalize to lowercase for internal use
        types_lower = [t.lower() for t in types_to_search]

        # When re-ranking is enabled, request vectors from Qdrant for MMR computation
        with_vectors = rerank

        # Generate embedding ONCE and share across all memory type searches
        query_embedding = await memory_service.factual_service._generate_embedding(query)
        if query_embedding is not None:
            logger.info(f"Generated shared query embedding ({len(query_embedding)} dims) for search: {query[:50]}...")
        else:
            logger.warning(f"Failed to generate query embedding for: {query[:50]}...")

        # Search all memory types in parallel
        search_dispatch = {
            "factual": (
                memory_service.vector_search_factual,
                memory_service.search_facts_by_subject,
            ),
            "episodic": (
                memory_service.vector_search_episodic,
                memory_service.search_episodes_by_event_type,
            ),
            "procedural": (
                memory_service.vector_search_procedural,
                memory_service.search_procedures_by_skill_type,
            ),
            "semantic": (
                memory_service.vector_search_semantic,
                memory_service.search_concepts_by_category,
            ),
            "working": (
                memory_service.vector_search_working,
                None,  # fallback handled inline
            ),
            "session": (
                memory_service.vector_search_session,
                None,
            ),
        }

        async def _search_one(memory_type: str):
            vector_fn, fallback_fn = search_dispatch[memory_type]
            try:
                return memory_type, await vector_fn(
                    user_id,
                    query,
                    limit,
                    similarity_threshold,
                    query_embedding=query_embedding,
                    with_vectors=with_vectors,
                )
            except Exception as e:
                logger.warning(f"Error in {memory_type} vector search, trying fallback: {e}")
                if fallback_fn:
                    try:
                        return memory_type, await fallback_fn(user_id, query, limit)
                    except Exception as e2:
                        logger.warning(f"Fallback for {memory_type} also failed: {e2}")
                elif memory_type == "working":
                    try:
                        all_working = await memory_service.get_active_working_memories(user_id)
                        filtered = [m for m in all_working if query.lower() in m.get("content", "").lower()]
                        return memory_type, filtered[:limit]
                    except Exception as e2:
                        logger.warning(f"Working memory fallback failed: {e2}")
                return memory_type, []

        parallel_results = await asyncio.gather(*[_search_one(t) for t in types_lower if t in search_dispatch])
        for memory_type, type_results in parallel_results:
            results[memory_type] = type_results
            total_count += len(type_results)
            logger.info(f"Vector search found {len(type_results)} {memory_type} memories")

        # Apply MMR re-ranking per memory type if enabled
        if rerank and query_embedding is not None:
            for memory_type in list(results.keys()):
                if results[memory_type]:
                    try:
                        results[memory_type] = apply_mmr_reranking(
                            results[memory_type],
                            query_embedding,
                            lambda_param=mmr_lambda,
                            top_k=limit,
                        )
                        logger.info(f"MMR re-ranked {memory_type} results (lambda={mmr_lambda})")
                    except Exception as e:
                        logger.warning(f"MMR re-ranking failed for {memory_type}, using raw results: {e}")

        # Apply context ordering per memory type if enabled
        if order_results:
            for memory_type in list(results.keys()):
                if results[memory_type]:
                    results[memory_type] = order_by_importance_edges(results[memory_type])

        # Query knowledge graph if enabled
        graph_results = None
        if include_graph and graph_client is not None:
            try:
                graph_results = await graph_client.search_entities(query=query, user_id=user_id, limit=limit)
                if graph_results.get("error"):
                    logger.warning("Graph query returned error: %s", graph_results["error"])
                else:
                    logger.info(
                        "Graph search found %d entities for query: %s",
                        graph_results.get("total", 0),
                        query[:50],
                    )
            except Exception as e:
                logger.warning("Graph query failed, continuing without graph results: %s", e)
                graph_results = {"entities": [], "total": 0, "error": str(e)}

        # Apply context compression if enabled
        if compress:
            try:
                compressor = ContextCompressor()
                compressed_summary = await compressor.compress_memories(
                    memories=results,
                    target_tokens=target_tokens,
                    query_context=query,
                )
                return {
                    "query": query,
                    "user_id": user_id,
                    "searched_types": types_to_search,
                    "compressed": True,
                    "target_tokens": target_tokens,
                    "summary": compressed_summary,
                    "results": results,
                    "total_count": total_count,
                }
            except Exception as e:
                logger.warning(f"Context compression failed, returning uncompressed: {e}")

        response = {
            "query": query,
            "user_id": user_id,
            "searched_types": types_to_search,
            "results": results,
            "total_count": total_count,
        }
        if graph_results is not None:
            response["graph_results"] = graph_results
        if rerank:
            response["reranked"] = True
            response["mmr_lambda"] = mmr_lambda
        if order_results:
            response["context_ordered"] = True

        return response

    except Exception as e:
        logger.error(f"Error in universal search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Hybrid Search (Vector + Graph) ====================


@app.get("/api/v1/memories/hybrid-search")
async def hybrid_search(
    query: str = Query(...),
    user_id: str = Query(...),
    memory_types: Optional[str] = Query(None, description="Comma-separated memory types (e.g., 'factual,episodic')"),
    limit: int = Query(10, ge=1, le=100),
    vector_weight: float = Query(0.6, ge=0.0, le=1.0, description="Weight for vector similarity results"),
    graph_weight: float = Query(0.4, ge=0.0, le=1.0, description="Weight for graph traversal results"),
):
    """
    Hybrid search combining Qdrant vector similarity with FalkorDB graph traversal.

    Merges results from both sources using configurable weights.
    Falls back to vector-only if the local memory graph is unavailable.

    Each result includes a 'source' field: "vector", "graph", or "both".
    """
    try:
        # --- Vector search across requested memory types ---
        if memory_types:
            types_to_search = [t.strip().lower() for t in memory_types.split(",")]
        else:
            types_to_search = [
                "factual",
                "episodic",
                "procedural",
                "semantic",
                "working",
                "session",
            ]

        # Generate embedding once
        query_embedding = await memory_service.factual_service._generate_embedding(query)

        # Collect vector results from all requested types
        vector_results: List[Dict[str, Any]] = []

        search_methods = {
            "factual": memory_service.vector_search_factual,
            "episodic": memory_service.vector_search_episodic,
            "procedural": memory_service.vector_search_procedural,
            "semantic": memory_service.vector_search_semantic,
            "working": memory_service.vector_search_working,
            "session": memory_service.vector_search_session,
        }

        for mem_type in types_to_search:
            search_fn = search_methods.get(mem_type)
            if not search_fn:
                continue
            try:
                results = await search_fn(user_id, query, limit, 0.15, query_embedding=query_embedding)
                for r in results:
                    r.setdefault("memory_id", r.get("id", ""))
                vector_results.extend(results)
            except Exception as e:
                logger.warning("Hybrid search: vector search failed for %s: %s", mem_type, e)

        # --- Graph search via local memory graph adapter ---
        graph_results: List[Dict[str, Any]] = []
        graph_available = False

        try:
            if graph_client is not None and await graph_client.health_check():
                graph_available = True
                entity_resp = await graph_client.search_entities(query=query, user_id=user_id, limit=limit)
                await _record_graph_billing_usage(
                    user_id=user_id,
                    query=query,
                    operation_type="graph_query",
                    result_count=entity_resp.get("total", len(entity_resp.get("entities", []))),
                    limit=limit,
                )
                for entity in entity_resp.get("entities", []):
                    graph_results.append(
                        {
                            "memory_id": entity.get("id", entity.get("entity_id", "")),
                            "content": entity.get("content", entity.get("name", "")),
                            "memory_type": entity.get("memory_type", entity.get("type", "graph")),
                            "relevance_score": entity.get("relevance_score", entity.get("score", 0.5)),
                        }
                    )
            else:
                logger.info("Hybrid search: graph service unavailable, falling back to vector-only")
        except Exception as e:
            graph_available = False
            logger.warning("Hybrid search: graph query failed, falling back to vector-only: %s", e)

        # --- Merge results ---
        merged = merge_hybrid_results(
            vector_results,
            graph_results,
            vector_weight=vector_weight,
            graph_weight=graph_weight,
        )

        # Trim to requested limit
        merged = merged[:limit]

        return {
            "query": query,
            "user_id": user_id,
            "vector_weight": vector_weight,
            "graph_weight": graph_weight,
            "results": merged,
            "total_count": len(merged),
            "graph_available": graph_available,
        }

    except Exception as e:
        logger.error("Error in hybrid search: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Memory Decay ====================


@app.post("/api/v1/memories/decay", response_model=DecayResponse)
async def run_memory_decay(request: DecayRequest):
    """
    Run Ebbinghaus forgetting-curve decay on memory importance scores.

    Reduces importance_score of unaccessed memories over time.
    Memories with importance >= protected_threshold are never decayed.
    Memories that decay below floor_threshold are soft-deleted (importance set to 0).
    Access count resets the decay timer (spaced repetition effect).
    """
    try:
        from .decay_service import DecayService, DecayConfig

        config = DecayConfig(
            half_life_days=request.half_life_days,
            floor_threshold=request.floor_threshold,
            protected_threshold=request.protected_threshold,
        )
        decay_svc = DecayService(memory_service=memory_service, config=config)
        result = await decay_svc.run_decay_cycle(user_id=request.user_id)

        return DecayResponse(
            success=True,
            total_processed=result["total_processed"],
            decayed_count=result["decayed_count"],
            floored_count=result["floored_count"],
            protected_count=result["protected_count"],
            skipped_count=result["skipped_count"],
            message=(
                f"Decay cycle complete: {result['decayed_count']} decayed, "
                f"{result['floored_count']} floored, {result['protected_count']} protected"
            ),
        )
    except Exception as e:
        logger.error(f"Error running memory decay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Memory Consolidation ====================


@app.post("/api/v1/memories/consolidate", response_model=ConsolidationResponse)
async def run_memory_consolidation(request: ConsolidationRequest):
    """
    Run memory consolidation pipeline: promote frequently-accessed episodic
    memories into semantic knowledge.

    Identifies episodic memories with high access counts and sufficient age,
    clusters them by embedding similarity, and uses an LLM to summarize each
    cluster into a semantic memory. Original episodics are tagged as consolidated,
    and bidirectional associations are created between the new semantic memory
    and its source episodics.
    """
    try:
        from .consolidation_service import ConsolidationService, ConsolidationConfig

        config = ConsolidationConfig(
            min_access_count=request.min_access_count,
            min_age_days=request.min_age_days,
            max_cluster_size=request.max_cluster_size,
            similarity_threshold=request.similarity_threshold,
        )
        consolidation_svc = ConsolidationService(
            episodic_service=memory_service.episodic_service,
            semantic_service=memory_service.semantic_service,
            association_service=memory_service.association_service,
            config=config,
        )
        result = await consolidation_svc.run_consolidation(user_id=request.user_id, config=config)

        return ConsolidationResponse(
            success=True,
            consolidated_count=result["consolidated_count"],
            new_semantic_ids=result["new_semantic_ids"],
            source_episodic_ids=result["source_episodic_ids"],
            message=(
                f"Consolidation complete: {result['consolidated_count']} clusters consolidated, "
                f"{len(result['source_episodic_ids'])} episodics processed"
            ),
        )
    except Exception as e:
        logger.error(f"Error running memory consolidation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Statistics ====================


@app.get("/api/v1/memories/statistics")
async def get_memory_statistics(user_id: str = Query(...)):
    """Get memory statistics for a user"""
    try:
        stats = await memory_service.get_memory_statistics(user_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting memory statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Server Entry Point ====================

if __name__ == "__main__":
    import uvicorn

    port = service_config.service_port
    host = "0.0.0.0"

    logger.info(f"Starting Memory Service on {host}:{port}")

    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
