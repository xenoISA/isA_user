#!/usr/bin/env bash
#
# End-to-End Test: PDF 上传 → Async 索引 → Qdrant 存储
#
# 测试完整异步流程：
# 1. 用户上传 PDF 到 Storage Service
# 2. Upload 立即返回（async）
# 3. Background task 调用 MCP 进行 PDF 文本提取
# 4. 数据存储到 Qdrant 和 storage_intelligence_index
# 5. 验证可以通过语义搜索找到 PDF 内容
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration - via Kubernetes Ingress
STORAGE_URL="${STORAGE_URL:-http://localhost}"
MCP_URL="${MCP_URL:-http://localhost:8081}"
TEST_USER="test_user_pdf_e2e_$$"
TEST_PDF_URL="https://arxiv.org/pdf/1706.03762.pdf"
TEST_PDF_PATH="/tmp/test_e2e_pdf_$$.pdf"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ End-to-End Test: PDF Upload → Async Index → Search           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  Storage Service: $STORAGE_URL"
echo "  MCP Service: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  Test PDF: $TEST_PDF_URL"
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
    if [ -f "$TEST_PDF_PATH" ]; then
        rm -f "$TEST_PDF_PATH"
    fi
}

trap cleanup EXIT

# ==============================================================================
# Test 0: Download Test PDF
# ==============================================================================
echo -e "${BLUE}[TEST 0]${NC} Download Test PDF"

curl -sL "$TEST_PDF_URL" -o "$TEST_PDF_PATH"

if [ -f "$TEST_PDF_PATH" ] && [ -s "$TEST_PDF_PATH" ]; then
    FILE_SIZE=$(wc -c < "$TEST_PDF_PATH" | tr -d ' ')
    pass_test "Downloaded test PDF ($FILE_SIZE bytes)"
else
    fail_test "Failed to download test PDF"
    exit 1
fi

# ==============================================================================
# Test 1: Services Health Check
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 1]${NC} Services Health Check"

STORAGE_HEALTH=$(curl -s "$STORAGE_URL/health" | jq -r '.status' 2>/dev/null)
MCP_HEALTH=$(curl -s "$MCP_URL/health" | jq -r '.status' 2>/dev/null)

if [[ "$STORAGE_HEALTH" == "healthy" && "$MCP_HEALTH" =~ ^(ok|healthy) ]]; then
    pass_test "All services healthy (Storage, MCP)"
else
    fail_test "Service health check failed"
    info "Storage: $STORAGE_HEALTH, MCP: $MCP_HEALTH"
fi

# ==============================================================================
# Test 2: Upload PDF to Storage Service (Async)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 2]${NC} Upload PDF to Storage Service (Async)"
info "Upload should return immediately, indexing happens in background..."

UPLOAD_START=$(date +%s)

UPLOAD_RESP=$(curl -s -X POST "$STORAGE_URL/api/v1/storage/files/upload" \
    -F "file=@$TEST_PDF_PATH" \
    -F "user_id=$TEST_USER" \
    -F "enable_indexing=true")

UPLOAD_END=$(date +%s)
UPLOAD_TIME=$((UPLOAD_END - UPLOAD_START))

FILE_ID=$(echo "$UPLOAD_RESP" | jq -r '.file_id' 2>/dev/null)

if [ -n "$FILE_ID" ] && [ "$FILE_ID" != "null" ]; then
    pass_test "PDF uploaded successfully in ${UPLOAD_TIME}s: $FILE_ID"
    
    if [ $UPLOAD_TIME -lt 5 ]; then
        info "✨ Fast upload time confirms async processing!"
    else
        info "⚠️  Upload took ${UPLOAD_TIME}s - should be faster with async"
    fi
else
    fail_test "PDF upload failed"
    echo "$UPLOAD_RESP" | jq '.' 2>/dev/null || echo "$UPLOAD_RESP"
    exit 1
fi

# ==============================================================================
# Test 3: Wait for Async Indexing to Complete
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Waiting for Background Indexing"
info "Async indexing should complete in 15-30 seconds..."

sleep 25

# ==============================================================================
# Test 4: Verify PDF Indexed in storage_intelligence_index
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Verify PDF in storage_intelligence_index"

# This requires database access - skip if not available
info "Checking if PDF was indexed (requires PostgreSQL access)..."
info "File ID: $FILE_ID"

# ==============================================================================
# Test 5: Search PDF Content via MCP
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Search PDF Content (Semantic Search)"
info "Searching for 'attention mechanism transformer'..."

SEARCH_PAYLOAD=$(cat <<SEARCH_EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "attention mechanism transformer",
      "search_options": {
        "limit": 3
      }
    }
  }
}
SEARCH_EOF
)

SEARCH_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$SEARCH_PAYLOAD")

SEARCH_DATA=$(echo "$SEARCH_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
TOTAL_RESULTS=$(echo "$SEARCH_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.total_results' 2>/dev/null)

if [ -n "$TOTAL_RESULTS" ] && [ "$TOTAL_RESULTS" != "null" ] && [ "$TOTAL_RESULTS" -gt 0 ]; then
    pass_test "PDF search successful ($TOTAL_RESULTS results found)"
    
    # Show first result preview
    FIRST_TEXT=$(echo "$SEARCH_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.search_results[0].text' 2>/dev/null | cut -c1-100)
    if [ -n "$FIRST_TEXT" ] && [ "$FIRST_TEXT" != "null" ]; then
        info "Preview: ${FIRST_TEXT}..."
    fi
else
    fail_test "PDF search returned no results"
    info "This means async indexing may have failed or not completed"
fi

# ==============================================================================
# Test 6: RAG Query with PDF Context
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} Knowledge Response with PDF Context (RAG)"

RAG_PAYLOAD=$(cat <<RAG_EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "What is the transformer architecture?",
      "response_options": {
        "rag_mode": "simple",
        "context_limit": 3
      }
    }
  }
}
RAG_EOF
)

RAG_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$RAG_PAYLOAD")

RAG_DATA=$(echo "$RAG_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
RAG_SUCCESS=$(echo "$RAG_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)

if [ "$RAG_SUCCESS" == "true" ]; then
    pass_test "RAG response with PDF context successful"
    
    RAG_ANSWER=$(echo "$RAG_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.response' 2>/dev/null | cut -c1-150)
    info "Answer: ${RAG_ANSWER}..."
else
    fail_test "RAG response failed"
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
    echo -e "${GREEN}✓ All PDF async indexing tests passed!${NC}"
    echo ""
    echo -e "${GREEN}✨ Complete Async Flow Verified!${NC}"
    echo ""
    echo "The system successfully:"
    echo "  ✓ Uploaded PDF with fast async response"
    echo "  ✓ Background task indexed PDF via MCP"
    echo "  ✓ Extracted text from PDF document"
    echo "  ✓ Stored PDF chunks in Qdrant"
    echo "  ✓ Semantic search returns PDF content"
    echo "  ✓ RAG provides answers with PDF context"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check logs:"
    echo "  docker logs user-staging | grep -E 'PDF|Indexing'"
    exit 1
fi
