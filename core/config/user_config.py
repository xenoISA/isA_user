#!/usr/bin/env python3
"""User service main configuration

Main configuration for isA_User microservices platform.
Combines all sub-configs and includes user-specific resource configuration.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List

from .infra_config import InfraConfig
from .logging_config import LoggingConfig
from .consul_config import ConsulConfig
from .model_config import ModelConfig
from .service_config import ServiceConfig


def _bool(val: str) -> bool:
    return val.lower() == "true"

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default


# ===========================================
# User-Specific Resource Configuration
# ===========================================

@dataclass
class UserQdrantConfig:
    """Qdrant collection names for User services"""
    # Memory service collections
    semantic_memories: str = "user_semantic_memories"
    working_memories: str = "user_working_memories"
    document_embeddings: str = "user_document_embeddings"
    media_embeddings: str = "user_media_embeddings"

    @property
    def all_collections(self) -> List[str]:
        return [
            self.semantic_memories,
            self.working_memories,
            self.document_embeddings,
            self.media_embeddings,
        ]

    @classmethod
    def from_env(cls) -> 'UserQdrantConfig':
        prefix = os.getenv("USER_QDRANT_PREFIX", "user")
        return cls(
            semantic_memories=os.getenv("USER_QDRANT_SEMANTIC", f"{prefix}_semantic_memories"),
            working_memories=os.getenv("USER_QDRANT_WORKING", f"{prefix}_working_memories"),
            document_embeddings=os.getenv("USER_QDRANT_DOCUMENTS", f"{prefix}_document_embeddings"),
            media_embeddings=os.getenv("USER_QDRANT_MEDIA", f"{prefix}_media_embeddings"),
        )


@dataclass
class UserMinIOConfig:
    """MinIO bucket names for User services"""
    media_bucket: str = "isa-media"
    documents_bucket: str = "isa-documents"
    storage_bucket: str = "isa-storage"
    backups_bucket: str = "isa-backups"
    temp_bucket: str = "isa-temp"

    @property
    def all_buckets(self) -> List[str]:
        return [
            self.media_bucket,
            self.documents_bucket,
            self.storage_bucket,
            self.backups_bucket,
            self.temp_bucket,
        ]

    @classmethod
    def from_env(cls) -> 'UserMinIOConfig':
        return cls(
            media_bucket=os.getenv("USER_MINIO_MEDIA", "isa-media"),
            documents_bucket=os.getenv("USER_MINIO_DOCUMENTS", "isa-documents"),
            storage_bucket=os.getenv("USER_MINIO_STORAGE", "isa-storage"),
            backups_bucket=os.getenv("USER_MINIO_BACKUPS", "isa-backups"),
            temp_bucket=os.getenv("USER_MINIO_TEMP", "isa-temp"),
        )


@dataclass
class UserRedisConfig:
    """Redis key prefixes for User services"""
    session_prefix: str = "user:session:"
    cache_prefix: str = "user:cache:"
    rate_prefix: str = "user:rate:"
    lock_prefix: str = "user:lock:"
    pubsub_prefix: str = "user:pubsub:"

    @classmethod
    def from_env(cls) -> 'UserRedisConfig':
        prefix = os.getenv("USER_REDIS_PREFIX", "user")
        return cls(
            session_prefix=f"{prefix}:session:",
            cache_prefix=f"{prefix}:cache:",
            rate_prefix=f"{prefix}:rate:",
            lock_prefix=f"{prefix}:lock:",
            pubsub_prefix=f"{prefix}:pubsub:",
        )


@dataclass
class UserNATSConfig:
    """NATS stream configuration for User services"""
    # Stream names for event-driven architecture
    account_stream: str = "ACCOUNT"
    audit_stream: str = "AUDIT"
    payment_stream: str = "PAYMENT"
    notification_stream: str = "NOTIFICATION"
    device_stream: str = "DEVICE"

    @classmethod
    def from_env(cls) -> 'UserNATSConfig':
        return cls(
            account_stream=os.getenv("USER_NATS_ACCOUNT_STREAM", "ACCOUNT"),
            audit_stream=os.getenv("USER_NATS_AUDIT_STREAM", "AUDIT"),
            payment_stream=os.getenv("USER_NATS_PAYMENT_STREAM", "PAYMENT"),
            notification_stream=os.getenv("USER_NATS_NOTIFICATION_STREAM", "NOTIFICATION"),
            device_stream=os.getenv("USER_NATS_DEVICE_STREAM", "DEVICE"),
        )


@dataclass
class UserResourceConfig:
    """Combined User resource configuration"""
    qdrant: UserQdrantConfig = field(default_factory=UserQdrantConfig)
    minio: UserMinIOConfig = field(default_factory=UserMinIOConfig)
    redis: UserRedisConfig = field(default_factory=UserRedisConfig)
    nats: UserNATSConfig = field(default_factory=UserNATSConfig)

    @classmethod
    def from_env(cls) -> 'UserResourceConfig':
        return cls(
            qdrant=UserQdrantConfig.from_env(),
            minio=UserMinIOConfig.from_env(),
            redis=UserRedisConfig.from_env(),
            nats=UserNATSConfig.from_env(),
        )


# ===========================================
# Main User Configuration
# ===========================================

@dataclass
class UserConfig:
    """Main User platform configuration with all sub-configs"""

    # Environment
    environment: str = "development"
    debug: bool = False

    # Default service settings (each microservice overrides these)
    default_host: str = "0.0.0.0"
    default_port: int = 8000

    # JWT/Auth Configuration
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600

    # Auth0 (external auth)
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None

    # Sub-configurations
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    infrastructure: InfraConfig = field(default_factory=InfraConfig)
    consul: ConsulConfig = field(default_factory=ConsulConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    services: ServiceConfig = field(default_factory=ServiceConfig)
    resources: UserResourceConfig = field(default_factory=UserResourceConfig)

    @classmethod
    def from_env(cls) -> 'UserConfig':
        """Load complete configuration from environment"""
        env = os.getenv("ENV") or os.getenv("ENVIRONMENT", "development")
        return cls(
            # Environment
            environment=env,
            debug=_bool(os.getenv("DEBUG", "true" if env == "development" else "false")),

            # Default service settings
            default_host=os.getenv("HOST", "0.0.0.0"),
            default_port=_int(os.getenv("PORT", "8000"), 8000),

            # JWT/Auth
            jwt_secret=os.getenv("LOCAL_JWT_SECRET") or os.getenv("JWT_SECRET"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expiration=_int(os.getenv("JWT_EXPIRATION", "3600"), 3600),

            # Auth0
            auth0_domain=os.getenv("AUTH0_DOMAIN"),
            auth0_audience=os.getenv("AUTH0_AUDIENCE"),

            # Load sub-configs
            logging=LoggingConfig.from_env(),
            infrastructure=InfraConfig.from_env(),
            consul=ConsulConfig.from_env(),
            model=ModelConfig.from_env(),
            services=ServiceConfig.from_env(),
            resources=UserResourceConfig.from_env(),
        )
