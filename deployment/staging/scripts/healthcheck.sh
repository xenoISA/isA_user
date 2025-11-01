#!/bin/bash

# ==========================================
# isA User Platform - Health Check Script
# ==========================================
# This script checks if all microservices are running and responding

set -e

SERVICES=(
    "auth_service:8201"
    "account_service:8202" 
    "session_service:8203"
    "authorization_service:8204"
    "audit_service:8205"
    "notification_service:8206"
    "payment_service:8207"
    "wallet_service:8208"
    "storage_service:8209"
    "order_service:8210"
    "task_service:8211"
    "organization_service:8212"
    "invitation_service:8213"
    "vault_service:8214"
    "device_service:8220"
    "ota_service:8221"
    "telemetry_service:8225"
    "event_service:8230"
)

FAILED_SERVICES=()

echo "Performing health check on all services..."

for service in "${SERVICES[@]}"; do
    IFS=':' read -r service_name port <<< "$service"
    
    # Check if service is responding on its port
    if curl -f -s "http://localhost:${port}/health" > /dev/null 2>&1; then
        echo "✓ ${service_name} (port ${port}) - OK"
    else
        echo "✗ ${service_name} (port ${port}) - FAILED"
        FAILED_SERVICES+=("$service_name")
    fi
done

if [ ${#FAILED_SERVICES[@]} -eq 0 ]; then
    echo "All services are healthy!"
    exit 0
else
    echo "Failed services: ${FAILED_SERVICES[*]}"
    exit 1
fi