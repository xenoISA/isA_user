#!/usr/bin/env bash
#
# 服务健康检查脚本
#
# 检查所有微服务是否正常运行
#
# 使用方式:
#   ./check_services_health.sh
#
# 环境变量:
#   CHECK_DETAILED - 是否检查详细健康状态 (true/false, 默认: false)
#

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
CHECK_DETAILED=${CHECK_DETAILED:-false}

# 服务列表 (服务名:端口:基础路径)
SERVICES=(
    "auth_service:8201:/api/v1/auth"
    "account_service:8202:/api/v1/accounts"
    "device_service:8203:/api/v1/devices"
    "organization_service:8204:/api/v1/organizations"
    "session_service:8205:/api/v1/sessions"
    "notification_service:8206:/api/v1/notifications"
)

# 基础设施服务
INFRA_SERVICES=(
    "PostgreSQL:5432"
    "NATS:4222"
    "Consul:8500"
)

echo "================================================================================"
echo "🏥 Service Health Check"
echo "================================================================================"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# 检查基础设施服务
echo "📋 Checking Infrastructure Services..."
echo "--------------------------------------------------------------------------------"

INFRA_HEALTHY=0
INFRA_TOTAL=${#INFRA_SERVICES[@]}

for service_info in "${INFRA_SERVICES[@]}"; do
    IFS=':' read -r service_name port <<< "$service_info"

    printf "%-20s " "$service_name:"

    if nc -z localhost "$port" 2>/dev/null; then
        echo -e "${GREEN}✓ Running${NC} (port $port)"
        ((INFRA_HEALTHY++))
    else
        echo -e "${RED}✗ Not responding${NC} (port $port)"
    fi
done

echo ""
echo "Infrastructure Status: $INFRA_HEALTHY/$INFRA_TOTAL services healthy"
echo ""

# 检查微服务
echo "📋 Checking Microservices..."
echo "--------------------------------------------------------------------------------"

SERVICES_HEALTHY=0
SERVICES_TOTAL=${#SERVICES[@]}

for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r service_name port base_path <<< "$service_info"

    printf "%-25s " "$service_name:"

    # 基础健康检查
    health_url="http://localhost:${port}/health"

    if response=$(curl -sf "$health_url" 2>/dev/null); then
        echo -e "${GREEN}✓ Healthy${NC}"
        ((SERVICES_HEALTHY++))

        # 详细检查
        if [ "$CHECK_DETAILED" = "true" ]; then
            detailed_url="http://localhost:${port}/health/detailed"
            if detailed_response=$(curl -sf "$detailed_url" 2>/dev/null); then
                echo "  └─ Detailed:"
                echo "$detailed_response" | jq -r '
                    "    Database: \(.database // "N/A") | " +
                    "NATS: \(.nats // .event_bus // "N/A") | " +
                    "Consul: \(.consul // .service_discovery // "N/A")"
                ' 2>/dev/null || echo "    (Details not available in JSON format)"
            fi
        fi
    else
        echo -e "${RED}✗ Unhealthy or not responding${NC}"

        # 尝试检查端口是否开放
        if nc -z localhost "$port" 2>/dev/null; then
            echo "  └─ Port $port is open but /health endpoint failed"
        else
            echo "  └─ Port $port is not responding"
        fi
    fi
done

echo ""
echo "Microservices Status: $SERVICES_HEALTHY/$SERVICES_TOTAL services healthy"
echo ""

# 总结
echo "================================================================================"
echo "📊 Health Check Summary"
echo "================================================================================"

TOTAL_HEALTHY=$((INFRA_HEALTHY + SERVICES_HEALTHY))
TOTAL_SERVICES=$((INFRA_TOTAL + SERVICES_TOTAL))

echo "Infrastructure: $INFRA_HEALTHY/$INFRA_TOTAL"
echo "Microservices:  $SERVICES_HEALTHY/$SERVICES_TOTAL"
echo "Total:          $TOTAL_HEALTHY/$TOTAL_SERVICES"
echo ""

if [ "$TOTAL_HEALTHY" -eq "$TOTAL_SERVICES" ]; then
    echo -e "${GREEN}✅ All services are healthy!${NC}"
    echo ""
    exit 0
elif [ "$INFRA_HEALTHY" -lt "$INFRA_TOTAL" ]; then
    echo -e "${RED}❌ Infrastructure services are not all healthy${NC}"
    echo "   Please ensure PostgreSQL, NATS, and Consul are running"
    echo ""
    exit 1
elif [ "$SERVICES_HEALTHY" -lt "$SERVICES_TOTAL" ]; then
    echo -e "${YELLOW}⚠️  Some microservices are not healthy${NC}"
    echo "   $((SERVICES_TOTAL - SERVICES_HEALTHY)) service(s) need attention"
    echo ""
    exit 1
else
    echo -e "${YELLOW}⚠️  Partial system health${NC}"
    echo ""
    exit 1
fi
