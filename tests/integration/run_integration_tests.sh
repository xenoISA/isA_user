#!/usr/bin/env bash
#
# 集成测试主运行脚本
#
# 此脚本执行完整的集成测试流程:
# 1. 检查服务健康状态
# 2. 运行用户和设备注册流程测试
# 3. 运行事件流测试
# 4. 生成测试报告
#
# 使用方式:
#   ./run_integration_tests.sh
#
# 环境变量:
#   SKIP_HEALTH_CHECK - 跳过健康检查 (true/false, 默认: false)
#   RUN_DETAILED_TESTS - 运行详细测试 (true/false, 默认: true)
#   TEST_EMAIL - 测试邮箱 (可选,自动生成)
#   VERIFICATION_CODE - 验证码 (可选,从dev端点获取)
#

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKIP_HEALTH_CHECK=${SKIP_HEALTH_CHECK:-false}
RUN_DETAILED_TESTS=${RUN_DETAILED_TESTS:-true}

# 日志文件
LOG_DIR="$PROJECT_ROOT/tests/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_LOG="$LOG_DIR/integration_test_${TIMESTAMP}.log"

# 测试结果
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# 函数: 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_header() {
    echo ""
    echo "================================================================================"
    echo -e "${CYAN}$1${NC}"
    echo "================================================================================"
}

# 函数: 记录日志
log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1" | tee -a "$TEST_LOG"
}

# 函数: 检查必要的工具
check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing_tools=()

    for tool in python3 curl jq nc psql; do
        if command -v "$tool" >/dev/null 2>&1; then
            print_success "$tool is installed"
        else
            print_error "$tool is not installed"
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing tools: ${missing_tools[*]}"
        print_info "Please install missing tools and try again"
        exit 1
    fi

    # 检查 Python 依赖
    print_info "Checking Python dependencies..."
    if python3 -c "import httpx, asyncpg, asyncio" 2>/dev/null; then
        print_success "Python dependencies are installed"
    else
        print_warning "Some Python dependencies may be missing"
        print_info "Run: pip install httpx asyncpg"
    fi
}

# 函数: 检查服务健康
check_services_health() {
    if [ "$SKIP_HEALTH_CHECK" = "true" ]; then
        print_warning "Skipping health check (SKIP_HEALTH_CHECK=true)"
        return 0
    fi

    print_header "Checking Services Health"

    if [ -x "$SCRIPT_DIR/check_services_health.sh" ]; then
        if "$SCRIPT_DIR/check_services_health.sh"; then
            print_success "All services are healthy"
            return 0
        else
            print_error "Some services are not healthy"
            print_info "Please fix unhealthy services before running tests"
            return 1
        fi
    else
        print_warning "Health check script not found or not executable"
        return 0
    fi
}

# 函数: 运行 Python 集成测试
run_python_integration_test() {
    print_header "Running Python Integration Tests"

    local test_script="$SCRIPT_DIR/test_user_device_registration_flow.py"

    if [ ! -f "$test_script" ]; then
        print_error "Test script not found: $test_script"
        ((TESTS_SKIPPED++))
        return 1
    fi

    print_info "Running: $test_script"
    log "Starting Python integration test"

    if python3 "$test_script" 2>&1 | tee -a "$TEST_LOG"; then
        print_success "Python integration tests passed"
        log "Python integration test completed successfully"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "Python integration tests failed"
        log "Python integration test failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# 函数: 运行事件流测试
run_event_flow_test() {
    print_header "Running Event Flow Tests"

    local test_script="$PROJECT_ROOT/tests/integration/test_event_flows.py"

    if [ ! -f "$test_script" ]; then
        print_warning "Event flow test script not found: $test_script"
        ((TESTS_SKIPPED++))
        return 0
    fi

    print_info "Running: $test_script"
    log "Starting event flow test"

    if python3 "$test_script" 2>&1 | tee -a "$TEST_LOG"; then
        print_success "Event flow tests passed"
        log "Event flow test completed successfully"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "Event flow tests failed"
        log "Event flow test failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# 函数: 运行用户注册测试 (bash)
run_user_registration_test_bash() {
    if [ "$RUN_DETAILED_TESTS" != "true" ]; then
        print_info "Skipping bash registration test (RUN_DETAILED_TESTS=false)"
        return 0
    fi

    print_header "Running Bash Registration Test"

    local test_script="$PROJECT_ROOT/microservices/auth_service/tests/register_test.sh"

    if [ ! -f "$test_script" ]; then
        print_warning "Bash registration test not found: $test_script"
        ((TESTS_SKIPPED++))
        return 0
    fi

    local test_email="bash_test_$(date +%s)@example.com"
    local test_password="TestPassword123!"

    print_info "Testing with email: $test_email"
    log "Starting bash registration test with email: $test_email"

    # 导出环境变量供脚本使用
    export AUTH_BASE_URL=${AUTH_BASE_URL:-"http://localhost:8201"}
    export VERIFICATION_CODE=${VERIFICATION_CODE:-""}

    if bash "$test_script" "$test_email" "$test_password" "BashTestUser" 2>&1 | tee -a "$TEST_LOG"; then
        print_success "Bash registration test passed"
        log "Bash registration test completed successfully"
        ((TESTS_PASSED++))
        return 0
    else
        print_warning "Bash registration test failed (may need manual verification code)"
        log "Bash registration test failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# 函数: 生成测试报告
generate_test_report() {
    print_header "Test Report"

    local total_tests=$((TESTS_PASSED + TESTS_FAILED))
    local pass_rate=0

    if [ "$total_tests" -gt 0 ]; then
        pass_rate=$((TESTS_PASSED * 100 / total_tests))
    fi

    echo ""
    echo "Test Summary:"
    echo "  Total Tests:    $total_tests"
    echo "  Passed:         $TESTS_PASSED ✓"
    echo "  Failed:         $TESTS_FAILED ✗"
    echo "  Skipped:        $TESTS_SKIPPED ⊘"
    echo "  Pass Rate:      ${pass_rate}%"
    echo ""
    echo "Log File: $TEST_LOG"
    echo ""

    log "Test summary: $TESTS_PASSED passed, $TESTS_FAILED failed, $TESTS_SKIPPED skipped"
}

# 主函数
main() {
    print_header "🚀 Integration Test Suite"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Project: isA_user Microservices"
    echo "Log File: $TEST_LOG"

    log "=== Integration Test Suite Started ==="

    # 1. 检查先决条件
    check_prerequisites

    # 2. 检查服务健���
    if ! check_services_health; then
        print_error "Health check failed. Aborting tests."
        log "Health check failed, tests aborted"
        exit 1
    fi

    # 3. 运行 Python 集成测试 (主测试)
    run_python_integration_test

    # 4. 运行事件流测试
    run_event_flow_test

    # 5. 运行 bash 注册测试 (可选)
    # run_user_registration_test_bash

    # 6. 生成测试报告
    generate_test_report

    log "=== Integration Test Suite Completed ==="

    # 返回退出码
    if [ "$TESTS_FAILED" -eq 0 ]; then
        print_success "All tests passed! 🎉"
        exit 0
    else
        print_error "Some tests failed. Please check the logs."
        exit 1
    fi
}

# 捕获中断信号
trap 'print_warning "Tests interrupted by user"; exit 130' INT TERM

# 运行主函数
main "$@"
