"""
Billing Service Data Repository

数据访问层 - PostgreSQL + gRPC (Async)
"""

import logging
import os
import sys
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    BillingRecord, BillingEvent, UsageAggregation, BillingQuota,
    BillingStatus, BillingMethod, EventType, ServiceType, Currency,
    BillingAccountType,
)

logger = logging.getLogger(__name__)


class BillingRepository:
    """计费服务数据仓库 - PostgreSQL (Async)"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("billing_service")

        # Discover PostgreSQL service
        # Priority: environment variable → Consul → localhost fallback
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
            user_id="billing_service",
        min_pool_size=1,
        max_pool_size=2,
        )
        self.schema = "billing"
        self.billing_records_table = "billing_records"
        self.billing_events_table = "billing_events"
        self.usage_aggregations_table = "usage_aggregations"
        self.billing_quotas_table = "billing_quotas"

    async def initialize(self):
        """Initialize repository and validate required schema."""
        required_record_columns = {
            "actor_user_id",
            "billing_account_type",
            "billing_account_id",
            "agent_id",
        }
        required_event_columns = {
            "actor_user_id",
            "billing_account_type",
            "billing_account_id",
            "agent_id",
        }
        table_requirements = {
            self.billing_records_table: required_record_columns,
            self.billing_events_table: required_event_columns,
        }
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = $1
              AND table_name = $2
        """

        async with self.db:
            for table_name, required_columns in table_requirements.items():
                results = await self.db.query(
                    query,
                    params=[self.schema, table_name],
                )
                available_columns = {
                    row["column_name"] if isinstance(row, dict) else row[0]
                    for row in (results or [])
                }
                missing_columns = sorted(required_columns - available_columns)
                if missing_columns:
                    raise RuntimeError(
                        f"billing.{table_name} schema is missing required columns: "
                        f"{', '.join(missing_columns)}. "
                        "Apply migrations 003_add_agent_attribution_to_billing.sql "
                        "and 004_add_canonical_payer_fields.sql."
                    )

            claim_table_results = await self.db.query(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = $1
                  AND table_name = $2
                """,
                params=[self.schema, "event_processing_claims"],
            )

        if not claim_table_results:
            raise RuntimeError(
                "billing.event_processing_claims table is missing. "
                "Apply migration 005_add_event_processing_claims.sql."
            )

        logger.info("Billing repository initialized")

    async def close(self):
        """关闭数据库连接"""
        logger.info("Billing repository database connection closed")

    # ====================
    # 计费记录管理
    # ====================

    async def create_billing_record(self, billing_record: BillingRecord) -> BillingRecord:
        """创建计费记录"""
        try:
            billing_id = billing_record.billing_id or f"bill_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.billing_records_table} (
                    billing_id, user_id, actor_user_id, billing_account_type, billing_account_id,
                    organization_id, agent_id, subscription_id, usage_record_id,
                    product_id, service_type, usage_amount, unit_price, total_amount,
                    currency, billing_method, billing_status,
                    wallet_transaction_id, payment_transaction_id, failure_reason,
                    billing_metadata, billing_period_start, billing_period_end,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                          $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23,
                          $24, $25)
                RETURNING *
            '''

            params = [
                billing_id,
                billing_record.user_id,
                billing_record.actor_user_id,
                (
                    billing_record.billing_account_type.value
                    if billing_record.billing_account_type
                    else None
                ),
                billing_record.billing_account_id,
                billing_record.organization_id,
                billing_record.agent_id,
                billing_record.subscription_id,
                billing_record.usage_record_id,
                billing_record.product_id,
                billing_record.service_type.value,
                float(billing_record.usage_amount),
                float(billing_record.unit_price),
                float(billing_record.total_amount),
                billing_record.currency.value,
                billing_record.billing_method.value,
                billing_record.billing_status.value,
                billing_record.wallet_transaction_id,
                billing_record.payment_transaction_id,
                billing_record.failure_reason,
                json.dumps(billing_record.billing_metadata) if billing_record.billing_metadata else "{}",
                billing_record.billing_period_start,
                billing_record.billing_period_end,
                now,
                now,
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_billing_record(results[0])
            else:
                raise Exception("Failed to create billing record")

        except Exception as e:
            logger.error(f"Error creating billing record: {e}", exc_info=True)
            raise

    async def get_billing_record(self, billing_id: str) -> Optional[BillingRecord]:
        """获取计费记录"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.billing_records_table}
                WHERE billing_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[billing_id])

            if result:
                return self._row_to_billing_record(result)
            return None

        except Exception as e:
            logger.error(f"Error getting billing record {billing_id}: {e}")
            raise

    async def update_billing_record_status(
        self,
        billing_id: str,
        status: BillingStatus,
        failure_reason: Optional[str] = None,
        wallet_transaction_id: Optional[str] = None,
        payment_transaction_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        billing_method: Optional[BillingMethod] = None,
    ) -> Optional[BillingRecord]:
        """更新计费记录状态"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.billing_records_table}
                SET billing_status = $1,
                    failure_reason = $2,
                    wallet_transaction_id = COALESCE($3, wallet_transaction_id),
                    payment_transaction_id = COALESCE($4, payment_transaction_id),
                    subscription_id = COALESCE($5, subscription_id),
                    billing_method = COALESCE($6, billing_method),
                    updated_at = $7
                WHERE billing_id = $8
                RETURNING *
            '''

            params = [
                status.value,
                failure_reason,
                wallet_transaction_id,
                payment_transaction_id,
                subscription_id,
                billing_method.value if billing_method else None,
                datetime.now(timezone.utc),
                billing_id,
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_billing_record(results[0])
            return None

        except Exception as e:
            logger.error(f"Error updating billing record status: {e}")
            raise

    async def get_user_billing_records(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        billing_account_type: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[BillingStatus] = None,
        service_type: Optional[ServiceType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[BillingRecord]:
        """获取用户的计费记录"""
        try:
            conditions = ["COALESCE(actor_user_id, user_id) = $1"]
            params = [user_id]
            param_count = 1

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if billing_account_type:
                param_count += 1
                conditions.append(f"billing_account_type = ${param_count}")
                params.append(billing_account_type)

            if billing_account_id:
                param_count += 1
                conditions.append(f"billing_account_id = ${param_count}")
                params.append(billing_account_id)

            if agent_id:
                param_count += 1
                conditions.append(f"agent_id = ${param_count}")
                params.append(agent_id)

            if product_id:
                param_count += 1
                conditions.append(f"product_id = ${param_count}")
                params.append(product_id)

            if start_date:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(end_date)

            if status:
                param_count += 1
                conditions.append(f"billing_status = ${param_count}")
                params.append(status.value)

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.billing_records_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_billing_record(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting user billing records: {e}")
            raise

    async def get_billing_records(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[BillingStatus] = None,
        service_type: Optional[ServiceType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BillingRecord]:
        """General billing records query with optional filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if start_date:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(end_date)

            if status:
                param_count += 1
                conditions.append(f"billing_status = ${param_count}")
                params.append(status.value)

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.billing_records_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_billing_record(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting billing records: {e}")
            raise

    async def count_billing_records(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[BillingStatus] = None,
        service_type: Optional[ServiceType] = None,
    ) -> int:
        """Count billing records matching filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if start_date:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(end_date)

            if status:
                param_count += 1
                conditions.append(f"billing_status = ${param_count}")
                params.append(status.value)

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT COUNT(*) as total FROM {self.schema}.{self.billing_records_table}
                {where_clause}
            '''

            async with self.db:
                result = await self.db.query_row(query, params=params)

            return result.get("total", 0) if result else 0

        except Exception as e:
            logger.error(f"Error counting billing records: {e}")
            raise

    async def get_user_quotas(
        self,
        user_id: str,
        service_type: Optional[ServiceType] = None,
    ) -> List[BillingQuota]:
        """Get all quotas for a user, optionally filtered by service type"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            # Current period filter
            now = datetime.now(timezone.utc)
            param_count += 1
            conditions.append(f"period_start <= ${param_count}")
            params.append(now)

            param_count += 1
            conditions.append(f"period_end >= ${param_count}")
            params.append(now)

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.billing_quotas_table}
                WHERE {where_clause}
                ORDER BY service_type
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_billing_quota(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting user quotas: {e}")
            return []

    # ====================
    # 计费事件管理
    # ====================

    async def create_billing_event(self, billing_event: BillingEvent) -> BillingEvent:
        """创建计费事件"""
        try:
            event_id = billing_event.event_id or f"evt_{uuid.uuid4().hex[:12]}"

            query = f'''
                INSERT INTO {self.schema}.{self.billing_events_table} (
                    event_id, event_type, billing_id, user_id, actor_user_id,
                    billing_account_type, billing_account_id, organization_id,
                    agent_id, event_data, service_type, amount, event_timestamp, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING *
            '''

            params = [
                event_id,
                billing_event.event_type.value,
                billing_event.billing_record_id,  # Maps to billing_id column
                billing_event.user_id,
                billing_event.actor_user_id,
                (
                    billing_event.billing_account_type.value
                    if billing_event.billing_account_type
                    else None
                ),
                billing_event.billing_account_id,
                billing_event.organization_id,
                billing_event.agent_id,
                json.dumps(billing_event.event_data) if billing_event.event_data else "{}",
                billing_event.service_type.value if billing_event.service_type else None,
                float(billing_event.amount) if billing_event.amount else None,
                billing_event.event_timestamp or datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_billing_event(results[0])
            else:
                raise Exception("Failed to create billing event")

        except Exception as e:
            logger.error(f"Error creating billing event: {e}", exc_info=True)
            raise

    async def claim_event_processing(
        self,
        claim_key: str,
        source_event_id: str,
        processor_id: str,
        stale_after_seconds: int = 300,
    ) -> bool:
        """Claim a billable event for processing unless it is already active or completed."""
        try:
            now = datetime.now(timezone.utc)
            stale_cutoff = now - timedelta(seconds=max(stale_after_seconds, 1))

            insert_query = f"""
                INSERT INTO {self.schema}.event_processing_claims (
                    claim_key,
                    source_event_id,
                    processing_status,
                    processor_id,
                    claimed_at,
                    completed_at,
                    last_error,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, 'processing', $3, $4, NULL, NULL, $4, $4)
                ON CONFLICT (claim_key) DO NOTHING
                RETURNING claim_key
            """

            async with self.db:
                inserted = await self.db.query_row(
                    insert_query,
                    params=[claim_key, source_event_id, processor_id, now],
                )
                if inserted:
                    return True

                reclaim_query = f"""
                    UPDATE {self.schema}.event_processing_claims
                    SET source_event_id = $2,
                        processing_status = 'processing',
                        processor_id = $3,
                        claimed_at = $4,
                        completed_at = NULL,
                        last_error = NULL,
                        updated_at = $4
                    WHERE claim_key = $1
                      AND processing_status <> 'completed'
                      AND (
                          processing_status = 'failed'
                          OR updated_at < $5
                      )
                    RETURNING claim_key
                """
                reclaimed = await self.db.query_row(
                    reclaim_query,
                    params=[claim_key, source_event_id, processor_id, now, stale_cutoff],
                )

            return bool(reclaimed)

        except Exception as e:
            logger.error("Error claiming billing event processing: %s", e, exc_info=True)
            raise

    async def mark_event_processing_completed(
        self,
        claim_key: str,
        source_event_id: str,
    ) -> None:
        """Mark a claimed event as completed."""
        try:
            query = f"""
                UPDATE {self.schema}.event_processing_claims
                SET source_event_id = $2,
                    processing_status = 'completed',
                    completed_at = $3,
                    last_error = NULL,
                    updated_at = $3
                WHERE claim_key = $1
            """

            completed_at = datetime.now(timezone.utc)
            async with self.db:
                await self.db.execute(query, params=[claim_key, source_event_id, completed_at])

        except Exception as e:
            logger.error("Error marking billing event processing completed: %s", e, exc_info=True)
            raise

    async def mark_event_processing_failed(
        self,
        claim_key: str,
        source_event_id: str,
        error_message: str,
    ) -> None:
        """Mark a claimed event as failed unless it already completed successfully."""
        try:
            query = f"""
                UPDATE {self.schema}.event_processing_claims
                SET source_event_id = $2,
                    processing_status = 'failed',
                    last_error = $3,
                    updated_at = $4
                WHERE claim_key = $1
                  AND processing_status <> 'completed'
            """

            failed_at = datetime.now(timezone.utc)
            async with self.db:
                await self.db.execute(
                    query,
                    params=[claim_key, source_event_id, error_message[:2000], failed_at],
                )

        except Exception as e:
            logger.error("Error marking billing event processing failed: %s", e, exc_info=True)
            raise

    # ====================
    # 使用量聚合
    # ====================

    async def get_usage_aggregations(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        billing_account_type: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        product_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        period_type: Optional[str] = None,
        limit: int = 100
    ) -> List[UsageAggregation]:
        """获取使用量聚合数据"""
        try:
            normalized_period_type, granularity = self._normalize_period_type(period_type)
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"COALESCE(actor_user_id, user_id) = ${param_count}")
                params.append(user_id)

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if billing_account_type:
                param_count += 1
                conditions.append(f"billing_account_type = ${param_count}")
                params.append(billing_account_type)

            if billing_account_id:
                param_count += 1
                conditions.append(f"billing_account_id = ${param_count}")
                params.append(billing_account_id)

            if agent_id:
                param_count += 1
                conditions.append(f"agent_id = ${param_count}")
                params.append(agent_id)

            if subscription_id:
                param_count += 1
                conditions.append(f"subscription_id = ${param_count}")
                params.append(subscription_id)

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            if product_id:
                param_count += 1
                conditions.append(f"product_id = ${param_count}")
                params.append(product_id)

            if period_start:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(period_start)

            if period_end:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(period_end)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT
                    date_trunc('{granularity}', created_at) AS period_start,
                    service_type,
                    product_id,
                    COUNT(*) AS total_usage_count,
                    COALESCE(SUM(usage_amount), 0) AS total_usage_amount,
                    COALESCE(SUM(total_amount), 0) AS total_cost
                FROM {self.schema}.{self.billing_records_table}
                {where_clause}
                GROUP BY 1, service_type, product_id
                ORDER BY period_start DESC, service_type, product_id
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            period_rows: Dict[datetime, Dict[str, Any]] = {}
            period_order: List[datetime] = []

            for row in results or []:
                current_period_start = row.get("period_start")
                if current_period_start not in period_rows:
                    if len(period_order) >= limit:
                        break
                    period_order.append(current_period_start)
                    period_rows[current_period_start] = {
                        "total_usage_count": 0,
                        "total_usage_amount": Decimal("0"),
                        "total_cost": Decimal("0"),
                        "service_breakdown": {},
                    }

                bucket = period_rows[current_period_start]
                usage_count = int(row.get("total_usage_count") or 0)
                usage_amount = Decimal(str(row.get("total_usage_amount") or 0))
                total_cost = Decimal(str(row.get("total_cost") or 0))
                row_service_type = row.get("service_type") or ServiceType.OTHER.value
                row_product_id = row.get("product_id")

                bucket["total_usage_count"] += usage_count
                bucket["total_usage_amount"] += usage_amount
                bucket["total_cost"] += total_cost

                service_bucket = bucket["service_breakdown"].setdefault(
                    row_service_type,
                    {
                        "usage_count": 0,
                        "usage_amount": 0.0,
                        "total_cost": 0.0,
                        "products": {},
                    },
                )
                service_bucket["usage_count"] += usage_count
                service_bucket["usage_amount"] += float(usage_amount)
                service_bucket["total_cost"] += float(total_cost)

                if row_product_id:
                    product_bucket = service_bucket["products"].setdefault(
                        row_product_id,
                        {
                            "usage_count": 0,
                            "usage_amount": 0.0,
                            "total_cost": 0.0,
                        },
                    )
                    product_bucket["usage_count"] += usage_count
                    product_bucket["usage_amount"] += float(usage_amount)
                    product_bucket["total_cost"] += float(total_cost)

            aggregations = []
            aggregation_account_type = None
            if billing_account_type:
                try:
                    aggregation_account_type = BillingAccountType(billing_account_type)
                except ValueError:
                    aggregation_account_type = None
            for current_period_start in period_order:
                bucket = period_rows[current_period_start]
                aggregations.append(
                    UsageAggregation(
                        aggregation_id=(
                            f"agg_{normalized_period_type}_"
                            f"{current_period_start.strftime('%Y%m%d%H%M%S')}"
                        ),
                        user_id=user_id,
                        actor_user_id=user_id,
                        organization_id=organization_id,
                        billing_account_type=aggregation_account_type,
                        billing_account_id=billing_account_id,
                        agent_id=agent_id,
                        subscription_id=subscription_id,
                        service_type=service_type,
                        product_id=product_id,
                        period_start=current_period_start,
                        period_end=self._get_period_end(
                            current_period_start,
                            normalized_period_type,
                        ),
                        period_type=normalized_period_type,
                        total_usage_count=bucket["total_usage_count"],
                        total_usage_amount=bucket["total_usage_amount"],
                        total_usage=bucket["total_usage_amount"],
                        total_cost=bucket["total_cost"],
                        service_breakdown=bucket["service_breakdown"],
                    )
                )

            return aggregations

        except Exception as e:
            logger.error(f"Error getting usage aggregations: {e}")
            return []

    # ====================
    # 配额管理
    # ====================

    async def get_billing_quota(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        product_id: Optional[str] = None
    ) -> Optional[BillingQuota]:
        """获取计费配额"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if subscription_id:
                param_count += 1
                conditions.append(f"subscription_id = ${param_count}")
                params.append(subscription_id)

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            if product_id:
                param_count += 1
                conditions.append(f"product_id = ${param_count}")
                params.append(product_id)

            # Add current period filter
            now = datetime.now(timezone.utc)
            param_count += 1
            conditions.append(f"period_start <= ${param_count}")
            params.append(now)

            param_count += 1
            conditions.append(f"period_end >= ${param_count}")
            params.append(now)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.billing_quotas_table}
                WHERE {where_clause}
                LIMIT 1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=params)

            if result:
                return self._row_to_billing_quota(result)
            return None

        except Exception as e:
            logger.error(f"Error getting billing quota: {e}")
            return None

    async def get_user_quotas(
        self,
        user_id: str,
        service_type: Optional[ServiceType] = None,
    ) -> List[BillingQuota]:
        """获取用户的所有配额"""
        try:
            conditions = ["user_id = $1", "is_active = true"]
            params: list = [user_id]
            param_count = 1

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.billing_quotas_table}
                WHERE {where_clause}
                ORDER BY service_type
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_billing_quota(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting user quotas: {e}")
            return []

    async def list_billing_records(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        billing_account_type: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        product_id: Optional[str] = None,
        status: Optional[BillingStatus] = None,
        service_type: Optional[ServiceType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[BillingRecord], int]:
        """获取计费记录列表（支持分页和过滤）"""
        try:
            conditions: list[str] = []
            params: list = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"COALESCE(actor_user_id, user_id) = ${param_count}")
                params.append(user_id)

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if billing_account_type:
                param_count += 1
                conditions.append(f"billing_account_type = ${param_count}")
                params.append(billing_account_type)

            if billing_account_id:
                param_count += 1
                conditions.append(f"billing_account_id = ${param_count}")
                params.append(billing_account_id)

            if agent_id:
                param_count += 1
                conditions.append(f"agent_id = ${param_count}")
                params.append(agent_id)

            if product_id:
                param_count += 1
                conditions.append(f"product_id = ${param_count}")
                params.append(product_id)

            if status:
                param_count += 1
                conditions.append(f"billing_status = ${param_count}")
                params.append(status.value)

            if service_type:
                param_count += 1
                conditions.append(f"service_type = ${param_count}")
                params.append(service_type.value)

            if start_date:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Count total
            count_query = f'''
                SELECT COUNT(*) as total
                FROM {self.schema}.{self.billing_records_table}
                {where_clause}
            '''

            async with self.db:
                count_result = await self.db.query_row(count_query, params=params)
            total = count_result.get("total", 0) if count_result else 0

            # Fetch records
            query = f'''
                SELECT * FROM {self.schema}.{self.billing_records_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            records = [self._row_to_billing_record(row) for row in results] if results else []
            return records, total

        except Exception as e:
            logger.error(f"Error listing billing records: {e}")
            raise

    # ====================
    # 统计和报告
    # ====================

    async def get_billing_statistics(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取计费统计"""
        return await self.get_billing_stats(user_id, organization_id, start_date, end_date)

    async def get_billing_stats(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取计费统计数据"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if start_date:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN billing_status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN billing_status = 'failed' THEN 1 END) as failed_count,
                    COUNT(CASE WHEN billing_status = 'pending' THEN 1 END) as pending_count,
                    COALESCE(SUM(total_amount), 0) as total_amount,
                    COALESCE(SUM(CASE WHEN billing_status = 'completed' THEN total_amount ELSE 0 END), 0) as completed_amount
                FROM {self.schema}.{self.billing_records_table}
                {where_clause}
            '''

            async with self.db:
                result = await self.db.query_row(query, params=params)

            if result:
                return {
                    "total_billing_records": result.get("total_records", 0),
                    "completed_billing_records": result.get("completed_count", 0),
                    "failed_billing_records": result.get("failed_count", 0),
                    "pending_billing_records": result.get("pending_count", 0),
                    "total_revenue": float(result.get("completed_amount", 0)),
                    "revenue_by_service": {},
                    "revenue_by_method": {},
                    "active_users": 0,
                    "period_start": start_date if start_date else datetime.now() - timedelta(days=30),
                    "period_end": end_date if end_date else datetime.now()
                }

            return {
                "total_billing_records": 0,
                "completed_billing_records": 0,
                "failed_billing_records": 0,
                "pending_billing_records": 0,
                "total_revenue": 0.0,
                "revenue_by_service": {},
                "revenue_by_method": {},
                "active_users": 0,
                "period_start": start_date if start_date else datetime.now() - timedelta(days=30),
                "period_end": end_date if end_date else datetime.now()
            }

        except Exception as e:
            logger.error(f"Error getting billing statistics: {e}")
            return {
                "total_records": 0,
                "completed_count": 0,
                "failed_count": 0,
                "pending_count": 0,
                "total_amount": 0.0,
                "completed_amount": 0.0
            }

    # ====================
    # Helper Methods
    # ====================

    def _row_to_billing_record(self, row: Dict[str, Any]) -> BillingRecord:
        """Convert database row to BillingRecord model"""
        return BillingRecord(
            id=row.get("id"),
            billing_id=row.get("billing_id"),
            user_id=row.get("user_id"),
            actor_user_id=row.get("actor_user_id") or row.get("user_id"),
            billing_account_type=(
                BillingAccountType(row.get("billing_account_type"))
                if row.get("billing_account_type")
                else None
            ),
            billing_account_id=row.get("billing_account_id"),
            organization_id=row.get("organization_id"),
            agent_id=row.get("agent_id"),
            subscription_id=row.get("subscription_id"),
            usage_record_id=row.get("usage_record_id"),
            product_id=row.get("product_id"),
            service_type=ServiceType(row.get("service_type")),
            usage_amount=Decimal(str(row.get("usage_amount", 0))),
            unit_price=Decimal(str(row.get("unit_price", 0))),
            total_amount=Decimal(str(row.get("total_amount", 0))),
            currency=Currency(row.get("currency", "USD")),
            billing_method=BillingMethod(row.get("billing_method")),
            billing_status=BillingStatus(row.get("billing_status")),
            wallet_transaction_id=row.get("wallet_transaction_id"),
            payment_transaction_id=row.get("payment_transaction_id"),
            failure_reason=row.get("failure_reason"),
            billing_metadata=row.get("billing_metadata", {}) if isinstance(row.get("billing_metadata"), dict) else json.loads(row.get("billing_metadata", "{}")),
            billing_period_start=row.get("billing_period_start"),
            billing_period_end=row.get("billing_period_end"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    def _row_to_billing_event(self, row: Dict[str, Any]) -> BillingEvent:
        """Convert database row to BillingEvent model"""
        return BillingEvent(
            id=row.get("id"),
            event_id=row.get("event_id"),
            event_type=EventType(row.get("event_type")),
            event_source="billing_service",  # Default source
            billing_record_id=row.get("billing_id"),  # billing_id maps to billing_record_id in model
            user_id=row.get("user_id"),
            actor_user_id=row.get("actor_user_id") or row.get("user_id"),
            billing_account_type=(
                BillingAccountType(row.get("billing_account_type"))
                if row.get("billing_account_type")
                else None
            ),
            billing_account_id=row.get("billing_account_id"),
            organization_id=row.get("organization_id"),
            agent_id=row.get("agent_id"),
            service_type=ServiceType(row.get("service_type")) if row.get("service_type") else None,
            event_data=row.get("event_data", {}) if isinstance(row.get("event_data"), dict) else json.loads(row.get("event_data", "{}")),
            amount=Decimal(str(row.get("amount"))) if row.get("amount") is not None else None,
            currency=None,  # Not stored in billing schema
            event_timestamp=row.get("event_timestamp"),
            created_at=row.get("created_at")
        )

    def _row_to_billing_quota(self, row: Dict[str, Any]) -> BillingQuota:
        """Convert database row to BillingQuota model"""
        return BillingQuota(
            id=row.get("id"),
            quota_id=row.get("quota_id"),
            user_id=row.get("user_id"),
            organization_id=row.get("organization_id"),
            service_type=ServiceType(row.get("service_type")),
            quota_limit=Decimal(str(row.get("quota_limit", 0))),
            quota_used=Decimal(str(row.get("quota_used", 0))),
            quota_remaining=Decimal(str(row.get("quota_remaining", 0))),
            period_start=row.get("period_start"),
            period_end=row.get("period_end"),
            reset_frequency=row.get("reset_frequency"),
            metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else json.loads(row.get("metadata", "{}")),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    def _normalize_period_type(self, period_type: Optional[str]) -> Tuple[str, str]:
        normalized = (period_type or "daily").strip().lower()
        alias_map = {
            "hour": "hourly",
            "hourly": "hourly",
            "day": "daily",
            "daily": "daily",
            "week": "weekly",
            "weekly": "weekly",
            "month": "monthly",
            "monthly": "monthly",
        }
        normalized = alias_map.get(normalized)
        if not normalized:
            raise ValueError(f"Unsupported period_type: {period_type}")

        granularity_map = {
            "hourly": "hour",
            "daily": "day",
            "weekly": "week",
            "monthly": "month",
        }
        return normalized, granularity_map[normalized]

    def _get_period_end(self, period_start: datetime, period_type: str) -> datetime:
        if period_type == "hourly":
            return period_start + timedelta(hours=1)
        if period_type == "daily":
            return period_start + timedelta(days=1)
        if period_type == "weekly":
            return period_start + timedelta(weeks=1)
        if period_type == "monthly":
            if period_start.month == 12:
                return period_start.replace(year=period_start.year + 1, month=1)
            return period_start.replace(month=period_start.month + 1)
        raise ValueError(f"Unsupported period_type: {period_type}")


__all__ = ["BillingRepository"]
