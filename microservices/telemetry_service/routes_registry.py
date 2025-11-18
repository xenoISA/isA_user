"""
Telemetry Service Routes Registry
Defines all API routes for Consul service registration
"""

from typing import List, Dict, Any

# Define all routes
SERVICE_ROUTES = [
    # Health checks
    {"path": "/health", "methods": ["GET"], "auth_required": False, "description": "Basic health check"},
    {"path": "/health/detailed", "methods": ["GET"], "auth_required": False, "description": "Detailed health check"},

    # Data ingestion
    {"path": "/api/v1/devices/{device_id}/telemetry", "methods": ["POST"], "auth_required": True, "description": "Ingest single data point"},
    {"path": "/api/v1/devices/{device_id}/telemetry/batch", "methods": ["POST"], "auth_required": True, "description": "Batch ingest data"},
    {"path": "/api/v1/telemetry/bulk", "methods": ["POST"], "auth_required": True, "description": "Bulk ingest multi-device"},

    # Metric management
    {"path": "/api/v1/metrics", "methods": ["GET", "POST"], "auth_required": True, "description": "List/create metrics"},
    {"path": "/api/v1/metrics/{metric_name}", "methods": ["GET", "DELETE"], "auth_required": True, "description": "Get/delete metric definition"},

    # Data queries
    {"path": "/api/v1/query", "methods": ["POST"], "auth_required": True, "description": "Query telemetry data"},
    {"path": "/api/v1/devices/{device_id}/metrics/{metric_name}/latest", "methods": ["GET"], "auth_required": True, "description": "Get latest value"},
    {"path": "/api/v1/devices/{device_id}/metrics", "methods": ["GET"], "auth_required": True, "description": "Get device metrics"},
    {"path": "/api/v1/devices/{device_id}/metrics/{metric_name}/range", "methods": ["GET"], "auth_required": True, "description": "Get metric range"},

    # Aggregation
    {"path": "/api/v1/aggregated", "methods": ["GET"], "auth_required": True, "description": "Get aggregated data"},

    # Alert management
    {"path": "/api/v1/alerts/rules", "methods": ["GET", "POST"], "auth_required": True, "description": "List/create alert rules"},
    {"path": "/api/v1/alerts/rules/{rule_id}", "methods": ["GET"], "auth_required": True, "description": "Get alert rule"},
    {"path": "/api/v1/alerts/rules/{rule_id}/enable", "methods": ["PUT"], "auth_required": True, "description": "Enable/disable rule"},
    {"path": "/api/v1/alerts", "methods": ["GET"], "auth_required": True, "description": "List alerts"},
    {"path": "/api/v1/alerts/{alert_id}/acknowledge", "methods": ["PUT"], "auth_required": True, "description": "Acknowledge alert"},
    {"path": "/api/v1/alerts/{alert_id}/resolve", "methods": ["PUT"], "auth_required": True, "description": "Resolve alert"},

    # Statistics
    {"path": "/api/v1/devices/{device_id}/stats", "methods": ["GET"], "auth_required": True, "description": "Device stats"},
    {"path": "/api/v1/stats", "methods": ["GET"], "auth_required": True, "description": "Service stats"},

    # Real-time streaming
    {"path": "/api/v1/subscribe", "methods": ["POST", "DELETE"], "auth_required": True, "description": "Subscribe/unsubscribe real-time"},
    {"path": "/ws/telemetry/{subscription_id}", "methods": ["WS"], "auth_required": True, "description": "WebSocket stream"},

    # Export
    {"path": "/api/v1/export/csv", "methods": ["GET"], "auth_required": True, "description": "Export CSV"},
    {"path": "/api/v1/service/stats", "methods": ["GET"], "auth_required": False, "description": "Service info"},
]

def get_routes_for_consul() -> Dict[str, Any]:
    """
    Generate compact route metadata for Consul
    Note: Consul meta fields have 512 character limit
    """
    # Categorize routes
    health_routes = []
    ingestion_routes = []
    metric_routes = []
    query_routes = []
    alert_routes = []
    stats_routes = []

    for route in SERVICE_ROUTES:
        path = route["path"]

        if "/health" in path:
            health_routes.append("health" if path == "/health" else "detailed")
        elif "/telemetry" in path or "/bulk" in path:
            ingestion_routes.append(path.split("/")[-1])
        elif "/metrics" in path and "/query" not in path:
            metric_routes.append(path.split("/")[-1] if "{" not in path.split("/")[-1] else "*")
        elif "/query" in path or "/latest" in path or "/range" in path or "/aggregated" in path:
            query_routes.append(path.split("/")[-1])
        elif "/alerts" in path:
            alert_routes.append(path.split("/")[-1] if "{" not in path.split("/")[-1] else "*")
        elif "/stats" in path:
            stats_routes.append("device" if "device_id" in path else "service")

    return {
        "route_count": str(len(SERVICE_ROUTES)),
        "base_path": "/api/v1/telemetry",
        "health": ",".join(set(health_routes)),
        "ingestion": ",".join(list(set(ingestion_routes))[:5]),  # Limit for space
        "metrics": ",".join(list(set(metric_routes))[:5]),
        "queries": ",".join(list(set(query_routes))[:5]),
        "alerts": ",".join(list(set(alert_routes))[:5]),
        "stats": ",".join(set(stats_routes)),
        "methods": "GET,POST,PUT,DELETE,WS",
        "public_count": str(sum(1 for r in SERVICE_ROUTES if not r["auth_required"])),
        "protected_count": str(sum(1 for r in SERVICE_ROUTES if r["auth_required"])),
    }

# Service metadata
SERVICE_METADATA = {
    "service_name": "telemetry_service",
    "version": "1.0.0",
    "tags": ["v1", "iot-microservice", "telemetry", "monitoring"],
    "capabilities": [
        "data_ingestion",
        "metric_definitions",
        "time_series_queries",
        "data_aggregation",
        "alert_management",
        "real_time_streaming",
        "statistical_analysis",
        "data_export"
    ]
}
