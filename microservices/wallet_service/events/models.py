"""
Wallet Event Data Models

wallet_service 专属的事件数据结构定义
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BillingCalculatedEventData(BaseModel):
    """
    计费计算完成事件数据 (wallet_service 视角)

    wallet_service 监听此事件并执行 token 扣费

    NATS Subject: billing.calculated
    Publisher: billing_service
    """

    user_id: str = Field(..., description="用户ID")
    billing_record_id: str = Field(..., description="计费记录ID")

    # wallet_service 关心的字段
    token_equivalent: Decimal = Field(..., description="需要扣除的 token 数量")
    cost_usd: Decimal = Field(..., description="USD 成本")

    # 计费类型
    is_free_tier: bool = Field(False, description="是否免费额度")
    is_included_in_subscription: bool = Field(False, description="是否订阅包含")

    # 可选字段
    product_id: Optional[str] = Field(None, description="产品ID")
    usage_event_id: Optional[str] = Field(None, description="原始使用事件ID")

    class Config:
        json_encoders = {Decimal: lambda v: float(v)}


class TokensDeductedEventData(BaseModel):
    """
    Token 扣费成功事件数据

    wallet_service 扣费成功后发布此事件

    NATS Subject: wallet.tokens.deducted
    Subscribers: analytics_service, notification_service
    """

    user_id: str = Field(..., description="用户ID")
    billing_record_id: str = Field(..., description="关联的计费记录ID")
    transaction_id: str = Field(..., description="钱包交易ID")

    # Token 信息
    tokens_deducted: Decimal = Field(..., description="扣除的 token 数量")
    balance_before: Decimal = Field(..., description="扣费前余额")
    balance_after: Decimal = Field(..., description="扣费后余额")

    # 配额追踪
    monthly_quota: Optional[Decimal] = Field(None, description="月度 token 配额")
    monthly_used: Optional[Decimal] = Field(None, description="本月已使用 token")
    percentage_used: Optional[float] = Field(None, description="配额使用百分比")

    # 时间戳
    timestamp: Optional[datetime] = Field(None, description="扣费时间")

    class Config:
        json_encoders = {Decimal: lambda v: float(v), datetime: lambda v: v.isoformat()}


class TokensInsufficientEventData(BaseModel):
    """
    Token 余额不足事件数据

    wallet_service 发现余额不足时发布此事件

    NATS Subject: wallet.tokens.insufficient
    Subscribers: notification_service, billing_service
    """

    user_id: str = Field(..., description="用户ID")
    billing_record_id: str = Field(..., description="关联的计费记录ID")

    # Token 信息
    tokens_required: Decimal = Field(..., description="所需 token 数量")
    tokens_available: Decimal = Field(..., description="当前可用 token")
    tokens_deficit: Decimal = Field(..., description="缺少的 token 数量")

    # 建议操作
    suggested_action: str = Field(
        "upgrade_plan", description="建议操作 (upgrade_plan, purchase_tokens)"
    )

    # 时间戳
    timestamp: Optional[datetime] = Field(None, description="发生时间")

    class Config:
        json_encoders = {Decimal: lambda v: float(v), datetime: lambda v: v.isoformat()}


class WalletDepositedEventData(BaseModel):
    """
    钱包充值成功事件数据

    wallet_service 充值成功后发布此事件

    NATS Subject: wallet.deposited
    """

    user_id: str = Field(..., description="用户ID")
    wallet_id: str = Field(..., description="钱包ID")
    transaction_id: str = Field(..., description="交易ID")

    # 充值信息
    amount_deposited: Decimal = Field(..., description="充值金额")
    balance_before: Decimal = Field(..., description="充值前余额")
    balance_after: Decimal = Field(..., description="充值后余额")

    # 充值来源
    deposit_source: str = Field(
        ..., description="充值来源 (payment, subscription, gift)"
    )
    payment_id: Optional[str] = Field(None, description="关联的支付ID")

    # 时间戳
    timestamp: Optional[datetime] = Field(None, description="充值时间")

    class Config:
        json_encoders = {Decimal: lambda v: float(v), datetime: lambda v: v.isoformat()}


# Helper functions
def parse_billing_calculated_event(event_data: dict) -> BillingCalculatedEventData:
    """解析 billing.calculated 事件数据"""
    return BillingCalculatedEventData(**event_data)


def create_tokens_deducted_event_data(
    user_id: str,
    billing_record_id: str,
    transaction_id: str,
    tokens_deducted: Decimal,
    balance_before: Decimal,
    balance_after: Decimal,
    monthly_quota: Optional[Decimal] = None,
    monthly_used: Optional[Decimal] = None,
) -> TokensDeductedEventData:
    """创建 tokens.deducted 事件数据"""

    percentage_used = None
    if monthly_quota and monthly_used and monthly_quota > 0:
        percentage_used = float((monthly_used / monthly_quota) * 100)

    return TokensDeductedEventData(
        user_id=user_id,
        billing_record_id=billing_record_id,
        transaction_id=transaction_id,
        tokens_deducted=tokens_deducted,
        balance_before=balance_before,
        balance_after=balance_after,
        monthly_quota=monthly_quota,
        monthly_used=monthly_used,
        percentage_used=percentage_used,
        timestamp=datetime.utcnow(),
    )


def create_tokens_insufficient_event_data(
    user_id: str,
    billing_record_id: str,
    tokens_required: Decimal,
    tokens_available: Decimal,
    suggested_action: str = "upgrade_plan",
) -> TokensInsufficientEventData:
    """创建 tokens.insufficient 事件数据"""

    tokens_deficit = tokens_required - tokens_available

    return TokensInsufficientEventData(
        user_id=user_id,
        billing_record_id=billing_record_id,
        tokens_required=tokens_required,
        tokens_available=tokens_available,
        tokens_deficit=tokens_deficit,
        suggested_action=suggested_action,
        timestamp=datetime.utcnow(),
    )
