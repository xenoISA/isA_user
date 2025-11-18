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
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from isa_common.consul_client import ConsulRegistry

from .models import (
    MemoryType, MemoryOperationResult,
    MemoryCreateRequest, MemoryUpdateRequest, MemoryListParams,
    MemoryServiceStatus
)
from .memory_service import MemoryService
from .events.handlers import MemoryEventHandlers
from .routes_registry import get_routes_for_consul, SERVICE_METADATA

# Initialize configuration
config_manager = ConfigManager("memory_service")
service_config = config_manager.get_service_config()

# Setup logger
logger = setup_service_logger("memory_service")

# Global service instance
memory_service = None
consul_registry: Optional[ConsulRegistry] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global memory_service, consul_registry

    logger.info("Starting Memory Service with AI capabilities...")

    # Initialize event bus for subscribing to session events
    event_bus = None
    event_handlers = None
    try:
        from .event_handlers import MemoryEventHandlers

        event_bus = await get_event_bus("memory_service")
        logger.info("✅ Event bus initialized successfully")

        # Initialize service with event bus
        memory_service = MemoryService(event_bus=event_bus)

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

        # Initialize service without event bus
        memory_service = MemoryService(event_bus=None)

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
                health_check_type='http'
            )
            consul_registry.register()
            logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count')} routes")
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with Consul: {e}")
            consul_registry = None

    logger.info("Memory Service initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down Memory Service...")
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")

    # Consul 注销
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("✅ Service deregistered from Consul")
        except Exception as e:
            logger.error(f"❌ Failed to deregister from Consul: {e}")


# Create FastAPI app
app = FastAPI(
    title="Memory Service",
    description="AI-powered memory service for intelligent information storage and retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check ====================

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint"""
    try:
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


@app.post("/memories/factual/extract", response_model=MemoryOperationResult)
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


@app.post("/memories/episodic/extract", response_model=MemoryOperationResult)
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


@app.post("/memories/procedural/extract", response_model=MemoryOperationResult)
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


@app.post("/memories/semantic/extract", response_model=MemoryOperationResult)
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

@app.post("/memories", response_model=MemoryOperationResult)
async def create_memory(request: MemoryCreateRequest):
    """Create a new memory"""
    try:
        result = await memory_service.create_memory(request)
        return result
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Session-specific Routes (must come before generic routes) ====================

@app.post("/memories/session/store", response_model=MemoryOperationResult)
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


@app.get("/memories/session/{session_id}/context")
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


@app.get("/memories/session/{session_id}")
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


@app.post("/memories/session/{session_id}/deactivate", response_model=MemoryOperationResult)
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


# ==================== Working Memory-specific Routes (must come before generic routes) ====================

@app.post("/memories/working/store", response_model=MemoryOperationResult)
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


@app.get("/memories/working/active")
async def get_active_working_memories(user_id: str = Query(...)):
    """Get active working memories"""
    try:
        results = await memory_service.get_active_working_memories(user_id)
        return {"memories": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting active working memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/working/cleanup", response_model=MemoryOperationResult)
async def cleanup_expired_memories(user_id: Optional[str] = Query(None)):
    """Clean up expired working memories"""
    try:
        result = await memory_service.cleanup_expired_memories(user_id)
        return result
    except Exception as e:
        logger.error(f"Error cleaning up expired memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Generic Memory Routes ====================

@app.get("/memories/{memory_type}/{memory_id}")
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


@app.get("/memories")
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


@app.put("/memories/{memory_type}/{memory_id}", response_model=MemoryOperationResult)
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


@app.delete("/memories/{memory_type}/{memory_id}", response_model=MemoryOperationResult)
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

@app.get("/memories/factual/search/subject")
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


@app.get("/memories/episodic/search/event_type")
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


@app.get("/memories/semantic/search/category")
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


@app.get("/memories/search")
async def search_all_memories(
    user_id: str = Query(...),
    query: str = Query(...),
    memory_types: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Universal search across all memory types or specified types

    Args:
        user_id: User ID
        query: Search query string
        memory_types: Comma-separated memory types (e.g., "factual,episodic"). If not provided, searches all types.
        limit: Maximum number of results per memory type

    Returns:
        Combined search results from all specified memory types
    """
    try:
        results = {}
        total_count = 0

        # Parse memory types if provided, otherwise search all
        if memory_types:
            types_to_search = [t.strip() for t in memory_types.split(',')]
        else:
            types_to_search = ['factual', 'episodic', 'procedural', 'semantic', 'working', 'session']

        # Search factual memories
        if 'factual' in types_to_search:
            try:
                factual_results = await memory_service.search_facts_by_subject(user_id, query, limit)
                results['factual'] = factual_results
                total_count += len(factual_results)
            except Exception as e:
                logger.warning(f"Error searching factual memories: {e}")
                results['factual'] = []

        # Search episodic memories
        if 'episodic' in types_to_search:
            try:
                episodic_results = await memory_service.search_episodes_by_event_type(user_id, query, limit)
                results['episodic'] = episodic_results
                total_count += len(episodic_results)
            except Exception as e:
                logger.warning(f"Error searching episodic memories: {e}")
                results['episodic'] = []

        # Search procedural memories
        if 'procedural' in types_to_search:
            try:
                procedural_results = await memory_service.search_procedures_by_skill_type(user_id, query, limit)
                results['procedural'] = procedural_results
                total_count += len(procedural_results)
            except Exception as e:
                logger.warning(f"Error searching procedural memories: {e}")
                results['procedural'] = []

        # Search semantic memories
        if 'semantic' in types_to_search:
            try:
                semantic_results = await memory_service.search_concepts_by_category(user_id, query, limit)
                results['semantic'] = semantic_results
                total_count += len(semantic_results)
            except Exception as e:
                logger.warning(f"Error searching semantic memories: {e}")
                results['semantic'] = []

        # Search working memories (search by content match)
        if 'working' in types_to_search:
            try:
                working_results = await memory_service.get_active_working_memories(user_id)
                # Filter by query string in content
                working_filtered = [m for m in working_results if query.lower() in m.get('content', '').lower()]
                results['working'] = working_filtered[:limit]
                total_count += len(results['working'])
            except Exception as e:
                logger.warning(f"Error searching working memories: {e}")
                results['working'] = []

        # Search session memories (not implemented - would need session_id)
        if 'session' in types_to_search:
            results['session'] = []
            logger.info("Session memory search requires session_id, skipping")

        return {
            "query": query,
            "user_id": user_id,
            "searched_types": types_to_search,
            "results": results,
            "total_count": total_count
        }

    except Exception as e:
        logger.error(f"Error in universal search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Statistics ====================

@app.get("/memories/statistics")
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
