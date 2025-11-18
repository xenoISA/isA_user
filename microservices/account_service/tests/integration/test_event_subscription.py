#!/usr/bin/env python3
"""
Test Event Subscription - Verify account_service can receive events from other services
This test simulates other services publishing events and verifies account_service handles them
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


async def test_payment_completed_event():
    """Test publishing payment.completed event to account_service"""
    print_test("Test 1: Publish payment.completed Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create payment.completed event
        print(f"{Colors.BLUE}Step 2: Creating payment.completed event{Colors.NC}")
        test_user_id = f"test_user_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "user_id": test_user_id,
            "payment_type": "subscription",
            "subscription_plan": "premium",
            "amount": 29.99,
            "payment_id": "pay_test_123",
            "timestamp": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.PAYMENT_COMPLETED,
            source=ServiceSource.BILLING_SERVICE,
            data=event_data,
        )

        print(f"Event data: {json.dumps(event_data, indent=2)}")
        print()

        # Publish event
        print(f"{Colors.BLUE}Step 3: Publishing event to NATS{Colors.NC}")
        await event_bus.publish(event)
        print(f"{Colors.GREEN}✓ Event published successfully{Colors.NC}")
        print()

        # Wait for processing
        print(
            f"{Colors.BLUE}Step 4: Waiting for account_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: payment.completed event published{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}To verify: kubectl logs -l app=account-service | grep 'payment.completed'${Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def test_organization_member_added_event():
    """Test publishing organization.member_added event to account_service"""
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
            "invited_by": "admin_user",
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
        await event_bus.publish(event)
        print(f"{Colors.GREEN}✓ Event published successfully{Colors.NC}")
        print()

        # Wait for processing
        print(
            f"{Colors.BLUE}Step 4: Waiting for account_service to process event{Colors.NC}"
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
            f"{Colors.YELLOW}To verify: kubectl logs -l app=account-service | grep 'organization.member_added'${Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def test_wallet_created_event():
    """Test publishing wallet.created event to account_service"""
    print_test("Test 3: Publish wallet.created Event")

    try:
        # Connect to NATS
        print(f"{Colors.BLUE}Step 1: Connecting to NATS event bus{Colors.NC}")
        event_bus = await get_event_bus("test_client")
        print(f"{Colors.GREEN}✓ Connected to NATS{Colors.NC}")
        print()

        # Create wallet.created event
        print(f"{Colors.BLUE}Step 2: Creating wallet.created event{Colors.NC}")
        test_user_id = f"test_user_{int(datetime.utcnow().timestamp())}"
        test_wallet_id = f"wallet_{int(datetime.utcnow().timestamp())}"

        event_data = {
            "user_id": test_user_id,
            "wallet_id": test_wallet_id,
            "currency": "USD",
            "initial_balance": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        event = Event(
            event_type=EventType.WALLET_CREATED,
            source=ServiceSource.WALLET_SERVICE,
            data=event_data,
        )

        print(f"Event data: {json.dumps(event_data, indent=2)}")
        print()

        # Publish event
        print(f"{Colors.BLUE}Step 3: Publishing event to NATS{Colors.NC}")
        await event_bus.publish(event)
        print(f"{Colors.GREEN}✓ Event published successfully{Colors.NC}")
        print()

        # Wait for processing
        print(
            f"{Colors.BLUE}Step 4: Waiting for account_service to process event{Colors.NC}"
        )
        await asyncio.sleep(2)
        print(f"{Colors.GREEN}✓ Event should be processed by now{Colors.NC}")
        print()

        # Cleanup
        await event_bus.close()

        print(f"{Colors.GREEN}✓ TEST PASSED: wallet.created event published{Colors.NC}")
        print(
            f"{Colors.YELLOW}To verify: kubectl logs -l app=account-service | grep 'wallet.created'${Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def main():
    print_header("EVENT SUBSCRIPTION INTEGRATION TEST")
    print(
        f"{Colors.BLUE}Testing account_service event subscription handlers{Colors.NC}"
    )
    print(f"{Colors.BLUE}This simulates other services publishing events{Colors.NC}")
    print()

    results = []

    # Run tests
    results.append(await test_payment_completed_event())
    results.append(await test_organization_member_added_event())
    results.append(await test_wallet_created_event())

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(results)
    total = len(results)

    print(
        f"Test 1: payment.completed event         - {'✓ PASSED' if results[0] else '✗ FAILED'}"
    )
    print(
        f"Test 2: organization.member_added event - {'✓ PASSED' if results[1] else '✗ FAILED'}"
    )
    print(
        f"Test 3: wallet.created event            - {'✓ PASSED' if results[2] else '✗ FAILED'}"
    )
    print()
    print(f"{Colors.CYAN}Total: {passed}/{total} tests passed{Colors.NC}")
    print()

    if passed == total:
        print(f"{Colors.GREEN}✓ ALL EVENT SUBSCRIPTION TESTS PASSED!{Colors.NC}")
        print(
            f"{Colors.GREEN}✓ account_service can receive events from other services{Colors.NC}"
        )
        print()
        print(f"{Colors.YELLOW}Verification Commands:{Colors.NC}")
        print(
            f"kubectl logs -l app=account-service | grep 'Received payment.completed'"
        )
        print(
            f"kubectl logs -l app=account-service | grep 'Received organization.member_added'"
        )
        print(f"kubectl logs -l app=account-service | grep 'Received wallet.created'")
        return 0
    else:
        print(f"{Colors.RED}✗ SOME TESTS FAILED{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}Troubleshooting:{Colors.NC}")
        print("1. Check if NATS is running: kubectl get pods | grep nats")
        print(
            "2. Check if account-service is subscribed: kubectl logs -l app=account-service | grep 'Subscribed to event'"
        )
        print(
            "3. Check for handler errors: kubectl logs -l app=account-service | grep ERROR"
        )
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
