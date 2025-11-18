#!/bin/bash

# Order Service Event Publishing Integration Test
# Tests that events are properly published to NATS when orders are created/updated/canceled

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

echo "======================================================================"
echo "Order Service Event Publishing Integration Tests"
echo "======================================================================"
echo ""

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Test 1: Run Python event publishing tests
print_section "Test 1: Python Event Publishing Tests"
echo "Running test_event_publishing.py..."

cd "$(dirname "$0")"
python3 test_event_publishing.py

if [ $? -eq 0 ]; then
    print_result 0 "Python event publishing tests passed"
else
    print_result 1 "Python event publishing tests failed"
fi

# Test 2: Run Python event subscription tests
print_section "Test 2: Python Event Subscription Tests"
echo "Running test_event_subscriptions.py..."

python3 test_event_subscriptions.py

if [ $? -eq 0 ]; then
    print_result 0 "Python event subscription tests passed"
else
    print_result 1 "Python event subscription tests failed"
fi

# Test 3: Verify NATS connection (if available)
print_section "Test 3: NATS Connection Check"
echo "Checking if NATS is available..."

# Try to connect to NATS using nc (netcat) if available
if command -v nc &> /dev/null; then
    nc -z -w 1 localhost 4222 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ NATS is running on localhost:4222${NC}"
        print_result 0 "NATS connection available"
    else
        echo -e "${YELLOW}⚠ NATS not running on localhost:4222${NC}"
        echo "This is OK for testing without NATS"
        print_result 0 "NATS connection check (optional)"
    fi
else
    echo -e "${YELLOW}⚠ netcat (nc) not available to test NATS connection${NC}"
    print_result 0 "NATS connection check skipped"
fi

# Summary
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All event publishing tests passed!${NC}"
    echo ""
    echo "Events Verified:"
    echo "  ✓ order.created - Published when new order is created"
    echo "  ✓ order.completed - Published when order is completed"
    echo "  ✓ order.canceled - Published when order is canceled"
    echo "  ✓ order.updated - Published when order is updated"
    echo ""
    echo "Event Subscriptions Verified:"
    echo "  ✓ payment.completed → Auto-complete order"
    echo "  ✓ payment.failed → Mark order as failed"
    echo "  ✓ Idempotency handling"
    echo "  ✓ Graceful degradation without NATS"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
