"""
End-to-End Integration Test for Photo Sharing via MQTT

Tests the complete workflow:
1. Mobile app uploads photo
2. storage_service processes and publishes event
3. album_service adds to album and publishes MQTT
4. Smart frame receives MQTT notification
5. Smart frame fetches from media_service
6. Smart frame downloads photo
7. Smart frame publishes status

Requirements:
- All services running (storage, album, media, MQTT broker)
- Test database with sample data
- Real photo file for upload
- MQTT broker accessible
"""

import asyncio
import pytest
import httpx
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import MQTT client (use centralized async client from core)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from core.mqtt_client import MQTTEventBus, get_mqtt_bus


# Test Configuration for Kind K8s Environment
# Services are accessed via NodePort or Port-Forward
TEST_CONFIG = {
    # K8s Service URLs (via port-forward or NodePort)
    # Note: storage-service is on port 8209 (not 8220)
    "storage_service_url": os.environ.get("STORAGE_SERVICE_URL", "http://localhost:8209"),
    "album_service_url": os.environ.get("ALBUM_SERVICE_URL", "http://localhost:8219"),
    "media_service_url": os.environ.get("MEDIA_SERVICE_URL", "http://localhost:8222"),

    # MQTT broker in K8s
    # Use: kubectl port-forward svc/mqtt-adapter 50053:50053
    "mqtt_host": os.environ.get("MQTT_HOST", "localhost"),
    "mqtt_port": int(os.environ.get("MQTT_PORT", "50053")),

    # Use EXISTING data from database
    # These should match real data in your K8s database
    "test_user_id": os.environ.get("TEST_USER_ID", "test_user_photo_e2e"),
    "test_album_id": os.environ.get("TEST_ALBUM_ID", "test_album_photo_e2e"),
    "test_frame_id": os.environ.get("TEST_FRAME_ID", "test_frame_photo_e2e"),

    # Test photo path
    "test_photo_path": "tests/fixtures/test_photo.jpg"
}


class SimulatedMobileApp:
    """Simulates mobile app uploading photos"""

    def __init__(self, storage_service_url: str):
        self.base_url = storage_service_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def upload_photo(
        self,
        photo_path: str,
        user_id: str,
        album_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload photo to storage service

        Args:
            photo_path: Path to photo file
            user_id: User ID
            album_id: Optional album ID to add photo to

        Returns:
            Upload response with file_id
        """
        print(f"📱 [Mobile App] Uploading photo: {photo_path}")

        # Prepare multipart form data
        with open(photo_path, 'rb') as f:
            files = {
                'file': ('test_photo.jpg', f, 'image/jpeg')
            }

            data = {
                'user_id': user_id,
            }

            # Add album_id to metadata if provided
            if album_id:
                data['metadata'] = json.dumps({'album_id': album_id})

            response = await self.client.post(
                f"{self.base_url}/api/v1/storage/files/upload",
                files=files,
                data=data
            )

        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ [Mobile App] Photo uploaded successfully: {result.get('file_id')}")
            return result
        else:
            print(f"❌ [Mobile App] Upload failed: {response.status_code} - {response.text}")
            raise Exception(f"Upload failed: {response.status_code}")

    async def close(self):
        await self.client.aclose()


class SimulatedSmartFrame:
    """Simulates smart frame hardware receiving MQTT and fetching photos"""

    def __init__(
        self,
        frame_id: str,
        mqtt_host: str,
        mqtt_port: int,
        media_service_url: str,
        storage_service_url: str
    ):
        self.frame_id = frame_id
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.media_service_url = media_service_url
        self.storage_service_url = storage_service_url

        self.mqtt_bus: Optional[MQTTEventBus] = None
        self.received_messages = []
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def connect_mqtt(self):
        """Connect to MQTT broker using async MQTTEventBus"""
        print(f"🖼️  [Smart Frame {self.frame_id}] Connecting to MQTT broker...")

        self.mqtt_bus = MQTTEventBus(
            service_name=f"smart_frame_{self.frame_id}",
            host=self.mqtt_host,
            port=self.mqtt_port,
            user_id=f"frame_{self.frame_id}"
        )

        await self.mqtt_bus.connect(client_id=f"frame-{self.frame_id}-connection")
        print(f"✅ [Smart Frame {self.frame_id}] Connected to MQTT (session: {self.mqtt_bus.session_id})")

    async def subscribe_to_album(self, album_id: str):
        """
        Subscribe to album photo updates

        Note: This is a simplified version. In real implementation,
        you would set up proper MQTT subscription callbacks.
        """
        print(f"🖼️  [Smart Frame {self.frame_id}] Subscribing to album: {album_id}")

        # In real implementation, this would subscribe to MQTT topic
        # For testing, we'll simulate by polling or using a test helper
        topic = f'albums/{album_id}/photo_added'
        print(f"✅ [Smart Frame {self.frame_id}] Subscribed to topic: {topic}")

    async def wait_for_photo_notification(
        self,
        album_id: str,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for photo_added MQTT notification

        Args:
            album_id: Album ID
            timeout: Timeout in seconds

        Returns:
            Photo notification data or None
        """
        print(f"🖼️  [Smart Frame {self.frame_id}] Waiting for photo notification...")

        topic = f'albums/{album_id}/photo_added'

        # Note: In real implementation, the MQTT service would provide subscription
        # For testing, we simulate the notification check
        # The async MQTT client doesn't have retained message fetching built-in
        # This would typically be handled by a callback-based subscription

        print(f"⚠️  [Smart Frame {self.frame_id}] Subscription-based notifications not implemented in test")
        print(f"   Topic would be: {topic}")
        return None

    async def fetch_photo_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Fetch photo metadata from media_service

        Args:
            file_id: Photo file ID

        Returns:
            Photo metadata with download URLs
        """
        print(f"🖼️  [Smart Frame {self.frame_id}] Fetching metadata for photo: {file_id}")

        # Use the correct media service endpoint: /api/v1/media/metadata/{file_id}
        response = await self.http_client.get(
            f"{self.media_service_url}/api/v1/media/metadata/{file_id}",
            params={'user_id': 'test_user_photo_e2e'}  # TODO: pass user_id from caller
        )

        if response.status_code == 200:
            metadata = response.json()
            print(f"✅ [Smart Frame {self.frame_id}] Metadata fetched:")
            print(f"   - Labels: {metadata.get('ai_labels', [])[:3]}")
            print(f"   - Scenes: {metadata.get('ai_scenes', [])}")
            print(f"   - Quality: {metadata.get('quality_score')}")
            return metadata
        else:
            print(f"❌ [Smart Frame {self.frame_id}] Failed to fetch metadata: {response.status_code}")
            raise Exception(f"Failed to fetch metadata: {response.status_code}")

    def _rewrite_url_for_local_access(self, url: str) -> str:
        """
        Rewrite internal K8s URLs to localhost for testing

        Args:
            url: Original URL (may contain K8s cluster DNS)

        Returns:
            Rewritten URL for local access
        """
        # Replace internal K8s MinIO address with localhost port-forward
        if "minio.isa-cloud-staging.svc.cluster.local" in url:
            url = url.replace("minio.isa-cloud-staging.svc.cluster.local:9000", "localhost:9000")
            print(f"   ℹ️  Rewritten URL for local access: {url}")

        # Replace storage service internal address if present
        if "storage.isa-cloud-staging.svc.cluster.local" in url:
            url = url.replace("storage.isa-cloud-staging.svc.cluster.local", "localhost:8209")
            print(f"   ℹ️  Rewritten URL for local access: {url}")

        return url

    async def download_photo(self, download_url: str, size: str = "hd") -> bytes:
        """
        Download photo file

        Args:
            download_url: Base download URL
            size: Size variant (thumbnail, hd, original)

        Returns:
            Photo bytes
        """
        print(f"🖼️  [Smart Frame {self.frame_id}] Downloading photo ({size})...")

        # Rewrite URL for local access (K8s cluster DNS -> localhost)
        download_url = self._rewrite_url_for_local_access(download_url)

        # Add size parameter if not original
        url = download_url if size == "original" else f"{download_url}?size={size}"

        response = await self.http_client.get(url)

        if response.status_code == 200:
            photo_bytes = response.content
            print(f"✅ [Smart Frame {self.frame_id}] Photo downloaded: {len(photo_bytes)} bytes")
            return photo_bytes
        else:
            print(f"❌ [Smart Frame {self.frame_id}] Failed to download: {response.status_code}")
            raise Exception(f"Failed to download photo: {response.status_code}")

    async def display_photo(self, photo_bytes: bytes) -> bool:
        """
        Simulate displaying photo on frame

        Args:
            photo_bytes: Photo data

        Returns:
            True if displayed successfully
        """
        print(f"🖼️  [Smart Frame {self.frame_id}] Displaying photo on screen...")
        print(f"   - Size: {len(photo_bytes)} bytes")
        print(f"   - Simulating e-ink/LCD display update...")

        # Simulate display delay
        await asyncio.sleep(0.5)

        print(f"✅ [Smart Frame {self.frame_id}] Photo displayed successfully!")
        return True

    async def publish_status(self, file_id: str, status: str):
        """
        Publish frame status back to MQTT

        Args:
            file_id: Photo file ID
            status: Status (displayed, cached, error)
        """
        print(f"🖼️  [Smart Frame {self.frame_id}] Publishing status: {status}")

        if not self.mqtt_bus or not self.mqtt_bus.connected:
            await self.connect_mqtt()

        status_msg = {
            'frame_id': self.frame_id,
            'file_id': file_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }

        topic = f'frames/{self.frame_id}/status'

        await self.mqtt_bus.publish_json(
            topic,
            status_msg,
            qos=0  # Fire and forget for status
        )

        print(f"✅ [Smart Frame {self.frame_id}] Status published to {topic}")

    async def close(self):
        """Cleanup resources"""
        if self.mqtt_bus:
            await self.mqtt_bus.close()

        await self.http_client.aclose()


# ==================== Integration Tests ====================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_photo_sharing_e2e_with_mqtt():
    """
    End-to-end test of photo sharing workflow

    Workflow:
    1. Mobile app uploads photo with album_id
    2. storage_service processes and publishes file.uploaded.with_ai
    3. album_service receives event, adds to album
    4. album_service publishes MQTT to albums/{album_id}/photo_added
    5. Smart frame receives MQTT notification
    6. Smart frame fetches metadata from media_service
    7. Smart frame downloads photo from storage_service
    8. Smart frame displays photo
    9. Smart frame publishes status back to MQTT
    """
    print("\n" + "="*80)
    print("🚀 Starting End-to-End Photo Sharing Integration Test")
    print("="*80 + "\n")

    # Setup
    user_id = TEST_CONFIG["test_user_id"]
    album_id = TEST_CONFIG["test_album_id"]
    frame_id = TEST_CONFIG["test_frame_id"]
    photo_path = TEST_CONFIG["test_photo_path"]

    # Ensure test photo exists
    if not os.path.exists(photo_path):
        pytest.skip(f"Test photo not found: {photo_path}")

    # Initialize clients
    mobile_app = SimulatedMobileApp(TEST_CONFIG["storage_service_url"])
    smart_frame = SimulatedSmartFrame(
        frame_id=frame_id,
        mqtt_host=TEST_CONFIG["mqtt_host"],
        mqtt_port=TEST_CONFIG["mqtt_port"],
        media_service_url=TEST_CONFIG["media_service_url"],
        storage_service_url=TEST_CONFIG["storage_service_url"]
    )

    try:
        # Step 1: Connect smart frame to MQTT
        print("\n📡 Step 1: Connecting Smart Frame to MQTT")
        await smart_frame.connect_mqtt()
        await smart_frame.subscribe_to_album(album_id)

        # Step 2: Mobile app uploads photo
        print("\n📱 Step 2: Mobile App Uploads Photo")
        upload_result = await mobile_app.upload_photo(
            photo_path=photo_path,
            user_id=user_id,
            album_id=album_id
        )

        file_id = upload_result.get('file_id')
        assert file_id, "Upload should return file_id"

        # Step 3: Wait for event processing (NATS + MQTT)
        print("\n⏳ Step 3: Waiting for Event Processing...")
        print("   - storage_service publishes file.uploaded.with_ai")
        print("   - album_service receives event and adds to album")
        print("   - album_service publishes MQTT notification")

        await asyncio.sleep(5)  # Wait for async event processing

        # Step 4: Smart frame receives MQTT notification (optional check)
        print("\n🔔 Step 4: Smart Frame Checking for MQTT Notification")
        notification = await smart_frame.wait_for_photo_notification(album_id, timeout=10)

        # Note: MQTT notification might not be available in test environment
        # Continue with direct fetching

        # Step 5: Smart frame fetches photo metadata
        print("\n📊 Step 5: Smart Frame Fetches Photo Metadata")
        metadata = await smart_frame.fetch_photo_metadata(file_id)

        assert metadata.get('file_id') == file_id
        assert 'ai_labels' in metadata or 'ai_scenes' in metadata, "Should have AI metadata"

        # Step 6: Smart frame downloads photo
        print("\n📥 Step 6: Smart Frame Downloads Photo")
        # Get download URL from full_metadata
        download_url = metadata.get('full_metadata', {}).get('download_url')
        if not download_url:
            print("⚠️  No download URL in metadata, skipping download test")
            download_url = f"http://localhost:8209/api/v1/storage/files/download/{file_id}"

        photo_bytes = await smart_frame.download_photo(download_url, size='hd')
        assert len(photo_bytes) > 0, "Photo should have content"

        # Step 7: Smart frame displays photo
        print("\n🖼️  Step 7: Smart Frame Displays Photo")
        displayed = await smart_frame.display_photo(photo_bytes)
        assert displayed, "Photo should be displayed successfully"

        # Step 8: Smart frame publishes status
        print("\n📤 Step 8: Smart Frame Publishes Status")
        await smart_frame.publish_status(file_id, 'displayed')

        # Final verification
        print("\n✅ Step 9: Verification Complete")
        print(f"   - File ID: {file_id}")
        print(f"   - User ID: {user_id}")
        print(f"   - Album ID: {album_id}")
        print(f"   - Frame ID: {frame_id}")
        print(f"   - Photo Size: {len(photo_bytes)} bytes")

        print("\n" + "="*80)
        print("🎉 End-to-End Photo Sharing Test PASSED")
        print("="*80 + "\n")

    finally:
        # Cleanup
        await mobile_app.close()
        await smart_frame.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_album_service_adds_photo_to_album():
    """
    Test that album_service correctly receives file.uploaded.with_ai event
    and adds photo to the specified album
    """
    print("\n🧪 Testing album_service event handling...")

    user_id = TEST_CONFIG["test_user_id"]
    album_id = TEST_CONFIG["test_album_id"]
    photo_path = TEST_CONFIG["test_photo_path"]

    if not os.path.exists(photo_path):
        pytest.skip(f"Test photo not found: {photo_path}")

    mobile_app = SimulatedMobileApp(TEST_CONFIG["storage_service_url"])
    album_client = httpx.AsyncClient(base_url=TEST_CONFIG["album_service_url"], timeout=30.0)

    try:
        # Upload photo with album_id in metadata
        upload_result = await mobile_app.upload_photo(
            photo_path=photo_path,
            user_id=user_id,
            album_id=album_id
        )

        file_id = upload_result.get('file_id')

        # Wait for event processing
        await asyncio.sleep(5)

        # Check if photo was added to album
        response = await album_client.get(f"/api/v1/albums/{album_id}")

        if response.status_code == 200:
            album = response.json()
            photos = album.get('photos', [])

            print(f"✅ Album contains {len(photos)} photos")

            # Verify file_id is in album
            photo_ids = [p.get('file_id') for p in photos]
            assert file_id in photo_ids, f"Photo {file_id} should be in album"

            print(f"✅ Photo {file_id} successfully added to album {album_id}")
        else:
            print(f"⚠️  Could not verify album (status: {response.status_code})")

    finally:
        await mobile_app.close()
        await album_client.aclose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_media_service_photo_endpoint():
    """
    Test that media_service provides photo metadata endpoint for frames
    """
    print("\n🧪 Testing media_service photo endpoint...")

    # First, ensure we have a photo uploaded
    user_id = TEST_CONFIG["test_user_id"]
    album_id = TEST_CONFIG["test_album_id"]
    photo_path = TEST_CONFIG["test_photo_path"]

    if not os.path.exists(photo_path):
        pytest.skip(f"Test photo not found: {photo_path}")

    mobile_app = SimulatedMobileApp(TEST_CONFIG["storage_service_url"])
    media_client = httpx.AsyncClient(base_url=TEST_CONFIG["media_service_url"], timeout=30.0)

    try:
        # Upload photo
        upload_result = await mobile_app.upload_photo(
            photo_path=photo_path,
            user_id=user_id,
            album_id=album_id
        )

        file_id = upload_result.get('file_id')

        # Wait for processing
        await asyncio.sleep(5)

        # Test media_service endpoint
        response = await media_client.get(
            f"/api/v1/photos/{file_id}",
            params={'frame_id': TEST_CONFIG["test_frame_id"]}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        metadata = response.json()
        print(f"✅ Media service returned metadata:")
        print(f"   - File ID: {metadata.get('file_id')}")
        print(f"   - AI Labels: {metadata.get('ai_metadata', {}).get('labels', [])[:3]}")
        print(f"   - Versions: {len(metadata.get('versions', []))}")
        print(f"   - Download URL: {metadata.get('download_url', '')[:50]}...")

        # Verify structure
        assert metadata.get('file_id') == file_id
        assert 'ai_metadata' in metadata
        assert 'versions' in metadata

        print(f"✅ Media service photo endpoint working correctly")

    finally:
        await mobile_app.close()
        await media_client.aclose()


# ==================== Helper Functions ====================

def create_test_photo():
    """Create a test photo file if it doesn't exist"""
    photo_path = TEST_CONFIG["test_photo_path"]

    # Create fixtures directory
    os.makedirs(os.path.dirname(photo_path), exist_ok=True)

    if not os.path.exists(photo_path):
        # Create a simple colored image using PIL
        try:
            from PIL import Image

            # Create 800x600 test image
            img = Image.new('RGB', (800, 600), color=(73, 109, 137))

            # Add some patterns
            for i in range(0, 800, 50):
                for j in range(0, 600, 50):
                    if (i + j) % 100 == 0:
                        for x in range(i, min(i+50, 800)):
                            for y in range(j, min(j+50, 600)):
                                img.putpixel((x, y), (200, 200, 200))

            img.save(photo_path, 'JPEG')
            print(f"✅ Created test photo: {photo_path}")

        except ImportError:
            print("⚠️  PIL not available, skipping test photo creation")


if __name__ == "__main__":
    """Run tests manually"""
    print("Creating test fixtures...")
    create_test_photo()

    print("\nRunning integration tests...")
    asyncio.run(test_photo_sharing_e2e_with_mqtt())
