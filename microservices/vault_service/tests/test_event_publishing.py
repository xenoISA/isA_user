"""
Vault Service Event Publishing Tests

Tests that Vault Service correctly publishes events for all vault operations
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.vault_service.vault_service import VaultService
from microservices.vault_service.models import (
    VaultCreateRequest, VaultUpdateRequest, VaultShareRequest,
    SecretType, PermissionLevel
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)

    def get_events_by_type(self, event_type: str):
        """Get events by type"""
        return [e for e in self.published_events if e.type == event_type]

    def clear(self):
        """Clear published events"""
        self.published_events = []


class MockVaultRepository:
    """Mock vault repository for testing"""

    def __init__(self):
        self.vault_items = {}
        self.access_logs = []
        self.shares = {}

    async def create_vault_item(self, vault_item):
        """Create vault item"""
        vault_id = f"vault_{len(self.vault_items) + 1}"
        item_dict = {
            "vault_id": vault_id,
            "user_id": vault_item.user_id,
            "organization_id": vault_item.organization_id,
            "secret_type": vault_item.secret_type.value,
            "provider": vault_item.provider,
            "name": vault_item.name,
            "description": vault_item.description,
            "encrypted_value": vault_item.encrypted_value,
            "metadata": vault_item.metadata,
            "is_active": True,
            "version": 1
        }
        self.vault_items[vault_id] = item_dict

        # Return mock response
        class MockVaultItemResponse:
            def __init__(self, data):
                self.vault_id = data["vault_id"]
                self.user_id = data["user_id"]
                self.organization_id = data["organization_id"]
                self.secret_type = data["secret_type"]
                self.provider = data["provider"]
                self.name = data["name"]
                self.version = data["version"]

        return MockVaultItemResponse(item_dict)

    async def get_vault_item(self, vault_id: str):
        """Get vault item"""
        return self.vault_items.get(vault_id)

    async def update_vault_item(self, vault_id: str, update_data: dict):
        """Update vault item"""
        if vault_id in self.vault_items:
            self.vault_items[vault_id].update(update_data)
            return True
        return False

    async def delete_vault_item(self, vault_id: str):
        """Delete vault item"""
        if vault_id in self.vault_items:
            self.vault_items[vault_id]["is_active"] = False
            return True
        return False

    async def check_user_access(self, vault_id: str, user_id: str):
        """Check user access"""
        item = self.vault_items.get(vault_id)
        if item and item["user_id"] == user_id:
            return "owner"
        return None

    async def increment_access_count(self, vault_id: str):
        """Increment access count"""
        pass

    async def create_share(self, share):
        """Create share"""
        share_id = f"share_{len(self.shares) + 1}"
        share_dict = {
            "share_id": share_id,
            "vault_id": share.vault_id,
            "owner_user_id": share.owner_user_id,
            "shared_with_user_id": share.shared_with_user_id,
            "shared_with_org_id": share.shared_with_org_id,
            "permission_level": share.permission_level.value
        }
        self.shares[share_id] = share_dict

        # Return mock response
        class MockVaultShareResponse:
            def __init__(self, data):
                self.share_id = data["share_id"]
                self.vault_id = data["vault_id"]

        return MockVaultShareResponse(share_dict)

    async def create_access_log(self, access_log):
        """Create access log"""
        self.access_logs.append(access_log)
        return True


async def test_secret_created_event():
    """Test that vault.secret.created event is published"""
    print("\n📝 Testing vault.secret.created event...")

    mock_event_bus = MockEventBus()
    service = VaultService(blockchain_client=None, event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockVaultRepository()

    request = VaultCreateRequest(
        organization_id="org123",
        secret_type=SecretType.API_KEY,
        provider="stripe",
        name="Stripe API Key",
        description="Production Stripe key",
        secret_value="sk_test_123456",
        metadata={"environment": "production"},
        tags=["payment", "stripe"],
        blockchain_verify=False
    )

    success, response, message = await service.create_secret(
        user_id="user123",
        request=request,
        ip_address="127.0.0.1",
        user_agent="TestClient"
    )

    # Check secret was created
    assert success is True, f"Secret creation should succeed: {message}"
    assert response is not None, "Response should not be None"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.VAULT_SECRET_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.VAULT_SERVICE.value, "Event source should be vault_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["organization_id"] == "org123", "Event should contain organization_id"
    assert event.data["secret_type"] == "api_key", "Event should contain secret_type"
    assert event.data["provider"] == "stripe", "Event should contain provider"

    print("✅ TEST PASSED: vault.secret.created event published correctly")
    return True


async def test_secret_accessed_event():
    """Test that vault.secret.accessed event is published"""
    print("\n📝 Testing vault.secret.accessed event...")

    mock_event_bus = MockEventBus()
    service = VaultService(blockchain_client=None, event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockVaultRepository()
    service.repository = mock_repo

    # Create a vault item first
    mock_repo.vault_items["vault_1"] = {
        "vault_id": "vault_1",
        "user_id": "user123",
        "secret_type": "api_key",
        "name": "Test Secret",
        "encrypted_value": "ZW5jcnlwdGVk",  # base64 encoded "encrypted"
        "metadata": {
            "dek_encrypted": "ZGVr",
            "kek_salt": "c2FsdA==",
            "nonce": "bm9uY2U="
        },
        "is_active": True,
        "provider": "stripe"  # Must be valid enum value
    }

    # Clear any previous events
    mock_event_bus.clear()

    success, response, message = await service.get_secret(
        vault_id="vault_1",
        user_id="user123",
        decrypt=False,  # Don't decrypt to avoid encryption dependencies
        ip_address="127.0.0.1",
        user_agent="TestClient"
    )

    # Check secret was accessed
    assert success is True, f"Secret access should succeed: {message}"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.VAULT_SECRET_ACCESSED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.VAULT_SERVICE.value, "Event source should be vault_service"
    assert event.data["vault_id"] == "vault_1", "Event should contain vault_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["decrypted"] is False, "Event should indicate not decrypted"

    print("✅ TEST PASSED: vault.secret.accessed event published correctly")
    return True


async def test_secret_updated_event():
    """Test that vault.secret.updated event is published"""
    print("\n📝 Testing vault.secret.updated event...")

    mock_event_bus = MockEventBus()
    service = VaultService(blockchain_client=None, event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockVaultRepository()
    service.repository = mock_repo

    # Create a vault item first
    from datetime import datetime, timezone
    mock_repo.vault_items["vault_1"] = {
        "vault_id": "vault_1",
        "user_id": "user123",
        "organization_id": "org123",
        "secret_type": "api_key",
        "name": "Test Secret",
        "description": "Test description",
        "encrypted_value": "ZW5jcnlwdGVk",
        "encryption_method": "aes_256_gcm",
        "metadata": {"key": "value"},
        "is_active": True,
        "version": 1,
        "provider": "stripe",
        "access_count": 0,
        "rotation_enabled": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    # Clear any previous events
    mock_event_bus.clear()

    request = VaultUpdateRequest(
        name="Updated Secret Name",
        description="Updated description",
        metadata={"updated": "true"}
    )

    success, response, message = await service.update_secret(
        vault_id="vault_1",
        user_id="user123",
        request=request,
        ip_address="127.0.0.1",
        user_agent="TestClient"
    )

    # Check secret was updated
    assert success is True, f"Secret update should succeed: {message}"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.VAULT_SECRET_UPDATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.VAULT_SERVICE.value, "Event source should be vault_service"
    assert event.data["vault_id"] == "vault_1", "Event should contain vault_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["metadata_updated"] is True, "Event should indicate metadata was updated"

    print("✅ TEST PASSED: vault.secret.updated event published correctly")
    return True


async def test_secret_deleted_event():
    """Test that vault.secret.deleted event is published"""
    print("\n📝 Testing vault.secret.deleted event...")

    mock_event_bus = MockEventBus()
    service = VaultService(blockchain_client=None, event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockVaultRepository()
    service.repository = mock_repo

    # Create a vault item first
    mock_repo.vault_items["vault_1"] = {
        "vault_id": "vault_1",
        "user_id": "user123",
        "secret_type": "api_key",
        "is_active": True
    }

    # Clear any previous events
    mock_event_bus.clear()

    success, message = await service.delete_secret(
        vault_id="vault_1",
        user_id="user123",
        ip_address="127.0.0.1",
        user_agent="TestClient"
    )

    # Check secret was deleted
    assert success is True, f"Secret deletion should succeed: {message}"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.VAULT_SECRET_DELETED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.VAULT_SERVICE.value, "Event source should be vault_service"
    assert event.data["vault_id"] == "vault_1", "Event should contain vault_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"

    print("✅ TEST PASSED: vault.secret.deleted event published correctly")
    return True


async def test_secret_shared_event():
    """Test that vault.secret.shared event is published"""
    print("\n📝 Testing vault.secret.shared event...")

    mock_event_bus = MockEventBus()
    service = VaultService(blockchain_client=None, event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockVaultRepository()
    service.repository = mock_repo

    # Create a vault item first
    mock_repo.vault_items["vault_1"] = {
        "vault_id": "vault_1",
        "user_id": "user123",
        "secret_type": "api_key"
    }

    # Clear any previous events
    mock_event_bus.clear()

    request = VaultShareRequest(
        shared_with_user_id="user456",
        shared_with_org_id=None,
        permission_level=PermissionLevel.READ
    )

    success, response, message = await service.share_secret(
        vault_id="vault_1",
        owner_user_id="user123",
        request=request,
        ip_address="127.0.0.1",
        user_agent="TestClient"
    )

    # Check secret was shared
    assert success is True, f"Secret sharing should succeed: {message}"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.VAULT_SECRET_SHARED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.VAULT_SERVICE.value, "Event source should be vault_service"
    assert event.data["vault_id"] == "vault_1", "Event should contain vault_id"
    assert event.data["owner_user_id"] == "user123", "Event should contain owner_user_id"
    assert event.data["shared_with_user_id"] == "user456", "Event should contain shared_with_user_id"
    assert event.data["permission_level"] == "read", "Event should contain permission_level"

    print("✅ TEST PASSED: vault.secret.shared event published correctly")
    return True


async def test_secret_rotated_event():
    """Test that vault.secret.rotated event is published"""
    print("\n📝 Testing vault.secret.rotated event...")

    mock_event_bus = MockEventBus()
    service = VaultService(blockchain_client=None, event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockVaultRepository()
    service.repository = mock_repo

    # Create a vault item first
    from datetime import datetime, timezone
    mock_repo.vault_items["vault_1"] = {
        "vault_id": "vault_1",
        "user_id": "user123",
        "organization_id": "org123",
        "secret_type": "api_key",
        "name": "Test Secret",
        "description": "Test description",
        "encrypted_value": "ZW5jcnlwdGVk",
        "encryption_method": "aes_256_gcm",
        "metadata": {"key": "value"},
        "is_active": True,
        "version": 1,
        "provider": "stripe",
        "access_count": 0,
        "rotation_enabled": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    # Clear any previous events
    mock_event_bus.clear()

    success, response, message = await service.rotate_secret(
        vault_id="vault_1",
        user_id="user123",
        new_secret_value="new_secret_value_123",
        ip_address="127.0.0.1",
        user_agent="TestClient"
    )

    # Check secret was rotated
    assert success is True, f"Secret rotation should succeed: {message}"

    # Check event was published (should have both updated and rotated events)
    rotated_events = mock_event_bus.get_events_by_type(EventType.VAULT_SECRET_ROTATED.value)
    assert len(rotated_events) == 1, f"Should publish 1 rotated event, got {len(rotated_events)}"

    event = rotated_events[0]
    assert event.source == ServiceSource.VAULT_SERVICE.value, "Event source should be vault_service"
    assert event.data["vault_id"] == "vault_1", "Event should contain vault_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"

    print("✅ TEST PASSED: vault.secret.rotated event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("VAULT SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Secret Created Event", test_secret_created_event),
        ("Secret Accessed Event", test_secret_accessed_event),
        ("Secret Updated Event", test_secret_updated_event),
        ("Secret Deleted Event", test_secret_deleted_event),
        ("Secret Shared Event", test_secret_shared_event),
        ("Secret Rotated Event", test_secret_rotated_event),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
