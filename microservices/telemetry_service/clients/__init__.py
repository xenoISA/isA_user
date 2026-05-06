"""
Telemetry Service Clients Module

HTTP clients for synchronous communication with other microservices.
"""

from .telemetry_client import TelemetryServiceClient
from .ws_resilient_client import (
    ReplicaEndpoint,
    ResilientTelemetryWebSocket,
    compute_backoff_delay,
    discover_replicas,
)

__all__ = [
    "TelemetryServiceClient",
    "ResilientTelemetryWebSocket",
    "ReplicaEndpoint",
    "compute_backoff_delay",
    "discover_replicas",
]
