"""L1 Unit — Project service Pydantic models"""

import pytest
from pydantic import ValidationError

from microservices.project_service.models import (
    CreateProjectRequest,
    UpdateProjectRequest,
    SetInstructionsRequest,
    ProjectResponse,
    ProjectListResponse,
    ErrorResponse,
)


class TestCreateProjectRequest:
    def test_valid_minimal(self):
        req = CreateProjectRequest(name="My Project")
        assert req.name == "My Project"
        assert req.description is None
        assert req.custom_instructions is None

    def test_valid_full(self):
        req = CreateProjectRequest(
            name="Proj", description="desc", custom_instructions="do X"
        )
        assert req.custom_instructions == "do X"

    def test_name_required(self):
        with pytest.raises(ValidationError):
            CreateProjectRequest()

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            CreateProjectRequest(name="x" * 256)

    def test_instructions_max_length(self):
        with pytest.raises(ValidationError):
            CreateProjectRequest(name="ok", custom_instructions="x" * 8001)


class TestUpdateProjectRequest:
    def test_empty_is_valid(self):
        req = UpdateProjectRequest()
        assert req.name is None
        assert req.description is None

    def test_partial_update(self):
        req = UpdateProjectRequest(name="New Name")
        assert req.name == "New Name"


class TestSetInstructionsRequest:
    def test_instructions_required(self):
        with pytest.raises(ValidationError):
            SetInstructionsRequest()

    def test_instructions_max_length(self):
        with pytest.raises(ValidationError):
            SetInstructionsRequest(instructions="x" * 8001)


class TestErrorResponse:
    def test_shape(self):
        err = ErrorResponse(error="not_found", detail="Project not found")
        assert err.status == "error"
        assert err.error == "not_found"


class TestProjectListResponse:
    def test_empty_list(self):
        resp = ProjectListResponse(projects=[], total=0)
        assert resp.total == 0
        assert resp.projects == []
