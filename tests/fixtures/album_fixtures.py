"""
Album Service Fixtures

Factories for album service test data.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .common import make_user_id, make_org_id


def make_album_id() -> str:
    """Generate a unique album ID"""
    return f"album_test_{uuid.uuid4().hex[:12]}"


def make_photo_id() -> str:
    """Generate a unique photo ID"""
    return f"photo_test_{uuid.uuid4().hex[:12]}"


def make_album(
    album_id: Optional[str] = None,
    name: str = "Test Album",
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    description: Optional[str] = None,
    cover_photo_id: Optional[str] = None,
    photo_count: int = 0,
    auto_sync: bool = True,
    sync_frames: Optional[List[str]] = None,
    is_family_shared: bool = False,
    sharing_resource_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an album dict for testing"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "album_id": album_id or make_album_id(),
        "name": name,
        "user_id": user_id or make_user_id(),
        "organization_id": organization_id,
        "description": description,
        "cover_photo_id": cover_photo_id,
        "photo_count": photo_count,
        "auto_sync": auto_sync,
        "sync_frames": sync_frames or [],
        "is_family_shared": is_family_shared,
        "sharing_resource_id": sharing_resource_id,
        "tags": tags or [],
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
        "last_synced_at": None,
    }


def make_album_create_request(
    name: Optional[str] = None,
    description: Optional[str] = None,
    organization_id: Optional[str] = None,
    auto_sync: bool = True,
    sync_frames: Optional[List[str]] = None,
    is_family_shared: bool = False,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create an album creation request"""
    return {
        "name": name or f"Test Album {uuid.uuid4().hex[:8]}",
        "description": description,
        "organization_id": organization_id,
        "auto_sync": auto_sync,
        "sync_frames": sync_frames or [],
        "is_family_shared": is_family_shared,
        "tags": tags or [],
    }


def make_album_update_request(
    name: Optional[str] = None,
    description: Optional[str] = None,
    cover_photo_id: Optional[str] = None,
    auto_sync: Optional[bool] = None,
    sync_frames: Optional[List[str]] = None,
    is_family_shared: Optional[bool] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create an album update request (partial)"""
    request = {}
    if name is not None:
        request["name"] = name
    if description is not None:
        request["description"] = description
    if cover_photo_id is not None:
        request["cover_photo_id"] = cover_photo_id
    if auto_sync is not None:
        request["auto_sync"] = auto_sync
    if sync_frames is not None:
        request["sync_frames"] = sync_frames
    if is_family_shared is not None:
        request["is_family_shared"] = is_family_shared
    if tags is not None:
        request["tags"] = tags
    return request


def make_add_photos_request(
    photo_ids: Optional[List[str]] = None,
    count: int = 2,
) -> Dict[str, Any]:
    """Create an add photos request"""
    if photo_ids is None:
        photo_ids = [make_photo_id() for _ in range(count)]
    return {"photo_ids": photo_ids}


def make_remove_photos_request(
    photo_ids: List[str],
) -> Dict[str, Any]:
    """Create a remove photos request"""
    return {"photo_ids": photo_ids}


def make_album_photo(
    album_id: Optional[str] = None,
    photo_id: Optional[str] = None,
    added_by: Optional[str] = None,
    is_featured: bool = False,
    display_order: int = 0,
    ai_tags: Optional[List[str]] = None,
    ai_objects: Optional[List[str]] = None,
    ai_scenes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create an album photo dict for testing"""
    return {
        "album_id": album_id or make_album_id(),
        "photo_id": photo_id or make_photo_id(),
        "added_by": added_by or make_user_id(),
        "is_featured": is_featured,
        "display_order": display_order,
        "ai_tags": ai_tags or [],
        "ai_objects": ai_objects or [],
        "ai_scenes": ai_scenes or [],
        "face_detection_results": {},
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
