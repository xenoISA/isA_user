#!/bin/bash

################################################################################
# isA User Microservices - 统一测试运行器
#
# 功能：自动发现并运行所有微服务的测试脚本
# 用法：
#   ./run_all_microservices_tests.sh              # 运行所有测试
#   ./run_all_microservices_tests.sh --service auth_service  # 只运行指定服务
#   ./run_all_microservices_tests.sh --stop-on-fail  # 遇到失败立即停止
#   ./run_all_microservices_tests.sh --parallel   # 并行运行测试(实验性)
################################################################################

# Removed set -e to allow tests to continue even if some fail
# set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 工作目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MICROSERVICES_DIR="$PROJECT_ROOT/microservices"

# 测试统计
TOTAL_SERVICES=0
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# 选项
STOP_ON_FAIL=false
SPECIFIC_SERVICE=""
PARALLEL_MODE=false
VERBOSE=false

# 日志目录
LOG_DIR="$PROJECT_ROOT/tests/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SUMMARY_LOG="$LOG_DIR/test_summary_${TIMESTAMP}.log"

################################################################################
# 辅助函数
################################################################################

print_header() {
    echo ""
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_service_header() {
    local service=$1
    local test_count=$2
    echo ""
    echo -e "${BLUE}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}${BOLD}║  📦 Service: ${service}${NC}"
    echo -e "${BLUE}${BOLD}║  📝 Tests: ${test_count}${NC}"
    echo -e "${BLUE}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_test_running() {
    local test_file=$1
    echo -e "${YELLOW}▶ Running: ${test_file}${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_skip() {
    echo -e "${MAGENTA}⏭️  $1${NC}"
}

################################################################################
# 解析命令行参数
################################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --service)
            SPECIFIC_SERVICE="$2"
            shift 2
            ;;
        --stop-on-fail)
            STOP_ON_FAIL=true
            shift
            ;;
        --parallel)
            PARALLEL_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --service <name>    只运行指定服务的测试"
            echo "  --stop-on-fail      遇到失败立即停止"
            echo "  --parallel          并行运行测试(实验性)"
            echo "  --verbose, -v       显示详细输出"
            echo "  --help, -h          显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                           # 运行所有测试"
            echo "  $0 --service auth_service    # 只测试 auth_service"
            echo "  $0 --stop-on-fail            # 失败时停止"
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

################################################################################
# 运行单个测试脚本
################################################################################

run_test_script() {
    local service=$1
    local test_script=$2
    local test_name=$(basename "$test_script" .sh)
    local log_file="$LOG_DIR/${service}_${test_name}_${TIMESTAMP}.log"

    print_test_running "$test_name"

    # 运行测试并捕获输出
    if $VERBOSE; then
        bash "$test_script" 2>&1 | tee "$log_file"
        local exit_code=${PIPESTATUS[0]}
    else
        # 使用管道避免输出缓冲问题
        bash "$test_script" 2>&1 | cat > "$log_file"
        local exit_code=${PIPESTATUS[0]}
    fi

    if [ $exit_code -eq 0 ]; then
        print_success "PASSED: $test_name"
        ((PASSED_TESTS++))
        echo "✅ PASSED: $service/$test_name" >> "$SUMMARY_LOG"
        return 0
    else
        print_error "FAILED: $test_name (exit code: $exit_code)"
        print_error "  Log: $log_file"
        ((FAILED_TESTS++))
        echo "❌ FAILED: $service/$test_name (exit code: $exit_code)" >> "$SUMMARY_LOG"

        # 显示失败日志的最后几行
        if [ -f "$log_file" ]; then
            echo -e "${RED}  Last 5 lines of log:${NC}"
            tail -5 "$log_file" | sed 's/^/    /'
        fi

        if $STOP_ON_FAIL; then
            print_error "停止测试 (--stop-on-fail enabled)"
            exit 1
        fi
        return 1
    fi
}

################################################################################
# 运行服务的所有测试
################################################################################

run_service_tests() {
    local service=$1
    local tests_dir="$MICROSERVICES_DIR/$service/tests"

    if [ ! -d "$tests_dir" ]; then
        print_skip "Service $service has no tests directory"
        return
    fi

    # 查找所有测试脚本 (排除一些辅助脚本)
    local test_scripts=()
    while IFS= read -r -d '' script; do
        local basename=$(basename "$script")
        # 跳过某些辅助脚本
        if [[ "$basename" != "debug_"* ]] && [[ "$basename" != "run_all_tests.sh" ]]; then
            test_scripts+=("$script")
        fi
    done < <(find "$tests_dir" -maxdepth 1 -name "*.sh" -type f -print0 | sort -z)

    local test_count=${#test_scripts[@]}

    if [ $test_count -eq 0 ]; then
        print_skip "Service $service has no test scripts"
        return
    fi

    print_service_header "$service" "$test_count"
    ((TOTAL_SERVICES++))

    # 运行所有测试
    for test_script in "${test_scripts[@]}"; do
        ((TOTAL_TESTS++))

        # 确保脚本可执行
        chmod +x "$test_script"

        # 切换到服务目录运行测试
        cd "$MICROSERVICES_DIR/$service/tests"
        run_test_script "$service" "$test_script"
        cd "$PROJECT_ROOT"
    done
}

################################################################################
# 主程序
################################################################################

main() {
    print_header "isA User Microservices - 测试运行器"

    echo -e "${CYAN}开始时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${CYAN}项目路径: $PROJECT_ROOT${NC}"
    echo -e "${CYAN}日志目录: $LOG_DIR${NC}"
    echo ""

    # 初始化摘要日志
    echo "isA User Microservices - 测试运行摘要" > "$SUMMARY_LOG"
    echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_LOG"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$SUMMARY_LOG"
    echo "" >> "$SUMMARY_LOG"

    # 获取所有服务列表
    local services=()
    if [ -n "$SPECIFIC_SERVICE" ]; then
        # 只运行指定服务
        if [ -d "$MICROSERVICES_DIR/$SPECIFIC_SERVICE" ]; then
            services=("$SPECIFIC_SERVICE")
            print_info "只运行服务: $SPECIFIC_SERVICE"
        else
            print_error "服务不存在: $SPECIFIC_SERVICE"
            exit 1
        fi
    else
        # 运行所有服务
        while IFS= read -r -d '' dir; do
            local service=$(basename "$dir")
            services+=("$service")
        done < <(find "$MICROSERVICES_DIR" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
    fi

    print_info "发现 ${#services[@]} 个微服务"
    echo ""

    # 运行所有服务的测试
    for service in "${services[@]}"; do
        run_service_tests "$service"
    done

    # 生成测试报告
    print_header "测试报告"

    local end_time=$(date '+%Y-%m-%d %H:%M:%S')

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$SUMMARY_LOG"
    echo "" >> "$SUMMARY_LOG"

    echo -e "${BOLD}统计信息:${NC}"
    echo -e "  测试的服务数: ${CYAN}$TOTAL_SERVICES${NC}"
    echo -e "  测试脚本总数: ${CYAN}$TOTAL_TESTS${NC}"
    echo -e "  通过的测试:   ${GREEN}$PASSED_TESTS${NC}"
    echo -e "  失败的测试:   ${RED}$FAILED_TESTS${NC}"
    echo -e "  跳过的测试:   ${YELLOW}$SKIPPED_TESTS${NC}"
    echo ""

    echo "统计信息:" >> "$SUMMARY_LOG"
    echo "  测试的服务数: $TOTAL_SERVICES" >> "$SUMMARY_LOG"
    echo "  测试脚本总数: $TOTAL_TESTS" >> "$SUMMARY_LOG"
    echo "  通过的测试:   $PASSED_TESTS" >> "$SUMMARY_LOG"
    echo "  失败的测试:   $FAILED_TESTS" >> "$SUMMARY_LOG"
    echo "  跳过的测试:   $SKIPPED_TESTS" >> "$SUMMARY_LOG"
    echo "" >> "$SUMMARY_LOG"

    if [ $TOTAL_TESTS -gt 0 ]; then
        local success_rate=$(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)
        echo -e "  成功率:       ${CYAN}${success_rate}%${NC}"
        echo "  成功率:       ${success_rate}%" >> "$SUMMARY_LOG"
    fi

    echo ""
    echo -e "${CYAN}结束时间: $end_time${NC}"
    echo -e "${CYAN}摘要日志: $SUMMARY_LOG${NC}"
    echo ""

    echo "结束时间: $end_time" >> "$SUMMARY_LOG"

    # 返回退出码
    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "所有测试通过! 🎉"
        return 0
    else
        print_error "有 $FAILED_TESTS 个测试失败"
        return 1
    fi
}

# 运行主程序
main
exit $?
