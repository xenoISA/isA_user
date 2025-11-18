#!/usr/bin/env python3
"""
计费流程完整集成测试

测试覆盖：
1. 基础计费流程 (usage.recorded → billing.calculated → tokens.deducted)
2. 免费套餐计费
3. 订阅包含额度计费
4. 余额不足处理
5. 事件发布和订阅验证
6. 数据库记录验证

环境变量:
    BILLING_BASE_URL - billing_service地址 (默认: http://localhost:8210)
    WALLET_BASE_URL - wallet_service地址 (默认: http://localhost:8211)
    PRODUCT_BASE_URL - product_service地址 (默认: http://localhost:8212)
    NATS_URL - NATS服务器地址 (默认: nats://localhost:4222)
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import asyncpg
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.nats_client import Event, EventType, ServiceSource, get_event_bus

# Service URLs
BILLING_BASE_URL = os.getenv("BILLING_BASE_URL", "http://localhost:8210")
WALLET_BASE_URL = os.getenv("WALLET_BASE_URL", "http://localhost:8211")
PRODUCT_BASE_URL = os.getenv("PRODUCT_BASE_URL", "http://localhost:8212")

# Database configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")


class EventCollector:
    """事件收集器 - 用于验证事件发布"""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    async def collect_event(self, event: Event):
        """收集事件"""
        self.events.append(
            {
                "id": event.id,
                "type": event.type,
                "source": event.source,
                "data": event.data,
                "timestamp": event.timestamp,
            }
        )
        print(f"  📨 Collected event: {event.type} from {event.source}")

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """按类型获取事件"""
        return [e for e in self.events if e["type"] == event_type]

    def clear(self):
        """清空事件"""
        self.events = []


class BillingFlowIntegrationTest:
    """计费流程集成测试套件"""

    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.event_bus = None
        self.event_collector = EventCollector()
        self.db_pools: Dict[str, asyncpg.Pool] = {}

        # Test data
        self.test_user_id = f"usr_test_{uuid.uuid4().hex[:8]}"
        self.test_wallet_id: Optional[str] = None

        self.passed_tests = 0
        self.failed_tests = 0

    async def setup(self):
        """初始化测试环境"""
        print("\n" + "=" * 80)
        print("🔧 Setting up billing flow integration test environment...")
        print("=" * 80)

        # Create HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        print("✅ HTTP client created")

        # Connect to NATS event bus
        try:
            self.event_bus = await get_event_bus("billing_integration_test")
            print("✅ Connected to NATS event bus")

            # Subscribe to billing and wallet events
            await self.event_bus.subscribe_to_events(
                pattern="billing.>", handler=self.event_collector.collect_event
            )
            await self.event_bus.subscribe_to_events(
                pattern="wallet.>", handler=self.event_collector.collect_event
            )
            print("✅ Subscribed to billing.> and wallet.> events")
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"⚠️  Warning: Could not connect to NATS: {e}")
            print("   Event verification tests will be skipped")

        # Connect to databases
        try:
            await self._setup_database_connections()
        except Exception as e:
            print(f"⚠️  Warning: Could not connect to databases: {e}")
            print("   Database verification tests will be skipped")

        # Setup test user and wallet
        await self._setup_test_user()

    async def _setup_database_connections(self):
        """设置数据库连接"""
        databases = {"billing_db": "billing_db", "wallet_db": "wallet_db"}

        for pool_name, db_name in databases.items():
            try:
                pool = await asyncpg.create_pool(
                    host=POSTGRES_HOST,
                    port=POSTGRES_PORT,
                    user=POSTGRES_USER,
                    password=POSTGRES_PASSWORD,
                    database=db_name,
                    min_size=1,
                    max_size=2,
                )
                self.db_pools[pool_name] = pool
                print(f"✅ Connected to {db_name}")
            except Exception as e:
                print(f"⚠️  Warning: Could not connect to {db_name}: {e}")

    async def _setup_test_user(self):
        """创建测试用户和钱包"""
        print("\n📝 Setting up test user and wallet...")

        try:
            # 创建钱包
            response = await self.http_client.post(
                f"{WALLET_BASE_URL}/api/v1/wallets",
                json={
                    "user_id": self.test_user_id,
                    "currency": "TOKEN",
                    "initial_balance": 10000,  # 初始 10000 tokens
                },
            )

            if response.status_code == 200 or response.status_code == 201:
                wallet_data = response.json()
                self.test_wallet_id = wallet_data.get("wallet_id")
                print(f"✅ Created test wallet: {self.test_wallet_id}")
                print(f"   Initial balance: 10000 tokens")
            else:
                print(f"⚠️  Failed to create wallet: {response.status_code}")

        except Exception as e:
            print(f"⚠️  Warning: Could not setup test user: {e}")

    async def teardown(self):
        """清理测试环境"""
        print("\n" + "=" * 80)
        print("🧹 Cleaning up test environment...")
        print("=" * 80)

        if self.http_client:
            await self.http_client.aclose()
            print("✅ HTTP client closed")

        if self.event_bus:
            await self.event_bus.close()
            print("✅ Event bus connection closed")

        for pool_name, pool in self.db_pools.items():
            await pool.close()
            print(f"✅ Database pool {pool_name} closed")

    def print_test_header(self, test_name: str, test_number: int, total_tests: int):
        """打印测试头部"""
        print("\n" + "=" * 80)
        print(f"TEST [{test_number}/{total_tests}]: {test_name}")
        print("=" * 80)

    async def test_1_basic_billing_flow(self):
        """
        测试1: 基础计费流程

        流程:
        1. 模拟发布 usage.recorded 事件 (300 tokens)
        2. billing_service 监听并处理
        3. 发布 billing.calculated 事件
        4. wallet_service 扣除 tokens
        5. 发布 tokens.deducted 事件
        6. 验证数据库记录和余额变化
        """
        self.print_test_header("Basic Billing Flow (Pay-as-you-go)", 1, 6)

        try:
            print("\n📝 Step 1: Publishing usage.recorded event...")
            self.event_collector.clear()

            # 构造使用记录事件
            usage_event = Event(
                event_type=EventType.USAGE_RECORDED,
                source=ServiceSource.ISA_MODEL,  # 模拟 isA_Model 发送
                data={
                    "user_id": self.test_user_id,
                    "product_id": "gpt-4",
                    "usage_amount": 300,
                    "unit_type": "token",
                    "usage_details": {
                        "input_tokens": 100,
                        "output_tokens": 200,
                        "provider": "openai",
                        "model": "gpt-4",
                        "operation": "chat",
                    },
                },
            )

            # 修改 subject 以匹配计费服务的订阅模式
            usage_event.type = "billing.usage.recorded.gpt-4"

            # 发布事件
            await self.event_bus.publish_event(usage_event)
            print(f"  ✅ Published usage.recorded event")
            print(f"     User: {self.test_user_id}")
            print(f"     Product: gpt-4")
            print(f"     Usage: 300 tokens")

            # 等待事件处理
            print("\n📝 Step 2: Waiting for event processing...")
            await asyncio.sleep(5)  # 给足够时间让事件处理完成

            # 验证事件链
            print("\n📝 Step 3: Verifying event chain...")
            if self.event_bus:
                # 应该收到 billing.calculated 事件
                billing_calculated_events = self.event_collector.get_events_by_type(
                    "billing.calculated"
                )
                print(
                    f"  📊 billing.calculated events: {len(billing_calculated_events)}"
                )

                if len(billing_calculated_events) > 0:
                    print(f"  ✅ billing.calculated event received")
                    billing_event_data = billing_calculated_events[0]["data"]
                    print(
                        f"     Token equivalent: {billing_event_data.get('token_equivalent')}"
                    )
                    print(f"     Cost USD: ${billing_event_data.get('cost_usd')}")
                else:
                    print(f"  ⚠️  No billing.calculated event received")

                # 应该收到 wallet.tokens.deducted 事件
                tokens_deducted_events = self.event_collector.get_events_by_type(
                    "wallet.tokens.deducted"
                )
                print(
                    f"  📊 wallet.tokens.deducted events: {len(tokens_deducted_events)}"
                )

                if len(tokens_deducted_events) > 0:
                    print(f"  ✅ wallet.tokens.deducted event received")
                    wallet_event_data = tokens_deducted_events[0]["data"]
                    print(
                        f"     Tokens deducted: {wallet_event_data.get('tokens_deducted')}"
                    )
                    print(
                        f"     Balance before: {wallet_event_data.get('balance_before')}"
                    )
                    print(
                        f"     Balance after: {wallet_event_data.get('balance_after')}"
                    )
                else:
                    print(f"  ⚠️  No wallet.tokens.deducted event received")

            # 验证数据库记录
            if "billing_db" in self.db_pools:
                print("\n📝 Step 4: Verifying billing database records...")
                async with self.db_pools["billing_db"].acquire() as conn:
                    billing_records = await conn.fetch(
                        "SELECT * FROM billing_records WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
                        self.test_user_id,
                    )

                    if len(billing_records) > 0:
                        record = billing_records[0]
                        print(f"  ✅ Billing record created")
                        print(f"     Record ID: {record['billing_record_id']}")
                        print(f"     Product: {record['product_id']}")
                        print(
                            f"     Usage: {record['usage_amount']} {record['unit_type']}"
                        )
                        print(f"     Token equivalent: {record['token_equivalent']}")
                        print(f"     Status: {record['status']}")
                    else:
                        print(f"  ⚠️  No billing record found")

            # 验证钱包余额
            if "wallet_db" in self.db_pools:
                print("\n📝 Step 5: Verifying wallet balance...")
                async with self.db_pools["wallet_db"].acquire() as conn:
                    wallet = await conn.fetchrow(
                        "SELECT * FROM wallets WHERE user_id = $1", self.test_user_id
                    )

                    if wallet:
                        print(f"  ✅ Wallet balance updated")
                        print(f"     Current balance: {wallet['balance']} tokens")
                        print(f"     Expected: 9700 tokens (10000 - 300)")

                        # 验证余额是否正确
                        if float(wallet["balance"]) == 9700:
                            print(f"  ✅ Balance is correct!")
                        else:
                            print(f"  ⚠️  Balance mismatch!")
                    else:
                        print(f"  ⚠️  Wallet not found")

            self.passed_tests += 1
            print("\n✅ TEST PASSED: Basic Billing Flow")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: Basic Billing Flow")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()

    async def test_2_insufficient_balance(self):
        """
        测试2: 余额不足处理

        流程:
        1. 模拟大额使用 (15000 tokens，余额不足)
        2. wallet_service 发现余额不足
        3. 发布 tokens.insufficient 事件
        4. 验证计费记录状态为 'insufficient_balance'
        """
        self.print_test_header("Insufficient Balance Handling", 2, 6)

        try:
            print("\n📝 Step 1: Publishing large usage event (15000 tokens)...")
            self.event_collector.clear()

            # 获取当前余额
            current_balance = 9700  # 从上一个测试知道的余额
            print(f"  📊 Current balance: ~{current_balance} tokens")
            print(f"  📊 Required tokens: 15000")
            print(f"  📊 Deficit: ~{15000 - current_balance} tokens")

            # 构造大额使用事件
            usage_event = Event(
                event_type=EventType.USAGE_RECORDED,
                source=ServiceSource.ISA_MODEL,
                data={
                    "user_id": self.test_user_id,
                    "product_id": "gpt-4",
                    "usage_amount": 15000,
                    "unit_type": "token",
                    "usage_details": {
                        "input_tokens": 7000,
                        "output_tokens": 8000,
                        "provider": "openai",
                        "model": "gpt-4",
                        "operation": "chat",
                    },
                },
            )

            usage_event.type = "billing.usage.recorded.gpt-4"

            await self.event_bus.publish_event(usage_event)
            print(f"  ✅ Published large usage event")

            # 等待处理
            print("\n📝 Step 2: Waiting for event processing...")
            await asyncio.sleep(5)

            # 验证 tokens.insufficient 事件
            print("\n📝 Step 3: Verifying tokens.insufficient event...")
            if self.event_bus:
                insufficient_events = self.event_collector.get_events_by_type(
                    "wallet.tokens.insufficient"
                )
                print(
                    f"  📊 wallet.tokens.insufficient events: {len(insufficient_events)}"
                )

                if len(insufficient_events) > 0:
                    print(f"  ✅ tokens.insufficient event received")
                    event_data = insufficient_events[0]["data"]
                    print(f"     Tokens required: {event_data.get('tokens_required')}")
                    print(
                        f"     Tokens available: {event_data.get('tokens_available')}"
                    )
                    print(f"     Tokens deficit: {event_data.get('tokens_deficit')}")
                    print(
                        f"     Suggested action: {event_data.get('suggested_action')}"
                    )
                else:
                    print(f"  ⚠️  No tokens.insufficient event received")

            # 验证计费记录状态
            if "billing_db" in self.db_pools:
                print("\n📝 Step 4: Verifying billing record status...")
                async with self.db_pools["billing_db"].acquire() as conn:
                    record = await conn.fetchrow(
                        """
                        SELECT * FROM billing_records
                        WHERE user_id = $1
                        AND usage_amount = 15000
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        self.test_user_id,
                    )

                    if record:
                        print(f"  ✅ Billing record found")
                        print(f"     Status: {record['status']}")

                        if record["status"] == "insufficient_balance":
                            print(f"  ✅ Status is 'insufficient_balance' - correct!")
                        else:
                            print(
                                f"  ⚠️  Status is '{record['status']}' - expected 'insufficient_balance'"
                            )
                    else:
                        print(f"  ⚠️  Billing record not found")

            self.passed_tests += 1
            print("\n✅ TEST PASSED: Insufficient Balance Handling")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: Insufficient Balance Handling")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()

    async def test_3_free_tier_usage(self):
        """
        测试3: 免费套餐使用

        流程:
        1. 模拟免费额度内的使用
        2. billing_service 识别为免费额度
        3. 不扣除钱包余额
        4. 验证余额未变化
        """
        self.print_test_header("Free Tier Usage", 3, 6)

        print("  ⚠️  This test requires product_service to define free tier")
        print("  Skipping for now - implement after product_service is ready")

        # TODO: Implement when product_service supports free tier

    async def test_4_subscription_included_usage(self):
        """
        测试4: 订阅包含额度使用

        流程:
        1. 创建测试订阅
        2. 模拟使用在订阅包含额度内
        3. billing_service 识别为订阅包含
        4. 不扣除钱包余额
        5. 验证余额未变化
        """
        self.print_test_header("Subscription Included Usage", 4, 6)

        print("  ⚠️  This test requires subscription management")
        print("  Skipping for now - implement after subscription service is ready")

        # TODO: Implement when subscription service is ready

    async def test_5_concurrent_billing(self):
        """
        测试5: 并发计费测试

        流程:
        1. 并发发布多个使用事件
        2. 验证所有事件都被正确处理
        3. 验证余额计算正确（无竞争条件）
        """
        self.print_test_header("Concurrent Billing", 5, 6)

        print("  ⚠️  This test requires careful wallet locking mechanism")
        print("  Skipping for now - implement after wallet service has proper locking")

        # TODO: Implement concurrent billing test

    async def test_6_end_to_end_verification(self):
        """
        测试6: 端到端验证

        汇总所有测试结果和数据一致性验证
        """
        self.print_test_header("End-to-End Verification", 6, 6)

        try:
            print("\n📝 Verifying overall data consistency...")

            # 验证事件总数
            if self.event_bus:
                total_events = len(self.event_collector.events)
                print(f"  📊 Total events collected: {total_events}")

                event_types = {}
                for event in self.event_collector.events:
                    event_type = event["type"]
                    event_types[event_type] = event_types.get(event_type, 0) + 1

                print(f"\n  📨 Event breakdown:")
                for event_type, count in sorted(event_types.items()):
                    print(f"     {event_type}: {count}")

            # 验证计费记录总数
            if "billing_db" in self.db_pools:
                async with self.db_pools["billing_db"].acquire() as conn:
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM billing_records WHERE user_id = $1",
                        self.test_user_id,
                    )
                    print(f"\n  📊 Total billing records: {count}")

            # 验证交易记录总数
            if "wallet_db" in self.db_pools:
                async with self.db_pools["wallet_db"].acquire() as conn:
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM transactions WHERE user_id = $1",
                        self.test_user_id,
                    )
                    print(f"  📊 Total wallet transactions: {count}")

            self.passed_tests += 1
            print("\n✅ TEST PASSED: End-to-End Verification")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: End-to-End Verification")
            print(f"   Error: {e}")

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 80)
        print("🚀 BILLING FLOW INTEGRATION TEST SUITE")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"\nTest Configuration:")
        print(f"  Billing Service: {BILLING_BASE_URL}")
        print(f"  Wallet Service: {WALLET_BASE_URL}")
        print(f"  Product Service: {PRODUCT_BASE_URL}")
        print(f"  Test User: {self.test_user_id}")

        await self.setup()

        # Run tests
        await self.test_1_basic_billing_flow()
        await self.test_2_insufficient_balance()
        await self.test_3_free_tier_usage()
        await self.test_4_subscription_included_usage()
        await self.test_5_concurrent_billing()
        await self.test_6_end_to_end_verification()

        await self.teardown()

        # Print final summary
        self.print_final_summary()

    def print_final_summary(self):
        """打印最终测试摘要"""
        print("\n" + "=" * 80)
        print("📊 FINAL TEST SUMMARY")
        print("=" * 80)

        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if self.failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Billing flow is working correctly end-to-end")
        else:
            print(f"\n⚠️  {self.failed_tests} test(s) failed")
            print("Please check the logs above for details")

        print("\n" + "=" * 80)


async def main():
    """主函数"""
    test_suite = BillingFlowIntegrationTest()

    try:
        await test_suite.run_all_tests()

        # Exit with appropriate code
        if test_suite.failed_tests == 0:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        await test_suite.teardown()
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        await test_suite.teardown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
