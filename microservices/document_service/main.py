"""
Document Microservice

Knowledge base document management service with RAG incremental updates
and fine-grained authorization.

Port: 8227
"""

import os
import sys
import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from isa_common.consul_client import ConsulRegistry

from .models import (
    DocumentCreateRequest,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentPermissionUpdateRequest,
    DocumentPermissionResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    DocumentStatsResponse,
    DocumentServiceStatus,
    DocumentStatus,
    DocumentType,
)
from .document_service import (
    DocumentService,
    DocumentServiceError,
    DocumentNotFoundError,
    DocumentValidationError,
    DocumentPermissionError,
)
from .routes_registry import get_routes_for_consul, SERVICE_METADATA

# Initialize configuration
config_manager = ConfigManager("document_service")
service_config = config_manager.get_service_config()

# Setup loggers
app_logger = setup_service_logger("document_service")
logger = app_logger

# Global service instance
document_service = None
event_bus = None  # NATS event bus
consul_registry: Optional[ConsulRegistry] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global document_service, event_bus, consul_registry

    logger.info("Starting Document Service...")

    # Initialize NATS event bus
    try:
        event_bus = await get_event_bus("document_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    # Initialize service
    document_service = DocumentService(
        event_bus=event_bus, config_manager=config_manager
    )

    # Subscribe to events (file.deleted, user.deleted, etc.)
    if event_bus:
        try:
            from .events import DocumentEventHandler
            event_handler = DocumentEventHandler(document_service)

            # Subscribe to file events (file.deleted from storage_service)
            await event_bus.subscribe_to_events(
                pattern="*.file.>",
                handler=lambda msg: event_handler.handle_event(msg),
                durable="document-file-consumer-v1"
            )
            logger.info("✅ Subscribed to file events (*.file.>)")

            # Subscribe to user/org deletion events
            await event_bus.subscribe_to_events(
                pattern="*.user.>",
                handler=lambda msg: event_handler.handle_event(msg),
                durable="document-user-consumer-v1"
            )
            logger.info("✅ Subscribed to user events (*.user.>)")

            await event_bus.subscribe_to_events(
                pattern="*.organization.>",
                handler=lambda msg: event_handler.handle_event(msg),
                durable="document-org-consumer-v1"
            )
            logger.info("✅ Subscribed to organization events (*.organization.>)")

        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    # Check database connection
    health = await document_service.check_health()
    if health.get("status") != "healthy":
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    # Consul service registration
    if service_config.consul_enabled:
        try:
            # Get route metadata
            route_meta = get_routes_for_consul()

            # Merge service metadata
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

    logger.info(f"Document Service started on port {service_config.service_port}")

    yield

    # Cleanup
    if event_bus:
        try:
            await event_bus.close()
            logger.info("Document event bus closed")
        except Exception as e:
            logger.error(f"Error closing event bus: {e}")

    # Consul deregister
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("✅ Service deregistered from Consul")
        except Exception as e:
            logger.error(f"❌ Failed to deregister from Consul: {e}")

    logger.info("Document Service stopped")


# Initialize FastAPI app
app = FastAPI(
    title="Document Service",
    description="Knowledge base document management with RAG and authorization",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== Dependency Injection ====================

def get_document_service() -> DocumentService:
    """Get document service instance"""
    if document_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return document_service


def get_user_id(user_id: str = Query(..., description="User ID")) -> str:
    """Extract user_id from query parameters"""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return user_id


# ==================== Health Check ====================

@app.get("/", response_model=DocumentServiceStatus)
async def root():
    """Root endpoint - service status"""
    health = await document_service.check_health()
    return DocumentServiceStatus(
        service="document_service",
        status="operational" if health.get("status") == "healthy" else "degraded",
        port=service_config.service_port,
        version="1.0.0",
        database_connected=health.get("database") == "connected",
        timestamp=datetime.fromisoformat(health.get("timestamp"))
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health = await document_service.check_health()
    status_code = 200 if health.get("status") == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


# ==================== Document CRUD Endpoints ====================

@app.post("/api/v1/documents", response_model=DocumentResponse, status_code=201)
async def create_document(
    request: DocumentCreateRequest,
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    service: DocumentService = Depends(get_document_service)
):
    """
    Create a new knowledge document and index it

    Creates document record and triggers RAG indexing via Digital Analytics Service.
    """
    try:
        return await service.create_document(request, user_id, organization_id)
    except DocumentValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# NOTE: Stats endpoint MUST be defined before {doc_id} routes to avoid path collision
@app.get("/api/v1/documents/stats", response_model=DocumentStatsResponse)
async def get_user_stats(
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    service: DocumentService = Depends(get_document_service)
):
    """
    Get user's document statistics
    """
    try:
        return await service.get_user_stats(user_id, organization_id)
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    user_id: str = Depends(get_user_id),
    service: DocumentService = Depends(get_document_service)
):
    """
    Get document by ID (with permission check)
    """
    try:
        return await service.get_document(doc_id, user_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents", response_model=List[DocumentResponse])
async def list_documents(
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    status: Optional[DocumentStatus] = Query(None),
    doc_type: Optional[DocumentType] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: DocumentService = Depends(get_document_service)
):
    """
    List user's documents with filters
    """
    try:
        return await service.list_user_documents(
            user_id, organization_id, status, doc_type, limit, offset
        )
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user_id: str = Depends(get_user_id),
    permanent: bool = Query(False, description="Permanent delete (including Qdrant points)"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Delete document

    - soft delete (default): Mark as deleted in database
    - permanent delete: Delete from database and Qdrant
    """
    try:
        success = await service.delete_document(doc_id, user_id, permanent)
        return {"success": success, "message": "Document deleted"}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RAG Incremental Update Endpoints ====================

@app.put("/api/v1/documents/{doc_id}/update", response_model=DocumentResponse)
async def update_document_incremental(
    doc_id: str,
    request: DocumentUpdateRequest,
    user_id: str = Depends(get_user_id),
    service: DocumentService = Depends(get_document_service)
):
    """
    RAG incremental update

    Strategies:
    - FULL: Delete old index, full reindex
    - SMART: Smart incremental (similarity-based)
    - DIFF: Diff-based precise update
    """
    try:
        return await service.update_document_incremental(doc_id, request, user_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DocumentValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Permission Management Endpoints ====================

@app.put("/api/v1/documents/{doc_id}/permissions", response_model=DocumentPermissionResponse)
async def update_document_permissions(
    doc_id: str,
    request: DocumentPermissionUpdateRequest,
    user_id: str = Depends(get_user_id),
    service: DocumentService = Depends(get_document_service)
):
    """
    Update document permissions

    Updates both database and Qdrant point metadata for permission filtering.
    """
    try:
        return await service.update_document_permissions(doc_id, request, user_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents/{doc_id}/permissions", response_model=DocumentPermissionResponse)
async def get_document_permissions(
    doc_id: str,
    user_id: str = Depends(get_user_id),
    service: DocumentService = Depends(get_document_service)
):
    """
    Get document permissions
    """
    try:
        return await service.get_document_permissions(doc_id, user_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RAG Query Endpoints (Permission-Filtered) ====================

@app.post("/api/v1/documents/rag/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    service: DocumentService = Depends(get_document_service)
):
    """
    RAG query with automatic permission filtering

    Only returns results from documents the user has access to.
    """
    try:
        return await service.rag_query_secure(request, user_id, organization_id)
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents/search", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    service: DocumentService = Depends(get_document_service)
):
    """
    Semantic search with permission filtering

    Searches across indexed documents the user has access to.
    """
    try:
        return await service.semantic_search_secure(request, user_id, organization_id)
    except DocumentServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn

    port = service_config.service_port if service_config else 8227

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
