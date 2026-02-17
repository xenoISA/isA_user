"""
Document Service Routes Registry

Defines all API routes and metadata for Consul service discovery
"""

SERVICE_METADATA = {
    'service_name': 'document_service',
    'version': '1.0.0',
    'capabilities': [
        'knowledge_base',
        'rag_incremental_update',
        'document_permissions',
        'semantic_search',
        'document_versioning'
    ],
    'tags': [
        'v1',
        'document',
        'knowledge_base',
        'rag',
        'vector_search',
        'authorization'
    ]
}

# API Routes for Consul metadata
API_ROUTES = {
    # Health
    'GET /health': 'Service health check',
    'GET /api/v1/documents/health': 'Service health check (API v1)',

    # Document CRUD
    'POST /api/v1/documents': 'Create knowledge document',
    'GET /api/v1/documents/{doc_id}': 'Get document by ID',
    'GET /api/v1/documents': 'List user documents',
    'DELETE /api/v1/documents/{doc_id}': 'Delete document',

    # RAG Incremental Update
    'PUT /api/v1/documents/{doc_id}/update': 'RAG incremental update',

    # Permission Management
    'PUT /api/v1/documents/{doc_id}/permissions': 'Update document permissions',
    'GET /api/v1/documents/{doc_id}/permissions': 'Get document permissions',

    # RAG Query (Permission-Filtered)
    'POST /api/v1/documents/rag/query': 'RAG query with permission filtering',
    'POST /api/v1/documents/search': 'Semantic search with permission filtering',

    # Statistics
    'GET /api/v1/documents/stats': 'Get user document statistics',

    # Health
    'GET /health': 'Health check'
}


def get_routes_for_consul():
    """
    Get routes metadata for Consul registration

    Returns:
        dict: Route metadata for Consul
    """
    return {
        'route_count': str(len(API_ROUTES)),
        'routes': ','.join(list(API_ROUTES.keys())[:10]),  # First 10 routes
        'api_version': 'v1',
        'base_path': '/api/v1/documents',  # Required for APISIX route sync
    }
