"""
Billing Service Data Repository

数据访问层 - PostgreSQL + gRPC (Async)
"""

import logging
import os
import sys
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    BillingRecord, BillingEvent, UsageAggregation, BillingQuota,
    BillingStatus, BillingMethod, EventType, ServiceType, Currency
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
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="billing_service"
        )
        self.schema = "billing"
        self.billing_records_table = "billing_records"
        self.billing_events_table = "billing_events"
        self.usage_aggregations_table = "usage_aggregations"
        self.billing_quotas_table = "billing_quotas"

    async def initialize(self):
        """初始化数据库连接"""
        logger.info("Billing repository initialized with PostgreSQL")

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
                    billing_id, user_id, organization_id, subscription_id, usage_record_id,
                    product_id, service_type, usage_amount, unit_price, total_amount,
                    currency, billing_method, billing_status,
                    wallet_transaction_id, payment_transaction_id, failure_reason,
                    billing_metadata, billing_period_start, billing_period_end,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                          $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                RETURNING *
            '''

            params = [
                billing_id,
                billing_record.user_id,
                billing_record.organization_id,
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
                now
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
        payment_transaction_id: Optional[str] = None
    ) -> Optional[BillingRecord]:
        """更新计费记录状态"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.billing_records_table}
                SET billing_status = $1,
                    failure_reason = $2,
                    wallet_transaction_id = COALESCE($3, wallet_transaction_id),
                    payment_transaction_id = COALESCE($4, payment_transaction_id),
                    updated_at = $5
                WHERE billing_id = $6
                RETURNING *
            '''

            params = [
                status.value,
                failure_reason,
                wallet_transaction_id,
                payment_transaction_id,
                datetime.now(timezone.utc),
                billing_id
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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[BillingStatus] = None,
        service_type: Optional[ServiceType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[BillingRecord]:
        """获取用户的计费记录"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

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

    # ====================
    # 计费事件管理
    # ====================

    async def create_billing_event(self, billing_event: BillingEvent) -> BillingEvent:
        """创建计费事件"""
        try:
            event_id = billing_event.event_id or f"evt_{uuid.uuid4().hex[:12]}"

            query = f'''
                INSERT INTO {self.schema}.{self.billing_events_table} (
                    event_id, event_type, billing_id, user_id, organization_id,
                    event_data, service_type, amount, event_timestamp, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
            '''

            params = [
                event_id,
                billing_event.event_type.value,
                billing_event.billing_record_id,  # Maps to billing_id column
                billing_event.user_id,
                billing_event.organization_id,
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

    # ====================
    # 使用量聚合
    # ====================

    async def get_usage_aggregations(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        period_type: Optional[str] = None,
        limit: int = 100
    ) -> List[UsageAggregation]:
        """获取使用量聚合数据"""
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

            if period_start:
                param_count += 1
                conditions.append(f"period_start >= ${param_count}")
                params.append(period_start)

            if period_end:
                param_count += 1
                conditions.append(f"period_end <= ${param_count}")
                params.append(period_end)

            if period_type:
                param_count += 1
                conditions.append(f"period_type = ${param_count}")
                params.append(period_type)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.usage_aggregations_table}
                {where_clause}
                ORDER BY period_start DESC
                LIMIT ${param_count + 1}
            '''

            params.append(limit)

            async with self.db:
                results = await self.db.query(query, params=params)

            # Convert to UsageAggregation objects
            aggregations = []
            if results:
                for row in results:
                    aggregations.append(UsageAggregation(
                        aggregation_id=row.get("aggregation_id"),
                        user_id=row.get("user_id"),
                        organization_id=row.get("organization_id"),
                        service_type=ServiceType(row.get("service_type")),
                        period_start=row.get("period_start"),
                        period_end=row.get("period_end"),
                        total_usage=Decimal(str(row.get("total_usage", 0))),
                        total_cost=Decimal(str(row.get("total_cost", 0))),
                        currency=Currency(row.get("currency", "USD")),
                        usage_breakdown=row.get("usage_breakdown", {})
                    ))

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
            organization_id=row.get("organization_id"),
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
            billing_metadata=row.get("billing_metadata", {}),
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
            organization_id=row.get("organization_id"),
            service_type=ServiceType(row.get("service_type")) if row.get("service_type") else None,
            event_data=row.get("event_data", {}),
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
            metadata=row.get("metadata", {}),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )


__all__ = ["BillingRepository"]
