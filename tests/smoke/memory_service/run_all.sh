#!/bin/bash
# Memory Service Smoke Tests Runner
# Runs all smoke tests for memory_service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Memory Service Smoke Tests"
echo "========================================"

TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_file="$1"
    echo ""
    echo "Running: $test_file"
    echo "----------------------------------------"
    if bash "$test_file"; then
        ((TESTS_PASSED++))
        echo "PASSED: $test_file"
    else
        ((TESTS_FAILED++))
        echo "FAILED: $test_file"
    fi
}

# Memory Type Tests
run_test "test_factual_memory.sh"
run_test "test_episodic_memory.sh"
run_test "test_procedural_memory.sh"
run_test "test_semantic_memory.sh"
run_test "test_session_memory.sh"
run_test "test_working_memory.sh"

# Event Tests
run_test "memory_service_test_event_publishing.sh"
run_test "memory_service_test_event_subscriptions.sh"

# Memory v2 Feature Tests
run_test "test_memory_decay.sh"
run_test "test_mmr_reranking.sh"
run_test "test_memory_associations.sh"
run_test "test_context_ordering.sh"
run_test "test_context_compression.sh"
run_test "test_memory_consolidation.sh"
run_test "test_graph_search.sh"
run_test "test_hybrid_search.sh"

echo ""
echo "========================================"
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "========================================"

[ $TESTS_FAILED -eq 0 ]
