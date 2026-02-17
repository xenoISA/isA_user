#!/bin/bash

# Organization Service Test Data Management Script
# Usage: ./manage_test_data.sh [seed|cleanup]

# Default PostgreSQL connection parameters
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-isa_platform}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-staging_postgres_2024}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to execute SQL file
execute_sql() {
    local sql_file=$1
    echo "Executing: $sql_file"

    if [ ! -f "$sql_file" ]; then
        echo "Error: SQL file not found: $sql_file"
        exit 1
    fi

    PGPASSWORD=$POSTGRES_PASSWORD psql \
        -h $POSTGRES_HOST \
        -p $POSTGRES_PORT \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        -f "$sql_file"

    if [ $? -eq 0 ]; then
        echo "✅ Successfully executed: $sql_file"
    else
        echo "❌ Failed to execute: $sql_file"
        exit 1
    fi
}

# Main script logic
case "$1" in
    seed)
        echo "🌱 Seeding test data for organization service..."
        execute_sql "$SCRIPT_DIR/seed_test_data.sql"
        echo "✅ Test data seeded successfully"
        ;;
    cleanup)
        echo "🧹 Cleaning up test data for organization service..."
        execute_sql "$SCRIPT_DIR/cleanup_test_data.sql"
        echo "✅ Test data cleaned up successfully"
        ;;
    *)
        echo "Usage: $0 {seed|cleanup}"
        echo ""
        echo "Commands:"
        echo "  seed    - Insert test data into the database"
        echo "  cleanup - Remove test data from the database"
        echo ""
        echo "Environment variables:"
        echo "  POSTGRES_HOST     (default: localhost)"
        echo "  POSTGRES_PORT     (default: 5432)"
        echo "  POSTGRES_DB       (default: isa_platform)"
        echo "  POSTGRES_USER     (default: postgres)"
        echo "  POSTGRES_PASSWORD (default: staging_postgres_2024)"
        exit 1
        ;;
esac

exit 0
