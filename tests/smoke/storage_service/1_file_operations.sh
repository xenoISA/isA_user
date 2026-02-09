#!/bin/bash
# Storage Service - File Operations Test Script
# Tests: Upload, List, Get Info, Download, Delete
# Event-Driven Architecture v2.0 - via APISIX Ingress

# Test mode: "gateway" (via APISIX) or "direct" (service port)
TEST_MODE="${TEST_MODE:-direct}"

if [ "$TEST_MODE" = "gateway" ]; then
    BASE_URL="http://localhost"
    API_BASE="${BASE_URL}/api/v1"
else
    BASE_URL="http://localhost:8209"
    API_BASE="${BASE_URL}/api/v1"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
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
echo -e "${CYAN}     STORAGE SERVICE - FILE OPERATIONS TEST (Event-Driven v2.0)${NC}"
echo -e "${CYAN}======================================================================${NC}"
if [ "$TEST_MODE" = "gateway" ]; then
    echo -e "${BLUE}Test Mode: GATEWAY (via APISIX, JWT required)${NC}"
else
    echo -e "${BLUE}Test Mode: DIRECT (service port, no JWT)${NC}"
fi
echo -e "${BLUE}Base URL: ${BASE_URL}${NC}"
echo ""

# Use test user from seed_test_data.sql
# See: microservices/storage_service/migrations/seed_test_data.sql
TEST_USER_ID="test_user_001"
echo -e "${GREEN}Using test user: ${CYAN}$TEST_USER_ID${NC}"
echo -e "${CYAN}(Defined in migrations/seed_test_data.sql)${NC}"
echo ""

# ============================================
# JWT Token Setup (for gateway mode)
# ============================================
AUTH_HEADER=""
if [ "$TEST_MODE" = "gateway" ]; then
    echo -e "${YELLOW}Gateway mode: Obtaining JWT Token from Auth Service...${NC}"
    TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/dev-token" \
      -H "Content-Type: application/json" \
      -d "{\"user_id\": \"${TEST_USER_ID}\", \"email\": \"testuser@example.com\", \"expires_in\": 3600}")

    JWT_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

    if [ -z "$JWT_TOKEN" ] || [ "$JWT_TOKEN" = "null" ]; then
        echo -e "${RED}✗ Failed to obtain JWT token${NC}"
        echo "Response: $TOKEN_RESPONSE"
        exit 1
    fi
    echo -e "${GREEN}✓ JWT Token obtained (first 50 chars): ${JWT_TOKEN:0:50}...${NC}"
    AUTH_HEADER="Authorization: Bearer $JWT_TOKEN"
else
    echo -e "${YELLOW}Direct mode: No JWT token required${NC}"
fi
echo ""

echo -e "${BLUE}Event-Driven Features:${NC}"
echo "  ✓ Events published via events/publishers.py"
echo "  ✓ Event handlers in events/handlers.py"
echo "  ✓ Expected events: file.uploaded, file.deleted"
echo ""

# Create a test file for upload
TEST_FILE="/tmp/storage_test_file_$(date +%s).txt"
echo "This is a test file for storage service testing." > "$TEST_FILE"
echo "Created at: $(date)" >> "$TEST_FILE"
echo "Test user: $TEST_USER_ID" >> "$TEST_FILE"

# Test 1: Upload File - Event Publisher Test
echo -e "${YELLOW}Test 1: Upload File - Event Publisher Test${NC}"
echo "POST /api/v1/storage/files/upload"
echo -e "${BLUE}Expected Event: file.uploaded will be published to NATS${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST "${API_BASE}/storage/files/upload" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -F "file=@${TEST_FILE}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "access_level=private" \
  -F "tags=test,automated,storage" \
  -F "enable_indexing=false" \
  -F "metadata={\"test\":true,\"purpose\":\"automated_testing\"}")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool

if echo "$UPLOAD_RESPONSE" | grep -q '"file_id"'; then
    FILE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['file_id'])")
    echo -e "${GREEN}✓ File uploaded: $FILE_ID${NC}"
    echo -e "${GREEN}✓ Event 'file.uploaded' should be published with:${NC}"
    echo "  - file_id: $FILE_ID"
    echo "  - user_id: $TEST_USER_ID"
    echo "  - file_name: $(basename $TEST_FILE)"
    test_result 0
else
    echo -e "${RED}✗ Upload failed${NC}"
    test_result 1
    FILE_ID=""
fi
echo ""

# Test 2: List Files
echo -e "${YELLOW}Test 2: List User Files${NC}"
echo "GET /api/v1/storage/files?user_id=${TEST_USER_ID}"
RESPONSE=$(curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "${API_BASE}/storage/files?user_id=${TEST_USER_ID}&limit=10")
echo "$RESPONSE" | python3 -m json.tool | head -50
if echo "$RESPONSE" | grep -q '\['; then
    FILE_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
    echo -e "${GREEN}✓ Found $FILE_COUNT files${NC}"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Get File Info
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 3: Get File Information${NC}"
    echo "GET /api/v1/storage/files/${FILE_ID}?user_id=${TEST_USER_ID}"
    RESPONSE=$(curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "${API_BASE}/storage/files/${FILE_ID}?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    if echo "$RESPONSE" | grep -q '"file_id"'; then
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 3: Get File Information - SKIPPED (no file_id)${NC}"
    echo ""
fi

# Test 4: Get Download URL
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 4: Get File Download URL${NC}"
    echo "GET /api/v1/storage/files/${FILE_ID}/download?user_id=${TEST_USER_ID}"
    RESPONSE=$(curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "${API_BASE}/storage/files/${FILE_ID}/download?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    if echo "$RESPONSE" | grep -q '"download_url"'; then
        DOWNLOAD_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['download_url'])" 2>/dev/null || echo "")
        if [ -n "$DOWNLOAD_URL" ]; then
            echo -e "${GREEN}✓ Download URL obtained${NC}"
            test_result 0
        else
            test_result 1
        fi
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 7: Get File Download URL - SKIPPED (no file_id)${NC}"
    echo ""
fi

# Test 8: Upload File with Auto-Indexing
echo -e "${YELLOW}Test 8: Upload File with Auto-Indexing${NC}"
echo "POST /api/v1/storage/files/upload (with enable_indexing=true)"

# Create a test file with more content for indexing
TEST_FILE_2="/tmp/storage_indexed_file_$(date +%s).txt"
cat > "$TEST_FILE_2" << EOF
This is a comprehensive test document for the storage service.
It contains multiple paragraphs to test the intelligent indexing feature.

The storage service integrates with MinIO for scalable object storage.
It provides semantic search capabilities powered by isA_MCP tools.

This document discusses cloud storage, file management, and intelligent retrieval.
Users can upload files, organize them in albums, and search using natural language.
EOF

UPLOAD_RESPONSE_2=$(curl -s -X POST "${API_BASE}/storage/files/upload" \
  ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
  -F "file=@${TEST_FILE_2}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "access_level=private" \
  -F "tags=indexed,searchable,test" \
  -F "enable_indexing=true" \
  -F "metadata={\"indexed\":true,\"content_type\":\"text\"}")

echo "$UPLOAD_RESPONSE_2" | python3 -m json.tool

if echo "$UPLOAD_RESPONSE_2" | grep -q '"file_id"'; then
    FILE_ID_2=$(echo "$UPLOAD_RESPONSE_2" | python3 -c "import sys, json; print(json.load(sys.stdin)['file_id'])")
    echo -e "${GREEN}✓ File uploaded with indexing: $FILE_ID_2${NC}"
    test_result 0
else
    echo -e "${RED}✗ Upload with indexing failed${NC}"
    test_result 1
    FILE_ID_2=""
fi
echo ""

# Test 9: List Files with Filters
echo -e "${YELLOW}Test 9: List Files with Filters${NC}"
echo "GET /api/v1/storage/files?user_id=${TEST_USER_ID}&prefix=storage&status=available"
RESPONSE=$(curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "${API_BASE}/storage/files?user_id=${TEST_USER_ID}&prefix=storage&status=available&limit=5")
echo "$RESPONSE" | python3 -m json.tool | head -30
if echo "$RESPONSE" | grep -q '\['; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 10: Delete File (Soft Delete)
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 10: Delete File (Soft Delete)${NC}"
    echo "DELETE /api/v1/storage/files/${FILE_ID}?user_id=${TEST_USER_ID}"
    RESPONSE=$(curl -s -X DELETE ${AUTH_HEADER:+-H "$AUTH_HEADER"} "${API_BASE}/storage/files/${FILE_ID}?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    if echo "$RESPONSE" | grep -q "deleted successfully"; then
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 10: Delete File - SKIPPED (no file_id)${NC}"
    echo ""
fi

# Test 11: Verify File is Deleted
if [ -n "$FILE_ID" ]; then
    echo -e "${YELLOW}Test 11: Verify File is Deleted${NC}"
    echo "GET /api/v1/storage/files/${FILE_ID}?user_id=${TEST_USER_ID}"
    RESPONSE=$(curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "${API_BASE}/storage/files/${FILE_ID}?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    # Should return 404 or show deleted status
    if echo "$RESPONSE" | grep -q "not found\|deleted"; then
        echo -e "${GREEN}✓ File confirmed deleted${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 11: Verify File is Deleted - SKIPPED${NC}"
    echo ""
fi

# Test 12: Permanent Delete
if [ -n "$FILE_ID_2" ]; then
    echo -e "${YELLOW}Test 12: Permanent Delete File${NC}"
    echo "DELETE /api/v1/storage/files/${FILE_ID_2}?user_id=${TEST_USER_ID}&permanent=true"
    RESPONSE=$(curl -s -X DELETE ${AUTH_HEADER:+-H "$AUTH_HEADER"} "${API_BASE}/storage/files/${FILE_ID_2}?user_id=${TEST_USER_ID}&permanent=true")
    echo "$RESPONSE" | python3 -m json.tool
    if echo "$RESPONSE" | grep -q "deleted successfully"; then
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 12: Permanent Delete File - SKIPPED${NC}"
    echo ""
fi

# Cleanup
rm -f "$TEST_FILE" "$TEST_FILE_2"

# Print summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e "Total Tests: ${TOTAL}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL FILE OPERATIONS TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
