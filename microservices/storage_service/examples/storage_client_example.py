"""
Storage Service Client Example

Demonstrates how to use the storage service for file operations including:
- File upload and download
- MinIO/S3 integration
- Photo version management
- Album operations
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageServiceClient:
    """Client for Storage Service operations"""

    def __init__(self, base_url: str = "http://localhost:8230", auth_token: Optional[str] = None):
        """
        Initialize Storage Service client

        Args:
            base_url: Base URL of storage service (default: localhost:8230)
            auth_token: Optional JWT token for authenticated requests
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(300.0),  # 5 minutes for file uploads
            headers=headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def upload_file(
        self,
        file_path: str,
        user_id: str,
        organization_id: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Upload file to storage

        Args:
            file_path: Path to file to upload
            user_id: User identifier
            organization_id: Optional organization ID
            **kwargs: Additional parameters (tags, metadata, etc.)

        Returns:
            Upload response with file_id and download_url
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            with open(file_path, 'rb') as f:
                files = {"file": (path.name, f, "application/octet-stream")}

                data = {
                    "user_id": user_id,
                    "file_name": path.name,
                }

                if organization_id:
                    data["organization_id"] = organization_id

                # Add optional parameters
                if "tags" in kwargs:
                    data["tags"] = str(kwargs["tags"])
                if "metadata" in kwargs:
                    data["metadata"] = str(kwargs["metadata"])

                response = await self.client.post(
                    "/api/v1/storage/upload",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    async def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download file content

        Args:
            file_id: File identifier

        Returns:
            File content as bytes or None
        """
        try:
            response = await self.client.get(f"/api/v1/storage/download/{file_id}")
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata

        Args:
            file_id: File identifier

        Returns:
            File metadata dict
        """
        try:
            response = await self.client.get(f"/api/v1/storage/files/{file_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """
        Delete file

        Args:
            file_id: File identifier
            user_id: User identifier

        Returns:
            True if deleted successfully
        """
        try:
            response = await self.client.delete(
                f"/api/v1/storage/files/{file_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    async def get_presigned_url(
        self,
        file_id: str,
        expires_in: int = 3600
    ) -> Optional[str]:
        """
        Generate pre-signed download URL

        Args:
            file_id: File identifier
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Pre-signed URL or None
        """
        try:
            response = await self.client.post(
                "/api/v1/storage/presigned-url",
                json={
                    "file_id": file_id,
                    "expires_in": expires_in
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("url")
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None


# ==================== Example Usage ====================

async def example_1_basic_file_operations():
    """Example 1: Basic file upload and download"""
    print("\n" + "=" * 70)
    print("Example 1: Basic File Operations")
    print("=" * 70)

    async with StorageServiceClient() as client:
        print("\n1. Uploading file...")

        # Create a test file
        test_file = "/tmp/test_firmware.bin"
        with open(test_file, 'wb') as f:
            f.write(b"Test firmware content" * 1000)

        upload_result = await client.upload_file(
            file_path=test_file,
            user_id="user_123",
            organization_id="org_123",
            tags=["firmware", "test"],
            metadata={"version": "1.0.0", "device": "smart_frame"}
        )

        if upload_result:
            file_id = upload_result.get("file_id")
            print(f"   ✓ File uploaded: {file_id}")
            print(f"     URL: {upload_result.get('download_url')}")

            print("\n2. Getting file info...")
            file_info = await client.get_file_info(file_id)
            if file_info:
                print(f"   ✓ File name: {file_info.get('file_name')}")
                print(f"     File size: {file_info.get('file_size')} bytes")

            print("\n3. Generating presigned URL...")
            presigned_url = await client.get_presigned_url(file_id, expires_in=1800)
            if presigned_url:
                print(f"   ✓ Presigned URL generated (expires in 30 minutes)")
                print(f"     URL: {presigned_url[:60]}...")

            print("\n4. Downloading file...")
            content = await client.download_file(file_id)
            if content:
                print(f"   ✓ Downloaded {len(content)} bytes")

            print("\n5. Deleting file...")
            deleted = await client.delete_file(file_id, "user_123")
            if deleted:
                print(f"   ✓ File deleted successfully")


async def example_2_firmware_storage():
    """Example 2: Firmware binary storage for OTA service"""
    print("\n" + "=" * 70)
    print("Example 2: Firmware Storage for OTA Service")
    print("=" * 70)

    async with StorageServiceClient() as client:
        print("\n1. Uploading firmware binary...")

        # Simulate firmware file
        firmware_file = "/tmp/smartframe_v2.1.0.bin"
        with open(firmware_file, 'wb') as f:
            # Write 5MB of test data
            f.write(b"FIRMWARE_DATA" * 400000)

        firmware_metadata = {
            "device_model": "SF-2024-Pro",
            "version": "2.1.0",
            "checksum_md5": "d41d8cd98f00b204e9800998ecf8427e",
            "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }

        upload_result = await client.upload_file(
            file_path=firmware_file,
            user_id="ota_service",
            organization_id="org_smarttech",
            tags=["firmware", "ota", "production"],
            metadata=firmware_metadata
        )

        if upload_result:
            firmware_id = upload_result.get("file_id")
            print(f"   ✓ Firmware uploaded: {firmware_id}")
            print(f"     Storage path: {upload_result.get('file_path')}")

            print("\n2. Generating download URL for devices...")
            download_url = await client.get_presigned_url(
                firmware_id,
                expires_in=3600  # 1 hour for device downloads
            )

            if download_url:
                print(f"   ✓ Download URL generated for OTA update")
                print(f"     URL: {download_url[:80]}...")
                print(f"     Expires in: 1 hour")

            print("\n3. Verifying file integrity...")
            file_info = await client.get_file_info(firmware_id)
            if file_info:
                stored_checksum = file_info.get("checksum")
                print(f"   ✓ Checksum verified: {stored_checksum}")
                print(f"     File size: {file_info.get('file_size')} bytes")


async def main():
    """Run all examples"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        await example_1_basic_file_operations()
        await example_2_firmware_storage()

        print("\n" + "=" * 70)
        print("✓ All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Storage Service Client Examples")
    print("=" * 70)
    print("\nThese examples demonstrate:")
    print("  1. Basic file upload and download")
    print("  2. Firmware binary storage for OTA service")
    print("\nNote: Requires running storage_service")
    print("=" * 70)

    asyncio.run(main())
