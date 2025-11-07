"""
Storage Service Routes Registry

Defines all API routes for Consul service registration and discovery.
This ensures route metadata is centralized and easy to maintain.
"""

from typing import List, Dict, Any


# Route definitions for storage_service
# Note: Storage service has extensive API surface, grouped by functionality
STORAGE_SERVICE_ROUTES = [
    # Health & Info
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Health check"},
    {"path": "/info", "methods": ["GET"], "auth_required": False, "description": "Service info"},

    # File Storage Operations
    {"path": "/api/v1/storage/files/upload", "methods": ["POST"], "auth_required": True, "description": "Upload file"},
    {"path": "/api/v1/storage/files", "methods": ["GET"], "auth_required": True, "description": "List files"},
    {"path": "/api/v1/storage/files/{file_id}", "methods": ["GET", "DELETE"], "auth_required": True, "description": "File CRUD"},
    {"path": "/api/v1/storage/files/{file_id}/download", "methods": ["GET"], "auth_required": True, "description": "Download file"},
    {"path": "/api/v1/storage/files/{file_id}/share", "methods": ["POST"], "auth_required": True, "description": "Share file"},
    {"path": "/api/v1/storage/shares/{share_id}", "methods": ["GET"], "auth_required": False, "description": "Get shared file"},
    {"path": "/api/v1/storage/files/stats", "methods": ["GET"], "auth_required": True, "description": "Storage stats"},
    {"path": "/api/v1/storage/files/quota", "methods": ["GET"], "auth_required": True, "description": "Storage quota"},

    # Photo Versions
    {"path": "/api/v1/storage/photos/versions/save", "methods": ["POST"], "auth_required": True, "description": "Save photo version"},
    {"path": "/api/v1/storage/photos/{photo_id}/versions", "methods": ["POST"], "auth_required": True, "description": "Get photo versions"},
    {"path": "/api/v1/storage/photos/{photo_id}/versions/{version_id}/switch", "methods": ["PUT"], "auth_required": True, "description": "Switch photo version"},
    {"path": "/api/v1/storage/photos/versions/{version_id}", "methods": ["DELETE"], "auth_required": True, "description": "Delete photo version"},

    # Intelligence - Semantic Search & RAG
    {"path": "/api/v1/storage/files/search", "methods": ["POST"], "auth_required": True, "description": "Semantic file search"},
    {"path": "/api/v1/storage/files/ask", "methods": ["POST"], "auth_required": True, "description": "RAG query on files"},
    {"path": "/api/v1/storage/intelligence/stats", "methods": ["GET"], "auth_required": True, "description": "Intelligence stats"},
    {"path": "/api/v1/storage/intelligence/search", "methods": ["POST"], "auth_required": True, "description": "Intelligence search"},
    {"path": "/api/v1/storage/intelligence/rag", "methods": ["POST"], "auth_required": True, "description": "Intelligence RAG"},

    # Image Intelligence
    {"path": "/api/v1/storage/intelligence/image/store", "methods": ["POST"], "auth_required": True, "description": "Store image for AI"},
    {"path": "/api/v1/storage/intelligence/image/search", "methods": ["POST"], "auth_required": True, "description": "Image semantic search"},
    {"path": "/api/v1/storage/intelligence/image/rag", "methods": ["POST"], "auth_required": True, "description": "Image RAG query"},

    # Albums
    {"path": "/api/v1/storage/albums", "methods": ["POST", "GET"], "auth_required": True, "description": "Album CRUD"},
    {"path": "/api/v1/storage/albums/{album_id}", "methods": ["GET", "PUT", "DELETE"], "auth_required": True, "description": "Album operations"},
    {"path": "/api/v1/storage/albums/{album_id}/photos", "methods": ["POST", "GET"], "auth_required": True, "description": "Album photos"},
    {"path": "/api/v1/storage/albums/{album_id}/share", "methods": ["POST"], "auth_required": True, "description": "Share album"},
    {"path": "/api/v1/storage/albums/{album_id}/sync-status/{frame_id}", "methods": ["GET"], "auth_required": True, "description": "Album sync status"},
    {"path": "/api/v1/storage/albums/{album_id}/sync/{frame_id}", "methods": ["POST"], "auth_required": True, "description": "Sync album to frame"},

    # Gallery & Playlists
    {"path": "/api/v1/storage/gallery/albums", "methods": ["GET"], "auth_required": True, "description": "Gallery albums"},
    {"path": "/api/v1/storage/gallery/playlists", "methods": ["GET", "POST"], "auth_required": True, "description": "Playlists"},
    {"path": "/api/v1/storage/gallery/playlists/{playlist_id}", "methods": ["GET", "PUT", "DELETE"], "auth_required": True, "description": "Playlist ops"},
    {"path": "/api/v1/storage/gallery/playlists/{playlist_id}/photos", "methods": ["GET"], "auth_required": True, "description": "Playlist photos"},
    {"path": "/api/v1/storage/gallery/photos/random", "methods": ["GET"], "auth_required": True, "description": "Random photos"},
    {"path": "/api/v1/storage/gallery/photos/metadata", "methods": ["POST"], "auth_required": True, "description": "Update metadata"},
    {"path": "/api/v1/storage/gallery/photos/{file_id}/metadata", "methods": ["GET"], "auth_required": True, "description": "Get metadata"},

    # Cache Management
    {"path": "/api/v1/storage/gallery/cache/preload", "methods": ["POST"], "auth_required": True, "description": "Preload cache"},
    {"path": "/api/v1/storage/gallery/cache/{frame_id}/stats", "methods": ["GET"], "auth_required": True, "description": "Cache stats"},
    {"path": "/api/v1/storage/gallery/cache/{frame_id}/clear", "methods": ["POST"], "auth_required": True, "description": "Clear cache"},

    # Schedules & Frames
    {"path": "/api/v1/storage/gallery/schedules", "methods": ["POST"], "auth_required": True, "description": "Create schedule"},
    {"path": "/api/v1/storage/gallery/schedules/{frame_id}", "methods": ["GET"], "auth_required": True, "description": "Get schedule"},
    {"path": "/api/v1/storage/gallery/frames/{frame_id}/playlists", "methods": ["GET"], "auth_required": True, "description": "Frame playlists"},

    # Test Endpoints (dev only)
    {"path": "/api/v1/storage/test/upload", "methods": ["POST"], "auth_required": False, "description": "Test upload"},
    {"path": "/api/v1/storage/test/minio-status", "methods": ["GET"], "auth_required": False, "description": "Test MinIO"},
]


def get_routes_for_consul() -> Dict[str, Any]:
    """
    Get formatted route metadata for Consul service registration

    Note: Consul meta fields have a 512 character limit per value.
    We use compact encoding and split routes into categories.

    Returns:
        Dictionary containing route information for Consul meta field
    """
    # Group routes by category
    health_routes = []
    file_routes = []
    photo_routes = []
    intelligence_routes = []
    album_routes = []
    gallery_routes = []
    test_routes = []

    for route in STORAGE_SERVICE_ROUTES:
        path = route["path"]
        compact_path = path.replace("/api/v1/storage/", "")

        if "health" in path or "info" in path:
            health_routes.append(compact_path)
        elif "test" in path:
            test_routes.append(compact_path)
        elif "intelligence" in path or "search" in path or "ask" in path or "rag" in path:
            intelligence_routes.append(compact_path)
        elif "albums" in path:
            album_routes.append(compact_path)
        elif "gallery" in path or "playlists" in path or "cache" in path or "schedules" in path or "frames" in path:
            gallery_routes.append(compact_path)
        elif "photos/versions" in path:
            photo_routes.append(compact_path)
        else:
            file_routes.append(compact_path)

    # Create compact route representation for meta
    route_meta = {
        "route_count": str(len(STORAGE_SERVICE_ROUTES)),
        "base_path": "/api/v1/storage",

        # Category summaries (under 512 chars each)
        "health": ",".join(health_routes[:10]),  # Limit to avoid 512 char limit
        "files": ",".join(file_routes[:15]),
        "photos": ",".join(photo_routes[:10]),
        "intelligence": ",".join(intelligence_routes[:10]),
        "albums": ",".join(album_routes[:10]),
        "gallery": ",".join(gallery_routes[:15]),

        # Methods and auth summary
        "methods": "GET,POST,PUT,DELETE",
        "public_count": str(sum(1 for r in STORAGE_SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in STORAGE_SERVICE_ROUTES if r["auth_required"])),

        # Endpoint for full route details
        "routes_endpoint": "/info"
    }

    return route_meta


def get_all_routes() -> List[Dict[str, Any]]:
    """Get all route definitions"""
    return STORAGE_SERVICE_ROUTES


def get_routes_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """Get routes grouped by category"""
    categories = {
        "health": [],
        "file_storage": [],
        "photo_versions": [],
        "intelligence": [],
        "albums": [],
        "gallery": [],
        "test": []
    }

    for route in STORAGE_SERVICE_ROUTES:
        path = route["path"]
        if "health" in path or "info" in path:
            categories["health"].append(route)
        elif "test" in path:
            categories["test"].append(route)
        elif "intelligence" in path or "search" in path or "ask" in path or "rag" in path:
            categories["intelligence"].append(route)
        elif "albums" in path:
            categories["albums"].append(route)
        elif "gallery" in path or "playlists" in path or "cache" in path or "schedules" in path:
            categories["gallery"].append(route)
        elif "photos/versions" in path:
            categories["photo_versions"].append(route)
        else:
            categories["file_storage"].append(route)

    return categories


# Service metadata for Consul registration
SERVICE_METADATA = {
    "service_name": "storage_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "storage"],
    "capabilities": [
        "file_storage",
        "photo_management",
        "semantic_search",
        "rag_queries",
        "album_management",
        "gallery_display",
        "image_ai"
    ]
}
