"""
Campaign Service Data Repository

Data access layer - PostgreSQL (Async)
"""

import logging
import os
import sys
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import uuid


class ExtendedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal and datetime types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def json_dumps(obj):
    """JSON dumps with Decimal and datetime support"""
    return json.dumps(obj, cls=ExtendedJSONEncoder)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    Campaign,
    CampaignAudience,
    CampaignChannel,
    CampaignVariant,
    CampaignTrigger,
    CampaignExecution,
    CampaignMessage,
    CampaignMetricsSummary,
    CampaignConversion,
    CampaignUnsubscribe,
    TriggerHistoryRecord,
    CampaignStatus,
    CampaignType,
    ScheduleType,
    ExecutionStatus,
    ExecutionType,
    MessageStatus,
    ChannelType,
    SegmentType,
    ThrottleConfig,
    ABTestConfig,
    ConversionConfig,
    AttributionModel,
    # Channel content types
    EmailChannelContent,
    SMSChannelContent,
    WhatsAppChannelContent,
    InAppChannelContent,
    WebhookChannelContent,
)

logger = logging.getLogger(__name__)


class CampaignRepository:
    """Campaign service data repository - PostgreSQL (Async)"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("campaign_service")

        # Discover PostgreSQL service
        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="campaign_service"
        )
        self.schema = "campaign"

        # Table names
        self.campaigns_table = "campaigns"
        self.audiences_table = "campaign_audiences"
        self.channels_table = "campaign_channels"
        self.variants_table = "campaign_variants"
        self.triggers_table = "campaign_triggers"
        self.executions_table = "campaign_executions"
        self.messages_table = "campaign_messages"
        self.metrics_table = "campaign_metrics"
        self.conversions_table = "campaign_conversions"
        self.unsubscribes_table = "campaign_unsubscribes"
        self.trigger_history_table = "trigger_history"

    async def initialize(self):
        """Initialize database connection"""
        logger.info("Campaign repository initialized with PostgreSQL")

    async def close(self):
        """Close database connection"""
        logger.info("Campaign repository database connection closed")

    async def health_check(self) -> bool:
        """Check repository health"""
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1 as healthy")
                return result is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    # ====================
    # Campaign CRUD
    # ====================

    async def save_campaign(self, campaign: Campaign) -> Campaign:
        """Save a campaign"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.campaigns_table} (
                    campaign_id, organization_id, name, description,
                    campaign_type, status, schedule_type, scheduled_at,
                    cron_expression, timezone, holdout_percentage,
                    task_id, tags, metadata, created_by, updated_by,
                    paused_at, paused_by, cancelled_at, cancelled_by,
                    cancelled_reason, cloned_from_id,
                    throttle_config, ab_test_config, conversion_config,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                    $21, $22, $23, $24, $25, $26, $27
                )
                ON CONFLICT (campaign_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    schedule_type = EXCLUDED.schedule_type,
                    scheduled_at = EXCLUDED.scheduled_at,
                    cron_expression = EXCLUDED.cron_expression,
                    timezone = EXCLUDED.timezone,
                    holdout_percentage = EXCLUDED.holdout_percentage,
                    task_id = EXCLUDED.task_id,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_by = EXCLUDED.updated_by,
                    paused_at = EXCLUDED.paused_at,
                    paused_by = EXCLUDED.paused_by,
                    cancelled_at = EXCLUDED.cancelled_at,
                    cancelled_by = EXCLUDED.cancelled_by,
                    cancelled_reason = EXCLUDED.cancelled_reason,
                    throttle_config = EXCLUDED.throttle_config,
                    ab_test_config = EXCLUDED.ab_test_config,
                    conversion_config = EXCLUDED.conversion_config,
                    updated_at = EXCLUDED.updated_at
                RETURNING *
            '''

            params = [
                campaign.campaign_id,
                campaign.organization_id,
                campaign.name,
                campaign.description,
                campaign.campaign_type.value,
                campaign.status.value,
                campaign.schedule_type.value if campaign.schedule_type else None,
                campaign.scheduled_at,
                campaign.cron_expression,
                campaign.timezone,
                float(campaign.holdout_percentage),
                campaign.task_id,
                json_dumps(campaign.tags),
                json_dumps(campaign.metadata),
                campaign.created_by,
                campaign.updated_by,
                campaign.paused_at,
                campaign.paused_by,
                campaign.cancelled_at,
                campaign.cancelled_by,
                campaign.cancelled_reason,
                campaign.cloned_from_id,
                json_dumps(campaign.throttle.model_dump() if campaign.throttle else {}),
                json_dumps(campaign.ab_test.model_dump() if campaign.ab_test else {}),
                json_dumps(campaign.conversion.model_dump() if campaign.conversion else {}),
                campaign.created_at or now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_campaign(results[0])

            return campaign

        except Exception as e:
            logger.error(f"Error saving campaign: {e}", exc_info=True)
            raise

    async def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.campaigns_table}
                WHERE campaign_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[campaign_id])

            if result:
                campaign = self._row_to_campaign(result)
                # Load related data
                campaign.audiences = await self.get_audiences(campaign_id)
                campaign.variants = await self.get_variants(campaign_id)
                campaign.triggers = await self.get_triggers(campaign_id)
                return campaign
            return None

        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            raise

    async def get_campaign_by_org(
        self, organization_id: str, campaign_id: str
    ) -> Optional[Campaign]:
        """Get campaign by organization and ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.campaigns_table}
                WHERE campaign_id = $1 AND organization_id = $2
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[campaign_id, organization_id])

            if result:
                campaign = self._row_to_campaign(result)
                campaign.audiences = await self.get_audiences(campaign_id)
                campaign.variants = await self.get_variants(campaign_id)
                campaign.triggers = await self.get_triggers(campaign_id)
                return campaign
            return None

        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id} for org {organization_id}: {e}")
            raise

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
        try:
            conditions = ["deleted_at IS NULL"]
            params = []
            param_count = 0

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if status:
                param_count += 1
                status_values = [s.value for s in status]
                conditions.append(f"status = ANY(${param_count})")
                params.append(status_values)

            if campaign_type:
                param_count += 1
                conditions.append(f"campaign_type = ${param_count}")
                params.append(campaign_type.value)

            if search:
                param_count += 1
                conditions.append(f"LOWER(name) LIKE LOWER(${param_count})")
                params.append(f"%{search}%")

            where_clause = " AND ".join(conditions)

            # Validate sort_by to prevent SQL injection
            valid_sort_fields = ["created_at", "updated_at", "name", "scheduled_at", "status"]
            if sort_by not in valid_sort_fields:
                sort_by = "created_at"
            order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

            # Count query
            count_query = f'''
                SELECT COUNT(*) as total FROM {self.schema}.{self.campaigns_table}
                WHERE {where_clause}
            '''

            async with self.db:
                count_result = await self.db.query_row(count_query, params=params)
                total = count_result.get("total", 0) if count_result else 0

            # List query
            list_query = f'''
                SELECT * FROM {self.schema}.{self.campaigns_table}
                WHERE {where_clause}
                ORDER BY {sort_by} {order_direction}
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''
            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(list_query, params=params)

            campaigns = []
            if results:
                for row in results:
                    campaign = self._row_to_campaign(row)
                    # Load related data for each campaign
                    campaign.audiences = await self.get_audiences(campaign.campaign_id)
                    campaign.variants = await self.get_variants(campaign.campaign_id)
                    campaign.triggers = await self.get_triggers(campaign.campaign_id)
                    campaigns.append(campaign)

            return campaigns, total

        except Exception as e:
            logger.error(f"Error listing campaigns: {e}")
            raise

    async def update_campaign(
        self, campaign_id: str, updates: dict
    ) -> Optional[Campaign]:
        """Update campaign fields"""
        try:
            if not updates:
                return await self.get_campaign(campaign_id)

            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                if isinstance(value, (dict, list)):
                    params.append(json_dumps(value))
                elif hasattr(value, 'value'):  # Enum
                    params.append(value.value)
                else:
                    params.append(value)

            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            param_count += 1
            params.append(campaign_id)

            query = f'''
                UPDATE {self.schema}.{self.campaigns_table}
                SET {", ".join(set_clauses)}
                WHERE campaign_id = ${param_count}
                RETURNING *
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                campaign = self._row_to_campaign(results[0])
                # Load related data
                campaign.audiences = await self.get_audiences(campaign_id)
                campaign.variants = await self.get_variants(campaign_id)
                campaign.triggers = await self.get_triggers(campaign_id)
                return campaign
            return None

        except Exception as e:
            logger.error(f"Error updating campaign {campaign_id}: {e}")
            raise

    async def update_campaign_status(
        self, campaign_id: str, status: CampaignStatus, **kwargs
    ) -> Optional[Campaign]:
        """Update campaign status"""
        updates = {"status": status, **kwargs}
        return await self.update_campaign(campaign_id, updates)

    async def delete_campaign(self, campaign_id: str) -> bool:
        """Soft delete campaign"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.campaigns_table}
                SET deleted_at = $1, updated_at = $1
                WHERE campaign_id = $2 AND deleted_at IS NULL
                RETURNING campaign_id
            '''

            now = datetime.now(timezone.utc)
            async with self.db:
                results = await self.db.query(query, params=[now, campaign_id])

            return results is not None and len(results) > 0

        except Exception as e:
            logger.error(f"Error deleting campaign {campaign_id}: {e}")
            raise

    # ====================
    # Audience Operations
    # ====================

    async def save_audiences(
        self, campaign_id: str, audiences: List[CampaignAudience]
    ) -> List[CampaignAudience]:
        """Save campaign audiences"""
        try:
            # Delete existing audiences
            delete_query = f'''
                DELETE FROM {self.schema}.{self.audiences_table}
                WHERE campaign_id = $1
            '''
            async with self.db:
                await self.db.query(delete_query, params=[campaign_id])

            # Insert new audiences
            for audience in audiences:
                insert_query = f'''
                    INSERT INTO {self.schema}.{self.audiences_table} (
                        audience_id, campaign_id, segment_type, segment_id,
                        segment_query, name, estimated_size, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                '''
                now = datetime.now(timezone.utc)
                params = [
                    audience.audience_id,
                    campaign_id,
                    audience.segment_type.value,
                    audience.segment_id,
                    json_dumps(audience.segment_query) if audience.segment_query else None,
                    audience.name,
                    audience.estimated_size,
                    now,
                    now
                ]
                async with self.db:
                    await self.db.query(insert_query, params=params)

            return audiences

        except Exception as e:
            logger.error(f"Error saving audiences for campaign {campaign_id}: {e}")
            raise

    async def get_audiences(self, campaign_id: str) -> List[CampaignAudience]:
        """Get campaign audiences"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.audiences_table}
                WHERE campaign_id = $1
            '''

            async with self.db:
                results = await self.db.query(query, params=[campaign_id])

            if not results:
                return []

            return [self._row_to_audience(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting audiences for campaign {campaign_id}: {e}")
            return []

    # ====================
    # Variant Operations
    # ====================

    async def save_variant(
        self, campaign_id: str, variant: CampaignVariant
    ) -> CampaignVariant:
        """Save campaign variant and its channels"""
        try:
            # Save variant (without channels - they go in separate table)
            query = f'''
                INSERT INTO {self.schema}.{self.variants_table} (
                    variant_id, campaign_id, name, description,
                    allocation_percentage, is_control,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (variant_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    allocation_percentage = EXCLUDED.allocation_percentage,
                    is_control = EXCLUDED.is_control,
                    updated_at = EXCLUDED.updated_at
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                variant.variant_id,
                campaign_id,
                variant.name,
                variant.description,
                float(variant.allocation_percentage),
                variant.is_control,
                variant.created_at or now,
                now
            ]

            async with self.db:
                await self.db.query(query, params=params)

            # Save channels to campaign_channels table with variant_id
            if variant.channels:
                for channel in variant.channels:
                    await self._save_variant_channel(campaign_id, variant.variant_id, channel)

            return variant

        except Exception as e:
            logger.error(f"Error saving variant for campaign {campaign_id}: {e}")
            raise

    async def _save_variant_channel(
        self, campaign_id: str, variant_id: str, channel: "CampaignChannel"
    ) -> None:
        """Save a channel for a variant"""
        try:
            # Extract channel-specific content
            email_subject = None
            email_body_html = None
            email_body_text = None
            email_sender_name = None
            email_sender_email = None
            email_reply_to = None
            sms_body = None
            whatsapp_body = None
            whatsapp_template_id = None
            in_app_title = None
            in_app_body = None
            in_app_action_url = None
            in_app_icon = None
            webhook_url = None
            webhook_method = None
            webhook_headers = None
            webhook_payload_template = None

            if channel.email_content:
                email_subject = channel.email_content.subject
                email_body_html = channel.email_content.body_html
                email_body_text = channel.email_content.body_text
                email_sender_name = channel.email_content.sender_name
                email_sender_email = channel.email_content.sender_email
                email_reply_to = channel.email_content.reply_to
            if channel.sms_content:
                sms_body = channel.sms_content.body
            if channel.whatsapp_content:
                whatsapp_body = channel.whatsapp_content.body
                whatsapp_template_id = channel.whatsapp_content.template_id
            if channel.in_app_content:
                in_app_title = channel.in_app_content.title
                in_app_body = channel.in_app_content.body
                in_app_action_url = channel.in_app_content.action_url
                in_app_icon = channel.in_app_content.icon
            if channel.webhook_content:
                webhook_url = channel.webhook_content.url
                webhook_method = channel.webhook_content.method
                webhook_headers = json_dumps(channel.webhook_content.headers) if channel.webhook_content.headers else None
                webhook_payload_template = channel.webhook_content.payload_template

            query = f'''
                INSERT INTO {self.schema}.{self.channels_table} (
                    channel_id, campaign_id, variant_id, channel_type, enabled, priority,
                    template_id, email_subject, email_body_html, email_body_text,
                    email_sender_name, email_sender_email, email_reply_to,
                    sms_body, whatsapp_body, whatsapp_template_id,
                    in_app_title, in_app_body, in_app_action_url, in_app_icon,
                    webhook_url, webhook_method, webhook_headers, webhook_payload_template,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                    $21, $22, $23, $24, $25, $26
                )
                ON CONFLICT (channel_id) DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    priority = EXCLUDED.priority,
                    template_id = EXCLUDED.template_id,
                    email_subject = EXCLUDED.email_subject,
                    email_body_html = EXCLUDED.email_body_html,
                    email_body_text = EXCLUDED.email_body_text,
                    updated_at = EXCLUDED.updated_at
            '''

            now = datetime.now(timezone.utc)
            params = [
                channel.channel_id,
                campaign_id,
                variant_id,
                channel.channel_type.value,
                channel.enabled,
                channel.priority,
                channel.template_id,
                email_subject,
                email_body_html,
                email_body_text,
                email_sender_name,
                email_sender_email,
                email_reply_to,
                sms_body,
                whatsapp_body,
                whatsapp_template_id,
                in_app_title,
                in_app_body,
                in_app_action_url,
                in_app_icon,
                webhook_url,
                webhook_method,
                webhook_headers,
                webhook_payload_template,
                channel.created_at or now,
                now
            ]

            async with self.db:
                await self.db.query(query, params=params)

        except Exception as e:
            logger.error(f"Error saving channel {channel.channel_id} for variant {variant_id}: {e}")
            raise

    async def get_variants(self, campaign_id: str) -> List[CampaignVariant]:
        """Get campaign variants with their channels"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.variants_table}
                WHERE campaign_id = $1
            '''

            async with self.db:
                results = await self.db.query(query, params=[campaign_id])

            if not results:
                return []

            variants = []
            for row in results:
                variant = self._row_to_variant(row)
                # Load channels for this variant
                variant.channels = await self._get_variant_channels(campaign_id, variant.variant_id)
                variants.append(variant)

            return variants

        except Exception as e:
            logger.error(f"Error getting variants for campaign {campaign_id}: {e}")
            return []

    async def _get_variant_channels(self, campaign_id: str, variant_id: str) -> List["CampaignChannel"]:
        """Get channels for a specific variant"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.channels_table}
                WHERE campaign_id = $1 AND variant_id = $2
                ORDER BY priority ASC
            '''

            async with self.db:
                results = await self.db.query(query, params=[campaign_id, variant_id])

            if not results:
                return []

            return [self._row_to_channel(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting channels for variant {variant_id}: {e}")
            return []

    async def update_variant(
        self, campaign_id: str, variant_id: str, updates: dict
    ) -> Optional[CampaignVariant]:
        """Update variant"""
        try:
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                if isinstance(value, (dict, list)):
                    params.append(json_dumps(value))
                elif isinstance(value, Decimal):
                    params.append(float(value))
                else:
                    params.append(value)

            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            params.extend([variant_id, campaign_id])

            query = f'''
                UPDATE {self.schema}.{self.variants_table}
                SET {", ".join(set_clauses)}
                WHERE variant_id = ${param_count + 1} AND campaign_id = ${param_count + 2}
                RETURNING *
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_variant(results[0])
            return None

        except Exception as e:
            logger.error(f"Error updating variant {variant_id}: {e}")
            raise

    async def delete_variant(self, campaign_id: str, variant_id: str) -> bool:
        """Delete variant"""
        try:
            query = f'''
                DELETE FROM {self.schema}.{self.variants_table}
                WHERE variant_id = $1 AND campaign_id = $2
                RETURNING variant_id
            '''

            async with self.db:
                results = await self.db.query(query, params=[variant_id, campaign_id])

            return results is not None and len(results) > 0

        except Exception as e:
            logger.error(f"Error deleting variant {variant_id}: {e}")
            raise

    # ====================
    # Channel Operations
    # ====================

    async def save_channels(
        self, campaign_id: str, channels: List[CampaignChannel]
    ) -> List[CampaignChannel]:
        """Save campaign channels"""
        try:
            # Delete existing channels
            delete_query = f'''
                DELETE FROM {self.schema}.{self.channels_table}
                WHERE campaign_id = $1
            '''
            async with self.db:
                await self.db.query(delete_query, params=[campaign_id])

            # Insert new channels
            for channel in channels:
                insert_query = f'''
                    INSERT INTO {self.schema}.{self.channels_table} (
                        channel_id, campaign_id, channel_type, enabled,
                        priority, template_id, content_config,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                '''
                now = datetime.now(timezone.utc)
                content_config = channel.model_dump(exclude={
                    "channel_id", "channel_type", "enabled", "priority",
                    "template_id", "created_at", "updated_at"
                })
                params = [
                    channel.channel_id,
                    campaign_id,
                    channel.channel_type.value,
                    channel.enabled,
                    channel.priority,
                    channel.template_id,
                    json_dumps(content_config),
                    now,
                    now
                ]
                async with self.db:
                    await self.db.query(insert_query, params=params)

            return channels

        except Exception as e:
            logger.error(f"Error saving channels for campaign {campaign_id}: {e}")
            raise

    async def get_channels(self, campaign_id: str) -> List[CampaignChannel]:
        """Get campaign channels"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.channels_table}
                WHERE campaign_id = $1
                ORDER BY priority ASC
            '''

            async with self.db:
                results = await self.db.query(query, params=[campaign_id])

            if not results:
                return []

            return [self._row_to_channel(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting channels for campaign {campaign_id}: {e}")
            return []

    # ====================
    # Trigger Operations
    # ====================

    async def save_triggers(
        self, campaign_id: str, triggers: List[CampaignTrigger]
    ) -> List[CampaignTrigger]:
        """Save campaign triggers"""
        try:
            # Delete existing triggers
            delete_query = f'''
                DELETE FROM {self.schema}.{self.triggers_table}
                WHERE campaign_id = $1
            '''
            async with self.db:
                await self.db.query(delete_query, params=[campaign_id])

            # Insert new triggers
            for trigger in triggers:
                insert_query = f'''
                    INSERT INTO {self.schema}.{self.triggers_table} (
                        trigger_id, campaign_id, event_type, conditions,
                        delay_minutes, delay_days, frequency_limit,
                        frequency_window_hours, quiet_hours_start,
                        quiet_hours_end, quiet_hours_timezone, enabled,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                '''
                now = datetime.now(timezone.utc)
                conditions_json = json_dumps([c.model_dump() for c in trigger.conditions])
                params = [
                    trigger.trigger_id,
                    campaign_id,
                    trigger.event_type,
                    conditions_json,
                    trigger.delay_minutes,
                    trigger.delay_days,
                    trigger.frequency_limit,
                    trigger.frequency_window_hours,
                    trigger.quiet_hours_start,
                    trigger.quiet_hours_end,
                    trigger.quiet_hours_timezone,
                    trigger.enabled,
                    now,
                    now
                ]
                async with self.db:
                    await self.db.query(insert_query, params=params)

            return triggers

        except Exception as e:
            logger.error(f"Error saving triggers for campaign {campaign_id}: {e}")
            raise

    async def get_triggers(self, campaign_id: str) -> List[CampaignTrigger]:
        """Get campaign triggers"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.triggers_table}
                WHERE campaign_id = $1
            '''

            async with self.db:
                results = await self.db.query(query, params=[campaign_id])

            if not results:
                return []

            return [self._row_to_trigger(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting triggers for campaign {campaign_id}: {e}")
            return []

    # ====================
    # Execution Operations
    # ====================

    async def save_execution(self, execution: CampaignExecution) -> CampaignExecution:
        """Save execution"""
        try:
            query = f'''
                INSERT INTO {self.schema}.{self.executions_table} (
                    execution_id, campaign_id, execution_type,
                    trigger_event_id, status, total_audience_size,
                    holdout_size, messages_queued, messages_sent,
                    messages_delivered, messages_failed,
                    started_at, completed_at, paused_at,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (execution_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    messages_queued = EXCLUDED.messages_queued,
                    messages_sent = EXCLUDED.messages_sent,
                    messages_delivered = EXCLUDED.messages_delivered,
                    messages_failed = EXCLUDED.messages_failed,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at,
                    paused_at = EXCLUDED.paused_at,
                    updated_at = EXCLUDED.updated_at
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                execution.execution_id,
                execution.campaign_id,
                execution.execution_type.value,
                execution.trigger_event_id,
                execution.status.value,
                execution.total_audience_size,
                execution.holdout_size,
                execution.messages_queued,
                execution.messages_sent,
                execution.messages_delivered,
                execution.messages_failed,
                execution.started_at,
                execution.completed_at,
                execution.paused_at,
                execution.created_at or now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_execution(results[0])
            return execution

        except Exception as e:
            logger.error(f"Error saving execution: {e}")
            raise

    async def get_execution(self, execution_id: str) -> Optional[CampaignExecution]:
        """Get execution by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.executions_table}
                WHERE execution_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[execution_id])

            if result:
                return self._row_to_execution(result)
            return None

        except Exception as e:
            logger.error(f"Error getting execution {execution_id}: {e}")
            raise

    async def list_executions(
        self, campaign_id: str, limit: int = 20, offset: int = 0
    ) -> Tuple[List[CampaignExecution], int]:
        """List executions for campaign"""
        try:
            count_query = f'''
                SELECT COUNT(*) as total FROM {self.schema}.{self.executions_table}
                WHERE campaign_id = $1
            '''

            async with self.db:
                count_result = await self.db.query_row(count_query, params=[campaign_id])
                total = count_result.get("total", 0) if count_result else 0

            list_query = f'''
                SELECT * FROM {self.schema}.{self.executions_table}
                WHERE campaign_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            '''

            async with self.db:
                results = await self.db.query(list_query, params=[campaign_id, limit, offset])

            executions = [self._row_to_execution(row) for row in results] if results else []
            return executions, total

        except Exception as e:
            logger.error(f"Error listing executions for campaign {campaign_id}: {e}")
            raise

    async def update_execution_status(
        self, execution_id: str, status: ExecutionStatus, **kwargs
    ) -> Optional[CampaignExecution]:
        """Update execution status"""
        try:
            set_clauses = ["status = $1", "updated_at = $2"]
            params = [status.value, datetime.now(timezone.utc)]
            param_count = 2

            for key, value in kwargs.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(execution_id)

            query = f'''
                UPDATE {self.schema}.{self.executions_table}
                SET {", ".join(set_clauses)}
                WHERE execution_id = ${param_count}
                RETURNING *
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_execution(results[0])
            return None

        except Exception as e:
            logger.error(f"Error updating execution {execution_id}: {e}")
            raise

    # ====================
    # Message Operations
    # ====================

    async def save_message(self, message: CampaignMessage) -> CampaignMessage:
        """Save message"""
        try:
            query = f'''
                INSERT INTO {self.schema}.{self.messages_table} (
                    message_id, campaign_id, execution_id, variant_id,
                    user_id, channel_type, recipient_address, status,
                    notification_id, provider_message_id,
                    queued_at, sent_at, delivered_at, opened_at,
                    clicked_at, bounced_at, failed_at, unsubscribed_at,
                    error_message, bounce_type, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                )
                ON CONFLICT (message_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    notification_id = EXCLUDED.notification_id,
                    provider_message_id = EXCLUDED.provider_message_id,
                    sent_at = EXCLUDED.sent_at,
                    delivered_at = EXCLUDED.delivered_at,
                    opened_at = EXCLUDED.opened_at,
                    clicked_at = EXCLUDED.clicked_at,
                    bounced_at = EXCLUDED.bounced_at,
                    failed_at = EXCLUDED.failed_at,
                    unsubscribed_at = EXCLUDED.unsubscribed_at,
                    error_message = EXCLUDED.error_message,
                    bounce_type = EXCLUDED.bounce_type,
                    metadata = EXCLUDED.metadata
                RETURNING *
            '''

            params = [
                message.message_id,
                message.campaign_id,
                message.execution_id,
                message.variant_id,
                message.user_id,
                message.channel_type.value,
                message.recipient_address,
                message.status.value,
                message.notification_id,
                message.provider_message_id,
                message.queued_at,
                message.sent_at,
                message.delivered_at,
                message.opened_at,
                message.clicked_at,
                message.bounced_at,
                message.failed_at,
                message.unsubscribed_at,
                message.error_message,
                message.bounce_type.value if message.bounce_type else None,
                json_dumps(message.metadata)
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_message(results[0])
            return message

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    async def get_message(self, message_id: str) -> Optional[CampaignMessage]:
        """Get message by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.messages_table}
                WHERE message_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[message_id])

            if result:
                return self._row_to_message(result)
            return None

        except Exception as e:
            logger.error(f"Error getting message {message_id}: {e}")
            raise

    async def list_messages(
        self,
        campaign_id: str,
        execution_id: Optional[str] = None,
        status: Optional[MessageStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[CampaignMessage], int]:
        """List messages for campaign"""
        try:
            conditions = ["campaign_id = $1"]
            params = [campaign_id]
            param_count = 1

            if execution_id:
                param_count += 1
                conditions.append(f"execution_id = ${param_count}")
                params.append(execution_id)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            where_clause = " AND ".join(conditions)

            count_query = f'''
                SELECT COUNT(*) as total FROM {self.schema}.{self.messages_table}
                WHERE {where_clause}
            '''

            async with self.db:
                count_result = await self.db.query_row(count_query, params=params)
                total = count_result.get("total", 0) if count_result else 0

            list_query = f'''
                SELECT * FROM {self.schema}.{self.messages_table}
                WHERE {where_clause}
                ORDER BY queued_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''
            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(list_query, params=params)

            messages = [self._row_to_message(row) for row in results] if results else []
            return messages, total

        except Exception as e:
            logger.error(f"Error listing messages for campaign {campaign_id}: {e}")
            raise

    async def update_message_status(
        self, message_id: str, status: MessageStatus, **kwargs
    ) -> Optional[CampaignMessage]:
        """Update message status"""
        try:
            set_clauses = ["status = $1"]
            params = [status.value]
            param_count = 1

            for key, value in kwargs.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                if hasattr(value, 'value'):  # Enum
                    params.append(value.value)
                else:
                    params.append(value)

            param_count += 1
            params.append(message_id)

            query = f'''
                UPDATE {self.schema}.{self.messages_table}
                SET {", ".join(set_clauses)}
                WHERE message_id = ${param_count}
                RETURNING *
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_message(results[0])
            return None

        except Exception as e:
            logger.error(f"Error updating message {message_id}: {e}")
            raise

    # ====================
    # Metrics Operations
    # ====================

    async def get_metrics_summary(
        self, campaign_id: str
    ) -> Optional[CampaignMetricsSummary]:
        """Get metrics summary for campaign"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.metrics_table}
                WHERE campaign_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[campaign_id])

            if result:
                return self._row_to_metrics_summary(result)
            return None

        except Exception as e:
            logger.error(f"Error getting metrics for campaign {campaign_id}: {e}")
            return None

    async def save_metrics_summary(
        self, metrics: CampaignMetricsSummary
    ) -> CampaignMetricsSummary:
        """Save metrics summary"""
        try:
            query = f'''
                INSERT INTO {self.schema}.{self.metrics_table} (
                    campaign_id, execution_id, sent, delivered, opened,
                    clicked, converted, bounced, failed, unsubscribed,
                    delivery_rate, open_rate, click_rate, conversion_rate,
                    bounce_rate, unsubscribe_rate, total_conversion_value,
                    updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18
                )
                ON CONFLICT (campaign_id) DO UPDATE SET
                    execution_id = EXCLUDED.execution_id,
                    sent = EXCLUDED.sent,
                    delivered = EXCLUDED.delivered,
                    opened = EXCLUDED.opened,
                    clicked = EXCLUDED.clicked,
                    converted = EXCLUDED.converted,
                    bounced = EXCLUDED.bounced,
                    failed = EXCLUDED.failed,
                    unsubscribed = EXCLUDED.unsubscribed,
                    delivery_rate = EXCLUDED.delivery_rate,
                    open_rate = EXCLUDED.open_rate,
                    click_rate = EXCLUDED.click_rate,
                    conversion_rate = EXCLUDED.conversion_rate,
                    bounce_rate = EXCLUDED.bounce_rate,
                    unsubscribe_rate = EXCLUDED.unsubscribe_rate,
                    total_conversion_value = EXCLUDED.total_conversion_value,
                    updated_at = EXCLUDED.updated_at
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                metrics.campaign_id,
                metrics.execution_id,
                metrics.sent,
                metrics.delivered,
                metrics.opened,
                metrics.clicked,
                metrics.converted,
                metrics.bounced,
                metrics.failed,
                metrics.unsubscribed,
                float(metrics.delivery_rate) if metrics.delivery_rate else None,
                float(metrics.open_rate) if metrics.open_rate else None,
                float(metrics.click_rate) if metrics.click_rate else None,
                float(metrics.conversion_rate) if metrics.conversion_rate else None,
                float(metrics.bounce_rate) if metrics.bounce_rate else None,
                float(metrics.unsubscribe_rate) if metrics.unsubscribe_rate else None,
                float(metrics.total_conversion_value),
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_metrics_summary(results[0])
            return metrics

        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            raise

    # ====================
    # Trigger History Operations
    # ====================

    async def save_trigger_history(
        self, history: TriggerHistoryRecord
    ) -> TriggerHistoryRecord:
        """Save trigger history record"""
        try:
            query = f'''
                INSERT INTO {self.schema}.{self.trigger_history_table} (
                    history_id, campaign_id, trigger_id, event_id,
                    event_type, user_id, triggered, skip_reason,
                    execution_id, evaluated_at, scheduled_send_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
            '''

            params = [
                history.history_id,
                history.campaign_id,
                history.trigger_id,
                history.event_id,
                history.event_type,
                history.user_id,
                history.triggered,
                history.skip_reason,
                history.execution_id,
                history.evaluated_at,
                history.scheduled_send_at
            ]

            async with self.db:
                await self.db.query(query, params=params)

            return history

        except Exception as e:
            logger.error(f"Error saving trigger history: {e}")
            raise

    async def get_recent_trigger_history(
        self,
        campaign_id: str,
        trigger_id: str,
        user_id: str,
        hours: int = 24,
    ) -> List[TriggerHistoryRecord]:
        """Get recent trigger history for frequency limiting"""
        try:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)

            query = f'''
                SELECT * FROM {self.schema}.{self.trigger_history_table}
                WHERE campaign_id = $1
                  AND trigger_id = $2
                  AND user_id = $3
                  AND triggered = true
                  AND evaluated_at >= $4
                ORDER BY evaluated_at DESC
            '''

            async with self.db:
                results = await self.db.query(
                    query, params=[campaign_id, trigger_id, user_id, since]
                )

            if not results:
                return []

            return [self._row_to_trigger_history(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting trigger history: {e}")
            return []

    # ====================
    # Helper Methods
    # ====================

    def _row_to_campaign(self, row: Dict[str, Any]) -> Campaign:
        """Convert database row to Campaign model"""
        throttle_config = row.get("throttle_config", {})
        if isinstance(throttle_config, str):
            throttle_config = json.loads(throttle_config)

        ab_test_config = row.get("ab_test_config", {})
        if isinstance(ab_test_config, str):
            ab_test_config = json.loads(ab_test_config)

        conversion_config = row.get("conversion_config", {})
        if isinstance(conversion_config, str):
            conversion_config = json.loads(conversion_config)

        tags = row.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags)

        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        # Use model_construct to skip validation during initial construction
        # Related data (audiences, variants, triggers) is loaded separately
        return Campaign.model_construct(
            campaign_id=row.get("campaign_id"),
            organization_id=row.get("organization_id"),
            name=row.get("name"),
            description=row.get("description"),
            campaign_type=CampaignType(row.get("campaign_type")),
            status=CampaignStatus(row.get("status")),
            # Default schedule_type to ONE_TIME for scheduled campaigns without it (legacy data)
            schedule_type=ScheduleType(row.get("schedule_type")) if row.get("schedule_type") else (
                ScheduleType.ONE_TIME if row.get("campaign_type") == "scheduled" and row.get("status") in ("scheduled", "running", "paused", "completed")
                else None
            ),
            scheduled_at=row.get("scheduled_at"),
            cron_expression=row.get("cron_expression"),
            timezone=row.get("timezone", "UTC"),
            holdout_percentage=Decimal(str(row.get("holdout_percentage", 0))),
            task_id=row.get("task_id"),
            tags=tags,
            metadata=metadata,
            created_by=row.get("created_by"),
            updated_by=row.get("updated_by"),
            paused_at=row.get("paused_at"),
            paused_by=row.get("paused_by"),
            cancelled_at=row.get("cancelled_at"),
            cancelled_by=row.get("cancelled_by"),
            cancelled_reason=row.get("cancelled_reason"),
            cloned_from_id=row.get("cloned_from_id"),
            throttle=ThrottleConfig(**throttle_config) if throttle_config else ThrottleConfig(),
            ab_test=ABTestConfig(**ab_test_config) if ab_test_config else ABTestConfig(),
            conversion=ConversionConfig(**conversion_config) if conversion_config else ConversionConfig(),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            deleted_at=row.get("deleted_at"),
            audiences=[],
            variants=[],
            triggers=[],
        )

    def _row_to_audience(self, row: Dict[str, Any]) -> CampaignAudience:
        """Convert database row to CampaignAudience model"""
        segment_query = row.get("segment_query")
        if isinstance(segment_query, str):
            segment_query = json.loads(segment_query)

        return CampaignAudience(
            audience_id=row.get("audience_id"),
            segment_type=SegmentType(row.get("segment_type")),
            segment_id=row.get("segment_id"),
            segment_query=segment_query,
            name=row.get("name"),
            estimated_size=row.get("estimated_size"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_variant(self, row: Dict[str, Any]) -> CampaignVariant:
        """Convert database row to CampaignVariant model"""
        # Note: channels are loaded separately via _get_variant_channels
        return CampaignVariant.model_construct(
            variant_id=row.get("variant_id"),
            name=row.get("name"),
            description=row.get("description"),
            allocation_percentage=Decimal(str(row.get("allocation_percentage", 0))),
            is_control=row.get("is_control", False),
            channels=[],  # Will be populated by get_variants
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_channel(self, row: Dict[str, Any]) -> CampaignChannel:
        """Convert database row to CampaignChannel model"""
        # Build channel-specific content objects from flat columns
        email_content = None
        sms_content = None
        whatsapp_content = None
        in_app_content = None
        webhook_content = None

        channel_type = ChannelType(row.get("channel_type"))

        # Build email content if present
        if row.get("email_subject") or row.get("email_body_html"):
            email_content = EmailChannelContent(
                subject=row.get("email_subject"),
                body_html=row.get("email_body_html"),
                body_text=row.get("email_body_text"),
                sender_name=row.get("email_sender_name"),
                sender_email=row.get("email_sender_email"),
                reply_to=row.get("email_reply_to"),
            )

        # Build SMS content if present
        if row.get("sms_body"):
            sms_content = SMSChannelContent(
                body=row.get("sms_body"),
            )

        # Build WhatsApp content if present
        if row.get("whatsapp_body") or row.get("whatsapp_template_id"):
            whatsapp_content = WhatsAppChannelContent(
                body=row.get("whatsapp_body"),
                template_id=row.get("whatsapp_template_id"),
            )

        # Build in-app content if present
        if row.get("in_app_title") or row.get("in_app_body"):
            in_app_content = InAppChannelContent(
                title=row.get("in_app_title"),
                body=row.get("in_app_body"),
                action_url=row.get("in_app_action_url"),
                icon=row.get("in_app_icon"),
            )

        # Build webhook content if present
        if row.get("webhook_url"):
            webhook_headers = row.get("webhook_headers", {})
            if isinstance(webhook_headers, str):
                webhook_headers = json.loads(webhook_headers)
            webhook_content = WebhookChannelContent(
                url=row.get("webhook_url"),
                method=row.get("webhook_method", "POST"),
                headers=webhook_headers,
                payload_template=row.get("webhook_payload_template"),
            )

        return CampaignChannel.model_construct(
            channel_id=row.get("channel_id"),
            channel_type=channel_type,
            enabled=row.get("enabled", True),
            priority=row.get("priority", 0),
            template_id=row.get("template_id"),
            email_content=email_content,
            sms_content=sms_content,
            whatsapp_content=whatsapp_content,
            in_app_content=in_app_content,
            webhook_content=webhook_content,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_trigger(self, row: Dict[str, Any]) -> CampaignTrigger:
        """Convert database row to CampaignTrigger model"""
        from .models import TriggerCondition

        conditions = row.get("conditions", [])
        if isinstance(conditions, str):
            conditions = json.loads(conditions)

        return CampaignTrigger(
            trigger_id=row.get("trigger_id"),
            event_type=row.get("event_type"),
            conditions=[TriggerCondition(**c) for c in conditions] if conditions else [],
            delay_minutes=row.get("delay_minutes", 0),
            delay_days=row.get("delay_days", 0),
            frequency_limit=row.get("frequency_limit", 1),
            frequency_window_hours=row.get("frequency_window_hours", 24),
            quiet_hours_start=row.get("quiet_hours_start"),
            quiet_hours_end=row.get("quiet_hours_end"),
            quiet_hours_timezone=row.get("quiet_hours_timezone", "user_local"),
            enabled=row.get("enabled", True),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_execution(self, row: Dict[str, Any]) -> CampaignExecution:
        """Convert database row to CampaignExecution model"""
        return CampaignExecution(
            execution_id=row.get("execution_id"),
            campaign_id=row.get("campaign_id"),
            execution_type=ExecutionType(row.get("execution_type")),
            trigger_event_id=row.get("trigger_event_id"),
            status=ExecutionStatus(row.get("status")),
            total_audience_size=row.get("total_audience_size", 0),
            holdout_size=row.get("holdout_size", 0),
            messages_queued=row.get("messages_queued", 0),
            messages_sent=row.get("messages_sent", 0),
            messages_delivered=row.get("messages_delivered", 0),
            messages_failed=row.get("messages_failed", 0),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            paused_at=row.get("paused_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_message(self, row: Dict[str, Any]) -> CampaignMessage:
        """Convert database row to CampaignMessage model"""
        from .models import BounceType

        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        bounce_type = row.get("bounce_type")
        if bounce_type:
            bounce_type = BounceType(bounce_type)

        return CampaignMessage(
            message_id=row.get("message_id"),
            campaign_id=row.get("campaign_id"),
            execution_id=row.get("execution_id"),
            variant_id=row.get("variant_id"),
            user_id=row.get("user_id"),
            channel_type=ChannelType(row.get("channel_type")),
            recipient_address=row.get("recipient_address"),
            status=MessageStatus(row.get("status")),
            notification_id=row.get("notification_id"),
            provider_message_id=row.get("provider_message_id"),
            queued_at=row.get("queued_at"),
            sent_at=row.get("sent_at"),
            delivered_at=row.get("delivered_at"),
            opened_at=row.get("opened_at"),
            clicked_at=row.get("clicked_at"),
            bounced_at=row.get("bounced_at"),
            failed_at=row.get("failed_at"),
            unsubscribed_at=row.get("unsubscribed_at"),
            error_message=row.get("error_message"),
            bounce_type=bounce_type,
            metadata=metadata,
        )

    def _row_to_metrics_summary(self, row: Dict[str, Any]) -> CampaignMetricsSummary:
        """Convert database row to CampaignMetricsSummary model"""
        return CampaignMetricsSummary(
            campaign_id=row.get("campaign_id"),
            execution_id=row.get("execution_id"),
            sent=row.get("sent", 0),
            delivered=row.get("delivered", 0),
            opened=row.get("opened", 0),
            clicked=row.get("clicked", 0),
            converted=row.get("converted", 0),
            bounced=row.get("bounced", 0),
            failed=row.get("failed", 0),
            unsubscribed=row.get("unsubscribed", 0),
            delivery_rate=Decimal(str(row.get("delivery_rate"))) if row.get("delivery_rate") else None,
            open_rate=Decimal(str(row.get("open_rate"))) if row.get("open_rate") else None,
            click_rate=Decimal(str(row.get("click_rate"))) if row.get("click_rate") else None,
            conversion_rate=Decimal(str(row.get("conversion_rate"))) if row.get("conversion_rate") else None,
            bounce_rate=Decimal(str(row.get("bounce_rate"))) if row.get("bounce_rate") else None,
            unsubscribe_rate=Decimal(str(row.get("unsubscribe_rate"))) if row.get("unsubscribe_rate") else None,
            total_conversion_value=Decimal(str(row.get("total_conversion_value", 0))),
            updated_at=row.get("updated_at"),
        )

    def _row_to_trigger_history(self, row: Dict[str, Any]) -> TriggerHistoryRecord:
        """Convert database row to TriggerHistoryRecord model"""
        return TriggerHistoryRecord(
            history_id=row.get("history_id"),
            campaign_id=row.get("campaign_id"),
            trigger_id=row.get("trigger_id"),
            event_id=row.get("event_id"),
            event_type=row.get("event_type"),
            user_id=row.get("user_id"),
            triggered=row.get("triggered", False),
            skip_reason=row.get("skip_reason"),
            execution_id=row.get("execution_id"),
            evaluated_at=row.get("evaluated_at"),
            scheduled_send_at=row.get("scheduled_send_at"),
        )


__all__ = ["CampaignRepository"]
