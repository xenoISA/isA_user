"""
Account Service Integration Test Configuration

Overrides the global event_collector to only subscribe to user.* events
for faster and more reliable testing.
"""
import pytest
import pytest_asyncio
import asyncio
import uuid
from typing import AsyncGenerator

from tests.integration.conftest import EventCollector


@pytest_asyncio.fixture(scope="function")
async def event_collector(event_bus) -> AsyncGenerator[EventCollector, None]:
    """
    Account-specific event collector - only subscribes to user.* events.

    This is faster and more reliable than the global collector which
    subscribes to 15+ event patterns.
    """
    collector = EventCollector()
    test_id = uuid.uuid4().hex[:8]

    if event_bus:
        # Only subscribe to user.* events for account service tests
        try:
            durable_name = f"user-test-{test_id}"
            await event_bus.subscribe_to_events(
                pattern="user.*",
                handler=collector.collect,
                durable=durable_name,
                delivery_policy='new'
            )
        except Exception as e:
            pass

        # Wait for subscription to be ready
        await asyncio.sleep(1.0)

    yield collector

    collector.clear()
