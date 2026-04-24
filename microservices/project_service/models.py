"""Project Service Pydantic Models (#258, #296, #297)"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ProjectRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


# ── Requests ─────────────────────────────────────────────────────────────


class CreateProjectRequest(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    custom_instructions: Optional[str] = Field(None, max_length=8000)


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class SetInstructionsRequest(BaseModel):
    instructions: str = Field(..., max_length=8000)


# ── Responses ────────────────────────────────────────────────────────────


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    org_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    custom_instructions: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProjectFileResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    storage_path: str
    created_at: Optional[datetime] = None


class ProjectFileListResponse(BaseModel):
    files: List[ProjectFileResponse]
    total: int


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    detail: str
