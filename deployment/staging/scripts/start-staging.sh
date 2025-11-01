#!/bin/bash

# ==========================================
# isA User Platform - Staging Container Startup Script
# ==========================================
# This script starts all microservices in a single Docker container

set -e

echo "============================================"
echo "Starting isA User Platform - Staging"
echo "Environment: ${ENVIRONMENT:-staging}"
echo "============================================"

# Set Python path
export PYTHONPATH=/app

# Display essential environment variables for debugging
echo "Configuration:"
echo "  CONSUL_HOST: ${CONSUL_HOST:-localhost}"
echo "  CONSUL_PORT: ${CONSUL_PORT:-8500}"
echo "  DATABASE_URL: ${DATABASE_URL:0:30}..." # Show only first 30 chars for security
echo "  SUPABASE_URL: ${SUPABASE_URL:-not set}"

# Wait for Consul to be ready
echo "Waiting for Consul..."
for i in {1..30}; do
    if curl -f -s "http://${CONSUL_HOST:-localhost}:${CONSUL_PORT:-8500}/v1/status/leader" > /dev/null 2>&1; then
        echo "Consul is ready!"
        break
    fi
    echo "Waiting for Consul... ($i/30)"
    sleep 2
done

# Use supervisor with environment variables passed through
echo "Starting microservices with supervisor..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf