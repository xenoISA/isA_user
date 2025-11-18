#!/bin/bash

# Telemetry Service Event Publishing Integration Test
# Tests that the service correctly publishes events via NATS

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Helper functions
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

increment_test() {
    ((TOTAL_TESTS++))
}

pass_test() {
    ((TESTS_PASSED++))
    echo -e "${GREEN}✓ PASSED${NC}: $1"
}

fail_test() {
    ((TESTS_FAILED++))
    echo -e "${RED}✗ FAILED${NC}: $1"
}

# Start tests
echo "======================================================================"
echo "Telemetry Service Event Publishing Test Suite"
echo "======================================================================"
echo ""

print_section "Running Python Event Publishing Tests"
increment_test

# Run the Python test file
cd "$(dirname "$0")"
python3 test_event_publishing.py

PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -eq 0 ]; then
    pass_test "Event publishing tests completed successfully"
else
    fail_test "Event publishing tests failed"
fi

# Summary
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total: $TOTAL_TESTS"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
