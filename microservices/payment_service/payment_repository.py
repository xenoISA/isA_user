"""
Payment Repository

数据访问层，处理支付、订阅、账单、退款等数据库操作
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json
import uuid

# Database client setup
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    SubscriptionPlan, Subscription, Payment, Invoice, Refund, PaymentMethodInfo,
    PaymentStatus, SubscriptionStatus, InvoiceStatus, RefundStatus,
    SubscriptionTier, BillingCycle, Currency, PaymentMethod
)

logger = logging.getLogger(__name__)


class PaymentRepository:
    """支付数据访问仓库"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        # 表名定义 - 使用新创建的表
        self.plans_table = "payment_subscription_plans"
        self.subscriptions_table = "payment_subscriptions"  # 使用新的payment_subscriptions表
        self.payments_table = "payment_transactions"
        self.invoices_table = "payment_invoices"
        self.refunds_table = "payment_refunds"
        self.payment_methods_table = "payment_methods"
    
    # ====================
    # 连接管理
    # ====================
    
    async def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            result = self.supabase.table(self.subscriptions_table).select("count").limit(1).execute()
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
                "features": json.dumps(plan.features) if plan.features else None,
                "credits_included": plan.credits_included,
                "max_users": plan.max_users,
                "max_storage_gb": plan.max_storage_gb,
                "trial_days": plan.trial_days,
                "stripe_price_id": plan.stripe_price_id,
                "stripe_product_id": plan.stripe_product_id,
                "is_active": plan.is_active,
                "is_public": plan.is_public,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.plans_table).insert(data).execute()
            
            if result.data:
                return self._convert_to_subscription_plan(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建订阅计划失败: {e}")
            return None
    
    async def get_subscription_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """获取订阅计划"""
        try:
            result = self.supabase.table(self.plans_table)\
                .select("*")\
                .eq("plan_id", plan_id)\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            if result.data:
                return self._convert_to_subscription_plan(result.data)
            return None
            
        except Exception as e:
            logger.error(f"获取订阅计划失败: {e}")
            return None
    
    async def list_subscription_plans(self, tier: Optional[SubscriptionTier] = None, 
                                     is_public: bool = True) -> List[SubscriptionPlan]:
        """列出订阅计划"""
        try:
            query = self.supabase.table(self.plans_table)\
                .select("*")\
                .eq("is_active", True)\
                .eq("is_public", is_public)
            
            if tier:
                query = query.eq("tier", tier.value)
            
            result = query.order("price_usd", desc=False).execute()
            
            if result.data:
                return [self._convert_to_subscription_plan(plan) for plan in result.data]
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
                "metadata": json.dumps(subscription.metadata) if subscription.metadata else None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.subscriptions_table).insert(data).execute()
            
            if result.data:
                return self._convert_to_subscription(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建订阅失败: {e}")
            return None
    
    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户当前订阅"""
        try:
            result = self.supabase.table(self.subscriptions_table)\
                .select("*")\
                .eq("user_id", user_id)\
                .in_("status", ["active", "trialing", "past_due"])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return self._convert_to_subscription(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"获取用户订阅失败: {e}")
            return None
    
    async def update_subscription(self, subscription_id: str, updates: Dict[str, Any]) -> Optional[Subscription]:
        """更新订阅"""
        try:
            # 添加更新时间戳
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            # 处理枚举值
            if "status" in updates and hasattr(updates["status"], "value"):
                updates["status"] = updates["status"].value
            if "tier" in updates and hasattr(updates["tier"], "value"):
                updates["tier"] = updates["tier"].value
            
            result = self.supabase.table(self.subscriptions_table)\
                .update(updates)\
                .eq("subscription_id", subscription_id)\
                .execute()
            
            if result.data:
                return self._convert_to_subscription(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"更新订阅失败: {e}")
            return None
    
    async def get_user_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户当前激活的订阅"""
        try:
            result = self.supabase.table(self.subscriptions_table)\
                .select("*")\
                .eq("user_id", user_id)\
                .in_("status", [SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return self._convert_to_subscription(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"获取用户激活订阅失败: {e}")
            return None
    
    async def get_user_default_payment_method(self, user_id: str) -> Optional[PaymentMethodInfo]:
        """获取用户默认支付方式"""
        try:
            result = self.supabase.table(self.payment_methods_table)\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_default", True)\
                .single()\
                .execute()
            
            if result.data:
                return self._convert_to_payment_method(result.data)
            return None
            
        except Exception as e:
            logger.error(f"获取用户默认支付方式失败: {e}")
            return None
    
    async def cancel_subscription(self, subscription_id: str, immediate: bool = False, 
                                reason: Optional[str] = None) -> bool:
        """取消订阅"""
        try:
            updates = {
                "canceled_at": datetime.utcnow().isoformat(),
                "cancellation_reason": reason,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if immediate:
                updates["status"] = SubscriptionStatus.CANCELED.value
            else:
                updates["cancel_at_period_end"] = True
            
            result = self.supabase.table(self.subscriptions_table)\
                .update(updates)\
                .eq("subscription_id", subscription_id)\
                .execute()
            
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            return False
    
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
                "processor_response": json.dumps(payment.processor_response) if payment.processor_response else None,
                "failure_reason": payment.failure_reason,
                "failure_code": payment.failure_code,
                "created_at": datetime.utcnow().isoformat(),
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "failed_at": payment.failed_at.isoformat() if payment.failed_at else None
            }
            
            result = self.supabase.table(self.payments_table).insert(data).execute()
            
            if result.data:
                return self._convert_to_payment(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建支付记录失败: {e}")
            return None
    
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """获取支付记录"""
        try:
            result = self.supabase.table(self.payments_table)\
                .select("*")\
                .eq("payment_id", payment_id)\
                .single()\
                .execute()
            
            if result.data:
                return self._convert_to_payment(result.data)
            return None
            
        except Exception as e:
            logger.error(f"获取支付记录失败: {e}")
            return None
    
    async def update_payment_status(self, payment_id: str, status: PaymentStatus, 
                                   failure_reason: Optional[str] = None) -> bool:
        """更新支付状态"""
        try:
            updates = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if status == PaymentStatus.SUCCEEDED:
                updates["paid_at"] = datetime.utcnow().isoformat()
            elif status == PaymentStatus.FAILED:
                updates["failed_at"] = datetime.utcnow().isoformat()
                updates["failure_reason"] = failure_reason
            
            result = self.supabase.table(self.payments_table)\
                .update(updates)\
                .eq("payment_id", payment_id)\
                .execute()
            
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            logger.error(f"更新支付状态失败: {e}")
            return False
    
    async def get_user_payments(self, user_id: str, limit: int = 10, 
                               status: Optional[PaymentStatus] = None) -> List[Payment]:
        """获取用户支付历史"""
        try:
            query = self.supabase.table(self.payments_table)\
                .select("*")\
                .eq("user_id", user_id)
            
            if status:
                query = query.eq("status", status.value)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            
            if result.data:
                return [self._convert_to_payment(payment) for payment in result.data]
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
                "line_items": json.dumps(invoice.line_items) if invoice.line_items else None,
                "stripe_invoice_id": invoice.stripe_invoice_id,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.invoices_table).insert(data).execute()
            
            if result.data:
                return self._convert_to_invoice(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建发票失败: {e}")
            return None
    
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """获取发票"""
        try:
            result = self.supabase.table(self.invoices_table)\
                .select("*")\
                .eq("invoice_id", invoice_id)\
                .single()\
                .execute()
            
            if result.data:
                return self._convert_to_invoice(result.data)
            return None
            
        except Exception as e:
            logger.error(f"获取发票失败: {e}")
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
                "processor_response": json.dumps(refund.processor_response) if refund.processor_response else None,
                "requested_by": refund.requested_by,
                "approved_by": refund.approved_by,
                "requested_at": refund.requested_at.isoformat(),
                "processed_at": refund.processed_at.isoformat() if refund.processed_at else None,
                "completed_at": refund.completed_at.isoformat() if refund.completed_at else None
            }
            
            result = self.supabase.table(self.refunds_table).insert(data).execute()
            
            if result.data:
                return self._convert_to_refund(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"创建退款失败: {e}")
            return None
    
    async def update_refund_status(self, refund_id: str, status: RefundStatus) -> bool:
        """更新退款状态"""
        try:
            updates = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if status == RefundStatus.PROCESSING:
                updates["processed_at"] = datetime.utcnow().isoformat()
            elif status == RefundStatus.SUCCEEDED:
                updates["completed_at"] = datetime.utcnow().isoformat()
            
            result = self.supabase.table(self.refunds_table)\
                .update(updates)\
                .eq("refund_id", refund_id)\
                .execute()
            
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            logger.error(f"更新退款状态失败: {e}")
            return False
    
    # ====================
    # 支付方式管理
    # ====================
    
    async def save_payment_method(self, method: PaymentMethodInfo) -> Optional[PaymentMethodInfo]:
        """保存支付方式"""
        try:
            data = {
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
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.payment_methods_table).insert(data).execute()
            
            if result.data:
                return self._convert_to_payment_method(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"保存支付方式失败: {e}")
            return None
    
    async def get_user_payment_methods(self, user_id: str) -> List[PaymentMethodInfo]:
        """获取用户支付方式"""
        try:
            result = self.supabase.table(self.payment_methods_table)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("is_default", desc=True)\
                .execute()
            
            if result.data:
                return [self._convert_to_payment_method(method) for method in result.data]
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
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 获取成功的支付
            result = self.supabase.table(self.payments_table)\
                .select("amount, created_at")\
                .eq("status", PaymentStatus.SUCCEEDED.value)\
                .gte("created_at", start_date.isoformat())\
                .execute()
            
            if result.data:
                total_revenue = sum(float(p["amount"]) for p in result.data)
                payment_count = len(result.data)
                
                # 按日统计
                daily_revenue = {}
                for payment in result.data:
                    date = datetime.fromisoformat(payment["created_at"].replace('Z', '+00:00')).date()
                    date_str = date.isoformat()
                    daily_revenue[date_str] = daily_revenue.get(date_str, 0) + float(payment["amount"])
                
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
            # 活跃订阅数
            active_result = self.supabase.table(self.subscriptions_table)\
                .select("count")\
                .in_("status", ["active", "trialing"])\
                .execute()
            
            active_count = len(active_result.data) if active_result.data else 0
            
            # 按层级统计
            tier_stats = {}
            for tier in SubscriptionTier:
                tier_result = self.supabase.table(self.subscriptions_table)\
                    .select("count")\
                    .eq("tier", tier.value)\
                    .in_("status", ["active", "trialing"])\
                    .execute()
                tier_stats[tier.value] = len(tier_result.data) if tier_result.data else 0
            
            # 流失率（最近30天）
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            canceled_result = self.supabase.table(self.subscriptions_table)\
                .select("count")\
                .eq("status", SubscriptionStatus.CANCELED.value)\
                .gte("canceled_at", thirty_days_ago.isoformat())\
                .execute()
            
            canceled_count = len(canceled_result.data) if canceled_result.data else 0
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
        return SubscriptionPlan(
            id=str(data.get("id")),
            plan_id=data["plan_id"],
            name=data["name"],
            description=data.get("description"),
            tier=SubscriptionTier(data["tier"]),
            price=Decimal(str(data["price_usd"])),  # Changed from price to price_usd
            currency=Currency(data["currency"]),
            billing_cycle=BillingCycle(data["billing_cycle"]),
            features=data["features"] if isinstance(data.get("features"), dict) else json.loads(data["features"]) if data.get("features") else {},
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
            metadata=json.loads(data["metadata"]) if data.get("metadata") else None,
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
        )
    
    def _convert_to_payment(self, data: Dict[str, Any]) -> Payment:
        """将数据库记录转换为Payment对象"""
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
            processor_response=data["processor_response"] if isinstance(data.get("processor_response"), dict) else json.loads(data["processor_response"]) if data.get("processor_response") else None,
            failure_reason=data.get("failure_reason"),
            failure_code=data.get("failure_code"),
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            paid_at=datetime.fromisoformat(data["paid_at"].replace('Z', '+00:00')) if data.get("paid_at") else None,
            failed_at=datetime.fromisoformat(data["failed_at"].replace('Z', '+00:00')) if data.get("failed_at") else None
        )
    
    def _convert_to_invoice(self, data: Dict[str, Any]) -> Invoice:
        """将数据库记录转换为Invoice对象"""
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
            line_items=data["line_items"] if isinstance(data.get("line_items"), list) else json.loads(data["line_items"]) if data.get("line_items") else [],
            stripe_invoice_id=data.get("stripe_invoice_id"),
            due_date=datetime.fromisoformat(data["due_date"].replace('Z', '+00:00')) if data.get("due_date") else None,
            paid_at=datetime.fromisoformat(data["paid_at"].replace('Z', '+00:00')) if data.get("paid_at") else None,
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
        )
    
    def _convert_to_refund(self, data: Dict[str, Any]) -> Refund:
        """将数据库记录转换为Refund对象"""
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
            processor_response=data["processor_response"] if isinstance(data.get("processor_response"), dict) else json.loads(data["processor_response"]) if data.get("processor_response") else None,
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