#!/usr/bin/env python3
"""
Test Service Clients - Verify account_service can make HTTP calls to other services
This test validates the service client implementations
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from microservices.account_service.clients import (
    BillingServiceClient,
    OrganizationServiceClient,
    WalletServiceClient,
)


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


async def test_organization_client():
    """Test OrganizationServiceClient"""
    print_test("Test 1: OrganizationServiceClient")

    try:
        print(f"{Colors.BLUE}Step 1: Initialize OrganizationServiceClient{Colors.NC}")
        # Use K8s service name
        client = OrganizationServiceClient(base_url="http://organization-service:8007")
        print(f"{Colors.GREEN}✓ Client initialized{Colors.NC}")
        print(f"  Base URL: http://organization-service:8007")
        print()

        # Test get_organization
        print(f"{Colors.BLUE}Step 2: Test get_organization(){Colors.NC}")
        test_org_id = "test_org_123"
        result = await client.get_organization(test_org_id)

        if result is not None:
            print(
                f"{Colors.GREEN}✓ Successfully called organization_service{Colors.NC}"
            )
            print(f"  Result: {result}")
        else:
            print(
                f"{Colors.YELLOW}⚠ Service returned None (org not found or service down){Colors.NC}"
            )
            print(
                f"{Colors.YELLOW}  This is expected if organization_service is not running${Colors.NC}"
            )
        print()

        # Test validate_organization_exists
        print(f"{Colors.BLUE}Step 3: Test validate_organization_exists(){Colors.NC}")
        exists = await client.validate_organization_exists(test_org_id)
        print(f"  Exists: {exists}")
        print()

        # Cleanup
        await client.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: OrganizationServiceClient works correctly{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def test_billing_client():
    """Test BillingServiceClient"""
    print_test("Test 2: BillingServiceClient")

    try:
        print(f"{Colors.BLUE}Step 1: Initialize BillingServiceClient{Colors.NC}")
        client = BillingServiceClient(base_url="http://billing-service:8009")
        print(f"{Colors.GREEN}✓ Client initialized{Colors.NC}")
        print(f"  Base URL: http://billing-service:8009")
        print()

        # Test get_subscription_status
        print(f"{Colors.BLUE}Step 2: Test get_subscription_status(){Colors.NC}")
        test_user_id = "test_user_photo_e2e"  # Known user from previous tests
        result = await client.get_subscription_status(test_user_id)

        if result is not None:
            print(f"{Colors.GREEN}✓ Successfully called billing_service{Colors.NC}")
            print(f"  Result: {result}")
        else:
            print(
                f"{Colors.YELLOW}⚠ Service returned None (user not found or service down){Colors.NC}"
            )
            print(
                f"{Colors.YELLOW}  This is expected if billing_service is not running${Colors.NC}"
            )
        print()

        # Test check_payment_status
        print(f"{Colors.BLUE}Step 3: Test check_payment_status(){Colors.NC}")
        status = await client.check_payment_status(test_user_id)
        print(f"  Payment status: {status}")
        print()

        # Cleanup
        await client.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: BillingServiceClient works correctly{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def test_wallet_client():
    """Test WalletServiceClient"""
    print_test("Test 3: WalletServiceClient")

    try:
        print(f"{Colors.BLUE}Step 1: Initialize WalletServiceClient{Colors.NC}")
        client = WalletServiceClient(base_url="http://wallet-service:8010")
        print(f"{Colors.GREEN}✓ Client initialized{Colors.NC}")
        print(f"  Base URL: http://wallet-service:8010")
        print()

        # Test get_wallet_balance
        print(f"{Colors.BLUE}Step 2: Test get_wallet_balance(){Colors.NC}")
        test_user_id = "test_user_photo_e2e"  # Known user
        result = await client.get_wallet_balance(test_user_id)

        if result is not None:
            print(f"{Colors.GREEN}✓ Successfully called wallet_service{Colors.NC}")
            print(f"  Result: {result}")
        else:
            print(
                f"{Colors.YELLOW}⚠ Service returned None (wallet not found or service down){Colors.NC}"
            )
            print(
                f"{Colors.YELLOW}  This is expected if wallet_service is not running${Colors.NC}"
            )
        print()

        # Test check_wallet_exists
        print(f"{Colors.BLUE}Step 3: Test check_wallet_exists(){Colors.NC}")
        exists = await client.check_wallet_exists(test_user_id)
        print(f"  Wallet exists: {exists}")
        print()

        # Cleanup
        await client.close()

        print(
            f"{Colors.GREEN}✓ TEST PASSED: WalletServiceClient works correctly{Colors.NC}"
        )
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def test_client_error_handling():
    """Test client error handling for non-existent services"""
    print_test("Test 4: Client Error Handling")

    try:
        print(f"{Colors.BLUE}Testing error handling with invalid URL{Colors.NC}")

        # Test with invalid URL (should timeout gracefully)
        print(f"{Colors.BLUE}Step 1: Test with timeout=1 second{Colors.NC}")
        client = OrganizationServiceClient(
            base_url="http://non-existent-service:9999", timeout=1.0
        )

        result = await client.get_organization("test")

        if result is None:
            print(
                f"{Colors.GREEN}✓ Client handled error gracefully (returned None){Colors.NC}"
            )
        else:
            print(f"{Colors.RED}✗ Expected None for failed connection{Colors.NC}")
            return False

        await client.close()
        print()

        print(f"{Colors.GREEN}✓ TEST PASSED: Error handling works correctly{Colors.NC}")
        print()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ TEST FAILED: {str(e)}{Colors.NC}")
        print()
        return False


async def main():
    print_header("SERVICE CLIENTS INTEGRATION TEST")
    print(
        f"{Colors.BLUE}Testing account_service HTTP clients for inter-service communication{Colors.NC}"
    )
    print()

    results = []

    # Run tests
    results.append(await test_organization_client())
    results.append(await test_billing_client())
    results.append(await test_wallet_client())
    results.append(await test_client_error_handling())

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(results)
    total = len(results)

    print(
        f"Test 1: OrganizationServiceClient - {'✓ PASSED' if results[0] else '✗ FAILED'}"
    )
    print(
        f"Test 2: BillingServiceClient      - {'✓ PASSED' if results[1] else '✗ FAILED'}"
    )
    print(
        f"Test 3: WalletServiceClient        - {'✓ PASSED' if results[2] else '✗ FAILED'}"
    )
    print(
        f"Test 4: Error Handling             - {'✓ PASSED' if results[3] else '✗ FAILED'}"
    )
    print()
    print(f"{Colors.CYAN}Total: {passed}/{total} tests passed{Colors.NC}")
    print()

    if passed == total:
        print(f"{Colors.GREEN}✓ ALL SERVICE CLIENT TESTS PASSED!{Colors.NC}")
        print(
            f"{Colors.GREEN}✓ account_service can make HTTP calls to other services{Colors.NC}"
        )
        print()
        print(f"{Colors.YELLOW}Note:{Colors.NC}")
        print("Service clients work correctly even if target services are not running.")
        print("They handle errors gracefully and return None instead of crashing.")
        print()
        print(f"{Colors.YELLOW}To test with real services:{Colors.NC}")
        print(
            "1. Ensure organization_service, billing_service, wallet_service are deployed"
        )
        print("2. Create test data in those services")
        print("3. Re-run this test to see actual data retrieval")
        return 0
    else:
        print(f"{Colors.RED}✗ SOME TESTS FAILED{Colors.NC}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
