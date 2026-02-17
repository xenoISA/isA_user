#!/usr/bin/env python3
"""Service configuration for peer ISA services

External service dependencies - peer ISA services that isA_User microservices
may call (model, mcp, agent, data, os).

Note: isA_User services communicate with each other via internal routing,
so this config is primarily for peer ISA service integration.
"""
import os
from dataclasses import dataclass

def _bool(val: str) -> bool:
    return val.lower() == "true"


@dataclass
class ServiceConfig:
    """Peer ISA service endpoints"""

    # ===========================================
    # Peer ISA Services
    # ===========================================
    # isA_Model - LLM/Embedding service
    model_service_url: str = "http://localhost:8082"

    # isA_MCP - MCP tools service
    mcp_service_url: str = "http://localhost:8081"

    # isA_Agent - Agent orchestration
    agent_service_url: str = "http://localhost:8080"

    # isA_Data - RAG/Analytics service
    data_service_url: str = "http://localhost:8084"

    # isA_OS - Web/Cloud OS services
    web_service_url: str = "http://localhost:8083"
    os_service_url: str = "http://localhost:8085"

    # ===========================================
    # API Gateway
    # ===========================================
    gateway_url: str = "http://localhost:9080"
    gateway_enabled: bool = False

    # ===========================================
    # Service Discovery
    # ===========================================
    use_consul_discovery: bool = True

    @classmethod
    def from_env(cls) -> 'ServiceConfig':
        """Load service configuration from environment variables"""
        return cls(
            # Peer ISA Services
            model_service_url=os.getenv("ISA_MODEL_URL") or os.getenv("MODEL_SERVICE_URL", "http://localhost:8082"),
            mcp_service_url=os.getenv("MCP_SERVICE_URL") or os.getenv("MCP_SERVER_URL", "http://localhost:8081"),
            agent_service_url=os.getenv("AGENT_SERVICE_URL", "http://localhost:8080"),
            data_service_url=os.getenv("DATA_SERVICE_URL") or os.getenv("DIGITAL_ANALYTICS_URL", "http://localhost:8084"),
            web_service_url=os.getenv("WEB_SERVICE_URL", "http://localhost:8083"),
            os_service_url=os.getenv("OS_SERVICE_URL", "http://localhost:8085"),

            # Gateway
            gateway_url=os.getenv("GATEWAY_URL", "http://localhost:9080"),
            gateway_enabled=_bool(os.getenv("GATEWAY_ENABLED", "false")),

            # Discovery
            use_consul_discovery=_bool(os.getenv("USE_CONSUL_DISCOVERY", "true")),
        )
