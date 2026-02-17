"""
Component tests for Auth Service event publishing
TDD approach - test first, then fix
"""
import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from microservices.auth_service.auth_service import AuthenticationService
from tests.component.golden.auth_service.mocks import MockJWTManager, MockEventBus

pytestmark = [pytest.mark.component, pytest.mark.tdd]


class TestAuthServiceEventPublishing:
    """Test that event publishing works correctly"""

    @pytest.mark.asyncio
    async def test_event_publishing_uses_injected_event_bus(self):
        """Test that service uses the injected event bus, not dynamic imports"""
        # Arrange
        jwt_manager = MockJWTManager()
        event_bus = MockEventBus()

        auth_service = AuthenticationService(
            jwt_manager=jwt_manager,
            account_client=None,
            notification_client=None,
            event_bus=event_bus,
            config=None,
        )

        # Act
        result = await auth_service.generate_token_pair(
            user_id="usr_test",
            email="test@example.com",
        )

        # Assert
        assert result["success"] is True

        # Event should be published without import errors
        events = event_bus.get_published_events()
        assert len(events) == 1, "Event should be published successfully"

        # Verify event data - event_type may be in wrapper or in event object
        event_data = events[0]
        event_type = event_data.get("event_type")
        if event_type is None:
            # Check the event object itself
            event_obj = event_data.get("event", {})
            if hasattr(event_obj, 'event_type'):
                event_type = event_obj.event_type
                if hasattr(event_type, 'value'):
                    event_type = event_type.value
            elif isinstance(event_obj, dict):
                event_type = event_obj.get("event_type")
        assert event_type == "user.logged_in", f"Expected user.logged_in, got {event_type}"

    @pytest.mark.asyncio
    async def test_event_publishing_degrades_gracefully_when_no_event_bus(self):
        """Test that service works without event bus"""
        # Arrange
        jwt_manager = MockJWTManager()

        auth_service = AuthenticationService(
            jwt_manager=jwt_manager,
            account_client=None,
            notification_client=None,
            event_bus=None,  # No event bus
            config=None,
        )

        # Act
        result = await auth_service.generate_token_pair(
            user_id="usr_test",
            email="test@example.com",
        )

        # Assert - should succeed without event bus
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
