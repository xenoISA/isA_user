#!/bin/bash
# Media Service - Run All Tests
# Executes all test scripts for media service

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   MEDIA SERVICE - RUN ALL TESTS${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if media service is running
echo -e "${YELLOW}Checking if Media Service is running...${NC}"
if ! curl -s http://localhost/health > /dev/null 2>&1; then
    echo -e "${RED}✗ Media Service is not running${NC}"
    echo -e "${YELLOW}Please start the service first:${NC}"
    echo -e "  cd microservices/media_service"
    echo -e "  python main.py"
    exit 1
fi
echo -e "${GREEN}✓ Media Service is running${NC}"
echo ""

# Test counters
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_TESTS=0

# Run each test script
run_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .sh)

    echo -e "${CYAN}======================================${NC}"
    echo -e "${CYAN}Running: ${test_name}${NC}"
    echo -e "${CYAN}======================================${NC}"

    if [ -f "$test_file" ] && [ -x "$test_file" ]; then
        "$test_file"
        local exit_code=$?

        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}✓ ${test_name} completed successfully${NC}"
            TOTAL_PASSED=$((TOTAL_PASSED + 1))
        else
            echo -e "${RED}✗ ${test_name} failed${NC}"
            TOTAL_FAILED=$((TOTAL_FAILED + 1))
        fi

        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    else
        echo -e "${RED}✗ Test file not found or not executable: ${test_file}${NC}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    fi

    echo ""
}

# Run tests in order
run_test "${SCRIPT_DIR}/1_photo_versions.sh"
run_test "${SCRIPT_DIR}/2_gallery_features.sh"

# Summary
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   MEDIA SERVICE TEST SUMMARY${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "Total Tests: ${TOTAL_TESTS}"
echo -e "${GREEN}Passed: ${TOTAL_PASSED}${NC}"
echo -e "${RED}Failed: ${TOTAL_FAILED}${NC}"
echo -e "${CYAN}========================================${NC}"

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
