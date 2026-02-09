#!/usr/bin/env python3
"""Logging configuration"""
import os
from dataclasses import dataclass

def _bool(val: str) -> bool:
    return val.lower() == "true"

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default


@dataclass
class LoggingConfig:
    """Logging configuration"""
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = ""
    enable_console: bool = True
    enable_structured: bool = False

    # Loki integration
    loki_enabled: bool = False
    loki_host: str = "localhost"
    loki_port: int = 3100
    loki_url: str = "http://localhost:3100"

    # Service identity for logging
    service_name: str = "user"
    environment: str = "development"

    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Load logging config from environment variables"""
        env = os.getenv("ENV") or os.getenv("ENVIRONMENT", "development")
        return cls(
            log_level=os.getenv("LOG_LEVEL", "DEBUG" if env == "development" else "INFO"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            log_file=os.getenv("LOG_FILE", ""),
            enable_console=True,
            enable_structured=_bool(os.getenv("ENABLE_STRUCTURED_LOGGING", "false")),
            loki_enabled=_bool(os.getenv("LOKI_ENABLED", "false")),
            loki_host=os.getenv("LOKI_HOST", "localhost"),
            loki_port=_int(os.getenv("LOKI_PORT", "3100"), 3100),
            loki_url=os.getenv("LOKI_URL", "http://localhost:3100"),
            service_name=os.getenv("SERVICE_NAME", "user"),
            environment=env,
        )
