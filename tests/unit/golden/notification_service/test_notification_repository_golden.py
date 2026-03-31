"""
Unit Golden Tests: Notification Repository Claim Semantics

Tests notification claiming behavior with mocked database client.
Focus: atomic claim queries for replica-safe processing.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from microservices.notification_service.models import NotificationStatus
from microservices.notification_service.notification_repository import (
    NotificationRepository,
)


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager"""
    config = MagicMock()
    config.discover_service.return_value = ("localhost", 5432)
    return config


@pytest.fixture
def mock_db_client():
    """Create a mock PostgresClient"""
    client = AsyncMock()
    client.query = AsyncMock(return_value=[])
    client.execute = AsyncMock(return_value=1)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def notification_repository(mock_config_manager, mock_db_client):
    """Create NotificationRepository with mocked dependencies"""
    with patch(
        "microservices.notification_service.notification_repository.AsyncPostgresClient"
    ) as mock_client:
        mock_client.return_value = mock_db_client
        repo = NotificationRepository(config=mock_config_manager)
        repo.db = mock_db_client
    return repo


@pytest.fixture
def sample_notification_row():
    """Create a sample database row"""
    now = datetime.utcnow().isoformat()
    return {
        "notification_id": "ntf_123",
        "type": "email",
        "priority": "normal",
        "user_id": "user_123",
        "recipient": "user@example.com",
        "content": "hello",
        "variables": {},
        "metadata": {},
        "retry_count": 0,
        "max_retries": 3,
        "status": "sending",
        "error_message": None,
        "provider": None,
        "provider_message_id": None,
        "scheduled_at": None,
        "created_at": now,
        "sent_at": None,
        "delivered_at": None,
        "read_at": None,
    }


class TestNotificationClaiming:
    """Test claim behavior used by background workers"""

    @pytest.mark.asyncio
    async def test_claim_notification_updates_only_pending_rows(
        self,
        notification_repository,
        mock_db_client,
    ):
        """Test direct claims transition pending notifications to sending"""
        claimed = await notification_repository.claim_notification("ntf_123")

        query, params = mock_db_client.execute.await_args.args[:2]
        assert claimed is True
        assert "SET status = $1" in query
        assert "WHERE notification_id = $2" in query
        assert "AND status = $3" in query
        assert params == [
            NotificationStatus.SENDING.value,
            "ntf_123",
            NotificationStatus.PENDING.value,
        ]

    @pytest.mark.asyncio
    async def test_get_pending_notifications_claims_rows_before_returning(
        self,
        notification_repository,
        mock_db_client,
        sample_notification_row,
    ):
        """Test background polling atomically claims rows before processing"""
        mock_db_client.query.return_value = [sample_notification_row]

        notifications = await notification_repository.get_pending_notifications(limit=25)

        query, params = mock_db_client.query.await_args.args[:2]
        assert "FOR UPDATE SKIP LOCKED" in query
        assert "RETURNING notifications.*" in query
        assert params[0] == NotificationStatus.PENDING.value
        assert params[2] == NotificationStatus.SENDING.value
        assert isinstance(params[1], datetime)
        assert len(notifications) == 1
        assert notifications[0].notification_id == sample_notification_row["notification_id"]
        assert notifications[0].status == NotificationStatus.SENDING
