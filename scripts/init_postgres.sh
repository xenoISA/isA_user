#!/bin/bash
# PostgreSQL Database Initialization Script for ISA Platform
# This script initializes all microservice schemas and runs migrations
# Version: 2.0.0
# Date: 2025-11-22
#
# Usage:
#   ./init_postgres.sh                    # Initialize schema only
#   ./init_postgres.sh --with-seed-data   # Initialize schema + test data
#   ./init_postgres.sh --cleanup          # Cleanup all test data

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-isa_platform}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MICROSERVICES_DIR="${PROJECT_ROOT}/microservices"

# Script options
LOAD_SEED_DATA=false
CLEANUP_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-seed-data)
            LOAD_SEED_DATA=true
            shift
            ;;
        --cleanup)
            CLEANUP_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-seed-data    Load test data after schema initialization"
            echo "  --cleanup           Cleanup all test data"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DB_HOST            Database host (default: localhost)"
            echo "  DB_PORT            Database port (default: 5432)"
            echo "  DB_NAME            Database name (default: isa_platform)"
            echo "  DB_USER            Database user (default: postgres)"
            echo "  DB_PASSWORD        Database password"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to execute SQL file
execute_sql_file() {
    local sql_file=$1
    local description=$2

    print_message "$BLUE" "  → Executing: $(basename $sql_file)"

    if [ -n "$DB_PASSWORD" ]; then
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$sql_file" 2>&1 | grep -v "^$" || true
    else
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$sql_file" 2>&1 | grep -v "^$" || true
    fi

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_message "$GREEN" "    ✓ $description"
        return 0
    else
        print_message "$RED" "    ✗ Failed: $description"
        return 1
    fi
}

# Function to execute SQL command
execute_sql() {
    local sql_command=$1
    local description=$2

    if [ -n "$description" ]; then
        print_message "$BLUE" "  → $description"
    fi

    if [ -n "$DB_PASSWORD" ]; then
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "$sql_command" > /dev/null 2>&1
    else
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "$sql_command" > /dev/null 2>&1
    fi

    if [ $? -eq 0 ]; then
        if [ -n "$description" ]; then
            print_message "$GREEN" "    ✓ Success"
        fi
        return 0
    else
        if [ -n "$description" ]; then
            print_message "$RED" "    ✗ Failed"
        fi
        return 1
    fi
}

# Function to check if database exists
check_database() {
    print_message "$YELLOW" "\n=== Checking Database Connection ==="

    if [ -n "$DB_PASSWORD" ]; then
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\q" > /dev/null 2>&1
    else
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\q" > /dev/null 2>&1
    fi

    if [ $? -ne 0 ]; then
        print_message "$RED" "✗ Cannot connect to PostgreSQL server"
        exit 1
    fi

    print_message "$GREEN" "✓ Connected to PostgreSQL server"

    # Check if database exists
    if [ -n "$DB_PASSWORD" ]; then
        DB_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
    else
        DB_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
    fi

    if [ "$DB_EXISTS" != "1" ]; then
        print_message "$YELLOW" "Database '$DB_NAME' does not exist. Creating..."
        if [ -n "$DB_PASSWORD" ]; then
            PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" > /dev/null 2>&1
        else
            psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" > /dev/null 2>&1
        fi
        print_message "$GREEN" "✓ Database '$DB_NAME' created"
    else
        print_message "$GREEN" "✓ Database '$DB_NAME' exists"
    fi
}

# Function to create base schema and functions
create_base_schema() {
    print_message "$YELLOW" "\n=== Creating Base Schema and Functions ==="

    # Create public schema helper function (used by many services)
    execute_sql "
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS \$\$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
\$\$ LANGUAGE plpgsql;
" "Creating public.update_updated_at_column() function"

    # Create authenticated role (used by storage and other services)
    execute_sql "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated;
    END IF;
END
\$\$;
" "Creating 'authenticated' role"

    print_message "$GREEN" "✓ Base schema and functions created"
}

# Function to filter and sort migration files
get_migration_files() {
    local service_dir=$1
    local include_seed=$2
    local migrations_dir="${service_dir}/migrations"

    if [ ! -d "$migrations_dir" ]; then
        return
    fi

    # Get all SQL files, excluding deprecated and helper files
    local all_files=$(find "$migrations_dir" -maxdepth 1 -name "*.sql" ! -name "*.deprecated" ! -name "*.old" ! -name "*.backup" 2>/dev/null | sort -V)

    for file in $all_files; do
        local filename=$(basename "$file")

        # Skip deprecated/helper files
        if [[ "$filename" == *".deprecated"* ]] || \
           [[ "$filename" == *".old"* ]] || \
           [[ "$filename" == *".backup"* ]]; then
            continue
        fi

        # Handle seed data based on flag
        if [[ "$filename" == *"seed_test_data"* ]] || \
           [[ "$filename" == *"cleanup_test_data"* ]] || \
           [[ "$filename" == *"insert_test_data"* ]]; then
            if [ "$include_seed" = "true" ]; then
                echo "$file"
            fi
        else
            # Include all schema migration files
            echo "$file"
        fi
    done
}

# Function to run migrations for a microservice
run_migrations() {
    local service_name=$1
    local include_seed=${2:-false}
    local service_dir="${MICROSERVICES_DIR}/${service_name}"

    if [ ! -d "$service_dir/migrations" ]; then
        print_message "$YELLOW" "  ⚠ No migrations directory found for $service_name"
        return 0
    fi

    print_message "$CYAN" "\n→ Running migrations for: $service_name"

    # Get sorted migration files
    local migration_files=$(get_migration_files "$service_dir" "$include_seed")

    if [ -z "$migration_files" ]; then
        print_message "$YELLOW" "  ⚠ No migration files found for $service_name"
        return 0
    fi

    # Execute each migration file
    local count=0
    for migration_file in $migration_files; do
        local filename=$(basename "$migration_file")
        execute_sql_file "$migration_file" "$filename" && ((count++)) || true
    done

    print_message "$GREEN" "  ✓ Completed $count migrations for $service_name"
}

# Function to run cleanup for a microservice
run_cleanup() {
    local service_name=$1
    local service_dir="${MICROSERVICES_DIR}/${service_name}"
    local cleanup_file="${service_dir}/migrations/cleanup_test_data.sql"

    if [ ! -f "$cleanup_file" ]; then
        return 0
    fi

    print_message "$CYAN" "\n→ Cleaning up test data for: $service_name"
    execute_sql_file "$cleanup_file" "cleanup_test_data.sql" || true
}

# Function to run migrations in dependency order
run_all_migrations() {
    print_message "$YELLOW" "\n=== Running Microservice Migrations ==="

    # Phase 1: Core identity and authentication services (no dependencies)
    print_message "$MAGENTA" "\n━━━ Phase 1: Core Identity & Authentication Services ━━━"
    run_migrations "auth_service" "$LOAD_SEED_DATA"
    run_migrations "account_service" "$LOAD_SEED_DATA"
    run_migrations "authorization_service" "$LOAD_SEED_DATA"
    run_migrations "organization_service" "$LOAD_SEED_DATA"

    # Phase 2: Foundation services (depend on auth)
    print_message "$MAGENTA" "\n━━━ Phase 2: Foundation Services ━━━"
    run_migrations "device_service" "$LOAD_SEED_DATA"
    run_migrations "session_service" "$LOAD_SEED_DATA"
    run_migrations "event_service" "$LOAD_SEED_DATA"

    # Phase 3: Business logic services
    print_message "$MAGENTA" "\n━━━ Phase 3: Business Logic Services ━━━"
    run_migrations "product_service" "$LOAD_SEED_DATA"
    run_migrations "wallet_service" "$LOAD_SEED_DATA"
    run_migrations "payment_service" "$LOAD_SEED_DATA"
    run_migrations "billing_service" "$LOAD_SEED_DATA"
    run_migrations "order_service" "$LOAD_SEED_DATA"

    # Phase 4: Storage and media services (files must come before album/media)
    print_message "$MAGENTA" "\n━━━ Phase 4: Storage & Media Services ━━━"
    run_migrations "storage_service" "$LOAD_SEED_DATA"
    run_migrations "media_service" "$LOAD_SEED_DATA"
    run_migrations "album_service" "$LOAD_SEED_DATA"

    # Phase 5: AI and intelligence services
    print_message "$MAGENTA" "\n━━━ Phase 5: AI & Intelligence Services ━━━"
    run_migrations "memory_service" "$LOAD_SEED_DATA"

    # Phase 6: Integration and support services
    print_message "$MAGENTA" "\n━━━ Phase 6: Integration & Support Services ━━━"
    run_migrations "notification_service" "$LOAD_SEED_DATA"
    run_migrations "calendar_service" "$LOAD_SEED_DATA"
    run_migrations "location_service" "$LOAD_SEED_DATA"
    run_migrations "weather_service" "$LOAD_SEED_DATA"
    run_migrations "invitation_service" "$LOAD_SEED_DATA"

    # Phase 7: Infrastructure and operations services
    print_message "$MAGENTA" "\n━━━ Phase 7: Infrastructure & Operations Services ━━━"
    run_migrations "task_service" "$LOAD_SEED_DATA"
    run_migrations "ota_service" "$LOAD_SEED_DATA"
    run_migrations "telemetry_service" "$LOAD_SEED_DATA"
    run_migrations "audit_service" "$LOAD_SEED_DATA"
    run_migrations "compliance_service" "$LOAD_SEED_DATA"
    run_migrations "vault_service" "$LOAD_SEED_DATA"

    # Phase 8: Optional services (if they exist)
    print_message "$MAGENTA" "\n━━━ Phase 8: Optional Services ━━━"
    [ -d "${MICROSERVICES_DIR}/document_service" ] && run_migrations "document_service" "$LOAD_SEED_DATA" || true
}

# Function to cleanup all test data in reverse order
cleanup_all_test_data() {
    print_message "$YELLOW" "\n=== Cleaning Up All Test Data ==="
    print_message "$RED" "⚠ This will remove ALL test data from the database!"

    # Cleanup in reverse order of dependencies
    print_message "$MAGENTA" "\n━━━ Cleanup Phase 1: Dependent Services ━━━"
    run_cleanup "album_service"
    run_cleanup "media_service"
    run_cleanup "storage_service"

    print_message "$MAGENTA" "\n━━━ Cleanup Phase 2: Business Services ━━━"
    run_cleanup "notification_service"
    run_cleanup "event_service"
    run_cleanup "session_service"
    run_cleanup "task_service"
    run_cleanup "order_service"
    run_cleanup "wallet_service"
    run_cleanup "payment_service"
    run_cleanup "product_service"

    print_message "$MAGENTA" "\n━━━ Cleanup Phase 3: Device & Organization ━━━"
    run_cleanup "device_service"
    run_cleanup "authorization_service"
    run_cleanup "organization_service"

    print_message "$MAGENTA" "\n━━━ Cleanup Phase 4: Core Services ━━━"
    run_cleanup "auth_service"
    run_cleanup "account_service"

    print_message "$GREEN" "\n✓ Test data cleanup completed"
}

# Function to verify schemas
verify_schemas() {
    print_message "$YELLOW" "\n=== Verifying Database Schemas ==="

    local expected_schemas=(
        "account"
        "album"
        "audit"
        "auth"
        "authz"
        "billing"
        "calendar"
        "compliance"
        "device"
        "event"
        "invitation"
        "location"
        "media"
        "memory"
        "notification"
        "orders"
        "organization"
        "ota"
        "payment"
        "product"
        "session"
        "storage"
        "task"
        "telemetry"
        "vault"
        "wallet"
        "weather"
    )

    local found=0
    local missing=0

    for schema in "${expected_schemas[@]}"; do
        if [ -n "$DB_PASSWORD" ]; then
            SCHEMA_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT 1 FROM information_schema.schemata WHERE schema_name='$schema'")
        else
            SCHEMA_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT 1 FROM information_schema.schemata WHERE schema_name='$schema'")
        fi

        if [ "$SCHEMA_EXISTS" = "1" ]; then
            print_message "$GREEN" "  ✓ Schema: $schema"
            ((found++))
        else
            print_message "$YELLOW" "  ⚠ Schema not found: $schema"
            ((missing++))
        fi
    done

    print_message "$CYAN" "\n  Summary: $found schemas found, $missing missing"
}

# Function to display statistics
display_statistics() {
    print_message "$YELLOW" "\n=== Database Statistics ==="

    # Count schemas
    if [ -n "$DB_PASSWORD" ]; then
        SCHEMA_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')")
        TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')")
        FUNCTION_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema NOT IN ('pg_catalog', 'information_schema')")
    else
        SCHEMA_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')")
        TABLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')")
        FUNCTION_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema NOT IN ('pg_catalog', 'information_schema')")
    fi

    print_message "$BLUE" "  Database: $DB_NAME"
    print_message "$BLUE" "  Schemas: $SCHEMA_COUNT"
    print_message "$BLUE" "  Tables: $TABLE_COUNT"
    print_message "$BLUE" "  Functions: $FUNCTION_COUNT"
}

# Main execution
main() {
    print_message "$GREEN" "╔════════════════════════════════════════════════════════════════╗"
    print_message "$GREEN" "║     ISA Platform - PostgreSQL Database Initialization         ║"
    print_message "$GREEN" "╚════════════════════════════════════════════════════════════════╝"

    print_message "$CYAN" "\nConfiguration:"
    print_message "$CYAN" "  Database Host: $DB_HOST"
    print_message "$CYAN" "  Database Port: $DB_PORT"
    print_message "$CYAN" "  Database Name: $DB_NAME"
    print_message "$CYAN" "  Database User: $DB_USER"
    print_message "$CYAN" "  Project Root: $PROJECT_ROOT"
    print_message "$CYAN" "  Load Seed Data: $LOAD_SEED_DATA"
    print_message "$CYAN" "  Cleanup Mode: $CLEANUP_MODE"

    # Check database connection
    check_database

    if [ "$CLEANUP_MODE" = "true" ]; then
        # Cleanup mode
        cleanup_all_test_data
    else
        # Normal initialization mode
        # Create base schema
        create_base_schema

        # Run all migrations
        run_all_migrations

        # Verify schemas
        verify_schemas

        # Display statistics
        display_statistics
    fi

    print_message "$GREEN" "\n╔════════════════════════════════════════════════════════════════╗"
    if [ "$CLEANUP_MODE" = "true" ]; then
        print_message "$GREEN" "║          Test Data Cleanup Completed Successfully              ║"
    else
        print_message "$GREEN" "║          Database Initialization Completed Successfully        ║"
    fi
    print_message "$GREEN" "╚════════════════════════════════════════════════════════════════╝\n"
}

# Run main function
main "$@"
