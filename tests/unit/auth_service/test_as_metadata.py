"""
Unit tests for OAuth Authorization Server Metadata (RFC 8414).

Validates that /.well-known/oauth-authorization-server returns the
Phase 3 fields: authorization_endpoint, response_types_supported,
code_challenge_methods_supported, client_id_metadata_document_supported,
and updated grant_types / auth methods.

Covers: xenoISA/isA_user#165
"""

import os
import sys

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.unit

METADATA_PATH = "/.well-known/oauth-authorization-server"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def metadata_response():
    """Fetch the AS metadata from the running FastAPI app."""
    from microservices.auth_service.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(METADATA_PATH)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.anyio
async def test_metadata_has_authorization_endpoint(metadata_response):
    """authorization_endpoint must be present and point to /oauth/authorize."""
    assert "authorization_endpoint" in metadata_response
    assert metadata_response["authorization_endpoint"].endswith("/oauth/authorize")


@pytest.mark.anyio
async def test_metadata_has_response_types(metadata_response):
    """response_types_supported must include 'code'."""
    assert metadata_response["response_types_supported"] == ["code"]


@pytest.mark.anyio
async def test_metadata_has_pkce_methods(metadata_response):
    """code_challenge_methods_supported must include S256."""
    assert metadata_response["code_challenge_methods_supported"] == ["S256"]


@pytest.mark.anyio
async def test_metadata_grant_types_include_auth_code(metadata_response):
    """grant_types_supported must include authorization_code."""
    grant_types = metadata_response["grant_types_supported"]
    assert "authorization_code" in grant_types
    assert "client_credentials" in grant_types


@pytest.mark.anyio
async def test_metadata_supports_public_clients(metadata_response):
    """token_endpoint_auth_methods_supported must include 'none' for public clients."""
    auth_methods = metadata_response["token_endpoint_auth_methods_supported"]
    assert "none" in auth_methods
    assert "client_secret_post" in auth_methods


@pytest.mark.anyio
async def test_metadata_cimd_supported(metadata_response):
    """client_id_metadata_document_supported must be True."""
    assert metadata_response["client_id_metadata_document_supported"] is True
