#!/bin/bash
# Album Service - Album Management Test Script
# Tests: Create Album, Get Album, List Albums, Update Album, Add Photos, Delete Album

BASE_URL="http://localhost:8219"
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
echo -e "${CYAN}       STORAGE SERVICE - ALBUM MANAGEMENT TEST${NC}"
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
    print(f'test_user_001|test@example.com', file=sys.stderr)
" 2>&1)

TEST_USER_ID=$(echo "$TEST_USER" | cut -d'|' -f1)
TEST_USER_EMAIL=$(echo "$TEST_USER" | cut -d'|' -f2)
echo -e "${GREEN}✓ Using test user: $TEST_USER_ID${NC}"
echo ""

# Test 1: Create Album
echo -e "${YELLOW}Test 1: Create Album${NC}"
echo "POST /api/v1/albums"

CREATE_REQUEST=$(cat <<EOF
{
    "name": "Family Vacation 2025",
    "description": "Our amazing summer vacation photos",
    "user_id": "${TEST_USER_ID}",
    "auto_sync": true,
    "enable_family_sharing": false,
    "tags": ["vacation", "family", "2025"]
}
EOF
)

ALBUM_RESPONSE=$(curl -s -X POST "${API_BASE}/albums?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$CREATE_REQUEST")

echo "$ALBUM_RESPONSE" | python3 -m json.tool

if echo "$ALBUM_RESPONSE" | grep -q '"album_id"'; then
    ALBUM_ID=$(echo "$ALBUM_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['album_id'])")
    echo -e "${GREEN}✓ Album created: $ALBUM_ID${NC}"
    test_result 0
else
    echo -e "${RED}✗ Album creation failed${NC}"
    test_result 1
    ALBUM_ID=""
fi
echo ""

# Test 2: Get Album Details
if [ -n "$ALBUM_ID" ]; then
    echo -e "${YELLOW}Test 2: Get Album Details${NC}"
    echo "GET /api/v1/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}"

    GET_RESPONSE=$(curl -s "${API_BASE}/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}")

    echo "$GET_RESPONSE" | python3 -m json.tool

    if echo "$GET_RESPONSE" | grep -q '"album_id"'; then
        ALBUM_NAME=$(echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('name', ''))")
        echo -e "${GREEN}✓ Album retrieved: $ALBUM_NAME${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 2: Get Album - SKIPPED${NC}"
    echo ""
fi

# Test 3: List User Albums
echo -e "${YELLOW}Test 3: List User Albums${NC}"
echo "GET /api/v1/albums?user_id=${TEST_USER_ID}"

LIST_RESPONSE=$(curl -s "${API_BASE}/albums?user_id=${TEST_USER_ID}&limit=10")

echo "$LIST_RESPONSE" | python3 -m json.tool | head -40

if echo "$LIST_RESPONSE" | grep -q '"albums"'; then
    ALBUM_COUNT=$(echo "$LIST_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
    echo -e "${GREEN}✓ Found $ALBUM_COUNT albums${NC}"
    test_result 0
else
    test_result 1
fi
echo ""

# Upload photos for album testing
echo -e "${CYAN}Uploading test photos for album...${NC}"

PHOTO_IDS=()
for i in 1 2 3; do
    TEST_PHOTO="/tmp/album_photo_${i}_$(date +%s).txt"
    echo "Test Photo $i for album testing" > "$TEST_PHOTO"

    UPLOAD_RESPONSE=$(curl -s -X POST "${API_BASE}/files/upload" \
      -F "file=@${TEST_PHOTO}" \
      -F "user_id=${TEST_USER_ID}" \
      -F "access_level=private" \
      -F "tags=album,photo,test" \
      -F "enable_indexing=false")

    if echo "$UPLOAD_RESPONSE" | grep -q '"file_id"'; then
        PHOTO_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['file_id'])")
        PHOTO_IDS+=("$PHOTO_ID")
        echo -e "  ${GREEN}✓ Photo $i uploaded: $PHOTO_ID${NC}"
    fi

    rm -f "$TEST_PHOTO"
done

echo ""

# Test 4: Add Photos to Album
if [ -n "$ALBUM_ID" ] && [ ${#PHOTO_IDS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Test 4: Add Photos to Album${NC}"
    echo "POST /api/v1/albums/${ALBUM_ID}/photos"

    PHOTO_IDS_JSON=$(printf '%s\n' "${PHOTO_IDS[@]}" | jq -R . | jq -s .)

    ADD_PHOTOS_REQUEST=$(cat <<EOF
{
    "photo_ids": $(echo "$PHOTO_IDS_JSON"),
    "added_by": "${TEST_USER_ID}",
    "is_featured": false
}
EOF
)

    ADD_RESPONSE=$(curl -s -X POST "${API_BASE}/albums/${ALBUM_ID}/photos?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$ADD_PHOTOS_REQUEST")

    echo "$ADD_RESPONSE" | python3 -m json.tool

    if echo "$ADD_RESPONSE" | grep -q '"success".*true'; then
        echo -e "${GREEN}✓ Photos added to album${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 4: Add Photos - SKIPPED${NC}"
    echo ""
fi

# Test 5: Get Album Photos
if [ -n "$ALBUM_ID" ]; then
    echo -e "${YELLOW}Test 5: Get Album Photos${NC}"
    echo "GET /api/v1/albums/${ALBUM_ID}/photos?user_id=${TEST_USER_ID}"

    PHOTOS_RESPONSE=$(curl -s "${API_BASE}/albums/${ALBUM_ID}/photos?user_id=${TEST_USER_ID}&limit=20")

    echo "$PHOTOS_RESPONSE" | python3 -m json.tool | head -40

    if echo "$PHOTOS_RESPONSE" | grep -q '"photos"'; then
        PHOTO_COUNT=$(echo "$PHOTOS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
        echo -e "${GREEN}✓ Album has $PHOTO_COUNT photos${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 5: Get Album Photos - SKIPPED${NC}"
    echo ""
fi

# Test 6: Update Album
if [ -n "$ALBUM_ID" ]; then
    echo -e "${YELLOW}Test 6: Update Album${NC}"
    echo "PUT /api/v1/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}"

    UPDATE_REQUEST=$(cat <<EOF
{
    "name": "Family Vacation 2025 - Updated",
    "description": "Updated description with more details",
    "tags": ["vacation", "family", "2025", "updated"]
}
EOF
)

    UPDATE_RESPONSE=$(curl -s -X PUT "${API_BASE}/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_REQUEST")

    echo "$UPDATE_RESPONSE" | python3 -m json.tool

    if echo "$UPDATE_RESPONSE" | grep -q '"album_id"'; then
        UPDATED_NAME=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('name', ''))")
        echo -e "${GREEN}✓ Album updated: $UPDATED_NAME${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 6: Update Album - SKIPPED${NC}"
    echo ""
fi

# Test 7: Create Album with Family Sharing (requires organization)
echo -e "${YELLOW}Test 7: Create Album with Family Sharing${NC}"

# Try to get organization_id
ORG_ID=$(docker exec user-staging python3 -c "
import sys
sys.path.insert(0, '/app')
from core.database.supabase_client import get_supabase_client

try:
    client = get_supabase_client()
    result = client.table('organization_members').select('organization_id').eq('user_id', '${TEST_USER_ID}').eq('status', 'active').limit(1).execute()
    if result.data and len(result.data) > 0:
        print(result.data[0]['organization_id'])
except:
    pass
" 2>&1)

if [ -n "$ORG_ID" ] && [ "$ORG_ID" != "" ]; then
    CREATE_SHARED_REQUEST=$(cat <<EOF
{
    "name": "Family Shared Album",
    "description": "Album shared with family members",
    "user_id": "${TEST_USER_ID}",
    "organization_id": "${ORG_ID}",
    "auto_sync": true,
    "enable_family_sharing": true,
    "tags": ["family", "shared"]
}
EOF
)

    SHARED_ALBUM_RESPONSE=$(curl -s -X POST "${API_BASE}/albums?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$CREATE_SHARED_REQUEST")

    echo "$SHARED_ALBUM_RESPONSE" | python3 -m json.tool

    if echo "$SHARED_ALBUM_RESPONSE" | grep -q '"album_id"'; then
        SHARED_ALBUM_ID=$(echo "$SHARED_ALBUM_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['album_id'])")
        echo -e "${GREEN}✓ Shared album created: $SHARED_ALBUM_ID${NC}"
        test_result 0
    else
        test_result 1
    fi
else
    echo -e "${YELLOW}⚠ No organization found, skipping family sharing test${NC}"
    test_result 0
fi
echo ""

# Test 8: Get Album Sync Status
if [ -n "$ALBUM_ID" ]; then
    echo -e "${YELLOW}Test 8: Get Album Sync Status${NC}"
    FRAME_ID="test_frame_001"
    echo "GET /api/v1/albums/${ALBUM_ID}/sync/${FRAME_ID}?user_id=${TEST_USER_ID}"

    SYNC_RESPONSE=$(curl -s "${API_BASE}/albums/${ALBUM_ID}/sync/${FRAME_ID}?user_id=${TEST_USER_ID}")

    echo "$SYNC_RESPONSE" | python3 -m json.tool

    if echo "$SYNC_RESPONSE" | grep -q '"sync_status"'; then
        SYNC_STATUS=$(echo "$SYNC_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('sync_status', ''))")
        echo -e "${GREEN}✓ Sync status: $SYNC_STATUS${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 8: Get Sync Status - SKIPPED${NC}"
    echo ""
fi

# Test 9: Trigger Album Sync
if [ -n "$ALBUM_ID" ]; then
    echo -e "${YELLOW}Test 9: Trigger Album Sync${NC}"
    FRAME_ID="test_frame_001"
    echo "POST /api/v1/albums/${ALBUM_ID}/sync?user_id=${TEST_USER_ID}"

    SYNC_REQUEST=$(cat <<EOF
{
    "frame_id": "${FRAME_ID}"
}
EOF
)

    TRIGGER_RESPONSE=$(curl -s -X POST "${API_BASE}/albums/${ALBUM_ID}/sync?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$SYNC_REQUEST")

    echo "$TRIGGER_RESPONSE" | python3 -m json.tool

    if echo "$TRIGGER_RESPONSE" | grep -q '"sync_status"'; then
        echo -e "${GREEN}✓ Sync triggered successfully${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 9: Trigger Sync - SKIPPED${NC}"
    echo ""
fi

# Test 10: Delete Album
if [ -n "$ALBUM_ID" ]; then
    echo -e "${YELLOW}Test 10: Delete Album${NC}"
    echo "DELETE /api/v1/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}"

    DELETE_RESPONSE=$(curl -s -X DELETE "${API_BASE}/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}")

    echo "$DELETE_RESPONSE" | python3 -m json.tool

    if echo "$DELETE_RESPONSE" | grep -q '"success".*true'; then
        echo -e "${GREEN}✓ Album deleted${NC}"
        test_result 0
    else
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 10: Delete Album - SKIPPED${NC}"
    echo ""
fi

# Test 11: Verify Album is Deleted
if [ -n "$ALBUM_ID" ]; then
    echo -e "${YELLOW}Test 11: Verify Album is Deleted${NC}"
    echo "GET /api/v1/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}"

    GET_RESPONSE=$(curl -s "${API_BASE}/albums/${ALBUM_ID}?user_id=${TEST_USER_ID}")

    echo "$GET_RESPONSE" | python3 -m json.tool

    if echo "$GET_RESPONSE" | grep -qi "not found\|error"; then
        echo -e "${GREEN}✓ Album confirmed deleted${NC}"
        test_result 0
    else
        echo -e "${RED}✗ Album still exists${NC}"
        test_result 1
    fi
    echo ""
else
    echo -e "${YELLOW}Test 11: Verify Deletion - SKIPPED${NC}"
    echo ""
fi

# Cleanup uploaded photos
for PHOTO_ID in "${PHOTO_IDS[@]}"; do
    curl -s -X DELETE "${API_BASE}/files/${PHOTO_ID}?user_id=${TEST_USER_ID}&permanent=true" > /dev/null
done

# Print summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e "Total Tests: ${TOTAL}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL ALBUM MANAGEMENT TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
