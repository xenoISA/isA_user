#!/usr/bin/env python3
"""
完整的用户注册、设备注册和登录流程集成测试

测试覆盖:
1. 用户注册 (auth_service → account_service)
2. 用户登录
3. 设备注册 (device_service + auth_service)
4. 设备认证
5. 事件发布和订阅
6. 数据库记录验证

运行方式:
    python test_user_device_registration_flow.py

环境变量:
    AUTH_BASE_URL - auth_service地址 (默认: http://localhost:8201)
    ACCOUNT_BASE_URL - account_service地址 (默认: http://localhost:8202)
    DEVICE_BASE_URL - device_service地址 (默认: http://localhost:8203)
    NATS_URL - NATS服务器地址 (默认: nats://localhost:4222)
    POSTGRES_HOST - PostgreSQL主机 (默认: localhost)
    POSTGRES_PORT - PostgreSQL端口 (默认: 5432)
    POSTGRES_USER - PostgreSQL用户 (默认: postgres)
    POSTGRES_PASSWORD - PostgreSQL密码 (默认: postgres)
"""

import asyncio
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.nats_client import Event, EventType, ServiceSource, get_event_bus

# Service URLs
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8201")
ACCOUNT_BASE_URL = os.getenv("ACCOUNT_BASE_URL", "http://localhost:8202")
DEVICE_BASE_URL = os.getenv("DEVICE_BASE_URL", "http://localhost:8203")
ORG_BASE_URL = os.getenv("ORG_BASE_URL", "http://localhost:8204")

# NATS configuration
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")


class EventCollector:
    """收集事件用于验证"""

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
        print(f"  📨 Event received: {event.type} from {event.source}")

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """按类型获取事件"""
        return [e for e in self.events if e["type"] == event_type]

    def clear(self):
        """清空事件"""
        self.events = []


class IntegrationTestSuite:
    """集成测试套件"""

    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.event_bus = None
        self.event_collector = EventCollector()
        self.db_pools: Dict[str, asyncpg.Pool] = {}

        # Test data
        self.test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.test_password = "TestPassword123!"
        self.test_name = "Integration Test User"
        self.user_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.device_id: Optional[str] = None
        self.device_secret: Optional[str] = None
        self.device_token: Optional[str] = None

        self.passed_tests = 0
        self.failed_tests = 0

    async def setup(self):
        """初始化测试环境"""
        print("\n" + "=" * 80)
        print("🔧 Setting up integration test environment...")
        print("=" * 80)

        # Create HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        print("✅ HTTP client created")

        # Connect to NATS event bus
        try:
            self.event_bus = await get_event_bus("integration_test")
            print("✅ Connected to NATS event bus")

            # Subscribe to all events
            await self.event_bus.subscribe_to_events(
                pattern=">", handler=self.event_collector.collect_event
            )
            print("✅ Subscribed to all events")
            await asyncio.sleep(0.5)  # Wait for subscription to establish

        except Exception as e:
            print(f"⚠️  Warning: Could not connect to NATS: {e}")
            print("   Event verification tests will be skipped")

        # Connect to databases
        try:
            await self._setup_database_connections()
        except Exception as e:
            print(f"⚠️  Warning: Could not connect to databases: {e}")
            print("   Database verification tests will be skipped")

    async def _setup_database_connections(self):
        """设置数据库连接"""
        databases = {
            "auth_db": "auth_db",
            "account_db": "account_db",
            "device_db": "device_db",
            "organization_db": "organization_db",
        }

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

    def assert_true(self, condition: bool, message: str):
        """断言为真"""
        if not condition:
            raise AssertionError(f"❌ {message}")
        print(f"  ✅ {message}")

    def assert_equal(self, actual, expected, message: str):
        """断言相等"""
        if actual != expected:
            raise AssertionError(
                f"❌ {message}\n     Expected: {expected}\n     Actual: {actual}"
            )
        print(f"  ✅ {message}")

    async def test_1_user_registration(self):
        """测试1: 用户注册流程"""
        self.print_test_header("User Registration Flow", 1, 8)

        try:
            # Step 1: Start registration
            print("\n📝 Step 1: Starting registration...")
            register_response = await self.http_client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/register",
                json={
                    "email": self.test_email,
                    "password": self.test_password,
                    "name": self.test_name,
                },
            )
            register_response.raise_for_status()
            register_data = register_response.json()

            self.assert_true(
                "pending_registration_id" in register_data,
                "Registration returned pending_registration_id",
            )

            pending_id = register_data["pending_registration_id"]
            print(f"  📋 Pending ID: {pending_id}")

            # Step 2: Get verification code (from dev endpoint)
            print("\n📝 Step 2: Getting verification code...")
            dev_response = await self.http_client.get(
                f"{AUTH_BASE_URL}/api/v1/auth/dev/pending-registration/{pending_id}"
            )

            if dev_response.status_code == 200:
                dev_data = dev_response.json()
                verification_code = dev_data.get("verification_code")
                self.assert_true(
                    verification_code is not None,
                    "Got verification code from dev endpoint",
                )
            else:
                # Fallback to environment variable
                verification_code = os.getenv("VERIFICATION_CODE")
                if not verification_code:
                    print(
                        "  ⚠️  No dev endpoint available and no VERIFICATION_CODE env var"
                    )
                    print(
                        "  ℹ️  Please set VERIFICATION_CODE environment variable and re-run"
                    )
                    raise Exception("Cannot get verification code")

            print(f"  🔑 Verification code: {verification_code}")

            # Step 3: Verify registration
            print("\n📝 Step 3: Verifying registration...")
            self.event_collector.clear()  # Clear events before verification

            verify_response = await self.http_client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/verify",
                json={"pending_registration_id": pending_id, "code": verification_code},
            )
            verify_response.raise_for_status()
            verify_data = verify_response.json()

            self.assert_true(verify_data.get("success"), "Verification successful")
            self.assert_true("user_id" in verify_data, "Verification returned user_id")
            self.assert_true(
                "access_token" in verify_data, "Verification returned access_token"
            )

            self.user_id = verify_data["user_id"]
            self.access_token = verify_data["access_token"]

            print(f"  👤 User ID: {self.user_id}")
            print(f"  🔐 Access Token: {self.access_token[:32]}...")

            # Wait for events
            await asyncio.sleep(2)

            # Step 4: Verify events were published
            if self.event_bus:
                print("\n📝 Step 4: Verifying events...")
                user_created_events = self.event_collector.get_events_by_type(
                    "user.created"
                )
                user_login_events = self.event_collector.get_events_by_type(
                    "user.logged_in"
                )

                self.assert_true(
                    len(user_created_events) > 0,
                    f"user.created event was published ({len(user_created_events)} events)",
                )
                self.assert_true(
                    len(user_login_events) > 0,
                    f"user.logged_in event was published ({len(user_login_events)} events)",
                )

            # Step 5: Verify database records
            if "account_db" in self.db_pools:
                print("\n📝 Step 5: Verifying database records...")
                async with self.db_pools["account_db"].acquire() as conn:
                    user_record = await conn.fetchrow(
                        "SELECT * FROM users WHERE user_id = $1", self.user_id
                    )

                    self.assert_true(
                        user_record is not None, "User record exists in database"
                    )
                    self.assert_equal(
                        user_record["email"],
                        self.test_email,
                        f"User email matches: {user_record['email']}",
                    )
                    self.assert_equal(
                        user_record["name"],
                        self.test_name,
                        f"User name matches: {user_record['name']}",
                    )

            self.passed_tests += 1
            print("\n✅ TEST PASSED: User Registration Flow")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: User Registration Flow")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def test_2_user_login(self):
        """测试2: 用户登录"""
        self.print_test_header("User Login", 2, 8)

        try:
            print("\n📝 Step 1: Generating token pair...")
            self.event_collector.clear()

            token_response = await self.http_client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/token-pair",
                json={"user_id": self.user_id, "email": self.test_email},
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            self.assert_true(token_data.get("success"), "Token generation successful")
            self.assert_true("access_token" in token_data, "Got access_token")
            self.assert_true("refresh_token" in token_data, "Got refresh_token")

            new_access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]

            print(f"  🔐 Access Token: {new_access_token[:32]}...")
            print(f"  🔄 Refresh Token: {refresh_token[:32]}...")

            # Wait for events
            await asyncio.sleep(2)

            # Verify login event
            if self.event_bus:
                print("\n📝 Step 2: Verifying login event...")
                login_events = self.event_collector.get_events_by_type("user.logged_in")
                self.assert_true(
                    len(login_events) > 0,
                    f"user.logged_in event was published ({len(login_events)} events)",
                )

            self.passed_tests += 1
            print("\n✅ TEST PASSED: User Login")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: User Login")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()

    async def test_3_device_registration(self):
        """测试3: 设备注册"""
        self.print_test_header("Device Registration", 3, 8)

        try:
            # Step 1: Register device in device_service
            print("\n📝 Step 1: Registering device...")
            self.event_collector.clear()

            device_data = {
                "device_name": "Integration Test Device",
                "device_type": "digital_photo_frame",
                "manufacturer": "TestManufacturer",
                "model": "TestModel-X1",
                "serial_number": f"SN-{uuid.uuid4().hex[:12].upper()}",
                "firmware_version": "1.0.0",
                "connectivity_type": "wifi",
            }

            device_response = await self.http_client.post(
                f"{DEVICE_BASE_URL}/api/v1/devices",
                json=device_data,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            device_response.raise_for_status()
            device_result = device_response.json()

            self.assert_true(
                "device_id" in device_result, "Device registration returned device_id"
            )
            self.device_id = device_result["device_id"]

            print(f"  📱 Device ID: {self.device_id}")

            # Wait for events
            await asyncio.sleep(2)

            # Verify device.registered event
            if self.event_bus:
                print("\n📝 Step 2: Verifying device.registered event...")
                device_events = self.event_collector.get_events_by_type(
                    "device.registered"
                )
                self.assert_true(
                    len(device_events) > 0,
                    f"device.registered event was published ({len(device_events)} events)",
                )

            # Step 3: Register device credentials in auth_service
            print("\n📝 Step 3: Registering device credentials...")

            device_auth_data = {
                "device_id": self.device_id,
                "organization_id": None,  # Individual user device
                "device_name": device_data["device_name"],
                "device_type": device_data["device_type"],
            }

            auth_device_response = await self.http_client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/device/register",
                json=device_auth_data,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            auth_device_response.raise_for_status()
            auth_device_result = auth_device_response.json()

            self.assert_true(
                auth_device_result.get("success"),
                "Device credential registration successful",
            )
            self.assert_true("device_secret" in auth_device_result, "Got device_secret")

            self.device_secret = auth_device_result["device_secret"]
            print(f"  🔑 Device Secret: {self.device_secret[:16]}...***")

            # Verify database records
            if "device_db" in self.db_pools:
                print("\n📝 Step 4: Verifying device database records...")
                async with self.db_pools["device_db"].acquire() as conn:
                    device_record = await conn.fetchrow(
                        "SELECT * FROM devices WHERE device_id = $1", self.device_id
                    )

                    self.assert_true(
                        device_record is not None, "Device record exists in database"
                    )
                    self.assert_equal(
                        device_record["device_name"],
                        device_data["device_name"],
                        f"Device name matches: {device_record['device_name']}",
                    )

            self.passed_tests += 1
            print("\n✅ TEST PASSED: Device Registration")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: Device Registration")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()

    async def test_4_device_authentication(self):
        """测试4: 设备认证"""
        self.print_test_header("Device Authentication", 4, 8)

        try:
            print("\n📝 Step 1: Authenticating device...")
            self.event_collector.clear()

            auth_request = {
                "device_id": self.device_id,
                "device_secret": self.device_secret,
            }

            device_auth_response = await self.http_client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/device/authenticate", json=auth_request
            )
            device_auth_response.raise_for_status()
            auth_result = device_auth_response.json()

            self.assert_true(
                auth_result.get("success"), "Device authentication successful"
            )
            self.assert_true(
                auth_result.get("authenticated"), "Device is authenticated"
            )
            self.assert_true("access_token" in auth_result, "Got device access_token")

            self.device_token = auth_result["access_token"]
            print(f"  🔐 Device Token: {self.device_token[:32]}...")

            # Wait for events
            await asyncio.sleep(2)

            # Verify device.authenticated event
            if self.event_bus:
                print("\n📝 Step 2: Verifying device.authenticated event...")
                auth_events = self.event_collector.get_events_by_type(
                    "device.authenticated"
                )
                self.assert_true(
                    len(auth_events) > 0,
                    f"device.authenticated event was published ({len(auth_events)} events)",
                )

            # Step 3: Verify device token
            print("\n📝 Step 3: Verifying device token...")

            verify_token_response = await self.http_client.post(
                f"{AUTH_BASE_URL}/api/v1/auth/device/verify-token",
                json={"token": self.device_token},
            )
            verify_token_response.raise_for_status()
            verify_result = verify_token_response.json()

            self.assert_true(verify_result.get("valid"), "Device token is valid")
            self.assert_equal(
                verify_result.get("device_id"),
                self.device_id,
                f"Token device_id matches: {verify_result.get('device_id')}",
            )

            self.passed_tests += 1
            print("\n✅ TEST PASSED: Device Authentication")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: Device Authentication")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()

    async def test_5_service_health_checks(self):
        """测试5: 服务健康检查"""
        self.print_test_header("Service Health Checks", 5, 8)

        services = [
            ("Auth Service", f"{AUTH_BASE_URL}/health"),
            ("Account Service", f"{ACCOUNT_BASE_URL}/health"),
            ("Device Service", f"{DEVICE_BASE_URL}/health"),
        ]

        try:
            all_healthy = True
            for service_name, health_url in services:
                try:
                    print(f"\n📝 Checking {service_name}...")
                    health_response = await self.http_client.get(health_url)

                    if health_response.status_code == 200:
                        print(f"  ✅ {service_name} is healthy")
                    else:
                        print(
                            f"  ⚠️  {service_name} returned status {health_response.status_code}"
                        )
                        all_healthy = False

                except Exception as e:
                    print(f"  ❌ {service_name} health check failed: {e}")
                    all_healthy = False

            self.assert_true(all_healthy, "All services are healthy")

            self.passed_tests += 1
            print("\n✅ TEST PASSED: Service Health Checks")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: Service Health Checks")
            print(f"   Error: {e}")

    async def test_6_event_bus_connectivity(self):
        """测试6: 事件总线连接性"""
        self.print_test_header("Event Bus Connectivity", 6, 8)

        try:
            if not self.event_bus:
                print("  ⚠️  Event bus not connected, skipping test")
                return

            print("\n📝 Step 1: Publishing test event...")
            self.event_collector.clear()

            test_event = Event(
                event_type=EventType.DEVICE_ONLINE,
                source=ServiceSource.DEVICE_SERVICE,
                data={
                    "device_id": "test_device",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            await self.event_bus.publish_event(test_event)
            print(f"  📤 Published event: {test_event.id}")

            # Wait for event
            await asyncio.sleep(2)

            # Verify we received it
            print("\n📝 Step 2: Verifying event was received...")
            received_events = self.event_collector.get_events_by_type("device.online")

            self.assert_true(
                len(received_events) > 0,
                f"Test event was received ({len(received_events)} events)",
            )

            self.passed_tests += 1
            print("\n✅ TEST PASSED: Event Bus Connectivity")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: Event Bus Connectivity")
            print(f"   Error: {e}")

    async def test_7_database_connectivity(self):
        """测试7: 数据库连接性"""
        self.print_test_header("Database Connectivity", 7, 8)

        try:
            if not self.db_pools:
                print("  ⚠️  No database connections, skipping test")
                return

            all_connected = True
            for pool_name, pool in self.db_pools.items():
                try:
                    print(f"\n📝 Testing {pool_name}...")
                    async with pool.acquire() as conn:
                        result = await conn.fetchval("SELECT 1")
                        self.assert_equal(result, 1, f"{pool_name} query successful")
                except Exception as e:
                    print(f"  ❌ {pool_name} query failed: {e}")
                    all_connected = False

            self.assert_true(all_connected, "All database connections working")

            self.passed_tests += 1
            print("\n✅ TEST PASSED: Database Connectivity")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: Database Connectivity")
            print(f"   Error: {e}")

    async def test_8_end_to_end_cleanup(self):
        """测试8: 端到端清理验证"""
        self.print_test_header("End-to-End Cleanup Verification", 8, 8)

        try:
            print("\n📝 Verifying all test data was created...")

            # Verify user was created
            self.assert_true(self.user_id is not None, "User ID was generated")
            self.assert_true(
                self.access_token is not None, "User access token was generated"
            )

            # Verify device was created
            self.assert_true(self.device_id is not None, "Device ID was generated")
            self.assert_true(
                self.device_secret is not None, "Device secret was generated"
            )
            self.assert_true(
                self.device_token is not None, "Device token was generated"
            )

            print(f"\n📊 Test Summary:")
            print(f"  User ID: {self.user_id}")
            print(f"  Device ID: {self.device_id}")
            print(f"  Total Events Collected: {len(self.event_collector.events)}")

            # List all collected event types
            event_types = set(e["type"] for e in self.event_collector.events)
            print(f"\n📨 Event Types Collected:")
            for event_type in sorted(event_types):
                count = len(self.event_collector.get_events_by_type(event_type))
                print(f"  - {event_type}: {count} events")

            self.passed_tests += 1
            print("\n✅ TEST PASSED: End-to-End Cleanup Verification")

        except Exception as e:
            self.failed_tests += 1
            print(f"\n❌ TEST FAILED: End-to-End Cleanup Verification")
            print(f"   Error: {e}")

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 80)
        print("🚀 INTEGRATION TEST SUITE: User & Device Registration Flow")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"\nTest Configuration:")
        print(f"  Auth Service: {AUTH_BASE_URL}")
        print(f"  Account Service: {ACCOUNT_BASE_URL}")
        print(f"  Device Service: {DEVICE_BASE_URL}")
        print(f"  NATS URL: {NATS_URL}")
        print(f"  PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}")
        print(f"\nTest Email: {self.test_email}")

        await self.setup()

        # Run all tests in sequence
        await self.test_1_user_registration()
        await self.test_2_user_login()
        await self.test_3_device_registration()
        await self.test_4_device_authentication()
        await self.test_5_service_health_checks()
        await self.test_6_event_bus_connectivity()
        await self.test_7_database_connectivity()
        await self.test_8_end_to_end_cleanup()

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
            print(
                "✅ User registration, device registration, and login flows are working correctly"
            )
        else:
            print(f"\n⚠️  {self.failed_tests} test(s) failed")
            print("Please check the logs above for details")

        print("\n" + "=" * 80)


async def main():
    """主函数"""
    test_suite = IntegrationTestSuite()

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
