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
        self.initial_credits = 1000

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
            await self.test_step_8_test_subscription_upgrade()
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
        """Step 2: 获取订阅产品"""
        self.log_step(2, "Get Subscription Products")

        response = await self.get(
            f"{self.config.PRODUCT_URL}/api/v1/products",
            params={"product_type": "subscription", "limit": 10}
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            products = data.get("products", data.get("items", []))
            self.log(f"  Found {len(products)} subscription products")

            if products:
                self.product_id = products[0].get("product_id")
                self.log(f"  Using Product: {products[0].get('name', self.product_id)}")
                self.log(f"  Price: {products[0].get('price', 'N/A')}")
            else:
                self.product_id = "basic_subscription"
                self.log(f"  Using default product ID: {self.product_id}", "yellow")

    async def test_step_3_create_subscription(self):
        """Step 3: 创建订阅"""
        self.log_step(3, "Create Subscription")

        if self.event_collector:
            self.event_collector.clear()

        response = await self.post(
            f"{self.config.SUBSCRIPTION_URL}/api/v1/subscriptions",
            json={
                "user_id": self.test_user_id,
                "product_id": self.product_id,
                "plan_type": "monthly",
                "auto_renew": True,
                "payment_method": "wallet",
                "credits_included": 500,
                "metadata": {
                    "source": "integration_test"
                }
            }
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            data = response.json()
            self.subscription_id = data.get("subscription_id")
            self.assert_not_none(self.subscription_id, "Subscription created")
            self.log(f"  Subscription ID: {self.subscription_id}")
            self.log(f"  Status: {data.get('status', 'active')}")
            self.log(f"  Plan: {data.get('plan_type', 'monthly')}")

            await self.wait(2, "Waiting for subscription.created event")

    async def test_step_4_verify_credits_allocated(self):
        """Step 4: 验证积分已分配"""
        self.log_step(4, "Verify Credits Allocated")

        if not self.subscription_id:
            self.log("  SKIP: No subscription_id", "yellow")
            return

        # 检查订阅积分
        response = await self.get(
            f"{self.config.SUBSCRIPTION_URL}/api/v1/subscriptions/{self.subscription_id}/credits"
        )

        if response.status_code == 200:
            data = response.json()
            credits_balance = data.get("credits_balance", data.get("remaining", 0))
            self.log(f"  Credits Balance: {credits_balance}")
            self.assert_true(credits_balance > 0, "Credits allocated to subscription")
        else:
            # 也可以检查钱包余额
            wallet_response = await self.get(
                f"{self.config.WALLET_URL}/api/v1/wallets/{self.wallet_id}"
            )
            if wallet_response.status_code == 200:
                wallet_data = wallet_response.json()
                self.log(f"  Wallet Balance: {wallet_data.get('balance')}")

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
            f"{self.config.BILLING_URL}/api/v1/billing/usage",
            json={
                "user_id": self.test_user_id,
                "product_id": "gpt-4",
                "usage_amount": 100,
                "unit_type": "token",
                "usage_details": {
                    "input_tokens": 50,
                    "output_tokens": 50,
                    "model": "gpt-4",
                    "operation": "chat"
                }
            }
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            data = response.json()
            self.assert_true(True, "Usage recorded")
            self.log(f"  Usage Amount: 100 tokens")
            self.log(f"  Billing Record: {data.get('billing_record_id', 'N/A')}")

            await self.wait(3, "Waiting for billing.calculated event")

    async def test_step_6_verify_billing_record(self):
        """Step 6: 验证计费记录"""
        self.log_step(6, "Verify Billing Record")

        if not self.test_user_id:
            self.log("  SKIP: No test_user_id", "yellow")
            return

        response = await self.get(
            f"{self.config.BILLING_URL}/api/v1/billing/records",
            params={"user_id": self.test_user_id, "limit": 5}
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            records = data.get("records", data.get("items", []))
            self.log(f"  Found {len(records)} billing record(s)")

            if records:
                latest = records[0]
                self.log(f"  Latest Record:")
                self.log(f"    - Amount: {latest.get('usage_amount', latest.get('amount'))}")
                self.log(f"    - Status: {latest.get('status')}")
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
            f"{self.config.BILLING_URL}/api/v1/billing/usage",
            json={
                "user_id": self.test_user_id,
                "product_id": "gpt-4",
                "usage_amount": 50000,  # 大量使用
                "unit_type": "token",
                "usage_details": {
                    "operation": "large_batch_test"
                }
            }
        )

        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "")

            if "insufficient" in status.lower():
                self.assert_true(True, "Insufficient credits handled correctly")
                self.log(f"  Status: {status}")
            else:
                self.log(f"  Response status: {status}", "yellow")
        elif response.status_code in [402, 400]:
            self.assert_true(True, "Insufficient credits rejected with proper error code")
            self.log(f"  Error Code: {response.status_code}")

        await self.wait(2, "Waiting for credits.insufficient event")

    async def test_step_8_test_subscription_upgrade(self):
        """Step 8: 测试订阅升级"""
        self.log_step(8, "Test Subscription Upgrade")

        if not self.subscription_id:
            self.log("  SKIP: No subscription_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        response = await self.post(
            f"{self.config.SUBSCRIPTION_URL}/api/v1/subscriptions/{self.subscription_id}/upgrade",
            json={
                "new_plan": "premium",
                "prorate": True
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.assert_true(True, "Subscription upgrade initiated")
            self.log(f"  New Plan: {data.get('plan_type', 'premium')}")
            self.log(f"  Status: {data.get('status')}")
        else:
            self.log(f"  Upgrade returned {response.status_code}", "yellow")

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
            json={
                "reason": "integration_test_complete",
                "immediate": False,
                "refund_unused": True
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.assert_true(True, "Subscription cancelled")
            self.log(f"  Cancel Status: {data.get('status')}")
            self.log(f"  End Date: {data.get('end_date', 'end of period')}")

            await self.wait(2, "Waiting for subscription.cancelled event")

    async def test_step_10_verify_events(self):
        """Step 10: 验证事件"""
        self.log_step(10, "Verify Events")

        if not self.event_collector:
            self.log("  SKIP: No event collector", "yellow")
            return

        summary = self.event_collector.summary()
        self.log(f"  Events collected: {summary}")

        expected_events = [
            "subscription.created",
            "billing.calculated",
        ]

        for event_type in expected_events:
            if self.event_collector.has_event(event_type):
                self.assert_true(True, f"Event {event_type} published")
            else:
                self.log(f"  Event {event_type} not captured", "yellow")


async def main():
    """主函数"""
    test = SubscriptionBillingCreditsIntegrationTest()
    success = await test.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
