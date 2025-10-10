#!/usr/bin/env python3
"""
Storage Service Image Functionality Test Script

Comprehensive testing of image/photo version management features:
1. Basic file upload/download functionality
2. Photo version save functionality
3. Photo version retrieval
4. Photo version switching
5. Photo version deletion
6. Error handling and edge cases
"""

import asyncio
import aiohttp
import json
import os
import uuid
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import tempfile
import requests
from pathlib import Path

# Add parent directory to path for config access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_manager import ConfigManager

# Test configuration - use config manager for storage service URL
config_manager = ConfigManager("storage_service")
config = config_manager.get_service_config()
BASE_URL = f"http://localhost:{config.service_port}" if config.service_port else "http://localhost:8208"
TEST_USER_ID = "test_user_123"
TEST_PHOTO_ID = "photo_test_001"

class StorageServiceTester:
    """Storage service test suite"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
        self.test_results = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, success: bool, message: str = "", data: Dict = None):
        """Log test result"""
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if data:
            print(f"  Data: {json.dumps(data, indent=2, default=str)}")
    
    async def test_service_health(self) -> bool:
        """Test if the storage service is running"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("service_health", True, "Service is healthy", data)
                    return True
                else:
                    self.log_test("service_health", False, f"Health check failed: {response.status}")
                    return False
        except Exception as e:
            self.log_test("service_health", False, f"Service unreachable: {str(e)}")
            return False
    
    def create_test_image(self) -> bytes:
        """Create a simple test image (minimal PNG)"""
        # Minimal 1x1 pixel PNG file
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D,  # IHDR chunk length
            0x49, 0x48, 0x44, 0x52,  # IHDR
            0x00, 0x00, 0x00, 0x01,  # Width: 1
            0x00, 0x00, 0x00, 0x01,  # Height: 1
            0x08, 0x02,              # Bit depth: 8, Color type: 2 (RGB)
            0x00, 0x00, 0x00,        # Compression, filter, interlace
            0x90, 0x77, 0x53, 0xDE,  # CRC
            0x00, 0x00, 0x00, 0x0C,  # IDAT chunk length
            0x49, 0x44, 0x41, 0x54,  # IDAT
            0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,  # Image data
            0xE2, 0x21, 0xBC, 0x33,  # CRC
            0x00, 0x00, 0x00, 0x00,  # IEND chunk length
            0x49, 0x45, 0x4E, 0x44,  # IEND
            0xAE, 0x42, 0x60, 0x82   # CRC
        ])
        return png_data
    
    async def test_file_upload(self) -> Optional[str]:
        """Test basic file upload functionality"""
        try:
            # Create test image
            image_data = self.create_test_image()
            
            # Prepare form data
            data = aiohttp.FormData()
            data.add_field('user_id', TEST_USER_ID)
            data.add_field('organization_id', 'test_org')
            data.add_field('access_level', 'private')
            data.add_field('file', image_data, filename='test_image.png', content_type='image/png')
            
            async with self.session.post(f"{self.base_url}/api/files/upload", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    file_id = result.get('file_id')
                    self.log_test("file_upload", True, f"File uploaded successfully", {
                        "file_id": file_id,
                        "file_size": result.get('file_size'),
                        "content_type": result.get('content_type')
                    })
                    return file_id
                else:
                    error_text = await response.text()
                    self.log_test("file_upload", False, f"Upload failed: {response.status}, {error_text}")
                    return None
        except Exception as e:
            self.log_test("file_upload", False, f"Upload error: {str(e)}")
            return None
    
    async def test_save_photo_version(self) -> Optional[str]:
        """Test saving a photo version"""
        try:
            # Create a mock AI-generated image URL (we'll use a public image for testing)
            test_image_url = "https://httpbin.org/image/png"
            
            request_data = {
                "photo_id": TEST_PHOTO_ID,
                "user_id": TEST_USER_ID,
                "version_name": "AI Enhanced Version",
                "version_type": "ai_enhanced",
                "processing_mode": "enhance_colors",
                "source_url": test_image_url,
                "save_local": False,
                "processing_params": {
                    "brightness": 1.2,
                    "contrast": 1.1,
                    "saturation": 1.15
                },
                "metadata": {
                    "ai_model": "test_model_v1",
                    "processing_time": 2.5
                },
                "set_as_current": True
            }
            
            async with self.session.post(
                f"{self.base_url}/api/photos/versions/save",
                json=request_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    version_id = result.get('version_id')
                    self.log_test("save_photo_version", True, f"Photo version saved successfully", {
                        "version_id": version_id,
                        "photo_id": result.get('photo_id'),
                        "cloud_url": result.get('cloud_url')
                    })
                    return version_id
                else:
                    error_text = await response.text()
                    self.log_test("save_photo_version", False, f"Save failed: {response.status}, {error_text}")
                    return None
        except Exception as e:
            self.log_test("save_photo_version", False, f"Save error: {str(e)}")
            return None
    
    async def test_get_photo_versions(self) -> bool:
        """Test retrieving photo versions"""
        try:
            params = {"user_id": TEST_USER_ID}
            
            async with self.session.post(
                f"{self.base_url}/api/photos/{TEST_PHOTO_ID}/versions",
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.log_test("get_photo_versions", True, f"Retrieved photo versions", {
                        "photo_id": result.get('photo_id'),
                        "version_count": result.get('version_count'),
                        "current_version_id": result.get('current_version_id')
                    })
                    return True
                else:
                    error_text = await response.text()
                    self.log_test("get_photo_versions", False, f"Get failed: {response.status}, {error_text}")
                    return False
        except Exception as e:
            self.log_test("get_photo_versions", False, f"Get error: {str(e)}")
            return False
    
    async def test_switch_photo_version(self, version_id: str) -> bool:
        """Test switching photo version"""
        try:
            params = {"user_id": TEST_USER_ID}
            
            async with self.session.put(
                f"{self.base_url}/api/photos/{TEST_PHOTO_ID}/versions/{version_id}/switch",
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.log_test("switch_photo_version", True, f"Version switched successfully", {
                        "photo_id": result.get('photo_id'),
                        "current_version_id": result.get('current_version_id')
                    })
                    return True
                else:
                    error_text = await response.text()
                    self.log_test("switch_photo_version", False, f"Switch failed: {response.status}, {error_text}")
                    return False
        except Exception as e:
            self.log_test("switch_photo_version", False, f"Switch error: {str(e)}")
            return False
    
    async def test_delete_photo_version(self, version_id: str) -> bool:
        """Test deleting photo version"""
        try:
            params = {"user_id": TEST_USER_ID}
            
            async with self.session.delete(
                f"{self.base_url}/api/photos/versions/{version_id}",
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.log_test("delete_photo_version", True, f"Version deleted successfully", {
                        "version_id": result.get('version_id')
                    })
                    return True
                else:
                    error_text = await response.text()
                    self.log_test("delete_photo_version", False, f"Delete failed: {response.status}, {error_text}")
                    return False
        except Exception as e:
            self.log_test("delete_photo_version", False, f"Delete error: {str(e)}")
            return False
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n🧪 Testing Error Handling...")
        
        # Test 1: Invalid photo ID
        try:
            params = {"user_id": TEST_USER_ID}
            async with self.session.post(
                f"{self.base_url}/api/photos/invalid_photo_id/versions",
                params=params
            ) as response:
                if response.status == 404 or response.status == 200:  # 200 might return empty list
                    self.log_test("error_invalid_photo_id", True, "Handled invalid photo ID correctly")
                else:
                    self.log_test("error_invalid_photo_id", False, f"Unexpected status: {response.status}")
        except Exception as e:
            self.log_test("error_invalid_photo_id", False, f"Error: {str(e)}")
        
        # Test 2: Missing user ID
        try:
            async with self.session.post(
                f"{self.base_url}/api/photos/{TEST_PHOTO_ID}/versions"
            ) as response:
                if response.status == 422:  # Validation error expected
                    self.log_test("error_missing_user_id", True, "Handled missing user ID correctly")
                else:
                    self.log_test("error_missing_user_id", False, f"Expected 422, got: {response.status}")
        except Exception as e:
            self.log_test("error_missing_user_id", False, f"Error: {str(e)}")
        
        # Test 3: Invalid URL for photo version save
        try:
            request_data = {
                "photo_id": TEST_PHOTO_ID,
                "user_id": TEST_USER_ID,
                "version_name": "Test Invalid URL",
                "version_type": "ai_enhanced",
                "source_url": "https://invalid-url-that-does-not-exist.com/image.jpg",
                "save_local": False,
                "set_as_current": False
            }
            
            async with self.session.post(
                f"{self.base_url}/api/photos/versions/save",
                json=request_data
            ) as response:
                if response.status == 400 or response.status == 500:
                    self.log_test("error_invalid_source_url", True, "Handled invalid source URL correctly")
                else:
                    self.log_test("error_invalid_source_url", False, f"Expected error, got: {response.status}")
        except Exception as e:
            self.log_test("error_invalid_source_url", False, f"Error: {str(e)}")
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Storage Service Image Functionality Tests\n")
        
        # Test 1: Service health
        if not await self.test_service_health():
            print("❌ Service is not healthy. Stopping tests.")
            return
        
        print("\n📤 Testing File Upload...")
        file_id = await self.test_file_upload()
        
        print("\n📸 Testing Photo Version Management...")
        version_id = await self.test_save_photo_version()
        
        await self.test_get_photo_versions()
        
        if version_id:
            await self.test_switch_photo_version(version_id)
            await self.test_delete_photo_version(version_id)
        
        await self.test_error_handling()
        
        # Print summary
        print("\n📊 Test Summary")
        print("=" * 50)
        passed = sum(1 for result in self.test_results.values() if result['success'])
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {test_name}: {result['message']}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {total - passed} tests failed")
        
        return self.test_results

async def main():
    """Main test execution"""
    print("Storage Service Image Functionality Test Suite")
    print("=" * 50)
    
    async with StorageServiceTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Test results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())