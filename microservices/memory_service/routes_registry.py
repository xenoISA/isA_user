"""
Memory Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# 定义所有路由
SERVICE_ROUTES = [
    {
        "path": "/",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Root health check"
    },
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check"
    },
    # Memory Extraction
    {
        "path": "/memories/factual/extract",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Extract factual memories using AI"
    },
    {
        "path": "/memories/episodic/extract",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Extract episodic memories using AI"
    },
    {
        "path": "/memories/procedural/extract",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Extract procedural memories using AI"
    },
    {
        "path": "/memories/semantic/extract",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Extract semantic memories using AI"
    },
    # Memory Storage
    {
        "path": "/memories",
        "methods": ["GET", "POST"],
        "auth_required": True,
        "description": "List/create memories"
    },
    {
        "path": "/memories/{memory_type}/{memory_id}",
        "methods": ["GET", "PUT", "DELETE"],
        "auth_required": True,
        "description": "Get/update/delete specific memory"
    },
    # Session Memory
    {
        "path": "/memories/session/store",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Store session memory"
    },
    {
        "path": "/memories/session/{session_id}/context",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get session context with AI-enhanced memory"
    },
    {
        "path": "/memories/session/{session_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get session memory history"
    },
    {
        "path": "/memories/session/{session_id}/deactivate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Deactivate session memory"
    },
    # Working Memory
    {
        "path": "/memories/working/store",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Store working memory"
    },
    {
        "path": "/memories/working/active",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get active working memories"
    },
    {
        "path": "/memories/working/cleanup",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Cleanup expired working memories"
    },
    # Memory Search
    {
        "path": "/memories/factual/search/subject",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search factual memories by subject"
    },
    {
        "path": "/memories/episodic/search/event_type",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search episodic memories by event type"
    },
    {
        "path": "/memories/semantic/search/category",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Search semantic memories by category"
    },
    {
        "path": "/memories/search",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Semantic search across all memories"
    },
    # Memory Statistics
    {
        "path": "/memories/statistics",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get memory statistics"
    },
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    为 Consul 生成紧凑的路由元数据
    注意：Consul meta 字段有 512 字符限制
    """
    # 按类别分组路由
    health_routes = []
    extraction_routes = []
    session_routes = []
    working_routes = []
    search_routes = []
    storage_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        # 使用紧凑表示：只保留路径的关键部分
        if path in ["/", "/health"]:
            health_routes.append(path)
        elif "/extract" in path:
            compact_path = path.replace("/memories/", "").replace("/extract", "")
            extraction_routes.append(compact_path)
        elif "/session/" in path:
            compact_path = path.replace("/memories/session/", "")
            session_routes.append(compact_path)
        elif "/working/" in path:
            compact_path = path.replace("/memories/working/", "")
            working_routes.append(compact_path)
        elif "/search" in path:
            compact_path = path.replace("/memories/", "").replace("/search", "")
            search_routes.append(compact_path)
        elif path == "/memories" or "/{memory_type}/{memory_id}" in path:
            storage_routes.append("crud")

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/memories",
        "health": ",".join(health_routes),
        "extraction": ",".join(extraction_routes),
        "session": "|".join(session_routes[:5]),  # 限制长度
        "working": ",".join(working_routes),
        "search": ",".join(search_routes),
        "storage": ",".join(storage_routes),
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# 服务元数据
SERVICE_METADATA = {
    "service_name": "memory_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "ai-powered", "memory-management"],
    "capabilities": [
        "factual_memory",
        "episodic_memory",
        "procedural_memory",
        "semantic_memory",
        "working_memory",
        "session_memory",
        "ai_extraction",
        "vector_search",
        "memory_statistics"
    ]
}
