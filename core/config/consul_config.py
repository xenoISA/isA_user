#!/usr/bin/env python3
"""Consul service discovery configuration"""
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
class ConsulConfig:
    """Consul service discovery settings"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 8500

    @classmethod
    def from_env(cls) -> 'ConsulConfig':
        """Load Consul config from environment"""
        return cls(
            enabled=_bool(os.getenv("CONSUL_ENABLED", "true")),
            host=os.getenv("CONSUL_HOST", "localhost"),
            port=_int(os.getenv("CONSUL_PORT", "8500"), 8500),
        )
