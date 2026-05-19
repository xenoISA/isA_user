"""
JWT pass-through tests for factual_service.

Mirrors test_summary_service_synthesis.py (PR xenoISA/isA_user#454) — when the
route receives an Authorization header, the extract path forwards it to
AsyncISAModel via extra_headers. When absent/empty, no extra_headers is
attached (preserves the service-level auth path).

Refs xenoISA/isA_user#464.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _make_service():
    """Build a FactualMemoryService without hitting Qdrant/Postgres."""
    from microservices.memory_service.factual_service import FactualMemoryService

    svc = FactualMemoryService.__new__(FactualMemoryService)
    svc.model_url = "http://isa-model:8082"
    svc.collection_name = "facts_test"
    svc.qdrant = MagicMock()
    return svc


@pytest.fixture
def captured_init_kwargs():
    """Capture the kwargs passed to AsyncISAModel so the test can inspect
    extra_headers without mocking the whole inference protocol."""
    captured = {}

    class _StubClient:
        def __init__(self, **kwargs):
            captured["init_kwargs"] = kwargs
            self.chat = MagicMock()
            self.chat.completions = MagicMock()
            self.chat.completions.create = AsyncMock(
                return_value=MagicMock(
                    choices=[MagicMock(message=MagicMock(content=json.dumps({"facts": []})))],
                    usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                )
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a, **kw):
            return False

    with patch(
        "microservices.memory_service.factual_service.AsyncISAModel",
        new=_StubClient,
    ):
        yield captured


async def test_extract_forwards_auth_header_to_llm(captured_init_kwargs):
    svc = _make_service()
    await svc._extract_facts("alice said hi", auth_token="test-jwt")
    assert captured_init_kwargs["init_kwargs"]["extra_headers"] == {"Authorization": "Bearer test-jwt"}


async def test_extract_no_auth_header_uses_default(captured_init_kwargs):
    """Empty / None token → no extra_headers attached → upstream uses default auth."""
    svc = _make_service()

    await svc._extract_facts("alice said hi")
    assert "extra_headers" not in captured_init_kwargs["init_kwargs"]

    await svc._extract_facts("alice said hi", auth_token=None)
    assert "extra_headers" not in captured_init_kwargs["init_kwargs"]

    await svc._extract_facts("alice said hi", auth_token="   ")
    assert "extra_headers" not in captured_init_kwargs["init_kwargs"]


async def test_extract_bare_jwt_gets_bearer_prefix(captured_init_kwargs):
    """Tokens that already have 'Bearer ' aren't double-prefixed; bare JWTs get one."""
    svc = _make_service()

    await svc._extract_facts("x", auth_token="raw-jwt-without-prefix")
    assert captured_init_kwargs["init_kwargs"]["extra_headers"]["Authorization"] == "Bearer raw-jwt-without-prefix"

    await svc._extract_facts("x", auth_token="Bearer already-prefixed")
    assert captured_init_kwargs["init_kwargs"]["extra_headers"]["Authorization"] == "Bearer already-prefixed"
