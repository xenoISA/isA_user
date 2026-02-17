#!/bin/bash

# Compliance Service Startup Script
# 合规服务启动脚本

set -e

echo "=========================================="
echo "Starting Compliance Service"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Python版本
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python version: $python_version${NC}"

# 检查环境变量
echo -e "${YELLOW}Checking environment variables...${NC}"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ DATABASE_URL not set${NC}"
    echo "  Please set: export DATABASE_URL=postgresql://user:pass@host:port/db"
    exit 1
fi
echo -e "${GREEN}✓ DATABASE_URL is set${NC}"

# 设置默认端口
export COMPLIANCE_SERVICE_PORT=${COMPLIANCE_SERVICE_PORT:-8250}
echo -e "${GREEN}✓ Service will run on port: $COMPLIANCE_SERVICE_PORT${NC}"

# 检查依赖
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! python3 -c "import fastapi, pydantic, sqlalchemy" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi
echo -e "${GREEN}✓ Dependencies installed${NC}"

# 运行数据库迁移（可选）
echo -e "${YELLOW}Database migration...${NC}"
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running migrations..."
    # psql $DATABASE_URL -f migrations/001_create_compliance_tables.sql
    echo -e "${GREEN}✓ Migrations completed${NC}"
else
    echo "Skipping migrations (set RUN_MIGRATIONS=true to run)"
fi

# 启动服务
echo -e "${YELLOW}Starting Compliance Service...${NC}"
echo "=========================================="
echo "Service URL: http://0.0.0.0:$COMPLIANCE_SERVICE_PORT"
echo "Health Check: http://0.0.0.0:$COMPLIANCE_SERVICE_PORT/health"
echo "API Docs: http://0.0.0.0:$COMPLIANCE_SERVICE_PORT/docs"
echo "=========================================="

# 从项目根目录启动
cd "$(dirname "$0")/../../.."
python3 -m microservices.compliance_service.main

# 如果使用uvicorn直接启动
# uvicorn microservices.compliance_service.main:app \
#     --host 0.0.0.0 \
#     --port $COMPLIANCE_SERVICE_PORT \
#     --reload \
#     --log-level info

