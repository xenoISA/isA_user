"""
Weather Service Component Test Configuration

Pytest fixtures for component testing with mocked dependencies.
"""
import pytest
import pytest_asyncio

from .mocks import MockWeatherRepository, MockEventBus, MockWeatherProvider, MockCache


@pytest.fixture
def mock_repository():
    """Create mock weather repository"""
    return MockWeatherRepository()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest.fixture
def mock_weather_provider():
    """Create mock weather provider"""
    return MockWeatherProvider()


@pytest.fixture
def mock_cache():
    """Create mock cache"""
    return MockCache()


@pytest_asyncio.fixture
async def weather_service(mock_repository, mock_event_bus):
    """
    Create WeatherService with mocked dependencies.

    Note: Current WeatherService creates repository internally.
    This fixture provides event_bus injection for event testing.
    For full DI testing, WeatherService would need refactoring.
    """
    from microservices.weather_service.weather_service import WeatherService

    service = WeatherService(event_bus=mock_event_bus)
    # Override the internal repository for testing
    service.repository = mock_repository

    yield service

    # Cleanup
    await service.close()
