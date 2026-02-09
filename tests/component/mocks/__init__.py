"""
Component Test Mocks

Shared mock implementations for component testing.
These mocks replace real I/O dependencies (database, NATS, HTTP).
"""

from .db_mock import MockAsyncPostgresClient
from .nats_mock import MockEventBus
from .http_mock import MockHttpClient

# Service-specific mocks should be in tests/component/{golden,tdd}/{service}/mocks.py
# Import auth mocks here for backwards compatibility
try:
    from .auth_mocks import MockJWTManager, MockAccountClient, MockNotificationClient
    from .auth_mocks import MockEventBus as AuthMockEventBus
except ImportError:
    pass

__all__ = [
    'MockAsyncPostgresClient',
    'MockEventBus',
    'MockHttpClient',
]
