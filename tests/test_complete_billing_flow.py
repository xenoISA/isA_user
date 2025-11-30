#!/usr/bin/env python3
"""
完整的计费流程端到端测试

验证整个事件驱动的计费流程：
1. Model Service -> 推理请求 -> 发布 usage.recorded 事件
2. NATS -> 事件传输
3. Billing Service -> 订阅事件 -> 查询 Product Service 获取定价
4. Billing Service -> 创建 billing record in DB
5. Billing Service -> 发布 billing.calculated 事件
6. NATS -> 事件传输
7. Wallet Service -> 订阅事件 -> 扣除余额
8. Wallet Service -> 创建 transaction record in DB
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional

import aiohttp

# 测试配置
TEST_USER_ID = f"test_billing_user_{int(time.time())}"
TEST_MODEL = "gpt-4o-mini"
MODEL_API_URL = "http://localhost:8082"
BILLING_API_URL = "http://localhost:8216"
WALLET_API_URL = "http://localhost:8208"


class BillingFlowTester:
    """完整的计费流程测试器"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_start_time = datetime.utcnow()
        self.billing_record_id: Optional[str] = None
        self.wallet_transaction_id: Optional[str] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def print_step(self, step_num: int, title: str, status: str = "🔄"):
        """打印步骤信息"""
        print(f"\n{'=' * 80}")
        print(f"{status} Step {step_num}: {title}")
        print(f"{'=' * 80}")

    def print_success(self, message: str):
        """打印成功信息"""
        print(f"✅ {message}")

    def print_error(self, message: str):
        """打印错误信息"""
        print(f"❌ {message}")

    def print_info(self, message: str):
        """打印提示信息"""
        print(f"ℹ️  {message}")

    async def step1_send_model_request(self) -> bool:
        """Step 1: 发送模型推理请求"""
        self.print_step(1, "Model Service - 发送推理请求")

        try:
            # 使用唯一的 prompt 避免缓存
            unique_prompt = f"Say: Billing test at {time.time()}"

            request_data = {
                "model": TEST_MODEL,
                "task": "chat",
                "service_type": "text",
                "input_data": [{"role": "user", "content": unique_prompt}],
                "user_id": TEST_USER_ID,
            }

            print(f"📤 Sending request to Model Service...")
            print(f"   User ID: {TEST_USER_ID}")
            print(f"   Model: {TEST_MODEL}")
            print(f"   Prompt: {unique_prompt}")

            async with self.session.post(
                f"{MODEL_API_URL}/api/v1/invoke",
                json=request_data,
                headers={"Content-Type": "application/json"},
            ) as resp:
                result = await resp.json()

                if not result.get("success"):
                    self.print_error(f"Model request failed: {result.get('error')}")
                    return False

                self.print_success("Model inference successful")

                if result.get("usage"):
                    usage = result["usage"]
                    print(
                        f"   Tokens: {usage.get('total_tokens')} (input: {usage.get('input_tokens')}, output: {usage.get('output_tokens')})"
                    )

                # 等待事件发布
                print("\n⏳ Waiting 2 seconds for event publishing...")
                await asyncio.sleep(2)

                return True

        except Exception as e:
            self.print_error(f"Exception: {e}")
            return False

    async def step2_verify_billing_record(self) -> bool:
        """Step 2: 验证 Billing Service 创建了计费记录"""
        self.print_step(2, "Billing Service - 验证计费记录")

        try:
            print(f"🔍 Checking billing records for user: {TEST_USER_ID}")

            # 查询用户的计费记录
            async with self.session.get(
                f"{BILLING_API_URL}/api/v1/billing/records/user/{TEST_USER_ID}",
                params={"limit": 10},
            ) as resp:
                if resp.status != 200:
                    self.print_error(
                        f"Failed to get billing records: HTTP {resp.status}"
                    )
                    return False

                data = await resp.json()
                records = data.get("records", [])

                if not records:
                    self.print_error("No billing records found")
                    self.print_info("Possible reasons:")
                    print("   1. Billing service didn't subscribe to events")
                    print("   2. NATS event bus not working")
                    print("   3. Event handler error")
                    return False

                # 找到最新的记录
                latest_record = records[0]
                self.billing_record_id = latest_record.get("billing_record_id")

                self.print_success(f"Found billing record: {self.billing_record_id}")
                print(f"   User ID: {latest_record.get('user_id')}")
                print(f"   Product ID: {latest_record.get('product_id')}")
                print(
                    f"   Usage Amount: {latest_record.get('usage_amount')} {latest_record.get('unit_type')}"
                )
                print(f"   Cost USD: ${latest_record.get('cost_usd')}")
                print(f"   Token Equivalent: {latest_record.get('token_equivalent')}")
                print(f"   Status: {latest_record.get('status')}")
                print(f"   Created: {latest_record.get('created_at')}")

                return True

        except Exception as e:
            self.print_error(f"Exception: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def step3_verify_wallet_transaction(self) -> bool:
        """Step 3: 验证 Wallet Service 创建了交易记录"""
        self.print_step(3, "Wallet Service - 验证钱包交易")

        try:
            print(f"🔍 Checking wallet transactions for user: {TEST_USER_ID}")

            # 查询用户的钱包交易
            async with self.session.get(
                f"{WALLET_API_URL}/api/v1/wallet/transactions/user/{TEST_USER_ID}",
                params={"limit": 10},
            ) as resp:
                if resp.status != 200:
                    self.print_error(
                        f"Failed to get wallet transactions: HTTP {resp.status}"
                    )
                    return False

                data = await resp.json()
                transactions = data.get("transactions", [])

                if not transactions:
                    self.print_error("No wallet transactions found")
                    self.print_info("Possible reasons:")
                    print(
                        "   1. Wallet service didn't subscribe to billing.calculated events"
                    )
                    print(
                        "   2. Billing service didn't publish billing.calculated event"
                    )
                    print("   3. User doesn't have a wallet")
                    print("   4. Insufficient balance (transaction rejected)")
                    return False

                # 找到最新的交易
                latest_transaction = transactions[0]
                self.wallet_transaction_id = latest_transaction.get("transaction_id")

                self.print_success(
                    f"Found wallet transaction: {self.wallet_transaction_id}"
                )
                print(f"   User ID: {latest_transaction.get('user_id')}")
                print(f"   Type: {latest_transaction.get('transaction_type')}")
                print(f"   Amount: {latest_transaction.get('amount')}")
                print(f"   Balance After: {latest_transaction.get('balance_after')}")
                print(f"   Description: {latest_transaction.get('description')}")
                print(f"   Created: {latest_transaction.get('created_at')}")

                return True

        except Exception as e:
            self.print_error(f"Exception: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def step4_verify_data_consistency(self) -> bool:
        """Step 4: 验证数据一致性"""
        self.print_step(4, "Data Consistency - 验证记录关联")

        if not self.billing_record_id:
            self.print_error("No billing record ID to verify")
            return False

        try:
            # 获取详细的计费记录
            async with self.session.get(
                f"{BILLING_API_URL}/api/v1/billing/record/{self.billing_record_id}"
            ) as resp:
                if resp.status != 200:
                    self.print_error(
                        f"Failed to get billing record details: HTTP {resp.status}"
                    )
                    return False

                billing_record = await resp.json()

                # 检查关键字段
                wallet_tx_id = billing_record.get("wallet_transaction_id")

                if wallet_tx_id:
                    self.print_success("Billing record has wallet_transaction_id")
                    print(f"   Wallet Transaction ID: {wallet_tx_id}")

                    if wallet_tx_id == self.wallet_transaction_id:
                        self.print_success("Wallet transaction ID matches!")
                    else:
                        self.print_error(
                            f"Wallet transaction ID mismatch: {wallet_tx_id} != {self.wallet_transaction_id}"
                        )
                        return False
                else:
                    self.print_info(
                        "Billing record doesn't have wallet_transaction_id (may be async)"
                    )

                return True

        except Exception as e:
            self.print_error(f"Exception: {e}")
            return False

    async def run_complete_test(self):
        """运行完整的测试流程"""
        print("\n" + "=" * 80)
        print("🧪 Complete Billing Flow End-to-End Test")
        print("=" * 80)
        print(f"\nTest Configuration:")
        print(f"  User ID: {TEST_USER_ID}")
        print(f"  Model: {TEST_MODEL}")
        print(f"  Model API: {MODEL_API_URL}")
        print(f"  Billing API: {BILLING_API_URL}")
        print(f"  Wallet API: {WALLET_API_URL}")
        print(f"  Start Time: {self.test_start_time}")

        results = {}

        # Step 1: Model Request
        results["step1_model"] = await self.step1_send_model_request()
        if not results["step1_model"]:
            print("\n❌ Test failed at Step 1 (Model Request)")
            return results

        # Step 2: Billing Record
        results["step2_billing"] = await self.step2_verify_billing_record()
        if not results["step2_billing"]:
            print("\n❌ Test failed at Step 2 (Billing Record)")
            print("\n📋 Debug Information:")
            print(f"   Check billing service logs:")
            print(
                f"   kubectl logs -n isa-cloud-staging deploy/billing --tail=100 | grep '{TEST_USER_ID}'"
            )
            print(f"\n   Check NATS subscriptions:")
            print(
                f"   kubectl exec -n isa-cloud-staging deploy/billing -- env | grep NATS"
            )
            return results

        # Step 3: Wallet Transaction
        results["step3_wallet"] = await self.step3_verify_wallet_transaction()
        if not results["step3_wallet"]:
            print("\n⚠️  Test failed at Step 3 (Wallet Transaction)")
            print("\n📋 Debug Information:")
            print(f"   Check wallet service logs:")
            print(
                f"   kubectl logs -n isa-cloud-staging deploy/wallet --tail=100 | grep '{TEST_USER_ID}'"
            )
            print(f"\n   Check if user has a wallet:")
            print(f"   curl http://localhost:8208/api/v1/wallet/user/{TEST_USER_ID}")
            return results

        # Step 4: Data Consistency
        results["step4_consistency"] = await self.step4_verify_data_consistency()

        # Final Summary
        print("\n" + "=" * 80)
        print("📊 Test Results Summary")
        print("=" * 80)

        all_passed = all(results.values())

        for step, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {step}")

        if all_passed:
            print("\n🎉 All tests PASSED! Complete billing flow is working!")
            print("\n✅ Event Flow Verified:")
            print("   1. Model Service → usage.recorded event → NATS")
            print("   2. NATS → Billing Service event subscriber")
            print("   3. Billing Service → Product Service (pricing)")
            print("   4. Billing Service → Billing record in DB")
            print("   5. Billing Service → billing.calculated event → NATS")
            print("   6. NATS → Wallet Service event subscriber")
            print("   7. Wallet Service → Wallet transaction in DB")
        else:
            print("\n⚠️  Some tests failed. See details above.")

        return results


async def main():
    """主函数"""
    async with BillingFlowTester() as tester:
        results = await tester.run_complete_test()

        # 返回退出码
        return 0 if all(results.values()) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
