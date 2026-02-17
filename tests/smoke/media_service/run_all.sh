#!/bin/bash
# Media Service Smoke Tests Runner
# Runs all smoke tests for media_service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Media Service Smoke Tests"
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

# API Tests
run_test "1_photo_versions.sh"
run_test "2_gallery_features.sh"
run_test "3_ai_metadata_caching.sh"

# Event Tests
run_test "media_service_test_event_publishing.sh"
run_test "media_service_test_event_subscriptions.sh"

echo ""
echo "========================================"
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "========================================"

[ $TESTS_FAILED -eq 0 ]
