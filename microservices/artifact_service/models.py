"""
Artifact Service Models

Pydantic v2 models for the artifact library backend. Field names match the
``LibraryArtifact`` shape consumed by the frontend store
(``isA_/src/stores/useArtifactLibrary.ts``) so that the BFF in pages/api can
proxy responses through with minimal reshaping. See
``isA_/docs/design/427-artifact-flows.md`` §4.1 for the table layout.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==================== Enumerations ====================


class ArtifactVisibility(str, Enum):
    """Visibility model from design doc §4.2."""

    PRIVATE = "private"  # owner only
    UNLISTED = "unlisted"  # anyone with token
    ORG = "org"  # token holders within owner_org_id
    PUBLIC = "public"  # token holders anywhere; indexable=false


class ArtifactStorageScope(str, Enum):
    """Storage scope for the Phase 3 KV table — kept as an enum so the column
    can be persisted today even though the KV plumbing lands later."""

    PERSONAL = "personal"
    SHARED = "shared"
    NONE = "none"


# ==================== Core Models ====================


def _parse_json_array(v):
    if isinstance(v, str):
        try:
            return json.loads(v) if v else []
        except json.JSONDecodeError:
            return []
    return v if v is not None else []


def _parse_json_dict(v):
    if isinstance(v, str):
        try:
            return json.loads(v) if v else {}
        except json.JSONDecodeError:
            return {}
    return v if v is not None else {}


class ArtifactVersion(BaseModel):
    """A single immutable version row."""

    id: str
    artifact_id: str
    number: int
    content: str
    language: Optional[str] = None
    filename: Optional[str] = None
    blob_url: Optional[str] = None  # Phase 1: plain string; Phase 3 plumbs Vercel Blob
    a2ui_state_json: Optional[Dict[str, Any]] = None
    instruction: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("a2ui_state_json", mode="before")
    @classmethod
    def _parse_a2ui(cls, v):
        return _parse_json_dict(v) if v not in (None, "") else None

    model_config = ConfigDict(from_attributes=True)


class Artifact(BaseModel):
    """Top-level artifact row + its version list."""

    id: str
    owner_user_id: str
    owner_org_id: Optional[str] = None
    title: str
    content_type: str  # e.g. 'code', 'markdown', 'svg', 'html', matching ArtifactContentType
    current_version_id: Optional[str] = None
    source_session_id: Optional[str] = None
    source_message_id: Optional[str] = None
    parent_artifact_id: Optional[str] = None  # remix lineage
    visibility: ArtifactVisibility = ArtifactVisibility.PRIVATE
    ai_runtime_enabled: bool = False
    storage_scope: ArtifactStorageScope = ArtifactStorageScope.NONE
    metadata: Dict[str, Any] = Field(default_factory=dict)
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    versions: List[ArtifactVersion] = Field(default_factory=list)

    @field_validator("metadata", mode="before")
    @classmethod
    def _parse_metadata(cls, v):
        return _parse_json_dict(v)

    model_config = ConfigDict(from_attributes=True)


# ==================== Request Models ====================


class ArtifactVersionCreateRequest(BaseModel):
    """Used both as the inner payload for POST /artifacts and the body of
    POST /artifacts/:id/versions."""

    content: str
    language: Optional[str] = None
    filename: Optional[str] = None
    blob_url: Optional[str] = None
    a2ui_state_json: Optional[Dict[str, Any]] = None
    instruction: Optional[str] = None
    # Optional explicit version number — when None, the service auto-increments.
    number: Optional[int] = Field(None, ge=1)


class ArtifactCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content_type: str = Field(..., min_length=1, max_length=64)
    owner_org_id: Optional[str] = None
    source_session_id: Optional[str] = None
    source_message_id: Optional[str] = None
    parent_artifact_id: Optional[str] = None
    visibility: ArtifactVisibility = ArtifactVisibility.PRIVATE
    ai_runtime_enabled: bool = False
    storage_scope: ArtifactStorageScope = ArtifactStorageScope.NONE
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # First version is always required at creation time.
    version: ArtifactVersionCreateRequest


class ArtifactUpdateRequest(BaseModel):
    """PATCH body — every field is optional and only supplied fields are
    written. Visibility flips are the most common use from
    ``useArtifactLibrary.setVisibility``."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    visibility: Optional[ArtifactVisibility] = None
    ai_runtime_enabled: Optional[bool] = None
    storage_scope: Optional[ArtifactStorageScope] = None
    metadata: Optional[Dict[str, Any]] = None


# ==================== Response Models ====================


class ArtifactListItem(BaseModel):
    """Compact listing row — does NOT include version content to keep
    payloads small for the library grid (xenoISA/isA_#427 §13)."""

    id: str
    owner_user_id: str
    owner_org_id: Optional[str]
    title: str
    content_type: str
    visibility: ArtifactVisibility
    parent_artifact_id: Optional[str]
    source_session_id: Optional[str]
    current_version_id: Optional[str]
    version_count: int
    latest_version_number: Optional[int] = None
    latest_language: Optional[str] = None
    latest_filename: Optional[str] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ArtifactListResponse(BaseModel):
    items: List[ArtifactListItem]
    total: int
    cursor: Optional[str] = None  # opaque next-page cursor


class ArtifactScope(str, Enum):
    """``GET /api/v1/artifacts?scope=`` filter values — mirror the frontend
    ``ArtifactScopeFilter`` in ``useArtifactLibrary.ts``."""

    ALL = "all"
    OWNED = "owned"
    SHARED = "shared"


# ==================== Service Status ====================


class ArtifactServiceStatus(BaseModel):
    service: str = "artifact_service"
    status: str = "operational"
    port: int = 8291
    version: str = "1.0.0"
    database_connected: bool
    timestamp: datetime


__all__ = [
    "ArtifactVisibility",
    "ArtifactStorageScope",
    "ArtifactScope",
    "ArtifactVersion",
    "Artifact",
    "ArtifactCreateRequest",
    "ArtifactVersionCreateRequest",
    "ArtifactUpdateRequest",
    "ArtifactListItem",
    "ArtifactListResponse",
    "ArtifactServiceStatus",
]
