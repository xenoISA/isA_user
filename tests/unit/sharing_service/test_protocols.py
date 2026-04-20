"""L1 Unit — Sharing service protocols and exceptions"""

import pytest

from microservices.sharing_service.protocols import (
    ShareExpiredError,
    ShareNotFoundError,
    SharePermissionError,
    ShareServiceError,
    ShareValidationError,
)

pytestmark = pytest.mark.unit


class TestExceptionHierarchy:
    def test_validation_error_is_service_error(self):
        assert issubclass(ShareValidationError, ShareServiceError)

    def test_permission_error_is_service_error(self):
        assert issubclass(SharePermissionError, ShareServiceError)

    def test_not_found_is_independent(self):
        assert not issubclass(ShareNotFoundError, ShareServiceError)

    def test_expired_is_independent(self):
        assert not issubclass(ShareExpiredError, ShareServiceError)

    def test_exceptions_carry_message(self):
        err = ShareNotFoundError("token abc not found")
        assert "abc" in str(err)
