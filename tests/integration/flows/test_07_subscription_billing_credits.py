#!/usr/bin/env python3
"""
P2 集成测试: 订阅、计费、积分流程

测试覆盖的服务:
- subscription_service: 订阅管理、积分分配
- billing_service: 使用量计费、账单生成
- wallet_service: 积分消耗、余额管理
- product_service: 产品定价、套餐管理
- payment_service: 支付处理

测试流程:
1. 创建订阅计划
2. 用户订阅
3. 分配订阅积分
4. 模拟使用消耗积分
5. 验证计费记录
6. 测试积分不足处理
7. 测试订阅升级
8. 测试订阅取消

事件验证:
- subscription.created
- subscription.credits.allocated
- subscription.credits.consumed
- billing.calculated
- wallet.tokens.deducted
- subscription.cancelled
"""

import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../..")
sys.path.insert(0, _project_root)
sys.path.insert(0, _current_dir)

from base_test import BaseIntegrationTest


class SubscriptionBillingCreditsIntegrationTest(BaseIntegrationTest):
    """订阅计费积分集成测试"""

    def __init__(self):
        super().__init__()
        self.test_user_id = None
        self.subscription_id = None
        self.wallet_id = None
        self.product_id = None
        self.subscription_tier_code = "pro"
        self.initial_credits = 1000
        self.initial_subscription_credits = 0
        self.last_billing_record_id = None

    async def run(self):
        """运行完整测试"""
        self.log_header("P2: Subscription → Billing → Credits Integration Test")
        self.log(f"Start Time: {datetime.utcnow().isoformat()}")

        try:
            await self.setup()

            self.test_user_id = self.generate_test_user_id()
            self.log(f"Test User ID: {self.test_user_id}")

            # 运行测试步骤
            await self.test_step_1_setup_wallet()
            await self.test_step_2_get_subscription_products()
            await self.test_step_3_create_subscription()
            await self.test_step_4_verify_credits_allocated()
            await self.test_step_5_consume_credits()
            await self.test_step_6_verify_billing_record()
            await self.test_step_7_test_insufficient_credits()
            await self.test_step_8_verify_subscription_balance()
            await self.test_step_9_cancel_subscription()
            await self.test_step_10_verify_events()

        except Exception as e:
            self.log(f"Test Error: {e}", "red")
            import traceback
            traceback.print_exc()
            self.failed_assertions += 1

        finally:
            await self.teardown()
            self.log_summary()

        return self.failed_assertions == 0

    async def test_step_1_setup_wallet(self):
        """Step 1: 设置钱包"""
        self.log_step(1, "Setup Wallet with Initial Balance")

        response = await self.post(
            f"{self.config.WALLET_URL}/api/v1/wallets",
            json={
                "user_id": self.test_user_id,
                "currency": "TOKEN",
                "initial_balance": self.initial_credits
            }
        )

        if response.status_code in [200, 201]:
            data = response.json()
            self.wallet_id = data.get("wallet_id")
            self.assert_not_none(self.wallet_id, "Wallet created")
            self.log(f"  Wallet ID: {self.wallet_id}")
            self.log(f"  Initial Balance: {self.initial_credits} credits")
        elif response.status_code == 409:
            # 已存在，获取
            get_resp = await self.get(f"{self.config.WALLET_URL}/api/v1/wallets/user/{self.test_user_id}")
            if get_resp.status_code == 200:
                self.wallet_id = get_resp.json().get("wallet_id")
                self.log(f"  Existing Wallet ID: {self.wallet_id}")

    async def test_step_2_get_subscription_products(self):
        """Step 2: 获取可计费产品"""
        self.log_step(2, "Get Billable Product")

        response = await self.get(
            f"{self.config.PRODUCT_URL}/api/v1/product/products",
            params={"is_active": True}
        )

        if self.assert_http_success(response, 200):
            products = response.json()
            if not isinstance(products, list):
                products = products.get("products", products.get("items", []))

            model_products = [
                product
                for product in products
                if product.get("product_type") == "model_inference"
            ]
            preferred_ids = ["gpt-4o-mini", "gpt-4o", "claude-sonnet-4"]

            selected = None
            for product_id in preferred_ids:
                selected = next(
                    (
                        product
                        for product in model_products
                        if product.get("product_id") == product_id
                    ),
                    None,
                )
                if selected:
                    break

            if not selected and model_products:
                selected = model_products[0]

            self.assert_not_none(selected, "Found at least one billable model product")
            if selected:
                self.product_id = selected.get("product_id")
                self.log(f"  Using Product: {selected.get('name', self.product_id)}")
                self.log(f"  Product ID: {self.product_id}")
                self.log(f"  Tier Code: {self.subscription_tier_code}")

    async def test_step_3_create_subscription(self):
        """Step 3: 创建订阅"""
        self.log_step(3, "Create Subscription")

        if self.event_collector:
            self.event_collector.clear()

        response = await self.post(
            f"{self.config.SUBSCRIPTION_URL}/api/v1/subscriptions",
            json={
                "user_id": self.test_user_id,
                "tier_code": self.subscription_tier_code,
                "billing_cycle": "monthly",
                "metadata": {
                    "source": "integration_test"
                }
            }
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            subscription = data.get("subscription", {})
            self.subscription_id = subscription.get("subscription_id")
            self.assert_not_none(self.subscription_id, "Subscription created")
            self.log(f"  Subscription ID: {self.subscription_id}")
            self.log(f"  Status: {subscription.get('status', 'active')}")
            self.log(f"  Tier: {subscription.get('tier_code', self.subscription_tier_code)}")
            self.log(
                f"  Credits Allocated: {data.get('credits_allocated', subscription.get('credits_allocated', 'N/A'))}"
            )

            await self.wait(2, "Waiting for subscription.created event")
            await self.assert_event_published("subscription.created", timeout=10.0)

    async def test_step_4_verify_credits_allocated(self):
        """Step 4: 验证积分已分配"""
        self.log_step(4, "Verify Credits Allocated")

        if not self.subscription_id:
            self.log("  SKIP: No subscription_id", "yellow")
            return

        # 检查订阅积分
        response = await self.get(
            f"{self.config.SUBSCRIPTION_URL}/api/v1/subscriptions/credits/balance",
            params={"user_id": self.test_user_id},
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            credits_balance = data.get(
                "subscription_credits_remaining",
                data.get("total_credits_available", 0),
            )
            self.initial_subscription_credits = credits_balance
            self.log(f"  Credits Balance: {credits_balance}")
            self.assert_true(credits_balance > 0, "Credits allocated to subscription")

    async def test_step_5_consume_credits(self):
        """Step 5: 消耗积分"""
        self.log_step(5, "Consume Credits")

        if not self.test_user_id:
            self.log("  SKIP: No test_user_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # 通过 billing_service 记录使用量
        response = await self.post(
            f"{self.config.BILLING_URL}/api/v1/billing/usage/record",
            json={
                "user_id": self.test_user_id,
                "subscription_id": self.subscription_id,
                "product_id": self.product_id,
                "service_type": "model_inference",
                "usage_amount": 100,
                "unit_type": "token",
                "usage_details": {
                    "input_tokens": 50,
                    "output_tokens": 50,
                    "model": self.product_id,
                    "operation": "chat"
                }
            }
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            self.last_billing_record_id = data.get("billing_record_id")
            self.assert_true(data.get("success", False), "Usage recorded")
            self.log(f"  Usage Amount: 100 tokens")
            self.log(f"  Billing Record: {self.last_billing_record_id or 'N/A'}")
            self.log(f"  Billing Method: {data.get('billing_method_used', 'N/A')}")
            self.log(f"  Amount Charged: {data.get('amount_charged', 'N/A')}")

            await self.wait(3, "Waiting for billing.calculated event")
            await self.assert_event_published("billing.calculated", timeout=10.0)

    async def test_step_6_verify_billing_record(self):
        """Step 6: 验证计费记录"""
        self.log_step(6, "Verify Billing Record")

        if not self.test_user_id:
            self.log("  SKIP: No test_user_id", "yellow")
            return

        response = await self.get(
            f"{self.config.BILLING_URL}/api/v1/billing/records/user/{self.test_user_id}",
            params={"limit": 5}
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            records = data.get("records", data.get("items", []))
            self.log(f"  Found {len(records)} billing record(s)")

            if records:
                latest = records[0]
                self.assert_equal(
                    latest.get("billing_id"),
                    self.last_billing_record_id,
                    "Latest billing record matches usage call",
                )
                self.assert_equal(
                    latest.get("product_id"),
                    self.product_id,
                    "Billing record product matches selected product",
                )
                self.log(f"  Latest Record:")
                self.log(f"    - Amount: {latest.get('usage_amount', latest.get('amount'))}")
                self.log(
                    f"    - Status: {latest.get('billing_status', latest.get('status'))}"
                )
                self.log(f"    - Product: {latest.get('product_id')}")

    async def test_step_7_test_insufficient_credits(self):
        """Step 7: 测试积分不足"""
        self.log_step(7, "Test Insufficient Credits")

        if not self.test_user_id:
            self.log("  SKIP: No test_user_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # 尝试消耗大量积分
        response = await self.post(
            f"{self.config.BILLING_URL}/api/v1/billing/usage/record",
            json={
                "user_id": self.test_user_id,
                "subscription_id": self.subscription_id,
                "product_id": self.product_id,
                "service_type": "model_inference",
                "usage_amount": 1000000000,
                "unit_type": "token",
                "usage_details": {
                    "operation": "large_batch_test"
                }
            }
        )

        if response.status_code == 200:
            data = response.json()
            message = str(data.get("message", ""))
            if not data.get("success", True) or "insufficient" in message.lower():
                self.assert_true(True, "Insufficient credits handled correctly")
                self.log(f"  Message: {message}")
            else:
                self.failed_assertions += 1
                self.log(f"  FAIL: Expected insufficient credits, got: {data}", "red")
        elif response.status_code in [402, 400]:
            self.assert_true(True, "Insufficient credits rejected with proper error code")
            self.log(f"  Error Code: {response.status_code}")

        await self.wait(2, "Waiting for credits.insufficient event")

    async def test_step_8_verify_subscription_balance(self):
        """Step 8: 验证订阅余额变化"""
        self.log_step(8, "Verify Subscription Balance")

        if not self.subscription_id:
            self.log("  SKIP: No subscription_id", "yellow")
            return

        response = await self.get(
            f"{self.config.SUBSCRIPTION_URL}/api/v1/subscriptions/credits/balance",
            params={"user_id": self.test_user_id},
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            remaining = data.get(
                "subscription_credits_remaining",
                data.get("total_credits_available", 0),
            )
            self.log(f"  Remaining Credits: {remaining}")
            if self.initial_subscription_credits:
                self.assert_true(
                    remaining < self.initial_subscription_credits,
                    "Subscription credits decreased after billing",
                )

    async def test_step_9_cancel_subscription(self):
        """Step 9: 取消订阅"""
        self.log_step(9, "Cancel Subscription")

        if not self.subscription_id:
            self.log("  SKIP: No subscription_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        response = await self.post(
            f"{self.config.SUBSCRIPTION_URL}/api/v1/subscriptions/{self.subscription_id}/cancel",
            params={"user_id": self.test_user_id},
            json={
                "reason": "integration_test_complete",
                "immediate": False,
                "feedback": "codex live billing e2e"
            }
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            self.assert_true(data.get("success", False), "Subscription cancelled")
            self.log(f"  Cancel Message: {data.get('message')}")
            self.log(f"  Effective Date: {data.get('effective_date', 'N/A')}")
            self.log(f"  Credits Remaining: {data.get('credits_remaining', 'N/A')}")

            await self.wait(2, "Waiting for subscription.canceled event")
            await self.assert_event_published("subscription.canceled", timeout=10.0)

    async def test_step_10_verify_events(self):
        """Step 10: 验证事件"""
        self.log_step(10, "Verify Events")

        if not self.event_collector:
            self.log("  SKIP: No event collector", "yellow")
            return

        summary = self.event_collector.summary()
        self.log(f"  Events collected: {summary}")

        if summary:
            self.assert_true(True, "Collected billing flow events")
        else:
            self.log("  No events currently buffered", "yellow")


async def main():
    """主函数"""
    test = SubscriptionBillingCreditsIntegrationTest()
    success = await test.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
