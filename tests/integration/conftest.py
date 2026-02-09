#!/usr/bin/env python3
"""
集成测试 Pytest 配置和 Fixtures

提供所有集成测试共享的 fixtures 和配置
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Optional

import pytest
import pytest_asyncio
import httpx
import asyncpg

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../..")
sys.path.insert(0, _project_root)
sys.path.insert(0, _current_dir)

# NATS imports - optional, may not be available locally
try:
    from core.nats_client import Event, get_event_bus
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    Event = None
    EventType = None
    ServiceSource = None
    get_event_bus = None


# ==================== 环境配置 ====================

class TestConfig:
    """测试配置"""

    # Service URLs (通过 APISIX Gateway 或直接访问)
    # Authoritative source: deployment/k8s/build-all-images.sh
    # Port order: 8201-8230 (sequential by service priority)
    AUTH_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8201")
    ACCOUNT_URL = os.getenv("ACCOUNT_BASE_URL", "http://localhost:8202")
    SESSION_URL = os.getenv("SESSION_BASE_URL", "http://localhost:8203")
    AUTHORIZATION_URL = os.getenv("AUTHORIZATION_BASE_URL", "http://localhost:8204")
    AUDIT_URL = os.getenv("AUDIT_BASE_URL", "http://localhost:8205")
    NOTIFICATION_URL = os.getenv("NOTIFICATION_BASE_URL", "http://localhost:8206")
    PAYMENT_URL = os.getenv("PAYMENT_BASE_URL", "http://localhost:8207")
    WALLET_URL = os.getenv("WALLET_BASE_URL", "http://localhost:8208")
    STORAGE_URL = os.getenv("STORAGE_BASE_URL", "http://localhost:8209")
    ORDER_URL = os.getenv("ORDER_BASE_URL", "http://localhost:8210")
    TASK_URL = os.getenv("TASK_BASE_URL", "http://localhost:8211")
    ORGANIZATION_URL = os.getenv("ORG_BASE_URL", "http://localhost:8212")
    INVITATION_URL = os.getenv("INVITATION_BASE_URL", "http://localhost:8213")
    VAULT_URL = os.getenv("VAULT_BASE_URL", "http://localhost:8214")
    PRODUCT_URL = os.getenv("PRODUCT_BASE_URL", "http://localhost:8215")
    BILLING_URL = os.getenv("BILLING_BASE_URL", "http://localhost:8216")
    CALENDAR_URL = os.getenv("CALENDAR_BASE_URL", "http://localhost:8217")
    WEATHER_URL = os.getenv("WEATHER_BASE_URL", "http://localhost:8218")
    ALBUM_URL = os.getenv("ALBUM_BASE_URL", "http://localhost:8219")
    DEVICE_URL = os.getenv("DEVICE_BASE_URL", "http://localhost:8220")
    OTA_URL = os.getenv("OTA_BASE_URL", "http://localhost:8221")
    MEDIA_URL = os.getenv("MEDIA_BASE_URL", "http://localhost:8222")
    MEMORY_URL = os.getenv("MEMORY_BASE_URL", "http://localhost:8223")
    LOCATION_URL = os.getenv("LOCATION_BASE_URL", "http://localhost:8224")
    TELEMETRY_URL = os.getenv("TELEMETRY_BASE_URL", "http://localhost:8225")
    COMPLIANCE_URL = os.getenv("COMPLIANCE_BASE_URL", "http://localhost:8226")
    DOCUMENT_URL = os.getenv("DOCUMENT_BASE_URL", "http://localhost:8227")
    SUBSCRIPTION_URL = os.getenv("SUBSCRIPTION_BASE_URL", "http://localhost:8228")
    EVENT_URL = os.getenv("EVENT_BASE_URL", "http://localhost:8230")

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
    """
    事件收集器 - 用于集成测试中验证事件发布

    重要: JetStream 消费者默认从流的开头开始消费 (DeliverAll)，
    会导致收到大量历史事件。为避免这个问题，EventCollector
    会过滤掉订阅建立之前发生的事件，只收集新事件。
    """

    def __init__(self):
        self.events: list[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        # 记录订阅开始时间，过滤历史事件
        self._subscribe_time = datetime.utcnow()

    def set_subscribe_time(self):
        """设置订阅开始时间 (在所有订阅建立后调用)"""
        self._subscribe_time = datetime.utcnow()

    async def collect(self, event: Event):
        """
        收集事件

        注意: JetStream 消费者默认使用 DeliverAll 策略，会先投递所有历史事件。
        这里通过时间戳过滤，只保留订阅时间之后的事件。

        TODO: 修改 core/nats_client.py 支持 DeliverNew 策略，
        这样消费者只会收到订阅后发布的新事件，避免历史事件堆积问题。
        """
        # 解析事件时间戳并与订阅时间比较
        try:
            event_time_str = event.timestamp
            if isinstance(event_time_str, str):
                # 移除时区后缀以便比较 (简化处理)
                event_time_str = event_time_str.replace('+00:00', '').replace('Z', '')
                if '.' in event_time_str:
                    event_time = datetime.fromisoformat(event_time_str)
                else:
                    event_time = datetime.fromisoformat(event_time_str)

                # 只收集订阅建立后的事件 (给 30 秒缓冲时间，避免时间同步问题)
                cutoff_time = self._subscribe_time - timedelta(seconds=30)
                if event_time < cutoff_time:
                    return  # 跳过历史事件
        except Exception:
            pass  # 如果解析失败，仍然收集事件

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
        return f"test_{uuid.uuid4().hex[:8]}@example.com"

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


@pytest_asyncio.fixture(scope="session")
async def event_bus():
    """
    NATS 事件总线 (session scope)

    注意: 使用 session scope 避免 async channel pool 在测试间被关闭的问题。
    isa_common.async_base_client 使用全局 channel pool，如果每个测试创建/关闭
    event_bus，会导致 channel pool 状态损坏 ("Event loop is closed" 错误)。

    每个测试通过 event_collector fixture 使用唯一的 consumer 名称来隔离事件。
    """
    if not NATS_AVAILABLE:
        yield None
        return

    from core.nats_client import NATSEventBus

    bus = None
    try:
        # 直接创建新实例，不使用 get_event_bus() 的 singleton
        bus = NATSEventBus(service_name="integration_test")
        await bus.connect()
        yield bus
    except Exception as e:
        print(f"Warning: Could not connect to NATS: {e}")
        yield None
    finally:
        if bus:
            await bus.close()


@pytest_asyncio.fixture(scope="function")
async def event_collector(event_bus) -> AsyncGenerator[EventCollector, None]:
    """
    事件收集器 - 订阅所有常用事件流

    注意: NATS gRPC gateway 按 stream 隔离事件，必须订阅具体的事件模式
    才能收到对应 stream 的事件。pattern=">" 会创建独立的 >-stream，
    无法收到 user-stream、device-stream 等的事件。

    重要: 每次测试使用唯一的 consumer 名称，避免 durable consumer 状态共享。
    JetStream durable consumer 记录消息投递位置，如果多个测试共享同一个 consumer，
    前一个测试消费的消息不会再投递给后续测试。

    Stream 映射 (定义在 core/nats_client.py._get_stream_name_for_event):
    - user.* -> user-stream (account_service 事件)
    - device.* -> device-stream
    - wallet.* -> wallet-stream
    - billing.* -> billing-stream
    - session.* -> session-stream
    - order.* -> order-stream
    - organization.* -> organization-stream
    - notification.* -> notification-stream
    - file.* -> storage-stream
    - album.* -> album-stream
    - task.* -> task-stream
    - memory.* -> memory-stream
    """
    collector = EventCollector()

    # 为每个测试生成唯一的 consumer 后缀，避免 durable consumer 状态共享
    test_id = uuid.uuid4().hex[:8]

    if event_bus:
        # 订阅各个服务的事件流 (必须分别订阅才能收到对应 stream 的事件)
        event_patterns = [
            "user.*",           # account_service: user.created, user.updated, user.deleted, user.profile_updated
            "device.*",         # device_service: device.registered, device.authenticated, etc.
            "wallet.*",         # wallet_service: wallet.created, wallet.deposited, etc.
            "billing.*",        # billing_service
            "session.*",        # session_service
            "order.*",          # order_service
            "organization.*",   # organization_service
            "subscription.*",   # subscription_service
            "payment.*",        # payment_service
            "notification.*",   # notification_service
            "file.*",           # storage_service
            "album.*",          # album_service
            "task.*",           # task_service
            "memory.*",         # memory_service
            "invitation.*",     # invitation_service
        ]

        for pattern in event_patterns:
            try:
                # 使用唯一的 consumer 名称，格式: {prefix}-test-{uuid}
                prefix = pattern.split('.')[0]
                durable_name = f"{prefix}-test-{test_id}"
                await event_bus.subscribe_to_events(
                    pattern=pattern,
                    handler=collector.collect,
                    durable=durable_name,
                    delivery_policy='new'  # 只接收新事件，跳过历史积压
                )
            except Exception as e:
                # 某些 stream 可能不存在，忽略错误
                pass

        # 等待订阅建立 - delivery_policy='new' 后不需要等太久
        await asyncio.sleep(1.0)

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
