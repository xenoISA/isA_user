#!/bin/bash

# Master Test Runner for Memory Service
# Runs all memory type tests and reports overall results

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Test result counters
TOTAL_TESTS=0
TOTAL_PASSED=0
TOTAL_FAILED=0

# Test files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILES=(
    "test_factual_memory.sh"
    "test_episodic_memory.sh"
    "test_procedural_memory.sh"
    "test_semantic_memory.sh"
    "test_working_memory.sh"
    "test_session_memory.sh"
)

# Test statuses
declare -A TEST_RESULTS

echo ""
echo "======================================================================"
echo -e "${CYAN}Memory Service - Master Test Runner${NC}"
echo "======================================================================"
echo ""
echo -e "${YELLOW}Running all memory service tests...${NC}"
echo ""

# Function to print test suite header
print_suite_header() {
    echo ""
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║  Running: $1${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Run each test file
for test_file in "${TEST_FILES[@]}"; do
    test_path="${SCRIPT_DIR}/${test_file}"

    if [ ! -f "$test_path" ]; then
        echo -e "${RED}✗ Test file not found: ${test_file}${NC}"
        TEST_RESULTS["$test_file"]="NOT_FOUND"
        continue
    fi

    # Make executable if not already
    chmod +x "$test_path"

    # Print header
    print_suite_header "$test_file"

    # Run the test
    "$test_path"
    exit_code=$?

    # Store result
    if [ $exit_code -eq 0 ]; then
        TEST_RESULTS["$test_file"]="PASSED"
        ((TOTAL_PASSED++))
    else
        TEST_RESULTS["$test_file"]="FAILED"
        ((TOTAL_FAILED++))
    fi

    ((TOTAL_TESTS++))
done

# Print summary
echo ""
echo ""
echo "======================================================================"
echo -e "${CYAN}Final Test Summary${NC}"
echo "======================================================================"
echo ""

echo -e "${BLUE}Individual Test Results:${NC}"
echo "----------------------------------------------------------------------"
for test_file in "${TEST_FILES[@]}"; do
    result="${TEST_RESULTS[$test_file]}"
    case "$result" in
        "PASSED")
            echo -e "  ${GREEN}✓ PASSED${NC} - $test_file"
            ;;
        "FAILED")
            echo -e "  ${RED}✗ FAILED${NC} - $test_file"
            ;;
        "NOT_FOUND")
            echo -e "  ${YELLOW}? NOT FOUND${NC} - $test_file"
            ;;
    esac
done

echo ""
echo "----------------------------------------------------------------------"
echo -e "${GREEN}Test Suites Passed: $TOTAL_PASSED${NC}"
echo -e "${RED}Test Suites Failed: $TOTAL_FAILED${NC}"
echo "Total Test Suites: $TOTAL_TESTS"
echo ""

# Calculate percentage
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_PERCENTAGE=$((TOTAL_PASSED * 100 / TOTAL_TESTS))
    echo "Success Rate: ${PASS_PERCENTAGE}%"
    echo ""
fi

# Final message
if [ $TOTAL_FAILED -eq 0 ]; then
    echo "======================================================================"
    echo -e "${GREEN}🎉 All memory service tests passed! 🎉${NC}"
    echo "======================================================================"
    echo ""
    exit 0
else
    echo "======================================================================"
    echo -e "${RED}❌ Some test suites failed. Please review the output above. ❌${NC}"
    echo "======================================================================"
    echo ""
    exit 1
fi
