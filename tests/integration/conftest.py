#!/usr/bin/env python3
"""
集成测试 Pytest 配置和 Fixtures

提供所有集成测试共享的 fixtures 和配置
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional

import pytest
import pytest_asyncio
import httpx
import asyncpg

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.nats_client import Event, EventType, ServiceSource, get_event_bus


# ==================== 环境配置 ====================

class TestConfig:
    """测试配置"""

    # Service URLs (通过 APISIX Gateway 或直接访问)
    AUTH_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8201")
    ACCOUNT_URL = os.getenv("ACCOUNT_BASE_URL", "http://localhost:8202")
    DEVICE_URL = os.getenv("DEVICE_BASE_URL", "http://localhost:8203")
    ORGANIZATION_URL = os.getenv("ORG_BASE_URL", "http://localhost:8204")
    SESSION_URL = os.getenv("SESSION_BASE_URL", "http://localhost:8205")
    NOTIFICATION_URL = os.getenv("NOTIFICATION_BASE_URL", "http://localhost:8206")
    CALENDAR_URL = os.getenv("CALENDAR_BASE_URL", "http://localhost:8207")
    TASK_URL = os.getenv("TASK_BASE_URL", "http://localhost:8208")
    STORAGE_URL = os.getenv("STORAGE_BASE_URL", "http://localhost:8209")
    BILLING_URL = os.getenv("BILLING_BASE_URL", "http://localhost:8210")
    WALLET_URL = os.getenv("WALLET_BASE_URL", "http://localhost:8211")
    PRODUCT_URL = os.getenv("PRODUCT_BASE_URL", "http://localhost:8212")
    PAYMENT_URL = os.getenv("PAYMENT_BASE_URL", "http://localhost:8213")
    ORDER_URL = os.getenv("ORDER_BASE_URL", "http://localhost:8214")
    SUBSCRIPTION_URL = os.getenv("SUBSCRIPTION_BASE_URL", "http://localhost:8215")
    LOCATION_URL = os.getenv("LOCATION_BASE_URL", "http://localhost:8216")
    OTA_URL = os.getenv("OTA_BASE_URL", "http://localhost:8217")
    TELEMETRY_URL = os.getenv("TELEMETRY_BASE_URL", "http://localhost:8218")
    ALBUM_URL = os.getenv("ALBUM_BASE_URL", "http://localhost:8219")
    MEDIA_URL = os.getenv("MEDIA_BASE_URL", "http://localhost:8222")
    AUTHORIZATION_URL = os.getenv("AUTHORIZATION_BASE_URL", "http://localhost:8220")
    INVITATION_URL = os.getenv("INVITATION_BASE_URL", "http://localhost:8221")
    MEMORY_URL = os.getenv("MEMORY_BASE_URL", "http://localhost:8223")
    VAULT_URL = os.getenv("VAULT_BASE_URL", "http://localhost:8224")
    AUDIT_URL = os.getenv("AUDIT_BASE_URL", "http://localhost:8225")
    COMPLIANCE_URL = os.getenv("COMPLIANCE_BASE_URL", "http://localhost:8226")
    DOCUMENT_URL = os.getenv("DOCUMENT_BASE_URL", "http://localhost:8227")
    EVENT_URL = os.getenv("EVENT_BASE_URL", "http://localhost:8228")
    WEATHER_URL = os.getenv("WEATHER_BASE_URL", "http://localhost:8229")

    # Database
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

    # NATS
    NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

    # Test settings
    EVENT_WAIT_TIMEOUT = int(os.getenv("EVENT_WAIT_TIMEOUT", "10"))
    HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))


# ==================== Event Collector ====================

class EventCollector:
    """事件收集器 - 用于集成测试中验证事件发布"""

    def __init__(self):
        self.events: list[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def collect(self, event: Event):
        """收集事件"""
        async with self._lock:
            self.events.append({
                "id": event.id,
                "type": event.type,
                "source": event.source,
                "data": event.data,
                "timestamp": event.timestamp,
                "received_at": datetime.utcnow().isoformat()
            })

    def get_by_type(self, event_type: str) -> list[Dict[str, Any]]:
        """按类型获取事件"""
        return [e for e in self.events if e["type"] == event_type]

    def get_by_source(self, source: str) -> list[Dict[str, Any]]:
        """按来源获取事件"""
        return [e for e in self.events if e["source"] == source]

    def has_event(self, event_type: str, data_match: Optional[Dict] = None) -> bool:
        """检查是否收到特定事件"""
        events = self.get_by_type(event_type)
        if not events:
            return False
        if data_match is None:
            return True
        for event in events:
            if all(event["data"].get(k) == v for k, v in data_match.items()):
                return True
        return False

    async def wait_for_event(
        self,
        event_type: str,
        timeout: float = 10.0,
        data_match: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """等待特定事件"""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if self.has_event(event_type, data_match):
                events = self.get_by_type(event_type)
                if data_match:
                    for e in events:
                        if all(e["data"].get(k) == v for k, v in data_match.items()):
                            return e
                return events[-1] if events else None
            await asyncio.sleep(0.1)
        return None

    def clear(self):
        """清空事件"""
        self.events.clear()

    def summary(self) -> Dict[str, int]:
        """获取事件统计摘要"""
        summary = {}
        for event in self.events:
            event_type = event["type"]
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary


# ==================== Test Data Generator ====================

class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def user_id() -> str:
        return f"usr_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def device_id() -> str:
        return f"dev_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def org_id() -> str:
        return f"org_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def order_id() -> str:
        return f"ord_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def wallet_id() -> str:
        return f"wal_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def email() -> str:
        return f"test_{uuid.uuid4().hex[:8]}@integration-test.local"

    @staticmethod
    def phone() -> str:
        return f"+1555{uuid.uuid4().hex[:7]}"

    @staticmethod
    def serial_number() -> str:
        return f"SN-TEST-{uuid.uuid4().hex[:12].upper()}"


# ==================== Pytest Fixtures ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def config():
    """测试配置"""
    return TestConfig()


@pytest_asyncio.fixture(scope="function")
async def http_client(config: TestConfig) -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP 客户端"""
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def event_bus():
    """NATS 事件总线"""
    bus = None
    try:
        bus = await get_event_bus("integration_test")
        yield bus
    except Exception as e:
        print(f"Warning: Could not connect to NATS: {e}")
        yield None
    finally:
        if bus:
            await bus.close()


@pytest_asyncio.fixture(scope="function")
async def event_collector(event_bus) -> AsyncGenerator[EventCollector, None]:
    """事件收集器"""
    collector = EventCollector()

    if event_bus:
        # 订阅所有事件
        await event_bus.subscribe_to_events(
            pattern=">",
            handler=collector.collect
        )
        await asyncio.sleep(0.5)  # 等待订阅建立

    yield collector

    collector.clear()


@pytest_asyncio.fixture(scope="function")
async def db_pools(config: TestConfig) -> AsyncGenerator[Dict[str, asyncpg.Pool], None]:
    """数据库连接池"""
    pools = {}
    databases = [
        "auth_db", "account_db", "device_db", "organization_db",
        "billing_db", "wallet_db", "payment_db", "order_db",
        "subscription_db", "product_db", "session_db", "notification_db",
        "storage_db", "media_db", "album_db", "location_db",
        "ota_db", "telemetry_db", "memory_db", "vault_db",
        "audit_db", "compliance_db", "document_db", "calendar_db",
        "task_db", "invitation_db", "authorization_db", "event_db"
    ]

    for db_name in databases:
        try:
            pool = await asyncpg.create_pool(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD,
                database=db_name,
                min_size=1,
                max_size=2
            )
            pools[db_name] = pool
        except Exception as e:
            print(f"Warning: Could not connect to {db_name}: {e}")

    yield pools

    for pool in pools.values():
        await pool.close()


@pytest.fixture
def test_data():
    """测试数据生成器"""
    return TestDataGenerator()


# ==================== Pytest Markers ====================

def pytest_configure(config):
    """配置自定义 markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_nats: marks tests that require NATS connection"
    )
    config.addinivalue_line(
        "markers", "requires_db: marks tests that require database connection"
    )


# ==================== Test Helpers ====================

async def assert_event_published(
    collector: EventCollector,
    event_type: str,
    timeout: float = 10.0,
    data_match: Optional[Dict] = None
) -> Dict[str, Any]:
    """断言事件已发布"""
    event = await collector.wait_for_event(event_type, timeout, data_match)
    assert event is not None, f"Expected event {event_type} was not published within {timeout}s"
    return event


async def assert_http_success(response: httpx.Response, expected_status: int = 200):
    """断言 HTTP 请求成功"""
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}: {response.text}"
    return response.json() if response.content else None


async def cleanup_test_data(db_pools: Dict[str, asyncpg.Pool], user_id: str):
    """清理测试数据"""
    cleanup_queries = {
        "account_db": "DELETE FROM users WHERE user_id = $1",
        "wallet_db": "DELETE FROM wallets WHERE user_id = $1",
        "device_db": "DELETE FROM devices WHERE owner_id = $1",
        "order_db": "DELETE FROM orders WHERE user_id = $1",
        "billing_db": "DELETE FROM billing_records WHERE user_id = $1",
        "session_db": "DELETE FROM sessions WHERE user_id = $1",
    }

    for db_name, query in cleanup_queries.items():
        if db_name in db_pools:
            try:
                async with db_pools[db_name].acquire() as conn:
                    await conn.execute(query, user_id)
            except Exception as e:
                print(f"Warning: Could not cleanup {db_name}: {e}")
