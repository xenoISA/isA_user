#!/bin/bash
# Storage Service - Run All Tests
# Executes all test scripts in sequence and reports overall results

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}${BOLD}=====================================================================${NC}"
echo -e "${CYAN}${BOLD}          STORAGE SERVICE - COMPREHENSIVE TEST SUITE${NC}"
echo -e "${CYAN}${BOLD}=====================================================================${NC}"
echo ""
echo -e "${CYAN}Test Suite Location: ${SCRIPT_DIR}${NC}"
echo -e "${CYAN}Start Time: $(date)${NC}"
echo ""

# Test suite tracking
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

# Array to store test results
declare -a TEST_RESULTS

# Function to run a test script
run_test() {
    local test_script=$1
    local test_name=$2

    TOTAL_SUITES=$((TOTAL_SUITES + 1))

    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}Running: ${test_name}${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ ! -f "$test_script" ]; then
        echo -e "${RED}✗ Test script not found: $test_script${NC}"
        TEST_RESULTS+=("${RED}✗ $test_name - SCRIPT NOT FOUND${NC}")
        FAILED_SUITES=$((FAILED_SUITES + 1))
        echo ""
        return 1
    fi

    if [ ! -x "$test_script" ]; then
        echo -e "${YELLOW}⚠ Making script executable: $test_script${NC}"
        chmod +x "$test_script"
    fi

    # Run the test script
    if bash "$test_script"; then
        echo ""
        echo -e "${GREEN}${BOLD}✓ $test_name PASSED${NC}"
        TEST_RESULTS+=("${GREEN}✓ $test_name - PASSED${NC}")
        PASSED_SUITES=$((PASSED_SUITES + 1))
        echo ""
        return 0
    else
        echo ""
        echo -e "${RED}${BOLD}✗ $test_name FAILED${NC}"
        TEST_RESULTS+=("${RED}✗ $test_name - FAILED${NC}")
        FAILED_SUITES=$((FAILED_SUITES + 1))
        echo ""
        return 1
    fi
}

# Run all test scripts
# NOTE: Photo versions, album management, and gallery features tests have been moved to
#       media_service and album_service respectively
run_test "${SCRIPT_DIR}/1_file_operations.sh" "File Operations"
run_test "${SCRIPT_DIR}/2_file_sharing.sh" "File Sharing"
run_test "${SCRIPT_DIR}/3_storage_quota.sh" "Storage Quota & Stats"
run_test "${SCRIPT_DIR}/6_intelligence.sh" "Intelligence Features"

# Print final summary
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}${BOLD}                     FINAL TEST SUMMARY${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BOLD}Test Results by Suite:${NC}"
for result in "${TEST_RESULTS[@]}"; do
    echo -e "  $result"
done
echo ""
echo -e "${BOLD}Overall Statistics:${NC}"
echo -e "  Total Test Suites: ${TOTAL_SUITES}"
echo -e "  ${GREEN}Passed: ${PASSED_SUITES}${NC}"
echo -e "  ${RED}Failed: ${FAILED_SUITES}${NC}"
echo -e "  Success Rate: $(awk "BEGIN {printf \"%.1f\", (${PASSED_SUITES}/${TOTAL_SUITES}*100)}")%"
echo ""
echo -e "${CYAN}End Time: $(date)${NC}"
echo ""

if [ $FAILED_SUITES -eq 0 ]; then
    echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║                                                                ║${NC}"
    echo -e "${GREEN}${BOLD}║     ✓✓✓ ALL TEST SUITES PASSED SUCCESSFULLY! ✓✓✓             ║${NC}"
    echo -e "${GREEN}${BOLD}║                                                                ║${NC}"
    echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}${BOLD}║                                                                ║${NC}"
    echo -e "${RED}${BOLD}║     ✗✗✗ SOME TEST SUITES FAILED ✗✗✗                           ║${NC}"
    echo -e "${RED}${BOLD}║                                                                ║${NC}"
    echo -e "${RED}${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Please review the failed tests above and fix any issues.${NC}"
    echo ""
    exit 1
fi
