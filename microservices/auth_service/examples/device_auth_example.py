"""
Device Authentication Client Example

Professional client for IoT device authentication with lifecycle management.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeviceCredentials:
    """Device credentials from registration"""
    device_id: str
    device_secret: str
    organization_id: str
    device_name: Optional[str]
    device_type: Optional[str]
    status: str
    created_at: str


@dataclass
class DeviceToken:
    """Device access token"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 86400


class DeviceAuthClient:
    """Professional Device Authentication Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8201",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=50,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "device-auth-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def register_device(
        self,
        device_id: str,
        organization_id: str,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_days: Optional[int] = None
    ) -> DeviceCredentials:
        """Register new device - returns device_secret ONCE"""
        payload = {
            "device_id": device_id,
            "organization_id": organization_id
        }
        if device_name:
            payload["device_name"] = device_name
        if device_type:
            payload["device_type"] = device_type
        if metadata:
            payload["metadata"] = metadata
        if expires_days:
            payload["expires_days"] = expires_days

        result = await self._make_request("POST", "/api/v1/auth/device/register", json=payload)

        if not result.get("success"):
            raise Exception(result.get("error", "Registration failed"))

        return DeviceCredentials(
            device_id=result["device_id"],
            device_secret=result["device_secret"],
            organization_id=result["organization_id"],
            device_name=result.get("device_name"),
            device_type=result.get("device_type"),
            status=result["status"],
            created_at=result["created_at"]
        )

    async def authenticate_device(self, device_id: str, device_secret: str) -> DeviceToken:
        """Authenticate device and get access token"""
        result = await self._make_request(
            "POST",
            "/api/v1/auth/device/authenticate",
            json={"device_id": device_id, "device_secret": device_secret}
        )

        if not result.get("authenticated"):
            raise Exception(result.get("error", "Authentication failed"))

        return DeviceToken(
            access_token=result["access_token"],
            token_type=result.get("token_type", "Bearer"),
            expires_in=result.get("expires_in", 86400)
        )

    async def verify_device_token(self, token: str) -> Dict[str, Any]:
        """Verify device access token"""
        return await self._make_request(
            "POST",
            "/api/v1/auth/device/verify-token",
            json={"token": token}
        )

    async def refresh_device_secret(self, device_id: str, organization_id: str) -> str:
        """Refresh device secret - returns new secret ONCE"""
        result = await self._make_request(
            "POST",
            f"/api/v1/auth/device/{device_id}/refresh-secret",
            params={"organization_id": organization_id}
        )

        if not result.get("success"):
            raise Exception(result.get("error", "Secret refresh failed"))

        return result["device_secret"]

    async def revoke_device(self, device_id: str, organization_id: str) -> bool:
        """Revoke device credentials"""
        result = await self._make_request(
            "DELETE",
            f"/api/v1/auth/device/{device_id}",
            params={"organization_id": organization_id}
        )
        return result.get("success", False)

    async def list_devices(self, organization_id: str) -> List[Dict[str, Any]]:
        """List all devices for organization"""
        result = await self._make_request(
            "GET",
            "/api/v1/auth/device/list",
            params={"organization_id": organization_id}
        )

        if not result.get("success"):
            raise Exception(result.get("error", "Failed to list devices"))

        return result.get("devices", [])

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Device Authentication Client Examples")
    print("=" * 70)

    async with DeviceAuthClient() as client:
        # Example 1: Register device
        print("\n1. Registering Device")
        print("-" * 70)
        credentials = await client.register_device(
            device_id=f"smartframe_{int(datetime.now().timestamp())}",
            organization_id="org_df12fb0e7a8e",
            device_name="Living Room Smart Frame",
            device_type="smart_frame",
            metadata={
                "model": "SF-2024-Pro",
                "firmware": "2.1.0",
                "location": "Living Room"
            },
            expires_days=365
        )

        print(f"✓ Device registered successfully")
        print(f"  Device ID: {credentials.device_id}")
        print(f"  Secret: {credentials.device_secret[:20]}...")
        print(f"  ⚠️  SAVE THIS SECRET - shown only once!")
        print(f"  Organization: {credentials.organization_id}")

        # Example 2: Authenticate device
        print("\n2. Authenticating Device")
        print("-" * 70)
        token = await client.authenticate_device(
            credentials.device_id,
            credentials.device_secret
        )

        print(f"✓ Device authenticated successfully")
        print(f"  Access Token: {token.access_token[:50]}...")
        print(f"  Expires In: {token.expires_in} seconds ({token.expires_in/3600:.1f} hours)")

        # Example 3: Verify token
        print("\n3. Verifying Device Token")
        print("-" * 70)
        verification = await client.verify_device_token(token.access_token)

        if verification["valid"]:
            print(f"✓ Token is valid")
            print(f"  Device ID: {verification['device_id']}")
            print(f"  Organization: {verification['organization_id']}")
            print(f"  Device Type: {verification.get('device_type')}")

        # Example 4: List devices
        print("\n4. Listing Organization Devices")
        print("-" * 70)
        devices = await client.list_devices("org_df12fb0e7a8e")

        print(f"Found {len(devices)} devices:")
        for device in devices[:3]:  # Show first 3
            status_icon = "🟢" if device["status"] == "active" else "🔴"
            print(f"  {status_icon} {device.get('device_name', 'Unnamed')}")
            print(f"     ID: {device['device_id']}")
            print(f"     Type: {device.get('device_type', 'N/A')}")
            print(f"     Auth Count: {device.get('authentication_count', 0)}")

        # Example 5: Refresh secret
        print("\n5. Refreshing Device Secret")
        print("-" * 70)
        new_secret = await client.refresh_device_secret(
            credentials.device_id,
            credentials.organization_id
        )

        print(f"✓ Device secret rotated successfully")
        print(f"  New Secret: {new_secret[:20]}...")
        print(f"  ⚠️  Update device with new secret!")

        # Example 6: Authenticate with new secret
        print("\n6. Authenticating with New Secret")
        print("-" * 70)
        new_token = await client.authenticate_device(
            credentials.device_id,
            new_secret
        )
        print(f"✓ Authenticated with new secret")
        print(f"  New Token: {new_token.access_token[:50]}...")

        # Example 7: Revoke device
        print("\n7. Revoking Device")
        print("-" * 70)
        success = await client.revoke_device(
            credentials.device_id,
            credentials.organization_id
        )

        if success:
            print(f"✓ Device {credentials.device_id} revoked successfully")

        # Show metrics
        print("\n8. Client Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Error rate: {metrics['error_rate']:.1%}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
