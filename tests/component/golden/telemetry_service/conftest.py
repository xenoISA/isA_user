"""
Telemetry Service Component Test Configuration

Provides fixtures for component testing with mocked dependencies.
The autouse fixture prevents the TelemetryRepository from attempting
to connect to the real database during component tests.
"""
import pytest
from unittest.mock import patch

from .mocks import MockTelemetryRepository


# Global mock repository instance - shared across tests in a module
_mock_repo_instance = None


@pytest.fixture(autouse=True)
def patch_telemetry_repository(request):
    """
    Patch TelemetryRepository at import time to prevent real DB connections.

    This fixture runs before every test and ensures the repository doesn't
    attempt to connect to the actual database. Instead, it returns our
    MockTelemetryRepository which has all the proper async methods.
    """
    global _mock_repo_instance

    # Create fresh mock for each test
    _mock_repo_instance = MockTelemetryRepository()

    with patch("microservices.telemetry_service.telemetry_service.TelemetryRepository") as mock_repo_class:
        # Configure the mock class to return our MockTelemetryRepository instance
        mock_repo_class.return_value = _mock_repo_instance
        yield mock_repo_class


@pytest.fixture
def injected_mock_repo():
    """
    Get the mock repository instance that was injected into the service.
    Use this fixture to access the mock for assertions.
    """
    global _mock_repo_instance
    return _mock_repo_instance
