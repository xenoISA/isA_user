#!/bin/bash
# Product Service Migration Runner
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER="staging-postgres"
DB_USER="postgres"
DB_NAME="isa_platform"

echo "========================================="
echo "Running Product Service Migrations"
echo "========================================="
echo ""

for migration in "$SCRIPT_DIR"/00*.sql; do
    if [ -f "$migration" ]; then
        filename=$(basename "$migration")
        echo "Running: $filename"
        docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$migration"
        echo "✓ $filename completed"
        echo ""
    fi
done

echo "========================================="
echo "All migrations completed!"
echo "========================================="
