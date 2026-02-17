#!/usr/bin/env python3
"""
Core Module for Microservices Architecture

This package provides essential shared components for all microservices in the system.
After cleanup, only the critical infrastructure components remain.

COMPONENTS:
    - config/: Modular configuration system (NEW - standardized config approach)
        - infra_config.py: Infrastructure services from isA_Cloud
        - service_config.py: Peer ISA services
        - model_config.py: LLM/embedding from isA_Model
        - user_config.py: User platform settings
    - config_manager.py: Legacy configuration management (backward compatibility)
    - blockchain_client.py: Blockchain integration for payment services
    - gateway_client.py: API Gateway client for inter-service communication
    - database/: Supabase database connection and utilities
    - nats_client.py: NATS event bus for event-driven architecture

USAGE:
    # New modular config (recommended)
    from core.config import get_settings
    settings = get_settings()
    vector_size = settings.model.vector_size

    # Legacy config manager (backward compatibility)
    from core.config_manager import ConfigManager
    config = ConfigManager("service_name")

NOTE: Service discovery now handled by Consul agent sidecar, not programmatic registration

VERSION: 2.1.0 - Added modular configuration system
"""

# Import new modular config system
try:
    from .config import (
        UserConfig,
        get_settings,
        reload_settings,
        settings as user_settings,
        LoggingConfig,
        InfraConfig,
        ConsulConfig,
        ModelConfig,
        ServiceConfig as PeerServiceConfig,
        UserResourceConfig,
    )
except ImportError:
    UserConfig = None
    get_settings = None
    reload_settings = None
    user_settings = None
    LoggingConfig = None
    InfraConfig = None
    ConsulConfig = None
    ModelConfig = None
    PeerServiceConfig = None
    UserResourceConfig = None

# Import legacy config manager (backward compatibility)
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
    # New modular config system (recommended)
    "UserConfig",
    "get_settings",
    "reload_settings",
    "user_settings",
    "LoggingConfig",
    "InfraConfig",
    "ConsulConfig",
    "ModelConfig",
    "PeerServiceConfig",
    "UserResourceConfig",
    # Legacy config (backward compatibility)
    "ConfigManager",
    "Environment",
    "ServiceConfig",
    "create_config",
    # Clients
    "BlockchainClient",
    "GatewayClient",
    "MQTTClient",
    "DeviceCommandClient",
    "create_command_client",
    "create_mqtt_client",
]

__version__ = "2.1.0"