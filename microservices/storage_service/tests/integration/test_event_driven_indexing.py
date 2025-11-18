#!/usr/bin/env python3
"""
Test Event-Driven File Indexing

Tests the asynchronous event-driven indexing architecture
"""
import sys
import os
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource


def test_event_types_exist():
    """Test that all required event types exist"""
    print("\n" + "="*60)
    print("TEST 1: Event Types Exist")
    print("="*60)

    # Verify event types are defined
    assert hasattr(EventType, 'FILE_INDEXING_REQUESTED'), "FILE_INDEXING_REQUESTED not found"
    assert hasattr(EventType, 'FILE_INDEXED'), "FILE_INDEXED not found"
    assert hasattr(EventType, 'FILE_INDEXING_FAILED'), "FILE_INDEXING_FAILED not found"

    # Verify values
    assert EventType.FILE_INDEXING_REQUESTED.value == "file.indexing.requested"
    assert EventType.FILE_INDEXED.value == "file.indexed"
    assert EventType.FILE_INDEXING_FAILED.value == "file.indexing.failed"

    print("✅ All file indexing event types are defined correctly")
    print(f"   - FILE_INDEXING_REQUESTED: {EventType.FILE_INDEXING_REQUESTED.value}")
    print(f"   - FILE_INDEXED: {EventType.FILE_INDEXED.value}")
    print(f"   - FILE_INDEXING_FAILED: {EventType.FILE_INDEXING_FAILED.value}")
    return True


def test_file_indexing_requested_event_structure():
    """Test FILE_INDEXING_REQUESTED event has correct structure"""
    print("\n" + "="*60)
    print("TEST 2: FILE_INDEXING_REQUESTED Event Structure")
    print("="*60)

    event = Event(
        event_type=EventType.FILE_INDEXING_REQUESTED,
        source=ServiceSource.STORAGE_SERVICE,
        data={
            "file_id": "test_file_123",
            "user_id": "user_456",
            "organization_id": "org_789",
            "file_name": "test_document.txt",
            "file_type": "text/plain",
            "file_size": 1024,
            "metadata": {"category": "documents"},
            "tags": ["test", "demo"],
            "bucket_name": "user-files",
            "object_name": "user_456/test_file_123"
        }
    )

    event_dict = event.to_dict()

    # Verify event structure
    assert event_dict["type"] == "file.indexing.requested", f"Expected 'file.indexing.requested', got {event_dict['type']}"
    assert event_dict["source"] == "storage_service", f"Expected 'storage_service', got {event_dict['source']}"
    assert event_dict["data"]["file_id"] == "test_file_123"
    assert event_dict["data"]["user_id"] == "user_456"
    assert event_dict["data"]["bucket_name"] == "user-files"
    assert event_dict["data"]["object_name"] == "user_456/test_file_123"
    assert "id" in event_dict
    assert "timestamp" in event_dict

    print("✅ FILE_INDEXING_REQUESTED event structure is correct")
    print(f"   Event ID: {event_dict['id']}")
    print(f"   Type: {event_dict['type']}")
    print(f"   Source: {event_dict['source']}")
    print(f"   File ID: {event_dict['data']['file_id']}")
    print(f"   Bucket: {event_dict['data']['bucket_name']}")
    return True


def test_file_indexed_event_structure():
    """Test FILE_INDEXED event has correct structure"""
    print("\n" + "="*60)
    print("TEST 3: FILE_INDEXED Event Structure")
    print("="*60)

    event = Event(
        event_type=EventType.FILE_INDEXED,
        source=ServiceSource.STORAGE_SERVICE,
        data={
            "file_id": "test_file_123",
            "user_id": "user_456",
            "file_name": "test_document.txt",
            "file_size": 1024,
            "indexed_at": datetime.utcnow().isoformat()
        }
    )

    event_dict = event.to_dict()

    # Verify event structure
    assert event_dict["type"] == "file.indexed", f"Expected 'file.indexed', got {event_dict['type']}"
    assert event_dict["source"] == "storage_service"
    assert event_dict["data"]["file_id"] == "test_file_123"
    assert "indexed_at" in event_dict["data"]

    print("✅ FILE_INDEXED event structure is correct")
    print(f"   Event ID: {event_dict['id']}")
    print(f"   File ID: {event_dict['data']['file_id']}")
    print(f"   Indexed at: {event_dict['data']['indexed_at']}")
    return True


def test_file_indexing_failed_event_structure():
    """Test FILE_INDEXING_FAILED event has correct structure"""
    print("\n" + "="*60)
    print("TEST 4: FILE_INDEXING_FAILED Event Structure")
    print("="*60)

    event = Event(
        event_type=EventType.FILE_INDEXING_FAILED,
        source=ServiceSource.STORAGE_SERVICE,
        data={
            "file_id": "test_file_123",
            "user_id": "user_456",
            "error": "Failed to download file from MinIO"
        }
    )

    event_dict = event.to_dict()

    # Verify event structure
    assert event_dict["type"] == "file.indexing.failed", f"Expected 'file.indexing.failed', got {event_dict['type']}"
    assert event_dict["source"] == "storage_service"
    assert event_dict["data"]["file_id"] == "test_file_123"
    assert "error" in event_dict["data"]

    print("✅ FILE_INDEXING_FAILED event structure is correct")
    print(f"   Event ID: {event_dict['id']}")
    print(f"   File ID: {event_dict['data']['file_id']}")
    print(f"   Error: {event_dict['data']['error']}")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("EVENT-DRIVEN FILE INDEXING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["event_types_exist"] = test_event_types_exist()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["event_types_exist"] = False

    try:
        results["indexing_requested_structure"] = test_file_indexing_requested_event_structure()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["indexing_requested_structure"] = False

    try:
        results["indexed_structure"] = test_file_indexed_event_structure()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["indexed_structure"] = False

    try:
        results["indexing_failed_structure"] = test_file_indexing_failed_event_structure()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["indexing_failed_structure"] = False

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nEvent-Driven Indexing Architecture:")
        print("  1. FILE_INDEXING_REQUESTED - Published when file uploaded")
        print("  2. Event handler processes indexing asynchronously")
        print("  3. FILE_INDEXED - Published on success")
        print("  4. FILE_INDEXING_FAILED - Published on failure")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = run_all_tests()

    # Exit with appropriate code
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)
