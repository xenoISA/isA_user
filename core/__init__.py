#!/usr/bin/env python3
"""
Core Module for Microservices Architecture

This package provides essential shared components for all microservices in the system.
After cleanup, only the critical infrastructure components remain.

COMPONENTS:
    - config.py: Legacy configuration (maintained for backward compatibility)
    - config_manager.py: Modern centralized configuration management system
    - blockchain_client.py: Blockchain integration for payment services
    - gateway_client.py: API Gateway client for inter-service communication
    - database/: Supabase database connection and utilities
    - nats_client.py: NATS event bus for event-driven architecture

USAGE:
    from core.config_manager import ConfigManager
    from core.blockchain_client import BlockchainClient

    # Initialize configuration for a service
    config = ConfigManager("service_name")

NOTE: Service discovery now handled by Consul agent sidecar, not programmatic registration

VERSION: 2.0.0 - Modernized and cleaned for microservices architecture
"""

# Import main components for easy access

try:
    from .config_manager import ConfigManager, Environment, ServiceConfig, create_config
except ImportError:
    ConfigManager = None
    Environment = None
    ServiceConfig = None
    create_config = None

try:
    from .blockchain_client import BlockchainClient
except ImportError:
    BlockchainClient = None

try:
    from .gateway_client import GatewayClient
except ImportError:
    GatewayClient = None

try:
    from .mqtt_client import MQTTClient, DeviceCommandClient, create_command_client, create_mqtt_client
except ImportError:
    MQTTClient = None
    DeviceCommandClient = None
    create_command_client = None
    create_mqtt_client = None

# Export public API
__all__ = [
    "ConfigManager",
    "Environment",
    "ServiceConfig",
    "create_config",
    "BlockchainClient",
    "GatewayClient",
    "MQTTClient",
    "DeviceCommandClient",
    "create_command_client",
    "create_mqtt_client",
]

__version__ = "2.0.0"