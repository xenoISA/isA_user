"""
Device Service Client Example

Demonstrates how to use the device service and interact with related services
(auth_service, organization_service, storage_service).
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DeviceServiceClient:
    """Client for Device Service operations"""

    def __init__(self, base_url: str = "http://localhost:8220", auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
            headers=headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def register_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new device"""
        response = await self.client.post("/api/v1/devices", json=device_data)
        response.raise_for_status()
        return response.json()

    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """Get device details"""
        response = await self.client.get(f"/api/v1/devices/{device_id}")
        response.raise_for_status()
        return response.json()

    async def update_device(self, device_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update device information"""
        response = await self.client.put(f"/api/v1/devices/{device_id}", json=updates)
        response.raise_for_status()
        return response.json()

    async def list_devices(self, **filters) -> Dict[str, Any]:
        """List devices with optional filters"""
        response = await self.client.get("/api/v1/devices", params=filters)
        response.raise_for_status()
        return response.json()

    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to device"""
        response = await self.client.post(f"/api/v1/devices/{device_id}/commands", json=command)
        response.raise_for_status()
        return response.json()

    async def get_device_health(self, device_id: str) -> Dict[str, Any]:
        """Get device health status"""
        response = await self.client.get(f"/api/v1/devices/{device_id}/health")
        response.raise_for_status()
        return response.json()

    async def authenticate_device(self, device_id: str, device_secret: str) -> Dict[str, Any]:
        """Authenticate a device and get access token"""
        response = await self.client.post(
            "/api/v1/devices/auth",
            json={"device_id": device_id, "device_secret": device_secret}
        )
        response.raise_for_status()
        return response.json()


class AuthServiceClient:
    """Client for Auth Service operations"""

    def __init__(self, base_url: str = "http://localhost:8201"):
        self.base_url = base_url.rstrip('/')
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def generate_dev_token(self, user_id: str, email: str, **kwargs) -> Dict[str, Any]:
        """Generate development JWT token"""
        payload = {
            "user_id": user_id,
            "email": email,
            **kwargs
        }
        response = await self.client.post("/api/v1/auth/dev-token", json=payload)
        response.raise_for_status()
        return response.json()

    async def register_device(
        self,
        device_id: str,
        organization_id: str,
        device_name: str,
        device_type: str = "smart_frame",
        **kwargs
    ) -> Dict[str, Any]:
        """Register device in auth service"""
        payload = {
            "device_id": device_id,
            "organization_id": organization_id,
            "device_name": device_name,
            "device_type": device_type,
            **kwargs
        }
        response = await self.client.post("/api/v1/auth/device/register", json=payload)
        response.raise_for_status()
        return response.json()

    async def authenticate_device(self, device_id: str, device_secret: str) -> Dict[str, Any]:
        """Authenticate device"""
        response = await self.client.post(
            "/api/v1/auth/device/authenticate",
            json={"device_id": device_id, "device_secret": device_secret}
        )
        response.raise_for_status()
        return response.json()


# ==================== Example Usage ====================

async def example_1_basic_device_management():
    """Example 1: Basic device management with authentication"""
    print("\n" + "=" * 70)
    print("Example 1: Basic Device Management")
    print("=" * 70)

    # Step 1: Get authentication token from auth service
    async with AuthServiceClient() as auth_client:
        print("\n1. Generating user authentication token...")
        token_response = await auth_client.generate_dev_token(
            user_id="example_user_001",
            email="user@example.com",
            organization_id="org_example_123",
            role="admin",
            expires_in=3600
        )
        user_token = token_response["token"]
        print(f"   ✓ Token generated: {user_token[:50]}...")

    # Step 2: Register and manage device
    async with DeviceServiceClient(auth_token=user_token) as device_client:
        print("\n2. Registering a new smart frame device...")
        device_data = {
            "device_name": "Living Room Smart Frame",
            "device_type": "smart_frame",
            "manufacturer": "SmartTech",
            "model": "SF-2024-Pro",
            "serial_number": f"SN_{int(datetime.now().timestamp())}",
            "firmware_version": "1.0.0",
            "connectivity_type": "wifi",
            "security_level": "standard",
            "mac_address": "AA:BB:CC:DD:EE:01",
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY"
            },
            "tags": ["living-room", "family"]
        }
        device = await device_client.register_device(device_data)
        device_id = device["device_id"]
        print(f"   ✓ Device registered: {device_id}")
        print(f"     Name: {device['device_name']}")
        print(f"     Type: {device['device_type']}")
        print(f"     Status: {device['status']}")

        print("\n3. Getting device details...")
        device_details = await device_client.get_device(device_id)
        print(f"   ✓ Retrieved device: {device_details['device_name']}")

        print("\n4. Updating device...")
        updated = await device_client.update_device(
            device_id,
            {
                "firmware_version": "1.1.0",
                "status": "active",
                "tags": ["living-room", "family", "updated"]
            }
        )
        print(f"   ✓ Device updated: firmware v{updated['firmware_version']}")

        print("\n5. Listing all devices...")
        devices_list = await device_client.list_devices(limit=10)
        print(f"   ✓ Found {devices_list['count']} device(s)")

        print("\n6. Getting device health...")
        health = await device_client.get_device_health(device_id)
        print(f"   ✓ Health score: {health['health_score']}")
        print(f"     CPU: {health['cpu_usage']}%")
        print(f"     Memory: {health['memory_usage']}%")


async def example_2_device_authentication_flow():
    """Example 2: Complete device authentication flow"""
    print("\n" + "=" * 70)
    print("Example 2: Device Authentication Flow")
    print("=" * 70)

    device_id = f"smart_frame_{int(datetime.now().timestamp())}"
    organization_id = "org_example_123"

    # Step 1: Register device in auth service
    async with AuthServiceClient() as auth_client:
        print("\n1. Registering device in auth service...")
        device_reg = await auth_client.register_device(
            device_id=device_id,
            organization_id=organization_id,
            device_name="Bedroom Smart Frame",
            device_type="smart_frame",
            expires_days=365
        )
        device_secret = device_reg["device_secret"]
        print(f"   ✓ Device registered: {device_id}")
        print(f"     Secret (first 20 chars): {device_secret[:20]}...")
        print(f"     ⚠️  Save this secret - shown only once!")

        print("\n2. Authenticating device...")
        auth_response = await auth_client.authenticate_device(device_id, device_secret)
        device_token = auth_response["access_token"]
        print(f"   ✓ Device authenticated")
        print(f"     Token (first 50 chars): {device_token[:50]}...")
        print(f"     Expires in: {auth_response['expires_in']} seconds")

    # Step 3: Use device token with device service
    async with DeviceServiceClient(auth_token=device_token) as device_client:
        print("\n3. Using device token to access service stats...")
        # Note: Device tokens may have limited permissions
        print("   ✓ Device can now communicate with device service")


async def example_3_device_commands():
    """Example 3: Sending commands to devices"""
    print("\n" + "=" * 70)
    print("Example 3: Device Commands & Control")
    print("=" * 70)

    # Get user token
    async with AuthServiceClient() as auth_client:
        token_response = await auth_client.generate_dev_token(
            user_id="example_user_002",
            email="admin@example.com",
            role="admin"
        )
        user_token = token_response["token"]

    async with DeviceServiceClient(auth_token=user_token) as device_client:
        # Register a device first
        print("\n1. Registering test device...")
        device = await device_client.register_device({
            "device_name": "Test Command Device",
            "device_type": "smart_frame",
            "manufacturer": "TestCorp",
            "model": "SF-CMD",
            "serial_number": f"CMD_{int(datetime.now().timestamp())}",
            "firmware_version": "1.0.0",
            "connectivity_type": "wifi",
            "security_level": "standard"
        })
        device_id = device["device_id"]
        print(f"   ✓ Device registered: {device_id}")

        print("\n2. Sending status check command...")
        status_cmd = await device_client.send_command(
            device_id,
            {
                "command": "status_check",
                "parameters": {"include_diagnostics": True},
                "timeout": 30,
                "priority": 5
            }
        )
        print(f"   ✓ Command sent: {status_cmd.get('command_id')}")
        print(f"     Status: {status_cmd.get('status')}")

        print("\n3. Sending reboot command...")
        reboot_cmd = await device_client.send_command(
            device_id,
            {
                "command": "reboot",
                "parameters": {"delay_seconds": 5},
                "timeout": 60,
                "priority": 8
            }
        )
        print(f"   ✓ Reboot command sent: {reboot_cmd.get('command_id')}")

        print("\n4. Sending firmware update command...")
        update_cmd = await device_client.send_command(
            device_id,
            {
                "command": "update_firmware",
                "parameters": {
                    "version": "1.2.0",
                    "url": "https://example.com/firmware/v1.2.0.bin",
                    "auto_restart": True
                },
                "timeout": 300,
                "priority": 7
            }
        )
        print(f"   ✓ Firmware update command sent: {update_cmd.get('command_id')}")


async def example_4_smart_frame_operations():
    """Example 4: Smart frame specific operations"""
    print("\n" + "=" * 70)
    print("Example 4: Smart Frame Operations")
    print("=" * 70)

    # Get user token
    async with AuthServiceClient() as auth_client:
        token_response = await auth_client.generate_dev_token(
            user_id="example_user_003",
            email="user@example.com"
        )
        user_token = token_response["token"]

    async with DeviceServiceClient(auth_token=user_token) as device_client:
        # Register smart frame
        print("\n1. Registering smart frame...")
        frame = await device_client.register_device({
            "device_name": "Kitchen Smart Frame",
            "device_type": "smart_frame",
            "manufacturer": "SmartTech",
            "model": "SF-2024-Pro",
            "serial_number": f"SF_{int(datetime.now().timestamp())}",
            "firmware_version": "1.0.0",
            "connectivity_type": "wifi",
            "security_level": "standard",
            "metadata": {
                "screen_size": "10.1 inch",
                "resolution": "1920x1080",
                "frame_config": {
                    "brightness": 80,
                    "slideshow_interval": 30,
                    "display_mode": "photo_slideshow"
                }
            }
        })
        frame_id = frame["device_id"]
        print(f"   ✓ Smart frame registered: {frame_id}")

        print("\n2. Controlling frame display...")
        # Note: This uses the device command infrastructure
        display_result = await device_client.send_command(
            frame_id,
            {
                "command": "display_control",
                "parameters": {
                    "action": "display_photo",
                    "photo_id": "photo_12345",
                    "transition": "fade",
                    "duration": 10
                }
            }
        )
        print(f"   ✓ Display command sent: {display_result.get('status')}")

        print("\n3. Syncing frame content...")
        sync_result = await device_client.send_command(
            frame_id,
            {
                "command": "sync_content",
                "parameters": {
                    "album_ids": ["album_001", "album_002"],
                    "sync_type": "incremental",
                    "force": False
                },
                "timeout": 300
            }
        )
        print(f"   ✓ Sync command sent: {sync_result.get('status')}")

        print("\n4. Updating frame configuration...")
        updated_frame = await device_client.update_device(
            frame_id,
            {
                "metadata": {
                    "screen_size": "10.1 inch",
                    "resolution": "1920x1080",
                    "frame_config": {
                        "brightness": 85,
                        "slideshow_interval": 60,
                        "display_mode": "photo_slideshow",
                        "orientation": "auto"
                    }
                }
            }
        )
        print(f"   ✓ Frame configuration updated")


async def main():
    """Run all examples"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        await example_1_basic_device_management()
        await example_2_device_authentication_flow()
        await example_3_device_commands()
        await example_4_smart_frame_operations()

        print("\n" + "=" * 70)
        print("✓ All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Device Service Client Examples")
    print("=" * 70)
    print("\nThese examples demonstrate:")
    print("  1. Basic device management (register, get, update, list)")
    print("  2. Device authentication flow (register in auth, authenticate)")
    print("  3. Sending commands to devices")
    print("  4. Smart frame specific operations")
    print("\nNote: Requires running auth_service and device_service")
    print("=" * 70)

    asyncio.run(main())
