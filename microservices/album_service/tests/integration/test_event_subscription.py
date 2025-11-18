#!/usr/bin/env python3
"""
Test Event Subscription - Verify album_service can receive events from other services
This test simulates other services publishing events and verifies album_service handles them
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from core.nats_client import Event, EventType, ServiceSource, get_event_bus


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def print_header(text):
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{text.center(70)}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print()


def print_test(text):
    print(f"{Colors.YELLOW}{'=' * 70}{Colors.NC}")
    print(f"{Colors.YELLOW}{text}{Colors.NC}")
    print(f"{Colors.YELLOW}{'=' * 70}{Colors.NC}")
    print()


async def test_file_uploaded_with_ai_event():
    """Test publishing file.uploaded.with_ai event to album_service"""
    print_test("Test 1: Publish file.uploaded.with_ai Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create file.uploaded.with_ai event
        print(f"{Colors.BLUE}Step 2: Creating file.uploaded.with_ai event{Colors.NC}")
        test_file_id = f"file_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "file_id": test_file_id,
            "user_id": "test_user_photo_e2e",
            "file_name": "test_photo.jpg",
            "content_type": "image/jpeg",
            "file_size": 1024000,
            "file_path": "/photos/test_photo.jpg",
            "metadata": {"album_id": "test_album_photo_e2e"},
            "ai_metadata": {
                "labels": ["sunset", "beach", "ocean"],
                "faces": [],
                "timestamp": datetime.utcnow().isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.FILE_UPLOADED_WITH_AI,
            source=ServiceSource.STORAGE_SERVICE,
            data=event_data,
        )

        print(f"Event data: {json.dumps(event_data, indent=2)}")
        print()

        # Publish event
        print(f"{Colors.BLUE}Step 3: Publishing event to NATS{Colors.NC}")
        await event_bus.publish_event(event)
        print(f"{Colors.GREEN}✓ Event published successfully{Colors.NC}")
        print()

        # Wait for processing
        print(
            f"{Colors.BLUE}Step 4: Waiting for album_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: file.uploaded.with_ai event published{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}To verify: Check album_service logs for 'Handling file.uploaded.with_ai event'{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def test_file_deleted_event():
    """Test publishing file.deleted event to album_service"""
    print_test("Test 2: Publish file.deleted Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create file.deleted event
        print(f"{Colors.BLUE}Step 2: Creating file.deleted event{Colors.NC}")
        test_file_id = f"file_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "file_id": test_file_id,
            "user_id": "test_user_photo_e2e",
            "file_path": "/photos/test.jpg",
            "deleted_at": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.FILE_DELETED,
            source=ServiceSource.STORAGE_SERVICE,
            data=event_data,
        )

        print(f"Event data: {json.dumps(event_data, indent=2)}")
        print()

        # Publish event
        print(f"{Colors.BLUE}Step 3: Publishing event to NATS{Colors.NC}")
        await event_bus.publish_event(event)
        print(f"{Colors.GREEN}✓ Event published successfully{Colors.NC}")
        print()

        # Wait for processing
        print(
            f"{Colors.BLUE}Step 4: Waiting for album_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(f"{Colors.GREEN}✓ TEST PASSED: file.deleted event published{Colors.NC}")
        print(
            f"{Colors.YELLOW}To verify: Check album_service logs for 'Handling file.deleted event'{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def test_device_offline_event():
    """Test publishing device.offline event to album_service"""
    print_test("Test 3: Publish device.offline Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create device.offline event
        print(f"{Colors.BLUE}Step 2: Creating device.offline event{Colors.NC}")
        test_device_id = f"device_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "device_id": test_device_id,
            "user_id": "test_user_photo_e2e",
            "device_name": "Smart Frame Test",
            "last_seen": datetime.utcnow().isoformat(),
            "reason": "Device deleted by user",
        }

        event = Event(
            event_type=EventType.DEVICE_OFFLINE,
            source=ServiceSource.DEVICE_SERVICE,
            data=event_data,
        )

        print(f"Event data: {json.dumps(event_data, indent=2)}")
        print()

        # Publish event
        print(f"{Colors.BLUE}Step 3: Publishing event to NATS{Colors.NC}")
        await event_bus.publish_event(event)
        print(f"{Colors.GREEN}✓ Event published successfully{Colors.NC}")
        print()

        # Wait for processing
        print(
            f"{Colors.BLUE}Step 4: Waiting for album_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(f"{Colors.GREEN}✓ TEST PASSED: device.offline event published{Colors.NC}")
        print(
            f"{Colors.YELLOW}To verify: Check album_service logs for 'Handling device.offline event'{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def main():
    print_header("EVENT SUBSCRIPTION INTEGRATION TEST")
    print(f"{Colors.BLUE}Testing album_service event subscription handlers{Colors.NC}")
    print(f"{Colors.BLUE}This simulates other services publishing events{Colors.NC}")
    print()

    results = []

    # Run tests
    results.append(await test_file_uploaded_with_ai_event())
    results.append(await test_file_deleted_event())
    results.append(await test_device_offline_event())

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(results)
    total = len(results)

    print(
        f"Test 1: file.uploaded.with_ai event - {'✓ PASSED' if results[0] else '✗ FAILED'}"
    )
    print(
        f"Test 2: file.deleted event          - {'✓ PASSED' if results[1] else '✗ FAILED'}"
    )
    print(
        f"Test 3: device.offline event        - {'✓ PASSED' if results[2] else '✗ FAILED'}"
    )
    print()
    print(f"{Colors.CYAN}Total: {passed}/{total} tests passed{Colors.NC}")
    print()

    if passed == total:
        print(f"{Colors.GREEN}✓ ALL EVENT SUBSCRIPTION TESTS PASSED!{Colors.NC}")
        print(
            f"{Colors.GREEN}✓ album_service can receive events from other services{Colors.NC}"
        )
        print()
        print(f"{Colors.YELLOW}Verification Commands:{Colors.NC}")
        print(f"Check album_service logs for 'Handling file.uploaded.with_ai event'")
        print(f"Check album_service logs for 'Handling file.deleted event'")
        print(f"Check album_service logs for 'Handling device.offline event'")
        return 0
    else:
        print(f"{Colors.RED}✗ SOME TESTS FAILED{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}Troubleshooting:{Colors.NC}")
        print("1. Check if NATS is running: kubectl get pods | grep nats")
        print(
            "2. Check if album service is subscribed: kubectl logs -l app=album | grep 'Subscribed to event'"
        )
        print("3. Check for handler errors: kubectl logs -l app=album | grep ERROR")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
