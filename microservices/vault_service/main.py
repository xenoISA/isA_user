"""
Vault Microservice

Secure credential and secret management with blockchain verification support.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import core components
from core.blockchain_client import BlockchainClient
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from isa_common.consul_client import ConsulRegistry

from .models import (
    HealthResponse,
    SecretType,
    ServiceInfo,
    VaultAccessLogResponse,
    VaultCreateRequest,
    VaultItemResponse,
    VaultListResponse,
    VaultSecretResponse,
    VaultShareRequest,
    VaultShareResponse,
    VaultStatsResponse,
    VaultTestRequest,
    VaultTestResponse,
    VaultUpdateRequest,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Import local components
from .vault_service import (
    VaultAccessDeniedError,
    VaultNotFoundError,
    VaultService,
    VaultServiceError,
)

# Initialize configuration
config_manager = ConfigManager("vault_service")
config = config_manager.get_service_config()

# Setup loggers
app_logger = setup_service_logger("vault_service")
logger = app_logger

# Global service instances
vault_service = None
blockchain_client = None
event_bus = None  # NATS event bus
consul_registry = None  # Consul registry


def get_user_id(request: Request) -> str:
    """Extract user ID from request headers"""
    x_user_id = request.headers.get("X-User-Id")
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required",
        )
    return x_user_id


def get_client_info(request: Request) -> tuple:
    """Extract client information from request"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    return ip_address, user_agent


def get_vault_service() -> VaultService:
    """Get vault service instance"""
    global vault_service
    if vault_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vault service not initialized",
        )
    return vault_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global consul_registry, vault_service, blockchain_client, event_bus

    try:
        # Initialize blockchain client (optional)
        try:
            # Get blockchain configuration
            blockchain_enabled = (
                os.getenv("BLOCKCHAIN_ENABLED", "false").lower() == "true"
            )
            if blockchain_enabled:
                gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8000")
                blockchain_client = BlockchainClient(gateway_url=gateway_url)
                logger.info("Blockchain client initialized")
        except Exception as e:
            logger.warning(f"Blockchain client initialization failed: {e}")
            blockchain_client = None

        # Initialize NATS JetStream event bus
        try:
            event_bus = await get_event_bus("vault_service")
            logger.info("✅ Event bus initialized successfully")

            # Initialize vault service with event bus
            vault_service = VaultService(blockchain_client=blockchain_client, event_bus=event_bus, config=config_manager)

        except Exception as e:
            logger.warning(
                f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing."
            )
            event_bus = None

            # Initialize vault service without event bus
            vault_service = VaultService(blockchain_client=blockchain_client, event_bus=None, config=config_manager)

        # =============================================================================
        # Subscribe to events using standardized event handlers
        # =============================================================================
        if event_bus and vault_service:
            try:
                from .events import get_event_handlers

                # Get all event handlers from events/handlers.py
                event_handlers = get_event_handlers(vault_service=vault_service)

                # Subscribe to each event pattern
                for pattern, handler in event_handlers.items():
                    await event_bus.subscribe_to_events(
                        pattern=pattern,
                        handler=handler,
                        durable=f"vault-{pattern.split('.')[-1]}-consumer",
                    )
                    logger.info(f"✅ Subscribed to {pattern}")

                logger.info(
                    f"✅ Vault service subscribed to {len(event_handlers)} event types"
                )

            except Exception as e:
                logger.warning(f"⚠️  Failed to subscribe to events: {e}")

        logger.info("Vault microservice initialized successfully")

        # Register with Consul
        if config.consul_enabled:
            try:
                # Get route metadata
                route_meta = get_routes_for_consul()

                # Merge service metadata
                consul_meta = {
                    "version": SERVICE_METADATA["version"],
                    "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                    **route_meta,
                }

                consul_registry = ConsulRegistry(
                    service_name=SERVICE_METADATA["service_name"],
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port,
                    tags=SERVICE_METADATA["tags"],
                    meta=consul_meta,
                    health_check_type="http",
                )
                consul_registry.register()
                logger.info(
                    f"✅ Service registered with Consul: {route_meta.get('route_count')} routes"
                )
            except Exception as e:
                logger.warning(f"⚠️  Failed to register with Consul: {e}")
                consul_registry = None

        logger.info(f"✅ Vault Service started on port {config.service_port}")

        yield

    except Exception as e:
        logger.error(f"Error during service startup: {e}")
        raise
    finally:
        # Cleanup resources
        if event_bus:
            try:
                await event_bus.close()
                logger.info("Vault event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")

        if consul_registry:
            try:
                consul_registry.deregister()
                logger.info("✅ Vault service deregistered from Consul")
            except Exception as e:
                logger.error(f"❌ Failed to deregister from Consul: {e}")

        logger.info("Vault Service shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Vault Service",
    description="Secure credential and secret management microservice with blockchain verification",
    version="1.0.0",
    lifespan=lifespan,
)


# ============ Health & Info Endpoints ============


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check"""
    return HealthResponse(
        status="healthy",
        service=config.service_name,
        port=config.service_port,
        version="1.0.0",
    )


@app.get("/health/detailed")
async def detailed_health_check(
    vault_service: VaultService = Depends(get_vault_service),
):
    """Detailed health check"""
    try:
        health_data = await vault_service.health_check()
        return {
            "service": config.service_name,
            "status": "operational",
            "port": config.service_port,
            "version": "1.0.0",
            **health_data,
        }
    except Exception as e:
        return {"service": config.service_name, "status": "degraded", "error": str(e)}


@app.get("/info", response_model=ServiceInfo)
async def service_info():
    """Service information"""
    return ServiceInfo()


# ============ Vault Secret Management Endpoints ============


@app.post(
    "/api/v1/vault/secrets",
    response_model=VaultItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_secret(
    request_data: VaultCreateRequest,
    request: Request,
    vault_service: VaultService = Depends(get_vault_service),
):
    """Create a new secret"""
    try:
        logger.info(f"[main.py] create_secret endpoint called for user header")
        user_id = get_user_id(request)
        logger.info(f"[main.py] User ID: {user_id}")
        ip_address, user_agent = get_client_info(request)

        logger.info(f"[main.py] Calling vault_service.create_secret")
        success, result, message = await vault_service.create_secret(
            user_id=user_id,
            request=request_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info(
            f"[main.py] vault_service.create_secret returned: success={success}, message={message}"
        )

        if not success:
            logger.error(f"[main.py] Create failed with message: {message}")
            raise HTTPException(status_code=400, detail=message)

        logger.info(f"[main.py] Returning success result")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating secret: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create secret")


@app.get("/api/v1/vault/secrets/{vault_id}", response_model=VaultSecretResponse)
async def get_secret(
    vault_id: str,
    request: Request,
    decrypt: bool = Query(True, description="Decrypt the secret value"),
    vault_service: VaultService = Depends(get_vault_service),
):
    """Get a secret by ID (optionally decrypted)"""
    try:
        user_id = get_user_id(request)
        ip_address, user_agent = get_client_info(request)

        success, result, message = await vault_service.get_secret(
            vault_id=vault_id,
            user_id=user_id,
            decrypt=decrypt,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not success:
            if "Access denied" in message:
                raise HTTPException(status_code=403, detail=message)
            elif "not found" in message.lower():
                raise HTTPException(status_code=404, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to get secret")


@app.get("/api/v1/vault/secrets", response_model=VaultListResponse)
async def list_secrets(
    request: Request,
    secret_type: Optional[SecretType] = Query(
        None, description="Filter by secret type"
    ),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    vault_service: VaultService = Depends(get_vault_service),
):
    """List user's secrets"""
    try:
        user_id = get_user_id(request)

        tag_list = tags.split(",") if tags else None

        success, result, message = await vault_service.list_secrets(
            user_id=user_id,
            secret_type=secret_type,
            tags=tag_list,
            page=page,
            page_size=page_size,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing secrets: {e}")
        raise HTTPException(status_code=500, detail="Failed to list secrets")


@app.put("/api/v1/vault/secrets/{vault_id}", response_model=VaultItemResponse)
async def update_secret(
    vault_id: str,
    request: Request,
    request_data: VaultUpdateRequest,
    vault_service: VaultService = Depends(get_vault_service),
):
    """Update a secret"""
    try:
        user_id = get_user_id(request)
        ip_address, user_agent = get_client_info(request)

        success, result, message = await vault_service.update_secret(
            vault_id=vault_id,
            user_id=user_id,
            request=request_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not success:
            if "Access denied" in message:
                raise HTTPException(status_code=403, detail=message)
            elif "not found" in message.lower():
                raise HTTPException(status_code=404, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to update secret")


@app.delete("/api/v1/vault/secrets/{vault_id}")
async def delete_secret(
    vault_id: str,
    request: Request,
    vault_service: VaultService = Depends(get_vault_service),
):
    """Delete a secret"""
    try:
        user_id = get_user_id(request)
        ip_address, user_agent = get_client_info(request)

        success, message = await vault_service.delete_secret(
            vault_id=vault_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not success:
            if "Access denied" in message:
                raise HTTPException(status_code=403, detail=message)
            elif "not found" in message.lower():
                raise HTTPException(status_code=404, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

        return {"message": message}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete secret")


@app.post("/api/v1/vault/secrets/{vault_id}/rotate", response_model=VaultItemResponse)
async def rotate_secret(
    vault_id: str,
    request: Request,
    new_secret_value: str = Query(..., description="New secret value"),
    vault_service: VaultService = Depends(get_vault_service),
):
    """Rotate a secret (create new version)"""
    try:
        user_id = get_user_id(request)
        ip_address, user_agent = get_client_info(request)

        success, result, message = await vault_service.rotate_secret(
            vault_id=vault_id,
            user_id=user_id,
            new_secret_value=new_secret_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not success:
            if "Access denied" in message:
                raise HTTPException(status_code=403, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate secret")


# ============ Sharing Endpoints ============


@app.post("/api/v1/vault/secrets/{vault_id}/share", response_model=VaultShareResponse)
async def share_secret(
    vault_id: str,
    request: Request,
    request_data: VaultShareRequest,
    vault_service: VaultService = Depends(get_vault_service),
):
    """Share a secret with another user or organization"""
    try:
        user_id = get_user_id(request)
        ip_address, user_agent = get_client_info(request)

        success, result, message = await vault_service.share_secret(
            vault_id=vault_id,
            owner_user_id=user_id,
            request=request_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not success:
            if "Access denied" in message:
                raise HTTPException(status_code=403, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to share secret")


@app.get("/api/v1/vault/shared", response_model=List[VaultShareResponse])
async def get_shared_secrets(
    request: Request, vault_service: VaultService = Depends(get_vault_service)
):
    """Get secrets shared with the user"""
    try:
        user_id = get_user_id(request)

        success, result, message = await vault_service.get_shared_secrets(
            user_id=user_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shared secrets: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shared secrets")


# ============ Utility Endpoints ============


@app.get("/api/v1/vault/audit-logs", response_model=List[VaultAccessLogResponse])
async def get_audit_logs(
    request: Request,
    vault_id: Optional[str] = Query(None, description="Filter by vault ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=200, description="Items per page"),
    vault_service: VaultService = Depends(get_vault_service),
):
    """Get access audit logs"""
    try:
        user_id = get_user_id(request)

        success, result, message = await vault_service.get_access_logs(
            user_id=user_id, vault_id=vault_id, page=page, page_size=page_size
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit logs")


@app.get("/api/v1/vault/stats", response_model=VaultStatsResponse)
async def get_vault_stats(
    request: Request, vault_service: VaultService = Depends(get_vault_service)
):
    """Get vault statistics"""
    try:
        user_id = get_user_id(request)

        success, result, message = await vault_service.get_stats(user_id=user_id)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")


@app.post("/api/v1/vault/secrets/{vault_id}/test", response_model=VaultTestResponse)
async def test_credential(
    vault_id: str,
    request: Request,
    test_request: Optional[VaultTestRequest] = None,
    vault_service: VaultService = Depends(get_vault_service),
):
    """Test if a credential is valid"""
    try:
        user_id = get_user_id(request)

        test_endpoint = test_request.test_endpoint if test_request else None

        success, result, message = await vault_service.test_credential(
            vault_id=vault_id, user_id=user_id, test_endpoint=test_endpoint
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to test credential")


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()

    uvicorn.run(
        "microservices.vault_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
