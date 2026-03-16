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

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Depends, Body
from fastapi.responses import JSONResponse

from contextlib import asynccontextmanager
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics
from isa_common.consul_client import ConsulRegistry

from .models import (
    MemoryType, MemoryOperationResult,
    MemoryCreateRequest, MemoryUpdateRequest, MemoryListParams,
    MemoryServiceStatus, DecayRequest, DecayResponse
)
from .memory_service import MemoryService
from .context_ordering import order_by_importance_edges
from .mmr_reranker import apply_mmr_reranking
from .events.handlers import MemoryEventHandlers
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
from .factory import create_memory_service

# Initialize configuration
config_manager = ConfigManager("memory_service")
service_config = config_manager.get_service_config()

# Setup logger
logger = setup_service_logger("memory_service")

# Global service instance
memory_service = None
consul_registry: Optional[ConsulRegistry] = None
shutdown_manager = GracefulShutdown("memory_service")


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global memory_service, consul_registry
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
            await event_bus.subscribe_to_events(
                pattern=event_pattern,
                handler=handler_func
            )

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

    # Consul 服务注册
    if service_config.consul_enabled:
        try:
            # 获取路由元数据
            route_meta = get_routes_for_consul()

            # 合并服务元数据
            consul_meta = {
                'version': SERVICE_METADATA['version'],
                'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                **route_meta
            }

            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA['service_name'],
                service_port=service_config.service_port,
                consul_host=service_config.consul_host,
                consul_port=service_config.consul_port,
                tags=SERVICE_METADATA['tags'],
                meta=consul_meta,
                health_check_type='ttl'  # Use TTL for reliable health checks
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

    # Consul deregistration is handled by shutdown_manager.initiate_shutdown()
    # so traffic stops before we reject requests with 503.


# Create FastAPI app
app = FastAPI(
    title="Memory Service",
    description="AI-powered memory service for intelligent information storage and retrieval",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "memory_service")


# ==================== Health Check ====================

@app.get("/api/v1/memories/health")
@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint"""
    try:
        # Report unhealthy during shutdown so Consul TTL checks fail
        if shutdown_manager.is_shutting_down:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "shutting_down",
                    "service": "memory_service",
                    "timestamp": datetime.now().isoformat()
                }
            )

        db_connected = await memory_service.check_connection()

        status = MemoryServiceStatus(
            service="memory_service",
            status="operational" if db_connected else "degraded",
            version="1.0.0",
            database_connected=db_connected,
            timestamp=datetime.now()
        )

        return {
            "status": status.status,
            "service": status.service,
            "version": status.version,
            "database_connected": status.database_connected,
            "timestamp": status.timestamp.isoformat()
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "memory_service",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# ==================== AI-Powered Memory Storage ====================

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
            importance_score=request.importance_score
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
            importance_score=request.importance_score
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
            importance_score=request.importance_score
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
            importance_score=request.importance_score
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
            "sequence": interaction_sequence
        }

        result = await memory_service.session_service.store_session_memory(
            user_id=request.user_id,
            session_id=request.session_id,
            content=request.message_content,
            interaction_sequence=interaction_sequence,
            conversation_state=conversation_state,
            session_type="chat"
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
    max_recent_messages: int = Query(5)
):
    """Get comprehensive session context"""
    try:
        # Get session memories
        memories = await memory_service.get_session_memories(user_id, session_id)

        # Sort by interaction sequence
        memories.sort(key=lambda m: m.get('interaction_sequence', 0))

        # Get recent messages
        recent_messages = memories[-max_recent_messages:] if max_recent_messages > 0 else memories

        # Build context response
        context = {
            "session_id": session_id,
            "user_id": user_id,
            "total_messages": len(memories),
            "recent_messages": recent_messages
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
async def get_session_memories(
    session_id: str,
    user_id: str = Query(...)
):
    """Get memories for a specific session"""
    try:
        results = await memory_service.get_session_memories(user_id, session_id)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting session memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memories/session/{session_id}/deactivate", response_model=MemoryOperationResult)
async def deactivate_session(
    session_id: str,
    user_id: str = Query(...)
):
    """Deactivate a session"""
    try:
        result = await memory_service.deactivate_session(user_id, session_id)
        return result
    except Exception as e:
        logger.error(f"Error deactivating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memories/session/{session_id}/summarize", response_model=MemoryOperationResult)
async def summarize_session(
    session_id: str,
    request: SummarizeSessionRequest
):
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
                message="No messages found in session to summarize"
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
                    data=existing_summary
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
            "created_at": datetime.now().isoformat()
        }

        # Store summary via repository
        await memory_service.session_service.repository.store_session_summary(
            user_id=request.user_id,
            session_id=session_id,
            summary_data=summary_data
        )

        return MemoryOperationResult(
            success=True,
            operation="summarize_session",
            message=f"Session summarized ({len(memories)} messages → {len(key_sentences)} key points)",
            data=summary_data
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
            "content_preview": request.dialog_content[:100] if len(request.dialog_content) > 100 else request.dialog_content
        }

        result = await memory_service.working_service.store_working_memory(
            user_id=request.user_id,
            content=request.dialog_content,
            task_id=task_id,
            task_context=task_context,
            priority=5,
            ttl_seconds=request.ttl_seconds
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
async def get_memory(
    memory_type: MemoryType,
    memory_id: str,
    user_id: Optional[str] = Query(None)
):
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
    importance_min: Optional[float] = Query(None)
):
    """List memories for a user"""
    try:
        params = MemoryListParams(
            user_id=user_id,
            memory_type=memory_type,
            limit=limit,
            offset=offset,
            importance_min=importance_min
        )
        result = await memory_service.list_memories(params)
        return {"memories": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/memories/{memory_type}/{memory_id}", response_model=MemoryOperationResult)
async def update_memory(
    memory_type: MemoryType,
    memory_id: str,
    request: MemoryUpdateRequest,
    user_id: str = Query(...)
):
    """Update a memory"""
    try:
        result = await memory_service.update_memory(
            memory_id=memory_id,
            memory_type=memory_type,
            request=request,
            user_id=user_id
        )
        return result
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/memories/{memory_type}/{memory_id}", response_model=MemoryOperationResult)
async def delete_memory(
    memory_type: MemoryType,
    memory_id: str,
    user_id: str = Query(...)
):
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
    limit: int = Query(10, ge=1, le=100)
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
    limit: int = Query(10, ge=1, le=100)
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
    limit: int = Query(10, ge=1, le=100)
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
    order_results: bool = Query(False, description="Order results for lost-in-the-middle mitigation (highest importance at edges)"),
):
    """Vector similarity search for factual memories using Qdrant"""
    try:
        results = await memory_service.vector_search_factual(user_id, query, limit, score_threshold, with_vectors=rerank)
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
    order_results: bool = Query(False, description="Order results for lost-in-the-middle mitigation (highest importance at edges)"),
):
    """Vector similarity search for episodic memories using Qdrant"""
    try:
        results = await memory_service.vector_search_episodic(user_id, query, limit, score_threshold, with_vectors=rerank)
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
    order_results: bool = Query(False, description="Order results for lost-in-the-middle mitigation (highest importance at edges)"),
):
    """Vector similarity search for procedural memories using Qdrant"""
    try:
        results = await memory_service.vector_search_procedural(user_id, query, limit, score_threshold, with_vectors=rerank)
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
    order_results: bool = Query(False, description="Order results for lost-in-the-middle mitigation (highest importance at edges)"),
):
    """Vector similarity search for semantic memories using Qdrant"""
    try:
        results = await memory_service.vector_search_semantic(user_id, query, limit, score_threshold, with_vectors=rerank)
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
    order_results: bool = Query(False, description="Order results for lost-in-the-middle mitigation (highest importance at edges)"),
):
    """Vector similarity search for working memories using Qdrant"""
    try:
        results = await memory_service.vector_search_working(user_id, query, limit, score_threshold, include_expired, with_vectors=rerank)
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
    order_results: bool = Query(False, description="Order results for lost-in-the-middle mitigation (highest importance at edges)"),
):
    """Vector similarity search for session memories using Qdrant"""
    try:
        results = await memory_service.vector_search_session(user_id, query, limit, score_threshold, session_id, with_vectors=rerank)
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
    mmr_lambda: float = Query(0.5, ge=0.0, le=1.0, description="MMR lambda: 0.0=pure diversity, 1.0=pure relevance"),
    order_results: bool = Query(False, description="Order results for lost-in-the-middle mitigation (highest importance at edges)"),
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
            types_to_search = [t.strip().upper() for t in memory_types.split(',')]
        else:
            types_to_search = ['FACTUAL', 'EPISODIC', 'PROCEDURAL', 'SEMANTIC', 'WORKING', 'SESSION']

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

        # Search factual memories using vector search
        if 'factual' in types_lower:
            try:
                factual_results = await memory_service.vector_search_factual(
                    user_id, query, limit, similarity_threshold, query_embedding=query_embedding, with_vectors=with_vectors
                )
                results['factual'] = factual_results
                total_count += len(factual_results)
                logger.info(f"Vector search found {len(factual_results)} factual memories for query: {query[:50]}...")
            except Exception as e:
                logger.warning(f"Error in factual vector search, falling back to text: {e}")
                try:
                    factual_results = await memory_service.search_facts_by_subject(user_id, query, limit)
                    results['factual'] = factual_results
                    total_count += len(factual_results)
                except Exception as e2:
                    logger.warning(f"Fallback text search also failed: {e2}")
                    results['factual'] = []

        # Search episodic memories using vector search
        if 'episodic' in types_lower:
            try:
                episodic_results = await memory_service.vector_search_episodic(
                    user_id, query, limit, similarity_threshold, query_embedding=query_embedding, with_vectors=with_vectors
                )
                results['episodic'] = episodic_results
                total_count += len(episodic_results)
                logger.info(f"Vector search found {len(episodic_results)} episodic memories")
            except Exception as e:
                logger.warning(f"Error in episodic vector search, falling back to text: {e}")
                try:
                    episodic_results = await memory_service.search_episodes_by_event_type(user_id, query, limit)
                    results['episodic'] = episodic_results
                    total_count += len(episodic_results)
                except Exception as e2:
                    logger.warning(f"Fallback text search also failed: {e2}")
                    results['episodic'] = []

        # Search procedural memories using vector search
        if 'procedural' in types_lower:
            try:
                procedural_results = await memory_service.vector_search_procedural(
                    user_id, query, limit, similarity_threshold, query_embedding=query_embedding, with_vectors=with_vectors
                )
                results['procedural'] = procedural_results
                total_count += len(procedural_results)
                logger.info(f"Vector search found {len(procedural_results)} procedural memories")
            except Exception as e:
                logger.warning(f"Error in procedural vector search, falling back to text: {e}")
                try:
                    procedural_results = await memory_service.search_procedures_by_skill_type(user_id, query, limit)
                    results['procedural'] = procedural_results
                    total_count += len(procedural_results)
                except Exception as e2:
                    logger.warning(f"Fallback text search also failed: {e2}")
                    results['procedural'] = []

        # Search semantic memories using vector search
        if 'semantic' in types_lower:
            try:
                semantic_results = await memory_service.vector_search_semantic(
                    user_id, query, limit, similarity_threshold, query_embedding=query_embedding, with_vectors=with_vectors
                )
                results['semantic'] = semantic_results
                total_count += len(semantic_results)
                logger.info(f"Vector search found {len(semantic_results)} semantic memories")
            except Exception as e:
                logger.warning(f"Error in semantic vector search, falling back to text: {e}")
                try:
                    semantic_results = await memory_service.search_concepts_by_category(user_id, query, limit)
                    results['semantic'] = semantic_results
                    total_count += len(semantic_results)
                except Exception as e2:
                    logger.warning(f"Fallback text search also failed: {e2}")
                    results['semantic'] = []

        # Search working memories using vector search
        if 'working' in types_lower:
            try:
                working_results = await memory_service.vector_search_working(
                    user_id, query, limit, similarity_threshold, query_embedding=query_embedding, with_vectors=with_vectors
                )
                results['working'] = working_results
                total_count += len(working_results)
                logger.info(f"Vector search found {len(working_results)} working memories")
            except Exception as e:
                logger.warning(f"Error in working vector search, falling back to filter: {e}")
                try:
                    working_results = await memory_service.get_active_working_memories(user_id)
                    working_filtered = [m for m in working_results if query.lower() in m.get('content', '').lower()]
                    results['working'] = working_filtered[:limit]
                    total_count += len(results['working'])
                except Exception as e2:
                    logger.warning(f"Fallback filter also failed: {e2}")
                    results['working'] = []

        # Search session memories using vector search
        if 'session' in types_lower:
            try:
                session_results = await memory_service.vector_search_session(
                    user_id, query, limit, similarity_threshold, query_embedding=query_embedding, with_vectors=with_vectors
                )
                results['session'] = session_results
                total_count += len(session_results)
                logger.info(f"Vector search found {len(session_results)} session memories")
            except Exception as e:
                logger.warning(f"Error in session vector search: {e}")
                results['session'] = []

        # Apply MMR re-ranking per memory type if enabled
        if rerank and query_embedding is not None:
            for memory_type in list(results.keys()):
                if results[memory_type]:
                    try:
                        results[memory_type] = apply_mmr_reranking(
                            results[memory_type], query_embedding, lambda_param=mmr_lambda, top_k=limit
                        )
                        logger.info(f"MMR re-ranked {memory_type} results (lambda={mmr_lambda})")
                    except Exception as e:
                        logger.warning(f"MMR re-ranking failed for {memory_type}, using raw results: {e}")

        # Apply context ordering per memory type if enabled
        if order_results:
            for memory_type in list(results.keys()):
                if results[memory_type]:
                    results[memory_type] = order_by_importance_edges(results[memory_type])

        response = {
            "query": query,
            "user_id": user_id,
            "searched_types": types_to_search,
            "results": results,
            "total_count": total_count,
        }
        if rerank:
            response["reranked"] = True
            response["mmr_lambda"] = mmr_lambda
        if order_results:
            response["context_ordered"] = True

        return response

    except Exception as e:
        logger.error(f"Error in universal search: {e}")
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

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
