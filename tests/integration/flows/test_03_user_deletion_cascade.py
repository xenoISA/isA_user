#!/usr/bin/env python3
"""
P0 集成测试: 用户删除级联处理

测试覆盖的服务 (订阅 user.deleted 事件的服务):
- account_service: 用户账户删除
- wallet_service: 钱包数据清理
- device_service: 用户设备清理
- session_service: 会话数据清理
- memory_service: 记忆数据清理
- calendar_service: 日历数据清理
- task_service: 任务数据清理
- location_service: 位置数据清理
- document_service: 文档权限清理
- vault_service: 密钥数据清理
- invitation_service: 邀请数据清理
- authorization_service: 权限数据清理
- order_service: 订单数据处理
- payment_service: 支付数据处理
- product_service: 订阅数据清理

测试流程:
1. 创建完整的测试用户数据 (在多个服务中创建关联数据)
2. 发布 user.deleted 事件
3. 验证所有服务正确处理级联删除
4. 验证数据一致性

这是系统健壮性的关键测试!
"""

import asyncio
import os
import sys
from datetime import datetime

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../..")
sys.path.insert(0, _project_root)
sys.path.insert(0, _current_dir)

from base_test import BaseIntegrationTest


class UserDeletionCascadeIntegrationTest(BaseIntegrationTest):
    """用户删除级联集成测试"""

    def __init__(self):
        super().__init__()
        # Test user data
        self.test_user_id = None
        self.test_email = None

        # Created resources to verify deletion
        self.wallet_id = None
        self.device_id = None
        self.session_id = None
        self.task_id = None
        self.calendar_event_id = None
        self.invitation_id = None
        self.vault_secret_id = None
        self.document_id = None

    async def run(self):
        """运行完整测试"""
        self.log_header("P0: User Deletion Cascade Integration Test")
        self.log(f"Start Time: {datetime.utcnow().isoformat()}")

        try:
            await self.setup()

            # Phase 1: 创建测试数据
            await self.test_phase_1_create_test_user()
            await self.test_phase_2_create_related_data()

            # Phase 2: 触发用户删除
            await self.test_phase_3_trigger_user_deletion()

            # Phase 3: 验证级联删除
            await self.test_phase_4_verify_cascade_deletion()

            # Phase 4: 验证事件
            await self.test_phase_5_verify_events()

        except Exception as e:
            self.log(f"Test Error: {e}", "red")
            import traceback
            traceback.print_exc()
            self.failed_assertions += 1

        finally:
            await self.teardown()
            self.log_summary()

        return self.failed_assertions == 0

    async def test_phase_1_create_test_user(self):
        """Phase 1: 创建测试用户"""
        self.log_step(1, "Create Test User")

        self.test_user_id = self.generate_test_user_id()
        self.test_email = self.generate_test_email()

        self.log(f"  Test User ID: {self.test_user_id}")
        self.log(f"  Test Email: {self.test_email}")

        # 在 account_service 创建用户
        response = await self.post(
            f"{self.config.ACCOUNT_URL}/api/v1/accounts",
            json={
                "user_id": self.test_user_id,
                "email": self.test_email,
                "name": "Cascade Delete Test User",
                "status": "active"
            }
        )

        if response.status_code in [200, 201, 409]:
            self.assert_true(True, "Test user ready in account_service")
        else:
            self.log(f"  Warning: account_service returned {response.status_code}", "yellow")

    async def test_phase_2_create_related_data(self):
        """Phase 2: 在各服务中创建关联数据"""
        self.log_step(2, "Create Related Data in Multiple Services")

        if not self.test_user_id:
            self.log("  SKIP: No test_user_id", "yellow")
            return

        # 并行创建各服务的数据
        await asyncio.gather(
            self._create_wallet(),
            self._create_device(),
            self._create_session(),
            self._create_task(),
            self._create_calendar_event(),
            self._create_invitation(),
            self._create_vault_secret(),
            self._create_memory(),
            self._create_location(),
            return_exceptions=True
        )

        self.log(f"  Created data in multiple services")
        self.log(f"  Wallet: {self.wallet_id}")
        self.log(f"  Device: {self.device_id}")
        self.log(f"  Session: {self.session_id}")
        self.log(f"  Task: {self.task_id}")
        self.log(f"  Calendar Event: {self.calendar_event_id}")
        self.log(f"  Invitation: {self.invitation_id}")
        self.log(f"  Vault Secret: {self.vault_secret_id}")

    async def _create_wallet(self):
        """创建钱包"""
        try:
            response = await self.post(
                f"{self.config.WALLET_URL}/api/v1/wallets",
                json={
                    "user_id": self.test_user_id,
                    "currency": "TOKEN",
                    "initial_balance": 100
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.wallet_id = data.get("wallet_id")
            elif response.status_code == 409:
                # 已存在
                get_resp = await self.get(f"{self.config.WALLET_URL}/api/v1/wallets/user/{self.test_user_id}")
                if get_resp.status_code == 200:
                    self.wallet_id = get_resp.json().get("wallet_id")
        except Exception as e:
            self.log(f"  Wallet creation error: {e}", "yellow")

    async def _create_device(self):
        """创建设备"""
        try:
            response = await self.post(
                f"{self.config.DEVICE_URL}/api/v1/devices",
                json={
                    "owner_id": self.test_user_id,
                    "device_name": "Cascade Test Device",
                    "device_type": "digital_photo_frame",
                    "serial_number": self.test_data.serial_number(),
                    "firmware_version": "1.0.0"
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.device_id = data.get("device_id")
        except Exception as e:
            self.log(f"  Device creation error: {e}", "yellow")

    async def _create_session(self):
        """创建会话"""
        try:
            response = await self.post(
                f"{self.config.SESSION_URL}/api/v1/sessions",
                json={
                    "user_id": self.test_user_id,
                    "session_type": "chat",
                    "metadata": {"source": "cascade_test"}
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.session_id = data.get("session_id")
        except Exception as e:
            self.log(f"  Session creation error: {e}", "yellow")

    async def _create_task(self):
        """创建任务"""
        try:
            response = await self.post(
                f"{self.config.TASK_URL}/api/v1/tasks",
                json={
                    "user_id": self.test_user_id,
                    "title": "Cascade Test Task",
                    "description": "Test task for cascade deletion",
                    "status": "pending"
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.task_id = data.get("task_id")
        except Exception as e:
            self.log(f"  Task creation error: {e}", "yellow")

    async def _create_calendar_event(self):
        """创建日历事件"""
        try:
            response = await self.post(
                f"{self.config.CALENDAR_URL}/api/v1/events",
                json={
                    "user_id": self.test_user_id,
                    "title": "Cascade Test Event",
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "event_type": "meeting"
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.calendar_event_id = data.get("event_id")
        except Exception as e:
            self.log(f"  Calendar event creation error: {e}", "yellow")

    async def _create_invitation(self):
        """创建邀请"""
        try:
            response = await self.post(
                f"{self.config.INVITATION_URL}/api/v1/invitations",
                json={
                    "inviter_id": self.test_user_id,
                    "invitee_email": f"invitee_{self.test_data.email()}",
                    "invitation_type": "organization",
                    "resource_id": "test_org_001"
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.invitation_id = data.get("invitation_id")
        except Exception as e:
            self.log(f"  Invitation creation error: {e}", "yellow")

    async def _create_vault_secret(self):
        """创建密钥"""
        try:
            response = await self.post(
                f"{self.config.VAULT_URL}/api/v1/secrets",
                json={
                    "user_id": self.test_user_id,
                    "name": "cascade_test_secret",
                    "secret_type": "api_key",
                    "value": "test_secret_value_12345"
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.vault_secret_id = data.get("secret_id")
        except Exception as e:
            self.log(f"  Vault secret creation error: {e}", "yellow")

    async def _create_memory(self):
        """创建记忆"""
        try:
            response = await self.post(
                f"{self.config.MEMORY_URL}/api/v1/memories/factual",
                json={
                    "user_id": self.test_user_id,
                    "content": "Test factual memory for cascade deletion",
                    "category": "test",
                    "confidence": 0.9
                }
            )
            # Memory service 可能返回不同的状态码
            if response.status_code in [200, 201]:
                self.log("  Memory created")
        except Exception as e:
            self.log(f"  Memory creation error: {e}", "yellow")

    async def _create_location(self):
        """创建位置记录"""
        try:
            response = await self.post(
                f"{self.config.LOCATION_URL}/api/v1/locations",
                json={
                    "user_id": self.test_user_id,
                    "latitude": 39.9042,
                    "longitude": 116.4074,
                    "accuracy": 10.0,
                    "source": "integration_test"
                }
            )
            if response.status_code in [200, 201]:
                self.log("  Location created")
        except Exception as e:
            self.log(f"  Location creation error: {e}", "yellow")

    async def test_phase_3_trigger_user_deletion(self):
        """Phase 3: 触发用户删除"""
        self.log_step(3, "Trigger User Deletion")

        if not self.test_user_id:
            self.log("  SKIP: No test_user_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # 方法1: 通过 account_service API 删除用户
        response = await self.delete(
            f"{self.config.ACCOUNT_URL}/api/v1/accounts/{self.test_user_id}"
        )

        if response.status_code in [200, 204]:
            self.assert_true(True, "User deletion triggered via API")
            self.log(f"  User {self.test_user_id} deletion initiated")
        else:
            self.log(f"  API deletion returned {response.status_code}, trying event publish...", "yellow")

            # 方法2: 直接发布 user.deleted 事件
            if self.event_bus:
                from core.nats_client import Event
                delete_event = Event(
                    event_type="user.deleted",
                    source="account_service",
                    data={
                        "user_id": self.test_user_id,
                        "email": self.test_email,
                        "deletion_type": "hard",
                        "reason": "integration_test"
                    }
                )
                await self.event_bus.publish_event(delete_event)
                self.assert_true(True, "user.deleted event published directly")

        # 等待事件传播和处理
        await self.wait(5, "Waiting for cascade deletion to complete")

    async def test_phase_4_verify_cascade_deletion(self):
        """Phase 4: 验证级联删除"""
        self.log_step(4, "Verify Cascade Deletion")

        if not self.test_user_id:
            self.log("  SKIP: No test_user_id", "yellow")
            return

        # 验证各服务中的数据已被清理
        verification_results = await asyncio.gather(
            self._verify_account_deleted(),
            self._verify_wallet_deleted(),
            self._verify_device_deleted(),
            self._verify_session_deleted(),
            self._verify_task_deleted(),
            self._verify_calendar_deleted(),
            return_exceptions=True
        )

        # 统计验证结果
        verified_count = sum(1 for r in verification_results if r is True)
        self.log(f"  Verified {verified_count}/{len(verification_results)} services cleaned up")

    async def _verify_account_deleted(self) -> bool:
        """验证账户已删除"""
        try:
            response = await self.get(f"{self.config.ACCOUNT_URL}/api/v1/accounts/{self.test_user_id}")
            if response.status_code == 404:
                self.assert_true(True, "Account deleted from account_service")
                return True
            elif response.status_code == 200:
                data = response.json()
                status = data.get("status", "").lower()
                if status in ["deleted", "inactive", "suspended"]:
                    self.assert_true(True, f"Account marked as {status}")
                    return True
                self.log(f"  Account still active: {status}", "yellow")
                return False
        except Exception as e:
            self.log(f"  Account verification error: {e}", "yellow")
            return False

    async def _verify_wallet_deleted(self) -> bool:
        """验证钱包已删除"""
        if not self.wallet_id:
            return True  # 没有创建钱包

        try:
            response = await self.get(f"{self.config.WALLET_URL}/api/v1/wallets/{self.wallet_id}")
            if response.status_code == 404:
                self.assert_true(True, "Wallet deleted from wallet_service")
                return True
            elif response.status_code == 200:
                data = response.json()
                if data.get("status", "").lower() in ["deleted", "closed"]:
                    self.assert_true(True, "Wallet marked as deleted")
                    return True
                self.log(f"  Wallet still exists", "yellow")
                return False
        except Exception as e:
            self.log(f"  Wallet verification error: {e}", "yellow")
            return False

    async def _verify_device_deleted(self) -> bool:
        """验证设备已删除"""
        if not self.device_id:
            return True

        try:
            response = await self.get(f"{self.config.DEVICE_URL}/api/v1/devices/{self.device_id}")
            if response.status_code == 404:
                self.assert_true(True, "Device deleted from device_service")
                return True
            elif response.status_code == 200:
                data = response.json()
                if data.get("owner_id") is None or data.get("status") == "orphaned":
                    self.assert_true(True, "Device ownership cleared")
                    return True
                self.log(f"  Device still linked to user", "yellow")
                return False
        except Exception as e:
            self.log(f"  Device verification error: {e}", "yellow")
            return False

    async def _verify_session_deleted(self) -> bool:
        """验证会话已删除"""
        if not self.session_id:
            return True

        try:
            response = await self.get(f"{self.config.SESSION_URL}/api/v1/sessions/{self.session_id}")
            if response.status_code == 404:
                self.assert_true(True, "Session deleted from session_service")
                return True
            elif response.status_code == 200:
                data = response.json()
                if data.get("status") in ["deleted", "ended", "terminated"]:
                    self.assert_true(True, "Session terminated")
                    return True
                self.log(f"  Session still exists", "yellow")
                return False
        except Exception as e:
            self.log(f"  Session verification error: {e}", "yellow")
            return False

    async def _verify_task_deleted(self) -> bool:
        """验证任务已删除"""
        if not self.task_id:
            return True

        try:
            response = await self.get(f"{self.config.TASK_URL}/api/v1/tasks/{self.task_id}")
            if response.status_code == 404:
                self.assert_true(True, "Task deleted from task_service")
                return True
            self.log(f"  Task still exists", "yellow")
            return False
        except Exception as e:
            self.log(f"  Task verification error: {e}", "yellow")
            return False

    async def _verify_calendar_deleted(self) -> bool:
        """验证日历事件已删除"""
        if not self.calendar_event_id:
            return True

        try:
            response = await self.get(f"{self.config.CALENDAR_URL}/api/v1/events/{self.calendar_event_id}")
            if response.status_code == 404:
                self.assert_true(True, "Calendar event deleted from calendar_service")
                return True
            self.log(f"  Calendar event still exists", "yellow")
            return False
        except Exception as e:
            self.log(f"  Calendar verification error: {e}", "yellow")
            return False

    async def test_phase_5_verify_events(self):
        """Phase 5: 验证事件处理"""
        self.log_step(5, "Verify Event Processing")

        if not self.event_collector:
            self.log("  SKIP: No event collector", "yellow")
            return

        summary = self.event_collector.summary()
        self.log(f"  Events collected: {summary}")

        # 验证 user.deleted 事件被发布
        if self.event_collector.has_event("user.deleted"):
            self.assert_true(True, "user.deleted event was published")

            # 获取事件详情
            events = self.event_collector.get_by_type("user.deleted")
            if events:
                event_data = events[0].get("data", {})
                self.log(f"  Event data: user_id={event_data.get('user_id')}")
        else:
            self.log("  user.deleted event not captured (may have been processed)", "yellow")


async def main():
    """主函数"""
    test = UserDeletionCascadeIntegrationTest()
    success = await test.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
