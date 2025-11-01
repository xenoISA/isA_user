#!/bin/bash
# Storage Service - File Sharing Test Script
# Tests: Create Share, Get Shared File, Share with Password, Access Control

BASE_URL="http://localhost:8209"
API_BASE="${BASE_URL}/api/v1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test counters
PASSED=0
FAILED=0
TOTAL=0

# Test result function
test_result() {
    TOTAL=$((TOTAL + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}       STORAGE SERVICE - FILE SHARING TEST${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Auto-discover test user
echo -e "${CYAN}Fetching test user from database...${NC}"
TEST_USER=$(docker exec user-staging python3 -c "
import sys
sys.path.insert(0, '/app')
from core.database.supabase_client import get_supabase_client

try:
    client = get_supabase_client()
    result = client.table('users').select('user_id, email').eq('is_active', True).limit(1).execute()
    if result.data and len(result.data) > 0:
        user = result.data[0]
        print(f\"{user['user_id']}|{user.get('email', 'test@example.com')}\")
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
" 2>&1)

if echo "$TEST_USER" | grep -q "ERROR"; then
    TEST_USER_ID="test_user_001"
    TEST_USER_EMAIL="test@example.com"
else
    TEST_USER_ID=$(echo "$TEST_USER" | cut -d'|' -f1)
    TEST_USER_EMAIL=$(echo "$TEST_USER" | cut -d'|' -f2)
fi

echo -e "${GREEN}✓ Using test user: $TEST_USER_ID${NC}"
echo ""

# Create a test file to share
TEST_FILE="/tmp/sharing_test_$(date +%s).txt"
echo "This file is for testing sharing functionality" > "$TEST_FILE"

# Test 1: Upload File for Sharing
echo -e "${YELLOW}Test 1: Upload File for Sharing${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST "${API_BASE}/files/upload" \
  -F "file=@${TEST_FILE}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "access_level=private" \
  -F "enable_indexing=false")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool

if echo "$UPLOAD_RESPONSE" | grep -q '"file_id"'; then
    FILE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['file_id'])")
    echo -e "${GREEN}✓ File uploaded: $FILE_ID${NC}"
    test_result 0
else
    echo -e "${RED}✗ Upload failed${NC}"
    test_result 1
    FILE_ID=""
fi
echo ""

# Test 2: Create Public Share Link
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 2: Create Public Share Link${NC}"
    echo "POST /api/v1/files/${FILE_ID}/share"
    SHARE_RESPONSE=$(curl -s -X POST "${API_BASE}/files/${FILE_ID}/share" \
      -F "shared_by=${TEST_USER_ID}" \
      -F "view=true" \
      -F "download=true" \
      -F "delete=false" \
      -F "expires_hours=24")

    echo "$SHARE_RESPONSE" | python3 -m json.tool

    if echo "$SHARE_RESPONSE" | grep -q '"share_id"'; then
        SHARE_ID=$(echo "$SHARE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['share_id'])")
        SHARE_URL=$(echo "$SHARE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('share_url', ''))" 2>/dev/null)
        echo -e "${GREEN}✓ Share created: $SHARE_ID${NC}"
        if [ -n "$SHARE_URL" ]; then
            echo -e "  Share URL: ${CYAN}$SHARE_URL${NC}"
        fi
        test_result 0
    else
        test_result 1
        SHARE_ID=""
    fi
    echo ""
else
    echo -e "${YELLOW}Test 2: Create Public Share Link - SKIPPED${NC}"
    echo ""
fi

# Test 3: Access Shared File (Public)
if [ -n "$SHARE_ID" ]; then
    echo -e "${YELLOW}Test 3: Access Shared File (Public)${NC}"
    echo "GET /api/v1/shares/${SHARE_ID}"
    RESPONSE=$(curl -s "${API_BASE}/shares/${SHARE_ID}")
    echo "$RESPONSE" | python3 -m json.tool

    if echo "$RESPONSE" | grep -q '"file_id"'; then
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 3: Access Shared File - SKIPPED${NC}"
    echo ""
fi

# Test 4: Create Password-Protected Share
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 4: Create Password-Protected Share${NC}"
    SHARE_PASSWORD="test1234"
    SHARE_RESPONSE_PWD=$(curl -s -X POST "${API_BASE}/files/${FILE_ID}/share" \
      -F "shared_by=${TEST_USER_ID}" \
      -F "view=true" \
      -F "download=true" \
      -F "password=${SHARE_PASSWORD}" \
      -F "expires_hours=48")

    echo "$SHARE_RESPONSE_PWD" | python3 -m json.tool

    if echo "$SHARE_RESPONSE_PWD" | grep -q '"share_id"'; then
        SHARE_ID_PWD=$(echo "$SHARE_RESPONSE_PWD" | python3 -c "import sys, json; print(json.load(sys.stdin)['share_id'])")
        echo -e "${GREEN}✓ Password-protected share created: $SHARE_ID_PWD${NC}"
        test_result 0
    else
        test_result 1
        SHARE_ID_PWD=""
    fi
    echo ""
else
    echo -e "${YELLOW}Test 4: Create Password-Protected Share - SKIPPED${NC}"
    echo ""
fi

# Test 5: Access Protected Share Without Password (Should Fail)
if [ -n "$SHARE_ID_PWD" ]; then
    echo -e "${YELLOW}Test 5: Access Protected Share Without Password (Should Fail)${NC}"
    echo "GET /api/v1/shares/${SHARE_ID_PWD}"
    RESPONSE=$(curl -s "${API_BASE}/shares/${SHARE_ID_PWD}")
    echo "$RESPONSE" | python3 -m json.tool

    # Should fail or return error
    if echo "$RESPONSE" | grep -qi "password\|unauthorized\|forbidden"; then
        echo -e "${GREEN}✓ Access correctly denied without password${NC}"
        test_result 0
    else
        echo -e "${RED}✗ Should require password${NC}"
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 5: Access Without Password - SKIPPED${NC}"
    echo ""
fi

# Test 6: Access Protected Share With Correct Password
if [ -n "$SHARE_ID_PWD" ]; then
    echo -e "${YELLOW}Test 6: Access Protected Share With Correct Password${NC}"
    echo "GET /api/v1/shares/${SHARE_ID_PWD}?password=${SHARE_PASSWORD}"
    RESPONSE=$(curl -s "${API_BASE}/shares/${SHARE_ID_PWD}?password=${SHARE_PASSWORD}")
    echo "$RESPONSE" | python3 -m json.tool

    if echo "$RESPONSE" | grep -q '"file_id"'; then
        echo -e "${GREEN}✓ Access granted with correct password${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 6: Access With Password - SKIPPED${NC}"
    echo ""
fi

# Test 7: Create Share with Specific User
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 7: Create Share with Specific User${NC}"
    SHARED_WITH_EMAIL="recipient@example.com"
    SHARE_RESPONSE_USER=$(curl -s -X POST "${API_BASE}/files/${FILE_ID}/share" \
      -F "shared_by=${TEST_USER_ID}" \
      -F "shared_with_email=${SHARED_WITH_EMAIL}" \
      -F "view=true" \
      -F "download=false" \
      -F "expires_hours=72")

    echo "$SHARE_RESPONSE_USER" | python3 -m json.tool

    if echo "$SHARE_RESPONSE_USER" | grep -q '"share_id"'; then
        SHARE_ID_USER=$(echo "$SHARE_RESPONSE_USER" | python3 -c "import sys, json; print(json.load(sys.stdin)['share_id'])")
        echo -e "${GREEN}✓ User-specific share created: $SHARE_ID_USER${NC}"
        test_result 0
    else
        test_result 1
        SHARE_ID_USER=""
    fi
    echo ""
else
    echo -e "${YELLOW}Test 7: Create User-Specific Share - SKIPPED${NC}"
    echo ""
fi

# Test 8: Create Share with Max Downloads Limit
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 8: Create Share with Download Limit${NC}"
    SHARE_RESPONSE_LIMIT=$(curl -s -X POST "${API_BASE}/files/${FILE_ID}/share" \
      -F "shared_by=${TEST_USER_ID}" \
      -F "view=true" \
      -F "download=true" \
      -F "max_downloads=3" \
      -F "expires_hours=24")

    echo "$SHARE_RESPONSE_LIMIT" | python3 -m json.tool

    if echo "$SHARE_RESPONSE_LIMIT" | grep -q '"share_id"'; then
        SHARE_ID_LIMIT=$(echo "$SHARE_RESPONSE_LIMIT" | python3 -c "import sys, json; print(json.load(sys.stdin)['share_id'])")
        echo -e "${GREEN}✓ Share with download limit created: $SHARE_ID_LIMIT${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 8: Create Share with Download Limit - SKIPPED${NC}"
    echo ""
fi

# Cleanup
rm -f "$TEST_FILE"

# Print summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e "Total Tests: ${TOTAL}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL FILE SHARING TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
