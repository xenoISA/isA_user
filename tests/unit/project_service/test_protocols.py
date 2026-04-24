"""L1 Unit — Project service protocols and exceptions"""

import pytest

from microservices.project_service.protocols import (
    ProjectServiceException,
    ProjectNotFoundError,
    ProjectPermissionError,
    ProjectLimitExceeded,
    InvalidProjectUpdate,
    ProjectStorageError,
    RepositoryError,
)


class TestExceptionHierarchy:
    """All domain exceptions inherit from ProjectServiceException."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ProjectNotFoundError,
            ProjectPermissionError,
            ProjectLimitExceeded,
            InvalidProjectUpdate,
            ProjectStorageError,
            RepositoryError,
        ],
    )
    def test_inherits_from_base(self, exc_cls):
        assert issubclass(exc_cls, ProjectServiceException)

    def test_project_not_found_message(self):
        exc = ProjectNotFoundError("proj_123 not found")
        assert "proj_123" in str(exc)

    def test_invalid_project_update_detail(self):
        exc = InvalidProjectUpdate("name too long")
        assert exc.detail == "name too long"

    def test_repository_error_stores_cause(self):
        cause = RuntimeError("connection refused")
        exc = RepositoryError("DB down", cause=cause)
        assert exc.cause is cause
        assert exc.detail == "DB down"

    def test_repository_error_defaults(self):
        exc = RepositoryError()
        assert exc.detail == "Repository error"
        assert exc.cause is None
