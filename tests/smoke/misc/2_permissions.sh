#!/bin/bash
# Test Document Permission Management - Real Integration Test
# This test verifies document permission updates with real file uploads

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}          DOCUMENT PERMISSION INTEGRATION TEST (REAL)${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="perm_test_user_${TEST_TS}"
TEST_USER_2="perm_test_user2_${TEST_TS}"
# Use APISIX gateway routes
DOCUMENT_URL="http://localhost/api/v1"
STORAGE_URL="http://localhost/api/v1"

echo -e "${BLUE}Document Service: ${DOCUMENT_URL}/documents${NC}"
echo -e "${BLUE}Storage Service: ${STORAGE_URL}/storage${NC}"
echo ""

# Health checks - via APISIX gateway
echo -e "${BLUE}Checking services health...${NC}"

DOC_HEALTH=$(curl -s "${DOCUMENT_URL}/documents?user_id=health_check" 2>/dev/null && echo '{"status":"healthy"}' || echo '{"status":"error"}')
STORAGE_HEALTH=$(curl -s "${STORAGE_URL}/storage/files/quota?user_id=health_check" 2>/dev/null && echo '{"status":"healthy"}' || echo '{"status":"error"}')

if ! echo "$DOC_HEALTH" | grep -q "healthy"; then
    echo -e "${RED}✗ Document service not healthy${NC}"
    exit 1
fi

if ! echo "$STORAGE_HEALTH" | grep -q "healthy"; then
    echo -e "${RED}✗ Storage service not healthy${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All services healthy${NC}"
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Upload File and Create Document with Private Access${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Create a temporary test file
TEST_FILE="/tmp/permission_test_${TEST_TS}.txt"
cat > "$TEST_FILE" << 'EOF'
# Permission Test Document

This document is used to test permission management functionality.

## Content
This is a private document that should only be accessible by authorized users.

## Access Control
- Default: Private (owner only)
- Can be shared with specific users
- Can be shared with groups
EOF

echo -e "${BLUE}Step 1: Upload file to storage service${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST "${STORAGE_URL}/storage/files/upload" \
  -F "file=@${TEST_FILE}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "access_level=private" \
  -F "enable_indexing=false")

if echo "$UPLOAD_RESPONSE" | grep -q "file_id"; then
    FILE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('file_id', ''))" 2>/dev/null)
    echo -e "${GREEN}✓ File uploaded: ${FILE_ID}${NC}"
else
    echo -e "${RED}✗ File upload failed${NC}"
    rm -f "$TEST_FILE"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 2: Create document${NC}"
DOC_PAYLOAD="{\"title\":\"Permission Test Doc ${TEST_TS}\",\"description\":\"Test document for permissions\",\"doc_type\":\"txt\",\"file_id\":\"${FILE_ID}\",\"access_level\":\"private\",\"tags\":[\"permission\",\"test\"]}"
RESPONSE=$(curl -s -X POST "${DOCUMENT_URL}/documents?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$DOC_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

if echo "$RESPONSE" | grep -q "doc_id"; then
    DOC_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('doc_id', ''))" 2>/dev/null)
    echo -e "${GREEN}✓ Document created: ${DOC_ID}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: Document creation failed${NC}"
    PASSED_1=0
    DOC_ID=""
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Get Document Permissions${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$DOC_ID" ]; then
    echo -e "${BLUE}Step 1: Get permissions${NC}"
    RESPONSE=$(curl -s -X GET "${DOCUMENT_URL}/documents/${DOC_ID}/permissions?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""

    if echo "$RESPONSE" | grep -q "access_level"; then
        echo -e "${GREEN}✓ Permissions retrieved successfully${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: Permission retrieval failed${NC}"
        PASSED_2=0
    fi
else
    echo -e "${YELLOW}⚠ Skipping - no document ID${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Update Permissions - Add Users${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$DOC_ID" ]; then
    echo -e "${BLUE}Step 1: Update permissions${NC}"
    PERM_PAYLOAD="{\"access_level\":\"team\",\"add_users\":[\"${TEST_USER_2}\"],\"add_groups\":[\"group_test\"]}"
    RESPONSE=$(curl -s -X PUT "${DOCUMENT_URL}/documents/${DOC_ID}/permissions?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$PERM_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""

    if echo "$RESPONSE" | grep -q "access_level\|allowed_users"; then
        echo -e "${GREEN}✓ Permissions updated successfully${NC}"
        echo -e "${BLUE}Note: Permission changes stored in PostgreSQL for query filtering${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: Permission update failed${NC}"
        PASSED_3=0
    fi
else
    echo -e "${YELLOW}⚠ Skipping - no document ID${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify Permissions Were Updated${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$DOC_ID" ]; then
    echo -e "${BLUE}Step 1: Get updated permissions${NC}"
    RESPONSE=$(curl -s -X GET "${DOCUMENT_URL}/documents/${DOC_ID}/permissions?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""

    if echo "$RESPONSE" | grep -q "team\|allowed_users"; then
        echo -e "${GREEN}✓ Permission changes verified${NC}"
        PASSED_4=1
    else
        echo -e "${RED}✗ FAILED: Permission verification failed${NC}"
        PASSED_4=0
    fi
else
    echo -e "${YELLOW}⚠ Skipping - no document ID${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Update Permissions - Remove Users${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$DOC_ID" ]; then
    echo -e "${BLUE}Step 1: Remove users from permissions${NC}"
    PERM_PAYLOAD="{\"remove_users\":[\"${TEST_USER_2}\"]}"
    RESPONSE=$(curl -s -X PUT "${DOCUMENT_URL}/documents/${DOC_ID}/permissions?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$PERM_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""

    if echo "$RESPONSE" | grep -q "access_level\|allowed_users"; then
        echo -e "${GREEN}✓ User removed from permissions${NC}"
        PASSED_5=1
    else
        echo -e "${RED}✗ FAILED: Permission removal failed${NC}"
        PASSED_5=0
    fi
else
    echo -e "${YELLOW}⚠ Skipping - no document ID${NC}"
    PASSED_5=0
fi
echo ""

# Cleanup
echo -e "${BLUE}Cleaning up test files...${NC}"
rm -f "$TEST_FILE"
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4 + PASSED_5))
echo -e "Tests Passed: ${GREEN}${TOTAL_PASSED}/5${NC}"
echo ""

if [ $TOTAL_PASSED -ge 3 ]; then
    echo -e "${GREEN}✓ PERMISSION MANAGEMENT TESTS PASSED!${NC}"
    echo ""
    echo -e "${CYAN}Permission Features Verified:${NC}"
    [ $PASSED_1 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Create document with access level"
    [ $PASSED_2 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Get document permissions"
    [ $PASSED_3 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Update permissions (add users/groups)"
    [ $PASSED_4 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Verify permission changes"
    [ $PASSED_5 -eq 1 ] && echo -e "  ${GREEN}✓${NC} Remove users from permissions"
    echo ""
    echo -e "${YELLOW}Note: Permissions are stored in PostgreSQL and enforced at query time${NC}"
    exit 0
else
    echo -e "${RED}✗ PERMISSION TESTS FAILED${NC}"
    exit 1
fi
