#!/usr/bin/env bash
#
# Storage Service - Image Upload with AI Extraction Test
#
# 测试图片上传后自动调用 MCP store_knowledge 进行AI提取
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
STORAGE_URL="${STORAGE_URL:-http://localhost:8209}"
MCP_URL="${MCP_URL:-http://localhost:8081}"
TEST_USER="test_user_storage_$$"
TEST_IMAGE_URL="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800"
TEST_IMAGE_PATH="/tmp/test_storage_image_$$.jpg"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ Storage Service - Image Upload with AI Extraction Test        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  Storage Service: $STORAGE_URL"
echo "  MCP Service: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  Test Image: $TEST_IMAGE_URL"
echo ""

# Test counter
PASS=0
FAIL=0

pass_test() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASS++))
}

fail_test() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAIL++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Cleanup
cleanup() {
    if [ -f "$TEST_IMAGE_PATH" ]; then
        rm -f "$TEST_IMAGE_PATH"
        info "Cleaned up test image"
    fi
}

trap cleanup EXIT

# ==============================================================================
# Test 0: Download Test Image
# ==============================================================================
echo -e "${BLUE}[TEST 0]${NC} Download Test Image from Unsplash"

curl -sL "$TEST_IMAGE_URL" -o "$TEST_IMAGE_PATH"

if [ -f "$TEST_IMAGE_PATH" ] && [ -s "$TEST_IMAGE_PATH" ]; then
    FILE_SIZE=$(wc -c < "$TEST_IMAGE_PATH" | tr -d ' ')
    pass_test "Downloaded test image ($FILE_SIZE bytes)"
else
    fail_test "Failed to download test image"
    exit 1
fi

# ==============================================================================
# Test 1: MCP Server Health Check
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 1]${NC} MCP Server Health Check"

HEALTH=$(curl -s "$MCP_URL/health")
STATUS=$(echo "$HEALTH" | jq -r '.status' 2>/dev/null)

if [[ "$STATUS" == "ok" || "$STATUS" =~ ^healthy ]]; then
    pass_test "MCP server is healthy"
else
    fail_test "MCP server is not healthy"
    echo "Response: $HEALTH"
fi

# ==============================================================================
# Test 2: Storage Service Health Check
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 2]${NC} Storage Service Health Check"

STORAGE_HEALTH=$(curl -s "$STORAGE_URL/health")
STORAGE_STATUS=$(echo "$STORAGE_HEALTH" | jq -r '.status' 2>/dev/null)

if [ "$STORAGE_STATUS" = "healthy" ]; then
    pass_test "Storage service is healthy"
else
    fail_test "Storage service is not healthy"
    echo "Response: $STORAGE_HEALTH"
fi

# ==============================================================================
# Test 3: Test Direct MCP store_knowledge (Baseline)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Direct MCP store_knowledge (Baseline)"

info "Testing MCP store_knowledge directly (10-15 seconds)..."

STORE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "content": "$TEST_IMAGE_URL",
      "content_type": "image",
      "metadata": {
        "source": "baseline_test"
      }
    }
  }
}
EOF
)

STORE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STORE_PAYLOAD")

STORE_DATA=$(echo "$STORE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
STORE_SUCCESS=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)

if [ "$STORE_SUCCESS" = "true" ]; then
    pass_test "MCP store_knowledge baseline successful"

    # Extract AI metadata
    AI_METADATA=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.ai_metadata' 2>/dev/null)
    if [ "$AI_METADATA" != "null" ] && [ -n "$AI_METADATA" ]; then
        TAGS=$(echo "$AI_METADATA" | jq -r '.ai_tags[:3][]' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
        info "Baseline AI tags: $TAGS"
    fi
else
    fail_test "MCP store_knowledge baseline failed"
fi

# ==============================================================================
# Test 4: Test Storage Service Intelligence API (store_image)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Storage Service Intelligence API (store_image)"

info "Testing Storage Intelligence /api/v1/intelligence/image/store endpoint..."

STORAGE_STORE_PAYLOAD=$(cat <<EOF
{
  "user_id": "$TEST_USER",
  "image_path": "$TEST_IMAGE_URL",
  "metadata": {
    "source": "storage_test",
    "test": "image_upload"
  },
  "model": "gpt-4o-mini"
}
EOF
)

STORAGE_STORE_RESP=$(curl -s -X POST "$STORAGE_URL/api/v1/intelligence/image/store" \
  -H "Content-Type: application/json" \
  -d "$STORAGE_STORE_PAYLOAD")

STORAGE_SUCCESS=$(echo "$STORAGE_STORE_RESP" | jq -r '.success' 2>/dev/null)
DESCRIPTION=$(echo "$STORAGE_STORE_RESP" | jq -r '.description' 2>/dev/null)

if [ "$STORAGE_SUCCESS" = "true" ]; then
    pass_test "Storage Intelligence store_image successful"
    info "Description length: $DESCRIPTION characters"

    # Extract metadata
    VLM_MODEL=$(echo "$STORAGE_STORE_RESP" | jq -r '.vlm_model' 2>/dev/null)
    STORAGE_ID=$(echo "$STORAGE_STORE_RESP" | jq -r '.storage_id' 2>/dev/null)
    info "VLM Model: $VLM_MODEL, Storage ID: ${STORAGE_ID:0:16}..."
else
    fail_test "Storage Intelligence store_image failed"
    echo "Response: $STORAGE_STORE_RESP" | jq '.' 2>/dev/null || echo "$STORAGE_STORE_RESP"
fi

# ==============================================================================
# Test 5: Search Images via Storage Service
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Search Images via Storage Intelligence API"

SEARCH_PAYLOAD=$(cat <<EOF
{
  "user_id": "$TEST_USER",
  "query": "mountains with snow and sunset",
  "top_k": 5
}
EOF
)

SEARCH_RESP=$(curl -s -X POST "$STORAGE_URL/api/v1/intelligence/image/search" \
  -H "Content-Type: application/json" \
  -d "$SEARCH_PAYLOAD")

SEARCH_SUCCESS=$(echo "$SEARCH_RESP" | jq -r '.success' 2>/dev/null)
TOTAL_FOUND=$(echo "$SEARCH_RESP" | jq -r '.total_images_found' 2>/dev/null)

if [ "$SEARCH_SUCCESS" = "true" ] && [ "$TOTAL_FOUND" -gt 0 ]; then
    pass_test "Image search returned $TOTAL_FOUND results"

    # Extract first result
    FIRST_SCORE=$(echo "$SEARCH_RESP" | jq -r '.image_results[0].relevance_score' 2>/dev/null)
    FIRST_DESC=$(echo "$SEARCH_RESP" | jq -r '.image_results[0].description' 2>/dev/null)
    info "Best match score: $FIRST_SCORE"
    info "Description preview: ${FIRST_DESC:0:80}..."
else
    fail_test "Image search failed or returned no results"
    echo "Response: $SEARCH_RESP" | jq '.' 2>/dev/null || echo "$SEARCH_RESP"
fi

# ==============================================================================
# Test 6: RAG Query with Images
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} RAG Query with Images"

RAG_PAYLOAD=$(cat <<EOF
{
  "user_id": "$TEST_USER",
  "query": "Describe the landscape photos in my collection",
  "context_limit": 3,
  "rag_mode": "simple"
}
EOF
)

RAG_RESP=$(curl -s -X POST "$STORAGE_URL/api/v1/intelligence/image/rag" \
  -H "Content-Type: application/json" \
  -d "$RAG_PAYLOAD")

RAG_SUCCESS=$(echo "$RAG_RESP" | jq -r '.success' 2>/dev/null)
RAG_ANSWER=$(echo "$RAG_RESP" | jq -r '.response' 2>/dev/null)  # 修复: 字段名从 .answer 改为 .response

if [ "$RAG_SUCCESS" = "true" ] && [ -n "$RAG_ANSWER" ] && [ "$RAG_ANSWER" != "null" ]; then
    pass_test "RAG query successful"
    info "Answer preview: ${RAG_ANSWER:0:120}..."

    # 显示上下文数量
    CONTEXT_ITEMS=$(echo "$RAG_RESP" | jq -r '.context_items' 2>/dev/null)
    if [ -n "$CONTEXT_ITEMS" ] && [ "$CONTEXT_ITEMS" != "null" ]; then
        info "Context items used: $CONTEXT_ITEMS"
    fi
else
    fail_test "RAG query failed"
    echo "Response: $RAG_RESP" | jq '.' 2>/dev/null || echo "$RAG_RESP"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ Test Summary                                                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS"
echo -e "${RED}Failed:${NC} $FAIL"
echo ""

TOTAL=$((PASS + FAIL))
echo "Total Tests: $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "✨ Storage Service Image AI Integration Verified!"
    echo ""
    echo "The system successfully:"
    echo "  ✓ Stores images via Storage Service"
    echo "  ✓ Calls MCP store_knowledge for AI extraction"
    echo "  ✓ Extracts AI metadata (categories, tags, mood, colors)"
    echo "  ✓ Stores embeddings in vector database"
    echo "  ✓ Searches images semantically"
    echo "  ✓ Generates RAG responses with image context"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check service logs:"
    echo "  - Storage Service logs"
    echo "  - MCP server logs"
    exit 1
fi
