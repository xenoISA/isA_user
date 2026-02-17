#!/usr/bin/env python3
"""
集成测试主运行器

运行所有集成测试并生成报告

使用方式:
    python run_all_integration_tests.py              # 运行所有测试
    python run_all_integration_tests.py --p0         # 只运行 P0 测试
    python run_all_integration_tests.py --p1         # 只运行 P1 测试
    python run_all_integration_tests.py --p2         # 只运行 P2 测试
    python run_all_integration_tests.py --test 01    # 运行特定测试
    python run_all_integration_tests.py --parallel   # 并行运行 (实验性)
"""

import argparse
import asyncio
import importlib
import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../..")
sys.path.insert(0, _project_root)
sys.path.insert(0, _current_dir)

# 测试定义
TEST_SUITES = {
    # P0 - 关键业务流程
    "01": {
        "name": "User Lifecycle",
        "module": "test_01_user_lifecycle",
        "class": "UserLifecycleIntegrationTest",
        "priority": "P0",
        "description": "用户注册、登录、Token 管理完整流程"
    },
    "02": {
        "name": "Order Payment Flow",
        "module": "test_02_order_payment_flow",
        "class": "OrderPaymentFlowIntegrationTest",
        "priority": "P0",
        "description": "订单创建、支付、钱包扣款完整流程"
    },
    "03": {
        "name": "User Deletion Cascade",
        "module": "test_03_user_deletion_cascade",
        "class": "UserDeletionCascadeIntegrationTest",
        "priority": "P0",
        "description": "用户删除时的级联清理验证"
    },

    # P1 - 核心功能流程
    "04": {
        "name": "File Media Album Pipeline",
        "module": "test_04_file_media_album_pipeline",
        "class": "FileMediaAlbumPipelineIntegrationTest",
        "priority": "P1",
        "description": "文件上传、媒体处理、相册管理流程"
    },
    "05": {
        "name": "Organization Permissions",
        "module": "test_05_organization_permissions",
        "class": "OrganizationPermissionsIntegrationTest",
        "priority": "P1",
        "description": "组织创建、邀请、权限管理流程"
    },
    "06": {
        "name": "Device OTA Telemetry",
        "module": "test_06_device_ota_telemetry",
        "class": "DeviceOtaTelemetryIntegrationTest",
        "priority": "P1",
        "description": "设备注册、OTA更新、遥测数据流程"
    },

    # P2 - 扩展功能流程
    "07": {
        "name": "Subscription Billing Credits",
        "module": "test_07_subscription_billing_credits",
        "class": "SubscriptionBillingCreditsIntegrationTest",
        "priority": "P2",
        "description": "订阅、计费、积分管理流程"
    },
    "08": {
        "name": "Session Memory",
        "module": "test_08_session_memory",
        "class": "SessionMemoryIntegrationTest",
        "priority": "P2",
        "description": "会话管理、记忆提取和检索流程"
    },
}


class IntegrationTestRunner:
    """集成测试运行器"""

    def __init__(self, args):
        self.args = args
        self.results: Dict[str, Dict] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def print_header(self):
        """打印标题"""
        print()
        print("=" * 80)
        print("  isA User Microservices - Integration Test Suite")
        print("=" * 80)
        print(f"  Start Time: {datetime.utcnow().isoformat()}")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Working Directory: {os.getcwd()}")
        print("=" * 80)
        print()

    def get_tests_to_run(self) -> List[str]:
        """获取要运行的测试列表"""
        if self.args.test:
            # 运行特定测试
            return [self.args.test] if self.args.test in TEST_SUITES else []

        tests = []
        for test_id, info in TEST_SUITES.items():
            priority = info["priority"]

            if self.args.p0 and priority == "P0":
                tests.append(test_id)
            elif self.args.p1 and priority == "P1":
                tests.append(test_id)
            elif self.args.p2 and priority == "P2":
                tests.append(test_id)
            elif not (self.args.p0 or self.args.p1 or self.args.p2):
                # 没有指定优先级，运行所有
                tests.append(test_id)

        return sorted(tests)

    async def run_single_test(self, test_id: str) -> Tuple[bool, Dict]:
        """运行单个测试"""
        info = TEST_SUITES.get(test_id)
        if not info:
            return False, {"error": "Test not found"}

        module_name = info["module"]
        class_name = info["class"]

        print()
        print("-" * 80)
        print(f"  [{info['priority']}] Test {test_id}: {info['name']}")
        print(f"  {info['description']}")
        print("-" * 80)

        try:
            # 动态导入测试模块 (从当前目录)
            module = importlib.import_module(module_name)
            test_class = getattr(module, class_name)

            # 创建测试实例并运行
            test_instance = test_class()
            success = await test_instance.run()

            return success, {
                "passed": test_instance.passed_assertions,
                "failed": test_instance.failed_assertions,
                "duration": (datetime.utcnow() - test_instance.test_start_time).total_seconds()
                    if test_instance.test_start_time else 0
            }

        except ImportError as e:
            print(f"  ERROR: Could not import test module: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            print(f"  ERROR: Test execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False, {"error": str(e)}

    async def run_all_tests(self):
        """运行所有测试"""
        self.start_time = datetime.utcnow()
        self.print_header()

        tests_to_run = self.get_tests_to_run()

        if not tests_to_run:
            print("No tests to run!")
            return

        print(f"Running {len(tests_to_run)} test(s):")
        for test_id in tests_to_run:
            info = TEST_SUITES[test_id]
            print(f"  [{info['priority']}] {test_id}: {info['name']}")
        print()

        # 运行测试
        for test_id in tests_to_run:
            success, result = await self.run_single_test(test_id)
            self.results[test_id] = {
                "success": success,
                "info": TEST_SUITES[test_id],
                **result
            }

        self.end_time = datetime.utcnow()
        self.print_summary()

    def print_summary(self):
        """打印摘要"""
        print()
        print("=" * 80)
        print("  TEST SUMMARY")
        print("=" * 80)
        print()

        total_passed = 0
        total_failed = 0
        total_assertions_passed = 0
        total_assertions_failed = 0

        # 按优先级分组
        by_priority = {"P0": [], "P1": [], "P2": []}

        for test_id, result in self.results.items():
            priority = result["info"]["priority"]
            by_priority[priority].append((test_id, result))

            if result["success"]:
                total_passed += 1
            else:
                total_failed += 1

            total_assertions_passed += result.get("passed", 0)
            total_assertions_failed += result.get("failed", 0)

        # 打印每个优先级的结果
        for priority in ["P0", "P1", "P2"]:
            tests = by_priority[priority]
            if not tests:
                continue

            print(f"  [{priority}] Tests:")
            for test_id, result in tests:
                status = "PASS" if result["success"] else "FAIL"
                status_color = "\033[92m" if result["success"] else "\033[91m"
                reset = "\033[0m"
                duration = result.get("duration", 0)
                print(f"    {status_color}{status}{reset} - {test_id}: {result['info']['name']} ({duration:.1f}s)")

                if not result["success"] and result.get("error"):
                    print(f"         Error: {result['error']}")

            print()

        # 总体统计
        total_tests = total_passed + total_failed
        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        total_duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0

        print("-" * 80)
        print(f"  Total Tests:       {total_tests}")
        print(f"  Passed:            {total_passed}")
        print(f"  Failed:            {total_failed}")
        print(f"  Pass Rate:         {pass_rate:.1f}%")
        print()
        print(f"  Total Assertions:  {total_assertions_passed + total_assertions_failed}")
        print(f"  Assertions Passed: {total_assertions_passed}")
        print(f"  Assertions Failed: {total_assertions_failed}")
        print()
        print(f"  Total Duration:    {total_duration:.1f}s")
        print("=" * 80)

        if total_failed == 0:
            print("\n  ALL TESTS PASSED!")
        else:
            print(f"\n  {total_failed} TEST(S) FAILED")

        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("--p0", action="store_true", help="Run only P0 (critical) tests")
    parser.add_argument("--p1", action="store_true", help="Run only P1 (high priority) tests")
    parser.add_argument("--p2", action="store_true", help="Run only P2 (medium priority) tests")
    parser.add_argument("--test", type=str, help="Run specific test by ID (e.g., 01, 02)")
    parser.add_argument("--list", action="store_true", help="List all available tests")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel (experimental)")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Integration Tests:")
        print("-" * 60)
        for test_id, info in TEST_SUITES.items():
            print(f"  [{info['priority']}] {test_id}: {info['name']}")
            print(f"       {info['description']}")
        print()
        return 0

    runner = IntegrationTestRunner(args)
    asyncio.run(runner.run_all_tests())

    # 返回退出码
    failed_count = sum(1 for r in runner.results.values() if not r["success"])
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
