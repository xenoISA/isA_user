"""Project Service data contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class CreateProjectRequestContract(BaseModel):
    """Contract for project creation requests."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    custom_instructions: Optional[str] = Field(None, max_length=8000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be empty")
        return value


class UpdateProjectRequestContract(BaseModel):
    """Contract for project update requests."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class SetInstructionsRequestContract(BaseModel):
    """Contract for instruction updates."""

    instructions: str = Field(..., min_length=1, max_length=8000)


class ProjectResponseContract(BaseModel):
    """Contract for project responses."""

    id: str
    user_id: str
    org_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    custom_instructions: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProjectListResponseContract(BaseModel):
    """Contract for project list responses."""

    projects: List[ProjectResponseContract]
    total: int = Field(ge=0)


class ProjectTestDataFactory:
    """Factory helpers for project-service tests."""

    @staticmethod
    def make_create_request(**overrides) -> CreateProjectRequestContract:
        payload = {
            "name": "Project Alpha",
            "description": "Primary project workspace",
            "custom_instructions": "Keep responses concise and reference the project context.",
        }
        payload.update(overrides)
        return CreateProjectRequestContract(**payload)

    @staticmethod
    def make_project_response(**overrides) -> ProjectResponseContract:
        now = datetime.now(timezone.utc)
        payload = {
            "id": f"prj_{uuid4().hex[:24]}",
            "user_id": "usr_project_owner",
            "org_id": None,
            "name": "Project Alpha",
            "description": "Primary project workspace",
            "custom_instructions": "Keep responses concise and reference the project context.",
            "created_at": now,
            "updated_at": now,
        }
        payload.update(overrides)
        return ProjectResponseContract(**payload)
