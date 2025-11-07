#!/usr/bin/env bash
#
# Debug script to test image upload with AI extraction
#

STORAGE_URL="${STORAGE_URL:-http://localhost:8209}"
TEST_USER="debug_user_$$"
TEST_ORG="debug_org"
TEST_IMAGE_URL="https://picsum.photos/800/600"
TEST_IMAGE_PATH="/tmp/debug_image_$$.jpg"

echo "=== Debug Upload Test ==="
echo "Storage Service: $STORAGE_URL"
echo "Test User: $TEST_USER"
echo ""

# Download test image
echo "[1] Downloading test image..."
curl -sL -H "User-Agent: Mozilla/5.0" "$TEST_IMAGE_URL" -o "$TEST_IMAGE_PATH"
if [ -f "$TEST_IMAGE_PATH" ] && [ -s "$TEST_IMAGE_PATH" ]; then
    echo "✓ Downloaded $(wc -c < "$TEST_IMAGE_PATH" | tr -d ' ') bytes"
else
    echo "✗ Failed to download image"
    exit 1
fi

# Upload image
echo ""
echo "[2] Uploading image to storage service..."
UPLOAD_RESP=$(curl -s -X POST "$STORAGE_URL/api/v1/storage/files/upload" \
  -F "file=@$TEST_IMAGE_PATH" \
  -F "user_id=$TEST_USER" \
  -F "organization_id=$TEST_ORG")

echo "Response:"
echo "$UPLOAD_RESP" | jq '.' 2>/dev/null || echo "$UPLOAD_RESP"

FILE_ID=$(echo "$UPLOAD_RESP" | jq -r '.file_id' 2>/dev/null)

if [ -n "$FILE_ID" ] && [ "$FILE_ID" != "null" ]; then
    echo ""
    echo "✓ Upload successful, file_id=$FILE_ID"
    echo ""
    echo "[3] Waiting 10 seconds for AI extraction..."
    sleep 10

    echo ""
    echo "[4] Testing image search..."
    SEARCH_RESP=$(curl -s -X POST "$STORAGE_URL/api/v1/storage/intelligence/image/search" \
      -H "Content-Type: application/json" \
      -d "{
        \"user_id\": \"$TEST_USER\",
        \"query\": \"photo\",
        \"top_k\": 5
      }")

    echo "Search Response:"
    echo "$SEARCH_RESP" | jq '.' 2>/dev/null || echo "$SEARCH_RESP"
else
    echo "✗ Upload failed"
fi

# Cleanup
rm -f "$TEST_IMAGE_PATH"
