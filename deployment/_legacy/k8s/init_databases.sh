#!/bin/bash

# ============================================================================
# Database Initialization Script for All Microservices (K8s)
# ============================================================================
# This script initializes all PostgreSQL databases for microservices
# Each service uses its own schema (account, auth, wallet, etc.)
#
# Usage:
#   Kubernetes:  ./init_databases.sh
#   Dry-run:     DRY_RUN=true ./init_databases.sh
#
# Environment Variables:
#   POSTGRES_HOST     - PostgreSQL host (default: localhost via port-forward)
#   POSTGRES_PORT     - PostgreSQL port (default: 5432)
#   POSTGRES_USER     - PostgreSQL user (default: postgres)
#   POSTGRES_PASSWORD - PostgreSQL password (default: postgres)
#   POSTGRES_DB       - PostgreSQL database name (default: postgres)
#   DRY_RUN           - Set to 'true' for dry-run mode
# ============================================================================

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-isa_platform}"
DRY_RUN="${DRY_RUN:-false}"

export PGPASSWORD="$POSTGRES_PASSWORD"

# Navigate to project root
cd "$(dirname "$0")/../.."

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}PostgreSQL Database Initialization for isA Microservices${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}🔍 DRY-RUN MODE - No changes will be made${NC}"
    echo ""
fi

echo -e "${CYAN}📊 Configuration:${NC}"
echo "   Host:     $POSTGRES_HOST"
echo "   Port:     $POSTGRES_PORT"
echo "   User:     $POSTGRES_USER"
echo "   Database: $POSTGRES_DB"
echo ""

# ============================================================================
# Helper Functions
# ============================================================================

execute_sql_file() {
    local file="$1"
    local display_name="$2"

    if [ "$DRY_RUN" = "true" ]; then
        echo -e "    ${YELLOW}[DRY-RUN]${NC} Would execute: $display_name"
        return 0
    fi

    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" -f "$file" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_connection() {
    echo -e "${BLUE}🔍 Testing database connection...${NC}"

    if [ "$DRY_RUN" = "true" ]; then
        echo -e "${YELLOW}[DRY-RUN] Skipping connection test${NC}"
        return 0
    fi

    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Database connection successful${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to connect to database${NC}"
        echo ""
        echo -e "${YELLOW}💡 For Kubernetes, run this in another terminal:${NC}"
        echo -e "${CYAN}   kubectl port-forward -n isa-cloud-staging svc/postgres 5432:5432${NC}"
        echo ""
        return 1
    fi
}

# ============================================================================
# Check Prerequisites
# ============================================================================

if ! check_connection; then
    exit 1
fi

echo ""

# ============================================================================
# Service Migration Order
# ============================================================================
# Services are listed in dependency order where possible
# Core identity/auth services first, then dependent services

declare -a SERVICES=(
    # Core identity & auth
    "account_service"
    "auth_service"
    "authorization_service"

    # Core platform services
    "session_service"
    "device_service"
    "organization_service"

    # Financial services
    "wallet_service"
    "payment_service"
    "billing_service"
    "order_service"
    "product_service"

    # Storage & media
    "storage_service"
    "album_service"
    "media_service"
    "memory_service"

    # Communication & events
    "notification_service"
    "event_service"
    "task_service"
    "invitation_service"

    # Additional services
    "vault_service"
    "calendar_service"
    "weather_service"
    "location_service"
    "audit_service"
    "compliance_service"
    "ota_service"
    "telemetry_service"
)

# ============================================================================
# Run Migrations
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Running Database Migrations${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

TOTAL_SERVICES=${#SERVICES[@]}
CURRENT=0
SUCCESS_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

for service in "${SERVICES[@]}"; do
    ((CURRENT++))
    MIGRATION_DIR="microservices/$service/migrations"

    # Check if migration directory exists
    if [ ! -d "$MIGRATION_DIR" ]; then
        echo -e "${YELLOW}[$CURRENT/$TOTAL_SERVICES] ⚠  $service: No migrations directory${NC}"
        ((SKIP_COUNT++))
        continue
    fi

    echo ""
    echo -e "${BLUE}[$CURRENT/$TOTAL_SERVICES] 🔨 Processing $service...${NC}"

    # Get all SQL migration files (sorted, exclude seed/cleanup/test)
    MIGRATION_FILES=$(find "$MIGRATION_DIR" -maxdepth 1 -name "*.sql" \
        ! -name "*seed*" \
        ! -name "*cleanup*" \
        ! -name "*test*" \
        | sort)

    if [ -z "$MIGRATION_FILES" ]; then
        echo -e "  ${YELLOW}⚠  No migration files found${NC}"
        ((SKIP_COUNT++))
        continue
    fi

    FILE_COUNT=$(echo "$MIGRATION_FILES" | wc -l | tr -d ' ')
    echo -e "  ${CYAN}📄 Found $FILE_COUNT migration file(s)${NC}"

    SERVICE_SUCCESS=true

    for file in $MIGRATION_FILES; do
        filename=$(basename "$file")
        echo -n "    → $filename ... "

        if execute_sql_file "$file" "$filename"; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗ Failed${NC}"
            SERVICE_SUCCESS=false
        fi
    done

    if [ "$SERVICE_SUCCESS" = true ]; then
        echo -e "  ${GREEN}✓ $service completed successfully${NC}"
        ((SUCCESS_COUNT++))
    else
        echo -e "  ${RED}✗ $service had errors${NC}"
        ((FAIL_COUNT++))
    fi
done

# ============================================================================
# Seed Test Data (Optional)
# ============================================================================

echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Seed Test Data${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}[DRY-RUN] Skipping test data seeding${NC}"
else
    read -p "Do you want to seed test data? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Seeding test data...${NC}"

        SEED_COUNT=0
        for service in "${SERVICES[@]}"; do
            SEED_FILE="microservices/$service/migrations/seed_test_data.sql"

            if [ -f "$SEED_FILE" ]; then
                echo -n "  → $service ... "
                if execute_sql_file "$SEED_FILE" "seed_test_data.sql"; then
                    echo -e "${GREEN}✓${NC}"
                    ((SEED_COUNT++))
                else
                    echo -e "${YELLOW}⚠ (may already exist)${NC}"
                fi
            fi
        done

        echo -e "${GREEN}✓ Seeded test data for $SEED_COUNT services${NC}"
    else
        echo -e "${YELLOW}Skipping test data seeding${NC}"
    fi
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Migration Summary${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Get schema count
if [ "$DRY_RUN" != "true" ]; then
    SCHEMA_COUNT=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public');" | tr -d ' ')

    TABLE_COUNT=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'public');" | tr -d ' ')
else
    SCHEMA_COUNT="N/A (dry-run)"
    TABLE_COUNT="N/A (dry-run)"
fi

echo -e "  ${GREEN}✓ Success:${NC}  $SUCCESS_COUNT services"
echo -e "  ${YELLOW}⚠ Skipped:${NC} $SKIP_COUNT services"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "  ${RED}✗ Failed:${NC}  $FAIL_COUNT services"
fi
echo ""
echo -e "  ${CYAN}Schemas:${NC}   $SCHEMA_COUNT"
echo -e "  ${CYAN}Tables:${NC}    $TABLE_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}🎉 Database initialization completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some migrations failed. Please review the output above.${NC}"
    exit 1
fi
