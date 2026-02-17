"""
Unit Tests for Campaign Pydantic Models

Tests all model validation rules from data_contract.py.
Reference: BR-CAM-001.1 (Create Campaign validation rules)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import ValidationError

import sys
import os

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
    WhatsAppChannelContent,
    InAppChannelContent,
    WebhookChannelContent,
    CampaignExecution,
    CampaignMessage,
    CampaignMetricRecord,
    CampaignMetricsSummary,
    CampaignConversion,
    CampaignUnsubscribe,
    TriggerHistoryRecord,
    # Request/Response Models
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignResponse,
    CampaignListResponse,
    CampaignQueryRequest,
    # Factory
    CampaignTestDataFactory,
)


# ====================
# Campaign Enum Tests
# ====================


class TestCampaignTypeEnum:
    """Tests for CampaignType enum"""

    def test_scheduled_type(self):
        """Test scheduled campaign type value"""
        assert CampaignType.SCHEDULED.value == "scheduled"

    def test_triggered_type(self):
        """Test triggered campaign type value"""
        assert CampaignType.TRIGGERED.value == "triggered"

    def test_type_from_string(self):
        """Test enum creation from string"""
        assert CampaignType("scheduled") == CampaignType.SCHEDULED
        assert CampaignType("triggered") == CampaignType.TRIGGERED

    def test_invalid_type_raises_error(self):
        """Test invalid type raises ValueError"""
        with pytest.raises(ValueError):
            CampaignType("invalid_type")


class TestCampaignStatusEnum:
    """Tests for CampaignStatus enum - BR-CAM-001 states"""

    def test_draft_status(self):
        """Test draft status value"""
        assert CampaignStatus.DRAFT.value == "draft"

    def test_scheduled_status(self):
        """Test scheduled status value"""
        assert CampaignStatus.SCHEDULED.value == "scheduled"

    def test_active_status(self):
        """Test active status value (for triggered campaigns)"""
        assert CampaignStatus.ACTIVE.value == "active"

    def test_running_status(self):
        """Test running status value"""
        assert CampaignStatus.RUNNING.value == "running"

    def test_paused_status(self):
        """Test paused status value"""
        assert CampaignStatus.PAUSED.value == "paused"

    def test_completed_status(self):
        """Test completed status value (terminal)"""
        assert CampaignStatus.COMPLETED.value == "completed"

    def test_cancelled_status(self):
        """Test cancelled status value (terminal)"""
        assert CampaignStatus.CANCELLED.value == "cancelled"

    def test_status_from_string(self):
        """Test enum creation from string"""
        assert CampaignStatus("draft") == CampaignStatus.DRAFT

    def test_invalid_status_raises_error(self):
        """Test invalid status raises ValueError"""
        with pytest.raises(ValueError):
            CampaignStatus("invalid_status")


class TestChannelTypeEnum:
    """Tests for ChannelType enum - BR-CAM-003"""

    def test_email_channel(self):
        """Test email channel value"""
        assert ChannelType.EMAIL.value == "email"

    def test_sms_channel(self):
        """Test SMS channel value"""
        assert ChannelType.SMS.value == "sms"

    def test_whatsapp_channel(self):
        """Test WhatsApp channel value"""
        assert ChannelType.WHATSAPP.value == "whatsapp"

    def test_in_app_channel(self):
        """Test in-app channel value"""
        assert ChannelType.IN_APP.value == "in_app"

    def test_webhook_channel(self):
        """Test webhook channel value"""
        assert ChannelType.WEBHOOK.value == "webhook"


class TestMessageStatusEnum:
    """Tests for MessageStatus enum - BR-CAM-005.1"""

    def test_queued_status(self):
        """Test queued status"""
        assert MessageStatus.QUEUED.value == "queued"

    def test_sent_status(self):
        """Test sent status"""
        assert MessageStatus.SENT.value == "sent"

    def test_delivered_status(self):
        """Test delivered status"""
        assert MessageStatus.DELIVERED.value == "delivered"

    def test_opened_status(self):
        """Test opened status"""
        assert MessageStatus.OPENED.value == "opened"

    def test_clicked_status(self):
        """Test clicked status"""
        assert MessageStatus.CLICKED.value == "clicked"

    def test_bounced_status(self):
        """Test bounced status"""
        assert MessageStatus.BOUNCED.value == "bounced"

    def test_failed_status(self):
        """Test failed status"""
        assert MessageStatus.FAILED.value == "failed"

    def test_unsubscribed_status(self):
        """Test unsubscribed status"""
        assert MessageStatus.UNSUBSCRIBED.value == "unsubscribed"


class TestExecutionStatusEnum:
    """Tests for ExecutionStatus enum"""

    def test_pending_status(self):
        """Test pending execution status"""
        assert ExecutionStatus.PENDING.value == "pending"

    def test_running_status(self):
        """Test running execution status"""
        assert ExecutionStatus.RUNNING.value == "running"

    def test_paused_status(self):
        """Test paused execution status"""
        assert ExecutionStatus.PAUSED.value == "paused"

    def test_completed_status(self):
        """Test completed execution status"""
        assert ExecutionStatus.COMPLETED.value == "completed"

    def test_failed_status(self):
        """Test failed execution status"""
        assert ExecutionStatus.FAILED.value == "failed"

    def test_cancelled_status(self):
        """Test cancelled execution status"""
        assert ExecutionStatus.CANCELLED.value == "cancelled"


class TestTriggerOperatorEnum:
    """Tests for TriggerOperator enum - BR-CAM-007.1"""

    def test_equals_operator(self):
        """Test equals operator"""
        assert TriggerOperator.EQUALS.value == "equals"

    def test_not_equals_operator(self):
        """Test not equals operator"""
        assert TriggerOperator.NOT_EQUALS.value == "not_equals"

    def test_contains_operator(self):
        """Test contains operator"""
        assert TriggerOperator.CONTAINS.value == "contains"

    def test_greater_than_operator(self):
        """Test greater than operator"""
        assert TriggerOperator.GREATER_THAN.value == "greater_than"

    def test_less_than_operator(self):
        """Test less than operator"""
        assert TriggerOperator.LESS_THAN.value == "less_than"

    def test_in_operator(self):
        """Test in operator"""
        assert TriggerOperator.IN.value == "in"

    def test_exists_operator(self):
        """Test exists operator"""
        assert TriggerOperator.EXISTS.value == "exists"


class TestAttributionModelEnum:
    """Tests for AttributionModel enum - BR-CAM-005.3"""

    def test_first_touch(self):
        """Test first touch attribution"""
        assert AttributionModel.FIRST_TOUCH.value == "first_touch"

    def test_last_touch(self):
        """Test last touch attribution"""
        assert AttributionModel.LAST_TOUCH.value == "last_touch"

    def test_linear(self):
        """Test linear attribution"""
        assert AttributionModel.LINEAR.value == "linear"


# ====================
# Core Model Tests
# ====================


class TestCampaignModel:
    """Tests for Campaign model - BR-CAM-001.1"""

    def test_create_campaign_minimal(self, factory):
        """Test creating campaign with minimal required fields"""
        campaign = Campaign(
            campaign_id="cmp_test123",
            organization_id="org_123",
            name="Test Campaign",
            campaign_type=CampaignType.SCHEDULED,
            created_by="usr_admin",
        )
        assert campaign.campaign_id == "cmp_test123"
        assert campaign.name == "Test Campaign"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.holdout_percentage == Decimal("0")

    def test_create_campaign_full(self, factory):
        """Test creating campaign with all fields"""
        campaign = factory.make_campaign()
        assert campaign.campaign_id is not None
        assert campaign.organization_id is not None
        assert campaign.campaign_type in [
            CampaignType.SCHEDULED,
            CampaignType.TRIGGERED,
        ]
        assert campaign.created_by is not None

    def test_campaign_name_required(self):
        """Test that campaign name is required - BR-CAM-001.1"""
        with pytest.raises(ValidationError) as exc_info:
            Campaign(
                campaign_id="cmp_test",
                organization_id="org_123",
                campaign_type=CampaignType.SCHEDULED,
                created_by="usr_admin",
            )
        assert "name" in str(exc_info.value).lower()

    def test_campaign_name_min_length(self):
        """Test campaign name minimum length - BR-CAM-001.1"""
        with pytest.raises(ValidationError):
            Campaign(
                campaign_id="cmp_test",
                organization_id="org_123",
                name="",  # Empty name
                campaign_type=CampaignType.SCHEDULED,
                created_by="usr_admin",
            )

    def test_campaign_name_max_length(self):
        """Test campaign name maximum length (255 chars) - BR-CAM-001.1"""
        with pytest.raises(ValidationError):
            Campaign(
                campaign_id="cmp_test",
                organization_id="org_123",
                name="x" * 256,  # Exceeds 255
                campaign_type=CampaignType.SCHEDULED,
                created_by="usr_admin",
            )

    def test_campaign_description_max_length(self):
        """Test campaign description max length (2000 chars) - BR-CAM-001.1"""
        with pytest.raises(ValidationError):
            Campaign(
                campaign_id="cmp_test",
                organization_id="org_123",
                name="Test Campaign",
                description="x" * 2001,  # Exceeds 2000
                campaign_type=CampaignType.SCHEDULED,
                created_by="usr_admin",
            )

    def test_campaign_holdout_percentage_max(self):
        """Test holdout percentage max is 20% - BR-CAM-001.1"""
        with pytest.raises(ValidationError):
            Campaign(
                campaign_id="cmp_test",
                organization_id="org_123",
                name="Test Campaign",
                campaign_type=CampaignType.SCHEDULED,
                created_by="usr_admin",
                holdout_percentage=Decimal("21"),  # Exceeds 20%
            )

    def test_campaign_holdout_percentage_valid(self):
        """Test valid holdout percentage"""
        campaign = Campaign(
            campaign_id="cmp_test",
            organization_id="org_123",
            name="Test Campaign",
            campaign_type=CampaignType.SCHEDULED,
            created_by="usr_admin",
            holdout_percentage=Decimal("5"),
        )
        assert campaign.holdout_percentage == Decimal("5")

    def test_campaign_default_status_is_draft(self):
        """Test default campaign status is draft"""
        campaign = Campaign(
            campaign_id="cmp_test",
            organization_id="org_123",
            name="Test Campaign",
            campaign_type=CampaignType.SCHEDULED,
            created_by="usr_admin",
        )
        assert campaign.status == CampaignStatus.DRAFT

    def test_campaign_id_format(self, factory):
        """Test campaign ID format (cmp_{uuid16})"""
        campaign_id = factory.make_campaign_id()
        assert campaign_id.startswith("cmp_")
        assert len(campaign_id) == 20  # cmp_ + 16 chars


class TestCampaignAudienceModel:
    """Tests for CampaignAudience model - BR-CAM-002"""

    def test_create_include_audience(self, factory):
        """Test creating include audience segment"""
        audience = factory.make_audience(segment_type=SegmentType.INCLUDE)
        assert audience.segment_type == SegmentType.INCLUDE
        assert audience.segment_id is not None

    def test_create_exclude_audience(self, factory):
        """Test creating exclude audience segment"""
        audience = factory.make_audience(segment_type=SegmentType.EXCLUDE)
        assert audience.segment_type == SegmentType.EXCLUDE

    def test_audience_requires_segment_source(self):
        """Test audience requires segment_id or segment_query - BR-CAM-002"""
        with pytest.raises(ValidationError) as exc_info:
            CampaignAudience(
                audience_id="aud_test",
                segment_type=SegmentType.INCLUDE,
                # Neither segment_id nor segment_query provided
            )
        assert "segment" in str(exc_info.value).lower()

    def test_audience_with_segment_id(self):
        """Test audience with segment_id"""
        audience = CampaignAudience(
            audience_id="aud_test",
            segment_type=SegmentType.INCLUDE,
            segment_id="seg_premium_users",
        )
        assert audience.segment_id == "seg_premium_users"

    def test_audience_with_segment_query(self):
        """Test audience with inline segment_query"""
        audience = CampaignAudience(
            audience_id="aud_test",
            segment_type=SegmentType.INCLUDE,
            segment_query={"field": "subscription_plan", "operator": "equals", "value": "premium"},
        )
        assert audience.segment_query is not None


class TestCampaignChannelModel:
    """Tests for CampaignChannel model - BR-CAM-003"""

    def test_create_email_channel(self, factory):
        """Test creating email channel"""
        channel = factory.make_channel(channel_type=ChannelType.EMAIL)
        assert channel.channel_type == ChannelType.EMAIL
        assert channel.email_content is not None

    def test_email_channel_requires_subject(self):
        """Test email channel requires subject - BR-CAM-003.1"""
        with pytest.raises(ValidationError):
            EmailChannelContent(
                body_html="<p>Hello</p>",
                # Missing subject
            )

    def test_sms_content_max_160_chars(self):
        """Test SMS content max 160 characters - BR-CAM-003.1"""
        with pytest.raises(ValidationError):
            SMSChannelContent(body="x" * 161)

    def test_sms_content_valid(self):
        """Test valid SMS content"""
        content = SMSChannelContent(body="Hello {{first_name}}!")
        assert len(content.body) <= 160

    def test_whatsapp_content_max_1600_chars(self):
        """Test WhatsApp content max 1600 characters - BR-CAM-003.1"""
        with pytest.raises(ValidationError):
            WhatsAppChannelContent(body="x" * 1601)

    def test_channel_requires_content_or_template(self):
        """Test channel requires content or template_id - BR-CAM-003.1"""
        with pytest.raises(ValidationError):
            CampaignChannel(
                channel_id="chn_test",
                channel_type=ChannelType.EMAIL,
                # Neither email_content nor template_id provided
            )

    def test_channel_with_template_id(self):
        """Test channel with template_id instead of content"""
        channel = CampaignChannel(
            channel_id="chn_test",
            channel_type=ChannelType.EMAIL,
            template_id="tpl_welcome_email",
        )
        assert channel.template_id == "tpl_welcome_email"

    def test_channel_priority(self):
        """Test channel priority for fallback - BR-CAM-003.3"""
        channel = CampaignChannel(
            channel_id="chn_test",
            channel_type=ChannelType.EMAIL,
            template_id="tpl_test",
            priority=1,
        )
        assert channel.priority == 1


class TestCampaignVariantModel:
    """Tests for CampaignVariant model - BR-CAM-004"""

    def test_create_variant(self, factory):
        """Test creating variant"""
        variant = factory.make_variant(name="Variant A", allocation=Decimal("50"))
        assert variant.name == "Variant A"
        assert variant.allocation_percentage == Decimal("50")

    def test_variant_allocation_range(self):
        """Test variant allocation must be 0-100 - BR-CAM-004.1"""
        with pytest.raises(ValidationError):
            CampaignVariant(
                variant_id="var_test",
                name="Test Variant",
                allocation_percentage=Decimal("101"),
            )

    def test_control_variant(self):
        """Test control variant (no message sent) - BR-CAM-004.1"""
        variant = CampaignVariant(
            variant_id="var_control",
            name="Control",
            allocation_percentage=Decimal("10"),
            is_control=True,
        )
        assert variant.is_control is True


class TestCampaignTriggerModel:
    """Tests for CampaignTrigger model - BR-CAM-007"""

    def test_create_trigger(self, factory):
        """Test creating trigger"""
        trigger = factory.make_trigger(event_type="user.purchase")
        assert trigger.event_type == "user.purchase"

    def test_trigger_delay_max_30_days(self):
        """Test trigger delay max 30 days - BR-CAM-007.2"""
        with pytest.raises(ValidationError):
            CampaignTrigger(
                trigger_id="trg_test",
                event_type="user.action",
                delay_days=31,  # Exceeds 30
            )

    def test_trigger_frequency_limit(self):
        """Test trigger frequency limit - BR-CAM-007.3"""
        trigger = CampaignTrigger(
            trigger_id="trg_test",
            event_type="user.action",
            frequency_limit=1,
            frequency_window_hours=24,
        )
        assert trigger.frequency_limit == 1
        assert trigger.frequency_window_hours == 24

    def test_trigger_quiet_hours(self):
        """Test trigger quiet hours - BR-CAM-006.3"""
        trigger = CampaignTrigger(
            trigger_id="trg_test",
            event_type="user.action",
            quiet_hours_start=21,
            quiet_hours_end=8,
        )
        assert trigger.quiet_hours_start == 21
        assert trigger.quiet_hours_end == 8

    def test_trigger_quiet_hours_valid_range(self):
        """Test quiet hours must be 0-23"""
        with pytest.raises(ValidationError):
            CampaignTrigger(
                trigger_id="trg_test",
                event_type="user.action",
                quiet_hours_start=24,  # Invalid
            )


class TestTriggerConditionModel:
    """Tests for TriggerCondition model - BR-CAM-007.1"""

    def test_create_equals_condition(self):
        """Test creating equals condition"""
        condition = TriggerCondition(
            field="subscription_plan",
            operator=TriggerOperator.EQUALS,
            value="premium",
        )
        assert condition.operator == TriggerOperator.EQUALS

    def test_create_in_condition(self):
        """Test creating IN condition"""
        condition = TriggerCondition(
            field="country",
            operator=TriggerOperator.IN,
            value=["US", "CA", "UK"],
        )
        assert condition.operator == TriggerOperator.IN
        assert "US" in condition.value


class TestThrottleConfigModel:
    """Tests for ThrottleConfig model - BR-CAM-006"""

    def test_create_throttle_config(self):
        """Test creating throttle configuration"""
        throttle = ThrottleConfig(
            per_minute=10000,
            per_hour=100000,
            send_window_start=8,
            send_window_end=21,
        )
        assert throttle.per_minute == 10000
        assert throttle.send_window_start == 8

    def test_throttle_exclude_weekends(self):
        """Test exclude weekends flag - BR-CAM-006.1"""
        throttle = ThrottleConfig(exclude_weekends=True)
        assert throttle.exclude_weekends is True


class TestABTestConfigModel:
    """Tests for ABTestConfig model - BR-CAM-004"""

    def test_create_ab_test_config(self):
        """Test creating A/B test configuration"""
        config = ABTestConfig(
            enabled=True,
            auto_winner_enabled=True,
            auto_winner_metric=AutoWinnerMetric.CLICK_RATE,
            auto_winner_confidence=Decimal("0.95"),
            auto_winner_min_sample=1000,
        )
        assert config.enabled is True
        assert config.auto_winner_metric == AutoWinnerMetric.CLICK_RATE

    def test_ab_test_confidence_range(self):
        """Test confidence must be 0.90-0.99 - BR-CAM-004.4"""
        with pytest.raises(ValidationError):
            ABTestConfig(
                enabled=True,
                auto_winner_confidence=Decimal("0.80"),  # Below 0.90
            )

    def test_ab_test_min_sample(self):
        """Test minimum sample size - BR-CAM-004.4"""
        with pytest.raises(ValidationError):
            ABTestConfig(
                enabled=True,
                auto_winner_min_sample=50,  # Below 100
            )


class TestConversionConfigModel:
    """Tests for ConversionConfig model - BR-CAM-005.3"""

    def test_create_conversion_config(self):
        """Test creating conversion configuration"""
        config = ConversionConfig(
            conversion_event_type="purchase.completed",
            attribution_window_days=7,
            attribution_model=AttributionModel.LAST_TOUCH,
        )
        assert config.conversion_event_type == "purchase.completed"
        assert config.attribution_model == AttributionModel.LAST_TOUCH

    def test_attribution_window_max_30_days(self):
        """Test attribution window max 30 days - BR-CAM-005.3"""
        with pytest.raises(ValidationError):
            ConversionConfig(attribution_window_days=31)


# ====================
# Execution Model Tests
# ====================


class TestCampaignExecutionModel:
    """Tests for CampaignExecution model"""

    def test_create_execution(self, factory, sample_campaign):
        """Test creating execution"""
        execution = factory.make_execution(campaign_id=sample_campaign.campaign_id)
        assert execution.campaign_id == sample_campaign.campaign_id
        assert execution.status == ExecutionStatus.PENDING

    def test_execution_counts_non_negative(self):
        """Test execution counts must be non-negative"""
        with pytest.raises(ValidationError):
            CampaignExecution(
                execution_id="exe_test",
                campaign_id="cmp_test",
                execution_type=ExecutionType.SCHEDULED,
                messages_sent=-1,  # Invalid
            )


class TestCampaignMessageModel:
    """Tests for CampaignMessage model - BR-CAM-005.1"""

    def test_create_message(self, factory, sample_campaign, sample_execution):
        """Test creating message"""
        message = factory.make_message(
            campaign_id=sample_campaign.campaign_id,
            execution_id=sample_execution.execution_id,
        )
        assert message.status == MessageStatus.QUEUED

    def test_message_default_status_queued(self):
        """Test default message status is queued"""
        message = CampaignMessage(
            message_id="msg_test",
            campaign_id="cmp_test",
            execution_id="exe_test",
            user_id="usr_test",
            channel_type=ChannelType.EMAIL,
        )
        assert message.status == MessageStatus.QUEUED


# ====================
# Request/Response Model Tests
# ====================


class TestCampaignCreateRequest:
    """Tests for CampaignCreateRequest - BR-CAM-001.1"""

    def test_valid_request(self):
        """Test valid campaign create request"""
        request = CampaignCreateRequest(
            name="Test Campaign",
            campaign_type=CampaignType.SCHEDULED,
        )
        assert request.name == "Test Campaign"
        assert request.timezone == "UTC"

    def test_request_with_schedule(self):
        """Test request with schedule"""
        request = CampaignCreateRequest(
            name="Scheduled Campaign",
            campaign_type=CampaignType.SCHEDULED,
            schedule_type=ScheduleType.ONE_TIME,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert request.schedule_type == ScheduleType.ONE_TIME


class TestCampaignQueryRequest:
    """Tests for CampaignQueryRequest - API pagination"""

    def test_query_defaults(self):
        """Test query request defaults"""
        query = CampaignQueryRequest()
        assert query.limit == 20
        assert query.offset == 0
        assert query.sort_by == "created_at"
        assert query.sort_order == "desc"

    def test_query_limit_max_100(self):
        """Test query limit max is 100"""
        with pytest.raises(ValidationError):
            CampaignQueryRequest(limit=101)

    def test_query_sort_order_values(self):
        """Test sort order must be asc or desc"""
        with pytest.raises(ValidationError):
            CampaignQueryRequest(sort_order="invalid")
