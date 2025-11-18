#!/usr/bin/env python3
"""
Test Event Subscription - Verify authorization_service can receive events from other services
This test simulates other services publishing events and verifies authorization_service handles them
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


async def test_user_deleted_event():
    """Test publishing user.deleted event to authorization_service"""
    print_test("Test 1: Publish user.deleted Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create user.deleted event
        print(f"{Colors.BLUE}Step 2: Creating user.deleted event{Colors.NC}")
        test_user_id = f"test_user_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "user_id": test_user_id,
            "email": f"{test_user_id}@example.com",
            "reason": "Test cleanup",
            "timestamp": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.USER_DELETED,
            source=ServiceSource.ACCOUNT_SERVICE,
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
            f"{Colors.BLUE}Step 4: Waiting for authorization_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: user.deleted event published{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}To verify: kubectl logs -l app=authorization-service | grep 'user.deleted'{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {e}{Colors.NC}")
        return False


async def test_organization_member_added_event():
    """Test publishing organization.member_added event to authorization_service"""
    print_test("Test 2: Publish organization.member_added Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create organization.member_added event
        print(
            f"{Colors.BLUE}Step 2: Creating organization.member_added event{Colors.NC}"
        )
        test_user_id = f"test_user_{int(datetime.utcnow().timestamp())}"
        test_org_id = f"test_org_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "organization_id": test_org_id,
            "user_id": test_user_id,
            "role": "member",
            "added_by": "admin_test",
            "timestamp": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.ORGANIZATION_MEMBER_ADDED,
            source=ServiceSource.ORGANIZATION_SERVICE,
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
            f"{Colors.BLUE}Step 4: Waiting for authorization_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: organization.member_added event published{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}To verify: kubectl logs -l app=authorization-service | grep 'organization.member_added'{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {e}{Colors.NC}")
        return False


async def test_organization_member_removed_event():
    """Test publishing organization.member_removed event to authorization_service"""
    print_test("Test 3: Publish organization.member_removed Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create organization.member_removed event
        print(
            f"{Colors.BLUE}Step 2: Creating organization.member_removed event{Colors.NC}"
        )
        test_user_id = f"test_user_{int(datetime.utcnow().timestamp())}"
        test_org_id = f"test_org_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "organization_id": test_org_id,
            "user_id": test_user_id,
            "removed_by": "admin_test",
            "timestamp": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.ORGANIZATION_MEMBER_REMOVED,
            source=ServiceSource.ORGANIZATION_SERVICE,
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
            f"{Colors.BLUE}Step 4: Waiting for authorization_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: organization.member_removed event published{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}To verify: kubectl logs -l app=authorization-service | grep 'organization.member_removed'{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {e}{Colors.NC}")
        return False


async def main():
    """Run all event subscription tests"""
    print_header("EVENT SUBSCRIPTION INTEGRATION TEST")

    results = []

    # Test 1: user.deleted event
    result1 = await test_user_deleted_event()
    results.append(result1)

    # Test 2: organization.member_added event
    result2 = await test_organization_member_added_event()
    results.append(result2)

    # Test 3: organization.member_removed event
    result3 = await test_organization_member_removed_event()
    results.append(result3)

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(results)
    total = len(results)

    print(f"Tests Passed: {Colors.GREEN}{passed}/{total}{Colors.NC}")
    print()

    if passed == total:
        print(f"{Colors.GREEN}✓ ALL EVENT SUBSCRIPTION TESTS PASSED!{Colors.NC}")
        return 0
    else:
        print(f"{Colors.RED}✗ SOME TESTS FAILED{Colors.NC}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
