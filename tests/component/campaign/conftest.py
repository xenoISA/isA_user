"""
Component Test Fixtures for Campaign Service

Provides fixtures for component testing with mocked dependencies.
Uses FastAPI TestClient for API testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    # Enums
    CampaignType,
    CampaignStatus,
    ScheduleType,
    ChannelType,
    SegmentType,
    TriggerOperator,
    MessageStatus,
    ExecutionType,
    ExecutionStatus,
    MetricType,
    AttributionModel,
    # Models
    Campaign,
    CampaignAudience,
    CampaignChannel,
    CampaignVariant,
    CampaignTrigger,
    ThrottleConfig,
    ABTestConfig,
    ConversionConfig,
    CampaignExecution,
    CampaignMessage,
    CampaignMetricsSummary,
    # Factory
    CampaignTestDataFactory,
)


# ====================
# Mock Repository
# ====================


class MockCampaignRepository:
    """Mock repository for component testing"""

    def __init__(self):
        self.campaigns: Dict[str, Campaign] = {}
        self.audiences: Dict[str, List[CampaignAudience]] = {}
        self.variants: Dict[str, List[CampaignVariant]] = {}
        self.channels: Dict[str, List[CampaignChannel]] = {}
        self.triggers: Dict[str, List[CampaignTrigger]] = {}
        self.executions: Dict[str, CampaignExecution] = {}
        self.messages: Dict[str, CampaignMessage] = {}
        self.metrics: Dict[str, CampaignMetricsSummary] = {}
        self._counter = 0
        self.db = MagicMock()
        self.db.health_check = MagicMock(return_value=True)

    async def initialize(self):
        pass

    async def close(self):
        pass

    async def health_check(self) -> bool:
        return True

    # Campaign CRUD
    async def save_campaign(self, campaign: Campaign) -> Campaign:
        self.campaigns[campaign.campaign_id] = campaign
        return campaign

    async def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        return self.campaigns.get(campaign_id)

    async def get_campaign_by_org(
        self, organization_id: str, campaign_id: str
    ) -> Optional[Campaign]:
        campaign = self.campaigns.get(campaign_id)
        if campaign and campaign.organization_id == organization_id:
            return campaign
        return None

    async def list_campaigns(
        self,
        organization_id: Optional[str] = None,
        status: Optional[List[CampaignStatus]] = None,
        campaign_type: Optional[CampaignType] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple:
        results = list(self.campaigns.values())

        # Filter deleted
        results = [c for c in results if c.deleted_at is None]

        if organization_id:
            results = [c for c in results if c.organization_id == organization_id]
        if status:
            results = [c for c in results if c.status in status]
        if campaign_type:
            results = [c for c in results if c.campaign_type == campaign_type]
        if search:
            results = [c for c in results if search.lower() in c.name.lower()]

        # Sort
        reverse = sort_order == "desc"
        if sort_by == "created_at":
            results.sort(key=lambda x: x.created_at or datetime.min, reverse=reverse)
        elif sort_by == "name":
            results.sort(key=lambda x: x.name, reverse=reverse)

        total = len(results)
        return results[offset : offset + limit], total

    async def update_campaign(self, campaign_id: str, updates: dict) -> Optional[Campaign]:
        campaign = self.campaigns.get(campaign_id)
        if campaign:
            for key, value in updates.items():
                if hasattr(campaign, key):
                    setattr(campaign, key, value)
            campaign.updated_at = datetime.now(timezone.utc)
        return campaign

    async def update_campaign_status(
        self, campaign_id: str, status: CampaignStatus, **kwargs
    ) -> Optional[Campaign]:
        campaign = self.campaigns.get(campaign_id)
        if campaign:
            campaign.status = status
            campaign.updated_at = datetime.now(timezone.utc)
            for key, value in kwargs.items():
                if hasattr(campaign, key):
                    setattr(campaign, key, value)
        return campaign

    async def delete_campaign(self, campaign_id: str) -> bool:
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id].deleted_at = datetime.now(timezone.utc)
            return True
        return False

    # Audience operations
    async def save_audiences(
        self, campaign_id: str, audiences: List[CampaignAudience]
    ) -> List[CampaignAudience]:
        self.audiences[campaign_id] = audiences
        return audiences

    async def get_audiences(self, campaign_id: str) -> List[CampaignAudience]:
        return self.audiences.get(campaign_id, [])

    # Variant operations
    async def save_variant(
        self, campaign_id: str, variant: CampaignVariant
    ) -> CampaignVariant:
        if campaign_id not in self.variants:
            self.variants[campaign_id] = []
        self.variants[campaign_id].append(variant)
        return variant

    async def get_variants(self, campaign_id: str) -> List[CampaignVariant]:
        return self.variants.get(campaign_id, [])

    async def update_variant(
        self, campaign_id: str, variant_id: str, updates: dict
    ) -> Optional[CampaignVariant]:
        variants = self.variants.get(campaign_id, [])
        for v in variants:
            if v.variant_id == variant_id:
                for key, value in updates.items():
                    if hasattr(v, key):
                        setattr(v, key, value)
                return v
        return None

    async def delete_variant(self, campaign_id: str, variant_id: str) -> bool:
        variants = self.variants.get(campaign_id, [])
        for i, v in enumerate(variants):
            if v.variant_id == variant_id:
                variants.pop(i)
                return True
        return False

    # Channel operations
    async def save_channels(
        self, campaign_id: str, channels: List[CampaignChannel]
    ) -> List[CampaignChannel]:
        self.channels[campaign_id] = channels
        return channels

    async def get_channels(self, campaign_id: str) -> List[CampaignChannel]:
        return self.channels.get(campaign_id, [])

    # Trigger operations
    async def save_triggers(
        self, campaign_id: str, triggers: List[CampaignTrigger]
    ) -> List[CampaignTrigger]:
        self.triggers[campaign_id] = triggers
        return triggers

    async def get_triggers(self, campaign_id: str) -> List[CampaignTrigger]:
        return self.triggers.get(campaign_id, [])

    # Execution operations
    async def save_execution(self, execution: CampaignExecution) -> CampaignExecution:
        self.executions[execution.execution_id] = execution
        return execution

    async def get_execution(self, execution_id: str) -> Optional[CampaignExecution]:
        return self.executions.get(execution_id)

    async def list_executions(
        self, campaign_id: str, limit: int = 20, offset: int = 0
    ) -> tuple:
        results = [e for e in self.executions.values() if e.campaign_id == campaign_id]
        results.sort(key=lambda x: x.started_at or datetime.min, reverse=True)
        return results[offset : offset + limit], len(results)

    async def update_execution_status(
        self, execution_id: str, status: ExecutionStatus, **kwargs
    ) -> Optional[CampaignExecution]:
        execution = self.executions.get(execution_id)
        if execution:
            execution.status = status
            for key, value in kwargs.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)
        return execution

    # Message operations
    async def save_message(self, message: CampaignMessage) -> CampaignMessage:
        self.messages[message.message_id] = message
        return message

    async def get_message(self, message_id: str) -> Optional[CampaignMessage]:
        return self.messages.get(message_id)

    async def list_messages(
        self,
        campaign_id: str,
        execution_id: Optional[str] = None,
        status: Optional[MessageStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple:
        results = [m for m in self.messages.values() if m.campaign_id == campaign_id]
        if execution_id:
            results = [m for m in results if m.execution_id == execution_id]
        if status:
            results = [m for m in results if m.status == status]
        return results[offset : offset + limit], len(results)

    async def update_message_status(
        self, message_id: str, status: MessageStatus, **kwargs
    ) -> Optional[CampaignMessage]:
        message = self.messages.get(message_id)
        if message:
            message.status = status
            for key, value in kwargs.items():
                if hasattr(message, key):
                    setattr(message, key, value)
        return message

    # Metrics operations
    async def get_metrics_summary(
        self, campaign_id: str
    ) -> Optional[CampaignMetricsSummary]:
        return self.metrics.get(campaign_id)

    async def save_metrics_summary(
        self, metrics: CampaignMetricsSummary
    ) -> CampaignMetricsSummary:
        self.metrics[metrics.campaign_id] = metrics
        return metrics


# ====================
# Mock Event Bus
# ====================


class MockEventBus:
    """Mock event bus for component testing"""

    def __init__(self):
        self.published_events: List[Dict[str, Any]] = []
        self.subscriptions: Dict[str, Any] = {}
        self.is_connected = True

    async def publish_event(self, event) -> bool:
        self.published_events.append(
            {
                "event_type": event.event_type,
                "source": event.source,
                "data": event.data,
            }
        )
        return True

    async def subscribe(self, subject: str, handler, durable: str = None) -> None:
        self.subscriptions[subject] = handler

    async def close(self) -> None:
        self.is_connected = False

    def get_events_by_type(self, event_type: str) -> List[Dict]:
        return [e for e in self.published_events if e["event_type"] == event_type]

    def clear_events(self):
        self.published_events = []


# ====================
# Mock External Clients
# ====================


class MockTaskClient:
    """Mock task service client"""

    def __init__(self):
        self.created_tasks: List[Dict] = []
        self.cancelled_tasks: List[str] = []

    async def create_task(self, **kwargs) -> Dict:
        task_id = f"task_{len(self.created_tasks) + 1}"
        task = {"task_id": task_id, **kwargs}
        self.created_tasks.append(task)
        return task

    async def cancel_task(self, task_id: str) -> bool:
        self.cancelled_tasks.append(task_id)
        return True


class MockNotificationClient:
    """Mock notification service client"""

    def __init__(self):
        self.sent_notifications: List[Dict] = []

    async def send_notification(self, **kwargs) -> Dict:
        notification_id = f"notif_{len(self.sent_notifications) + 1}"
        notification = {"notification_id": notification_id, **kwargs}
        self.sent_notifications.append(notification)
        return notification


class MockIsADataClient:
    """Mock isA_Data client for segment resolution"""

    def __init__(self):
        self.segment_data: Dict[str, List[str]] = {}
        self.user_data: Dict[str, Dict] = {}

    async def get_segment_users(self, segment_id: str) -> List[str]:
        return self.segment_data.get(segment_id, [])

    async def get_user_360(self, user_id: str) -> Dict:
        return self.user_data.get(user_id, {})

    def set_segment_users(self, segment_id: str, user_ids: List[str]):
        self.segment_data[segment_id] = user_ids


# ====================
# Global repository instance for FastAPI mocking
# ====================

_mock_repository = None
_mock_event_bus = None


def get_mock_repository():
    global _mock_repository
    if _mock_repository is None:
        _mock_repository = MockCampaignRepository()
    return _mock_repository


def reset_mock_repository():
    global _mock_repository
    _mock_repository = MockCampaignRepository()
    return _mock_repository


def get_mock_event_bus():
    global _mock_event_bus
    if _mock_event_bus is None:
        _mock_event_bus = MockEventBus()
    return _mock_event_bus


def reset_mock_event_bus():
    global _mock_event_bus
    _mock_event_bus = MockEventBus()
    return _mock_event_bus


# ====================
# Fixtures
# ====================


@pytest.fixture
def factory():
    """Provide CampaignTestDataFactory"""
    return CampaignTestDataFactory


@pytest.fixture
def mock_repository():
    """Get fresh mock repository for each test"""
    return reset_mock_repository()


@pytest.fixture
def mock_event_bus():
    """Get fresh mock event bus for each test"""
    return reset_mock_event_bus()


@pytest.fixture
def mock_task_client():
    """Create mock task service client"""
    return MockTaskClient()


@pytest.fixture
def mock_notification_client():
    """Create mock notification service client"""
    return MockNotificationClient()


@pytest.fixture
def mock_isa_data_client():
    """Create mock isA_Data client"""
    return MockIsADataClient()


@pytest.fixture
async def sample_campaign(mock_repository, factory):
    """Create and save a sample campaign"""
    campaign = factory.make_campaign(
        campaign_type=CampaignType.SCHEDULED, status=CampaignStatus.DRAFT
    )
    await mock_repository.save_campaign(campaign)
    return campaign


@pytest.fixture
async def scheduled_campaign(mock_repository, factory):
    """Create and save a scheduled campaign"""
    campaign = factory.make_scheduled_campaign()
    campaign.status = CampaignStatus.SCHEDULED
    campaign.task_id = "task_schedule_123"
    await mock_repository.save_campaign(campaign)
    return campaign


@pytest.fixture
async def running_campaign(mock_repository, factory):
    """Create and save a running campaign"""
    campaign = factory.make_campaign(
        campaign_type=CampaignType.SCHEDULED, status=CampaignStatus.RUNNING
    )
    await mock_repository.save_campaign(campaign)
    return campaign


@pytest.fixture
async def triggered_campaign(mock_repository, factory):
    """Create and save a triggered campaign"""
    campaign = factory.make_triggered_campaign()
    campaign.status = CampaignStatus.ACTIVE
    await mock_repository.save_campaign(campaign)
    return campaign


@pytest.fixture
async def ab_test_campaign(mock_repository, factory):
    """Create and save an A/B test campaign"""
    campaign = factory.make_ab_test_campaign(num_variants=2)
    await mock_repository.save_campaign(campaign)
    return campaign


@pytest.fixture
async def sample_execution(mock_repository, factory, sample_campaign):
    """Create and save a sample execution"""
    execution = factory.make_execution(
        campaign_id=sample_campaign.campaign_id, status=ExecutionStatus.PENDING
    )
    await mock_repository.save_execution(execution)
    return execution


@pytest.fixture
async def sample_messages(mock_repository, factory, sample_campaign, sample_execution):
    """Create and save sample messages"""
    messages = []
    for i in range(5):
        message = factory.make_message(
            campaign_id=sample_campaign.campaign_id,
            execution_id=sample_execution.execution_id,
            user_id=f"usr_test_{i}",
            channel_type=ChannelType.EMAIL,
            status=MessageStatus.QUEUED,
        )
        await mock_repository.save_message(message)
        messages.append(message)
    return messages
