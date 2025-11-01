"""
Vault Service Client Example

Professional client for secure credential and secret management with encryption, sharing, and audit features.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Types of secrets"""
    API_KEY = "api_key"
    DATABASE_CREDENTIAL = "database_credential"
    SSH_KEY = "ssh_key"
    SSL_CERTIFICATE = "ssl_certificate"
    OAUTH_TOKEN = "oauth_token"
    AWS_CREDENTIAL = "aws_credential"
    BLOCKCHAIN_KEY = "blockchain_key"
    ENVIRONMENT_VARIABLE = "environment_variable"
    CUSTOM = "custom"


class SecretProvider(str, Enum):
    """Service providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    STRIPE = "stripe"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    GITHUB = "github"
    GITLAB = "gitlab"
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    CUSTOM = "custom"


class PermissionLevel(str, Enum):
    """Permission levels for sharing"""
    READ = "read"
    READ_WRITE = "read_write"


@dataclass
class VaultItem:
    """Vault item (secret metadata)"""
    vault_id: str
    user_id: str
    secret_type: str
    name: str
    provider: Optional[str]
    description: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    version: int
    is_active: bool
    rotation_enabled: bool
    created_at: str
    updated_at: str


@dataclass
class VaultSecret:
    """Decrypted secret"""
    vault_id: str
    name: str
    secret_type: str
    secret_value: str
    provider: Optional[str]
    metadata: Dict[str, Any]
    expires_at: Optional[str]
    blockchain_verified: bool


@dataclass
class VaultShare:
    """Secret share"""
    share_id: str
    vault_id: str
    owner_user_id: str
    shared_with_user_id: Optional[str]
    shared_with_org_id: Optional[str]
    permission_level: str
    created_at: str
    expires_at: Optional[str]


@dataclass
class VaultStats:
    """Vault statistics"""
    total_secrets: int
    active_secrets: int
    expired_secrets: int
    secrets_by_type: Dict[str, int]
    secrets_by_provider: Dict[str, int]
    total_access_count: int
    shared_secrets: int
    blockchain_verified_secrets: int


class VaultClient:
    """Professional Vault Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8214",
        user_id: str = "default_user",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "vault-client/1.0",
                "Accept": "application/json",
                "X-User-Id": self.user_id
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    # Secret Management
    async def create_secret(
        self,
        name: str,
        secret_type: SecretType,
        secret_value: str,
        provider: Optional[SecretProvider] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        rotation_enabled: bool = False,
        rotation_days: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        blockchain_verify: bool = False
    ) -> VaultItem:
        """Create a new encrypted secret"""
        payload = {
            "name": name,
            "secret_type": secret_type.value,
            "secret_value": secret_value
        }
        if provider:
            payload["provider"] = provider.value
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags
        if metadata:
            payload["metadata"] = metadata
        if rotation_enabled:
            payload["rotation_enabled"] = rotation_enabled
        if rotation_days:
            payload["rotation_days"] = rotation_days
        if expires_at:
            payload["expires_at"] = expires_at.isoformat()
        if blockchain_verify:
            payload["blockchain_verify"] = blockchain_verify

        result = await self._make_request(
            "POST",
            "/api/v1/vault/secrets",
            json=payload
        )
        return VaultItem(**result)

    async def get_secret(
        self,
        vault_id: str,
        decrypt: bool = True
    ) -> VaultSecret:
        """Get a secret by ID (optionally decrypted)"""
        result = await self._make_request(
            "GET",
            f"/api/v1/vault/secrets/{vault_id}",
            params={"decrypt": decrypt}
        )
        return VaultSecret(**result)

    async def list_secrets(
        self,
        secret_type: Optional[SecretType] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """List user's secrets"""
        params = {"page": page, "page_size": page_size}
        if secret_type:
            params["secret_type"] = secret_type.value
        if tags:
            params["tags"] = ",".join(tags)

        result = await self._make_request(
            "GET",
            "/api/v1/vault/secrets",
            params=params
        )
        return result

    async def update_secret(
        self,
        vault_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        secret_value: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        rotation_enabled: Optional[bool] = None,
        rotation_days: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> VaultItem:
        """Update a secret"""
        payload = {}
        if name:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if secret_value:
            payload["secret_value"] = secret_value
        if tags:
            payload["tags"] = tags
        if metadata:
            payload["metadata"] = metadata
        if rotation_enabled is not None:
            payload["rotation_enabled"] = rotation_enabled
        if rotation_days:
            payload["rotation_days"] = rotation_days
        if is_active is not None:
            payload["is_active"] = is_active

        result = await self._make_request(
            "PUT",
            f"/api/v1/vault/secrets/{vault_id}",
            json=payload
        )
        return VaultItem(**result)

    async def rotate_secret(
        self,
        vault_id: str,
        new_secret_value: str
    ) -> VaultItem:
        """Rotate a secret to a new value"""
        result = await self._make_request(
            "POST",
            f"/api/v1/vault/secrets/{vault_id}/rotate",
            params={"new_secret_value": new_secret_value}
        )
        return VaultItem(**result)

    async def delete_secret(self, vault_id: str) -> bool:
        """Delete a secret"""
        result = await self._make_request(
            "DELETE",
            f"/api/v1/vault/secrets/{vault_id}"
        )
        return "deleted" in result.get("message", "").lower()

    # Sharing Operations
    async def share_secret(
        self,
        vault_id: str,
        shared_with_user_id: Optional[str] = None,
        shared_with_org_id: Optional[str] = None,
        permission_level: PermissionLevel = PermissionLevel.READ,
        expires_at: Optional[datetime] = None
    ) -> VaultShare:
        """Share a secret with another user or organization"""
        payload = {"permission_level": permission_level.value}
        if shared_with_user_id:
            payload["shared_with_user_id"] = shared_with_user_id
        if shared_with_org_id:
            payload["shared_with_org_id"] = shared_with_org_id
        if expires_at:
            payload["expires_at"] = expires_at.isoformat()

        result = await self._make_request(
            "POST",
            f"/api/v1/vault/secrets/{vault_id}/share",
            json=payload
        )
        return VaultShare(**result)

    async def get_shared_secrets(self) -> List[VaultShare]:
        """Get secrets shared with the user"""
        result = await self._make_request(
            "GET",
            "/api/v1/vault/shared"
        )
        return [VaultShare(**share) for share in result]

    # Audit & Statistics
    async def get_audit_logs(
        self,
        vault_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Get access audit logs"""
        params = {"page": page, "page_size": page_size}
        if vault_id:
            params["vault_id"] = vault_id

        result = await self._make_request(
            "GET",
            "/api/v1/vault/audit-logs",
            params=params
        )
        return result

    async def get_stats(self) -> VaultStats:
        """Get vault statistics"""
        result = await self._make_request(
            "GET",
            "/api/v1/vault/stats"
        )
        return VaultStats(**result)

    async def test_credential(self, vault_id: str) -> Dict[str, Any]:
        """Test if a credential is valid"""
        result = await self._make_request(
            "POST",
            f"/api/v1/vault/secrets/{vault_id}/test",
            json={}
        )
        return result

    # Health & Info
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

    async def detailed_health_check(self) -> Dict[str, Any]:
        """Detailed health check"""
        return await self._make_request("GET", "/health/detailed")

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return await self._make_request("GET", "/info")

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Vault Service Client Examples")
    print("=" * 70)

    test_user_id = "client_example_user"
    
    async with VaultClient(user_id=test_user_id) as client:
        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f"  Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Detailed Health Check
        print("\n2. Detailed Health Check")
        print("-" * 70)
        detailed_health = await client.detailed_health_check()
        print(f"  Service: {detailed_health['service']}")
        print(f"  Status: {detailed_health['status']}")
        print(f"  Encryption: {detailed_health['encryption']}")
        print(f"  Blockchain: {detailed_health['blockchain']['enabled']}")

        # Example 3: Service Info
        print("\n3. Get Service Information")
        print("-" * 70)
        info = await client.get_service_info()
        print(f"  Service: {info['service']}")
        print(f"  Version: {info['version']}")
        print(f"  Capabilities:")
        for cap, enabled in info['capabilities'].items():
            print(f"    {cap}: {'✓' if enabled else '✗'}")

        # Example 4: Create API Key Secret
        print("\n4. Create API Key Secret")
        print("-" * 70)
        try:
            api_secret = await client.create_secret(
                name="OpenAI Production Key",
                secret_type=SecretType.API_KEY,
                provider=SecretProvider.OPENAI,
                secret_value="sk-proj-example1234567890abcdefghijklmnopqrstuvwxyz",
                description="Production OpenAI API key for GPT-4",
                tags=["openai", "production", "gpt4"],
                metadata={
                    "environment": "production",
                    "team": "ai-research",
                    "model": "gpt-4"
                },
                rotation_enabled=True,
                rotation_days=90
            )
            print(f"  Secret created: {api_secret.vault_id}")
            print(f"  Name: {api_secret.name}")
            print(f"  Type: {api_secret.secret_type}")
            print(f"  Rotation: {api_secret.rotation_enabled}")
            vault_id = api_secret.vault_id
        except Exception as e:
            print(f"  ⚠️  Error creating secret: {e}")
            vault_id = None

        # Example 5: Create Database Credential
        print("\n5. Create Database Credential")
        print("-" * 70)
        try:
            db_secret = await client.create_secret(
                name="Production PostgreSQL",
                secret_type=SecretType.DATABASE_CREDENTIAL,
                provider=SecretProvider.CUSTOM,
                secret_value="postgresql://dbuser:SecureP@ss123!@db.example.com:5432/maindb",
                description="Main production database credentials",
                tags=["database", "postgresql", "production"],
                metadata={
                    "db_type": "postgresql",
                    "host": "db.example.com",
                    "database": "maindb",
                    "port": 5432
                },
                rotation_enabled=True,
                rotation_days=30
            )
            print(f"  DB Secret created: {db_secret.vault_id}")
            print(f"  Name: {db_secret.name}")
            print(f"  Rotation days: {db_secret.rotation_enabled}")
            db_vault_id = db_secret.vault_id
        except Exception as e:
            print(f"  ⚠️  Error creating DB secret: {e}")
            db_vault_id = None

        # Example 6: Create AWS Credential
        print("\n6. Create AWS Credential")
        print("-" * 70)
        try:
            aws_secret = await client.create_secret(
                name="AWS Production Keys",
                secret_type=SecretType.AWS_CREDENTIAL,
                provider=SecretProvider.AWS,
                secret_value='{"access_key": "AKIAIOSFODNN7EXAMPLE", "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}',
                description="AWS production environment credentials",
                tags=["aws", "cloud", "production"],
                metadata={
                    "region": "us-east-1",
                    "account_id": "123456789012",
                    "environment": "production"
                },
                rotation_enabled=True,
                rotation_days=60
            )
            print(f"  AWS Secret created: {aws_secret.vault_id}")
            print(f"  Provider: {aws_secret.provider}")
        except Exception as e:
            print(f"  ⚠️  Error creating AWS secret: {e}")

        # Example 7: List All Secrets
        print("\n7. List All Secrets")
        print("-" * 70)
        secrets_list = await client.list_secrets(page=1, page_size=10)
        print(f"  Total secrets: {secrets_list['total']}")
        print(f"  Page: {secrets_list['page']}")
        for item in secrets_list['items'][:3]:
            print(f"    - {item['name']} ({item['secret_type']})")

        # Example 8: Filter Secrets by Type
        print("\n8. Filter Secrets by Type (API Keys)")
        print("-" * 70)
        api_secrets = await client.list_secrets(secret_type=SecretType.API_KEY)
        print(f"  API Key secrets: {api_secrets['total']}")
        for item in api_secrets['items'][:2]:
            print(f"    - {item['name']}")

        # Example 9: Filter Secrets by Tags
        print("\n9. Filter Secrets by Tags")
        print("-" * 70)
        tagged_secrets = await client.list_secrets(tags=["production", "api"])
        print(f"  Secrets with tags 'production' and 'api': {tagged_secrets['total']}")

        if vault_id:
            # Example 10: Get Secret (Encrypted)
            print("\n10. Get Secret (Encrypted)")
            print("-" * 70)
            try:
                encrypted_secret = await client.get_secret(vault_id, decrypt=False)
                print(f"  Vault ID: {encrypted_secret.vault_id}")
                print(f"  Name: {encrypted_secret.name}")
                print(f"  Secret Value: {encrypted_secret.secret_value}")
                print(f"  (Should show [ENCRYPTED])")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

            # Example 11: Get Secret (Decrypted)
            print("\n11. Get Secret (Decrypted)")
            print("-" * 70)
            try:
                decrypted_secret = await client.get_secret(vault_id, decrypt=True)
                print(f"  Vault ID: {decrypted_secret.vault_id}")
                print(f"  Name: {decrypted_secret.name}")
                print(f"  Secret Value: {'*' * 20} (hidden for security)")
                print(f"  Blockchain Verified: {decrypted_secret.blockchain_verified}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

            # Example 12: Update Secret Metadata
            print("\n12. Update Secret Metadata")
            print("-" * 70)
            try:
                updated_secret = await client.update_secret(
                    vault_id=vault_id,
                    name="OpenAI Production Key (Updated)",
                    description="Updated production OpenAI API key for GPT-4",
                    tags=["openai", "production", "gpt4", "updated"],
                    metadata={
                        "environment": "production",
                        "team": "ai-research",
                        "model": "gpt-4",
                        "last_updated": datetime.now().isoformat()
                    }
                )
                print(f"  Secret updated: {updated_secret.vault_id}")
                print(f"  New name: {updated_secret.name}")
                print(f"  Version: {updated_secret.version}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

            # Example 13: Share Secret
            print("\n13. Share Secret with Another User")
            print("-" * 70)
            try:
                share = await client.share_secret(
                    vault_id=vault_id,
                    shared_with_user_id="teammate_user_123",
                    permission_level=PermissionLevel.READ
                )
                print(f"  Share created: {share.share_id}")
                print(f"  Shared with: {share.shared_with_user_id}")
                print(f"  Permission: {share.permission_level}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

            # Example 14: Test Credential
            print("\n14. Test Credential")
            print("-" * 70)
            try:
                test_result = await client.test_credential(vault_id)
                print(f"  Test Success: {test_result['success']}")
                print(f"  Message: {test_result['message']}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

        if db_vault_id:
            # Example 15: Rotate Secret
            print("\n15. Rotate Database Secret")
            print("-" * 70)
            try:
                rotated_secret = await client.rotate_secret(
                    vault_id=db_vault_id,
                    new_secret_value="postgresql://dbuser:NewRotatedP@ss456!@db.example.com:5432/maindb"
                )
                print(f"  Secret rotated: {rotated_secret.vault_id}")
                print(f"  New version: {rotated_secret.version}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

        # Example 16: Get Shared Secrets
        print("\n16. Get Shared Secrets")
        print("-" * 70)
        try:
            shared_secrets = await client.get_shared_secrets()
            print(f"  Total shared secrets: {len(shared_secrets)}")
            for share in shared_secrets[:3]:
                print(f"    - Vault: {share.vault_id} (Permission: {share.permission_level})")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

        # Example 17: Get Vault Statistics
        print("\n17. Get Vault Statistics")
        print("-" * 70)
        try:
            stats = await client.get_stats()
            print(f"  Total secrets: {stats.total_secrets}")
            print(f"  Active secrets: {stats.active_secrets}")
            print(f"  Shared secrets: {stats.shared_secrets}")
            print(f"  Blockchain verified: {stats.blockchain_verified_secrets}")
            print(f"  Secrets by type:")
            for stype, count in stats.secrets_by_type.items():
                print(f"    {stype}: {count}")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

        # Example 18: Get Audit Logs
        print("\n18. Get Audit Logs")
        print("-" * 70)
        try:
            audit_logs = await client.get_audit_logs(page=1, page_size=10)
            print(f"  Total audit entries: {len(audit_logs)}")
            for log in audit_logs[:3]:
                print(f"    - Action: {log['action']} | Success: {log['success']} | Time: {log['created_at']}")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

        if vault_id:
            # Example 19: Get Audit Logs for Specific Vault
            print("\n19. Get Audit Logs for Specific Vault")
            print("-" * 70)
            try:
                vault_logs = await client.get_audit_logs(vault_id=vault_id, page=1, page_size=5)
                print(f"  Audit entries for vault: {len(vault_logs)}")
                for log in vault_logs:
                    print(f"    - {log['action']} at {log['created_at']}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

        if db_vault_id:
            # Example 20: Delete Secret
            print("\n20. Delete Secret")
            print("-" * 70)
            try:
                deleted = await client.delete_secret(db_vault_id)
                print(f"  Secret deleted: {deleted}")
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

        # Show Client Metrics
        print("\n21. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"  Total requests: {metrics['total_requests']}")
        print(f"  Total errors: {metrics['total_errors']}")
        print(f"  Error rate: {metrics['error_rate']:.2%}")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())

