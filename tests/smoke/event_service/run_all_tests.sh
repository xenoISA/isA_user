#!/bin/bash
# ============================================================================
# Event Service Smoke Tests - Run All
# ============================================================================
# Runs all smoke tests for the Event Service
# Target: localhost:8230
# Total Tests: 19 tests across 6 test files
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Configuration
# ============================================================================
export EVENT_SERVICE_URL="${EVENT_SERVICE_URL:-http://localhost:8230}"

# Test files to run
TEST_FILES=(
    "event_service_test_health.sh"
    "event_service_test_create.sh"
    "event_service_test_query.sh"
    "event_service_test_subscriptions.sh"
    "event_service_test_statistics.sh"
    "event_service_test_frontend.sh"
)

# ============================================================================
# Results Tracking
# ============================================================================
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_TESTS=0
FAILED_SUITES=()

# ============================================================================
# Main Execution
# ============================================================================

echo ""
echo -e "${CYAN}============================================================================${NC}"
echo -e "${CYAN}     EVENT SERVICE SMOKE TESTS - RUN ALL${NC}"
echo -e "${CYAN}============================================================================${NC}"
echo -e "${YELLOW}Target URL: ${EVENT_SERVICE_URL}${NC}"
echo -e "${YELLOW}Test Files: ${#TEST_FILES[@]}${NC}"
echo ""

# Check if service is available
echo -e "${YELLOW}Checking service availability...${NC}"
if curl -s --max-time 5 "${EVENT_SERVICE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}Service is available${NC}"
else
    echo -e "${RED}Service is not available at ${EVENT_SERVICE_URL}${NC}"
    echo -e "${YELLOW}Please ensure the event service is running${NC}"
    exit 1
fi
echo ""

# Run each test file
for test_file in "${TEST_FILES[@]}"; do
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}  Running: ${test_file}${NC}"
    echo -e "${CYAN}============================================================================${NC}"

    if [ -f "${SCRIPT_DIR}/${test_file}" ]; then
        if "${SCRIPT_DIR}/${test_file}"; then
            echo -e "${GREEN}Suite PASSED${NC}"
        else
            echo -e "${RED}Suite FAILED${NC}"
            FAILED_SUITES+=("$test_file")
        fi
    else
        echo -e "${RED}Test file not found: ${test_file}${NC}"
        FAILED_SUITES+=("$test_file (not found)")
    fi

    echo ""
done

# ============================================================================
# Final Summary
# ============================================================================

echo -e "${CYAN}============================================================================${NC}"
echo -e "${CYAN}     FINAL SUMMARY${NC}"
echo -e "${CYAN}============================================================================${NC}"
echo ""
echo -e "Test Suites Run: ${#TEST_FILES[@]}"
echo -e "Test Suites Passed: $((${#TEST_FILES[@]} - ${#FAILED_SUITES[@]}))"
echo -e "Test Suites Failed: ${#FAILED_SUITES[@]}"
echo ""

if [ ${#FAILED_SUITES[@]} -eq 0 ]; then
    echo -e "${GREEN}============================================================================${NC}"
    echo -e "${GREEN}     ALL TEST SUITES PASSED${NC}"
    echo -e "${GREEN}============================================================================${NC}"
    exit 0
else
    echo -e "${RED}Failed Suites:${NC}"
    for suite in "${FAILED_SUITES[@]}"; do
        echo -e "${RED}  - ${suite}${NC}"
    done
    echo ""
    echo -e "${RED}============================================================================${NC}"
    echo -e "${RED}     SOME TEST SUITES FAILED${NC}"
    echo -e "${RED}============================================================================${NC}"
    exit 1
fi
