"""
Unit Test Fixtures for Campaign Service

Provides mock fixtures for unit testing.
Uses CampaignTestDataFactory from the data contract.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
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
    BounceType,
    ExecutionType,
    ExecutionStatus,
    MetricType,
    AttributionModel,
    AutoWinnerMetric,
    FrequencyWindow,
    # Models
    Campaign,
    CampaignAudience,
    CampaignChannel,
    CampaignVariant,
    CampaignTrigger,
    TriggerCondition,
    ThrottleConfig,
    ABTestConfig,
    ConversionConfig,
    EmailChannelContent,
    SMSChannelContent,
    InAppChannelContent,
    CampaignExecution,
    CampaignMessage,
    CampaignMetricsSummary,
    CampaignConversion,
    # Factory
    CampaignTestDataFactory,
    CampaignCreateRequestBuilder,
)


# ====================
# Mock Repository
# ====================


class MockCampaignRepository:
    """Mock repository for unit testing"""

    def __init__(self):
        self.campaigns: Dict[str, Campaign] = {}
        self.executions: Dict[str, CampaignExecution] = {}
        self.messages: Dict[str, CampaignMessage] = {}
        self.metrics: Dict[str, CampaignMetricsSummary] = {}
        self.conversions: List[CampaignConversion] = []
        self._counter = 0

    async def initialize(self):
        pass

    async def close(self):
        pass

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
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Campaign], int]:
        results = list(self.campaigns.values())
        if organization_id:
            results = [c for c in results if c.organization_id == organization_id]
        if status:
            results = [c for c in results if c.status in status]
        if campaign_type:
            results = [c for c in results if c.campaign_type == campaign_type]
        total = len(results)
        return results[offset : offset + limit], total

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

    async def save_execution(self, execution: CampaignExecution) -> CampaignExecution:
        self.executions[execution.execution_id] = execution
        return execution

    async def get_execution(self, execution_id: str) -> Optional[CampaignExecution]:
        return self.executions.get(execution_id)

    async def save_message(self, message: CampaignMessage) -> CampaignMessage:
        self.messages[message.message_id] = message
        return message

    async def get_message(self, message_id: str) -> Optional[CampaignMessage]:
        return self.messages.get(message_id)

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

    async def get_metrics_summary(
        self, campaign_id: str
    ) -> Optional[CampaignMetricsSummary]:
        return self.metrics.get(campaign_id)

    async def save_conversion(
        self, conversion: CampaignConversion
    ) -> CampaignConversion:
        self.conversions.append(conversion)
        return conversion

    async def health_check(self) -> bool:
        return True


# ====================
# Mock Event Bus
# ====================


class MockEventBus:
    """Mock event bus for unit testing"""

    def __init__(self):
        self.published_events: List[Dict[str, Any]] = []
        self.is_connected = True

    async def publish_event(self, event) -> bool:
        self.published_events.append(
            {"event_type": event.event_type, "data": event.data}
        )
        return True

    async def subscribe(self, subject: str, handler, durable: str = None) -> None:
        pass

    async def close(self) -> None:
        self.is_connected = False


# ====================
# Fixtures
# ====================


@pytest.fixture
def factory():
    """Provide CampaignTestDataFactory"""
    return CampaignTestDataFactory


@pytest.fixture
def mock_repository():
    """Create mock repository"""
    return MockCampaignRepository()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest.fixture
def sample_campaign(factory):
    """Create sample draft campaign"""
    return factory.make_campaign(
        campaign_type=CampaignType.SCHEDULED, status=CampaignStatus.DRAFT
    )


@pytest.fixture
def scheduled_campaign(factory):
    """Create scheduled campaign"""
    campaign = factory.make_scheduled_campaign()
    campaign.status = CampaignStatus.SCHEDULED
    return campaign


@pytest.fixture
def triggered_campaign(factory):
    """Create triggered campaign"""
    campaign = factory.make_triggered_campaign()
    campaign.status = CampaignStatus.ACTIVE
    return campaign


@pytest.fixture
def ab_test_campaign(factory):
    """Create A/B test campaign"""
    return factory.make_ab_test_campaign(num_variants=2)


@pytest.fixture
def sample_execution(factory, sample_campaign):
    """Create sample execution"""
    return factory.make_execution(
        campaign_id=sample_campaign.campaign_id, status=ExecutionStatus.PENDING
    )


@pytest.fixture
def sample_message(factory, sample_campaign, sample_execution):
    """Create sample message"""
    return factory.make_message(
        campaign_id=sample_campaign.campaign_id,
        execution_id=sample_execution.execution_id,
        channel_type=ChannelType.EMAIL,
        status=MessageStatus.QUEUED,
    )


@pytest.fixture
def sample_metrics(factory, sample_campaign):
    """Create sample metrics summary"""
    return factory.make_metrics_summary(
        campaign_id=sample_campaign.campaign_id, sent=10000
    )


@pytest.fixture
def sample_variants(factory):
    """Create sample A/B test variants"""
    return [
        factory.make_variant(name="Variant A", allocation=Decimal("50")),
        factory.make_variant(name="Variant B", allocation=Decimal("50")),
    ]


@pytest.fixture
def sample_audience(factory):
    """Create sample audience"""
    return factory.make_audience(segment_type=SegmentType.INCLUDE)


@pytest.fixture
def sample_trigger(factory):
    """Create sample trigger"""
    return factory.make_trigger(event_type="user.action")


@pytest.fixture
def sample_channel(factory):
    """Create sample email channel"""
    return factory.make_channel(channel_type=ChannelType.EMAIL)
