"""
Authentication Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_auth_service
    service = create_auth_service(config, event_bus)
"""
from typing import Optional
import os

from core.config_manager import ConfigManager

from .auth_service import AuthenticationService


def create_auth_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> AuthenticationService:
    """
    Create AuthenticationService with real dependencies.

    This function imports the real clients and JWT manager (which have I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events

    Returns:
        Configured AuthenticationService instance
    """
    # Import real dependencies here (not at module level)
    from core.jwt_manager import get_jwt_manager
    from microservices.account_service.client import AccountServiceClient
    from microservices.notification_service.clients.notification_client import (
        NotificationServiceClient,
    )
    from .auth_repository import AuthRepository
    from .oauth_client_repository import OAuthClientRepository

    # Get configuration values
    jwt_secret = None
    jwt_expiry = 3600

    if config:
        # Extract config from ServiceConfig object
        jwt_secret = getattr(config, 'local_jwt_secret', None) or os.getenv("JWT_SECRET")
        jwt_expiry = getattr(config, 'jwt_expiration', 3600)
    else:
        jwt_secret = os.getenv("JWT_SECRET")

    # Create JWT Manager
    jwt_manager = get_jwt_manager(
        secret_key=jwt_secret,
        algorithm="HS256",
        issuer="isA_user",
        access_token_expiry=jwt_expiry,
        refresh_token_expiry=604800,  # 7 days
    )

    # Create Account Service Client
    account_client = AccountServiceClient()

    # Create Notification Service Client
    notification_client = NotificationServiceClient()

    # Create Auth Repository for database operations
    auth_repository = AuthRepository(config)
    oauth_client_repository = OAuthClientRepository(config)

    return AuthenticationService(
        jwt_manager=jwt_manager,
        account_client=account_client,
        notification_client=notification_client,
        event_bus=event_bus,
        auth_repository=auth_repository,
        oauth_client_repository=oauth_client_repository,
        config=config,
    )
