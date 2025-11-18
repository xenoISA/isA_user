"""
Telemetry Service Clients Module

HTTP clients for synchronous communication with other microservices.
"""

from .telemetry_client import TelemetryServiceClient

__all__ = [
    "TelemetryServiceClient",
]
