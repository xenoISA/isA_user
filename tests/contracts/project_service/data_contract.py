"""
Project Service Data Contract

Canonical test-layer data structures for project_service, including
project CRUD metadata and project knowledge file responses.
"""

from datetime import datetime, timezone
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectRequestContract(BaseModel):
    """Contract for project creation requests."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    custom_instructions: Optional[str] = Field(None, max_length=8000)


class SetInstructionsRequestContract(BaseModel):
    """Contract for project instruction updates."""

    instructions: str = Field(..., min_length=1, max_length=8000)


class ProjectFileUploadRequestContract(BaseModel):
    """Contract for project knowledge file metadata at upload time."""

    project_id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    content_type: Optional[str] = None
    file_size: Optional[int] = Field(None, ge=0)


class ProjectResponseContract(BaseModel):
    """Contract for persisted project responses."""

    id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    org_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    custom_instructions: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProjectFileResponseContract(BaseModel):
    """Contract for a single project knowledge file record."""

    id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    file_type: Optional[str] = None
    file_size: Optional[int] = Field(None, ge=0)
    storage_path: str = Field(..., min_length=1)
    created_at: Optional[datetime] = None


class ProjectFileListResponseContract(BaseModel):
    """Contract for project knowledge file list responses."""

    files: List[ProjectFileResponseContract]
    total: int = Field(..., ge=0)


class ProjectErrorResponseContract(BaseModel):
    """Structured project_service error contract."""

    status: str = Field("error")
    error: str
    detail: str


class ProjectTestDataFactory:
    """Factory helpers for project_service contract-driven tests."""

    @staticmethod
    def make_project_id() -> str:
        return f"proj_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_file_id() -> str:
        return f"file_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_project_request(**overrides) -> ProjectRequestContract:
        data = {
            "name": "Knowledge Workspace",
            "description": "Project-scoped context",
            "custom_instructions": "Prefer project knowledge when answering.",
        }
        data.update(overrides)
        return ProjectRequestContract(**data)

    @staticmethod
    def make_project_response(**overrides) -> ProjectResponseContract:
        now = datetime.now(timezone.utc)
        data = {
            "id": ProjectTestDataFactory.make_project_id(),
            "user_id": "user_test_123",
            "name": "Knowledge Workspace",
            "description": "Project-scoped context",
            "custom_instructions": "Prefer project knowledge when answering.",
            "created_at": now,
            "updated_at": now,
        }
        data.update(overrides)
        return ProjectResponseContract(**data)

    @staticmethod
    def make_project_file_response(**overrides) -> ProjectFileResponseContract:
        now = datetime.now(timezone.utc)
        project_id = overrides.get(
            "project_id", ProjectTestDataFactory.make_project_id()
        )
        filename = overrides.get("filename", "guide.md")
        data = {
            "id": ProjectTestDataFactory.make_file_id(),
            "project_id": project_id,
            "filename": filename,
            "file_type": "text/markdown",
            "file_size": 128,
            "storage_path": f"storage/{project_id}/{filename}",
            "created_at": now,
        }
        data.update(overrides)
        return ProjectFileResponseContract(**data)
