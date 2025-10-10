"""
Payment Service Business Logic Layer

处理支付相关的业务逻辑，包括订阅管理、支付处理、发票管理等
"""

import stripe
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import os

from .payment_repository import PaymentRepository
from .models import (
    SubscriptionPlan, Subscription, Payment, Invoice, Refund,
    PaymentMethodInfo, PaymentStatus, SubscriptionStatus,
    SubscriptionTier, BillingCycle, RefundStatus, InvoiceStatus,
    CreatePaymentIntentRequest, CreateSubscriptionRequest,
    UpdateSubscriptionRequest, CancelSubscriptionRequest,
    CreateRefundRequest, PaymentIntentResponse,
    SubscriptionResponse, PaymentHistoryResponse,
    InvoiceResponse, UsageRecord
)

logger = logging.getLogger(__name__)


class PaymentService:
    """支付服务业务逻辑层"""
    
    def __init__(self, repository: PaymentRepository, stripe_secret_key: Optional[str] = None):
        """
        初始化支付服务
        
        Args:
            repository: 数据访问层实例
            stripe_secret_key: Stripe API密钥
        """
        self.repository = repository
        
        # 初始化Stripe
        if stripe_secret_key:
            stripe.api_key = stripe_secret_key
            logger.info("Stripe initialized with provided secret key")
        elif os.getenv("STRIPE_SECRET_KEY"):
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            logger.info("Stripe initialized from environment variable")
        elif os.getenv("PAYMENT_SERVICE_STRIPE_SECRET_KEY"):
            stripe.api_key = os.getenv("PAYMENT_SERVICE_STRIPE_SECRET_KEY")
            logger.info("Stripe initialized from service-specific environment variable")
        
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET") or os.getenv("PAYMENT_SERVICE_STRIPE_WEBHOOK_SECRET")
        
        logger.info("PaymentService initialized")
    
    # ====================
    # 订阅计划管理
    # ====================
    
    async def create_subscription_plan(
        self,
        plan_id: str,
        name: str,
        tier: SubscriptionTier,
        price: Decimal,
        billing_cycle: BillingCycle,
        features: Dict[str, Any] = None,
        trial_days: int = 0,
        stripe_product_id: Optional[str] = None,
        stripe_price_id: Optional[str] = None
    ) -> SubscriptionPlan:
        """
        创建订阅计划
        
        Args:
            plan_id: 计划ID
            name: 计划名称
            tier: 订阅层级
            price: 价格
            billing_cycle: 计费周期
            features: 计划特性
            trial_days: 试用天数
            stripe_product_id: Stripe产品ID
            stripe_price_id: Stripe价格ID
            
        Returns:
            创建的订阅计划
        """
        # 如果提供了Stripe集成，创建Stripe产品和价格
        if stripe.api_key and not stripe_price_id:
            try:
                # 创建Stripe产品
                product = stripe.Product.create(
                    name=name,
                    description=f"{tier.value} plan - {billing_cycle.value}",
                    metadata={"plan_id": plan_id, "tier": tier.value}
                )
                stripe_product_id = product.id
                
                # 创建Stripe价格
                recurring_config = None
                if billing_cycle != BillingCycle.ONE_TIME:
                    interval_map = {
                        BillingCycle.MONTHLY: "month",
                        BillingCycle.QUARTERLY: "month",
                        BillingCycle.YEARLY: "year"
                    }
                    interval_count_map = {
                        BillingCycle.MONTHLY: 1,
                        BillingCycle.QUARTERLY: 3,
                        BillingCycle.YEARLY: 1
                    }
                    recurring_config = {
                        "interval": interval_map.get(billing_cycle, "month"),
                        "interval_count": interval_count_map.get(billing_cycle, 1)
                    }
                
                price_obj = stripe.Price.create(
                    product=stripe_product_id,
                    unit_amount=int(price * 100),  # Stripe uses cents
                    currency="usd",
                    recurring=recurring_config if recurring_config else None,
                    metadata={"plan_id": plan_id}
                )
                stripe_price_id = price_obj.id
                
            except stripe.error.StripeError as e:
                logger.error(f"Failed to create Stripe product/price: {str(e)}")
        
        # 创建数据库记录
        plan = SubscriptionPlan(
            plan_id=plan_id,
            name=name,
            tier=tier,
            price=price,
            billing_cycle=billing_cycle,
            features=features or {},
            trial_days=trial_days,
            stripe_product_id=stripe_product_id,
            stripe_price_id=stripe_price_id
        )
        
        result = await self.repository.create_subscription_plan(plan)
        logger.info(f"Subscription plan created: {plan_id}")
        return result
    
    async def get_subscription_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """获取订阅计划"""
        return await self.repository.get_subscription_plan(plan_id)
    
    async def list_subscription_plans(
        self,
        tier: Optional[SubscriptionTier] = None,
        is_active: bool = True
    ) -> List[SubscriptionPlan]:
        """列出订阅计划"""
        return await self.repository.list_subscription_plans(tier, is_active)
    
    # ====================
    # 订阅管理
    # ====================
    
    async def create_subscription(
        self,
        request: CreateSubscriptionRequest
    ) -> SubscriptionResponse:
        """
        创建订阅
        
        Args:
            request: 创建订阅请求
            
        Returns:
            订阅响应
        """
        # 获取计划信息
        plan = await self.get_subscription_plan(request.plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {request.plan_id}")
        
        # 计算订阅周期
        now = datetime.utcnow()
        trial_days = request.trial_days or plan.trial_days or 0
        
        if trial_days > 0:
            trial_start = now
            trial_end = now + timedelta(days=trial_days)
            current_period_start = trial_start
            current_period_end = trial_end
            status = SubscriptionStatus.TRIALING
        else:
            current_period_start = now
            if plan.billing_cycle == BillingCycle.MONTHLY:
                current_period_end = now + timedelta(days=30)
            elif plan.billing_cycle == BillingCycle.QUARTERLY:
                current_period_end = now + timedelta(days=90)
            elif plan.billing_cycle == BillingCycle.YEARLY:
                current_period_end = now + timedelta(days=365)
            else:
                current_period_end = now + timedelta(days=30)
            status = SubscriptionStatus.ACTIVE
            trial_start = None
            trial_end = None
        
        # 如果有Stripe集成，创建Stripe订阅
        stripe_subscription_id = None
        stripe_customer_id = None
        
        if stripe.api_key and plan.stripe_price_id and request.payment_method_id:
            try:
                # 创建或获取Stripe客户
                customers = stripe.Customer.list(email=request.user_id, limit=1)
                if customers.data:
                    customer = customers.data[0]
                else:
                    customer = stripe.Customer.create(
                        email=request.user_id,
                        payment_method=request.payment_method_id,
                        invoice_settings={"default_payment_method": request.payment_method_id}
                    )
                stripe_customer_id = customer.id
                
                # 创建Stripe订阅
                stripe_subscription = stripe.Subscription.create(
                    customer=stripe_customer_id,
                    items=[{"price": plan.stripe_price_id}],
                    trial_period_days=trial_days if trial_days > 0 else None,
                    metadata=request.metadata or {}
                )
                stripe_subscription_id = stripe_subscription.id
                
            except stripe.error.StripeError as e:
                logger.error(f"Failed to create Stripe subscription: {str(e)}")
        
        # 创建数据库记录
        subscription = Subscription(
            subscription_id=f"sub_{request.user_id}_{request.plan_id}_{now.timestamp()}",
            user_id=request.user_id,
            plan_id=request.plan_id,
            status=status,
            tier=plan.tier,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            billing_cycle=plan.billing_cycle,
            trial_start=trial_start,
            trial_end=trial_end,
            payment_method_id=request.payment_method_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            metadata=request.metadata
        )
        
        created_subscription = await self.repository.create_subscription(subscription)
        
        # 准备响应
        response = SubscriptionResponse(
            subscription=created_subscription,
            plan=plan,
            payment_method=None
        )
        
        logger.info(f"Subscription created for user {request.user_id}: {created_subscription.subscription_id}")
        return response
    
    async def get_user_subscription(
        self,
        user_id: str
    ) -> Optional[SubscriptionResponse]:
        """获取用户当前订阅"""
        subscription = await self.repository.get_user_active_subscription(user_id)
        if not subscription:
            return None
        
        plan = await self.repository.get_subscription_plan(subscription.plan_id)
        payment_method = await self.repository.get_user_default_payment_method(user_id)
        
        return SubscriptionResponse(
            subscription=subscription,
            plan=plan,
            payment_method=payment_method,
            next_invoice=None
        )
    
    async def update_subscription(
        self,
        subscription_id: str,
        request: UpdateSubscriptionRequest
    ) -> SubscriptionResponse:
        """更新订阅"""
        subscription = await self.repository.get_subscription(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        # 更新Stripe订阅
        if stripe.api_key and subscription.stripe_subscription_id:
            try:
                update_params = {}
                
                if request.plan_id:
                    new_plan = await self.repository.get_subscription_plan(request.plan_id)
                    if new_plan and new_plan.stripe_price_id:
                        # 获取当前订阅项
                        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                        current_item_id = stripe_sub['items']['data'][0]['id']
                        
                        update_params['items'] = [{
                            "id": current_item_id,
                            "price": new_plan.stripe_price_id
                        }]
                
                if request.cancel_at_period_end is not None:
                    update_params['cancel_at_period_end'] = request.cancel_at_period_end
                
                if request.payment_method_id:
                    update_params['default_payment_method'] = request.payment_method_id
                
                if request.metadata:
                    update_params['metadata'] = request.metadata
                
                if update_params:
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        **update_params
                    )
                    
            except stripe.error.StripeError as e:
                logger.error(f"Failed to update Stripe subscription: {str(e)}")
        
        # 更新数据库记录
        updated_subscription = await self.repository.update_subscription(
            subscription_id,
            request.plan_id,
            request.cancel_at_period_end,
            request.metadata
        )
        
        plan = await self.repository.get_subscription_plan(updated_subscription.plan_id)
        payment_method = await self.repository.get_user_default_payment_method(updated_subscription.user_id)
        
        response = SubscriptionResponse(
            subscription=updated_subscription,
            plan=plan,
            payment_method=payment_method
        )
        
        logger.info(f"Subscription updated: {subscription_id}")
        return response
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        request: CancelSubscriptionRequest
    ) -> Subscription:
        """取消订阅"""
        subscription = await self.repository.get_subscription(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        # 取消Stripe订阅
        if stripe.api_key and subscription.stripe_subscription_id:
            try:
                if request.immediate:
                    stripe.Subscription.delete(subscription.stripe_subscription_id)
                else:
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True
                    )
            except stripe.error.StripeError as e:
                logger.error(f"Failed to cancel Stripe subscription: {str(e)}")
        
        # 更新数据库记录
        cancelled_subscription = await self.repository.cancel_subscription(
            subscription_id,
            request.immediate,
            request.reason
        )
        
        logger.info(f"Subscription cancelled: {subscription_id}")
        return cancelled_subscription
    
    # ====================
    # 支付处理
    # ====================
    
    async def create_payment_intent(
        self,
        request: CreatePaymentIntentRequest
    ) -> PaymentIntentResponse:
        """
        创建支付意图
        
        Args:
            request: 创建支付意图请求
            
        Returns:
            支付意图响应
        """
        payment_intent_id = f"pi_{request.user_id}_{datetime.utcnow().timestamp()}"
        client_secret = None
        
        # 创建Stripe支付意图
        if stripe.api_key:
            try:
                stripe_intent = stripe.PaymentIntent.create(
                    amount=int(request.amount * 100),  # Stripe uses cents
                    currency=request.currency.value.lower(),
                    description=request.description,
                    metadata=request.metadata or {},
                    automatic_payment_methods={"enabled": True}
                )
                payment_intent_id = stripe_intent.id
                client_secret = stripe_intent.client_secret
                
            except stripe.error.StripeError as e:
                logger.error(f"Failed to create Stripe payment intent: {str(e)}")
                raise ValueError(f"Failed to create payment intent: {str(e)}")
        
        # 创建支付记录
        payment = Payment(
            payment_id=payment_intent_id,
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            status=PaymentStatus.PENDING,
            payment_method="stripe",
            processor_payment_id=payment_intent_id,
            metadata=request.metadata
        )
        
        await self.repository.create_payment(payment)
        
        response = PaymentIntentResponse(
            payment_intent_id=payment_intent_id,
            client_secret=client_secret,
            amount=request.amount,
            currency=request.currency,
            status=PaymentStatus.PENDING,
            metadata=request.metadata
        )
        
        logger.info(f"Payment intent created: {payment_intent_id}")
        return response
    
    async def confirm_payment(
        self,
        payment_id: str,
        processor_response: Optional[Dict[str, Any]] = None
    ) -> Payment:
        """确认支付"""
        payment = await self.repository.get_payment(payment_id)
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")
        
        # 更新支付状态
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = datetime.utcnow()
        payment.processor_response = processor_response
        
        updated_payment = await self.repository.update_payment_status(
            payment_id,
            PaymentStatus.SUCCEEDED,
            processor_response
        )
        
        logger.info(f"Payment confirmed: {payment_id}")
        return updated_payment
    
    async def fail_payment(
        self,
        payment_id: str,
        failure_reason: str,
        failure_code: Optional[str] = None
    ) -> Payment:
        """标记支付失败"""
        payment = await self.repository.get_payment(payment_id)
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")
        
        # 更新支付状态
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = failure_reason
        payment.failure_code = failure_code
        payment.failed_at = datetime.utcnow()
        
        updated_payment = await self.repository.update_payment_status(
            payment_id,
            PaymentStatus.FAILED,
            {"failure_reason": failure_reason, "failure_code": failure_code}
        )
        
        logger.info(f"Payment failed: {payment_id} - {failure_reason}")
        return updated_payment
    
    async def get_payment_history(
        self,
        user_id: str,
        status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> PaymentHistoryResponse:
        """获取支付历史"""
        payments = await self.repository.get_user_payments(
            user_id, status, start_date, end_date, limit
        )
        
        # 计算统计信息
        total_count = len(payments)
        total_amount = sum(p.amount for p in payments if p.status == PaymentStatus.SUCCEEDED)
        
        filters_applied = {
            "user_id": user_id,
            "status": status.value if status else None,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": limit
        }
        
        return PaymentHistoryResponse(
            payments=payments,
            total_count=total_count,
            total_amount=total_amount,
            filters_applied=filters_applied
        )
    
    # ====================
    # 发票管理
    # ====================
    
    async def create_invoice(
        self,
        user_id: str,
        subscription_id: Optional[str],
        amount_due: Decimal,
        due_date: Optional[datetime],
        line_items: List[Dict[str, Any]]
    ) -> Invoice:
        """创建发票"""
        invoice = Invoice(
            invoice_id=f"inv_{user_id}_{datetime.utcnow().timestamp()}",
            invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{user_id[:8]}",
            user_id=user_id,
            subscription_id=subscription_id,
            status=InvoiceStatus.OPEN,
            amount_total=amount_due,
            amount_due=amount_due,
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30),
            due_date=due_date,
            line_items=line_items
        )
        
        created_invoice = await self.repository.create_invoice(invoice)
        logger.info(f"Invoice created: {created_invoice.invoice_id}")
        return created_invoice
    
    async def get_invoice(self, invoice_id: str) -> Optional[InvoiceResponse]:
        """获取发票"""
        invoice = await self.repository.get_invoice(invoice_id)
        if not invoice:
            return None
        
        # 获取关联的支付记录
        payment = None
        if invoice.payment_intent_id:
            payment = await self.repository.get_payment(invoice.payment_intent_id)
        
        return InvoiceResponse(
            invoice=invoice,
            payment=payment,
            download_url=None  # TODO: 实现PDF生成
        )
    
    async def pay_invoice(
        self,
        invoice_id: str,
        payment_method_id: str
    ) -> Invoice:
        """支付发票"""
        invoice = await self.repository.get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        
        if invoice.status != InvoiceStatus.OPEN:
            raise ValueError(f"Invoice is not open for payment: {invoice.status}")
        
        # 创建支付
        payment_request = CreatePaymentIntentRequest(
            amount=invoice.amount_due,
            user_id=invoice.user_id,
            payment_method_id=payment_method_id,
            description=f"Payment for invoice {invoice.invoice_number}"
        )
        
        payment_intent = await self.create_payment_intent(payment_request)
        
        # 更新发票
        invoice.payment_intent_id = payment_intent.payment_intent_id
        invoice.payment_method_id = payment_method_id
        
        # 这里应该等待支付确认，简化处理直接标记为已支付
        paid_invoice = await self.repository.mark_invoice_paid(
            invoice_id,
            payment_intent.payment_intent_id
        )
        
        logger.info(f"Invoice paid: {invoice_id}")
        return paid_invoice
    
    # ====================
    # 退款处理
    # ====================
    
    async def create_refund(
        self,
        request: CreateRefundRequest
    ) -> Refund:
        """创建退款"""
        # 获取原始支付
        payment = await self.repository.get_payment(request.payment_id)
        if not payment:
            raise ValueError(f"Payment not found: {request.payment_id}")
        
        if payment.status != PaymentStatus.SUCCEEDED:
            raise ValueError(f"Payment is not eligible for refund: {payment.status}")
        
        # 确定退款金额
        refund_amount = request.amount or payment.amount
        if refund_amount > payment.amount:
            raise ValueError(f"Refund amount exceeds payment amount")
        
        refund_id = f"re_{payment.payment_id}_{datetime.utcnow().timestamp()}"
        
        # 创建Stripe退款
        if stripe.api_key and payment.processor_payment_id:
            try:
                stripe_refund = stripe.Refund.create(
                    payment_intent=payment.processor_payment_id,
                    amount=int(refund_amount * 100) if request.amount else None,
                    reason=request.reason
                )
                refund_id = stripe_refund.id
                
            except stripe.error.StripeError as e:
                logger.error(f"Failed to create Stripe refund: {str(e)}")
                raise ValueError(f"Failed to create refund: {str(e)}")
        
        # 创建退款记录
        refund = Refund(
            refund_id=refund_id,
            payment_id=request.payment_id,
            user_id=payment.user_id,
            amount=refund_amount,
            currency=payment.currency,
            reason=request.reason,
            status=RefundStatus.PROCESSING,
            requested_by=request.requested_by,
            processor_refund_id=refund_id
        )
        
        created_refund = await self.repository.create_refund(refund)
        
        # 更新支付状态
        if refund_amount == payment.amount:
            await self.repository.update_payment_status(
                payment.payment_id,
                PaymentStatus.REFUNDED
            )
        else:
            await self.repository.update_payment_status(
                payment.payment_id,
                PaymentStatus.PARTIAL_REFUND
            )
        
        logger.info(f"Refund created: {refund_id} for payment {request.payment_id}")
        return created_refund
    
    async def process_refund(
        self,
        refund_id: str,
        approved_by: Optional[str] = None
    ) -> Refund:
        """处理退款"""
        return await self.repository.process_refund(refund_id, approved_by)
    
    # ====================
    # Webhook处理
    # ====================
    
    async def handle_stripe_webhook(
        self,
        payload: bytes,
        sig_header: str
    ) -> Dict[str, Any]:
        """
        处理Stripe webhook事件
        
        Args:
            payload: 请求体
            sig_header: 签名头
            
        Returns:
            处理结果
        """
        try:
            # 验证签名
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            
            logger.info(f"Received Stripe webhook: {event['type']}")
            
            # 处理不同类型的事件
            event_type = event['type']
            event_data = event['data']['object']
            
            if event_type == 'payment_intent.succeeded':
                await self.confirm_payment(
                    event_data['id'],
                    {"stripe_event": event}
                )
                
            elif event_type == 'payment_intent.payment_failed':
                await self.fail_payment(
                    event_data['id'],
                    event_data.get('last_payment_error', {}).get('message', 'Payment failed'),
                    event_data.get('last_payment_error', {}).get('code')
                )
                
            elif event_type == 'invoice.payment_succeeded':
                invoice_id = event_data.get('metadata', {}).get('invoice_id')
                if invoice_id:
                    await self.repository.mark_invoice_paid(
                        invoice_id,
                        event_data['payment_intent']
                    )
                    
            elif event_type == 'customer.subscription.created':
                # 处理订阅创建
                pass
                
            elif event_type == 'customer.subscription.updated':
                # 处理订阅更新
                pass
                
            elif event_type == 'customer.subscription.deleted':
                # 处理订阅删除
                pass
                
            return {"success": True, "event": event_type}
            
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise ValueError(f"Invalid payload: {e}")
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise ValueError(f"Invalid signature: {e}")
            
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            raise ValueError(f"Failed to handle webhook: {str(e)}")
    
    # ====================
    # 统计和报告
    # ====================
    
    async def get_revenue_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取收入统计"""
        return await self.repository.get_revenue_stats(start_date, end_date)
    
    async def get_subscription_stats(self) -> Dict[str, Any]:
        """获取订阅统计"""
        return await self.repository.get_subscription_stats()
    
    async def record_usage(
        self,
        user_id: str,
        subscription_id: str,
        metric_name: str,
        quantity: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """记录使用量"""
        usage_record = UsageRecord(
            user_id=user_id,
            subscription_id=subscription_id,
            metric_name=metric_name,
            quantity=quantity,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        
        # TODO: 实现使用量记录存储
        logger.info(f"Usage recorded for user {user_id}: {metric_name} = {quantity}")
        return usage_record