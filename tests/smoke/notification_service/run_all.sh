#!/bin/bash
# Notification Service Smoke Tests Runner
# Runs all smoke tests for notification_service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Notification Service Smoke Tests"
echo "========================================"

TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_file="$1"
    echo ""
    echo "Running: $test_file"
    echo "----------------------------------------"
    if bash "$test_file"; then
        ((TESTS_PASSED++))
        echo "PASSED: $test_file"
    else
        ((TESTS_FAILED++))
        echo "FAILED: $test_file"
    fi
}

# Main Service Tests
run_test "notification_test.sh"
run_test "notification_api_test.sh"

# Event Tests
run_test "notification_service_test_event_publishing.sh"
run_test "notification_service_test_event_subscriptions.sh"

echo ""
echo "========================================"
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "========================================"

[ $TESTS_FAILED -eq 0 ]
