#!/usr/bin/env python3
"""Modular configuration system for isA_User

Configuration hierarchy:
- infra_config: Infrastructure services from isA_Cloud (PostgreSQL, Redis, Qdrant, etc.)
- service_config: Peer ISA services (model, mcp, agent, data, os)
- model_config: LLM/embedding models from isA_Model
- user_config: User platform settings (auth, resources)
- consul_config: Service discovery settings
- logging_config: Logging configuration
"""
import os
from dotenv import load_dotenv
from .logging_config import LoggingConfig
from .infra_config import InfraConfig
from .consul_config import ConsulConfig
from .model_config import ModelConfig
from .service_config import ServiceConfig
from .user_config import (
    UserConfig,
    UserResourceConfig,
    UserQdrantConfig,
    UserMinIOConfig,
    UserRedisConfig,
    UserNATSConfig,
)

# Load environment file based on ENV
env = os.getenv("ENV") or os.getenv("ENVIRONMENT", "development")
env_files = {
    "development": "deployment/environments/dev.env",
    "dev": "deployment/environments/dev.env",
    "testing": "deployment/environments/test.env",
    "test": "deployment/environments/test.env",
    "staging": "deployment/environments/staging.env",
    "production": "deployment/environments/production.env",
}
env_file = env_files.get(env, "deployment/environments/dev.env")
load_dotenv(env_file, override=False)

# Create global settings instance
settings = UserConfig.from_env()

def get_settings() -> UserConfig:
    """Get global settings instance"""
    return settings

def reload_settings() -> UserConfig:
    """Reload settings from environment"""
    global settings
    settings = UserConfig.from_env()
    return settings

__all__ = [
    # Main config
    'UserConfig',
    'get_settings',
    'reload_settings',
    'settings',
    # Sub-configs
    'LoggingConfig',
    'InfraConfig',
    'ConsulConfig',
    'ModelConfig',
    'ServiceConfig',
    # User resource configs
    'UserResourceConfig',
    'UserQdrantConfig',
    'UserMinIOConfig',
    'UserRedisConfig',
    'UserNATSConfig',
]
