#!/usr/bin/env python3
"""
集成测试基类

提供所有集成测试共享的基础功能
"""

import asyncio
import os
import sys
from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../..")
sys.path.insert(0, _project_root)
sys.path.insert(0, _current_dir)

from conftest import TestConfig, EventCollector, TestDataGenerator


class BaseIntegrationTest(ABC):
    """集成测试基类"""

    def __init__(self):
        self.config = TestConfig()
        self.test_data = TestDataGenerator()
        self.http_client: Optional[httpx.AsyncClient] = None
        self.event_collector: Optional[EventCollector] = None
        self.event_bus = None
        self.db_pools: Dict[str, Any] = {}

        # Test state
        self.passed_assertions = 0
        self.failed_assertions = 0
        self.test_start_time: Optional[datetime] = None
        self.created_resources: List[Dict[str, Any]] = []  # 用于清理

    async def setup(self):
        """测试前置设置"""
        self.test_start_time = datetime.utcnow()
        self.http_client = httpx.AsyncClient(timeout=self.config.HTTP_TIMEOUT)

        # 连接事件总线
        try:
            from core.nats_client import get_event_bus
            self.event_bus = await get_event_bus("integration_test")
            self.event_collector = EventCollector()
            await self.event_bus.subscribe_to_events(
                pattern=">",
                handler=self.event_collector.collect
            )
            await asyncio.sleep(0.5)
            self.log("Connected to NATS event bus")
        except Exception as e:
            self.log(f"Warning: Could not connect to NATS: {e}")

    async def teardown(self):
        """测试后置清理"""
        if self.http_client:
            await self.http_client.aclose()
        if self.event_bus:
            await self.event_bus.close()

        # 清理创建的资源
        await self._cleanup_resources()

    async def _cleanup_resources(self):
        """清理测试中创建的资源"""
        for resource in reversed(self.created_resources):
            try:
                resource_type = resource.get("type")
                resource_id = resource.get("id")
                cleanup_url = resource.get("cleanup_url")

                if cleanup_url and self.http_client:
                    # 尝试删除资源
                    response = await self.http_client.delete(cleanup_url)
                    if response.status_code in [200, 204, 404]:
                        self.log(f"Cleaned up {resource_type}: {resource_id}")
                    else:
                        self.log(f"Warning: Could not cleanup {resource_type} {resource_id}: {response.status_code}")
            except Exception as e:
                self.log(f"Warning: Cleanup error for {resource}: {e}")

    def track_resource(self, resource_type: str, resource_id: str, cleanup_url: str):
        """跟踪创建的资源以便清理"""
        self.created_resources.append({
            "type": resource_type,
            "id": resource_id,
            "cleanup_url": cleanup_url
        })

    # ==================== 断言方法 ====================

    def assert_true(self, condition: bool, message: str) -> bool:
        """断言为真"""
        if condition:
            self.passed_assertions += 1
            self.log(f"  PASS: {message}", "green")
            return True
        else:
            self.failed_assertions += 1
            self.log(f"  FAIL: {message}", "red")
            return False

    def assert_false(self, condition: bool, message: str) -> bool:
        """断言为假"""
        return self.assert_true(not condition, message)

    def assert_equal(self, actual: Any, expected: Any, message: str) -> bool:
        """断言相等"""
        if actual == expected:
            self.passed_assertions += 1
            self.log(f"  PASS: {message}", "green")
            return True
        else:
            self.failed_assertions += 1
            self.log(f"  FAIL: {message} (expected: {expected}, actual: {actual})", "red")
            return False

    def assert_not_none(self, value: Any, message: str) -> bool:
        """断言不为空"""
        return self.assert_true(value is not None, message)

    def assert_in(self, item: Any, container: Any, message: str) -> bool:
        """断言包含"""
        return self.assert_true(item in container, message)

    def assert_http_success(self, response: httpx.Response, expected_status: int = 200) -> bool:
        """断言 HTTP 请求成功"""
        success = response.status_code == expected_status
        if success:
            self.passed_assertions += 1
            self.log(f"  PASS: HTTP {response.status_code}", "green")
        else:
            self.failed_assertions += 1
            self.log(f"  FAIL: Expected HTTP {expected_status}, got {response.status_code}: {response.text[:200]}", "red")
        return success

    async def assert_event_published(
        self,
        event_type: str,
        timeout: float = 10.0,
        data_match: Optional[Dict] = None
    ) -> Optional[Dict]:
        """断言事件已发布"""
        if not self.event_collector:
            self.log(f"  SKIP: Event verification (no NATS connection)", "yellow")
            return None

        event = await self.event_collector.wait_for_event(event_type, timeout, data_match)
        if event:
            self.passed_assertions += 1
            self.log(f"  PASS: Event {event_type} published", "green")
            return event
        else:
            self.failed_assertions += 1
            self.log(f"  FAIL: Event {event_type} not published within {timeout}s", "red")
            return None

    # ==================== HTTP 请求方法 ====================

    async def post(self, url: str, json: Dict = None, params: Dict = None, headers: Dict = None, files: Dict = None) -> httpx.Response:
        """POST 请求"""
        return await self.http_client.post(url, json=json, params=params, headers=headers, files=files)

    async def get(self, url: str, params: Dict = None, headers: Dict = None) -> httpx.Response:
        """GET 请求"""
        return await self.http_client.get(url, params=params, headers=headers)

    async def put(self, url: str, json: Dict = None, params: Dict = None, headers: Dict = None) -> httpx.Response:
        """PUT 请求"""
        return await self.http_client.put(url, json=json, params=params, headers=headers)

    async def delete(self, url: str, params: Dict = None, json: Dict = None, headers: Dict = None) -> httpx.Response:
        """DELETE 请求"""
        # httpx supports json body for DELETE via content parameter
        if json:
            import json as json_lib
            headers = headers or {}
            headers["Content-Type"] = "application/json"
            return await self.http_client.request("DELETE", url, params=params, content=json_lib.dumps(json), headers=headers)
        return await self.http_client.delete(url, params=params, headers=headers)

    # ==================== 日志方法 ====================

    def log(self, message: str, color: str = None):
        """打印日志"""
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "cyan": "\033[96m",
            "reset": "\033[0m"
        }

        timestamp = datetime.utcnow().strftime("%H:%M:%S")

        if color and color in colors:
            print(f"[{timestamp}] {colors[color]}{message}{colors['reset']}")
        else:
            print(f"[{timestamp}] {message}")

    def log_header(self, title: str):
        """打印测试标题"""
        print()
        print("=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def log_step(self, step_num: int, description: str):
        """打印测试步骤"""
        print()
        print(f"Step {step_num}: {description}")
        print("-" * 40)

    def log_summary(self):
        """打印测试摘要"""
        total = self.passed_assertions + self.failed_assertions
        pass_rate = (self.passed_assertions / total * 100) if total > 0 else 0
        duration = (datetime.utcnow() - self.test_start_time).total_seconds() if self.test_start_time else 0

        print()
        print("=" * 80)
        print("  TEST SUMMARY")
        print("=" * 80)
        print(f"  Total Assertions: {total}")
        print(f"  Passed: {self.passed_assertions}")
        print(f"  Failed: {self.failed_assertions}")
        print(f"  Pass Rate: {pass_rate:.1f}%")
        print(f"  Duration: {duration:.2f}s")
        print()

        if self.event_collector:
            summary = self.event_collector.summary()
            if summary:
                print("  Events Collected:")
                for event_type, count in sorted(summary.items()):
                    print(f"    - {event_type}: {count}")
                print()

        if self.failed_assertions == 0:
            self.log("ALL TESTS PASSED!", "green")
        else:
            self.log(f"{self.failed_assertions} ASSERTION(S) FAILED", "red")

        print("=" * 80)

    # ==================== 工具方法 ====================

    async def wait(self, seconds: float, reason: str = ""):
        """等待指定时间"""
        if reason:
            self.log(f"Waiting {seconds}s: {reason}", "cyan")
        await asyncio.sleep(seconds)

    def generate_test_email(self) -> str:
        """生成测试邮箱"""
        return self.test_data.email()

    def generate_test_user_id(self) -> str:
        """生成测试用户 ID"""
        return self.test_data.user_id()

    def generate_test_device_id(self) -> str:
        """生成测试设备 ID"""
        return self.test_data.device_id()
