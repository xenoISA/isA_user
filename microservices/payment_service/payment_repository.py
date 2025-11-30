"""
Payment Repository

数据访问层，处理支付、订阅、账单、退款等数据库操作
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

# Database client setup
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    SubscriptionPlan, Subscription, Payment, Invoice, Refund, PaymentMethodInfo,
    PaymentStatus, SubscriptionStatus, InvoiceStatus, RefundStatus,
    SubscriptionTier, BillingCycle, Currency, PaymentMethod
)

logger = logging.getLogger(__name__)


class PaymentRepository:
    """支付数据访问仓库"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """初始化 Payment Repository"""
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("payment_service")

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
            user_id="payment_service"
        )

        # Schema and table names
        self.schema = "payment"
        self.plans_table = "subscription_plans"
        self.subscriptions_table = "subscriptions"
        self.payments_table = "transactions"
        self.invoices_table = "invoices"
        self.refunds_table = "refunds"
        self.payment_methods_table = "payment_methods"

        logger.info("PaymentRepository initialized with PostgresClient")

    # ====================
    # 连接管理
    # ====================

    async def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            query = f"SELECT 1 FROM {self.schema}.{self.subscriptions_table} LIMIT 1"
            async with self.db:
                result = await self.db.query(query, [], schema=self.schema)
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False

    # ====================
    # 订阅计划管理
    # ====================

    async def create_subscription_plan(self, plan: SubscriptionPlan) -> Optional[SubscriptionPlan]:
        """创建订阅计划"""
        try:
            data = {
                "plan_id": plan.plan_id or f"plan_{uuid.uuid4().hex[:8]}",
                "name": plan.name,
                "description": plan.description,
                "tier": plan.tier.value,
                "price_usd": float(plan.price),
                "currency": plan.currency.value,
                "billing_cycle": plan.billing_cycle.value,
                "features": plan.features or {},  # Direct dict, not json.dumps
                "credits_included": plan.credits_included,
                "max_users": plan.max_users,
                "max_storage_gb": plan.max_storage_gb,
                "trial_days": plan.trial_days,
                "stripe_price_id": plan.stripe_price_id,
                "stripe_product_id": plan.stripe_product_id,
                "is_active": plan.is_active,
                "is_public": plan.is_public,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            async with self.db:
                count = await self.db.insert_into(self.plans_table, [data], schema=self.schema)

            # Check return value for None
            if count is not None and count > 0:
                return await self.get_subscription_plan(data["plan_id"])

            # If count is None or 0, check if plan exists (might be ON CONFLICT)
            return await self.get_subscription_plan(data["plan_id"])

        except Exception as e:
            logger.error(f"创建订阅计划失败: {e}")
            return None

    async def get_subscription_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """获取订阅计划"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.plans_table}
                WHERE plan_id = $1 AND is_active = true
            """

            async with self.db:
                result = await self.db.query_row(query, [plan_id], schema=self.schema)

            if result:
                return self._convert_to_subscription_plan(result)
            return None

        except Exception as e:
            logger.error(f"获取订阅计划失败: {e}")
            return None

    async def list_subscription_plans(
        self,
        tier: Optional[SubscriptionTier] = None,
        is_public: bool = True
    ) -> List[SubscriptionPlan]:
        """列出订阅计划"""
        try:
            conditions = ["is_active = $1", "is_public = $2"]
            params = [True, is_public]
            param_count = 2

            if tier:
                param_count += 1
                conditions.append(f"tier = ${param_count}")
                params.append(tier.value)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.plans_table}
                WHERE {where_clause}
                ORDER BY price_usd ASC
            """

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            if results:
                return [self._convert_to_subscription_plan(plan) for plan in results]
            return []

        except Exception as e:
            logger.error(f"列出订阅计划失败: {e}")
            return []

    # ====================
    # 订阅管理
    # ====================

    async def create_subscription(self, subscription: Subscription) -> Optional[Subscription]:
        """创建订阅"""
        try:
            data = {
                "subscription_id": subscription.subscription_id or f"sub_{uuid.uuid4().hex[:8]}",
                "user_id": subscription.user_id,
                "organization_id": subscription.organization_id,
                "plan_id": subscription.plan_id,
                "status": subscription.status.value,
                "tier": subscription.tier.value,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat(),
                "billing_cycle": subscription.billing_cycle.value,
                "trial_start": subscription.trial_start.isoformat() if subscription.trial_start else None,
                "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": subscription.canceled_at.isoformat() if subscription.canceled_at else None,
                "cancellation_reason": subscription.cancellation_reason,
                "payment_method_id": subscription.payment_method_id,
                "last_payment_date": subscription.last_payment_date.isoformat() if subscription.last_payment_date else None,
                "next_payment_date": subscription.next_payment_date.isoformat() if subscription.next_payment_date else None,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "stripe_customer_id": subscription.stripe_customer_id,
                "metadata": subscription.metadata or {},  # Direct dict
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            async with self.db:
                count = await self.db.insert_into(self.subscriptions_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_subscription(data["subscription_id"])

            return await self.get_subscription(data["subscription_id"])

        except Exception as e:
            logger.error(f"创建订阅失败: {e}")
            return None

    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户当前订阅"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.subscriptions_table}
                WHERE user_id = $1
                  AND status IN ('active', 'trialing', 'past_due')
                ORDER BY created_at DESC
                LIMIT 1
            """

            async with self.db:
                result = await self.db.query_row(query, [user_id], schema=self.schema)

            if result:
                return self._convert_to_subscription(result)
            return None

        except Exception as e:
            logger.error(f"获取用户订阅失败: {e}")
            return None

    async def update_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Subscription]:
        """更新订阅"""
        try:
            # Add updated_at
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Handle enum values
            if "status" in updates and hasattr(updates["status"], "value"):
                updates["status"] = updates["status"].value
            if "tier" in updates and hasattr(updates["tier"], "value"):
                updates["tier"] = updates["tier"].value

            # Handle metadata - direct dict, not json.dumps
            if "metadata" in updates and isinstance(updates["metadata"], dict):
                # Keep as dict, PostgresClient will handle serialization
                pass

            # Build SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add WHERE condition
            param_count += 1
            params.append(subscription_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.subscriptions_table}
                SET {set_clause}
                WHERE subscription_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is not None and count > 0:
                return await self.get_subscription(subscription_id)
            return None

        except Exception as e:
            logger.error(f"更新订阅失败: {e}")
            return None

    async def get_user_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户当前激活的订阅"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.subscriptions_table}
                WHERE user_id = $1
                  AND status IN ($2, $3)
                ORDER BY created_at DESC
                LIMIT 1
            """

            async with self.db:
                result = await self.db.query_row(
                    query,
                    [user_id, SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value],
                    schema=self.schema
                )

            if result:
                return self._convert_to_subscription(result)
            return None

        except Exception as e:
            logger.error(f"获取用户激活订阅失败: {e}")
            return None

    async def get_user_default_payment_method(self, user_id: str) -> Optional[PaymentMethodInfo]:
        """获取用户默认支付方式"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.payment_methods_table}
                WHERE user_id = $1 AND is_default = true
                LIMIT 1
            """

            async with self.db:
                result = await self.db.query_row(query, [user_id], schema=self.schema)

            if result:
                return self._convert_to_payment_method(result)
            return None

        except Exception as e:
            logger.error(f"获取用户默认支付方式失败: {e}")
            return None

    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """获取订阅"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.subscriptions_table}
                WHERE subscription_id = $1
            """

            async with self.db:
                result = await self.db.query_row(query, [subscription_id], schema=self.schema)

            if result:
                return self._convert_to_subscription(result)
            return None

        except Exception as e:
            logger.error(f"获取订阅失败: {e}")
            return None

    async def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False,
        reason: Optional[str] = None
    ) -> Optional[Subscription]:
        """取消订阅"""
        try:
            updates = {
                "canceled_at": datetime.now(timezone.utc).isoformat(),
                "cancellation_reason": reason,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if immediate:
                updates["status"] = SubscriptionStatus.CANCELED.value
            else:
                updates["cancel_at_period_end"] = True

            # Build SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(subscription_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.subscriptions_table}
                SET {set_clause}
                WHERE subscription_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is not None and count > 0:
                return await self.get_subscription(subscription_id)
            return None

        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            return None

    # ====================
    # 支付管理
    # ====================

    async def create_payment(self, payment: Payment) -> Optional[Payment]:
        """创建支付记录"""
        try:
            data = {
                "payment_id": payment.payment_id or f"pay_{uuid.uuid4().hex[:8]}",
                "user_id": payment.user_id,
                "organization_id": payment.organization_id,
                "amount": float(payment.amount),
                "currency": payment.currency.value,
                "description": payment.description,
                "status": payment.status.value,
                "payment_method": payment.payment_method.value,
                "subscription_id": payment.subscription_id,
                "invoice_id": payment.invoice_id,
                "processor": payment.processor,
                "processor_payment_id": payment.processor_payment_id,
                "processor_response": payment.processor_response or {},  # Direct dict
                "failure_reason": payment.failure_reason,
                "failure_code": payment.failure_code,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "failed_at": payment.failed_at.isoformat() if payment.failed_at else None
            }

            async with self.db:
                count = await self.db.insert_into(self.payments_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_payment(data["payment_id"])

            return await self.get_payment(data["payment_id"])

        except Exception as e:
            logger.error(f"创建支付记录失败: {e}")
            return None

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """获取支付记录"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.payments_table}
                WHERE payment_id = $1
            """

            async with self.db:
                result = await self.db.query_row(query, [payment_id], schema=self.schema)

            if result:
                return self._convert_to_payment(result)
            return None

        except Exception as e:
            logger.error(f"获取支付记录失败: {e}")
            return None

    async def update_payment_status(
        self,
        payment_id: str,
        status: PaymentStatus,
        processor_response: Optional[Dict[str, Any]] = None
    ) -> Optional[Payment]:
        """更新支付状态"""
        try:
            updates = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if status == PaymentStatus.SUCCEEDED:
                updates["paid_at"] = datetime.now(timezone.utc).isoformat()
            elif status == PaymentStatus.FAILED:
                if processor_response:
                    updates["failure_reason"] = processor_response.get("failure_reason")
                    updates["failure_code"] = processor_response.get("failure_code")
                updates["failed_at"] = datetime.now(timezone.utc).isoformat()

            if processor_response:
                updates["processor_response"] = processor_response  # Direct dict

            # Build SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(payment_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.payments_table}
                SET {set_clause}
                WHERE payment_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is not None and count > 0:
                return await self.get_payment(payment_id)
            return None

        except Exception as e:
            logger.error(f"更新支付状态失败: {e}")
            return None

    async def get_user_payments(
        self,
        user_id: str,
        limit: int = 10,
        status: Optional[PaymentStatus] = None
    ) -> List[Payment]:
        """获取用户支付历史"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.payments_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit}
            """

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            if results:
                return [self._convert_to_payment(payment) for payment in results]
            return []

        except Exception as e:
            logger.error(f"获取用户支付历史失败: {e}")
            return []

    # ====================
    # 发票管理
    # ====================

    async def create_invoice(self, invoice: Invoice) -> Optional[Invoice]:
        """创建发票"""
        try:
            data = {
                "invoice_id": invoice.invoice_id or f"inv_{uuid.uuid4().hex[:8]}",
                "invoice_number": invoice.invoice_number,
                "user_id": invoice.user_id,
                "organization_id": invoice.organization_id,
                "subscription_id": invoice.subscription_id,
                "status": invoice.status.value,
                "amount_total": float(invoice.amount_total),
                "amount_paid": float(invoice.amount_paid),
                "amount_due": float(invoice.amount_due),
                "currency": invoice.currency.value,
                "billing_period_start": invoice.billing_period_start.isoformat(),
                "billing_period_end": invoice.billing_period_end.isoformat(),
                "payment_method_id": invoice.payment_method_id,
                "payment_intent_id": invoice.payment_intent_id,
                "line_items": invoice.line_items or [],  # Direct list
                "stripe_invoice_id": invoice.stripe_invoice_id,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            async with self.db:
                count = await self.db.insert_into(self.invoices_table, [data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_invoice(data["invoice_id"])

            return await self.get_invoice(data["invoice_id"])

        except Exception as e:
            logger.error(f"创建发票失败: {e}")
            return None

    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """获取发票"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.invoices_table}
                WHERE invoice_id = $1
            """

            async with self.db:
                result = await self.db.query_row(query, [invoice_id], schema=self.schema)

            if result:
                return self._convert_to_invoice(result)
            return None

        except Exception as e:
            logger.error(f"获取发票失败: {e}")
            return None

    async def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_intent_id: str
    ) -> Optional[Invoice]:
        """标记发票为已支付"""
        try:
            updates = {
                "status": InvoiceStatus.PAID.value,
                "payment_intent_id": payment_intent_id,
                "paid_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # Build SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(invoice_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.invoices_table}
                SET {set_clause}
                WHERE invoice_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is not None and count > 0:
                return await self.get_invoice(invoice_id)
            return None

        except Exception as e:
            logger.error(f"标记发票已支付失败: {e}")
            return None

    # ====================
    # 退款管理
    # ====================

    async def create_refund(self, refund: Refund) -> Optional[Refund]:
        """创建退款"""
        try:
            data = {
                "refund_id": refund.refund_id or f"ref_{uuid.uuid4().hex[:8]}",
                "payment_id": refund.payment_id,
                "user_id": refund.user_id,
                "amount": float(refund.amount),
                "currency": refund.currency.value,
                "reason": refund.reason,
                "status": refund.status.value,
                "processor": refund.processor,
                "processor_refund_id": refund.processor_refund_id,
                "processor_response": refund.processor_response or {},  # Direct dict
                "requested_by": refund.requested_by,
                "approved_by": refund.approved_by,
                "requested_at": refund.requested_at.isoformat(),
                "processed_at": refund.processed_at.isoformat() if refund.processed_at else None,
                "completed_at": refund.completed_at.isoformat() if refund.completed_at else None
            }

            async with self.db:
                count = await self.db.insert_into(self.refunds_table, [data], schema=self.schema)

            if count is not None and count > 0:
                query = f"SELECT * FROM {self.schema}.{self.refunds_table} WHERE refund_id = $1"
                async with self.db:
                    result = await self.db.query_row(query, [data["refund_id"]], schema=self.schema)
                if result:
                    return self._convert_to_refund(result)

            return None

        except Exception as e:
            logger.error(f"创建退款失败: {e}")
            return None

    async def update_refund_status(self, refund_id: str, status: RefundStatus) -> bool:
        """更新退款状态"""
        try:
            updates = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if status == RefundStatus.PROCESSING:
                updates["processed_at"] = datetime.now(timezone.utc).isoformat()
            elif status == RefundStatus.SUCCEEDED:
                updates["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Build SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(refund_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.refunds_table}
                SET {set_clause}
                WHERE refund_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"更新退款状态失败: {e}")
            return False

    async def process_refund(
        self,
        refund_id: str,
        approved_by: Optional[str] = None
    ) -> Optional[Refund]:
        """处理退款"""
        try:
            updates = {
                "status": RefundStatus.SUCCEEDED.value,
                "approved_by": approved_by,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat()
            }

            # Build SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(refund_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.refunds_table}
                SET {set_clause}
                WHERE refund_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is not None and count > 0:
                # Fetch the updated refund
                fetch_query = f"SELECT * FROM {self.schema}.{self.refunds_table} WHERE refund_id = $1"
                async with self.db:
                    result = await self.db.query_row(fetch_query, [refund_id], schema=self.schema)
                if result:
                    return self._convert_to_refund(result)

            logger.error(f"Refund not found: {refund_id}")
            return None

        except Exception as e:
            logger.error(f"处理退款失败: {e}", exc_info=True)
            return None

    # ====================
    # 支付方式管理
    # ====================

    async def save_payment_method(self, method: PaymentMethodInfo) -> Optional[PaymentMethodInfo]:
        """保存支付方式"""
        try:
            data = {
                "method_id": str(uuid.uuid4()),
                "user_id": method.user_id,
                "method_type": method.method_type.value,
                "card_brand": method.card_brand,
                "card_last4": method.card_last4,
                "card_exp_month": method.card_exp_month,
                "card_exp_year": method.card_exp_year,
                "bank_name": method.bank_name,
                "bank_account_last4": method.bank_account_last4,
                "external_account_id": method.external_account_id,
                "stripe_payment_method_id": method.stripe_payment_method_id,
                "is_default": method.is_default,
                "is_verified": method.is_verified,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            async with self.db:
                count = await self.db.insert_into(self.payment_methods_table, [data], schema=self.schema)

            if count is not None and count > 0:
                query = f"SELECT * FROM {self.schema}.{self.payment_methods_table} WHERE method_id = $1"
                async with self.db:
                    result = await self.db.query_row(query, [data["method_id"]], schema=self.schema)
                if result:
                    return self._convert_to_payment_method(result)

            return None

        except Exception as e:
            logger.error(f"保存支付方式失败: {e}")
            return None

    async def get_user_payment_methods(self, user_id: str) -> List[PaymentMethodInfo]:
        """获取用户支付方式"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.payment_methods_table}
                WHERE user_id = $1
                ORDER BY is_default DESC, created_at DESC
            """

            async with self.db:
                results = await self.db.query(query, [user_id], schema=self.schema)

            if results:
                return [self._convert_to_payment_method(method) for method in results]
            return []

        except Exception as e:
            logger.error(f"获取用户支付方式失败: {e}")
            return []

    # ====================
    # 统计和分析
    # ====================

    async def get_revenue_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取收入统计"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            query = f"""
                SELECT amount, created_at
                FROM {self.schema}.{self.payments_table}
                WHERE status = $1 AND created_at >= $2
            """

            async with self.db:
                results = await self.db.query(
                    query,
                    [PaymentStatus.SUCCEEDED.value, start_date.isoformat()],
                    schema=self.schema
                )

            if results:
                total_revenue = sum(float(p.get("amount", 0)) for p in results)
                payment_count = len(results)

                # Daily revenue calculation
                daily_revenue = {}
                for payment in results:
                    created_at_str = payment.get("created_at")
                    if created_at_str:
                        date = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')).date()
                        date_str = date.isoformat()
                        daily_revenue[date_str] = daily_revenue.get(date_str, 0) + float(payment.get("amount", 0))

                return {
                    "total_revenue": total_revenue,
                    "payment_count": payment_count,
                    "average_payment": total_revenue / payment_count if payment_count > 0 else 0,
                    "daily_revenue": daily_revenue,
                    "period_days": days
                }

            return {
                "total_revenue": 0,
                "payment_count": 0,
                "average_payment": 0,
                "daily_revenue": {},
                "period_days": days
            }

        except Exception as e:
            logger.error(f"获取收入统计失败: {e}")
            return {}

    async def get_subscription_statistics(self) -> Dict[str, Any]:
        """获取订阅统计"""
        try:
            # Active subscriptions
            active_query = f"""
                SELECT COUNT(*) as count FROM {self.schema}.{self.subscriptions_table}
                WHERE status IN ('active', 'trialing')
            """

            async with self.db:
                active_result = await self.db.query_row(active_query, [], schema=self.schema)

            active_count = int(active_result.get("count", 0)) if active_result else 0

            # Tier distribution
            tier_stats = {}
            for tier in SubscriptionTier:
                tier_query = f"""
                    SELECT COUNT(*) as count FROM {self.schema}.{self.subscriptions_table}
                    WHERE tier = $1 AND status IN ('active', 'trialing')
                """
                async with self.db:
                    tier_result = await self.db.query_row(tier_query, [tier.value], schema=self.schema)
                tier_stats[tier.value] = int(tier_result.get("count", 0)) if tier_result else 0

            # Churn rate
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            canceled_query = f"""
                SELECT COUNT(*) as count FROM {self.schema}.{self.subscriptions_table}
                WHERE status = $1 AND canceled_at >= $2
            """

            async with self.db:
                canceled_result = await self.db.query_row(
                    canceled_query,
                    [SubscriptionStatus.CANCELED.value, thirty_days_ago.isoformat()],
                    schema=self.schema
                )

            canceled_count = int(canceled_result.get("count", 0)) if canceled_result else 0
            churn_rate = (canceled_count / active_count * 100) if active_count > 0 else 0

            return {
                "active_subscriptions": active_count,
                "tier_distribution": tier_stats,
                "churn_rate": churn_rate,
                "canceled_last_30_days": canceled_count
            }

        except Exception as e:
            logger.error(f"获取订阅统计失败: {e}")
            return {}

    # ====================
    # 数据转换辅助方法
    # ====================

    def _convert_to_subscription_plan(self, data: Dict[str, Any]) -> SubscriptionPlan:
        """将数据库记录转换为SubscriptionPlan对象"""
        # Handle features: might be dict or need parsing
        features = data.get("features")
        if isinstance(features, str):
            import json
            features = json.loads(features)
        elif not isinstance(features, dict):
            features = {}

        return SubscriptionPlan(
            id=str(data.get("id")),
            plan_id=data["plan_id"],
            name=data["name"],
            description=data.get("description"),
            tier=SubscriptionTier(data["tier"]),
            price=Decimal(str(data["price_usd"])),
            currency=Currency(data["currency"]),
            billing_cycle=BillingCycle(data["billing_cycle"]),
            features=features,
            credits_included=data.get("credits_included", 0),
            max_users=data.get("max_users"),
            max_storage_gb=data.get("max_storage_gb"),
            trial_days=data.get("trial_days", 0),
            stripe_price_id=data.get("stripe_price_id"),
            stripe_product_id=data.get("stripe_product_id"),
            is_active=data.get("is_active", True),
            is_public=data.get("is_public", True),
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
        )

    def _convert_to_subscription(self, data: Dict[str, Any]) -> Subscription:
        """将数据库记录转换为Subscription对象"""
        # Handle metadata
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)
        elif not isinstance(metadata, dict):
            metadata = {}

        return Subscription(
            id=str(data.get("id")),
            subscription_id=data["subscription_id"],
            user_id=data["user_id"],
            organization_id=data.get("organization_id"),
            plan_id=data["plan_id"],
            status=SubscriptionStatus(data["status"]),
            tier=SubscriptionTier(data["tier"]),
            current_period_start=datetime.fromisoformat(data["current_period_start"].replace('Z', '+00:00')),
            current_period_end=datetime.fromisoformat(data["current_period_end"].replace('Z', '+00:00')),
            billing_cycle=BillingCycle(data["billing_cycle"]),
            trial_start=datetime.fromisoformat(data["trial_start"].replace('Z', '+00:00')) if data.get("trial_start") else None,
            trial_end=datetime.fromisoformat(data["trial_end"].replace('Z', '+00:00')) if data.get("trial_end") else None,
            cancel_at_period_end=data.get("cancel_at_period_end", False),
            canceled_at=datetime.fromisoformat(data["canceled_at"].replace('Z', '+00:00')) if data.get("canceled_at") else None,
            cancellation_reason=data.get("cancellation_reason"),
            payment_method_id=data.get("payment_method_id"),
            last_payment_date=datetime.fromisoformat(data["last_payment_date"].replace('Z', '+00:00')) if data.get("last_payment_date") else None,
            next_payment_date=datetime.fromisoformat(data["next_payment_date"].replace('Z', '+00:00')) if data.get("next_payment_date") else None,
            stripe_subscription_id=data.get("stripe_subscription_id"),
            stripe_customer_id=data.get("stripe_customer_id"),
            metadata=metadata,
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
        )

    def _convert_to_payment(self, data: Dict[str, Any]) -> Payment:
        """将数据库记录转换为Payment对象"""
        # Handle processor_response
        processor_response = data.get("processor_response")
        if isinstance(processor_response, str):
            import json
            processor_response = json.loads(processor_response)
        elif not isinstance(processor_response, dict):
            processor_response = {}

        return Payment(
            id=str(data.get("id")),
            payment_id=data["payment_id"],
            user_id=data["user_id"],
            organization_id=data.get("organization_id"),
            amount=Decimal(str(data["amount"])),
            currency=Currency(data["currency"]),
            description=data.get("description"),
            status=PaymentStatus(data["status"]),
            payment_method=PaymentMethod(data["payment_method"]),
            subscription_id=data.get("subscription_id"),
            invoice_id=data.get("invoice_id"),
            processor=data.get("processor", "stripe"),
            processor_payment_id=data.get("processor_payment_id"),
            processor_response=processor_response,
            failure_reason=data.get("failure_reason"),
            failure_code=data.get("failure_code"),
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            paid_at=datetime.fromisoformat(data["paid_at"].replace('Z', '+00:00')) if data.get("paid_at") else None,
            failed_at=datetime.fromisoformat(data["failed_at"].replace('Z', '+00:00')) if data.get("failed_at") else None
        )

    def _convert_to_invoice(self, data: Dict[str, Any]) -> Invoice:
        """将数据库记录转换为Invoice对象"""
        # Handle line_items
        line_items = data.get("line_items")
        if isinstance(line_items, str):
            import json
            line_items = json.loads(line_items)
        elif not isinstance(line_items, list):
            line_items = []

        return Invoice(
            id=str(data.get("id")),
            invoice_id=data["invoice_id"],
            invoice_number=data["invoice_number"],
            user_id=data["user_id"],
            organization_id=data.get("organization_id"),
            subscription_id=data.get("subscription_id"),
            status=InvoiceStatus(data["status"]),
            amount_total=Decimal(str(data["amount_total"])),
            amount_paid=Decimal(str(data["amount_paid"])),
            amount_due=Decimal(str(data["amount_due"])),
            currency=Currency(data["currency"]),
            billing_period_start=datetime.fromisoformat(data["billing_period_start"].replace('Z', '+00:00')),
            billing_period_end=datetime.fromisoformat(data["billing_period_end"].replace('Z', '+00:00')),
            payment_method_id=data.get("payment_method_id"),
            payment_intent_id=data.get("payment_intent_id"),
            line_items=line_items,
            stripe_invoice_id=data.get("stripe_invoice_id"),
            due_date=datetime.fromisoformat(data["due_date"].replace('Z', '+00:00')) if data.get("due_date") else None,
            paid_at=datetime.fromisoformat(data["paid_at"].replace('Z', '+00:00')) if data.get("paid_at") else None,
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
        )

    def _convert_to_refund(self, data: Dict[str, Any]) -> Refund:
        """将数据库记录转换为Refund对象"""
        # Handle processor_response
        processor_response = data.get("processor_response")
        if isinstance(processor_response, str):
            import json
            processor_response = json.loads(processor_response)
        elif not isinstance(processor_response, dict):
            processor_response = {}

        return Refund(
            id=str(data.get("id")),
            refund_id=data["refund_id"],
            payment_id=data["payment_id"],
            user_id=data["user_id"],
            amount=Decimal(str(data["amount"])),
            currency=Currency(data["currency"]),
            reason=data.get("reason"),
            status=RefundStatus(data["status"]),
            processor=data.get("processor", "stripe"),
            processor_refund_id=data.get("processor_refund_id"),
            processor_response=processor_response,
            requested_by=data.get("requested_by"),
            approved_by=data.get("approved_by"),
            requested_at=datetime.fromisoformat(data["requested_at"].replace('Z', '+00:00')),
            processed_at=datetime.fromisoformat(data["processed_at"].replace('Z', '+00:00')) if data.get("processed_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"].replace('Z', '+00:00')) if data.get("completed_at") else None
        )

    def _convert_to_payment_method(self, data: Dict[str, Any]) -> PaymentMethodInfo:
        """将数据库记录转换为PaymentMethodInfo对象"""
        return PaymentMethodInfo(
            id=str(data.get("id")),
            user_id=data["user_id"],
            method_type=PaymentMethod(data["method_type"]),
            card_brand=data.get("card_brand"),
            card_last4=data.get("card_last4"),
            card_exp_month=data.get("card_exp_month"),
            card_exp_year=data.get("card_exp_year"),
            bank_name=data.get("bank_name"),
            bank_account_last4=data.get("bank_account_last4"),
            external_account_id=data.get("external_account_id"),
            stripe_payment_method_id=data.get("stripe_payment_method_id"),
            is_default=data.get("is_default", False),
            is_verified=data.get("is_verified", False),
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None
        )
