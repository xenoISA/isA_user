"""CDD L4 data contract for training_service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TrainingCohortContract(BaseModel):
    organization_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    path_code: str = Field(min_length=1)
    course_ids: list[str] = Field(min_length=1)
    learner_ids: list[str] = Field(default_factory=list)
    delivery_status: Literal["scheduled", "in_progress", "completed", "cancelled"]


class TrainingAttendanceContract(BaseModel):
    learner_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    status: Literal["present", "absent", "excused"]


class TrainingLabSubmissionContract(BaseModel):
    artifact: str = Field(min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)


class TrainingReviewOverrideContract(BaseModel):
    status: Literal["approved", "rejected", "resubmission_requested"]
    reason: str = Field(min_length=1)
    score: int | None = Field(default=None, ge=0, le=100)
    passed: bool | None = None
