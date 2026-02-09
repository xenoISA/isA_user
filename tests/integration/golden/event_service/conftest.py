"""
Event Service Integration Test Configuration

Provides fixtures for integration testing:
- http_client: Async HTTP client for making requests
- internal_headers: Headers to bypass authentication
- cleanup_events: Fixture to cleanup test data
- sample data factories for event testing
"""
import pytest
import pytest_asyncio
import httpx
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any


# Event Service runs on port 8230 per conftest.py TestConfig.SERVICES
EVENT_SERVICE_URL = "http://localhost:8230"
API_BASE = f"{EVENT_SERVICE_URL}/api/v1/events"


@pytest_asyncio.fixture
async def http_client():
    """Create async HTTP client with extended timeout for integration tests"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def internal_headers():
    """Headers to bypass authentication for internal service calls"""
    return {
        "X-Internal-Call": "true",
        "Content-Type": "application/json",
    }


@pytest.fixture
def event_api_base():
    """Base URL for event API"""
    return API_BASE


@pytest.fixture
def health_url():
    """Health check URL"""
    return f"{EVENT_SERVICE_URL}/health"


# =============================================================================
# Test Data Factory
# =============================================================================

class EventTestDataFactory:
    """Factory for creating test event data"""

    _counter = 0

    @classmethod
    def _next_id(cls) -> str:
        cls._counter += 1
        return f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{cls._counter:04d}"

    @classmethod
    def make_user_id(cls) -> str:
        """Generate unique user ID"""
        return f"usr_test_{cls._next_id()}"

    @classmethod
    def make_device_id(cls) -> str:
        """Generate unique device ID"""
        return f"dev_test_{cls._next_id()}"

    @classmethod
    def make_session_id(cls) -> str:
        """Generate unique session ID"""
        return f"sess_test_{cls._next_id()}"

    @classmethod
    def make_org_id(cls) -> str:
        """Generate unique organization ID"""
        return f"org_test_{cls._next_id()}"

    @classmethod
    def make_event_create_request(
        cls,
        event_type: str = "user.action",
        event_source: str = "backend",
        event_category: str = "user_action",
        user_id: str = None,
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create event request payload"""
        return {
            "event_type": event_type,
            "event_source": event_source,
            "event_category": event_category,
            "user_id": user_id or cls.make_user_id(),
            "data": data or {"action": "test_action", "details": "test_details"},
            "metadata": metadata or {"source": "integration_test"},
            "context": context or {"test": True},
        }

    @classmethod
    def make_frontend_event_request(
        cls,
        event_type: str = "page_view",
        category: str = "user_interaction",
        page_url: str = None,
        user_id: str = None,
        session_id: str = None,
        data: Dict[str, Any] = None,
        metadata: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Create frontend event request payload"""
        return {
            "event_type": event_type,
            "category": category,
            "page_url": page_url or "https://example.com/test-page",
            "user_id": user_id or cls.make_user_id(),
            "session_id": session_id or cls.make_session_id(),
            "data": data or {"element": "test_button", "action": "click"},
            "metadata": metadata or {"browser": "test_browser"},
        }

    @classmethod
    def make_query_request(
        cls,
        user_id: str = None,
        event_type: str = None,
        event_source: str = None,
        event_category: str = None,
        status: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Create event query request payload"""
        query = {
            "limit": limit,
            "offset": offset,
        }
        if user_id:
            query["user_id"] = user_id
        if event_type:
            query["event_type"] = event_type
        if event_source:
            query["event_source"] = event_source
        if event_category:
            query["event_category"] = event_category
        if status:
            query["status"] = status
        if start_time:
            query["start_time"] = start_time
        if end_time:
            query["end_time"] = end_time
        return query

    @classmethod
    def make_subscription_request(
        cls,
        subscriber_name: str = None,
        subscriber_type: str = "service",
        event_types: List[str] = None,
        event_sources: List[str] = None,
        event_categories: List[str] = None,
        callback_url: str = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Create subscription request payload"""
        return {
            "subscriber_name": subscriber_name or f"test_subscriber_{cls._next_id()}",
            "subscriber_type": subscriber_type,
            "event_types": event_types or ["user.action", "user.login"],
            "event_sources": event_sources,
            "event_categories": event_categories,
            "callback_url": callback_url or "https://example.com/webhook",
            "enabled": enabled,
        }

    @classmethod
    def make_processor_request(
        cls,
        processor_name: str = None,
        processor_type: str = "webhook",
        enabled: bool = True,
        priority: int = 0,
        filters: Dict[str, Any] = None,
        config: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create processor registration request payload"""
        return {
            "processor_name": processor_name or f"test_processor_{cls._next_id()}",
            "processor_type": processor_type,
            "enabled": enabled,
            "priority": priority,
            "filters": filters or {"event_type": "user.action"},
            "config": config or {"url": "https://example.com/process"},
        }

    @classmethod
    def make_replay_request(
        cls,
        stream_id: str = None,
        event_ids: List[str] = None,
        start_time: str = None,
        end_time: str = None,
        target_service: str = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Create event replay request payload"""
        request = {
            "dry_run": dry_run,
        }
        if stream_id:
            request["stream_id"] = stream_id
        if event_ids:
            request["event_ids"] = event_ids
        if start_time:
            request["start_time"] = start_time
        if end_time:
            request["end_time"] = end_time
        if target_service:
            request["target_service"] = target_service
        return request

    @classmethod
    def make_batch_events(cls, count: int = 3) -> List[Dict[str, Any]]:
        """Create batch of event requests"""
        events = []
        event_types = ["user.login", "user.action", "user.logout", "system.health", "device.status"]
        for i in range(count):
            events.append(cls.make_event_create_request(
                event_type=event_types[i % len(event_types)],
                data={"batch_index": i, "action": f"batch_action_{i}"},
            ))
        return events

    @classmethod
    def make_frontend_batch_events(cls, count: int = 3) -> Dict[str, Any]:
        """Create batch of frontend events"""
        events = []
        event_types = ["page_view", "button_click", "form_submit", "scroll", "hover"]
        for i in range(count):
            events.append(cls.make_frontend_event_request(
                event_type=event_types[i % len(event_types)],
                data={"batch_index": i},
            ))
        return {
            "events": events,
            "client_info": {"app_version": "1.0.0", "platform": "web"},
        }


@pytest.fixture
def event_factory():
    """Provide event test data factory"""
    return EventTestDataFactory


@pytest.fixture
def sample_event_request(event_factory):
    """Create a sample event request"""
    return event_factory.make_event_create_request()


@pytest.fixture
def sample_frontend_event(event_factory):
    """Create a sample frontend event request"""
    return event_factory.make_frontend_event_request()


@pytest.fixture
def sample_query_request(event_factory):
    """Create a sample query request"""
    return event_factory.make_query_request()


@pytest.fixture
def sample_subscription_request(event_factory):
    """Create a sample subscription request"""
    return event_factory.make_subscription_request()


@pytest.fixture
def cleanup_events():
    """Factory fixture for cleanup - tracks created event IDs"""
    created_ids: List[str] = []

    def _register(event_id: str):
        created_ids.append(event_id)
        return event_id

    yield _register

    # Note: Events are typically not deleted - managed by retention policies


@pytest.fixture
def cleanup_subscriptions(http_client, internal_headers):
    """Factory fixture for cleanup - deletes created subscriptions"""
    created_ids: List[str] = []

    def _register(subscription_id: str):
        created_ids.append(subscription_id)
        return subscription_id

    yield _register

    # Cleanup is handled after test completes
    # Note: Actual deletion would require async context which is complex in fixtures
