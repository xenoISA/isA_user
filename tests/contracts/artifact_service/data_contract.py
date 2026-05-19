"""Artifact Service data contract.

Layer 4 CDD source for canonical artifact_service test data. Tests that need
artifact fixtures should prefer this factory over ad hoc dictionaries.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from microservices.artifact_service.models import (
    Artifact,
    ArtifactCreateRequest,
    ArtifactKVResponse,
    ArtifactKVScope,
    ArtifactMCPGrant,
    ArtifactRuntimeInvokeRequest,
    ArtifactRuntimeUsageResponse,
    ArtifactShare,
    ArtifactShareVisibility,
    ArtifactStorageScope,
    ArtifactVersion,
    ArtifactVersionCreateRequest,
    ArtifactVisibility,
    MCPApproveRequest,
    MCPCallRequest,
    MCPGrantDecision,
    MCPGrantScope,
    PublishArtifactRequest,
)


class ArtifactVersionContract(BaseModel):
    artifact_id: str = "art_test_1"
    number: int = Field(1, ge=1)
    content: str = "print('hello from artifact')"
    language: str = "python"
    filename: str = "hello.py"


class ArtifactShareContract(BaseModel):
    artifact_id: str = "art_test_1"
    token: str = "artsh_test_token"
    visibility: ArtifactShareVisibility = ArtifactShareVisibility.PUBLIC
    created_by: str = "user_test_1"
    org_id: Optional[str] = None


class ArtifactRuntimeUsageContract(BaseModel):
    artifact_id: str = "art_test_1"
    user_id: str = "user_test_1"
    day_bucket: str = "2026-05-19"
    tokens_in: int = 12
    tokens_out: int = 24
    calls: int = 1
    quota: int = 50


class ArtifactMCPGrantContract(BaseModel):
    artifact_id: str = "art_test_1"
    user_id: str = "user_test_1"
    tool_name: str = "search_docs"
    server_id: str = "isa_docs"
    decision: MCPGrantDecision = MCPGrantDecision.ALLOW
    scope: MCPGrantScope = MCPGrantScope.ALWAYS


class ArtifactKVContract(BaseModel):
    artifact_id: str = "art_test_1"
    scope: ArtifactKVScope = ArtifactKVScope.PERSONAL
    user_id: Optional[str] = "user_test_1"
    key: str = "panel.state"
    value: Dict[str, Any] = Field(default_factory=lambda: {"open": True})


class ArtifactContractFactory:
    """Factory for canonical artifact_service fixtures."""

    @staticmethod
    def version_create(**overrides: Any) -> ArtifactVersionCreateRequest:
        data = ArtifactVersionContract().model_dump()
        data.pop("artifact_id")
        data.update(overrides)
        return ArtifactVersionCreateRequest(**data)

    @staticmethod
    def create_request(**overrides: Any) -> ArtifactCreateRequest:
        data = {
            "title": "Test Artifact",
            "content_type": "code",
            "owner_org_id": "org_test_1",
            "visibility": ArtifactVisibility.PRIVATE,
            "ai_runtime_enabled": True,
            "storage_scope": ArtifactStorageScope.PERSONAL,
            "metadata": {"source": "contract"},
            "version": ArtifactContractFactory.version_create(),
        }
        data.update(overrides)
        return ArtifactCreateRequest(**data)

    @staticmethod
    def artifact(**overrides: Any) -> Artifact:
        now = datetime.now(timezone.utc)
        version = ArtifactVersion(
            id="ver_test_1",
            artifact_id="art_test_1",
            number=1,
            content="print('hello from artifact')",
            language="python",
            filename="hello.py",
            created_by="user_test_1",
            created_at=now,
        )
        data = {
            "id": "art_test_1",
            "owner_user_id": "user_test_1",
            "owner_org_id": "org_test_1",
            "title": "Test Artifact",
            "content_type": "code",
            "current_version_id": version.id,
            "visibility": ArtifactVisibility.PRIVATE,
            "ai_runtime_enabled": True,
            "storage_scope": ArtifactStorageScope.PERSONAL,
            "metadata": {"source": "contract"},
            "created_at": now,
            "updated_at": now,
            "versions": [version],
        }
        data.update(overrides)
        return Artifact(**data)

    @staticmethod
    def share(**overrides: Any) -> ArtifactShare:
        now = datetime.now(timezone.utc)
        data = {
            **ArtifactShareContract().model_dump(),
            "expires_at": now + timedelta(days=7),
            "created_at": now,
            "view_count": 0,
        }
        data.update(overrides)
        return ArtifactShare(**data)

    @staticmethod
    def publish_request(**overrides: Any) -> PublishArtifactRequest:
        data = {
            "user_id": "user_test_1",
            "visibility": ArtifactShareVisibility.PUBLIC,
            "version_pin": 1,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        }
        data.update(overrides)
        return PublishArtifactRequest(**data)

    @staticmethod
    def runtime_invoke_request(**overrides: Any) -> ArtifactRuntimeInvokeRequest:
        data = {
            "user_id": "user_test_1",
            "prompt": "Summarize this artifact",
            "max_tokens": 128,
        }
        data.update(overrides)
        return ArtifactRuntimeInvokeRequest(**data)

    @staticmethod
    def runtime_usage(**overrides: Any) -> ArtifactRuntimeUsageResponse:
        contract = ArtifactRuntimeUsageContract()
        data = {
            **contract.model_dump(),
            "remaining": contract.quota - contract.calls,
        }
        data.update(overrides)
        return ArtifactRuntimeUsageResponse(**data)

    @staticmethod
    def mcp_approve_request(**overrides: Any) -> MCPApproveRequest:
        data = ArtifactMCPGrantContract().model_dump()
        data.update(overrides)
        return MCPApproveRequest(**data)

    @staticmethod
    def mcp_call_request(**overrides: Any) -> MCPCallRequest:
        data = {
            "user_id": "user_test_1",
            "tool_name": "search_docs",
            "server_id": "isa_docs",
            "args": {"query": "artifact service"},
        }
        data.update(overrides)
        return MCPCallRequest(**data)

    @staticmethod
    def mcp_grant(**overrides: Any) -> ArtifactMCPGrant:
        now = datetime.now(timezone.utc)
        data = {
            "id": "grnt_test_1",
            **ArtifactMCPGrantContract().model_dump(),
            "approved_at": now,
            "created_at": now,
            "updated_at": now,
        }
        data.update(overrides)
        return ArtifactMCPGrant(**data)

    @staticmethod
    def kv_response(**overrides: Any) -> ArtifactKVResponse:
        data = {
            **ArtifactKVContract().model_dump(),
            "updated_at": datetime.now(timezone.utc),
        }
        data.update(overrides)
        return ArtifactKVResponse(**data)
