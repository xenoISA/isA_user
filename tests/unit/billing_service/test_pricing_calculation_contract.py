from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from microservices.billing_service.billing_service import BillingService
from microservices.billing_service.models import (
    BillingCalculationRequest,
    BillingMethod,
    BillingStatus,
    Currency,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_billing_cost_uses_compatibility_unit_price():
    service = BillingService(
        repository=AsyncMock(),
        event_bus=AsyncMock(),
        product_client=AsyncMock(),
        wallet_client=AsyncMock(),
        subscription_client=AsyncMock(),
    )
    service._get_product_pricing = AsyncMock(
        return_value={
            "success": True,
            "unit_price": "0.00000030",
            "total_price": "0.00001110",
            "currency": "USD",
            "pricing_found": True,
        }
    )
    service._get_user_balances = AsyncMock(return_value=(0, 0, Decimal("0"), None))

    result = await service.calculate_billing_cost(
        BillingCalculationRequest(
            user_id="user_123",
            product_id="gpt-4o-mini",
            usage_amount=Decimal("37"),
            unit_type="token",
        )
    )

    assert result.success is True
    assert result.unit_price == Decimal("0.00000030")
    assert result.total_cost == Decimal("0.00001110")
    assert result.currency == Currency.USD
    assert result.suggested_billing_method in {
        BillingMethod.WALLET_DEDUCTION,
        BillingMethod.PAYMENT_CHARGE,
        BillingMethod.CREDIT_CONSUMPTION,
        BillingMethod.SUBSCRIPTION_CREDIT,
        BillingMethod.SUBSCRIPTION_INCLUDED,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_billing_cost_prefers_subscription_credit_when_balance_exists():
    service = BillingService(
        repository=AsyncMock(),
        event_bus=AsyncMock(),
        product_client=AsyncMock(),
        wallet_client=AsyncMock(),
        subscription_client=AsyncMock(),
    )
    service._get_product_pricing = AsyncMock(
        return_value={
            "success": True,
            "unit_price": "0.0100",
            "total_price": "0.0100",
            "currency": "USD",
            "pricing_found": True,
        }
    )
    service._get_user_balances = AsyncMock(
        return_value=(5000, 0, Decimal("0"), "sub_123")
    )

    result = await service.calculate_billing_cost(
        BillingCalculationRequest(
            user_id="user_123",
            organization_id="org_123",
            billing_account_type="organization",
            billing_account_id="org_123",
            product_id="web_crawl",
            usage_amount=Decimal("1"),
            unit_type="url",
        )
    )

    assert result.success is True
    assert result.subscription_id == "sub_123"
    assert result.suggested_billing_method == BillingMethod.SUBSCRIPTION_CREDIT
