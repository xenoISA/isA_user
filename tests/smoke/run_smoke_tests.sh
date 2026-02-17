#!/bin/bash
# Smoke Test Runner
# Quick validation of API endpoints using bash scripts
#
# Usage:
#   ./run_smoke_tests.sh              # Run all smoke tests
#   ./run_smoke_tests.sh api          # Run only API tests
#   ./run_smoke_tests.sh events       # Run only event tests
#   ./run_smoke_tests.sh account      # Run tests matching "account"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=====================================================================${NC}"
echo -e "${CYAN}                    SMOKE TEST RUNNER${NC}"
echo -e "${CYAN}=====================================================================${NC}"
echo ""

FILTER="${1:-all}"
PASSED=0
FAILED=0
SKIPPED=0

run_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .sh)

    echo -e "${YELLOW}Running: ${test_name}${NC}"

    if bash "$test_file" > /tmp/smoke_test_output.txt 2>&1; then
        echo -e "${GREEN}  ✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}  ✗ FAILED${NC}"
        tail -5 /tmp/smoke_test_output.txt
        ((FAILED++))
    fi
}

# Run API tests
if [ "$FILTER" = "all" ] || [ "$FILTER" = "api" ] || [ -z "$(echo "$FILTER" | grep -E '^(api|events|all)$')" ]; then
    echo -e "\n${CYAN}=== API Tests ===${NC}\n"

    for test_file in api/*.sh; do
        if [ -f "$test_file" ]; then
            if [ "$FILTER" = "all" ] || [ "$FILTER" = "api" ] || echo "$test_file" | grep -qi "$FILTER"; then
                run_test "$test_file"
            fi
        fi
    done
fi

# Run Event tests
if [ "$FILTER" = "all" ] || [ "$FILTER" = "events" ] || [ -z "$(echo "$FILTER" | grep -E '^(api|events|all)$')" ]; then
    echo -e "\n${CYAN}=== Event Tests ===${NC}\n"

    for test_file in events/*.sh; do
        if [ -f "$test_file" ]; then
            if [ "$FILTER" = "all" ] || [ "$FILTER" = "events" ] || echo "$test_file" | grep -qi "$FILTER"; then
                run_test "$test_file"
            fi
        fi
    done
fi

# Summary
echo ""
echo -e "${CYAN}=====================================================================${NC}"
echo -e "${CYAN}                         SUMMARY${NC}"
echo -e "${CYAN}=====================================================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
TOTAL=$((PASSED + FAILED))
echo "Total: $TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL SMOKE TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME SMOKE TESTS FAILED${NC}"
    exit 1
fi
