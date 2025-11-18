"""
Vault Service

Business logic for secure credential and secret management with blockchain integration.
"""

import base64
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from core.blockchain_client import BlockchainClient

# from .clients import AccountClient, NotificationClient, OrganizationClient  # clients are empty files
from .encryption import (
    BlockchainVaultIntegration,
    VaultEncryption,
    decrypt_field,
    encrypt_field,
)
from core.nats_client import Event, EventType, ServiceSource
from .models import (
    EncryptionMethod,
    SecretType,
    VaultAccessLogResponse,
    VaultAction,
    VaultCreateRequest,
    VaultItem,
    VaultItemResponse,
    VaultListResponse,
    VaultSecretResponse,
    VaultShare,
    VaultShareRequest,
    VaultShareResponse,
    VaultStatsResponse,
    VaultTestResponse,
    VaultUpdateRequest,
)
from .vault_repository import VaultRepository

logger = logging.getLogger(__name__)


class VaultServiceError(Exception):
    """Base exception for vault service"""

    pass


class VaultAccessDeniedError(VaultServiceError):
    """Raised when user doesn't have permission"""

    pass


class VaultNotFoundError(VaultServiceError):
    """Raised when vault item not found"""

    pass


class VaultService:
    """Vault service for secure credential management"""

    def __init__(
        self,
        blockchain_client: Optional[BlockchainClient] = None,
        event_bus=None,
        config=None,
    ):
        self.repository = VaultRepository(config=config)
        self.encryption = VaultEncryption()
        self.event_bus = event_bus

        # Initialize blockchain integration if client provided
        self.blockchain = BlockchainVaultIntegration(blockchain_client)

        logger.info(
            f"Vault service initialized (Blockchain: {'enabled' if self.blockchain.enabled else 'disabled'})"
        )

    # ============ Core Vault Operations ============

    async def create_secret(
        self,
        user_id: str,
        request: VaultCreateRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[VaultItemResponse], str]:
        """Create a new secret"""
        try:
            logger.info(
                f"Creating secret for user {user_id}, type: {request.secret_type}"
            )

            # Encrypt the secret
            encrypted_data, dek_encrypted, kek_salt, nonce = (
                self.encryption.encrypt_secret(request.secret_value, user_id)
            )
            logger.info(
                f"Secret encrypted successfully, encrypted_data length: {len(encrypted_data)}"
            )

            # Create blockchain hash if requested
            blockchain_tx_hash = None
            if request.blockchain_verify and self.blockchain.enabled:
                secret_hash = self.encryption.hash_secret_for_blockchain(
                    request.secret_value
                )
                blockchain_tx_hash = await self.blockchain.store_secret_hash(
                    vault_id="temp",  # Will be updated after creation
                    secret_hash=secret_hash,
                )

            # Prepare encryption metadata
            encryption_metadata = {
                "dek_encrypted": base64.b64encode(dek_encrypted).decode(),
                "kek_salt": base64.b64encode(kek_salt).decode(),
                "nonce": base64.b64encode(nonce).decode(),
            }

            # Create vault item
            logger.info(f"Creating VaultItem model with provider: {request.provider}")
            vault_item = VaultItem(
                user_id=user_id,
                organization_id=request.organization_id,
                secret_type=request.secret_type,
                provider=request.provider,
                name=request.name,
                description=request.description,
                encrypted_value=encrypted_data,
                encryption_method=EncryptionMethod.AES_256_GCM,
                encryption_key_id=f"kek_{user_id}",
                metadata={**request.metadata, **encryption_metadata},
                tags=request.tags,
                expires_at=request.expires_at,
                rotation_enabled=request.rotation_enabled,
                rotation_days=request.rotation_days,
                blockchain_reference=blockchain_tx_hash,
            )
            logger.info("VaultItem model created successfully")

            logger.info("Calling repository.create_vault_item")
            result = await self.repository.create_vault_item(vault_item)
            logger.info(f"Repository create result: {result}")

            if not result:
                await self._log_access(
                    user_id,
                    "temp",
                    VaultAction.CREATE,
                    False,
                    ip_address,
                    user_agent,
                    "Failed to create vault item",
                )
                return False, None, "Failed to create secret"

            # Update blockchain reference if needed
            if blockchain_tx_hash:
                await self.repository.update_vault_item(
                    result.vault_id, {"blockchain_reference": blockchain_tx_hash}
                )

            # Log successful creation
            await self._log_access(
                user_id,
                result.vault_id,
                VaultAction.CREATE,
                True,
                ip_address,
                user_agent,
            )

            # Publish vault.secret.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.VAULT_SECRET_CREATED,
                        source=ServiceSource.VAULT_SERVICE,
                        data={
                            "vault_id": result.vault_id,
                            "user_id": user_id,
                            "organization_id": request.organization_id,
                            "secret_type": request.secret_type.value,
                            "provider": request.provider,
                            "name": request.name,
                            "blockchain_verified": blockchain_tx_hash is not None,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish vault.secret.created event: {e}")

            logger.info(f"Secret created successfully with vault_id: {result.vault_id}")
            return True, result, "Secret created successfully"

        except Exception as e:
            logger.error(f"Error creating secret: {e}", exc_info=True)
            return False, None, f"Failed to create secret: {str(e)}"

    async def get_secret(
        self,
        vault_id: str,
        user_id: str,
        decrypt: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[VaultSecretResponse], str]:
        """Get and optionally decrypt a secret"""
        try:
            # Check access
            permission = await self.repository.check_user_access(vault_id, user_id)
            if not permission:
                await self._log_access(
                    user_id,
                    vault_id,
                    VaultAction.READ,
                    False,
                    ip_address,
                    user_agent,
                    "Access denied",
                )
                return False, None, "Access denied"

            # Get vault item
            item = await self.repository.get_vault_item(vault_id)
            if not item:
                return False, None, "Secret not found"

            # Check if active
            if not item.get("is_active"):
                return False, None, "Secret is inactive"

            # Check expiration
            if item.get("expires_at"):
                expires_at = datetime.fromisoformat(item["expires_at"])
                if expires_at < datetime.utcnow():
                    return False, None, "Secret has expired"

            # Decrypt if requested
            secret_value = "[ENCRYPTED]"
            blockchain_verified = False

            if decrypt:
                try:
                    # Extract encryption components from metadata
                    metadata = item.get("metadata", {})
                    encrypted_data = base64.b64decode(item["encrypted_value"])
                    dek_encrypted = base64.b64decode(metadata["dek_encrypted"])
                    kek_salt = base64.b64decode(metadata["kek_salt"])
                    nonce = base64.b64decode(metadata["nonce"])

                    # Decrypt
                    secret_value = self.encryption.decrypt_secret(
                        encrypted_data, dek_encrypted, kek_salt, nonce, item["user_id"]
                    )

                    # Verify with blockchain if available
                    if item.get("blockchain_reference") and self.blockchain.enabled:
                        secret_hash = self.encryption.hash_secret_for_blockchain(
                            secret_value
                        )
                        blockchain_verified = (
                            await self.blockchain.verify_secret_from_blockchain(
                                vault_id, secret_hash, item["blockchain_reference"]
                            )
                        )

                except Exception as e:
                    logger.error(f"Decryption failed: {e}")
                    await self._log_access(
                        user_id,
                        vault_id,
                        VaultAction.READ,
                        False,
                        ip_address,
                        user_agent,
                        f"Decryption failed: {str(e)}",
                    )
                    return False, None, "Failed to decrypt secret"

            # Increment access count
            await self.repository.increment_access_count(vault_id)

            # Log successful access
            await self._log_access(
                user_id, vault_id, VaultAction.READ, True, ip_address, user_agent
            )

            # Publish vault.secret.accessed event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.VAULT_SECRET_ACCESSED,
                        source=ServiceSource.VAULT_SERVICE,
                        data={
                            "vault_id": vault_id,
                            "user_id": user_id,
                            "secret_type": item["secret_type"],
                            "decrypted": decrypt,
                            "blockchain_verified": blockchain_verified,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish vault.secret.accessed event: {e}")

            response = VaultSecretResponse(
                vault_id=vault_id,
                name=item["name"],
                secret_type=SecretType(item["secret_type"]),
                provider=item.get("provider"),
                secret_value=secret_value,
                metadata=item.get("metadata", {}),
                expires_at=datetime.fromisoformat(item["expires_at"])
                if item.get("expires_at")
                else None,
                blockchain_verified=blockchain_verified,
            )

            return True, response, "Secret retrieved successfully"

        except Exception as e:
            logger.error(f"Error getting secret: {e}")
            return False, None, f"Failed to get secret: {str(e)}"

    async def update_secret(
        self,
        vault_id: str,
        user_id: str,
        request: VaultUpdateRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[VaultItemResponse], str]:
        """Update a secret"""
        try:
            # Check write permission
            permission = await self.repository.check_user_access(vault_id, user_id)
            if permission not in ["owner", "read_write"]:
                await self._log_access(
                    user_id,
                    vault_id,
                    VaultAction.UPDATE,
                    False,
                    ip_address,
                    user_agent,
                    "Access denied",
                )
                return False, None, "Access denied"

            update_data = {}

            # Update non-secret fields
            if request.name:
                update_data["name"] = request.name
            if request.description is not None:
                update_data["description"] = request.description
            if request.metadata:
                # Merge with existing metadata
                item = await self.repository.get_vault_item(vault_id)
                existing_metadata = item.get("metadata", {})
                update_data["metadata"] = {**existing_metadata, **request.metadata}
            if request.tags:
                update_data["tags"] = request.tags
            if request.expires_at:
                update_data["expires_at"] = request.expires_at.isoformat()
            if request.rotation_enabled is not None:
                update_data["rotation_enabled"] = request.rotation_enabled
            if request.rotation_days:
                update_data["rotation_days"] = request.rotation_days
            if request.is_active is not None:
                update_data["is_active"] = request.is_active

            # Update secret value if provided
            if request.secret_value:
                item = await self.repository.get_vault_item(vault_id)
                encrypted_data, dek_encrypted, kek_salt, nonce = (
                    self.encryption.encrypt_secret(
                        request.secret_value, item["user_id"]
                    )
                )

                update_data["encrypted_value"] = base64.b64encode(
                    encrypted_data
                ).decode()
                update_data["version"] = item.get("version", 1) + 1

                # Update metadata with new encryption components
                encryption_metadata = {
                    "dek_encrypted": base64.b64encode(dek_encrypted).decode(),
                    "kek_salt": base64.b64encode(kek_salt).decode(),
                    "nonce": base64.b64encode(nonce).decode(),
                }
                existing_metadata = item.get("metadata", {})
                update_data["metadata"] = {**existing_metadata, **encryption_metadata}

            # Perform update
            success = await self.repository.update_vault_item(vault_id, update_data)

            if not success:
                await self._log_access(
                    user_id,
                    vault_id,
                    VaultAction.UPDATE,
                    False,
                    ip_address,
                    user_agent,
                    "Update failed",
                )
                return False, None, "Failed to update secret"

            # Get updated item
            updated_item = await self.repository.get_vault_item(vault_id)
            response = VaultItemResponse(**updated_item)

            await self._log_access(
                user_id, vault_id, VaultAction.UPDATE, True, ip_address, user_agent
            )

            # Publish vault.secret.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.VAULT_SECRET_UPDATED,
                        source=ServiceSource.VAULT_SERVICE,
                        data={
                            "vault_id": vault_id,
                            "user_id": user_id,
                            "secret_value_updated": request.secret_value is not None,
                            "metadata_updated": request.metadata is not None,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish vault.secret.updated event: {e}")

            return True, response, "Secret updated successfully"

        except Exception as e:
            logger.error(f"Error updating secret: {e}")
            return False, None, f"Failed to update secret: {str(e)}"

    async def delete_secret(
        self,
        vault_id: str,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Delete a secret (soft delete)"""
        try:
            # Check owner permission
            item = await self.repository.get_vault_item(vault_id)
            if not item or item.get("user_id") != user_id:
                await self._log_access(
                    user_id,
                    vault_id,
                    VaultAction.DELETE,
                    False,
                    ip_address,
                    user_agent,
                    "Access denied",
                )
                return False, "Access denied"

            success = await self.repository.delete_vault_item(vault_id)

            if not success:
                await self._log_access(
                    user_id,
                    vault_id,
                    VaultAction.DELETE,
                    False,
                    ip_address,
                    user_agent,
                    "Delete failed",
                )
                return False, "Failed to delete secret"

            await self._log_access(
                user_id, vault_id, VaultAction.DELETE, True, ip_address, user_agent
            )

            # Publish vault.secret.deleted event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.VAULT_SECRET_DELETED,
                        source=ServiceSource.VAULT_SERVICE,
                        data={
                            "vault_id": vault_id,
                            "user_id": user_id,
                            "secret_type": item.get("secret_type"),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish vault.secret.deleted event: {e}")

            return True, "Secret deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting secret: {e}")
            return False, f"Failed to delete secret: {str(e)}"

    async def list_secrets(
        self,
        user_id: str,
        secret_type: Optional[SecretType] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[bool, Optional[VaultListResponse], str]:
        """List user's secrets"""
        try:
            offset = (page - 1) * page_size

            items = await self.repository.list_user_vault_items(
                user_id=user_id,
                secret_type=secret_type,
                tags=tags,
                active_only=True,
                limit=page_size,
                offset=offset,
            )

            # Get total count (simplified)
            all_items = await self.repository.list_user_vault_items(
                user_id=user_id,
                secret_type=secret_type,
                tags=tags,
                active_only=True,
                limit=1000,
                offset=0,
            )
            total = len(all_items)

            response = VaultListResponse(
                items=items, total=total, page=page, page_size=page_size
            )

            return True, response, f"Found {len(items)} secrets"

        except Exception as e:
            logger.error(f"Error listing secrets: {e}")
            return False, None, f"Failed to list secrets: {str(e)}"

    # ============ Share Operations ============

    async def share_secret(
        self,
        vault_id: str,
        owner_user_id: str,
        request: VaultShareRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[VaultShareResponse], str]:
        """Share a secret with another user or organization"""
        try:
            # Verify ownership
            item = await self.repository.get_vault_item(vault_id)
            if not item or item.get("user_id") != owner_user_id:
                return False, None, "Access denied"

            share = VaultShare(
                vault_id=vault_id,
                owner_user_id=owner_user_id,
                shared_with_user_id=request.shared_with_user_id,
                shared_with_org_id=request.shared_with_org_id,
                permission_level=request.permission_level,
                expires_at=request.expires_at,
            )

            result = await self.repository.create_share(share)

            if not result:
                await self._log_access(
                    owner_user_id,
                    vault_id,
                    VaultAction.SHARE,
                    False,
                    ip_address,
                    user_agent,
                    "Share failed",
                )
                return False, None, "Failed to create share"

            await self._log_access(
                owner_user_id,
                vault_id,
                VaultAction.SHARE,
                True,
                ip_address,
                user_agent,
                metadata={
                    "shared_with": request.shared_with_user_id
                    or request.shared_with_org_id
                },
            )

            # Publish vault.secret.shared event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.VAULT_SECRET_SHARED,
                        source=ServiceSource.VAULT_SERVICE,
                        data={
                            "vault_id": vault_id,
                            "owner_user_id": owner_user_id,
                            "shared_with_user_id": request.shared_with_user_id,
                            "shared_with_org_id": request.shared_with_org_id,
                            "permission_level": request.permission_level.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish vault.secret.shared event: {e}")

            return True, result, "Secret shared successfully"

        except Exception as e:
            logger.error(f"Error sharing secret: {e}")
            return False, None, f"Failed to share secret: {str(e)}"

    async def get_shared_secrets(
        self, user_id: str
    ) -> Tuple[bool, List[VaultShareResponse], str]:
        """Get secrets shared with user"""
        try:
            shares = await self.repository.get_shares_for_user(user_id)
            return True, shares, f"Found {len(shares)} shared secrets"

        except Exception as e:
            logger.error(f"Error getting shared secrets: {e}")
            return False, [], f"Failed to get shared secrets: {str(e)}"

    # ============ Utility Operations ============

    async def get_access_logs(
        self,
        user_id: str,
        vault_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[bool, List[VaultAccessLogResponse], str]:
        """Get access logs"""
        try:
            offset = (page - 1) * page_size
            logs = await self.repository.get_access_logs(
                vault_id, user_id, page_size, offset
            )
            return True, logs, f"Found {len(logs)} log entries"

        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return False, [], f"Failed to get access logs: {str(e)}"

    async def get_stats(self, user_id: str) -> Tuple[bool, VaultStatsResponse, str]:
        """Get vault statistics"""
        try:
            stats = await self.repository.get_vault_stats(user_id)
            response = VaultStatsResponse(**stats)
            return True, response, "Statistics retrieved successfully"

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return False, VaultStatsResponse(), f"Failed to get stats: {str(e)}"

    async def rotate_secret(
        self,
        vault_id: str,
        user_id: str,
        new_secret_value: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[VaultItemResponse], str]:
        """Rotate a secret (create new version)"""
        try:
            # This is essentially an update with version increment
            request = VaultUpdateRequest(secret_value=new_secret_value)
            success, response, message = await self.update_secret(
                vault_id, user_id, request, ip_address, user_agent
            )

            # Publish vault.secret.rotated event if successful
            if success and self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.VAULT_SECRET_ROTATED,
                        source=ServiceSource.VAULT_SERVICE,
                        data={
                            "vault_id": vault_id,
                            "user_id": user_id,
                            "new_version": response.version if response else None,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish vault.secret.rotated event: {e}")

            return success, response, message

        except Exception as e:
            logger.error(f"Error rotating secret: {e}")
            return False, None, f"Failed to rotate secret: {str(e)}"

    async def test_credential(
        self, vault_id: str, user_id: str, test_endpoint: Optional[str] = None
    ) -> Tuple[bool, VaultTestResponse, str]:
        """Test if a credential is valid"""
        # This is a placeholder - actual implementation would depend on the secret type
        # For now, we just verify we can decrypt it
        try:
            success, secret, message = await self.get_secret(
                vault_id, user_id, decrypt=True
            )

            if not success:
                return False, VaultTestResponse(success=False, message=message), message

            # In a real implementation, you would test the credential against its service
            # For example, for API keys, make a test request to the provider

            response = VaultTestResponse(
                success=True,
                message="Credential is accessible and can be decrypted",
                details={
                    "secret_type": str(secret.secret_type),
                    "provider": str(secret.provider),
                },
            )

            return True, response, "Credential test completed"

        except Exception as e:
            logger.error(f"Error testing credential: {e}")
            return (
                False,
                VaultTestResponse(success=False, message=str(e)),
                f"Test failed: {str(e)}",
            )

    # ============ Helper Methods ============

    async def _log_access(
        self,
        user_id: str,
        vault_id: str,
        action: VaultAction,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log vault access"""
        try:
            log = VaultAccessLog(
                vault_id=vault_id,
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message,
                metadata=metadata or {},
            )
            await self.repository.create_access_log(log)
        except Exception as e:
            logger.error(f"Failed to create access log: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        return {
            "status": "healthy",
            "encryption": "enabled",
            "blockchain": self.blockchain.get_integration_status(),
            "timestamp": datetime.utcnow().isoformat(),
        }
