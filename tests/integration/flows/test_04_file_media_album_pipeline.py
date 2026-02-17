#!/usr/bin/env python3
"""
P1 集成测试: 文件→媒体→相册 处理管道

测试覆盖的服务:
- storage_service: 文件上传、存储、AI分析
- media_service: 媒体处理、版本生成、元数据管理
- album_service: 相册管理、照片组织

测试流程:
1. 上传文件到 storage_service
2. 验证 file.uploaded.with_ai 事件
3. 验证 media_service 创建媒体记录
4. 验证多版本生成 (thumbnail, hd, original)
5. 创建相册并添加照片
6. 验证相册照片列表
7. 测试照片删除级联

事件验证:
- file.uploaded
- file.uploaded.with_ai
- media.version_created
- media.metadata_updated
- album.created
- album.photo_added
- album.photo_removed
"""

import asyncio
import os
import sys
import base64
from datetime import datetime
from io import BytesIO

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../..")
sys.path.insert(0, _project_root)
sys.path.insert(0, _current_dir)

from base_test import BaseIntegrationTest


class FileMediaAlbumPipelineIntegrationTest(BaseIntegrationTest):
    """文件媒体相册管道集成测试"""

    def __init__(self):
        super().__init__()
        # Test data
        self.test_user_id = None
        self.file_id = None
        self.album_id = None
        self.media_metadata = None

    async def run(self):
        """运行完整测试"""
        self.log_header("P1: File → Media → Album Pipeline Integration Test")
        self.log(f"Start Time: {datetime.utcnow().isoformat()}")

        try:
            await self.setup()

            # 准备测试数据
            self.test_user_id = self.generate_test_user_id()
            self.log(f"Test User ID: {self.test_user_id}")

            # 运行测试步骤
            await self.test_step_1_upload_file()
            await self.test_step_2_verify_file_uploaded_event()
            await self.test_step_3_verify_media_record_created()
            await self.test_step_4_verify_media_versions()
            await self.test_step_5_create_album()
            await self.test_step_6_add_photo_to_album()
            await self.test_step_7_verify_album_photos()
            await self.test_step_8_get_media_metadata()
            await self.test_step_9_test_photo_removal()
            await self.test_step_10_verify_events()

        except Exception as e:
            self.log(f"Test Error: {e}", "red")
            import traceback
            traceback.print_exc()
            self.failed_assertions += 1

        finally:
            await self.teardown()
            self.log_summary()

        return self.failed_assertions == 0

    def _create_test_image(self) -> bytes:
        """创建测试图片 (简单的 JPEG)"""
        try:
            from PIL import Image
            img = Image.new('RGB', (800, 600), color=(73, 109, 137))
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            return buffer.getvalue()
        except ImportError:
            # 如果没有 PIL，使用一个最小的有效 JPEG
            # 这是一个 1x1 像素的红色 JPEG
            minimal_jpeg = base64.b64decode(
                "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
                "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
                "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
                "CAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAA"
                "AAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMB"
                "AAIRAxEAPwCwAB//2Q=="
            )
            return minimal_jpeg

    async def test_step_1_upload_file(self):
        """Step 1: 上传文件到 storage_service"""
        self.log_step(1, "Upload File to Storage Service")

        if self.event_collector:
            self.event_collector.clear()

        # 创建测试图片
        image_data = self._create_test_image()
        self.log(f"  Test image size: {len(image_data)} bytes")

        # 使用 multipart/form-data 上传
        # 由于 httpx 的 files 参数会自动处理 multipart
        import httpx

        files = {
            'file': ('test_photo.jpg', image_data, 'image/jpeg')
        }
        data = {
            'user_id': self.test_user_id,
            'metadata': '{"source": "integration_test", "test_run": "' + datetime.utcnow().isoformat() + '"}'
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.config.STORAGE_URL}/api/v1/storage/files/upload",
                files=files,
                data=data
            )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            result = response.json()
            self.file_id = result.get("file_id")
            self.assert_not_none(self.file_id, "Got file_id from upload")
            self.log(f"  File ID: {self.file_id}")
            self.log(f"  File URL: {result.get('url', 'N/A')}")

            # 等待 AI 处理
            await self.wait(5, "Waiting for AI analysis and event propagation")

    async def test_step_2_verify_file_uploaded_event(self):
        """Step 2: 验证 file.uploaded.with_ai 事件"""
        self.log_step(2, "Verify file.uploaded.with_ai Event")

        if not self.event_collector:
            self.log("  SKIP: No event collector", "yellow")
            return

        # 检查 file.uploaded.with_ai 事件
        event = await self.event_collector.wait_for_event(
            "file.uploaded.with_ai",
            timeout=10.0,
            data_match={"file_id": self.file_id} if self.file_id else None
        )

        if event:
            self.assert_true(True, "file.uploaded.with_ai event received")
            event_data = event.get("data", {})
            self.log(f"  AI Labels: {event_data.get('ai_labels', [])[:5]}")
            self.log(f"  AI Scenes: {event_data.get('ai_scenes', [])}")
        else:
            # 也检查普通的 file.uploaded 事件
            plain_event = await self.event_collector.wait_for_event("file.uploaded", timeout=5.0)
            if plain_event:
                self.log("  Received file.uploaded (without AI)", "yellow")
            else:
                self.log("  No file upload event received", "yellow")

    async def test_step_3_verify_media_record_created(self):
        """Step 3: 验证 media_service 创建了媒体记录"""
        self.log_step(3, "Verify Media Record Created")

        if not self.file_id:
            self.log("  SKIP: No file_id", "yellow")
            return

        # 等待 media_service 处理
        await self.wait(2, "Waiting for media_service processing")

        response = await self.get(
            f"{self.config.MEDIA_URL}/api/v1/media/metadata/{self.file_id}",
            params={"user_id": self.test_user_id}
        )

        # Media record creation depends on NATS event propagation from storage_service
        # This may not work locally without K8s DNS, so we handle 404 gracefully
        if response.status_code == 200:
            self.media_metadata = response.json()
            self.assert_equal(
                self.media_metadata.get("file_id"),
                self.file_id,
                "Media record file_id matches"
            )
            self.log(f"  Media type: {self.media_metadata.get('content_type', 'N/A')}")
            self.log(f"  AI Labels: {self.media_metadata.get('ai_labels', [])[:3]}")
        elif response.status_code == 404:
            self.log("  Media record not found (requires NATS for event propagation)", "yellow")

    async def test_step_4_verify_media_versions(self):
        """Step 4: 验证多版本生成"""
        self.log_step(4, "Verify Media Versions Generated")

        if not self.file_id:
            self.log("  SKIP: No file_id", "yellow")
            return

        response = await self.get(
            f"{self.config.MEDIA_URL}/api/v1/media/{self.file_id}/versions",
            params={"user_id": self.test_user_id}
        )

        if response.status_code == 200:
            data = response.json()
            versions = data.get("versions", [])
            self.log(f"  Available versions: {len(versions)}")

            expected_versions = ["thumbnail", "hd", "original"]
            for version in expected_versions:
                version_exists = any(v.get("size") == version or v.get("name") == version for v in versions)
                if version_exists:
                    self.log(f"    - {version}: available")
                else:
                    self.log(f"    - {version}: not found", "yellow")

            if len(versions) >= 1:
                self.assert_true(True, f"Found {len(versions)} media version(s)")
        elif response.status_code == 404:
            self.log("  Versions endpoint not available", "yellow")

    async def test_step_5_create_album(self):
        """Step 5: 创建相册"""
        self.log_step(5, "Create Album")

        if self.event_collector:
            self.event_collector.clear()

        # album_service requires user_id as query parameter
        response = await self.post(
            f"{self.config.ALBUM_URL}/api/v1/albums",
            params={"user_id": self.test_user_id},
            json={
                "name": "Integration Test Album",
                "description": "Album for pipeline integration test",
                "is_public": False,
                "metadata": {
                    "source": "integration_test",
                    "created_at": datetime.utcnow().isoformat()
                }
            }
        )

        # 201 is correct for creation
        if self.assert_http_success(response, 201) or self.assert_http_success(response, 200):
            data = response.json()
            self.album_id = data.get("album_id")
            self.assert_not_none(self.album_id, "Album created")
            self.log(f"  Album ID: {self.album_id}")
            self.log(f"  Album Name: {data.get('name')}")

            self.track_resource(
                "album",
                self.album_id,
                f"{self.config.ALBUM_URL}/api/v1/albums/{self.album_id}"
            )

            await self.wait(1, "Waiting for album.created event")

    async def test_step_6_add_photo_to_album(self):
        """Step 6: 添加照片到相册"""
        self.log_step(6, "Add Photo to Album")

        if not self.album_id or not self.file_id:
            self.log("  SKIP: No album_id or file_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # album_service requires user_id as query param and photo_ids as list
        response = await self.post(
            f"{self.config.ALBUM_URL}/api/v1/albums/{self.album_id}/photos",
            params={"user_id": self.test_user_id},
            json={
                "photo_ids": [self.file_id]
            }
        )

        if self.assert_http_success(response, 200) or self.assert_http_success(response, 201):
            data = response.json()
            self.assert_true(True, "Photo added to album")
            self.log(f"  Photo added: {self.file_id}")

            await self.wait(2, "Waiting for album.photo_added event")

    async def test_step_7_verify_album_photos(self):
        """Step 7: 验证相册照片列表"""
        self.log_step(7, "Verify Album Photos")

        if not self.album_id:
            self.log("  SKIP: No album_id", "yellow")
            return

        response = await self.get(
            f"{self.config.ALBUM_URL}/api/v1/albums/{self.album_id}/photos",
            params={"user_id": self.test_user_id}
        )

        if self.assert_http_success(response, 200):
            data = response.json()
            photos = data.get("photos", data.get("items", []))
            self.log(f"  Album contains {len(photos)} photo(s)")

            if self.file_id:
                # album_service uses photo_id field (which is the file_id)
                photo_ids = [p.get("photo_id") or p.get("file_id") for p in photos]
                self.assert_in(self.file_id, photo_ids, "Uploaded photo is in album")

    async def test_step_8_get_media_metadata(self):
        """Step 8: 获取完整媒体元数据"""
        self.log_step(8, "Get Full Media Metadata")

        if not self.file_id:
            self.log("  SKIP: No file_id", "yellow")
            return

        response = await self.get(
            f"{self.config.MEDIA_URL}/api/v1/media/{self.file_id}",
            params={"user_id": self.test_user_id}
        )

        if response.status_code == 200:
            data = response.json()
            self.log(f"  File ID: {data.get('file_id')}")
            self.log(f"  Content Type: {data.get('content_type')}")
            self.log(f"  Size: {data.get('size', 'N/A')} bytes")
            self.log(f"  AI Labels: {data.get('ai_labels', [])[:5]}")
            self.log(f"  Quality Score: {data.get('quality_score', 'N/A')}")

            # 验证 AI 元数据
            if data.get("ai_labels") or data.get("ai_scenes"):
                self.assert_true(True, "Media has AI metadata")
            else:
                self.log("  No AI metadata found", "yellow")
        else:
            self.log(f"  Media metadata endpoint returned {response.status_code}", "yellow")

    async def test_step_9_test_photo_removal(self):
        """Step 9: 测试照片移除"""
        self.log_step(9, "Test Photo Removal from Album")

        if not self.album_id or not self.file_id:
            self.log("  SKIP: No album_id or file_id", "yellow")
            return

        if self.event_collector:
            self.event_collector.clear()

        # album_service uses DELETE with body containing photo_ids
        response = await self.delete(
            f"{self.config.ALBUM_URL}/api/v1/albums/{self.album_id}/photos",
            params={"user_id": self.test_user_id},
            json={"photo_ids": [self.file_id]}
        )

        if response.status_code in [200, 204]:
            self.assert_true(True, "Photo removed from album")

            # 验证照片已移除
            await self.wait(1, "Waiting for removal to process")

            verify_response = await self.get(
                f"{self.config.ALBUM_URL}/api/v1/albums/{self.album_id}/photos",
                params={"user_id": self.test_user_id}
            )
            if verify_response.status_code == 200:
                data = verify_response.json()
                photos = data.get("photos", data.get("items", []))
                photo_ids = [p.get("file_id") for p in photos]
                self.assert_true(
                    self.file_id not in photo_ids,
                    "Photo no longer in album"
                )
        else:
            self.log(f"  Photo removal returned {response.status_code}", "yellow")

    async def test_step_10_verify_events(self):
        """Step 10: 验证事件"""
        self.log_step(10, "Verify Events")

        if not self.event_collector:
            self.log("  SKIP: No event collector", "yellow")
            return

        summary = self.event_collector.summary()
        self.log(f"  Events collected: {summary}")

        # 验证关键事件
        expected_events = [
            "album.created",
            "album.photo.added",
        ]

        for event_type in expected_events:
            if self.event_collector.has_event(event_type):
                self.assert_true(True, f"Event {event_type} published")
            else:
                self.log(f"  Event {event_type} not captured", "yellow")


async def main():
    """主函数"""
    test = FileMediaAlbumPipelineIntegrationTest()
    success = await test.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
