"""
Weather Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_weather_service
    service = create_weather_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .weather_service import WeatherService


def create_weather_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> WeatherService:
    """
    Create WeatherService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager for service discovery
        event_bus: Event bus for publishing events (NATS)

    Returns:
        Configured WeatherService instance

    Note:
        Current WeatherService creates its own repository internally.
        For full DI, WeatherService would need refactoring to accept
        repository via constructor. This factory provides the event_bus
        injection which is the primary testability concern.
    """
    # WeatherService currently creates repository internally
    # This factory primarily handles event_bus injection
    return WeatherService(event_bus=event_bus)


def create_weather_service_for_testing(
    mock_repository=None,
    mock_event_bus=None,
) -> WeatherService:
    """
    Create WeatherService with mock dependencies for testing.

    Args:
        mock_repository: Mock repository (for future DI refactor)
        mock_event_bus: Mock event bus for testing events

    Returns:
        WeatherService configured for testing

    Note:
        Full repository injection requires refactoring WeatherService.
        Currently only event_bus can be mocked via constructor.
    """
    return WeatherService(event_bus=mock_event_bus)


class WeatherServiceFactory:
    """
    Factory class for creating WeatherService instances.

    Provides both production and testing factory methods.

    Usage:
        # Production
        service = WeatherServiceFactory.create_service(event_bus=nats_client)

        # Testing
        service = WeatherServiceFactory.create_for_testing(
            mock_event_bus=MockEventBus()
        )
    """

    @staticmethod
    def create_service(
        config: Optional[ConfigManager] = None,
        event_bus=None,
    ) -> WeatherService:
        """
        Create WeatherService with real dependencies.

        Args:
            config: Configuration manager (for future use)
            event_bus: Event bus implementation

        Returns:
            Configured WeatherService instance
        """
        return create_weather_service(config=config, event_bus=event_bus)

    @staticmethod
    def create_for_testing(
        mock_repository=None,
        mock_event_bus=None,
    ) -> WeatherService:
        """
        Create service with mock dependencies for testing.

        Args:
            mock_repository: Mock repository (for future DI refactor)
            mock_event_bus: Mock event bus

        Returns:
            WeatherService configured for testing
        """
        return create_weather_service_for_testing(
            mock_repository=mock_repository,
            mock_event_bus=mock_event_bus,
        )
