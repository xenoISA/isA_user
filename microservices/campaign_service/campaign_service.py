"""
Campaign Service Business Logic

Implements campaign lifecycle, audience management, A/B testing,
trigger evaluation, and message delivery orchestration.
"""

import logging
import uuid
import hashlib
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from scipy import stats

from .models import (
    Campaign,
    CampaignAudience,
    CampaignChannel,
    CampaignVariant,
    CampaignTrigger,
    TriggerCondition,
    CampaignExecution,
    CampaignMessage,
    CampaignMetricsSummary,
    CampaignConversion,
    TriggerHistoryRecord,
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignStatus,
    CampaignType,
    ScheduleType,
    ChannelType,
    SegmentType,
    TriggerOperator,
    MessageStatus,
    ExecutionType,
    ExecutionStatus,
    MetricType,
    AttributionModel,
    ThrottleConfig,
    ABTestConfig,
    ConversionConfig,
    VariantStatistics,
)
from .protocols import (
    CampaignRepositoryProtocol,
    EventBusProtocol,
    TaskClientProtocol,
    NotificationClientProtocol,
    IsADataClientProtocol,
    AccountClientProtocol,
    CampaignNotFoundError,
    InvalidCampaignStateError,
    InvalidCampaignTypeError,
    CampaignValidationError,
    AudienceResolutionError,
    VariantAllocationError,
)

logger = logging.getLogger(__name__)


class CampaignService:
    """Campaign service business logic layer"""

    # Constants from business rules
    MIN_SCHEDULE_MINUTES = 5  # BR-CAM-001.2
    MAX_HOLDOUT_PERCENTAGE = 20  # BR-CAM-001
    MAX_SEGMENTS_PER_CAMPAIGN = 10  # BR-CAM-002.6
    MAX_VARIANTS = 5  # BR-CAM-004.1
    MAX_TRIGGER_DELAY_DAYS = 30  # BR-CAM-007.4
    MIN_SAMPLE_SIZE_AUTO_WINNER = 1000  # BR-CAM-004.6
    DEFAULT_FREQUENCY_LIMIT = 1
    DEFAULT_FREQUENCY_WINDOW_HOURS = 24

    # Valid state transitions
    VALID_TRANSITIONS = {
        CampaignStatus.DRAFT: [CampaignStatus.SCHEDULED, CampaignStatus.ACTIVE, CampaignStatus.CANCELLED],
        CampaignStatus.SCHEDULED: [CampaignStatus.RUNNING, CampaignStatus.DRAFT, CampaignStatus.CANCELLED],
        CampaignStatus.ACTIVE: [CampaignStatus.RUNNING, CampaignStatus.PAUSED, CampaignStatus.DRAFT, CampaignStatus.CANCELLED],
        CampaignStatus.RUNNING: [CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED],
        CampaignStatus.PAUSED: [CampaignStatus.RUNNING, CampaignStatus.ACTIVE, CampaignStatus.CANCELLED],
        CampaignStatus.COMPLETED: [],  # Terminal state
        CampaignStatus.CANCELLED: [],  # Terminal state
    }

    def __init__(
        self,
        repository: CampaignRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        task_client: Optional[TaskClientProtocol] = None,
        notification_client: Optional[NotificationClientProtocol] = None,
        isa_data_client: Optional[IsADataClientProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.task_client = task_client
        self.notification_client = notification_client
        self.isa_data_client = isa_data_client
        self.account_client = account_client

    # ====================
    # Campaign CRUD - BR-CAM-001
    # ====================

    async def create_campaign(
        self,
        request: CampaignCreateRequest,
        organization_id: str,
        created_by: str,
    ) -> Campaign:
        """
        Create a new campaign - BR-CAM-001.1

        Validates input, creates campaign in draft status, publishes event.
        """
        # Validate request
        self._validate_campaign_create_request(request)

        # Generate campaign ID
        campaign_id = f"cmp_{uuid.uuid4().hex[:16]}"

        # Create campaign model
        now = datetime.now(timezone.utc)
        campaign = Campaign(
            campaign_id=campaign_id,
            organization_id=organization_id,
            name=request.name,
            description=request.description,
            campaign_type=request.campaign_type,
            status=CampaignStatus.DRAFT,
            schedule_type=request.schedule_type,
            scheduled_at=request.scheduled_at,
            cron_expression=request.cron_expression,
            timezone=request.timezone or "UTC",
            holdout_percentage=request.holdout_percentage,
            tags=request.tags or [],
            metadata=request.metadata or {},
            created_by=created_by,
            updated_by=created_by,
            throttle=request.throttle or ThrottleConfig(),
            ab_test=ABTestConfig(
                enabled=getattr(request, 'enable_ab_testing', False),
                variants=[],
            ),
            conversion=ConversionConfig(
                event_type=getattr(request, 'conversion_event_type', None),
                attribution_window_days=getattr(request, 'attribution_window_days', 7),
            ),
            created_at=now,
            updated_at=now,
            audiences=[],
            variants=[],
            triggers=[],
        )

        # Save campaign
        campaign = await self.repository.save_campaign(campaign)

        # Save audiences if provided
        if request.audiences:
            audiences = [
                CampaignAudience(
                    audience_id=f"aud_{uuid.uuid4().hex[:12]}",
                    segment_type=a.segment_type,
                    segment_id=a.segment_id,
                    segment_query=a.segment_query,
                    name=a.name,
                    created_at=now,
                    updated_at=now,
                )
                for a in request.audiences
            ]
            campaign.audiences = await self.repository.save_audiences(campaign_id, audiences)

        # Save channels/variants
        if request.variants:
            for variant_req in request.variants:
                variant = CampaignVariant(
                    variant_id=f"var_{uuid.uuid4().hex[:12]}",
                    name=variant_req.name,
                    description=variant_req.description,
                    allocation_percentage=variant_req.allocation_percentage,
                    is_control=variant_req.is_control,
                    channels=variant_req.channels,
                    created_at=now,
                    updated_at=now,
                )
                await self.repository.save_variant(campaign_id, variant)
                campaign.variants.append(variant)
        elif request.channels:
            # Create default variant with channels
            default_variant = CampaignVariant(
                variant_id=f"var_{uuid.uuid4().hex[:12]}",
                name="Default",
                allocation_percentage=Decimal("100"),
                channels=request.channels,
                created_at=now,
                updated_at=now,
            )
            await self.repository.save_variant(campaign_id, default_variant)
            campaign.variants.append(default_variant)

        # Save triggers if provided
        if request.triggers:
            triggers = [
                CampaignTrigger(
                    trigger_id=f"trg_{uuid.uuid4().hex[:12]}",
                    event_type=t.event_type,
                    conditions=t.conditions,
                    delay_minutes=t.delay_minutes,
                    delay_days=t.delay_days,
                    frequency_limit=t.frequency_limit or self.DEFAULT_FREQUENCY_LIMIT,
                    frequency_window_hours=t.frequency_window_hours or self.DEFAULT_FREQUENCY_WINDOW_HOURS,
                    quiet_hours_start=t.quiet_hours_start,
                    quiet_hours_end=t.quiet_hours_end,
                    quiet_hours_timezone=t.quiet_hours_timezone or "user_local",
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
                for t in request.triggers
            ]
            campaign.triggers = await self.repository.save_triggers(campaign_id, triggers)

        # Publish event
        await self._publish_event("campaign.created", {
            "campaign_id": campaign_id,
            "organization_id": organization_id,
            "name": campaign.name,
            "campaign_type": campaign.campaign_type.value,
            "status": campaign.status.value,
            "created_by": created_by,
        })

        logger.info(f"Campaign created: {campaign_id}")
        return campaign

    async def get_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
    ) -> Campaign:
        """Get campaign by ID"""
        if organization_id:
            campaign = await self.repository.get_campaign_by_org(organization_id, campaign_id)
        else:
            campaign = await self.repository.get_campaign(campaign_id)

        if not campaign:
            raise CampaignNotFoundError(f"Campaign not found: {campaign_id}")

        return campaign

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
    ) -> Tuple[List[Campaign], int]:
        """List campaigns with filters"""
        return await self.repository.list_campaigns(
            organization_id=organization_id,
            status=status,
            campaign_type=campaign_type,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_campaign(
        self,
        campaign_id: str,
        request: CampaignUpdateRequest,
        updated_by: str,
        organization_id: Optional[str] = None,
    ) -> Campaign:
        """
        Update campaign - BR-CAM-001.8

        Only draft or paused campaigns can be updated.
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Check if campaign can be updated
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]:
            if campaign.status == CampaignStatus.RUNNING:
                raise InvalidCampaignStateError(
                    "Running campaigns cannot be edited, pause first",
                    campaign.status
                )
            elif campaign.status == CampaignStatus.COMPLETED:
                raise InvalidCampaignStateError(
                    "Completed campaigns cannot be edited, use clone",
                    campaign.status
                )
            elif campaign.status == CampaignStatus.CANCELLED:
                raise InvalidCampaignStateError(
                    "Cancelled campaigns cannot be modified",
                    campaign.status
                )

        # Build updates dict
        updates = {}
        changed_fields = []

        if request.name is not None and request.name != campaign.name:
            self._validate_name(request.name)
            updates["name"] = request.name
            changed_fields.append("name")

        if request.description is not None:
            updates["description"] = request.description
            changed_fields.append("description")

        holdout_pct = getattr(request, 'holdout_percentage', None)
        if holdout_pct is not None:
            self._validate_holdout_percentage(holdout_pct)
            updates["holdout_percentage"] = float(holdout_pct)
            changed_fields.append("holdout_percentage")

        schedule_type = getattr(request, 'schedule_type', None)
        if schedule_type is not None:
            updates["schedule_type"] = schedule_type.value if hasattr(schedule_type, 'value') else schedule_type
            changed_fields.append("schedule_type")

        if request.scheduled_at is not None:
            updates["scheduled_at"] = request.scheduled_at
            changed_fields.append("scheduled_at")

        if request.cron_expression is not None:
            updates["cron_expression"] = request.cron_expression
            changed_fields.append("cron_expression")

        if request.timezone is not None:
            updates["timezone"] = request.timezone
            changed_fields.append("timezone")

        if request.tags is not None:
            updates["tags"] = request.tags
            changed_fields.append("tags")

        if request.metadata is not None:
            updates["metadata"] = request.metadata
            changed_fields.append("metadata")

        if request.throttle is not None:
            updates["throttle_config"] = request.throttle.model_dump()
            changed_fields.append("throttle")

        # Note: ab_test and conversion config updates are handled via specific fields
        # in the data contract (enable_ab_testing, variants, conversion_event_type, etc.)
        # These are updated through the variants and channels endpoints

        updates["updated_by"] = updated_by

        # Update campaign
        if updates:
            campaign = await self.repository.update_campaign(campaign_id, updates)

        # Update audiences if provided
        if request.audiences is not None:
            self._validate_audiences(request.audiences)
            now = datetime.now(timezone.utc)
            audiences = [
                CampaignAudience(
                    audience_id=a.audience_id or f"aud_{uuid.uuid4().hex[:12]}",
                    segment_type=a.segment_type,
                    segment_id=a.segment_id,
                    segment_query=a.segment_query,
                    name=a.name,
                    created_at=now,
                    updated_at=now,
                )
                for a in request.audiences
            ]
            campaign.audiences = await self.repository.save_audiences(campaign_id, audiences)
            changed_fields.append("audiences")

        # Publish event
        if changed_fields:
            await self._publish_event("campaign.updated", {
                "campaign_id": campaign_id,
                "changed_fields": changed_fields,
                "updated_by": updated_by,
            })

        return campaign

    async def delete_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
    ) -> bool:
        """
        Delete campaign (soft delete)

        Cannot delete running or completed campaigns.
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        if campaign.status == CampaignStatus.RUNNING:
            raise InvalidCampaignStateError(
                "Cannot delete running campaign, cancel first",
                campaign.status
            )

        return await self.repository.delete_campaign(campaign_id)

    # ====================
    # Campaign Lifecycle - BR-CAM-001.2 to BR-CAM-001.7
    # ====================

    async def schedule_campaign(
        self,
        campaign_id: str,
        scheduled_at: Optional[datetime] = None,
        tz_name: str = "UTC",
        organization_id: Optional[str] = None,
        scheduled_by: Optional[str] = None,
    ) -> Campaign:
        """
        Schedule a campaign - BR-CAM-001.2

        Scheduled campaigns require:
        - Campaign type must be 'scheduled'
        - Current status must be 'draft'
        - At least one audience segment
        - Valid content for configured channels
        - Scheduled time >= now + 5 minutes
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Validate campaign type
        if campaign.campaign_type != CampaignType.SCHEDULED:
            raise InvalidCampaignTypeError(
                "Cannot schedule a triggered campaign",
                campaign.campaign_type
            )

        # Validate current status
        if campaign.status != CampaignStatus.DRAFT:
            raise InvalidCampaignStateError(
                "Only draft campaigns can be scheduled",
                campaign.status
            )

        # Validate campaign has audiences
        if not campaign.audiences:
            raise CampaignValidationError(
                "Campaign must have at least one audience segment",
                "audiences"
            )

        # Validate campaign has content
        if not campaign.variants:
            raise CampaignValidationError(
                "Campaign must have valid content for configured channels",
                "channels"
            )

        # Use existing scheduled_at if not provided
        schedule_time = scheduled_at or campaign.scheduled_at
        if not schedule_time:
            raise CampaignValidationError(
                "Scheduled time is required",
                "scheduled_at"
            )

        # Validate scheduled time is at least 5 minutes in future
        min_schedule_time = datetime.now(timezone.utc) + timedelta(minutes=self.MIN_SCHEDULE_MINUTES)
        if schedule_time < min_schedule_time:
            raise CampaignValidationError(
                "Scheduled time must be at least 5 minutes in the future",
                "scheduled_at"
            )

        # Create task in task_service
        task_id = None
        if self.task_client:
            try:
                task_result = await self.task_client.create_task(
                    task_type="campaign.execute",
                    payload={
                        "campaign_id": campaign_id,
                        "organization_id": campaign.organization_id,
                    },
                    scheduled_at=schedule_time,
                )
                task_id = task_result.get("task_id")
            except Exception as e:
                # Log warning but continue - task_service may be unavailable in dev
                logger.warning(f"Task service unavailable for campaign {campaign_id}: {e}")
        else:
            logger.warning(f"No task client configured - campaign {campaign_id} scheduled without task")

        # Update campaign status
        # Default to one_time schedule if not set
        schedule_type = campaign.schedule_type or ScheduleType.ONE_TIME
        updates = {
            "status": CampaignStatus.SCHEDULED,
            "scheduled_at": schedule_time,
            "timezone": tz_name,
            "schedule_type": schedule_type,
            "task_id": task_id,
        }
        if scheduled_by:
            updates["updated_by"] = scheduled_by

        campaign = await self.repository.update_campaign(campaign_id, updates)

        # Publish event
        await self._publish_event("campaign.scheduled", {
            "campaign_id": campaign_id,
            "scheduled_at": schedule_time.isoformat(),
            "task_id": task_id,
        })

        logger.info(f"Campaign scheduled: {campaign_id} at {schedule_time}")
        return campaign

    async def activate_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
        activated_by: Optional[str] = None,
    ) -> Campaign:
        """
        Activate a triggered campaign - BR-CAM-001.3

        Triggered campaigns require:
        - Campaign type must be 'triggered'
        - Current status must be 'draft'
        - At least one trigger with valid conditions
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Validate campaign type
        if campaign.campaign_type != CampaignType.TRIGGERED:
            raise InvalidCampaignTypeError(
                "Cannot activate a scheduled campaign",
                campaign.campaign_type
            )

        # Validate current status
        if campaign.status != CampaignStatus.DRAFT:
            raise InvalidCampaignStateError(
                "Only draft campaigns can be activated",
                campaign.status
            )

        # Validate triggers exist
        if not campaign.triggers:
            raise CampaignValidationError(
                "Triggered campaigns require at least one trigger",
                "triggers"
            )

        # Validate each trigger has valid event_type
        for trigger in campaign.triggers:
            if not trigger.event_type:
                raise CampaignValidationError(
                    "Invalid trigger event type",
                    "triggers"
                )

        # Update campaign status
        now = datetime.now(timezone.utc)
        updates = {
            "status": CampaignStatus.ACTIVE,
        }
        if activated_by:
            updates["updated_by"] = activated_by

        campaign = await self.repository.update_campaign(campaign_id, updates)

        # Publish event
        await self._publish_event("campaign.activated", {
            "campaign_id": campaign_id,
            "activated_at": now.isoformat(),
            "trigger_count": len(campaign.triggers),
        })

        logger.info(f"Campaign activated: {campaign_id}")
        return campaign

    async def pause_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
        paused_by: Optional[str] = None,
    ) -> Campaign:
        """
        Pause a running or active campaign - BR-CAM-001.4

        Running or active campaigns can be paused.
        In-flight messages complete delivery, new queueing stops.
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Validate current status
        if campaign.status == CampaignStatus.PAUSED:
            raise InvalidCampaignStateError(
                "Campaign is already paused",
                campaign.status
            )

        # Allow pausing RUNNING or ACTIVE campaigns
        # ACTIVE = triggered campaign waiting for triggers
        # RUNNING = campaign currently executing
        if campaign.status not in (CampaignStatus.RUNNING, CampaignStatus.ACTIVE):
            raise InvalidCampaignStateError(
                "Only running or active campaigns can be paused",
                campaign.status
            )

        # Update campaign status
        now = datetime.now(timezone.utc)
        campaign = await self.repository.update_campaign_status(
            campaign_id,
            CampaignStatus.PAUSED,
            paused_at=now,
            paused_by=paused_by,
        )

        # Get current execution metrics
        executions, _ = await self.repository.list_executions(campaign_id, limit=1)
        messages_sent = 0
        messages_remaining = 0
        if executions:
            execution = executions[0]
            messages_sent = execution.messages_sent
            messages_remaining = execution.total_audience_size - execution.messages_sent

            # Update execution status
            await self.repository.update_execution_status(
                execution.execution_id,
                ExecutionStatus.PAUSED,
                paused_at=now,
            )

        # Publish event
        await self._publish_event("campaign.paused", {
            "campaign_id": campaign_id,
            "execution_id": executions[0].execution_id if executions else None,
            "paused_by": paused_by,
            "messages_sent": messages_sent,
            "messages_remaining": messages_remaining,
        })

        logger.info(f"Campaign paused: {campaign_id}")
        return campaign

    async def resume_campaign(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
        resumed_by: Optional[str] = None,
    ) -> Campaign:
        """
        Resume a paused campaign - BR-CAM-001.5

        Only paused campaigns can be resumed.
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Validate current status
        if campaign.status != CampaignStatus.PAUSED:
            raise InvalidCampaignStateError(
                "Only paused campaigns can be resumed",
                campaign.status
            )

        # Check if scheduled time expired for scheduled campaigns
        if campaign.campaign_type == CampaignType.SCHEDULED and campaign.scheduled_at:
            if campaign.scheduled_at < datetime.now(timezone.utc):
                # For expired campaigns, we may still resume but log warning
                logger.warning(f"Resuming expired campaign {campaign_id}")

        # Determine target status based on campaign type
        # - Triggered campaigns resume to ACTIVE (waiting for triggers)
        # - Scheduled/running campaigns resume to RUNNING
        target_status = CampaignStatus.RUNNING
        if campaign.campaign_type == CampaignType.TRIGGERED:
            # Check if there was an active execution (meaning it was RUNNING)
            executions, _ = await self.repository.list_executions(campaign_id, limit=1)
            if not executions or executions[0].status != ExecutionStatus.PAUSED:
                # Was paused while ACTIVE, resume to ACTIVE
                target_status = CampaignStatus.ACTIVE

        # Update campaign status
        now = datetime.now(timezone.utc)
        campaign = await self.repository.update_campaign_status(
            campaign_id,
            target_status,
            updated_by=resumed_by,
        )

        # Get current execution and update status
        executions, _ = await self.repository.list_executions(campaign_id, limit=1)
        messages_remaining = 0
        if executions:
            execution = executions[0]
            messages_remaining = execution.total_audience_size - execution.messages_sent

            await self.repository.update_execution_status(
                execution.execution_id,
                ExecutionStatus.RUNNING,
            )

        # Publish event
        await self._publish_event("campaign.resumed", {
            "campaign_id": campaign_id,
            "execution_id": executions[0].execution_id if executions else None,
            "resumed_by": resumed_by,
            "messages_remaining": messages_remaining,
        })

        logger.info(f"Campaign resumed: {campaign_id}")
        return campaign

    async def cancel_campaign(
        self,
        campaign_id: str,
        reason: Optional[str] = None,
        organization_id: Optional[str] = None,
        cancelled_by: Optional[str] = None,
    ) -> Campaign:
        """
        Cancel a campaign - BR-CAM-001.6

        Cannot cancel already completed or cancelled campaigns.
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Validate current status
        if campaign.status == CampaignStatus.COMPLETED:
            raise InvalidCampaignStateError(
                "Cannot cancel a completed campaign",
                campaign.status
            )

        if campaign.status == CampaignStatus.CANCELLED:
            raise InvalidCampaignStateError(
                "Campaign is already cancelled",
                campaign.status
            )

        # Cancel scheduled task if exists
        if campaign.task_id and self.task_client:
            try:
                await self.task_client.cancel_task(campaign.task_id)
            except Exception as e:
                logger.warning(f"Failed to cancel task {campaign.task_id}: {e}")

        # Get messages sent before cancel
        messages_sent = 0
        executions, _ = await self.repository.list_executions(campaign_id, limit=1)
        if executions:
            execution = executions[0]
            messages_sent = execution.messages_sent

            await self.repository.update_execution_status(
                execution.execution_id,
                ExecutionStatus.CANCELLED,
            )

        # Update campaign status
        now = datetime.now(timezone.utc)
        campaign = await self.repository.update_campaign_status(
            campaign_id,
            CampaignStatus.CANCELLED,
            cancelled_at=now,
            cancelled_by=cancelled_by,
            cancelled_reason=reason,
        )

        # Publish event
        await self._publish_event("campaign.cancelled", {
            "campaign_id": campaign_id,
            "cancelled_by": cancelled_by,
            "reason": reason,
            "messages_sent_before_cancel": messages_sent,
        })

        logger.info(f"Campaign cancelled: {campaign_id}")
        return campaign

    async def clone_campaign(
        self,
        campaign_id: str,
        new_name: Optional[str] = None,
        organization_id: Optional[str] = None,
        cloned_by: Optional[str] = None,
    ) -> Campaign:
        """
        Clone a campaign - BR-CAM-001.7

        Creates a copy of campaign with draft status.
        All configuration is copied, schedule and metrics are not.
        """
        source = await self.get_campaign(campaign_id, organization_id)

        # Generate new campaign ID and name
        new_campaign_id = f"cmp_{uuid.uuid4().hex[:16]}"
        clone_name = new_name or f"Copy of {source.name}"

        # Validate name
        self._validate_name(clone_name)

        # Create cloned campaign
        now = datetime.now(timezone.utc)
        cloned = Campaign(
            campaign_id=new_campaign_id,
            organization_id=source.organization_id,
            name=clone_name,
            description=source.description,
            campaign_type=source.campaign_type,
            status=CampaignStatus.DRAFT,
            schedule_type=source.schedule_type,
            scheduled_at=None,  # Clear schedule
            cron_expression=source.cron_expression,
            timezone=source.timezone,
            holdout_percentage=source.holdout_percentage,
            tags=source.tags.copy() if source.tags else [],
            metadata=source.metadata.copy() if source.metadata else {},
            created_by=cloned_by,
            updated_by=cloned_by,
            cloned_from_id=campaign_id,
            throttle=source.throttle,
            ab_test=source.ab_test,
            conversion=source.conversion,
            created_at=now,
            updated_at=now,
            audiences=[],
            variants=[],
            triggers=[],
        )

        # Save cloned campaign
        cloned = await self.repository.save_campaign(cloned)

        # Clone audiences
        if source.audiences:
            audiences = [
                CampaignAudience(
                    audience_id=f"aud_{uuid.uuid4().hex[:12]}",
                    segment_type=a.segment_type,
                    segment_id=a.segment_id,
                    segment_query=a.segment_query,
                    name=a.name,
                    estimated_size=a.estimated_size,
                    created_at=now,
                    updated_at=now,
                )
                for a in source.audiences
            ]
            cloned.audiences = await self.repository.save_audiences(new_campaign_id, audiences)

        # Clone variants
        if source.variants:
            for v in source.variants:
                variant = CampaignVariant(
                    variant_id=f"var_{uuid.uuid4().hex[:12]}",
                    name=v.name,
                    description=v.description,
                    allocation_percentage=v.allocation_percentage,
                    is_control=v.is_control,
                    channels=[
                        CampaignChannel(**c.model_dump())
                        for c in v.channels
                    ],
                    created_at=now,
                    updated_at=now,
                )
                await self.repository.save_variant(new_campaign_id, variant)
                cloned.variants.append(variant)

        # Clone triggers
        if source.triggers:
            triggers = [
                CampaignTrigger(
                    trigger_id=f"trg_{uuid.uuid4().hex[:12]}",
                    event_type=t.event_type,
                    conditions=[
                        TriggerCondition(**c.model_dump())
                        for c in t.conditions
                    ],
                    delay_minutes=t.delay_minutes,
                    delay_days=t.delay_days,
                    frequency_limit=t.frequency_limit,
                    frequency_window_hours=t.frequency_window_hours,
                    quiet_hours_start=t.quiet_hours_start,
                    quiet_hours_end=t.quiet_hours_end,
                    quiet_hours_timezone=t.quiet_hours_timezone,
                    enabled=t.enabled,
                    created_at=now,
                    updated_at=now,
                )
                for t in source.triggers
            ]
            cloned.triggers = await self.repository.save_triggers(new_campaign_id, triggers)

        # Publish event (campaign.created for the clone)
        await self._publish_event("campaign.created", {
            "campaign_id": new_campaign_id,
            "organization_id": cloned.organization_id,
            "name": cloned.name,
            "campaign_type": cloned.campaign_type.value,
            "status": cloned.status.value,
            "created_by": cloned_by,
            "cloned_from_id": campaign_id,
        })

        logger.info(f"Campaign cloned: {campaign_id} -> {new_campaign_id}")
        return cloned

    # ====================
    # Variant Operations - BR-CAM-004
    # ====================

    async def add_variant(
        self,
        campaign_id: str,
        name: str,
        allocation_percentage: Decimal,
        channels: List[CampaignChannel],
        description: Optional[str] = None,
        is_control: bool = False,
        organization_id: Optional[str] = None,
    ) -> CampaignVariant:
        """
        Add variant to campaign - BR-CAM-004.1

        Maximum 5 variants per campaign.
        Only one control variant allowed.
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Check max variants
        if len(campaign.variants) >= self.MAX_VARIANTS:
            raise VariantAllocationError(f"Maximum {self.MAX_VARIANTS} variants per campaign")

        # Check control variant
        if is_control:
            existing_controls = [v for v in campaign.variants if v.is_control]
            if existing_controls:
                raise VariantAllocationError("Only one control variant allowed")

        # Create variant
        now = datetime.now(timezone.utc)
        variant = CampaignVariant(
            variant_id=f"var_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            allocation_percentage=allocation_percentage,
            is_control=is_control,
            channels=channels,
            created_at=now,
            updated_at=now,
        )

        # Save variant
        variant = await self.repository.save_variant(campaign_id, variant)

        logger.info(f"Variant added to campaign {campaign_id}: {variant.variant_id}")
        return variant

    async def update_variant_allocations(
        self,
        campaign_id: str,
        allocations: Dict[str, Decimal],
        organization_id: Optional[str] = None,
    ) -> List[CampaignVariant]:
        """
        Update variant allocations - BR-CAM-004.1

        Allocations must sum to 100%.
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Validate sum
        total = sum(allocations.values())
        if abs(float(total) - 100.0) > 0.01:
            raise VariantAllocationError("Variant allocations must sum to 100%")

        # Update each variant
        updated_variants = []
        for variant_id, allocation in allocations.items():
            variant = await self.repository.update_variant(
                campaign_id,
                variant_id,
                {"allocation_percentage": float(allocation)},
            )
            if variant:
                updated_variants.append(variant)

        return updated_variants

    def assign_variant(
        self,
        user_id: str,
        campaign_id: str,
        variants: List[CampaignVariant],
    ) -> CampaignVariant:
        """
        Deterministic variant assignment - BR-CAM-004.2

        Uses hash of user_id + campaign_id for consistent assignment.
        """
        if not variants:
            raise VariantAllocationError("No variants available")

        # Sort variants by variant_id for consistency
        sorted_variants = sorted(variants, key=lambda v: v.variant_id)

        # Calculate hash bucket
        hash_input = f"{user_id}:{campaign_id}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        bucket = int(hash_value, 16) % 100

        # Find variant based on cumulative allocation
        cumulative = Decimal("0")
        for variant in sorted_variants:
            cumulative += variant.allocation_percentage
            if bucket < cumulative:
                return variant

        # Fallback to last variant
        return sorted_variants[-1]

    # ====================
    # Holdout and Audience - BR-CAM-002
    # ====================

    def is_in_holdout(
        self,
        user_id: str,
        campaign_id: str,
        holdout_percentage: Decimal,
    ) -> bool:
        """
        Check if user is in holdout group - BR-CAM-002.2

        Uses deterministic hash for consistent holdout assignment.
        """
        if holdout_percentage <= 0:
            return False

        hash_input = f"{user_id}:{campaign_id}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        bucket = int(hash_value, 16) % 100

        return bucket < holdout_percentage

    async def estimate_audience_size(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate audience size - BR-CAM-002.3
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        segment_estimates = []
        total_include = 0
        total_exclude = 0

        for audience in campaign.audiences:
            size = 0
            if self.isa_data_client and audience.segment_id:
                try:
                    size = await self.isa_data_client.estimate_segment_size(audience.segment_id)
                except Exception as e:
                    logger.warning(f"Failed to estimate segment {audience.segment_id}: {e}")
                    size = audience.estimated_size or 0

            segment_estimates.append({
                "segment_id": audience.segment_id,
                "type": audience.segment_type.value,
                "size": size,
            })

            if audience.segment_type == SegmentType.INCLUDE:
                if total_include == 0:
                    total_include = size
                else:
                    total_include = min(total_include, size)  # Intersection
            else:
                total_exclude += size

        # Calculate final estimates
        after_exclusions = max(0, total_include - total_exclude)
        holdout_reduction = int(after_exclusions * campaign.holdout_percentage / 100)
        after_holdout = after_exclusions - holdout_reduction

        return {
            "estimated_size": after_holdout,
            "by_segment": segment_estimates,
            "after_exclusions": after_exclusions,
            "after_holdout": after_holdout,
            "estimated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ====================
    # Trigger Evaluation - BR-CAM-007
    # ====================

    async def evaluate_trigger(
        self,
        campaign_id: str,
        trigger_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate trigger conditions - BR-CAM-007.1

        Returns (should_fire, skip_reason)
        """
        campaign = await self.get_campaign(campaign_id)

        # Find trigger
        trigger = None
        for t in campaign.triggers:
            if t.trigger_id == trigger_id:
                trigger = t
                break

        if not trigger:
            return False, "trigger_not_found"

        if not trigger.enabled:
            return False, "trigger_disabled"

        # Evaluate all conditions (AND logic)
        for condition in trigger.conditions:
            if not self._evaluate_condition(condition, event_data):
                return False, "condition_not_met"

        # Check frequency limit
        history = await self.repository.get_recent_trigger_history(
            campaign_id,
            trigger_id,
            user_id,
            hours=trigger.frequency_window_hours,
        )

        if len(history) >= trigger.frequency_limit:
            return False, "frequency_limit"

        # Verify user in segment (if audiences defined)
        if campaign.audiences and self.isa_data_client:
            in_segment = False
            for audience in campaign.audiences:
                if audience.segment_type == SegmentType.INCLUDE:
                    try:
                        segment_users = await self.isa_data_client.get_segment_users(audience.segment_id)
                        if user_id in segment_users:
                            in_segment = True
                            break
                    except Exception as e:
                        logger.warning(f"Failed to check segment membership: {e}")

            if not in_segment and campaign.audiences:
                return False, "not_in_segment"

        return True, None

    def _evaluate_condition(
        self,
        condition: TriggerCondition,
        event_data: Dict[str, Any],
    ) -> bool:
        """Evaluate single trigger condition"""
        value = event_data.get(condition.field)

        if condition.operator == TriggerOperator.EQUALS:
            return value == condition.value
        elif condition.operator == TriggerOperator.NOT_EQUALS:
            return value != condition.value
        elif condition.operator == TriggerOperator.CONTAINS:
            return condition.value in str(value) if value else False
        elif condition.operator == TriggerOperator.GREATER_THAN:
            return value > condition.value if value is not None else False
        elif condition.operator == TriggerOperator.LESS_THAN:
            return value < condition.value if value is not None else False
        elif condition.operator == TriggerOperator.IN:
            values = condition.value if isinstance(condition.value, list) else [condition.value]
            return value in values
        elif condition.operator == TriggerOperator.EXISTS:
            return value is not None

        return False

    # ====================
    # Metrics - BR-CAM-005
    # ====================

    async def get_campaign_metrics(
        self,
        campaign_id: str,
        organization_id: Optional[str] = None,
        breakdown_by: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get campaign metrics - BR-CAM-005.2"""
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Get base metrics
        metrics_summary = await self.repository.get_metrics_summary(campaign_id)

        if not metrics_summary:
            # Return empty metrics
            return {
                "campaign_id": campaign_id,
                "metrics": {
                    "total": {
                        "sent": 0,
                        "delivered": 0,
                        "opened": 0,
                        "clicked": 0,
                        "converted": 0,
                        "bounced": 0,
                        "unsubscribed": 0,
                    }
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        result = {
            "campaign_id": campaign_id,
            "metrics": {
                "total": {
                    "sent": metrics_summary.sent,
                    "delivered": metrics_summary.delivered,
                    "opened": metrics_summary.opened,
                    "clicked": metrics_summary.clicked,
                    "converted": metrics_summary.converted,
                    "bounced": metrics_summary.bounced,
                    "unsubscribed": metrics_summary.unsubscribed,
                    "delivery_rate": float(metrics_summary.delivery_rate) if metrics_summary.delivery_rate else None,
                    "open_rate": float(metrics_summary.open_rate) if metrics_summary.open_rate else None,
                    "click_rate": float(metrics_summary.click_rate) if metrics_summary.click_rate else None,
                    "conversion_rate": float(metrics_summary.conversion_rate) if metrics_summary.conversion_rate else None,
                    "bounce_rate": float(metrics_summary.bounce_rate) if metrics_summary.bounce_rate else None,
                    "unsubscribe_rate": float(metrics_summary.unsubscribe_rate) if metrics_summary.unsubscribe_rate else None,
                }
            },
            "updated_at": (metrics_summary.updated_at or datetime.now(timezone.utc)).isoformat(),
        }

        return result

    async def calculate_variant_statistics(
        self,
        campaign_id: str,
        target_metric: str = "click_rate",
        confidence_level: float = 0.95,
    ) -> Dict[str, VariantStatistics]:
        """
        Calculate A/B test statistics - BR-CAM-004.3

        Returns statistical significance analysis for variants.
        """
        campaign = await self.get_campaign(campaign_id)

        # Get messages by variant
        messages, _ = await self.repository.list_messages(campaign_id, limit=100000)

        variant_data = {}
        for variant in campaign.variants:
            variant_messages = [m for m in messages if m.variant_id == variant.variant_id]
            sent = len(variant_messages)
            delivered = len([m for m in variant_messages if m.status in [
                MessageStatus.DELIVERED, MessageStatus.OPENED, MessageStatus.CLICKED
            ]])
            opened = len([m for m in variant_messages if m.status in [
                MessageStatus.OPENED, MessageStatus.CLICKED
            ]])
            clicked = len([m for m in variant_messages if m.status == MessageStatus.CLICKED])

            variant_data[variant.variant_id] = {
                "sent": sent,
                "delivered": delivered,
                "opened": opened,
                "clicked": clicked,
                "open_rate": opened / delivered if delivered > 0 else 0,
                "click_rate": clicked / delivered if delivered > 0 else 0,
            }

        # Calculate statistical significance between variants
        results = {}
        variant_ids = list(variant_data.keys())

        # Get variant names
        variant_names = {v.variant_id: v.name for v in campaign.variants}

        for i, variant_id in enumerate(variant_ids):
            data = variant_data[variant_id]
            stats_result = VariantStatistics(
                variant_id=variant_id,
                variant_name=variant_names.get(variant_id, f"Variant {i+1}"),
                sent=data["sent"],
                delivered=data["delivered"],
                opened=data["opened"],
                clicked=data["clicked"],
                open_rate=Decimal(str(data["open_rate"])),
                click_rate=Decimal(str(data["click_rate"])),
            )

            # Compare with first variant (control) if multiple variants
            if i > 0 and len(variant_ids) > 1:
                control_data = variant_data[variant_ids[0]]

                # Chi-square test for the target metric
                if target_metric == "click_rate":
                    observed = [[data["clicked"], data["delivered"] - data["clicked"]],
                               [control_data["clicked"], control_data["delivered"] - control_data["clicked"]]]
                else:  # open_rate
                    observed = [[data["opened"], data["delivered"] - data["opened"]],
                               [control_data["opened"], control_data["delivered"] - control_data["opened"]]]

                try:
                    chi2, p_value, _, _ = stats.chi2_contingency(observed)
                    stats_result.chi_square_statistic = Decimal(str(chi2))
                    stats_result.p_value = Decimal(str(p_value))
                    stats_result.is_significant = p_value < (1 - confidence_level)
                except Exception:
                    # Not enough data for chi-square
                    pass

            results[variant_id] = stats_result

        return results

    # ====================
    # Content Preview - BR-CAM-008
    # ====================

    async def preview_content(
        self,
        campaign_id: str,
        variant_id: Optional[str] = None,
        channel_type: Optional[ChannelType] = None,
        sample_user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Preview campaign content - BR-CAM-008.2
        """
        campaign = await self.get_campaign(campaign_id, organization_id)

        # Get variant
        if variant_id:
            variant = next((v for v in campaign.variants if v.variant_id == variant_id), None)
        else:
            variant = campaign.variants[0] if campaign.variants else None

        if not variant:
            raise CampaignValidationError("No variant found", "variant_id")

        # Get channel
        if channel_type:
            channel = next((c for c in variant.channels if c.channel_type == channel_type), None)
        else:
            channel = variant.channels[0] if variant.channels else None

        if not channel:
            raise CampaignValidationError("No channel found", "channel_type")

        # Get sample user data
        sample_user = {}
        if sample_user_id and self.isa_data_client:
            try:
                sample_user = await self.isa_data_client.get_user_360(sample_user_id)
            except Exception as e:
                logger.warning(f"Failed to get user 360: {e}")
                sample_user = {"first_name": "John", "email": "john@example.com"}
        else:
            sample_user = {"first_name": "John", "last_name": "Doe", "email": "john@example.com"}

        # Render content with variables
        rendered_content = self._render_content(channel, sample_user)

        return {
            "campaign_id": campaign_id,
            "variant_id": variant.variant_id,
            "channel_type": channel.channel_type.value,
            "rendered_content": rendered_content,
            "sample_user": sample_user,
        }

    def _render_content(
        self,
        channel: CampaignChannel,
        user_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Render channel content with variable substitution"""
        result = {}

        if channel.channel_type == ChannelType.EMAIL and channel.email_content:
            content = channel.email_content
            result["subject"] = self._substitute_variables(content.subject, user_data)
            if content.body_html:
                result["body_html"] = self._substitute_variables(content.body_html, user_data)
            if content.body_text:
                result["body_text"] = self._substitute_variables(content.body_text, user_data)

        elif channel.channel_type == ChannelType.SMS and channel.sms_content:
            result["body"] = self._substitute_variables(channel.sms_content.body, user_data)

        elif channel.channel_type == ChannelType.WHATSAPP and channel.whatsapp_content:
            result["body"] = self._substitute_variables(channel.whatsapp_content.body, user_data)

        elif channel.channel_type == ChannelType.IN_APP and channel.in_app_content:
            content = channel.in_app_content
            result["title"] = self._substitute_variables(content.title, user_data)
            result["body"] = self._substitute_variables(content.body, user_data)

        return result

    def _substitute_variables(self, template: str, data: Dict[str, Any]) -> str:
        """Substitute {{variable}} placeholders with values"""
        if not template:
            return template

        def replace_var(match):
            var_name = match.group(1)
            # Support nested keys like custom_field.value
            value = data
            for key in var_name.split('.'):
                if isinstance(value, dict):
                    value = value.get(key, "")
                else:
                    value = ""
                    break
            return str(value) if value else ""

        return re.sub(r'\{\{(\w+(?:\.\w+)*)\}\}', replace_var, template)

    # ====================
    # Validation Helpers
    # ====================

    def _validate_campaign_create_request(self, request: CampaignCreateRequest) -> None:
        """Validate campaign create request"""
        self._validate_name(request.name)
        self._validate_holdout_percentage(request.holdout_percentage)

        if request.audiences:
            self._validate_audiences(request.audiences)

        if request.variants:
            self._validate_variants(request.variants)

        if request.triggers and request.campaign_type == CampaignType.TRIGGERED:
            self._validate_triggers(request.triggers)

    def _validate_name(self, name: str) -> None:
        """Validate campaign name"""
        if not name:
            raise CampaignValidationError("Campaign name is required", "name")
        if len(name) < 1:
            raise CampaignValidationError("Name must be at least 1 character", "name")
        if len(name) > 255:
            raise CampaignValidationError("Name must not exceed 255 characters", "name")

    def _validate_holdout_percentage(self, holdout: Decimal) -> None:
        """Validate holdout percentage"""
        if holdout < 0 or holdout > self.MAX_HOLDOUT_PERCENTAGE:
            raise CampaignValidationError(
                f"Holdout percentage must be between 0 and {self.MAX_HOLDOUT_PERCENTAGE}",
                "holdout_percentage"
            )

    def _validate_audiences(self, audiences: List) -> None:
        """Validate audiences list"""
        if len(audiences) > self.MAX_SEGMENTS_PER_CAMPAIGN:
            raise CampaignValidationError(
                f"Maximum {self.MAX_SEGMENTS_PER_CAMPAIGN} segments per campaign",
                "audiences"
            )

    def _validate_variants(self, variants: List) -> None:
        """Validate variants list"""
        if len(variants) > self.MAX_VARIANTS:
            raise VariantAllocationError(f"Maximum {self.MAX_VARIANTS} variants per campaign")

        # Check allocations sum
        total = sum(v.allocation_percentage for v in variants)
        if abs(float(total) - 100.0) > 0.01:
            raise VariantAllocationError("Variant allocations must sum to 100%")

        # Check control variants
        controls = [v for v in variants if v.is_control]
        if len(controls) > 1:
            raise VariantAllocationError("Only one control variant allowed")

    def _validate_triggers(self, triggers: List) -> None:
        """Validate triggers list"""
        for trigger in triggers:
            total_delay = trigger.delay_minutes + (trigger.delay_days * 24 * 60)
            if total_delay > self.MAX_TRIGGER_DELAY_DAYS * 24 * 60:
                raise CampaignValidationError(
                    f"Trigger delay cannot exceed {self.MAX_TRIGGER_DELAY_DAYS} days",
                    "triggers"
                )

    def _validate_state_transition(
        self,
        current: CampaignStatus,
        target: CampaignStatus,
    ) -> bool:
        """Validate state transition is allowed"""
        valid_targets = self.VALID_TRANSITIONS.get(current, [])
        return target in valid_targets

    # ====================
    # Event Publishing
    # ====================

    async def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event to event bus"""
        if not self.event_bus:
            logger.debug(f"Event bus not configured, skipping event: {event_type}")
            return

        try:
            event = {
                "event_type": event_type,
                "source": "campaign_service",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            await self.event_bus.publish_event(event)
            logger.debug(f"Published event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")


__all__ = ["CampaignService"]
