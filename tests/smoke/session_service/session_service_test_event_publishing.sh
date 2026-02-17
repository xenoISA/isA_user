#!/bin/bash

# Session Service Event Publishing Test Script
# Tests that session service correctly publishes events to NATS

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../../.." && pwd )"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "Session Service Event Publishing Tests"
echo "======================================================================"
echo ""
echo "Project Root: ${PROJECT_ROOT}"
echo "Script Directory: ${SCRIPT_DIR}"
echo ""

# Check if Python test file exists
if [ ! -f "${SCRIPT_DIR}/test_event_publishing.py" ]; then
    echo -e "${RED}Error: test_event_publishing.py not found${NC}"
    exit 1
fi

# Run Python test
echo -e "${BLUE}Running Python event publishing tests...${NC}"
echo ""

cd "${PROJECT_ROOT}"
python3 "${SCRIPT_DIR}/test_event_publishing.py"
TEST_RESULT=$?

echo ""
echo "======================================================================"
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}Event Publishing Tests PASSED${NC}"
else
    echo -e "${RED}Event Publishing Tests FAILED${NC}"
fi
echo "======================================================================"

exit $TEST_RESULT
