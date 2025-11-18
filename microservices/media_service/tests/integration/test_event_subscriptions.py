"""
Media Service Event Subscription Tests

Tests that Media Service correctly handles events from other services
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.media_service.events import MediaEventHandler
from microservices.media_service.models import (
    PhotoMetadata, RotationSchedule, ScheduleType
)


class MockMediaRepository:
    """Mock Media Repository for testing"""

    def __init__(self):
        self.metadata = {}
        self.schedules = {}
        self.cache = {}
        self.deleted_metadata = []
        self.deleted_schedules = []
        self.removed_photos = []

    async def get_photo_metadata(self, file_id):
        """Mock get photo metadata"""
        return self.metadata.get(file_id)

    async def delete_photo_metadata(self, file_id, user_id):
        """Mock delete photo metadata"""
        if file_id in self.metadata:
            del self.metadata[file_id]
            self.deleted_metadata.append(file_id)
            return True
        return False

    async def list_frame_schedules(self, frame_id, user_id):
        """Mock list frame schedules"""
        return [s for s in self.schedules.values() if s.frame_id == frame_id]

    async def delete_rotation_schedule(self, schedule_id, user_id):
        """Mock delete rotation schedule"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            self.deleted_schedules.append(schedule_id)
            return True
        return False

    async def create_or_update_metadata(self, metadata):
        """Mock create or update metadata"""
        self.metadata[metadata.file_id] = metadata
        return metadata


class MockMediaService:
    """Mock Media Service for testing"""

    def __init__(self):
        self.repository = MockMediaRepository()


async def test_file_deleted_event():
    """Test that file.deleted event removes photo metadata"""
    print("\n" + "="*80)
    print("TEST: Handle file.deleted Event")
    print("="*80)

    # Setup
    mock_service = MockMediaService()
    event_handler = MediaEventHandler(mock_service)

    # Prepare test data - file has metadata
    mock_service.repository.metadata["file_123"] = PhotoMetadata(
        file_id="file_123",
        user_id="user_456",
        organization_id=None,
        ai_labels=["sunset", "beach"],
        ai_objects=["ocean"],
        ai_scenes=["outdoor"],
        ai_colors=["blue", "orange"],
        face_detection={},
        quality_score=0.85
    )

    # Create file.deleted event
    event_data = {
        "event_type": "file.deleted",
        "file_id": "file_123",
        "user_id": "user_456",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    await event_handler.handle_file_deleted(event_data)

    # Verify
    assert "file_123" in mock_service.repository.deleted_metadata, "Metadata should be deleted"
    assert "file_123" not in mock_service.repository.metadata, "Metadata should be removed"

    print("✅ TEST PASSED: file.deleted event handled correctly")
    print(f"   Deleted metadata for file_id: file_123")
    return True


async def test_device_deleted_event():
    """Test that device.deleted event cleans up schedules"""
    print("\n" + "="*80)
    print("TEST: Handle device.deleted Event")
    print("="*80)

    # Setup
    mock_service = MockMediaService()
    event_handler = MediaEventHandler(mock_service)

    # Prepare test data - device has 3 schedules
    mock_service.repository.schedules = {
        "sch_1": RotationSchedule(
            schedule_id="sch_1",
            user_id="user_123",
            frame_id="frame_456",
            playlist_id="pl_1",
            schedule_type=ScheduleType.TIME_BASED,
            start_time="08:00",
            end_time="22:00",
            days_of_week=[1, 2, 3, 4, 5],
            rotation_interval=10,
            shuffle=False,
            is_active=True
        ),
        "sch_2": RotationSchedule(
            schedule_id="sch_2",
            user_id="user_123",
            frame_id="frame_456",
            playlist_id="pl_2",
            schedule_type=ScheduleType.TIME_BASED,
            start_time="00:00",
            end_time="23:59",
            days_of_week=[6, 7],
            rotation_interval=15,
            shuffle=True,
            is_active=True
        ),
        "sch_3": RotationSchedule(
            schedule_id="sch_3",
            user_id="user_789",
            frame_id="frame_999",
            playlist_id="pl_3",
            schedule_type=ScheduleType.CONTINUOUS,
            start_time=None,
            end_time=None,
            days_of_week=[],
            rotation_interval=20,
            shuffle=False,
            is_active=True
        )
    }

    # Create device.deleted event
    event_data = {
        "event_type": "device.deleted",
        "device_id": "frame_456",
        "user_id": "user_123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    await event_handler.handle_device_deleted(event_data)

    # Verify
    assert "sch_1" in mock_service.repository.deleted_schedules, "Schedule 1 should be deleted"
    assert "sch_2" in mock_service.repository.deleted_schedules, "Schedule 2 should be deleted"
    assert "sch_3" not in mock_service.repository.deleted_schedules, "Schedule 3 should remain"
    assert "sch_3" in mock_service.repository.schedules, "Schedule 3 should still exist"

    print("✅ TEST PASSED: device.deleted event handled correctly")
    print(f"   Deleted {len(mock_service.repository.deleted_schedules)} schedules for frame_456")
    return True


async def test_file_uploaded_event():
    """Test that file.uploaded event creates initial metadata"""
    print("\n" + "="*80)
    print("TEST: Handle file.uploaded Event")
    print("="*80)

    # Setup
    mock_service = MockMediaService()
    event_handler = MediaEventHandler(mock_service)

    # Create file.uploaded event
    event_data = {
        "event_type": "file.uploaded",
        "file_id": "file_789",
        "user_id": "user_123",
        "organization_id": "org_456",
        "file_type": "image/jpeg",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    await event_handler.handle_file_uploaded(event_data)

    # Verify
    assert "file_789" in mock_service.repository.metadata, "Metadata should be created"
    metadata = mock_service.repository.metadata["file_789"]
    assert metadata.file_id == "file_789", "Metadata should have correct file_id"
    assert metadata.user_id == "user_123", "Metadata should have correct user_id"
    assert metadata.ai_labels == [], "Initial AI labels should be empty"

    print("✅ TEST PASSED: file.uploaded event handled correctly")
    print(f"   Created initial metadata for file_id: file_789")
    return True


async def test_file_uploaded_event_non_image():
    """Test that file.uploaded event skips non-image files"""
    print("\n" + "="*80)
    print("TEST: Handle file.uploaded Event (Non-Image)")
    print("="*80)

    # Setup
    mock_service = MockMediaService()
    event_handler = MediaEventHandler(mock_service)

    # Create file.uploaded event for non-image file
    event_data = {
        "event_type": "file.uploaded",
        "file_id": "file_999",
        "user_id": "user_123",
        "file_type": "application/pdf",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    await event_handler.handle_file_uploaded(event_data)

    # Verify
    assert "file_999" not in mock_service.repository.metadata, "Non-image should not create metadata"

    print("✅ TEST PASSED: file.uploaded event correctly skipped non-image file")
    print(f"   No metadata created for PDF file")
    return True


async def run_all_tests():
    """Run all event subscription tests"""
    print("\n" + "="*80)
    print("MEDIA SERVICE EVENT SUBSCRIPTION TESTS")
    print("="*80)

    tests = [
        ("file.deleted Handler", test_file_deleted_event),
        ("device.deleted Handler", test_device_deleted_event),
        ("file.uploaded Handler", test_file_uploaded_event),
        ("file.uploaded Handler (Non-Image)", test_file_uploaded_event_non_image)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASSED", None))
        except Exception as e:
            results.append((test_name, "FAILED", str(e)))
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, status, _ in results if status == "PASSED")
    failed = sum(1 for _, status, _ in results if status == "FAILED")

    for test_name, status, error in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {status}")
        if error:
            print(f"   Error: {error}")

    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
